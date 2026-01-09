***REMOVED*** 05 - Troubleshooting & Common Issues

> **Problem Solver**: Quick fixes for common deployment issues.

---

***REMOVED******REMOVED*** Quick Issue Lookup

```
🔍 Use Ctrl+F to find your error message
```

| Category | Jump To |
|----------|---------|
| Prerequisites | [Setup Issues](***REMOVED***1-setup-issues) |
| Terraform Errors | [Terraform Issues](***REMOVED***2-terraform-issues) |
| AWS Errors | [AWS Issues](***REMOVED***3-aws-issues) |
| Databricks Errors | [Databricks Issues](***REMOVED***4-databricks-issues) |
| KMS/Encryption | [Encryption Issues](***REMOVED***5-encryption-issues) |
| Destroy Problems | [Destroy Issues](***REMOVED***6-destroy-issues) |

---

***REMOVED******REMOVED*** 1. Setup Issues

***REMOVED******REMOVED******REMOVED*** Issue: `terraform: command not found`

**Solution**:
```bash
***REMOVED*** Install Terraform
brew install terraform  ***REMOVED*** macOS
***REMOVED*** or download from https://terraform.io
```

**Docs**: [Install Terraform](00-PREREQUISITES.md***REMOVED***31-install-terraform)

***REMOVED******REMOVED******REMOVED*** Issue: `Unable to locate credentials`

**Solution**:
```bash
***REMOVED*** Check AWS credentials
aws sts get-caller-identity --profile your-profile

***REMOVED*** If fails, configure:
aws configure --profile your-profile
***REMOVED*** or
aws sso login --profile your-profile
```

**Docs**: [AWS Auth](00-PREREQUISITES.md***REMOVED***22-aws-authentication-setup)

***REMOVED******REMOVED******REMOVED*** Issue: Environment variables not set

**Symptom**: Terraform asks for `databricks_client_id` input

**Solution**:
```bash
***REMOVED*** Check variables
echo $TF_VAR_databricks_client_id

***REMOVED*** If empty, set in ~/.zshrc:
export TF_VAR_databricks_client_id="your-id"
export TF_VAR_databricks_client_secret="your-secret"

***REMOVED*** Reload
source ~/.zshrc
```

**Docs**: [Environment Setup](00-PREREQUISITES.md***REMOVED***41-terraform-provider-authentication)

---

***REMOVED******REMOVED*** 2. Terraform Issues

***REMOVED******REMOVED******REMOVED*** Issue: `Error: Missing required argument`

**Full Error**:
```
Error: Missing required argument
  on main.tf line 50, in module "databricks_workspace":
  50: module "databricks_workspace" {

The argument "databricks_client_id" is required, but no definition was found.
```

**Solution**: Set environment variables (see issue above)

***REMOVED******REMOVED******REMOVED*** Issue: `Error: Unsupported argument`

**Full Error**:
```
Error: Unsupported argument
  on modules/unity_catalog/variables.tf line 42:
  42:   client_id = var.databricks_client_id

An argument named "client_id" is not expected here.
```

**Cause**: Variable name mismatch after refactoring

**Solution**:
```bash
***REMOVED*** Pull latest code
git pull

***REMOVED*** Re-initialize
terraform init -upgrade
```

***REMOVED******REMOVED******REMOVED*** Issue: `Error: Invalid reference in variable validation`

**Full Error**:
```
Error: Invalid reference in variable validation
The condition for variable "existing_workspace_cmk_key_alias" can only refer to the variable itself
```

**Cause**: Cross-variable validation not supported

**Solution**: Validation moved to module logic (fixed in current version)

---

***REMOVED******REMOVED*** 3. AWS Issues

***REMOVED******REMOVED******REMOVED*** Issue: S3 bucket already exists

**Full Error**:
```
Error: creating S3 Bucket (mycompany-dbx-root): BucketAlreadyExists
```

**Solution**:
```hcl
***REMOVED*** Change bucket names in terraform.tfvars
root_storage_bucket_name = "mycompany-dbx-root-v2"
***REMOVED*** or add different prefix
```

**Tip**: Random suffix is added automatically, but base name must be unique

***REMOVED******REMOVED******REMOVED*** Issue: `MalformedPolicyDocumentException: Policy contains invalid principals`

**Full Error**:
```
Error: creating KMS Key: MalformedPolicyDocumentException: Policy contains a statement with one or more invalid principals
```

**Cause**: Circular dependency - KMS key policy references IAM role before it exists

**Solution**: Fixed in current version (modules reordered: IAM → KMS → Storage)

**Details**: [KMS Unity Catalog Fix](KMS_UNITY_CATALOG_FIX.md)

***REMOVED******REMOVED******REMOVED*** Issue: VPC endpoint service name not found

**Full Error**:
```
Error: InvalidServiceName: The Vpc Endpoint Service 'com.amazonaws.vpce.us-west-1.vpce-svc-xxxxx' does not exist
```

**Solution**: VPC endpoint service names are region-specific and auto-detected

