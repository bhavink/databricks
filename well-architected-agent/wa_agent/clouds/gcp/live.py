"""Collect GCP facts from a deployed workspace, read-only.

Sources: the Databricks Account API (workspace, network configuration,
private access settings, keys, NCC, network policy, audit log delivery) and
read-only gcloud commands (subnet, Cloud NAT, firewall rules, DNS, VPC
Service Controls), plus the same workspace-level reads as Azure (IP access
lists, workspace settings, metastore). Only commands in READ_ONLY_COMMANDS
can run. Anything the caller can't read is left out and reported UNKNOWN.
"""

from __future__ import annotations

from ...facts import EVIDENCE
from ..azure import live as common

READ_ONLY_COMMANDS = {
    ("databricks", "auth", "profiles"),
    ("databricks", "account", "workspaces", "list"),
    ("databricks", "account", "workspaces", "get"),
    ("databricks", "account", "networks", "get"),
    ("databricks", "account", "private-access", "get"),
    ("databricks", "account", "log-delivery", "list"),
    ("databricks", "account", "network-connectivity", "get-network-connectivity-configuration"),
    ("databricks", "account", "workspace-network-configuration", "get-workspace-network-option-rpc"),
    ("databricks", "account", "network-policies", "get-network-policy-rpc"),
    ("databricks", "workspace-conf", "get-status"),
    ("databricks", "ip-access-lists", "list"),
    ("databricks", "metastores", "current"),
    ("gcloud", "compute", "networks", "subnets", "describe"),
    ("gcloud", "compute", "routers", "list"),
    ("gcloud", "compute", "firewall-rules", "list"),
    ("gcloud", "dns", "managed-zones", "list"),
    ("gcloud", "dns", "record-sets", "list"),
    ("gcloud", "projects", "describe"),
    ("gcloud", "projects", "get-ancestors"),
    ("gcloud", "access-context-manager", "policies", "list"),
    ("gcloud", "access-context-manager", "perimeters", "list"),
}
ACCOUNT_HOST = "accounts.gcp.databricks.com"
RESTRICTED_VIP = {"199.36.153.4", "199.36.153.5", "199.36.153.6", "199.36.153.7"}


def assert_read_only(args: list[str]) -> None:
    common.assert_read_only(args, READ_ONLY_COMMANDS)


def workspace_url(ws: dict) -> str | None:
    name = ws.get("deployment_name")
    return f"https://{name}.gcp.databricks.com" if name else None


def resolve_workspace(ref: str, run, account_profile: str) -> dict:
    """The account's workspace matching a name, URL or numeric id."""
    listed = run(["databricks", "-o", "json", "--profile", account_profile, "account", "workspaces", "list"])
    items = listed if isinstance(listed, list) else (listed or {}).get("workspaces", []) if isinstance(listed, dict) else []
    key = ref.lower().rstrip("/").removeprefix("https://")
    for ws in items:
        names = {str(ws.get("workspace_name", "")).lower(), str(ws.get("workspace_id", "")),
                 str(ws.get("deployment_name", "")).lower(),
                 str(workspace_url(ws) or "").lower().removeprefix("https://")}
        if key in names:
            return ws
    raise RuntimeError(f"no workspace matching {ref!r} in this account (name, URL or numeric id)")


