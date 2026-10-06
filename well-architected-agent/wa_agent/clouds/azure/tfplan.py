"""Collect Azure facts from `terraform show -json` output (plan or state).

Pre-deployment review: run against the plan of any Terraform root (the
adb4u deployments, or your own). If network or account-level resources
live in a different root, collect each plan and pass all of them to
`assess` — facts are merged.

Workspaces are read from `azurerm_databricks_workspace` and from
`azapi_resource` of type `Microsoft.Databricks/workspaces` (how the
Databricks SRA creates serverless workspaces: `computeMode = "Serverless"`).
A plan with several workspaces (e.g. the SRA hub and spoke) needs
`workspace=` set to the address or name of the one to assess.

Plan-time limits (documented, deterministic): resource IDs are unknown
before apply, so correlation is by resource type and count, and DBFS
private endpoints are recognised by address name ("dbfs"). Network,
private endpoint and serverless facts come from the whole plan, not only
the selected workspace's module. Use the live collector for exact
correlation.
"""

from __future__ import annotations

from ...facts import COMPUTED, EVIDENCE
from .live import egress_restricted, ingress_restricted

DATABRICKS_DELEGATION = "Microsoft.Databricks/workspaces"
DBX_ZONE = "privatelink.azuredatabricks.net"
STORAGE_SERVICE_ENDPOINTS = ("Microsoft.Storage", "Microsoft.Storage.Global")


def _overlay_unknown(after, unknown):
    """Replace values Terraform marks as unknown with COMPUTED."""
    if unknown is True:
        return COMPUTED
    if isinstance(after, dict) and isinstance(unknown, dict):
        keys = set(after) | set(unknown)
        return {k: _overlay_unknown(after.get(k), unknown.get(k)) for k in keys}
    if isinstance(after, list) and isinstance(unknown, list):
        return [_overlay_unknown(a, u) for a, u in zip(after, unknown + [None] * len(after))]
    return after


def _walk_module(module: dict):
    yield from module.get("resources", [])
    for child in module.get("child_modules", []):
        yield from _walk_module(child)


def resources(doc: dict) -> list[dict]:
    """Return managed resources as {address, type, name, values}, sorted."""
    out = []
    if "resource_changes" in doc:
        for rc in doc["resource_changes"]:
            if rc.get("mode") != "managed" or rc["change"]["actions"] == ["delete"]:
                continue
            values = _overlay_unknown(rc["change"].get("after") or {}, rc["change"].get("after_unknown") or {})
            out.append({"address": rc["address"], "type": rc["type"], "name": rc["name"], "values": values})
    else:
        root = (doc.get("values") or doc.get("planned_values") or {}).get("root_module", {})
        for r in _walk_module(root):
            if r.get("mode") == "managed":
                out.append({"address": r["address"], "type": r["type"], "name": r["name"], "values": r.get("values") or {}})
    return sorted(out, key=lambda r: r["address"])


def _of_type(rs, *types):
    return [r for r in rs if r["type"] in types]


def _first(block):
    if isinstance(block, list):
        return block[0] if block else {}
    return block or {}


def _is_set(value) -> bool:
    return value not in (None, "", [], {})


