"""Synthetic `terraform show -json` plans shaped like the adb4u deployments."""

import pytest

from wa_agent import catalog


def rc(address, rtype, after, after_unknown=None, actions=("create",)):
    return {
        "address": address,
        "mode": "managed",
        "type": rtype,
        "name": address.rsplit(".", 1)[-1],
        "change": {"actions": list(actions), "after": after, "after_unknown": after_unknown or {}},
    }


def subnet(name, policies=None):
    return rc(
        f"module.networking.azurerm_subnet.{name}[0]",
        "azurerm_subnet",
        {
            "name": f"ws-{name}-subnet",
            "delegation": [{"name": "databricks-delegation",
                            "service_delegation": [{"name": "Microsoft.Databricks/workspaces"}]}],
            "address_prefixes": ["10.178.0.0/26"],  # as in the adb4u tfvars examples
            "service_endpoints": ["Microsoft.KeyVault", "Microsoft.Storage"],
            "service_endpoint_policy_ids": policies,
        },
    )


def workspace(**overrides):
    after = {
        "name": "ws-demo",
        "sku": "premium",
        "public_network_access_enabled": True,
        "network_security_group_rules_required": "AllRules",
        "managed_services_cmk_key_vault_key_id": None,
        "managed_disk_cmk_key_vault_key_id": None,
        "default_storage_firewall_enabled": None,
        "custom_parameters": [{"no_public_ip": True}],
    }
    after.update(overrides)
    return rc("module.workspace.azurerm_databricks_workspace.this", "azurerm_databricks_workspace", after,
              {"custom_parameters": [{"virtual_network_id": True}]})


def non_pl_plan():
    return {
        "format_version": "1.2",
        "resource_changes": [
            workspace(),
            subnet("public"),
            subnet("private"),
            rc("module.networking.azurerm_subnet_network_security_group_association.public[0]",
               "azurerm_subnet_network_security_group_association", {}),
            rc("module.networking.azurerm_subnet_network_security_group_association.private[0]",
               "azurerm_subnet_network_security_group_association", {}),
            rc("module.networking.azurerm_subnet_nat_gateway_association.public[0]",
               "azurerm_subnet_nat_gateway_association", {}),
            rc("module.networking.azurerm_subnet_nat_gateway_association.private[0]",
               "azurerm_subnet_nat_gateway_association", {}),
            rc("module.service_endpoint_policy.azurerm_subnet_service_endpoint_storage_policy.this[0]",
               "azurerm_subnet_service_endpoint_storage_policy", {}),
            rc("module.ncc.databricks_mws_ncc_binding.this", "databricks_mws_ncc_binding", {}),
            rc("module.workspace.databricks_workspace_conf.this[0]", "databricks_workspace_conf",
               {"custom_config": {"enableIpAccessLists": "true"}}),
            rc("module.workspace.databricks_ip_access_list.allowed[0]", "databricks_ip_access_list",
               {"list_type": "ALLOW", "enabled": True}),
            rc("module.unity_catalog.databricks_metastore_assignment.this[0]", "databricks_metastore_assignment", {}),
            rc("module.unity_catalog.azurerm_databricks_access_connector.this", "azurerm_databricks_access_connector", {}),
        ],
    }


def pe(name, sub):
    return rc(f"module.private_endpoints.azurerm_private_endpoint.{name}", "azurerm_private_endpoint",
              {"private_service_connection": [{"subresource_names": [sub]}]})


def full_private_plan():
    plan = non_pl_plan()
    changes = [r for r in plan["resource_changes"]
               if r["type"] not in ("azurerm_subnet_nat_gateway_association", "databricks_workspace_conf",
                                    "databricks_ip_access_list", "azurerm_databricks_workspace")]
    changes += [
        workspace(public_network_access_enabled=False, network_security_group_rules_required="NoAzureDatabricksRules"),
        pe("databricks_ui_api", "databricks_ui_api"),
        pe("browser_authentication", "browser_authentication"),
        pe("dbfs_dfs", "dfs"),
        pe("dbfs_blob", "blob"),
        rc("module.private_endpoints.azurerm_private_dns_zone.databricks", "azurerm_private_dns_zone",
           {"name": "privatelink.azuredatabricks.net"}),
        rc("module.private_endpoints.azurerm_private_dns_zone_virtual_network_link.databricks",
           "azurerm_private_dns_zone_virtual_network_link", {"private_dns_zone_name": None},
           {"private_dns_zone_name": True}),
        rc("module.ncc.databricks_mws_ncc_private_endpoint_rule.uc_dfs", "databricks_mws_ncc_private_endpoint_rule", {}),
        rc("module.ncc.databricks_account_network_policy.this[0]", "databricks_account_network_policy",
           {"egress": {"network_access": {"restriction_mode": "RESTRICTED_ACCESS",
                                          "policy_enforcement": {"enforcement_mode": "ENFORCED"}}}}),
        rc("module.ncc.databricks_workspace_network_option.this[0]", "databricks_workspace_network_option", {}),
        rc("azurerm_monitor_diagnostic_setting.databricks", "azurerm_monitor_diagnostic_setting", {}),
    ]
    plan["resource_changes"] = changes
    return plan


@pytest.fixture(scope="session")
def azure_catalog():
    return catalog.load("azure")


def serverless_plan(cmk=False, leak_features_off=False, storage_pe=False):
    """Shaped like adb4u/deployments/serverless: no network for a public serverless workspace."""
    properties = {"computeMode": "Serverless", "publicNetworkAccess": "Enabled"}
    if cmk:
        properties["encryption"] = {"entities": {"managedServices": {
            "keySource": "Microsoft.Keyvault", "keyName": "cmk", "keyVaultUri": "https://kv.vault.azure.net/",
            "keyVersion": "0123456789abcdef"}}}
    conf = {"enableIpAccessLists": "true"}
    if leak_features_off:
        conf.update(enableExportNotebook="false", enableResultsDownloading="false", enableNotebookTableClipboard="false")
    changes = [
        rc("azapi_resource.workspace", "azapi_resource",
           {"type": "Microsoft.Databricks/workspaces@2026-01-01", "name": "srvtest-workspace",
            "body": {"sku": {"name": "premium"}, "properties": properties}}),
        rc("databricks_mws_network_connectivity_config.this", "databricks_mws_network_connectivity_config", {}),
        rc("databricks_mws_ncc_binding.this", "databricks_mws_ncc_binding", {}),
        rc("databricks_account_network_policy.this", "databricks_account_network_policy",
           {"egress": {"network_access": {"restriction_mode": "RESTRICTED_ACCESS",
                                          "policy_enforcement": {"enforcement_mode": "ENFORCED"}}}}),
        rc("databricks_workspace_network_option.this", "databricks_workspace_network_option", {}),
        rc("databricks_metastore_assignment.this", "databricks_metastore_assignment", {}),
        rc("databricks_workspace_conf.this[0]", "databricks_workspace_conf", {"custom_config": conf}),
        rc("databricks_ip_access_list.allowed[0]", "databricks_ip_access_list", {"list_type": "ALLOW", "enabled": True}),
        rc("module.monitoring[0].azurerm_monitor_diagnostic_setting.workspace", "azurerm_monitor_diagnostic_setting", {}),
    ]
    if storage_pe:
        changes.append(rc('databricks_mws_ncc_private_endpoint_rule.storage["st"]',
                          "databricks_mws_ncc_private_endpoint_rule", {"group_id": "dfs"}))
    return {"format_version": "1.2", "resource_changes": changes}
