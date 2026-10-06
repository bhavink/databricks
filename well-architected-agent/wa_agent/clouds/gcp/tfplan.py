"""Collect GCP facts from `terraform show -json` output (plan or state).

Works for the gcpdb4u roots (infra4db, byovpc-*, lpw, workspace-guardrails)
and any Terraform using the same resources. A multi-root build gives one
plan per root: collect each and pass all of them to `assess` (facts merge).

Facts a plan can't establish (e.g. a VPC created in another root, a
perimeter managed by another team) are left out, so their checks report
UNKNOWN rather than FAIL.
"""

from __future__ import annotations

from ...facts import COMPUTED, EVIDENCE
from ..azure import tfplan as common
from ..azure.live import egress_restricted

resources = common.resources
_of_type = common._of_type
_first = common._first
_is_set = common._is_set

RESTRICTED_VIP = {"199.36.153.4", "199.36.153.5", "199.36.153.6", "199.36.153.7"}

PROVENANCE = {
    "workspace.": ("databricks_mws_workspaces",),
    "workspace.public_access_enabled": ("databricks_mws_private_access_settings",),
    "workspace.private_access_level": ("databricks_mws_private_access_settings",),
    "network.smallest_subnet_prefix_length": ("google_compute_subnetwork",),
    "network.private_google_access": ("google_compute_subnetwork",),
    "network.cloud_nat": ("google_compute_router_nat",),
    "network.egress_deny_default": ("google_compute_firewall",),
    "network.google_apis_endpoint": ("google_dns_managed_zone", "google_dns_record_set"),
    "network.service_perimeter": ("google_access_context_manager_service_perimeter",
                                  "google_access_context_manager_service_perimeters"),
    "private_link.": ("databricks_mws_networks", "databricks_mws_vpc_endpoint",
                      "databricks_mws_private_access_settings"),
    "dns.workspace_private_zone": ("google_dns_managed_zone",),
    "serverless.ncc_bound": ("databricks_mws_ncc_binding", "databricks_mws_workspaces"),
    "serverless.egress_restricted": ("databricks_account_network_policy", "databricks_workspace_network_option"),
    "access.": ("databricks_workspace_conf", "databricks_ip_access_list"),
    "access.context_ingress_enforced": ("databricks_account_network_policy", "databricks_workspace_network_option"),
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


def _workspaces(rs, workspace):
    candidates = _of_type(rs, "databricks_mws_workspaces")
    if workspace:
        chosen = [r for r in candidates if workspace in (r["address"], r["values"].get("workspace_name"))]
        if len(chosen) != 1:
            raise ValueError(f"no single workspace matching {workspace!r}; candidates: {[r['address'] for r in candidates]}")
        return chosen[0]
    if len(candidates) > 1:
        raise ValueError(f"plan contains more than one Databricks workspace; choose one with --workspace: "
                         f"{[r['address'] for r in candidates]}")
    return candidates[0] if candidates else None


def _collect(doc: dict, rs: list[dict], workspace: str | None) -> dict:
    facts: dict = {"cloud": "gcp", "source": "terraform-plan" if "resource_changes" in doc else "terraform-state"}
    ws = _workspaces(rs, workspace)
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
    zones = _of_type(rs, "google_dns_managed_zone")
    if zones:
        facts["dns"] = {"workspace_private_zone": any(
            str(z["values"].get("dns_name", "")).rstrip(".").endswith("gcp.databricks.com")
            and z["values"].get("visibility", "private") == "private" for z in zones)}
    facts["serverless"] = _serverless(rs, ws)
    facts["access"] = common._access(rs)
    if _of_type(rs, "databricks_metastore_assignment") or ws:
        facts["governance"] = {"metastore_assigned": bool(_of_type(rs, "databricks_metastore_assignment"))}
    if _of_type(rs, "databricks_mws_log_delivery"):
        facts["operations"] = {"audit_log_delivery": any(
            r["values"].get("log_type") == "AUDIT_LOGS" and r["values"].get("status", "ENABLED") == "ENABLED"
            for r in _of_type(rs, "databricks_mws_log_delivery"))}
    return {k: v for k, v in facts.items() if v not in ({}, None)}


def _network(rs) -> dict:
    out: dict = {}
    subnets = [r["values"] for r in _of_type(rs, "google_compute_subnetwork")
               if "psc" not in str(r["values"].get("name", "")).lower()]
    if subnets:
        prefixes = [int(str(s.get("ip_cidr_range")).split("/")[1]) for s in subnets
                    if "/" in str(s.get("ip_cidr_range", ""))]
        if prefixes:
            out["smallest_subnet_prefix_length"] = max(prefixes)
        out["private_google_access"] = all(s.get("private_ip_google_access") is True for s in subnets)
    if _of_type(rs, "google_compute_network") or subnets:
        out["cloud_nat"] = bool(_of_type(rs, "google_compute_router_nat"))
        out["egress_deny_default"] = any(_denies_all_egress(r["values"]) for r in _of_type(rs, "google_compute_firewall"))
    endpoint = _google_apis_endpoint(rs)
    if endpoint:
        out["google_apis_endpoint"] = endpoint
    if _of_type(rs, "google_access_context_manager_service_perimeter",
                "google_access_context_manager_service_perimeters"):
        out["service_perimeter"] = True
    return out


def _denies_all_egress(fw: dict) -> bool:
    return (str(fw.get("direction", "")).upper() == "EGRESS"
            and any(_first(d).get("protocol") == "all" or d.get("protocol") == "all" for d in fw.get("deny") or [])
            and "0.0.0.0/0" in (fw.get("destination_ranges") or []))


def _google_apis_endpoint(rs) -> str | None:
    """`restricted` or `private`, from the *.googleapis.com record (CNAME or A records)."""
    for r in _of_type(rs, "google_dns_record_set"):
        v = r["values"]
        if str(v.get("name", "")).rstrip(".") not in ("*.googleapis.com", "googleapis.com"):
            continue
        data = " ".join(str(x) for x in v.get("rrdatas") or [])
        if "restricted.googleapis.com" in data or RESTRICTED_VIP & set(v.get("rrdatas") or []):
            return "restricted"
        if "private.googleapis.com" in data or data:
            return "private"
    return None


def _private_link(rs) -> dict:
    nets = [r["values"] for r in _of_type(rs, "databricks_mws_networks")]
    endpoints = _of_type(rs, "databricks_mws_vpc_endpoint")
    out: dict = {}
    if nets:
        vpce = _first(nets[0].get("vpc_endpoints"))
        relay = vpce.get("dataplane_relay") if isinstance(vpce, dict) else None
        rest = vpce.get("rest_api") if isinstance(vpce, dict) else None
        out["backend_psc"] = _is_set(relay) or (relay is COMPUTED) or bool(endpoints and vpce)
        out["frontend_psc"] = bool(_of_type(rs, "databricks_mws_private_access_settings")) and (
            _is_set(rest) or rest is COMPUTED or len(endpoints) >= 2)
    elif endpoints:
        out["backend_psc"] = True
        out["frontend_psc"] = bool(_of_type(rs, "databricks_mws_private_access_settings")) and len(endpoints) >= 2
    return out


def _serverless(rs, ws) -> dict:
    out: dict = {}
    bound = bool(_of_type(rs, "databricks_mws_ncc_binding")) or (
        ws is not None and _is_set(ws["values"].get("network_connectivity_config_id")))
    if bound or ws is not None:
        out["ncc_bound"] = bound
    policies = _of_type(rs, "databricks_account_network_policy")
    if policies or _of_type(rs, "databricks_workspace_network_option") or ws is not None:
        restricted = any(egress_restricted({"egress": {"network_access": common._network_access(r["values"])}})
                         for r in policies)
        out["egress_restricted"] = restricted and bool(_of_type(rs, "databricks_workspace_network_option"))
    return out