_WS = ("azurerm_databricks_workspace", "azapi_resource")
AZAPI_WORKSPACE = "Microsoft.Databricks/workspaces"
_SUBNETS = ("azurerm_subnet",)
_SERVERLESS = ("databricks_mws_ncc_binding", "databricks_mws_workspaces")
PROVENANCE = {
    "workspace.": _WS,
    "workspace.cmk_dbfs_root": ("azurerm_databricks_workspace_root_dbfs_customer_managed_key",
                                "azurerm_databricks_workspace_customer_managed_key"),
    "network.delegated_subnet_count": _SUBNETS,
    "network.smallest_subnet_prefix_length": _SUBNETS,
    "network.all_subnets_have_nsg": _SUBNETS + ("azurerm_subnet_network_security_group_association",),
    "network.nat_gateway_attached": _SUBNETS + ("azurerm_subnet_nat_gateway_association",),
    "network.default_route_to_appliance": _SUBNETS + ("azurerm_route_table", "azurerm_route",
                                                      "azurerm_subnet_route_table_association"),
    "network.storage_service_endpoint": _SUBNETS,
    "network.service_endpoint_policy": _SUBNETS + ("azurerm_subnet_service_endpoint_storage_policy",),
    "network.firewall_present": ("azurerm_firewall",),
    "network.hub_peering": ("azurerm_virtual_network_peering",),
    "network.firewall_application_rules": ("azurerm_firewall_policy_rule_collection_group",
                                           "azurerm_firewall_application_rule_collection"),
    "network.firewall_logs": ("azurerm_firewall", "azurerm_monitor_diagnostic_setting"),
    "private_link.": ("azurerm_private_endpoint",),
    "dns.": ("azurerm_private_dns_zone", "azurerm_private_dns_zone_virtual_network_link"),
    "serverless.ncc_bound": _SERVERLESS,
    "serverless.ncc_private_endpoint_rules": ("databricks_mws_ncc_private_endpoint_rule",),
    "serverless.egress_restricted": ("databricks_account_network_policy", "databricks_workspace_network_option"),
    "access.": ("databricks_workspace_conf", "databricks_ip_access_list"),
    "access.context_ingress_enforced": ("databricks_account_network_policy", "databricks_workspace_network_option"),
    "governance.metastore_assigned": ("databricks_metastore_assignment",),
    "governance.access_connector": ("azurerm_databricks_access_connector",),
    "operations.diagnostic_settings": ("azurerm_monitor_diagnostic_setting",),
}


def _provenance(facts: dict, rs: list[dict]) -> dict:
    evidence = {}
    for ns, values in facts.items():
        if not isinstance(values, dict):
            continue
        for key in values:
            path = f"{ns}.{key}"
            types = PROVENANCE.get(path) or PROVENANCE.get(f"{ns}.")
            if not types:
                continue
            found = [f"terraform:{r['address']}" for r in rs if r["type"] in types]
            evidence[path] = found or [f"terraform: no {' / '.join(types)} in plan"]
    return evidence


def collect(doc: dict, workspace: str | None = None) -> dict:
    rs = resources(doc)
    facts = _collect(doc, rs, workspace)
    selected = facts.pop("_workspace_address", None)
    facts[EVIDENCE] = _provenance(facts, rs)
    if selected:
        for path in facts[EVIDENCE]:
            if path.startswith("workspace.") and path != "workspace.cmk_dbfs_root":
                facts[EVIDENCE][path] = [f"terraform:{selected}"]
    return facts


def _workspaces(rs) -> list[dict]:
    return [r for r in rs if r["type"] == "azurerm_databricks_workspace"
            or (r["type"] == "azapi_resource"
                and str(r["values"].get("type", "")).split("@")[0] == AZAPI_WORKSPACE)]


def select_workspace(rs, workspace: str | None) -> dict | None:
    candidates = _workspaces(rs)
    if workspace:
        chosen = [r for r in candidates if workspace in (r["address"], r["values"].get("name"))]
        if len(chosen) != 1:
            raise ValueError(f"no single workspace matching {workspace!r}; candidates: "
                             f"{[r['address'] for r in candidates]}")
        return chosen[0]
    if len(candidates) > 1:
        raise ValueError("plan contains more than one Databricks workspace; choose one with --workspace: "
                         f"{[r['address'] for r in candidates]}")
    return candidates[0] if candidates else None


def _azapi_workspace(values: dict) -> dict:
    body = values.get("body") if isinstance(values.get("body"), dict) else {}
    props = body.get("properties") if isinstance(body.get("properties"), dict) else {}
    params = props.get("parameters") if isinstance(props.get("parameters"), dict) else {}
    entities = _first(props.get("encryption")).get("entities") or {}

    def param(name):
        p = params.get(name)
        return p.get("value") if isinstance(p, dict) else p

    serverless = props.get("computeMode") == "Serverless"
    return {
        "name": values.get("name"),
        "sku": _first(body.get("sku")).get("name"),
        "compute_mode": "serverless" if serverless else "classic",
        "vnet_injected": _is_set(param("customVirtualNetworkId")),
        "no_public_ip": param("enableNoPublicIp"),
        "public_network_access_enabled": None if props.get("publicNetworkAccess") is None
        else props.get("publicNetworkAccess") != "Disabled",
        "required_nsg_rules": props.get("requiredNsgRules"),
        "cmk_managed_services": _is_set(entities.get("managedServices")),
        "cmk_managed_disks": _is_set(entities.get("managedDisk")),
        "cmk_dbfs_root": _is_set(param("encryption")),
        "default_storage_firewall_enabled": props.get("defaultStorageFirewall") == "Enabled",
    }


