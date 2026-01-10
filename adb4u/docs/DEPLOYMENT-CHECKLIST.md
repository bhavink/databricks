# Deployment Checklist

**Purpose**: Pre-flight checklist to ensure successful deployment and prevent common issues.

Use this checklist **before** running `terraform apply` or `terraform destroy`.

---

## 📋 Pre-Deployment Checklist

### 1. Code Configuration

- [ ] **Metastore `force_destroy` is set to `true`**
  ```hcl
  # modules/unity-catalog/main.tf
  resource "databricks_metastore" "this" {
    force_destroy = true  # REQUIRED for clean destroy
  }
  ```

- [ ] **NSG rules are conditional for Private Link only**
  ```hcl
  # modules/networking/nsg-rules.tf
  resource "azurerm_network_security_rule" "example" {
    count = var.enable_private_link ? 1 : 0  # Only for PL
  }
  ```

- [ ] **Storage accounts use `default_action = "Allow"` initially**
  ```hcl
  # modules/unity-catalog/main.tf
  network_rules {
    default_action = "Allow"  # Required for container creation
  }
  ```

- [ ] **Tags are configured**
  ```hcl
  # deployments/non-pl/terraform.tfvars
  tag_owner     = "your-email@company.com"
  tag_keepuntil = "MM/DD/YYYY"
  ```

- [ ] **Random suffixes are enabled** (4-character)
  ```hcl
  # deployments/non-pl/main.tf
  resource "random_string" "deployment_suffix" {
    length = 4
  }
  ```

### 2. Environment Variables

- [ ] **Azure Authentication**
  ```bash
  export ARM_SUBSCRIPTION_ID="..."
  export ARM_TENANT_ID="..."
  # If using service principal:
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

### 3. Terraform Configuration

- [ ] **Terraform version >= 1.5**
  ```bash
  terraform version
  ```

- [ ] **Provider versions match**
  ```hcl
  # deployments/non-pl/versions.tf
  azurerm    ~> 3.100
  databricks ~> 1.40
  random     ~> 3.6
  ```

- [ ] **Backend configuration** (if using remote state)
  ```hcl
  terraform {
    backend "azurerm" {
      # ...
    }
  }
  ```

### 4. Variable Values

- [ ] **`terraform.tfvars` is populated**
  ```hcl
  # Required variables
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

### 5. Pre-Flight Validation

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
  # Review the plan carefully!
  ```

- [ ] **Check for warnings**
  - No deprecated features
  - No security warnings
  - Resource counts look reasonable

---

## 🗑️ Pre-Destroy Checklist

### 1. Confirm Intention

- [ ] **Data backup completed** (if needed)
  - Unity Catalog data exported
  - Notebooks backed up
  - Job definitions saved

- [ ] **Confirm metastore deletion** is acceptable
  - Metastore is account-level resource
  - May be shared across workspaces
  - May need to remain for other workspaces

### 2. Check Dependencies

- [ ] **No active compute clusters**
  ```bash
  # Check via Databricks UI or API
  databricks clusters list
  ```

- [ ] **No running jobs**
  ```bash
  databricks jobs list
  ```

- [ ] **External dependencies removed**
  - No external systems referencing workspace
  - Private endpoints in other VNets deleted

### 3. Destroy Sequence

- [ ] **Review destroy plan**
  ```bash
  terraform plan -destroy
  ```

- [ ] **If destroy fails with metastore error**:
  ```bash
  # Remove metastore from state (does not delete in Databricks)
  terraform state rm 'module.unity_catalog.databricks_metastore_data_access.this[0]'
  terraform state rm 'module.unity_catalog.databricks_metastore.this[0]'
  ```

- [ ] **If destroy fails with SEP error**:
  ```bash
  # Update subnets to remove SEP first
  terraform apply -target=module.networking.azurerm_subnet.public \
                  -target=module.networking.azurerm_subnet.private \
                  -auto-approve
  ```

- [ ] **Execute destroy**
  ```bash
  terraform destroy -auto-approve
  ```

### 4. Post-Destroy Cleanup

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
  # Only if metastore should be deleted
  databricks metastores delete --metastore-id <id> --account-id <account-id>
  ```

---

## ⚠️ Common Mistakes to Avoid

### Code Configuration Mistakes

❌ **Setting `force_destroy = false` or not setting it at all**
```hcl
# DON'T DO THIS
resource "databricks_metastore" "this" {
  force_destroy = false  # ❌ Will block destroy
}
```

✅ **Always use `force_destroy = true`**
```hcl
# DO THIS
resource "databricks_metastore" "this" {
  force_destroy = true  # ✅ Allows clean destroy
}
```

---

❌ **Adding `lifecycle.ignore_changes` for `force_destroy`**
```hcl
# DON'T DO THIS
resource "databricks_metastore" "this" {
  force_destroy = true
  lifecycle {
    ignore_changes = [force_destroy]  # ❌ Prevents destroy
  }
}
```

✅ **No lifecycle ignore for force_destroy**
```hcl
# DO THIS
resource "databricks_metastore" "this" {
  force_destroy = true  # ✅ No lifecycle block
}
```

---

❌ **Creating NSG rules for Non-PL deployments**
```hcl
# DON'T DO THIS
resource "azurerm_network_security_rule" "example" {
  # This will conflict with Databricks auto-created rules
}
```

✅ **Conditional NSG rules for Private Link only**
```hcl
# DO THIS
resource "azurerm_network_security_rule" "example" {
  count = var.enable_private_link ? 1 : 0  # ✅ Only for PL
}
```

---

❌ **Storage account with `default_action = "Deny"` initially**
```hcl
# DON'T DO THIS
resource "azurerm_storage_account" "example" {
  network_rules {
    default_action = "Deny"  # ❌ Blocks container creation
  }
}
```

✅ **Allow initial access for container creation**
```hcl
# DO THIS
resource "azurerm_storage_account" "example" {
  network_rules {
    default_action = "Allow"  # ✅ Required initially
  }
}
```

---

### Environment Mistakes

❌ **Missing `DATABRICKS_AZURE_TENANT_ID`**
```bash
# DON'T FORGET THIS
export DATABRICKS_AZURE_TENANT_ID="..."  # ❌ Often forgotten
```

✅ **Always export tenant ID**
```bash
# DO THIS
export DATABRICKS_AZURE_TENANT_ID="$ARM_TENANT_ID"  # ✅ Required
```

---

❌ **Running destroy without checking metastore usage**
```bash
# DON'T DO THIS
terraform destroy -auto-approve  # ❌ May delete shared metastore
```

✅ **Check metastore dependencies first**
```bash
# DO THIS
databricks metastores get --metastore-id <id> --account-id <account-id>
# Check if used by other workspaces
terraform destroy -auto-approve
```

---

## 🎯 Success Criteria

### Deployment Success

✅ All resources created without errors
✅ Workspace accessible at returned URL
✅ Unity Catalog metastore assigned
✅ External location created and accessible
✅ Tags applied to all resources
✅ Random suffixes prevent naming conflicts

### Destroy Success

✅ All Azure resources deleted
✅ No orphaned resources remain
✅ Terraform state is clean
✅ (Optional) Metastore deleted if intended

---

## 📞 Need Help?

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

**Document Version**: 1.0  
**Last Updated**: 2026-01-10  
**Next Review**: Before each major deployment
