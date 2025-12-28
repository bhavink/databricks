resource "databricks_connection" "bigquery" {
  provider        = databricks.workspace
  for_each        = var.provision_workspace_resources ? local.foriegn_catalog_bq_connection_map : {}
  name            = each.value.name
  connection_type = "BIGQUERY"
  comment         = "this is a connection to BQ"
  options = {
    GoogleServiceAccountKeyJson = jsonencode(each.value.service_account)
  }
  properties = {
    purpose = "bq_connection"
  }
  ***REMOVED*** MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [null_resource.wait_for_workspace_running]
}