def _collect(doc: dict, rs: list[dict], workspace: str | None = None) -> dict:
    facts: dict = {"cloud": "azure", "source": "terraform-plan" if "resource_changes" in doc else "terraform-state"}

    selected = select_workspace(rs, workspace)
    if selected and selected["type"] == "azapi_resource":
        facts["workspace"] = _azapi_workspace(selected["values"])
        facts["_workspace_address"] = selected["address"]
    elif selected:
        facts["_workspace_address"] = selected["address"]
        ws = selected["values"]
        cp = _first(ws.get("custom_parameters"))
        facts["workspace"] = {
            "name": ws.get("name"),
            "sku": ws.get("sku"),
            "compute_mode": "classic",
            "vnet_injected": _is_set(cp.get("virtual_network_id")),
            "no_public_ip": cp.get("no_public_ip"),
            "public_network_access_enabled": ws.get("public_network_access_enabled"),
            "required_nsg_rules": ws.get("network_security_group_rules_required"),
            "cmk_managed_services": _is_set(ws.get("managed_services_cmk_key_vault_key_id")),
            "cmk_managed_disks": _is_set(ws.get("managed_disk_cmk_key_vault_key_id")),
            "cmk_dbfs_root": bool(
                _of_type(rs, "azurerm_databricks_workspace_root_dbfs_customer_managed_key",
                         "azurerm_databricks_workspace_customer_managed_key")
            ),
            # Unset in config means the provider default (disabled).
            "default_storage_firewall_enabled": bool(ws.get("default_storage_firewall_enabled")),
        }

    facts["network"] = _network(rs)
    facts["private_link"] = _private_link(rs)
    facts["dns"] = _dns(rs)
    facts["serverless"] = _serverless(rs)
    facts["access"] = _access(rs)
    facts["governance"] = {
        "metastore_assigned": bool(_of_type(rs, "databricks_metastore_assignment")),
        "access_connector": bool(_of_type(rs, "azurerm_databricks_access_connector")),
    }
    facts["operations"] = {"diagnostic_settings": bool(_of_type(rs, "azurerm_monitor_diagnostic_setting"))}
    return facts


def _network(rs) -> dict:
    subnets = [
        r["values"] for r in _of_type(rs, "azurerm_subnet")
        if any(_first(d.get("service_delegation")).get("name") == DATABRICKS_DELEGATION
               for d in r["values"].get("delegation") or [])
    ]
    if not subnets:
        # Subnets are managed outside this plan (BYO network / data sources):
        # leave network facts unknown rather than reporting false failures.
        return {}
    count = len(subnets)
    routes = [rt for r in _of_type(rs, "azurerm_route_table") for rt in r["values"].get("route") or []]
    routes += [r["values"] for r in _of_type(rs, "azurerm_route")]
    to_appliance = any(
        rt.get("address_prefix") == "0.0.0.0/0" and rt.get("next_hop_type") == "VirtualAppliance" for rt in routes
    )
    prefixes = [int(str(cidr).split("/")[1]) for sub in subnets for cidr in sub.get("address_prefixes") or []
                if "/" in str(cidr)]
    return {
        "smallest_subnet_prefix_length": max(prefixes) if prefixes else None,
        "delegated_subnet_count": count,
        "all_subnets_have_nsg": len(_of_type(rs, "azurerm_subnet_network_security_group_association")) >= count,
        "nat_gateway_attached": len(_of_type(rs, "azurerm_subnet_nat_gateway_association")) >= count,
        "default_route_to_appliance": to_appliance
        and len(_of_type(rs, "azurerm_subnet_route_table_association")) >= count,
        "storage_service_endpoint": all(
            any(e in STORAGE_SERVICE_ENDPOINTS for e in s.get("service_endpoints") or []) for s in subnets
        ),
        "service_endpoint_policy": bool(_of_type(rs, "azurerm_subnet_service_endpoint_storage_policy"))
        or all(_is_set(s.get("service_endpoint_policy_ids")) for s in subnets),
        "firewall_present": bool(_of_type(rs, "azurerm_firewall")),
    } | _hub(rs)


