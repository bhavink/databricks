"""Collect AWS facts from `terraform show -json` output (plan or state).

Works for the awsdb4u roots (aws-pl-ws/databricks-aws-production,
serverless-ws, workspace-guardrails), the Databricks SRA (aws/tf) and any
Terraform using the same resources. A multi-root build gives one plan per
root: collect each and pass all of them to `assess` (facts merge).

Facts a plan can't establish (e.g. an existing VPC managed elsewhere) are
left out, so their checks report UNKNOWN rather than FAIL.
"""

from __future__ import annotations

import json

from ...facts import COMPUTED, EVIDENCE
from ..azure import tfplan as common
from ..gcp import tfplan as gcp

resources = common.resources
_of_type = common._of_type
_first = common._first
_is_set = common._is_set

PROVENANCE = {
    "workspace.": ("databricks_mws_workspaces",),
    "workspace.public_access_enabled": ("databricks_mws_private_access_settings",),
    "workspace.private_access_level": ("databricks_mws_private_access_settings",),
    "network.": ("aws_vpc", "aws_subnet"),
    "network.s3_gateway_endpoint": ("aws_vpc_endpoint",),
    "network.s3_endpoint_policy_restricted": ("aws_vpc_endpoint", "aws_vpc_endpoint_policy"),
    "network.nat_gateway": ("aws_nat_gateway",),
    "network.egress_controlled": ("aws_vpc", "aws_nat_gateway", "aws_internet_gateway",
                                  "aws_networkfirewall_firewall"),
    "private_link.": ("databricks_mws_networks", "databricks_mws_vpc_endpoint",
                      "databricks_mws_private_access_settings"),
    "serverless.ncc_bound": ("databricks_mws_ncc_binding", "databricks_mws_workspaces"),
    "serverless.egress_restricted": ("databricks_account_network_policy", "databricks_workspace_network_option"),
    "access.": ("databricks_workspace_conf", "databricks_ip_access_list"),
    "access.context_ingress_enforced": ("databricks_account_network_policy", "databricks_workspace_network_option"),
    "access.public_ingress_ip_restricted": ("databricks_account_network_policy",
                                            "databricks_workspace_network_option"),
    "governance.metastore_assigned": ("databricks_metastore_assignment",),
    "operations.audit_log_delivery": ("databricks_mws_log_delivery",),
}


def collect(doc: dict, workspace: str | None = None) -> dict:
    rs = resources(doc)
    facts = _collect(doc, rs, workspace)
    evidence = {}
    for ns, values in facts.items():
        if not isinstance(values, dict):
            continue
        for key in values:
            path = f"{ns}.{key}"
            types = PROVENANCE.get(path) or PROVENANCE.get(f"{ns}.")
            if types:
                found = [f"terraform:{r['address']}" for r in rs if r["type"] in types]
                evidence[path] = found or [f"terraform: no {' / '.join(types)} in plan"]
    facts[EVIDENCE] = evidence
    return facts


def _collect(doc: dict, rs: list[dict], workspace: str | None) -> dict:
    facts: dict = {"cloud": "aws", "source": "terraform-plan" if "resource_changes" in doc else "terraform-state"}
    ws = gcp._workspaces(rs, workspace)
    pas = [r["values"] for r in _of_type(rs, "databricks_mws_private_access_settings")]
    keys = _of_type(rs, "databricks_mws_customer_managed_keys")
    if ws:
        v = ws["values"]
        serverless = v.get("compute_mode") == "SERVERLESS"
        info = {
            "name": v.get("workspace_name"),
            "compute_mode": "serverless" if serverless else "classic",
            "customer_managed_vpc": not serverless and (
                _is_set(v.get("network_id")) or bool(_of_type(rs, "databricks_mws_networks"))),
            "cmk_managed_services": _is_set(v.get("managed_services_customer_managed_key_id")),
            "cmk_storage": _is_set(v.get("storage_customer_managed_key_id")),
        }
        if pas or _is_set(v.get("private_access_settings_id")):
            info["public_access_enabled"] = (pas[0].get("public_access_enabled", True) if pas else COMPUTED)
            info["private_access_level"] = pas[0].get("private_access_level", "ACCOUNT") if pas else COMPUTED
        else:
            info["public_access_enabled"] = True  # no private access settings: public front-end
        # Keys created in the same plan but attached by id later still count
        if keys and not (info["cmk_managed_services"] or info["cmk_storage"]):
            uses = {u for r in keys for u in r["values"].get("use_cases") or []}
            info["cmk_managed_services"] = "MANAGED_SERVICES" in uses
            info["cmk_storage"] = "STORAGE" in uses
        facts["workspace"] = info

    facts["network"] = _network(rs)
    facts["private_link"] = _private_link(rs)
    facts["serverless"] = gcp._serverless(rs, ws)
    facts["access"] = _access(rs)
    if _of_type(rs, "databricks_metastore_assignment") or ws:
        facts["governance"] = {"metastore_assigned": bool(_of_type(rs, "databricks_metastore_assignment"))}
    if _of_type(rs, "databricks_mws_log_delivery"):
        facts["operations"] = {"audit_log_delivery": any(
            r["values"].get("log_type") == "AUDIT_LOGS" and r["values"].get("status", "ENABLED") == "ENABLED"
            for r in _of_type(rs, "databricks_mws_log_delivery"))}
    return {k: v for k, v in facts.items() if v not in ({}, None)}