**Supported Regions**:
- us-east-1, us-east-2, us-west-1, us-west-2
- eu-west-1, eu-central-1, ap-southeast-1, ap-south-1

**Manual Override** (if needed):
```hcl
workspace_vpce_service = "com.amazonaws.vpce.us-west-1.vpce-svc-actual-id"
relay_vpce_service     = "com.amazonaws.vpce.us-west-1.vpce-svc-actual-id"
```

---

***REMOVED******REMOVED*** 4. Databricks Issues

***REMOVED******REMOVED******REMOVED*** Issue: Cannot create external location - KMS permissions

**Full Error**:
```
Error: cannot create external location: AWS IAM role does not have WRITE, DELETE permissions on url s3://...
User: arn:aws:sts::account:assumed-role/dbx-catalog-xxx/databricks is not authorized to perform: kms:GenerateDataKey
```

**Cause**: Unity Catalog role missing KMS permissions when `enable_encryption=true`

**Solution**: Fixed in current version - KMS policies automatically added

**IAM Propagation**: If still fails, wait 60 seconds and retry:
```bash
terraform apply
***REMOVED*** Wait appears in plan, policy created but not propagated yet
```

**Details**: [KMS Fix Documentation](KMS_UNITY_CATALOG_FIX.md)

***REMOVED******REMOVED******REMOVED*** Issue: 401 Unauthorized from Databricks API

**Full Error**:
```
Error: cannot authenticate Databricks account: 401 Unauthorized
```

**Solution**:
```bash
***REMOVED*** Verify Service Principal credentials
echo $TF_VAR_databricks_client_id
echo $TF_VAR_databricks_account_id

***REMOVED*** Test authentication
curl -X GET \
  -u "$TF_VAR_databricks_client_id:$TF_VAR_databricks_client_secret" \
  https://accounts.cloud.databricks.com/api/2.0/accounts/$TF_VAR_databricks_account_id/workspaces
```

**Check**: Service Principal has Account Admin role

***REMOVED******REMOVED******REMOVED*** Issue: Cannot access workspace after deployment

**Symptom**: Workspace URL loads but can't create clusters

**Solution**: **Wait 20 minutes** for Private Link backend stabilization

**Why?**: Databricks provisions backend infrastructure after workspace creation

**Verify**:
```bash
***REMOVED*** Check workspace status
terraform output workspace_status
***REMOVED*** Should show: RUNNING
```

---

***REMOVED******REMOVED*** 5. Encryption Issues

***REMOVED******REMOVED******REMOVED*** Issue: `enable_encryption` vs `enable_workspace_cmk` confusion

**Question**: Which encryption should I use?

**Answer**: They are **independent** encryption layers:

```
Layer 1 - S3 Bucket Encryption (enable_encryption):
├── Encrypts: S3 buckets (DBFS, UC metastore, UC external)
├── Use for: Data at rest in S3
└── Cost: KMS key charges

Layer 2 - Workspace CMK (enable_workspace_cmk):
├── Encrypts: DBFS root, EBS volumes, Managed Services
├── Use for: Workspace-level encryption
└── Cost: KMS key charges

You can enable:
- Neither (AWS-managed encryption)
- One or the other
- Both simultaneously ✅
```

**Docs**: [Encryption Layers](03-NETWORK-ENCRYPTION.md***REMOVED***3-encryption-layers)

***REMOVED******REMOVED******REMOVED*** Issue: Key rotation concerns

**Question**: How does key rotation work?

**Answer**:
```
AWS Automatic Rotation (enabled by default):
✅ Rotates key material annually
✅ ARN stays the same
✅ No action required
✅ Applies to both encryption layers

Manual Rotation to Different Key:
✅ Managed Services CMK: Supported
❌ Storage CMK: NOT supported (only auto-rotation)
✅ S3 Bucket keys: Update bucket config
```