def _hub(rs) -> dict:
    """Peering and firewall facts, only where this plan can establish them.

    The hub often lives in another Terraform root: a missing peering or
    firewall here is unknown (collect the hub plan too, or scan live), not FAIL.
    """
    out: dict = {}
    if _of_type(rs, "azurerm_virtual_network_peering"):
        out["hub_peering"] = True
    if not _of_type(rs, "azurerm_firewall"):
        return out
    groups = _of_type(rs, "azurerm_firewall_policy_rule_collection_group")
    out["firewall_application_rules"] = bool(_of_type(rs, "azurerm_firewall_application_rule_collection")) or any(
        r["values"].get("application_rule_collection") not in (None, [], COMPUTED) for r in groups)
    out["firewall_logs"] = any(
        "azurefirewalls" in str(r["values"].get("target_resource_id", "")).lower() or "firewall" in r["address"].lower()
        for r in _of_type(rs, "azurerm_monitor_diagnostic_setting"))
    return out


def _private_link(rs) -> dict:
    found = set()
    for r in _of_type(rs, "azurerm_private_endpoint"):
        for conn in r["values"].get("private_service_connection") or []:
            for sub in conn.get("subresource_names") or []:
                if sub in ("dfs", "blob"):
                    if "dbfs" in r["address"].lower():
                        found.add(f"dbfs_{sub}")
                else:
                    found.add(sub)
    return {
        "ui_api": "databricks_ui_api" in found,
        "browser_authentication": "browser_authentication" in found,
        "dbfs_dfs": "dbfs_dfs" in found,
        "dbfs_blob": "dbfs_blob" in found,
    }


def _dns(rs) -> dict:
    zone = any(r["values"].get("name") == DBX_ZONE for r in _of_type(rs, "azurerm_private_dns_zone"))
    linked = zone and any(
        r["values"].get("private_dns_zone_name") in (DBX_ZONE, COMPUTED)
        for r in _of_type(rs, "azurerm_private_dns_zone_virtual_network_link")
    )
    return {"azuredatabricks_zone": zone, "azuredatabricks_zone_linked": linked}


def _serverless(rs) -> dict:
    bound = bool(_of_type(rs, "databricks_mws_ncc_binding")) or any(
        _is_set(r["values"].get("network_connectivity_config_id")) for r in _of_type(rs, "databricks_mws_workspaces")
    )
    restricted_policy = any(
        egress_restricted({"egress": {"network_access": _network_access(r["values"])}})
        for r in _of_type(rs, "databricks_account_network_policy")
    )
    return {
        "ncc_bound": bound,
        "ncc_private_endpoint_rules": len(_of_type(rs, "databricks_mws_ncc_private_endpoint_rule")),
        "egress_restricted": restricted_policy and bool(_of_type(rs, "databricks_workspace_network_option")),
    }


def _network_access(values: dict) -> dict:
    access = dict(_first(_first(values.get("egress")).get("network_access")))
    access["policy_enforcement"] = _first(access.get("policy_enforcement"))
    return access


def _access(rs) -> dict:
    enabled = any(
        str((r["values"].get("custom_config") or {}).get("enableIpAccessLists")).lower() == "true"
        for r in _of_type(rs, "databricks_workspace_conf")
    )
    allow_lists = [
        r for r in _of_type(rs, "databricks_ip_access_list")
        if r["values"].get("list_type") == "ALLOW" and r["values"].get("enabled", True) is not False
    ]
    conf = {}
    for r in _of_type(rs, "databricks_workspace_conf"):
        conf.update(r["values"].get("custom_config") or {})

    def feature_enabled(key: str) -> bool:
        # Unset means the Databricks default, which is enabled.
        return str(conf.get(key, "")).lower() != "false"

    out = {
        "ip_access_lists_enabled": enabled,
        "ip_access_list_count": len(allow_lists),
        "notebook_export_enabled": feature_enabled("enableExportNotebook"),
        "results_download_enabled": feature_enabled("enableResultsDownloading"),
        "table_clipboard_enabled": feature_enabled("enableNotebookTableClipboard"),
    }
    policies = _of_type(rs, "databricks_account_network_policy")
    if policies:
        # Context-based ingress lives on the same network policy object as serverless egress.
        out["context_ingress_enforced"] = bool(_of_type(rs, "databricks_workspace_network_option")) and any(
            ingress_restricted(r["values"]) for r in policies)
    return out
