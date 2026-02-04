# User Assignment Module

This module assigns an existing Databricks account user as a workspace administrator.

## Reference

Based on the [Databricks SRA User Assignment Module](https://github.com/databricks/terraform-databricks-sra/tree/main/aws/tf/modules/databricks_account/user_assignment).

## Prerequisites

1. **User must already exist** in the Databricks account console
2. **Workspace must be assigned** to a Unity Catalog metastore before running this module

## Usage

```hcl
module "user_assignment" {
  source = "./modules/user_assignment"

  user_name    = "admin@example.com"
  workspace_id = module.databricks_workspace.workspace_id

  providers = {
    databricks = databricks.account
  }

  depends_on = [
    module.unity_catalog.metastore_assignment_id
  ]
}
```

## Inputs

| Name | Description | Type | Required |
|------|-------------|------|----------|
| `user_name` | Email address of the user to assign as workspace admin | `string` | Yes |
| `workspace_id` | Databricks workspace ID | `string` | Yes |

## Outputs

| Name | Description |
|------|-------------|
| `user_id` | ID of the user assigned as workspace admin |
| `permission_assignment_id` | ID of the workspace permission assignment |
| `user_name` | Email address of the workspace admin |

## Important Notes

- The user must already exist in the Databricks account console before running this module
- This module uses `databricks_mws_permission_assignment` which requires the workspace to have Unity Catalog enabled and assigned
- The `lifecycle { ignore_changes = [principal_id] }` prevents Terraform from trying to update the assignment if the user ID changes

## Dependencies

This module should be applied **after**:
1. Workspace creation
2. Unity Catalog metastore assignment to the workspace

