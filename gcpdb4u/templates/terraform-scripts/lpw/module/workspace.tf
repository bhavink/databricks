resource "databricks_mws_networks" "dbx_network" {
  provider     = databricks.accounts
  account_id   = local.databricks_account_id
  network_name = join("-", [substr(var.workspace_name, 0, 20), "nwconfig"])

  gcp_network_info {
    network_project_id = var.network_project_id
    vpc_id             = var.vpc_id
    subnet_id          = var.subnet_id
    subnet_region      = var.google_region
  }

  #vpc_endpoints {
  #  dataplane_relay = [local.dataplane_relay_vpc_endpoint_id[var.google_region]]
  #  rest_api        = [local.rest_api_vpc_endpoint_id[var.google_region]]
  #}
}

resource "databricks_mws_workspaces" "dbx_workspace" {
  provider       = databricks.accounts
  account_id     = local.databricks_account_id
  workspace_name = var.workspace_name
  location       = var.google_region

  cloud_resource_container {
    gcp {
      project_id = var.google_project_name
    }
  }
  # MODIFICATION - The following optional block is intentionally left blank.
  # Reason: All workspace properties are now set either in the main arguments or in conditional attachments (network/private_access).
  # Phase selection
  expected_workspace_status = var.expected_workspace_status

  # ---------------------------------------------------------
  # Conditional Attachments (only in Phase 2 = RUNNING)
  # ---------------------------------------------------------
  network_id                 = var.expected_workspace_status == "RUNNING" ? databricks_mws_networks.dbx_network.network_id : null
  private_access_settings_id = var.expected_workspace_status == "RUNNING" ? local.private_access_settings_id[var.google_region] : null


  #token {} #v0l02v1 comment
}



# MODIFICATION: Added explicit wait for workspace RUNNING state before proceeding with dependent resources.
# This ensures that provisioning dependent Databricks resources will only occur after the workspace is fully ready.
# Note: This resource introduces a blocking wait loop using gcloud and curl for status polling.

resource "null_resource" "wait_for_workspace_running" {
  count = var.expected_workspace_status == "RUNNING" ? 1 : 0

  # MODIFICATION: Use workspace_id and network_id as triggers to rerun if they change.
  triggers = {
    workspace_id = databricks_mws_workspaces.dbx_workspace.workspace_id
    network_id   = databricks_mws_workspaces.dbx_workspace.network_id
  }

  # MODIFICATION: Use a local-exec provisioner to poll Databricks workspace status via GCP and Databricks APIs.
  provisioner "local-exec" {
    command = <<-EOT
      echo "Waiting for workspace ${databricks_mws_workspaces.dbx_workspace.workspace_id} to reach RUNNING state..."
      
      # Get authentication tokens by impersonating the service account
      AUTH_TOKEN=$(gcloud auth print-identity-token \
        --impersonate-service-account="${var.databricks_google_service_account}" \
        --include-email \
        --audiences="https://accounts.gcp.databricks.com")
      
      ACCESS_TOKEN=$(gcloud auth print-access-token \
        --impersonate-service-account="${var.databricks_google_service_account}")
      
      max_attempts=60
      attempt=0
      while [ $attempt -lt $max_attempts ]; do
        status=$(curl -s -X GET \
          -H "X-Databricks-GCP-SA-Access-Token: $ACCESS_TOKEN" \
          -H "Authorization: Bearer $AUTH_TOKEN" \
          "https://accounts.gcp.databricks.com/api/2.0/accounts/${local.databricks_account_id}/workspaces/${databricks_mws_workspaces.dbx_workspace.workspace_id}" \
          | grep -o '"workspace_status":"[^"]*"' | cut -d'"' -f4)
        
        echo "Attempt $((attempt+1))/$max_attempts: Workspace status is: $status"
        
        if [ "$status" = "RUNNING" ]; then
          echo "Workspace is RUNNING. Proceeding with resource creation..."
          exit 0
        fi
        
        if [ "$status" = "FAILED" ]; then
          echo "ERROR: Workspace provisioning FAILED!"
          exit 1
        fi
        
        attempt=$((attempt+1))
        sleep 10
      done
      
      echo "ERROR: Timeout waiting for workspace to reach RUNNING state"
      exit 1
    EOT
  }

  # MODIFICATION: Explicitly depend on workspace resource to make sure it exists first.
  depends_on = [databricks_mws_workspaces.dbx_workspace]
}

# MODIFICATION: Ensure metastore assignment happens only after workspace is RUNNING by depending on null_resource.wait_for_workspace_running.
resource "databricks_metastore_assignment" "this" {
  count        = var.provision_workspace_resources ? 1 : 0
  provider     = databricks.accounts
  metastore_id = var.metastore_id == "" ? local.databricks_metastore_id[var.google_region] : var.metastore_id
  workspace_id = databricks_mws_workspaces.dbx_workspace.workspace_id
  # MODIFICATION - added null_resource.wait_for_workspace_running dependency to make sure that workspace is in running state
  depends_on = [null_resource.wait_for_workspace_running]
}

