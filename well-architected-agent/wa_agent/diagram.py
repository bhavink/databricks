"""Architecture diagram + resource manifest from a `terraform show -json` plan
or state. Works for any Terraform (repo deployments, the SRA, your own): the
diagram is drawn from the same facts the assessment uses, the manifest lists
every managed resource. Deterministic: same input, same Markdown."""

from __future__ import annotations

from .clouds.azure import tfplan
from .facts import COMPUTED

# First matching prefix wins; order matters.
AREAS = (
    ("Workspace", ("azurerm_databricks_workspace", "databricks_workspace_conf", "databricks_ip_access_list",
                   "databricks_disable_legacy")),
    ("Private Link & DNS", ("azurerm_private_endpoint", "azurerm_private_dns")),
    ("Network", ("azurerm_virtual_network", "azurerm_subnet", "azurerm_network_security", "azurerm_nat_gateway",
                 "azurerm_public_ip", "azurerm_route", "azurerm_firewall", "azurerm_ip_group")),
    ("Serverless", ("databricks_mws_ncc", "databricks_mws_network_connectivity_config",
                    "databricks_account_network_policy", "databricks_workspace_network_option")),
    ("Unity Catalog & storage", ("databricks_metastore", "databricks_catalog", "databricks_storage_credential",
                                 "databricks_external_location", "databricks_schema", "azurerm_databricks_access_connector",
                                 "azurerm_storage")),
    ("Keys & identity", ("azurerm_key_vault", "azurerm_role_assignment", "azurerm_user_assigned_identity",
                         "azurerm_disk_encryption_set")),
    ("Observability", ("azurerm_monitor",)),
)
WORKSPACE_TYPES = ("azapi_resource",)  # azapi workspaces are classified by their ARM type


def area_of(resource: dict) -> str:
    rtype = resource["type"]
    if rtype in WORKSPACE_TYPES and str(resource["values"].get("type", "")).startswith(tfplan.AZAPI_WORKSPACE):
        return "Workspace"
    for area, prefixes in AREAS:
        if rtype.startswith(prefixes):
            return area
    return "Other"


def _on(value) -> bool:
    return value is True


def _yes(value, yes: str, no: str, unknown: str = "not in this plan") -> str:
    if value is COMPUTED or value == COMPUTED:
        return "known after apply"
    if value is None:
        return unknown
    return yes if value else no


