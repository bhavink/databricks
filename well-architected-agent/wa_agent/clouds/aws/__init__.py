"""Databricks on AWS collectors."""

COLLECTION_HINTS = {
    "workspace": "include databricks_mws_workspaces in the plan",
    "network": "the VPC is managed outside this plan (e.g. an existing VPC for the SRA custom network): add that "
               "plan, or set the facts with --set",
    "private_link": "include databricks_mws_networks / databricks_mws_private_access_settings in the plan",
    "serverless": "include the plan that binds the NCC and network policy (workspace-guardrails, or the SRA)",
    "access": "include databricks_workspace_conf / databricks_ip_access_list (or the account network policy) in "
              "the plan",
    "governance": "include databricks_metastore_assignment in the plan",
    "operations": "audit log delivery is account-level: include databricks_mws_log_delivery, or set "
                  "operations.audit_log_delivery with --set after checking the account console",
}
