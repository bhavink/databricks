# Databricks Workspace Module

This module creates the Databricks workspace and all required MWS (Multi-Workspace Services) configurations.

## Features

- ✅ MWS credentials configuration
- ✅ MWS storage configuration  
- ✅ MWS network configuration
- ✅ MWS private access settings (Backend Private Link)
- ✅ Databricks workspace creation
- ✅ Workspace admin user assignment

## Resources Created

| Resource | Description |
|----------|-------------|
| `databricks_mws_credentials` | Cross-account IAM role credentials |
| `databricks_mws_storage_configurations` | Root storage bucket configuration |
| `databricks_mws_networks` | VPC, subnets, and security group configuration |
| `databricks_mws_private_access_settings` | Backend Private Link settings |
| `databricks_mws_workspaces` | Databricks workspace |
| `databricks_mws_permission_assignment` | Workspace admin permissions |

## Usage

```hcl
module "databricks_workspace" {
  source = "./modules/databricks_workspace"

  prefix                      = "dbx-prod"
  workspace_name              = "production"
  region                      = "us-west-2"
  databricks_account_id       = "your-account-id"
  workspace_admin_email       = "admin@company.com"
  client_id                   = var.databricks_client_id
  client_secret               = var.databricks_client_secret
  
  vpc_id                      = module.networking.vpc_id
  private_subnet_ids          = module.networking.private_subnet_ids
  workspace_security_group_id = module.networking.workspace_security_group_id
  workspace_vpce_id           = module.networking.workspace_vpce_id
  relay_vpce_id               = module.networking.relay_vpce_id
  
  root_storage_bucket         = module.storage.root_storage_bucket
  cross_account_role_arn      = module.iam.cross_account_role_arn
  
  tags = {
    Environment = "production"
  }

  providers = {
    databricks.account = databricks.account
  }
}
```

## Requirements

- Databricks provider with account-level authentication
- AWS networking resources (VPC, subnets, security groups, VPC endpoints)
- AWS IAM cross-account role
- AWS S3 root storage bucket

## Inputs

| Name | Description | Type | Required |
|------|-------------|------|----------|
| prefix | Prefix for resource naming | string | yes |
| workspace_name | Name of the workspace | string | yes |
| region | AWS region | string | yes |
| databricks_account_id | Databricks account ID | string | yes |
| workspace_admin_email | Admin user email | string | yes |
| vpc_id | VPC ID | string | yes |
| private_subnet_ids | Private subnet IDs | list(string) | yes |
| workspace_security_group_id | Security group ID | string | yes |
| workspace_vpce_id | Workspace VPC endpoint ID | string | yes |
| relay_vpce_id | Relay VPC endpoint ID | string | yes |
| root_storage_bucket | Root storage bucket name | string | yes |
| cross_account_role_arn | Cross-account role ARN | string | yes |

## Outputs

| Name | Description |
|------|-------------|
| workspace_id | Workspace ID |
| workspace_url | Workspace URL |
| workspace_status | Workspace status |
| deployment_name | Deployment name |

## Dependencies

This module depends on:
- Networking module (VPC, subnets, security groups, VPC endpoints)
- Storage module (root storage bucket)
- IAM module (cross-account role)

## Notes

- The workspace takes ~5-10 minutes to provision
- Wait 20 minutes after creation before creating clusters (backend Private Link stabilization)
- Workspace admin must exist in Databricks account before assignment