def collect(workspace: str, run=common.cli_runner, databricks_profile: str | None = None,
            account_profile: str | None = None, auto_profiles: bool = True) -> dict:
    run = common.guarded(run, READ_ONLY_COMMANDS)
    if auto_profiles and account_profile is None:
        _, account_profile = common.match_profiles(None, run, ACCOUNT_HOST)
    if not account_profile:
        raise RuntimeError("GCP scans start from the Databricks account: pass --account-profile "
                           f"(a valid CLI profile for https://{ACCOUNT_HOST})")
    ws = resolve_workspace(workspace, run, account_profile)
    url = workspace_url(ws)
    if auto_profiles and databricks_profile is None:
        databricks_profile, _ = common.match_profiles(url, run, ACCOUNT_HOST)
    acct = ["databricks", "-o", "json", "--profile", account_profile, "account"]
    facts: dict = {"cloud": "gcp", "source": "gcp-live",
                   "_scan": {"workspace": workspace, "workspace_url": url, "profile": databricks_profile,
                             "account_profile": account_profile}}

    info = {
        "name": ws.get("workspace_name"),
        "compute_mode": "serverless" if ws.get("compute_mode") == "SERVERLESS" else "classic",
        "customer_managed_vpc": bool(ws.get("network_id")),
        "cmk_managed_services": bool(ws.get("managed_services_customer_managed_key_id")),
        "cmk_storage": bool(ws.get("storage_customer_managed_key_id")),
        "public_access_enabled": True,
    }
    pas = None
    if ws.get("private_access_settings_id"):
        pas = run(acct + ["private-access", "get", ws["private_access_settings_id"]])
        if isinstance(pas, dict):
            info["public_access_enabled"] = bool(pas.get("public_access_enabled", True))
            info["private_access_level"] = pas.get("private_access_level", "ACCOUNT")
        else:
            info.pop("public_access_enabled")
    facts["workspace"] = info

    net = run(acct + ["networks", "get", ws["network_id"]]) if ws.get("network_id") else None
    if isinstance(net, dict):
        vpce = net.get("vpc_endpoints") or {}
        facts["private_link"] = {"backend_psc": bool(vpce.get("dataplane_relay")),
                                 "frontend_psc": bool(ws.get("private_access_settings_id")) and bool(vpce.get("rest_api"))}
        gni = net.get("gcp_network_info") or {}
        project = gni.get("network_project_id")
        if project:
            facts["network"], facts["dns"] = _network(run, gni)
            compute_project = ((ws.get("cloud_resource_container") or {}).get("gcp") or {}).get("project_id") or project
            perimeter = _perimeter(run, sorted({project, compute_project}))
            if perimeter is not None:
                facts["network"]["service_perimeter"] = perimeter

    deliveries = run(acct + ["log-delivery", "list"])
    if deliveries is not None:
        items = deliveries if isinstance(deliveries, list) else (deliveries or {}).get("log_configurations", [])
        wid = ws.get("workspace_id")
        facts["operations"] = {"audit_log_delivery": any(
            d.get("log_type") == "AUDIT_LOGS" and d.get("status", "ENABLED") == "ENABLED"
            and (not d.get("workspace_ids_filter") or wid in d.get("workspace_ids_filter"))
            for d in items)}

    workspace_side = common._databricks(run, {"workspaceUrl": (url or "").removeprefix("https://"),
                                              "workspaceId": ws.get("workspace_id")},
                                        databricks_profile, account_profile)
    facts.update(workspace_side)
    facts = {k: v for k, v in facts.items() if v not in ({}, None)}
    facts[EVIDENCE] = _provenance(facts, ws)
    return facts


def _network(run, gni: dict) -> tuple[dict, dict]:
    project, vpc, subnet, region = (gni.get(k) for k in ("network_project_id", "vpc_id", "subnet_id", "subnet_region"))
    out: dict = {}
    dns: dict = {}
    sub = run(["gcloud", "compute", "networks", "subnets", "describe", subnet, "--region", region,
               "--project", project, "--format", "json"]) if subnet and region else None
    if isinstance(sub, dict):
        cidr = sub.get("ipCidrRange") or ""
        if "/" in cidr:
            out["smallest_subnet_prefix_length"] = int(cidr.split("/")[1])
        out["private_google_access"] = bool(sub.get("privateIpGoogleAccess"))
    network_filter = f"network~/networks/{vpc}$"
    routers = run(["gcloud", "compute", "routers", "list", "--project", project, "--filter", network_filter,
                   "--format", "json"])
    if isinstance(routers, list):
        out["cloud_nat"] = any(r.get("nats") for r in routers)
    rules = run(["gcloud", "compute", "firewall-rules", "list", "--project", project, "--filter", network_filter,
                 "--format", "json"])
    if isinstance(rules, list):
        out["egress_deny_default"] = any(
            r.get("direction") == "EGRESS" and not r.get("disabled")
            and any(d.get("IPProtocol") == "all" for d in r.get("denied") or [])
            and "0.0.0.0/0" in (r.get("destinationRanges") or []) for r in rules)
    zones = run(["gcloud", "dns", "managed-zones", "list", "--project", project, "--format", "json"])
    if isinstance(zones, list):
        private = [z for z in zones if z.get("visibility") == "private"
                   and any(str(n.get("networkUrl", "")).endswith(f"/networks/{vpc}")
                           for n in ((z.get("privateVisibilityConfig") or {}).get("networks") or []))]
        dns["workspace_private_zone"] = any(str(z.get("dnsName", "")).rstrip(".").endswith("gcp.databricks.com")
                                            for z in private)
        for z in private:
            if str(z.get("dnsName", "")).rstrip(".") != "googleapis.com":
                continue
            records = run(["gcloud", "dns", "record-sets", "list", "--zone", z["name"], "--project", project,
                           "--format", "json"]) or []
            for rec in records if isinstance(records, list) else []:
                if str(rec.get("name", "")).rstrip(".") in ("*.googleapis.com", "googleapis.com"):
                    data = rec.get("rrdatas") or []
                    out["google_apis_endpoint"] = ("restricted" if any("restricted.googleapis.com" in d for d in data)
                                                   or RESTRICTED_VIP & set(data) else "private")
    return out, dns


