"""Databricks on Google Cloud collectors."""

COLLECTION_HINTS = {
    "workspace": "include databricks_mws_workspaces in the plan, or run `collect live --cloud gcp`",
    "network": "the VPC is managed outside this plan (e.g. infra4db): add that plan, or run `collect live --cloud gcp`",
    "private_link": "include databricks_mws_networks / databricks_mws_private_access_settings, or run "
                    "`collect live --cloud gcp --account-profile`",
    "dns": "include the private DNS zones (infra4db), or run `collect live --cloud gcp`",
    "serverless": "include the plan that binds the NCC and network policy (lpw or workspace-guardrails), or pass "
                  "--account-profile to `collect live`",
    "access": "include databricks_workspace_conf / databricks_ip_access_list, or run `collect live --profile` from a "
              "network the workspace IP access list allows",
    "governance": "include databricks_metastore_assignment, or run `collect live --profile`",
    "operations": "audit log delivery is account-level: run `collect live --cloud gcp --account-profile`",
}