def _compute_subnets(rs) -> list[dict]:
    """Private (compute) subnets: `private` in awsdb4u and the SRA; else every subnet that isn't public or for endpoints."""
    subnets = _of_type(rs, "aws_subnet")
    private = [r for r in subnets if r["name"] == "private"]
    return [r["values"] for r in private or [r for r in subnets if r["name"] not in ("public", "privatelink", "intra")]]


def _network(rs) -> dict:
    out: dict = {}
    subnets = _compute_subnets(rs)
    if subnets:
        zones = {s.get("availability_zone") or s.get("availability_zone_id") for s in subnets} - {None, COMPUTED}
        if zones:
            out["subnet_az_count"] = len(zones)
        prefixes = [int(str(s.get("cidr_block")).split("/")[1]) for s in subnets if "/" in str(s.get("cidr_block", ""))]
        if prefixes:
            out["smallest_subnet_prefix_length"] = max(prefixes)
    vpc = bool(_of_type(rs, "aws_vpc"))
    s3 = [r for r in _of_type(rs, "aws_vpc_endpoint") if _is_s3_gateway(r)]
    if vpc or s3:
        out["s3_gateway_endpoint"] = bool(s3)
    if s3:
        # inline on the endpoint, or a separate aws_vpc_endpoint_policy
        policies = [r["values"].get("policy") for r in s3 + _of_type(rs, "aws_vpc_endpoint_policy")]
        out["s3_endpoint_policy_restricted"] = any(_restrictive(p) for p in policies)
    if vpc:
        nat = bool(_of_type(rs, "aws_nat_gateway"))
        out["nat_gateway"] = nat
        firewall = bool(_of_type(rs, "aws_networkfirewall_firewall"))
        out["egress_controlled"] = firewall or not (nat or _of_type(rs, "aws_internet_gateway"))
    return out


def _is_s3_gateway(r: dict) -> bool:
    v = r["values"]
    service = str(v.get("service_name") or "")
    named = service.endswith(".s3") or r["address"].endswith('["s3"]')
    return named and str(v.get("vpc_endpoint_type") or "Gateway") == "Gateway"


def _restrictive(policy) -> bool:
    """An endpoint policy that doesn't allow every action on every resource. Computed policies count as set."""
    if policy is COMPUTED or policy == COMPUTED:
        return True
    if not _is_set(policy):
        return False
    try:
        doc = json.loads(policy) if isinstance(policy, str) else policy
    except ValueError:
        return True
    statements = doc.get("Statement") or []
    statements = statements if isinstance(statements, list) else [statements]

    def anything(value) -> bool:
        return value == "*" or (isinstance(value, list) and "*" in value)

    return not any(s.get("Effect") == "Allow" and anything(s.get("Resource")) and
                   (anything(s.get("Action")) or s.get("Action") in ("s3:*", ["s3:*"])) for s in statements)


def _private_link(rs) -> dict:
    nets = [r["values"] for r in _of_type(rs, "databricks_mws_networks")]
    pas = bool(_of_type(rs, "databricks_mws_private_access_settings"))
    out: dict = {}
    if nets:
        vpce = _first(nets[0].get("vpc_endpoints"))
        relay = vpce.get("dataplane_relay") if isinstance(vpce, dict) else None
        rest = vpce.get("rest_api") if isinstance(vpce, dict) else None
        out["backend"] = _is_set(relay) or relay is COMPUTED
        out["frontend"] = pas and (_is_set(rest) or rest is COMPUTED)
    return out


def _access(rs) -> dict:
    out = common._access(rs)
    policies = _of_type(rs, "databricks_account_network_policy")
    if policies:
        bound = bool(_of_type(rs, "databricks_workspace_network_option"))
        out["public_ingress_ip_restricted"] = bound and any(_public_ip_restricted(r["values"]) for r in policies)
    return out


def _public_ip_restricted(policy: dict) -> bool:
    """Context-based ingress (enforced, not dry run) limits public access to listed IP ranges."""
    public = _first(_first(policy.get("ingress")).get("public_access"))
    if public.get("restriction_mode") != "RESTRICTED_ACCESS":
        return False
    rules = public.get("allow_rules") or []
    return bool(rules) and all(_is_set(_first(_first(r.get("origin")).get("included_ip_ranges")).get("ip_ranges"))
                               for r in rules)

