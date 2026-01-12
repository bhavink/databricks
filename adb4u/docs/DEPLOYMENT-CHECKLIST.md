***REMOVED*** Deployment Checklist

**Purpose**: Pre-flight checklist to ensure successful deployment and prevent common issues.

Use this checklist **before** running `terraform apply` or `terraform destroy`.

---

***REMOVED******REMOVED*** 📋 Pre-Deployment Checklist

***REMOVED******REMOVED******REMOVED*** 1. Code Configuration

- [ ] **Metastore `force_destroy` is set to `true`**
  ```hcl
  ***REMOVED*** modules/unity-catalog/main.tf
  resource "databricks_metastore" "this" {
    force_destroy = true  ***REMOVED*** REQUIRED for clean destroy
  }
  ```

- [ ] **NSG rules are conditional for Private Link only**
  ```hcl
  ***REMOVED*** modules/networking/nsg-rules.tf
  resource "azurerm_network_security_rule" "example" {
    count = var.enable_private_link ? 1 : 0  ***REMOVED*** Only for PL
  }
  ```

- [ ] **Storage accounts use `default_action = "Allow"` initially**
  ```hcl
  ***REMOVED*** modules/unity-catalog/main.tf
  network_rules {
    default_action = "Allow"  ***REMOVED*** Required for container creation
  }
  ```

- [ ] **Tags are configured**
  ```hcl
  ***REMOVED*** deployments/non-pl/terraform.tfvars
  tag_owner     = "your-email@company.com"
  tag_keepuntil = "MM/DD/YYYY"
  ```

- [ ] **Random suffixes are enabled** (4-character)
  ```hcl
  ***REMOVED*** deployments/non-pl/main.tf
  resource "random_string" "deployment_suffix" {
    length = 4
  }
  ```

***REMOVED******REMOVED******REMOVED*** 2. Environment Variables

- [ ] **Azure Authentication**
  ```bash
  export ARM_SUBSCRIPTION_ID="..."
  export ARM_TENANT_ID="..."
  ***REMOVED*** If using service principal:
  export ARM_CLIENT_ID="..."
  export ARM_CLIENT_SECRET="..."
  ```

- [ ] **Databricks Authentication**
  ```bash
  export DATABRICKS_ACCOUNT_ID="..."
  export DATABRICKS_AZURE_TENANT_ID="$ARM_TENANT_ID"
  ```

- [ ] **Verify authentication**
  ```bash
  az account show
  echo $DATABRICKS_ACCOUNT_ID
  ```

***REMOVED******REMOVED******REMOVED*** 3. Terraform Configuration

- [ ] **Terraform version >= 1.5**
  ```bash
  terraform version
  ```

- [ ] **Provider versions match**
  ```hcl
  ***REMOVED*** deployments/non-pl/versions.tf
  azurerm    ~> 3.100
  databricks ~> 1.40
  random     ~> 3.6
  ```

- [ ] **Backend configuration** (if using remote state)
  ```hcl
  terraform {
    backend "azurerm" {
      ***REMOVED*** ...
    }
  }
  ```

***REMOVED******REMOVED******REMOVED*** 4. Variable Values

- [ ] **`terraform.tfvars` is populated**
  ```hcl
  ***REMOVED*** Required variables
  workspace_prefix    = "..."
  location           = "eastus2"
  databricks_account_id = "..."
  metastore_name     = "..."
  ```

- [ ] **Naming conventions follow Azure limits**
  - Storage account names: 3-24 characters, lowercase, alphanumeric only
  - Resource group names: Valid Azure naming
  - Workspace names: Valid Databricks naming

- [ ] **Region is supported**
  - Databricks available in region
  - Unity Catalog supported

***REMOVED******REMOVED******REMOVED*** 5. Pre-Flight Validation

- [ ] **Initialize Terraform**
  ```bash
  terraform init
  ```

