"""Collect Azure facts from a deployed workspace (read-only).

Uses the `az` CLI (ARM) and, optionally, the `databricks` CLI (workspace
and account APIs). Every command is a read; nothing is modified. Any call
that fails leaves the related facts unset, so the engine reports UNKNOWN
with the missing fact instead of a false PASS/FAIL.

Auth: whatever `az login` / Databricks CLI profiles are already configured.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from typing import Callable

from ...facts import EVIDENCE
from ...redact import redact

Runner = Callable[[list[str]], object]

DATABRICKS_DELEGATION = "Microsoft.Databricks/workspaces"
DBX_ZONE = "privatelink.azuredatabricks.net"
STORAGE_SERVICE_ENDPOINTS = ("Microsoft.Storage", "Microsoft.Storage.Global")


# Rule 1: the agent never changes anything. Every command must match one of
# these read-only verbs exactly; anything else is refused before it runs.
READ_ONLY_COMMANDS = {
    ("az", "databricks", "workspace", "show"),
    ("az", "databricks", "workspace", "list"),
    ("az", "account", "list"),
    ("az", "extension", "list"),
    ("databricks", "auth", "profiles"),
    ("az", "network", "vnet", "subnet", "show"),
    ("az", "network", "route-table", "show"),
    ("az", "network", "vnet", "peering", "list"),
    ("az", "network", "private-endpoint", "show"),
    ("az", "network", "private-dns", "zone", "list"),
    ("az", "network", "private-dns", "link", "vnet", "list"),
    ("az", "storage", "account", "show"),
    ("az", "monitor", "diagnostic-settings", "list"),
    ("az", "resource", "list"),
    ("az", "resource", "show"),
    ("databricks", "workspace-conf", "get-status"),
    ("databricks", "ip-access-lists", "list"),
    ("databricks", "metastores", "current"),
    ("databricks", "account", "workspaces", "get"),
    ("databricks", "account", "network-connectivity", "get-network-connectivity-configuration"),
    ("databricks", "account", "workspace-network-configuration", "get-workspace-network-option-rpc"),
    ("databricks", "account", "network-policies", "get-network-policy-rpc"),
}
_DATABRICKS_GLOBAL_FLAGS = {"-o": 1, "--output": 1, "--profile": 1, "-p": 1, "--host": 1}


class ReadOnlyViolation(RuntimeError):
    pass


def command_verb(args: list[str], allowed: set | None = None) -> tuple[str, ...]:
    """The command path without flags and positional values."""
    if args[:1] == ["databricks"]:
        rest, i = [], 1
        while i < len(args):
            if args[i] in _DATABRICKS_GLOBAL_FLAGS:
                i += 1 + _DATABRICKS_GLOBAL_FLAGS[args[i]]
                continue
            rest.append(args[i])
            i += 1
        candidates = [("databricks", *rest[:n]) for n in range(1, len(rest) + 1)]
    else:
        flagless = []
        for a in args:
            if a.startswith("-"):
                break
            flagless.append(a)
        candidates = [tuple(flagless[:n]) for n in range(1, len(flagless) + 1)]
    allowed = READ_ONLY_COMMANDS if allowed is None else allowed
    return next((c for c in reversed(candidates) if c in allowed), tuple(args[:4]))


def assert_read_only(args: list[str], allowed: set | None = None) -> None:
    allowed = READ_ONLY_COMMANDS if allowed is None else allowed
    if command_verb(args, allowed) not in allowed:
        raise ReadOnlyViolation(f"refusing to run non-allowlisted command: {' '.join(args[:5])}")


def guarded(run: Runner, allowed: set | None = None) -> Runner:
    def _run(args: list[str]):
        assert_read_only(args, allowed)
        return run(args)
    return _run


# Workspace settings that let users move data out through the UI.
DATA_LEAK_SETTINGS = {
    "notebook_export_enabled": "enableExportNotebook",
    "results_download_enabled": "enableResultsDownloading",
    "table_clipboard_enabled": "enableNotebookTableClipboard",
}


# Returned by the runner when the workspace front-end rejects the caller's
# IP. That rejection is itself evidence that IP access lists are enforced.
IP_ACL_BLOCKED = {"_error": "ip_acl_blocked"}


def _blocked(response) -> bool:
    return response == IP_ACL_BLOCKED


def cli_runner(args: list[str]):
    """Run a CLI command and parse JSON output; None on any failure."""
    exe = shutil.which(args[0])  # Windows: az is az.cmd, which a shell-less launch cannot find by bare name
    if exe is None:
        print(f"warning: {args[0]} not found on PATH", file=sys.stderr)
        return None
    try:
        proc = subprocess.run([exe, *args[1:]], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        if "blocked by Databricks IP ACL" in proc.stderr:
            return IP_ACL_BLOCKED
        message = re.sub(r"\s*\[ReqId:[^\]]*\]", "", (proc.stderr.strip().splitlines() or ["failed"])[0])
        print(redact(f"warning: {' '.join(args[:4])}: {message}"), file=sys.stderr)
        return None
    if not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _param(ws: dict, name: str):
    return ((ws.get("parameters") or {}).get(name) or {}).get("value")


def resolve_workspace(ref: str, run: Runner) -> str:
    """ARM resource id for a workspace given as ARM id, name, URL or numeric id.
    Searches the current subscription first, then every enabled subscription."""
    if ref.lower().startswith("/subscriptions/"):
        return ref
    needle = ref.lower().removeprefix("https://").rstrip("/")

    def matches(ws: dict) -> bool:
        return needle in {str(ws.get("name", "")).lower(), str(ws.get("workspaceUrl", "")).lower(),
                          str(ws.get("workspaceId", ""))}

    found = [w for w in run(["az", "databricks", "workspace", "list", "-o", "json"]) or [] if matches(w)]
    if not found:
        subs = run(["az", "account", "list", "--query", "[?state=='Enabled'].id", "-o", "json"]) or []
        for sub in subs:
            found += [w for w in run(["az", "databricks", "workspace", "list", "--subscription", sub, "-o", "json"]) or []
                      if matches(w)]
            if found:
                break
    ids = sorted({w["id"] for w in found})
    if not ids:
        raise RuntimeError(f"no workspace matching {ref!r} in your subscriptions (check `az login` / `az account list`)")
    if len(ids) > 1:
        raise RuntimeError(f"{ref!r} matches several workspaces; pass the ARM id: {', '.join(ids)}")
    return ids[0]


def match_profiles(workspace_url: str | None, run: Runner,
                   account_host: str = "accounts.azuredatabricks.net") -> tuple[str | None, str | None]:
    """Valid Databricks CLI profiles for this workspace and (if unambiguous) its account."""
    data = run(["databricks", "auth", "profiles", "-o", "json"]) or {}
    profiles = [p for p in (data.get("profiles", []) if isinstance(data, dict) else []) if p.get("valid")]
    host = (workspace_url or "").lower()
    workspace = next((p["name"] for p in sorted(profiles, key=lambda p: p["name"])
                      if host and host in str(p.get("host", "")).lower()), None)
    accounts = sorted(p["name"] for p in profiles if account_host in str(p.get("host", "")))
    return workspace, (accounts[0] if len(accounts) == 1 else None)


def collect(
    workspace_resource_id: str,
    run: Runner = cli_runner,
    databricks_profile: str | None = None,
    account_profile: str | None = None,
    auto_profiles: bool = True,
) -> dict:
    run = guarded(run)
    ref = workspace_resource_id
    workspace_resource_id = resolve_workspace(ref, run)
    facts: dict = {"cloud": "azure", "source": "azure-live"}
    ws = run(["az", "databricks", "workspace", "show", "--ids", workspace_resource_id, "-o", "json"])
    if not isinstance(ws, dict):
        raise RuntimeError(f"could not read workspace {workspace_resource_id} (check `az login` and the resource id)")

    scan = {"workspace": ref, "resolved_to": workspace_resource_id,
            "profile": databricks_profile, "account_profile": account_profile}
    if auto_profiles and (databricks_profile is None or account_profile is None):
        auto_ws, auto_acct = match_profiles(ws.get("workspaceUrl"), run)
        if databricks_profile is None and auto_ws:
            databricks_profile = scan["profile"] = auto_ws
            scan["profile_auto_matched"] = True
        if account_profile is None and auto_acct:
            account_profile = scan["account_profile"] = auto_acct
            scan["account_profile_auto_matched"] = True
    scan["workspace_url"] = ws.get("workspaceUrl")
    facts["_scan"] = scan

    vnet_id = _param(ws, "customVirtualNetworkId")
    encryption = ((ws.get("encryption") or {}).get("entities")) or {}
    dbfs_encryption = _param(ws, "encryption") or {}
    facts["workspace"] = {
        "name": ws.get("name"),
        "sku": (ws.get("sku") or {}).get("name"),
        # ARM computeMode: "Hybrid" (classic + serverless) or "Serverless".
        "compute_mode": "serverless" if ws.get("computeMode") == "Serverless" else "classic",
        "vnet_injected": bool(vnet_id),
        "no_public_ip": _param(ws, "enableNoPublicIp"),
        "public_network_access_enabled": (ws.get("publicNetworkAccess") or "Enabled") == "Enabled",
        "required_nsg_rules": ws.get("requiredNsgRules"),
        "cmk_managed_services": bool(encryption.get("managedServices")),
        "cmk_managed_disks": bool(encryption.get("managedDisk")),
        "cmk_dbfs_root": dbfs_encryption.get("keySource") == "Microsoft.Keyvault",
    }

    if vnet_id:
        facts["network"] = _network(run, vnet_id, [_param(ws, "customPublicSubnetName"), _param(ws, "customPrivateSubnetName")])

    groups = {
        g
        for conn in ws.get("privateEndpointConnections") or []
        if ((conn.get("properties") or {}).get("privateLinkServiceConnectionState") or {}).get("status") == "Approved"
        for g in (conn.get("properties") or {}).get("groupIds") or []
    }
    facts["private_link"] = {
        "ui_api": "databricks_ui_api" in groups,
        "browser_authentication": "browser_authentication" in groups,
    }
    dbfs = _dbfs_storage(run, ws)
    if dbfs is not None:
        facts["private_link"].update(_dbfs_private_endpoints(run, dbfs))
        # Read the DBFS account itself rather than the workspace's
        # defaultStorageFirewall flag, which older API versions omit.
        facts["workspace"]["default_storage_firewall_enabled"] = (
            dbfs.get("publicNetworkAccess") == "Disabled"
            or ((dbfs.get("networkRuleSet") or dbfs.get("networkAcls") or {}).get("defaultAction")) == "Deny"
        )

    if vnet_id:
        facts["dns"] = _dns(run, vnet_id)

    diag = run(["az", "monitor", "diagnostic-settings", "list", "--resource", workspace_resource_id, "-o", "json"])
    if diag is not None:
        entries = diag.get("value", diag) if isinstance(diag, dict) else diag
        facts["operations"] = {"diagnostic_settings": bool(entries)}

    facts.update(_databricks(run, ws, databricks_profile, account_profile))
    facts[EVIDENCE] = _provenance(facts, workspace_resource_id, ws)
    return facts


def _provenance(facts: dict, ws_id: str, ws: dict) -> dict:
    """Fact path -> the read command and response field it came from."""
    vnet = _param(ws, "customVirtualNetworkId") or "<vnet>"
    subnets = " , ".join(f"{vnet}/subnets/{n}" for n in (_param(ws, "customPublicSubnetName"),
                                                       _param(ws, "customPrivateSubnetName")) if n)
    dbfs = _param(ws, "storageAccountName") or "<dbfs>"
    host = ws.get("workspaceUrl") or "<workspace>"
    policy = (facts.get("serverless") or {}).get("network_policy_id") or "<policy>"
    ws_show = f"az databricks workspace show --ids {ws_id}"
    subnet_show = f"az network vnet subnet show --ids {subnets}"
    acct_ws = f"databricks account workspaces get {ws.get('workspaceId')}"
    blocked = (facts.get("access") or {}).keys() == {"ip_access_lists_enabled"}
    table = {
        "workspace.compute_mode": f"{ws_show} -> computeMode",
        "workspace.sku": f"{ws_show} -> sku.name",
        "workspace.vnet_injected": f"{ws_show} -> parameters.customVirtualNetworkId",
        "workspace.no_public_ip": f"{ws_show} -> parameters.enableNoPublicIp",
        "workspace.public_network_access_enabled": f"{ws_show} -> publicNetworkAccess",
        "workspace.required_nsg_rules": f"{ws_show} -> requiredNsgRules",
        "workspace.cmk_managed_services": f"{ws_show} -> encryption.entities.managedServices",
        "workspace.cmk_managed_disks": f"{ws_show} -> encryption.entities.managedDisk",
        "workspace.cmk_dbfs_root": f"{ws_show} -> parameters.encryption.keySource",
        "workspace.default_storage_firewall_enabled":
            f"az storage account show -n {dbfs} -> publicNetworkAccess, networkRuleSet.defaultAction",
        "network.delegated_subnet_count": f"{subnet_show} -> delegations[].serviceName",
        "network.smallest_subnet_prefix_length": f"{subnet_show} -> addressPrefix",
        "access.notebook_export_enabled": f"databricks workspace-conf get-status enableExportNotebook (https://{host})",
        "access.results_download_enabled": f"databricks workspace-conf get-status enableResultsDownloading (https://{host})",
        "access.table_clipboard_enabled":
            f"databricks workspace-conf get-status enableNotebookTableClipboard (https://{host})",
        "network.all_subnets_have_nsg": f"{subnet_show} -> networkSecurityGroup",
        "network.nat_gateway_attached": f"{subnet_show} -> natGateway",
        "network.default_route_to_appliance": f"{subnet_show} -> routeTable; az network route-table show -> routes[]",
        "network.storage_service_endpoint": f"{subnet_show} -> serviceEndpoints[].service",
        "network.service_endpoint_policy": f"{subnet_show} -> serviceEndpointPolicies",
        "network.hub_peering": f"az network vnet peering list --vnet-name {vnet.split('/')[-1]} -> peeringState == Connected",
        "network.firewall_present": "az resource list --resource-type Microsoft.Network/azureFirewalls (spoke and peered "
                                    "hub resource groups) -> ipConfigurations[].privateIPAddress == route next hop",
        "network.firewall_id": "Azure Firewall matched by the 0.0.0.0/0 next-hop IP",
        "network.firewall_application_rules":
            f"az resource show --ids {(facts.get('network') or {}).get('firewall_id', '<firewall>')} -> "
            "applicationRuleCollections, or firewallPolicy -> ruleCollectionGroups[].ruleCollections[].rules[].ruleType",
        "network.firewall_logs": f"az monitor diagnostic-settings list --resource "
                                 f"{(facts.get('network') or {}).get('firewall_id', '<firewall>')}",
        "private_link.ui_api": f"{ws_show} -> privateEndpointConnections[] (Approved, groupIds)",
        "private_link.browser_authentication": f"{ws_show} -> privateEndpointConnections[] (Approved, groupIds)",
        "private_link.dbfs_dfs": f"az storage account show -n {dbfs} -> privateEndpointConnections[]",
        "private_link.dbfs_blob": f"az storage account show -n {dbfs} -> privateEndpointConnections[]",
        "dns.azuredatabricks_zone": f"az network private-dns zone list -> name == {DBX_ZONE}",
        "dns.azuredatabricks_zone_linked": f"az network private-dns link vnet list -z {DBX_ZONE} -> virtualNetwork.id == {vnet}",
        "operations.diagnostic_settings": f"az monitor diagnostic-settings list --resource {ws_id}",
        "access.ip_access_lists_enabled":
            f"https://{host}: API rejected this source IP with 'blocked by Databricks IP ACL'" if blocked
            else f"databricks workspace-conf get-status enableIpAccessLists (https://{host})",
        "access.ip_access_list_count": f"databricks ip-access-lists list (https://{host}) -> ALLOW, enabled",
        "governance.metastore_assigned": f"databricks metastores current (https://{host}) -> metastore_id",
        "governance.access_connector": f"{ws_show} -> accessConnector; az resource list --resource-type "
                                       "Microsoft.Databricks/accessConnectors",
        "serverless.ncc_bound": f"{acct_ws} -> network_connectivity_config_id",
        "serverless.ncc_private_endpoint_rules":
            "databricks account network-connectivity get-network-connectivity-configuration "
            "-> azure_private_endpoint_rules[] (ESTABLISHED)",
        "serverless.network_policy_id":
            f"databricks account workspace-network-configuration get-workspace-network-option-rpc {ws.get('workspaceId')}",
        "serverless.egress_restricted": f"databricks account network-policies get-network-policy-rpc {policy} "
                                        "-> egress.network_access (restriction_mode, enforcement_mode)",
    }
    return {
        f"{ns}.{key}": [table[f"{ns}.{key}"]]
        for ns, values in facts.items() if isinstance(values, dict)
        for key in values if f"{ns}.{key}" in table
    }


def _network(run: Runner, vnet_id: str, subnet_names: list[str]) -> dict:
    subnets = [run(["az", "network", "vnet", "subnet", "show", "--ids", f"{vnet_id}/subnets/{n}", "-o", "json"])
               for n in subnet_names if n]
    if not subnets or any(not isinstance(s, dict) for s in subnets):
        return {}

    next_hops: set[str] = set()

    def has_default_route_to_appliance(subnet: dict) -> bool:
        rt_id = (subnet.get("routeTable") or {}).get("id")
        if not rt_id:
            return False
        rt = run(["az", "network", "route-table", "show", "--ids", rt_id, "-o", "json"]) or {}
        hops = [r for r in rt.get("routes") or []
                if r.get("addressPrefix") == "0.0.0.0/0" and r.get("nextHopType") == "VirtualAppliance"]
        next_hops.update(r["nextHopIpAddress"] for r in hops if r.get("nextHopIpAddress"))
        return bool(hops)

    prefixes = [int(s["addressPrefix"].split("/")[1]) for s in subnets if "/" in (s.get("addressPrefix") or "")]
    to_appliance = all(has_default_route_to_appliance(s) for s in subnets)
    return _hub_firewall(run, vnet_id, next_hops if to_appliance else set()) | {
        "smallest_subnet_prefix_length": max(prefixes) if prefixes else None,
        "delegated_subnet_count": sum(
            1 for s in subnets if any(d.get("serviceName") == DATABRICKS_DELEGATION for d in s.get("delegations") or [])
        ),
        "all_subnets_have_nsg": all(s.get("networkSecurityGroup") for s in subnets),
        "nat_gateway_attached": all(s.get("natGateway") for s in subnets),
        "default_route_to_appliance": to_appliance,
        "storage_service_endpoint": all(
            any(e.get("service") in STORAGE_SERVICE_ENDPOINTS for e in s.get("serviceEndpoints") or []) for s in subnets
        ),
        "service_endpoint_policy": all(s.get("serviceEndpointPolicies") for s in subnets),
    }


def _arm_parts(resource_id: str) -> tuple[str, str, str] | None:
    """(subscription, resource group, name) of an ARM id, or None."""
    parts = resource_id.split("/")
    return (parts[2], parts[4], parts[-1]) if len(parts) >= 9 and parts[1].lower() == "subscriptions" else None


def _hub_firewall(run: Runner, vnet_id: str, next_hops: set[str]) -> dict:
    """Hub-spoke facts: peering, and the Azure Firewall the default route points at.

    Follows spoke VNet -> peerings -> hub resource groups -> the Azure Firewall
    whose private IP is the route's next hop. Facts the scan can't establish
    (no read access, or an NVA instead of Azure Firewall) are left out, so
    their checks report UNKNOWN rather than FAIL.
    """
    out: dict = {}
    spoke = _arm_parts(vnet_id)
    if not spoke:
        return out
    sub, rg, name = spoke
    peerings = run(["az", "network", "vnet", "peering", "list", "-g", rg, "--vnet-name", name,
                    "--subscription", sub, "-o", "json"])
    connected = []
    if isinstance(peerings, list):
        connected = [x for x in peerings if x.get("peeringState") == "Connected"]
        out["hub_peering"] = bool(connected)
    if not next_hops:
        return out

    scopes = {(sub, rg)}
    for x in connected:
        remote = _arm_parts((x.get("remoteVirtualNetwork") or {}).get("id") or "")
        if remote:
            scopes.add(remote[:2])
    for s_id, group in sorted(scopes):
        listed = run(["az", "resource", "list", "-g", group, "--subscription", s_id,
                      "--resource-type", "Microsoft.Network/azureFirewalls", "-o", "json"])
        for ref in listed if isinstance(listed, list) else []:
            fw = run(["az", "resource", "show", "--ids", ref["id"], "-o", "json"]) or {}
            props = fw.get("properties") or {}
            ips = {(c.get("properties") or {}).get("privateIPAddress") for c in props.get("ipConfigurations") or []}
            if not ips & next_hops:
                continue
            out["firewall_present"] = True
            out["firewall_id"] = ref["id"]
            app_rules = bool(props.get("applicationRuleCollections"))
            policy_id = (props.get("firewallPolicy") or {}).get("id")
            if policy_id and not app_rules:
                policy = run(["az", "resource", "show", "--ids", policy_id, "-o", "json"]) or {}
                for group_ref in (policy.get("properties") or {}).get("ruleCollectionGroups") or []:
                    rcg = run(["az", "resource", "show", "--ids", group_ref["id"], "-o", "json"]) or {}
                    app_rules = app_rules or any(
                        rule.get("ruleType") == "ApplicationRule"
                        for coll in (rcg.get("properties") or {}).get("ruleCollections") or []
                        for rule in coll.get("rules") or [])
            out["firewall_application_rules"] = app_rules
            diag = run(["az", "monitor", "diagnostic-settings", "list", "--resource", ref["id"], "-o", "json"])
            if diag is not None:
                entries = diag.get("value", diag) if isinstance(diag, dict) else diag
                out["firewall_logs"] = bool(entries)
            return out
    return out


def _dbfs_storage(run: Runner, ws: dict) -> dict | None:
    managed_rg = (ws.get("managedResourceGroupId") or "").rsplit("/", 1)[-1]
    account = _param(ws, "storageAccountName")
    if not managed_rg or not account:
        return None
    sa = run(["az", "storage", "account", "show", "-g", managed_rg, "-n", account, "-o", "json"])
    return sa if isinstance(sa, dict) else None


def _dbfs_private_endpoints(run: Runner, sa: dict) -> dict:
    groups = {
        g
        for conn in sa.get("privateEndpointConnections") or []
        if ((conn.get("privateLinkServiceConnectionState") or {}).get("status")) == "Approved"
        for g in conn.get("groupIds") or _group_ids_from_endpoint(run, conn)
    }
    return {"dbfs_dfs": "dfs" in groups, "dbfs_blob": "blob" in groups}


def _group_ids_from_endpoint(run: Runner, conn: dict) -> list[str]:
    pe_id = (conn.get("privateEndpoint") or {}).get("id")
    if not pe_id:
        return []
    pe = run(["az", "network", "private-endpoint", "show", "--ids", pe_id, "-o", "json"]) or {}
    return [g for c in pe.get("privateLinkServiceConnections") or [] for g in c.get("groupIds") or []]


def _dns(run: Runner, vnet_id: str) -> dict:
    zones = run(["az", "network", "private-dns", "zone", "list", "-o", "json"])
    if not isinstance(zones, list):
        return {}
    # A subscription can hold many such zones; check the VNet's own resource
    # group first and stop at the first zone linked to the VNet.
    vnet_rg = vnet_id.split("/resourceGroups/")[-1].split("/")[0].lower()
    matches = sorted(
        (z for z in zones if z.get("name") == DBX_ZONE),
        key=lambda z: (z["resourceGroup"].lower() != vnet_rg, z["resourceGroup"].lower()),
    )
    linked = False
    for zone in matches:
        links = run(["az", "network", "private-dns", "link", "vnet", "list", "-g", zone["resourceGroup"],
                     "-z", DBX_ZONE, "-o", "json"]) or []
        if any(((link.get("virtualNetwork") or {}).get("id") or "").lower() == vnet_id.lower() for link in links):
            linked = True
            break
    return {"azuredatabricks_zone": bool(matches), "azuredatabricks_zone_linked": linked}


def _databricks(run: Runner, ws: dict, profile: str | None, account_profile: str | None) -> dict:
    out: dict = {}
    if not profile:
        # No login for this workspace: leave workspace-level facts unknown (the report says how to
        # log in). Never fall back to the CLI's default profile, which may be another workspace.
        return out | _account(run, ws, account_profile)
    base = ["databricks", "-o", "json", "--profile", profile]

    governance: dict = {}
    conf = run(base + ["workspace-conf", "get-status", "enableIpAccessLists"])
    if _blocked(conf):
        print("warning: workspace API rejected this source IP; IP access lists are enforced, "
              "run from an allowed network to read them", file=sys.stderr)
        out["access"] = {"ip_access_lists_enabled": True}
    else:
        lists = run(base + ["ip-access-lists", "list"])
        if conf is not None and lists is not None and not _blocked(lists):
            entries = lists.get("ip_access_lists", lists) if isinstance(lists, dict) else lists
            out["access"] = {
                "ip_access_lists_enabled": str(conf.get("enableIpAccessLists")).lower() == "true",
                "ip_access_list_count": sum(
                    1 for e in entries or [] if e.get("list_type") == "ALLOW" and e.get("enabled")
                ),
            }
        leak = run(base + ["workspace-conf", "get-status", ",".join(DATA_LEAK_SETTINGS.values())])
        if isinstance(leak, dict) and not _blocked(leak):
            # Unset ("") means the Databricks default, which is enabled.
            out.setdefault("access", {}).update(
                {fact: str(leak.get(key, "")).lower() != "false" for fact, key in DATA_LEAK_SETTINGS.items()}
            )
        metastore = run(base + ["metastores", "current"])
        if isinstance(metastore, dict) and not _blocked(metastore):
            governance["metastore_assigned"] = bool(metastore.get("metastore_id"))

    resource_group = (ws.get("id") or "").split("/resourceGroups/")[-1].split("/")[0]
    connectors = run(["az", "resource", "list", "-g", resource_group,
                      "--resource-type", "Microsoft.Databricks/accessConnectors", "-o", "json"]) if resource_group else None
    if ws.get("accessConnector") or connectors:
        governance["access_connector"] = True
    elif connectors == []:
        governance["access_connector"] = False
    if governance:
        out["governance"] = governance

    return out | _account(run, ws, account_profile)


def _account(run: Runner, ws: dict, account_profile: str | None) -> dict:
    out: dict = {}
    workspace_id = ws.get("workspaceId")
    if account_profile and workspace_id:
        acct = run(["databricks", "-o", "json", "--profile", account_profile, "account", "workspaces", "get", str(workspace_id)])
        if isinstance(acct, dict):
            ncc_id = acct.get("network_connectivity_config_id")
            out["serverless"] = {"ncc_bound": bool(ncc_id)}
            if ncc_id:
                ncc = run(["databricks", "-o", "json", "--profile", account_profile, "account",
                           "network-connectivity", "get-network-connectivity-configuration", ncc_id])
                rules = (((ncc or {}).get("egress_config") or {}).get("target_rules") or {}).get(
                    "azure_private_endpoint_rules") or []
                # PENDING / EXPIRED / REJECTED rules carry no traffic.
                out["serverless"]["ncc_private_endpoint_rules"] = sum(
                    1 for r in rules if r.get("connection_state") == "ESTABLISHED"
                )
            option = run(["databricks", "-o", "json", "--profile", account_profile, "account",
                          "workspace-network-configuration", "get-workspace-network-option-rpc", str(workspace_id)])
            policy_id = option.get("network_policy_id") if isinstance(option, dict) else None
            policy = run(["databricks", "-o", "json", "--profile", account_profile, "account",
                          "network-policies", "get-network-policy-rpc", policy_id]) if policy_id else None
            if isinstance(policy, dict):
                out["serverless"]["network_policy_id"] = policy_id
                out["serverless"]["egress_restricted"] = egress_restricted(policy)
    return out


def egress_restricted(policy: dict) -> bool:
    """RESTRICTED_ACCESS only counts when enforced; DRY_RUN just logs."""
    access = (policy.get("egress") or {}).get("network_access") or {}
    enforcement = (access.get("policy_enforcement") or {}).get("enforcement_mode", "ENFORCED")
    return access.get("restriction_mode") == "RESTRICTED_ACCESS" and enforcement != "DRY_RUN"


def replay_runner(calls: list[dict]) -> Runner:
    """Runner that answers from recorded calls (demo mode and tests)."""
    table = {tuple(c["args"]): c["response"] for c in calls}
    return lambda args: table.get(tuple(args))


def replay(calls: list[dict]) -> dict:
    workspace_id = calls[0]["args"][calls[0]["args"].index("--ids") + 1]
    profiles = [c["args"][4] for c in calls if c["args"][:4] == ["databricks", "-o", "json", "--profile"]]
    profile = next((p for p in profiles if p != "account-profile"), None)
    account = "account-profile" if "account-profile" in profiles else None
    return collect(workspace_id, run=replay_runner(calls), databricks_profile=profile,
                   account_profile=account, auto_profiles=False)
