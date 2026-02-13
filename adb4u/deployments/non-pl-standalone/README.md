# Standalone Non–Private Link Databricks Deployment

Self-contained Terraform that creates a minimal **non–Private Link** Azure Databricks workspace with VNet injection. No modules, no CMK, no Private Link, no SEPs.

## Features

- **Single deployment** — all resources inlined (no `../../modules/...`)
- **Networking** — VNet, public/private subnets (Databricks delegation), NSG, NAT gateway
- **Workspace** — `azurerm_databricks_workspace` with public network access, no customer-managed keys
- **Existing Unity Catalog** — optional attachment to an existing metastore (no UC resources created here)

## Prerequisites

- Terraform >= 1.5
- Azure CLI or service principal (ARM_* or Azure CLI login)
- For UC assignment: Databricks SP (DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET, DATABRICKS_AZURE_TENANT_ID)

## Usage

1. Copy `terraform.tfvars.example` to `terraform.tfvars` and set `location`, `resource_group_name`, `workspace_prefix`.
2. **Without UC:**
   `terraform init -backend=false` (or configure backend), then `terraform plan` / `terraform apply`.
3. **With existing UC:**
   - First apply with UC vars empty (creates workspace only).
   - Set `existing_metastore_id` and `databricks_host` (use `workspace_url` from output).
   - Apply again to create `databricks_metastore_assignment`.

## Variables (main)

| Variable | Description |
|----------|-------------|
| `location` | Azure region |
| `resource_group_name` | Resource group name |
| `workspace_prefix` | Prefix for workspace and network resources |
| `existing_metastore_id` | (Optional) Existing UC metastore UUID; when set (with `databricks_host`), workspace is attached to this metastore |
| `databricks_host` | (Optional) Workspace URL for Databricks provider; required when using `existing_metastore_id` (set after first apply) |

## Outputs

- `workspace_url` — workspace URL
- `workspace_id` — Azure resource ID
- `workspace_id_numeric` — numeric workspace ID (APIs / UC)
- `nat_gateway_public_ip` — NAT gateway public IP
