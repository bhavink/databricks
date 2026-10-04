"""Azure Databricks collectors."""

COLLECTION_HINTS = {
    "workspace": "include azurerm_databricks_workspace in the plan, or run `collect live --cloud azure`",
    "network": "subnets are managed outside this plan: add that plan, or run `collect live --cloud azure`",
    "private_link": "include the private-endpoints module in the plan, or run `collect live --cloud azure`",
    "dns": "include private DNS zones in the plan, or run `collect live --cloud azure`",
    "serverless": "include the account-level plan (NCC / network policy), or pass --account-profile to `collect live`",
    "access": "include databricks_workspace_conf / databricks_ip_access_list, or run `collect live --profile` "
              "from a network the workspace IP access list allows",
    "governance": "include the unity-catalog module, or run `collect live --profile` from a network the "
                  "workspace IP access list allows",
    "operations": "include azurerm_monitor_diagnostic_setting, or run `collect live --cloud azure`",
}