- [ ] **Validate configuration**
  ```bash
  terraform validate
  ```

- [ ] **Review plan**
  ```bash
  terraform plan -out=tfplan
  ***REMOVED*** Review the plan carefully!
  ```

- [ ] **Check for warnings**
  - No deprecated features
  - No security warnings
  - Resource counts look reasonable

---

***REMOVED******REMOVED*** 🗑️ Pre-Destroy Checklist

***REMOVED******REMOVED******REMOVED*** 1. Confirm Intention

- [ ] **Data backup completed** (if needed)
  - Unity Catalog data exported
  - Notebooks backed up
  - Job definitions saved

- [ ] **Confirm metastore deletion** is acceptable
  - Metastore is account-level resource
  - May be shared across workspaces
  - May need to remain for other workspaces

***REMOVED******REMOVED******REMOVED*** 2. Check Dependencies

- [ ] **No active compute clusters**
  ```bash
  ***REMOVED*** Check via Databricks UI or API
  databricks clusters list
  ```

- [ ] **No running jobs**
  ```bash
  databricks jobs list
  ```

- [ ] **External dependencies removed**
  - No external systems referencing workspace
  - Private endpoints in other VNets deleted

***REMOVED******REMOVED******REMOVED*** 3. Destroy Sequence

- [ ] **Review destroy plan**
  ```bash
  terraform plan -destroy
  ```

- [ ] **If destroy fails with metastore error**:
  ```bash
  ***REMOVED*** Remove metastore from state (does not delete in Databricks)
  terraform state rm 'module.unity_catalog.databricks_metastore_data_access.this[0]'
  terraform state rm 'module.unity_catalog.databricks_metastore.this[0]'
  ```

- [ ] **If destroy fails with SEP error**:
  ```bash
  ***REMOVED*** Update subnets to remove SEP first
  terraform apply -target=module.networking.azurerm_subnet.public \
                  -target=module.networking.azurerm_subnet.private \
                  -auto-approve
  ```

- [ ] **Execute destroy**
  ```bash
  terraform destroy -auto-approve
  ```

***REMOVED******REMOVED******REMOVED*** 4. Post-Destroy Cleanup

- [ ] **Verify Azure resources deleted**
  ```bash
  az resource list --resource-group rg-databricks-prod-eastus2
  ```

- [ ] **Check for orphaned resources**
  - Managed resource group deleted
  - Private endpoints removed
  - Role assignments cleaned up

- [ ] **Metastore cleanup** (if needed)
  ```bash
  ***REMOVED*** Only if metastore should be deleted
  databricks metastores delete --metastore-id <id> --account-id <account-id>
  ```

---

***REMOVED******REMOVED*** ⚠️ Common Mistakes to Avoid

***REMOVED******REMOVED******REMOVED*** Code Configuration Mistakes

❌ **Setting `force_destroy = false` or not setting it at all**
```hcl
***REMOVED*** DON'T DO THIS
resource "databricks_metastore" "this" {
  force_destroy = false  ***REMOVED*** ❌ Will block destroy
}
```

✅ **Always use `force_destroy = true`**
```hcl
***REMOVED*** DO THIS
resource "databricks_metastore" "this" {
  force_destroy = true  ***REMOVED*** ✅ Allows clean destroy
}
```

---

❌ **Adding `lifecycle.ignore_changes` for `force_destroy`**
```hcl
***REMOVED*** DON'T DO THIS
resource "databricks_metastore" "this" {
  force_destroy = true
  lifecycle {
    ignore_changes = [force_destroy]  ***REMOVED*** ❌ Prevents destroy
  }
}
```

✅ **No lifecycle ignore for force_destroy**
```hcl
***REMOVED*** DO THIS
resource "databricks_metastore" "this" {
  force_destroy = true  ***REMOVED*** ✅ No lifecycle block
}
```

---