def _perimeter(run, projects: list[str]) -> bool | None:
    """True if any workspace project is in an enforced VPC-SC perimeter; None if it can't be read."""
    numbers = []
    org = None
    for p in projects:
        desc = run(["gcloud", "projects", "describe", p, "--format", "json"])
        if isinstance(desc, dict) and desc.get("projectNumber"):
            numbers.append(f"projects/{desc['projectNumber']}")
        anc = run(["gcloud", "projects", "get-ancestors", p, "--format", "json"])
        if isinstance(anc, list):
            org = org or next((a["id"] for a in anc if a.get("type") == "organization"), None)
    if not org or not numbers:
        return None
    policies = run(["gcloud", "access-context-manager", "policies", "list", "--organization", org, "--format", "json"])
    if not isinstance(policies, list):
        return None
    for policy in policies:
        pid = str(policy.get("name", "")).split("/")[-1]
        perimeters = run(["gcloud", "access-context-manager", "perimeters", "list", "--policy", pid, "--format", "json"])
        for per in perimeters if isinstance(perimeters, list) else []:
            if set(numbers) & set((per.get("status") or {}).get("resources") or []):
                return True
    return False


def _provenance(facts: dict, ws: dict) -> dict:
    wid = ws.get("workspace_id")
    acct_ws = f"databricks account workspaces get {wid}"
    table = {
        "workspace.": f"{acct_ws} (network_id, private_access_settings_id, *_customer_managed_key_id)",
        "workspace.public_access_enabled": "databricks account private-access get -> public_access_enabled",
        "workspace.private_access_level": "databricks account private-access get -> private_access_level",
        "private_link.": "databricks account networks get -> vpc_endpoints (dataplane_relay, rest_api)",
        "network.smallest_subnet_prefix_length": "gcloud compute networks subnets describe -> ipCidrRange",
        "network.private_google_access": "gcloud compute networks subnets describe -> privateIpGoogleAccess",
        "network.cloud_nat": "gcloud compute routers list -> nats",
        "network.egress_deny_default": "gcloud compute firewall-rules list -> EGRESS deny all 0.0.0.0/0",
        "network.google_apis_endpoint": "gcloud dns record-sets list (private googleapis.com zone) -> *.googleapis.com",
        "network.service_perimeter": "gcloud access-context-manager perimeters list -> status.resources",
        "dns.workspace_private_zone": "gcloud dns managed-zones list -> private gcp.databricks.com zone",
        "operations.audit_log_delivery": "databricks account log-delivery list -> AUDIT_LOGS, ENABLED",
        "serverless.": "databricks account workspaces get / network-policies get-network-policy-rpc",
        "access.": "databricks workspace-conf get-status / ip-access-lists list",
        "access.context_ingress_enforced": "databricks account network-policies get-network-policy-rpc -> ingress",
        "governance.": "databricks metastores current",
    }
    out = {}
    for ns, values in facts.items():
        if isinstance(values, dict) and not ns.startswith("_"):
            for key in values:
                path = f"{ns}.{key}"
                src = table.get(path) or table.get(f"{ns}.")
                if src:
                    out[path] = [src]
    return out