**Databricks Docs**: [Key Rotation](https://docs.databricks.com/aws/en/security/keys/configure-customer-managed-keys***REMOVED***rotate-an-existing-key)

---

***REMOVED******REMOVED*** 6. Destroy Issues

***REMOVED******REMOVED******REMOVED*** Issue: Subnet/VPC cannot be deleted - has dependencies

**Full Error**:
```
Error: deleting subnet: DependencyViolation: The subnet has dependencies and cannot be deleted
Error: deleting VPC: DependencyViolation: The vpc has dependencies and cannot be deleted
```

**Cause**: Databricks launched cluster nodes (EC2) that created ENIs (network interfaces) not tracked by Terraform

**Solution**:

**Step 1**: Find VPC ID
```bash
VPC_ID=$(terraform output -raw vpc_id)
```

**Step 2**: Terminate EC2 instances
```bash
***REMOVED*** Find instances
aws ec2 describe-instances \
  --filters "Name=vpc-id,Values=$VPC_ID" \
            "Name=instance-state-name,Values=running" \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name]' \
  --output table

***REMOVED*** Terminate
INSTANCE_IDS=$(aws ec2 describe-instances \
  --filters "Name=vpc-id,Values=$VPC_ID" \
            "Name=instance-state-name,Values=running,stopped" \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text)

aws ec2 terminate-instances --instance-ids $INSTANCE_IDS

***REMOVED*** Wait
aws ec2 wait instance-terminated --instance-ids $INSTANCE_IDS
```

**Step 3**: Delete unattached ENIs
```bash
ENI_IDS=$(aws ec2 describe-network-interfaces \
  --filters "Name=vpc-id,Values=$VPC_ID" \
            "Name=status,Values=available" \
  --query 'NetworkInterfaces[*].NetworkInterfaceId' \
  --output text)

for ENI in $ENI_IDS; do
  aws ec2 delete-network-interface --network-interface-id $ENI
done
```

**Step 4**: Retry destroy
```bash
terraform destroy
```

---

***REMOVED******REMOVED*** 7. Module-Specific Issues

***REMOVED******REMOVED******REMOVED*** Issue: User assignment fails with "resource not found"

**Full Error**:
```
Error: cannot create permission assignment: resource not found
```

**Cause**: User assignment runs before Unity Catalog resources are ready

**Solution**: Fixed in current version - `depends_on` added

**Workaround** (if needed):
```bash
***REMOVED*** Create everything except user assignment
terraform apply -target=module.unity_catalog

***REMOVED*** Then create user assignment
terraform apply
```

***REMOVED******REMOVED******REMOVED*** Issue: Metastore already exists

**Symptom**: Want to use existing metastore instead of creating new one

**Solution**:
```hcl
***REMOVED*** In terraform.tfvars
metastore_id = "your-existing-metastore-id"
```

This skips metastore creation, only assigns workspace to existing metastore

---

***REMOVED******REMOVED*** 8. Performance Issues

***REMOVED******REMOVED******REMOVED*** Issue: Terraform apply is slow

**Symptom**: Deployment takes > 30 minutes

**Expected Time**:
- Normal: 15-20 minutes
- With Private Link: 18-22 minutes
- First run (provider download): +2 minutes

**Check for**:
1. IAM propagation waits (60s each - expected)
2. VPC endpoint creation (5-10 min - expected)
3. Workspace provisioning (5-7 min - expected)

**Not Normal**:
- Stuck on "Still creating..." for > 10 minutes on one resource
- Solution: Check AWS console for actual resource status

---

***REMOVED******REMOVED*** 9. Validation Errors

***REMOVED******REMOVED******REMOVED*** Issue: VPC CIDR validation fails

**Full Error**:
```
Error: Invalid value for variable "vpc_cidr": VPC CIDR overlaps with Databricks reserved range
```

**Reserved CIDRs** (avoid these):
```
❌ 127.187.216.0/24  (Databricks internal)
❌ 192.168.216.0/24  (Databricks internal)
❌ 198.18.216.0/24   (Databricks internal)
❌ 172.17.0.0/16     (Docker default)
```

**Solution**:
```hcl
***REMOVED*** Use different CIDR
vpc_cidr = "10.0.0.0/22"  ***REMOVED*** ✅ Good
vpc_cidr = "172.16.0.0/16" ***REMOVED*** ✅ Good
vpc_cidr = "192.168.0.0/16" ***REMOVED*** ✅ Good (avoid .216 subnet)
```

---

***REMOVED******REMOVED*** 10. Getting More Help

***REMOVED******REMOVED******REMOVED*** Enable Terraform Debug Logging

```bash
export TF_LOG=DEBUG
export TF_LOG_PATH=terraform-debug.log
terraform apply
```

***REMOVED******REMOVED******REMOVED*** Check AWS CloudTrail

```bash
***REMOVED*** Recent API calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateVpc \
  --max-results 10
```

***REMOVED******REMOVED******REMOVED*** Databricks Support

1. Get workspace ID: `terraform output workspace_id`
2. Get deployment logs: `cat terraform-debug.log`
3. Contact: [Databricks Support](https://help.databricks.com)

***REMOVED******REMOVED******REMOVED*** Community Resources

- [Databricks Community](https://community.databricks.com/)
- [Terraform Databricks Provider Issues](https://github.com/databricks/terraform-provider-databricks/issues)

---

***REMOVED******REMOVED*** Common Error Patterns

| Error Pattern | Typical Cause | Solution |
|---------------|---------------|----------|
| `403 Forbidden` | IAM permissions | Check AWS/Databricks service principal permissions |
| `404 Not Found` | Resource doesn't exist | Check resource IDs, region |
| `401 Unauthorized` | Auth failure | Verify credentials, environment variables |
| `400 Bad Request` | Invalid parameter | Check terraform.tfvars values |
| `409 Conflict` | Resource already exists | Change names or import existing |
| `DependencyViolation` | Resource in use | Clean up dependencies first |
| `InvalidParameter` | Wrong value | Check AWS/Databricks API documentation |

---

**Still Stuck?** Open an issue with:
1. Terraform version: `terraform version`
2. Error message (full)
3. Relevant `terraform.tfvars` (redact secrets!)
4. Deployment logs

**Docs**: [All Documentation](00-PREREQUISITES.md)