❌ **Creating NSG rules for Non-PL deployments**
```hcl
***REMOVED*** DON'T DO THIS
resource "azurerm_network_security_rule" "example" {
  ***REMOVED*** This will conflict with Databricks auto-created rules
}
```

✅ **Conditional NSG rules for Private Link only**
```hcl
***REMOVED*** DO THIS
resource "azurerm_network_security_rule" "example" {
  count = var.enable_private_link ? 1 : 0  ***REMOVED*** ✅ Only for PL
}
```

---

❌ **Storage account with `default_action = "Deny"` initially**
```hcl
***REMOVED*** DON'T DO THIS
resource "azurerm_storage_account" "example" {
  network_rules {
    default_action = "Deny"  ***REMOVED*** ❌ Blocks container creation
  }
}
```

✅ **Allow initial access for container creation**
```hcl
***REMOVED*** DO THIS
resource "azurerm_storage_account" "example" {
  network_rules {
    default_action = "Allow"  ***REMOVED*** ✅ Required initially
  }
}
```

---

***REMOVED******REMOVED******REMOVED*** Environment Mistakes

❌ **Missing `DATABRICKS_AZURE_TENANT_ID`**
```bash
***REMOVED*** DON'T FORGET THIS
export DATABRICKS_AZURE_TENANT_ID="..."  ***REMOVED*** ❌ Often forgotten
```

✅ **Always export tenant ID**
```bash
***REMOVED*** DO THIS
export DATABRICKS_AZURE_TENANT_ID="$ARM_TENANT_ID"  ***REMOVED*** ✅ Required
```

---

❌ **Running destroy without checking metastore usage**
```bash
***REMOVED*** DON'T DO THIS
terraform destroy -auto-approve  ***REMOVED*** ❌ May delete shared metastore
```

✅ **Check metastore dependencies first**
```bash
***REMOVED*** DO THIS
databricks metastores get --metastore-id <id> --account-id <account-id>
***REMOVED*** Check if used by other workspaces
terraform destroy -auto-approve
```

---

***REMOVED******REMOVED*** 🎯 Success Criteria

***REMOVED******REMOVED******REMOVED*** Deployment Success

✅ All resources created without errors  
✅ Workspace accessible at returned URL  
✅ Unity Catalog metastore assigned  
✅ External location created and accessible  
✅ **NCC attached to workspace** (serverless-ready)  
✅ Tags applied to all resources  
✅ Random suffixes prevent naming conflicts

**Verify NCC**:
```bash
terraform output ncc_id
***REMOVED*** Expected: ncc-<id>

terraform output ncc_name
***REMOVED*** Expected: <workspace-prefix>-ncc
```

***REMOVED******REMOVED******REMOVED*** Post-Deployment (Optional)

⏸️ **Enable Serverless Compute**:
- **Non-PL**: See [deployments/non-pl/docs/SERVERLESS-SETUP.md](../deployments/non-pl/docs/SERVERLESS-SETUP.md)
- **Full-Private**: See [deployments/full-private/docs/04-SERVERLESS-SETUP.md](../deployments/full-private/docs/04-SERVERLESS-SETUP.md)

***REMOVED******REMOVED******REMOVED*** Destroy Success

✅ All Azure resources deleted  
✅ No orphaned resources remain  
✅ Terraform state is clean  
✅ (Optional) Metastore deleted if intended  
✅ NCC binding removed (or kept for reuse)

---

***REMOVED******REMOVED*** 📞 Need Help?

If you encounter issues:

1. **Check [Troubleshooting Guide](./TROUBLESHOOTING.md)** first
2. Review this checklist for missed steps
3. Enable debug logging:
   ```bash
   export TF_LOG=DEBUG
   terraform apply 2>&1 | tee debug.log
   ```
4. Check checkpoint documents for similar issues
5. Contact your platform team

---

**Document Version**: 1.1  
**Last Updated**: 2026-01-12  
**Next Review**: Before each major deployment
