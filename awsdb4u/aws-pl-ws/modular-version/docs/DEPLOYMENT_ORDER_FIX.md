***REMOVED*** Workspace Admin Assignment - Deployment Order Fix

***REMOVED******REMOVED*** The Problem

The permission assignment was failing because Unity Catalog had not been assigned to the workspace yet.

```
ERROR: Permission assignment APIs are not available for this workspace.
```

***REMOVED******REMOVED*** Understanding the Issue

***REMOVED******REMOVED******REMOVED*** ❌ **What Was Happening (WRONG)**

```
┌─────────────────────────────────────────────────────────────┐
│ Workspace Module (runs in parallel with UC module)          │
│                                                              │
│  1. Create Workspace                                        │
│     ↓                                                        │
│  2. Assign Admin ❌ ERROR!                                  │
│     (UC not assigned yet!)                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Unity Catalog Module (runs in parallel)                     │
│                                                              │
│  1. Create Metastore                                        │
│     ↓                                                        │
│  2. Assign Metastore to Workspace                           │
│     (happens AFTER admin assignment tried to run)           │
└─────────────────────────────────────────────────────────────┘
```

**Problem**: Both modules depend on the workspace, so they run in parallel. The admin assignment tries to run before UC assignment completes.

***REMOVED******REMOVED******REMOVED*** ✅ **What Should Happen (CORRECT)**

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Workspace Module                                    │
│                                                              │
│  • Create Workspace                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Unity Catalog Module                                │
│                                                              │
│  1. Create Metastore                                        │
│     ↓                                                        │
│  2. Assign Metastore to Workspace ✅                        │
│     (This enables permission assignment APIs!)              │
│     ↓                                                        │
│  3. Assign Workspace Admin ✅                               │
│     (Now the APIs are available!)                           │
└─────────────────────────────────────────────────────────────┘
```

***REMOVED******REMOVED*** The Fix

***REMOVED******REMOVED******REMOVED*** File Changes

***REMOVED******REMOVED******REMOVED******REMOVED*** 1. Removed from `modules/databricks_workspace/main.tf`
```hcl
***REMOVED*** Removed (lines 125-141):
***REMOVED*** - data "databricks_user" "workspace_admin"
***REMOVED*** - resource "databricks_mws_permission_assignment" "workspace_admin"
```

***REMOVED******REMOVED******REMOVED******REMOVED*** 2. Added to `modules/unity_catalog/01-metastore.tf`
```hcl
***REMOVED*** After metastore assignment (lines 75-99):

data "databricks_user" "workspace_admin" {
  provider  = databricks.account
  user_name = var.workspace_admin_email
}

resource "databricks_mws_permission_assignment" "workspace_admin" {
  provider     = databricks.account
  workspace_id = var.workspace_id
  principal_id = data.databricks_user.workspace_admin.id
  permissions  = ["ADMIN"]

  depends_on = [databricks_metastore_assignment.workspace_assignment]
  ***REMOVED*** ☝️ THIS IS THE KEY: Wait for UC assignment before admin assignment

  lifecycle {
    ignore_changes = [principal_id]
  }
}
```

***REMOVED******REMOVED******REMOVED******REMOVED*** 3. Updated `main.tf`
```hcl
***REMOVED*** Updated Databricks provider version:
databricks = {
  source  = "databricks/databricks"
  version = "~> 1.50"  ***REMOVED*** Was: ~> 1.0
}
```

***REMOVED******REMOVED*** Why This Works

The `databricks_mws_permission_assignment` API is **only available after Unity Catalog is assigned** to a workspace. By moving the admin assignment to the Unity Catalog module and making it depend on the metastore assignment, we ensure:

1. ✅ Workspace is created
2. ✅ Unity Catalog metastore is assigned to the workspace
3. ✅ Permission assignment APIs become available
4. ✅ Workspace admin is assigned successfully

***REMOVED******REMOVED*** Deployment Commands

```bash
cd /Users/bhavin.kukadia/Downloads/0-projects/aws/modular-version

***REMOVED*** Upgrade to the new provider version
terraform init -upgrade

***REMOVED*** Review the changes
terraform plan

***REMOVED*** Apply the deployment
terraform apply
```

***REMOVED******REMOVED*** Key Takeaway

🔑 **The permission assignment APIs are enabled by Unity Catalog assignment, not by workspace creation alone.**

Always ensure Unity Catalog metastore is assigned to the workspace before attempting to use `databricks_mws_permission_assignment`.