def mermaid(facts: dict) -> list[str]:
    ws = facts.get("workspace") or {}
    net = facts.get("network") or {}
    pl = facts.get("private_link") or {}
    srv = facts.get("serverless") or {}
    acc = facts.get("access") or {}
    gov = facts.get("governance") or {}
    ops = facts.get("operations") or {}
    serverless = ws.get("compute_mode") == "serverless"
    name = ws.get("name") or "workspace"
    lines = ["```mermaid",
             '%%{init: {"theme": "base", "themeVariables": {"fontFamily": "Space Grotesk, Helvetica, Arial, sans-serif", '
             '"lineColor": "#1a1a1a", "edgeLabelBackground": "#ffffff", "primaryTextColor": "#1a1a1a"}}}%%',
             "flowchart LR",
             f'  WS["Databricks workspace<br/>{name} · {ws.get("compute_mode", "unknown")}"]']

    lines.append('  USERS["Users and tools"]')
    if _on(pl.get("ui_api")) and ws.get("public_network_access_enabled") is False:
        lines.append('  USERS -->|"HTTPS via private endpoint only"| WS')
    elif _on(pl.get("ui_api")):
        lines.append('  USERS -->|"HTTPS via private endpoint or internet"| WS')
    else:
        acl = "IP access list" if _on(acc.get("ip_access_lists_enabled")) else "no IP access list"
        lines.append(f'  USERS -->|"HTTPS over internet · {acl}"| WS')

    if not serverless and ws:
        if _on(ws.get("vnet_injected")):
            size = net.get("smallest_subnet_prefix_length")
            subnets = f"{net.get('delegated_subnet_count', '?')} delegated subnets" + (f" /{size}" if size else "")
            nsg = " · NSG" if _on(net.get("all_subnets_have_nsg")) else ""
            lines.append(f'  VNET["Your VNet: classic compute<br/>{subnets}{nsg}"]')
        else:
            lines.append('  VNET["Databricks-managed VNet: classic compute"]')
        lines.append('  WS -->|"runs clusters in"| VNET')
        scc = "secure cluster connectivity, no public IPs" if _on(ws.get("no_public_ip")) else "public IPs on nodes"
        path = "over Private Link" if _on(pl.get("ui_api")) else "over the internet"
        lines.append(f'  VNET -->|"{scc} · {path}"| CP["Databricks control plane"]')
        if _on(net.get("default_route_to_appliance")):
            fw = "Azure Firewall" if _on(net.get("firewall_present")) else "Firewall / NVA"
            lines.append(f'  VNET -->|"0.0.0.0/0 via route table"| FW["{fw}<br/>FQDN allowlist"]')
            lines.append('  FW -->|"allowed destinations only"| NET["Internet"]')
        elif _on(net.get("nat_gateway_attached")):
            lines.append('  VNET -->|"outbound via NAT gateway"| NET["Internet"]')
        elif net:
            lines.append('  VNET -->|"no explicit egress path in this plan"| NET["Internet"]')
        storage = []
        if _on(pl.get("dbfs_dfs")) or _on(pl.get("dbfs_blob")):
            storage.append("private endpoints")
        if _on(net.get("storage_service_endpoint")):
            storage.append("service endpoint" + (" + policy" if _on(net.get("service_endpoint_policy")) else ""))
        if storage:
            lines.append(f'  VNET -->|"storage via {" and ".join(storage)}"| ST["Azure Storage<br/>workspace and data"]')

    if srv.get("ncc_bound") is not None:
        policy = "egress restricted and enforced" if _on(srv.get("egress_restricted")) else "egress not restricted"
        lines.append('  SRV["Serverless compute<br/>Databricks account"]')
        lines.append(f'  WS -->|"serverless workloads · NCC {_yes(srv.get("ncc_bound"), "bound", "not bound")}"| SRV')
        lines.append(f'  SRV -->|"{policy}"| SNET["Internet"]')
        rules = srv.get("ncc_private_endpoint_rules") or 0
        if rules:
            lines.append(f'  SRV -->|"{rules} NCC private endpoint rule(s)"| SST["Your storage accounts"]')

    if _on(gov.get("metastore_assigned")):
        lines.append('  WS -->|"metastore assignment"| UC["Unity Catalog metastore"]')
    keys = [k for k, label in (("cmk_managed_services", "managed services"), ("cmk_managed_disks", "disks"),
                               ("cmk_dbfs_root", "DBFS root")) if _on(ws.get(k))]
    if keys:
        what = ", ".join(label for k, label in (("cmk_managed_services", "managed services"),
                                                ("cmk_managed_disks", "disks"), ("cmk_dbfs_root", "DBFS root"))
                         if k in keys)
        lines.append(f'  KV["Key Vault<br/>customer-managed keys"] -->|"encrypts {what}"| WS')
    if _on(ops.get("diagnostic_settings")):
        lines.append('  WS -->|"diagnostic (audit) logs"| LOGS["Log destination<br/>Log Analytics / Storage / Event Hub"]')
    # Swiss Modern Samurai: ink on white, vermillion marks the workspace only.
    lines += ["  classDef default fill:#ffffff,stroke:#1a1a1a,color:#1a1a1a",
              "  classDef focus fill:#ffffff,stroke:#cc3311,stroke-width:2px,color:#1a1a1a",
              "  class WS focus", "```"]
    return lines


def to_markdown(doc: dict, workspace: str | None = None) -> str:
    facts = tfplan.collect(doc, workspace=workspace)
    rs = tfplan.resources(doc)
    kind = "plan" if facts["source"] == "terraform-plan" else "state"
    ws = facts.get("workspace") or {}
    lines = [f"# Architecture — {ws.get('name') or 'Terraform ' + kind}", "",
             f"Generated from a Terraform {kind} ({len(rs)} managed resources). The agent changed nothing.", ""]
    lines += mermaid(facts)

    groups: dict[str, list[dict]] = {}
    for r in rs:
        groups.setdefault(area_of(r), []).append(r)
    order = [a for a, _ in AREAS] + ["Other"]
    lines += ["", "## Manifest", "", "| Area | Resource type | Count |", "|---|---|---|"]
    for area in order:
        counts: dict[str, int] = {}
        for r in groups.get(area, []):
            counts[r["type"]] = counts.get(r["type"], 0) + 1
        for rtype in sorted(counts):
            lines.append(f"| {area} | `{rtype}` | {counts[rtype]} |")
    lines += ["", "<details><summary>All resource addresses</summary>", ""]
    lines += [f"- `{r['address']}`" for area in order for r in groups.get(area, [])]
    lines += ["", "</details>", ""]
    return "\n".join(lines)
