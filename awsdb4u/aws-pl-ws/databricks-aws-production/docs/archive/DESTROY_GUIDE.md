# Terraform Destroy Guide

> **Related Documentation:**
> - 🚀 [QUICK_START.md](QUICK_START.md) - Quick deployment reference
> - 📐 [ARCHITECTURE.md](../ARCHITECTURE.md) - Understand what resources are created
> - 📁 [DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md) - See all modules that will be destroyed

This guide helps you safely destroy your Databricks Private Link infrastructure without encountering dependency issues.

## The Problem

When destroying Databricks infrastructure, you may encounter errors like:
- `The subnet has dependencies and cannot be deleted`
- `The security group is associated with network interfaces`
- `VPC has dependencies and cannot be deleted`
- `Network interface is currently in use`

**Root Cause**: Databricks may launch cluster nodes (EC2 instances) that create ENIs (Elastic Network Interfaces) in your subnets, even after you've deleted the workspace in Terraform. These resources are **not tracked by Terraform** and must be manually cleaned up before Terraform can destroy networking resources.

---

## Solution Options

### Option 1: Automated Pre-Destroy Script (Recommended)

If you have a pre-destroy cleanup script, use it to automatically clean up Databricks-managed resources:

```bash
cd /path/to/modular-version3

# Run pre-destroy cleanup (if available)
./scripts/pre-destroy.sh --profile your-aws-profile --region us-west-2

# Then destroy
terraform destroy
```

The script would:
1. ✅ Find all EC2 instances in your VPC
2. ✅ Terminate running Databricks cluster nodes
3. ✅ Wait for termination to complete
4. ✅ Delete unattached ENIs
5. ✅ Ensure clean state for Terraform destroy

**Note:** If you don't have the pre-destroy script, proceed to Option 2 for manual cleanup.

---

### Option 2: Manual Cleanup (If Script Fails)

#### Step 1: Find Resources in Your VPC

```bash
# Get VPC ID from Terraform
VPC_ID=$(terraform output -raw vpc_id)

# OR get it from AWS
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=*databricks*" \
  --query 'Vpcs[0].VpcId' \
  --output text \
  --profile your-profile \
  --region your-region)

echo "VPC ID: $VPC_ID"
```

#### Step 2: Terminate EC2 Instances

```bash
# Find running instances
aws ec2 describe-instances \
  --filters "Name=vpc-id,Values=$VPC_ID" \
            "Name=instance-state-name,Values=running,pending,stopping,stopped" \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name]' \
  --output table \
  --profile your-profile \
  --region your-region

# Terminate all instances
INSTANCE_IDS=$(aws ec2 describe-instances \
  --filters "Name=vpc-id,Values=$VPC_ID" \
            "Name=instance-state-name,Values=running,pending,stopping,stopped" \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text \
  --profile your-profile \
  --region your-region)

if [ -n "$INSTANCE_IDS" ]; then
  aws ec2 terminate-instances \
    --instance-ids $INSTANCE_IDS \
    --profile your-profile \
    --region your-region
  
  # Wait for termination
  aws ec2 wait instance-terminated \
    --instance-ids $INSTANCE_IDS \
    --profile your-profile \
    --region your-region
fi
```

#### Step 3: Delete Unattached ENIs

```bash
# Find unattached ENIs
aws ec2 describe-network-interfaces \
  --filters "Name=vpc-id,Values=$VPC_ID" \
            "Name=status,Values=available" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Description]' \
  --output table \
  --profile your-profile \
  --region your-region

# Delete them
ENI_IDS=$(aws ec2 describe-network-interfaces \
  --filters "Name=vpc-id,Values=$VPC_ID" \
            "Name=status,Values=available" \
  --query 'NetworkInterfaces[*].NetworkInterfaceId' \
  --output text \
  --profile your-profile \
  --region your-region)

for ENI in $ENI_IDS; do
  echo "Deleting ENI: $ENI"
  aws ec2 delete-network-interface \
    --network-interface-id $ENI \
    --profile your-profile \
    --region your-region
done
```

#### Step 4: Run Terraform Destroy

```bash
terraform destroy
```

---

### Option 3: Force Remove from Terraform State

If AWS resources are already deleted but Terraform state is stuck:

```bash
# Remove specific resources from state
terraform state rm aws_subnet.private[0]
terraform state rm aws_subnet.private[1]
terraform state rm aws_security_group.workspace_sg
terraform state rm aws_vpc.databricks_vpc

# Then manually delete in AWS Console or CLI
```

---

## Prevention: Best Practices

### 1. Destroy in Reverse Order (Targeted Destroy)

Always destroy Databricks resources before AWS infrastructure:

```bash
# Step 1: Destroy user assignment (workspace admin)
terraform destroy -target=module.user_assignment

# Step 2: Destroy Unity Catalog resources
terraform destroy -target=module.unity_catalog

# Step 3: Destroy Databricks workspace
terraform destroy -target=module.databricks_workspace

# Step 4: Destroy AWS infrastructure (storage, IAM, networking)
terraform destroy
```

**Why this order?**
- User assignment depends on Unity Catalog
- Unity Catalog depends on workspace
- Workspace depends on networking/storage/IAM
- See [DEPLOYMENT_ORDER_FIX.md](DEPLOYMENT_ORDER_FIX.md) for dependency details

### 2. Disable Workspace Before Destroying

In the Databricks account console:
1. Go to **Workspaces**
2. Find your workspace
3. Click **...** → **Disable**
4. Wait for all clusters to terminate
5. Then run `terraform destroy`

### 3. Check for Running Clusters

Before destroying, verify no clusters are running:

```bash
# Via Databricks CLI (if configured)
databricks clusters list --profile your-databricks-profile

# Via AWS
aws ec2 describe-instances \
  --filters "Name=vpc-id,Values=$VPC_ID" \
            "Name=instance-state-name,Values=running" \
  --profile your-aws-profile \
  --region your-region
```

---

## Common Errors and Solutions

### Error: "Network interface is currently in use"

**Solution**: The ENI is attached to a running EC2 instance. Terminate the instance first.

```bash
# Find what the ENI is attached to
aws ec2 describe-network-interfaces \
  --network-interface-ids eni-xxxxxxxxx \
  --query 'NetworkInterfaces[0].Attachment.InstanceId'

# Terminate that instance
aws ec2 terminate-instances --instance-ids i-xxxxxxxxx
```

### Error: "Subnet has dependencies"

**Solution**: There are ENIs or instances still in the subnet.

```bash
# Find ENIs in the subnet
aws ec2 describe-network-interfaces \
  --filters "Name=subnet-id,Values=subnet-xxxxxxxxx" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Status,Description]' \
  --output table
```

### Error: "Security group is in use"

**Solution**: Security group is attached to running instances or ENIs.

```bash
# Find what's using the security group
aws ec2 describe-network-interfaces \
  --filters "Name=group-id,Values=sg-xxxxxxxxx" \
  --query 'NetworkInterfaces[*].[NetworkInterfaceId,Description]' \
  --output table
```

### Error: "Cannot delete external location" (Unity Catalog)

**Error Message:**
```
Error: cannot delete external location: Cannot delete external location (name = dbx-xxxx-external-location)
because the location has 1 dependent managed tables. You may use force option to delete it but the
managed storage data under this location cannot be purged by Unity Catalog anymore
```

**Root Cause**: External location has dependent managed tables, schemas, or volumes.

**Solution**: The code now includes `force_destroy = true` on all external locations. If you're using older code, update:

**Files to Check:**
- `modules/unity_catalog/02-root-storage.tf`
- `modules/unity_catalog/03-external-storage.tf`

**Add this parameter:**
```hcl
resource "databricks_external_location" "external_location" {
  # ... other parameters ...
  force_destroy = true  # Allow deletion even with dependent tables
}
```

Then apply the change before destroying:
```bash
terraform apply -target=module.unity_catalog.databricks_external_location.external_location
terraform apply -target=module.unity_catalog.databricks_external_location.root_storage
terraform destroy
```

**Important Notes:**
- This only removes the Unity Catalog registration, not the S3 data
- S3 data deletion is controlled by S3 bucket `force_destroy` setting (separate)
- Safe for dev/test environments, use with caution in production

### Error: "Cannot resolve ec2.us-west-2.amazonaws.com"

**Solution**: DNS/network connectivity issue.

```bash
# Check DNS
nslookup ec2.us-west-2.amazonaws.com

# Check AWS connectivity
aws sts get-caller-identity

# Check if VPN/proxy is blocking
ping 8.8.8.8
```

---

## Complete Cleanup Workflow

Here's the complete step-by-step process:

```bash
# 1. Navigate to project
cd /path/to/modular-version3

# 2. Get VPC ID (for verification later)
VPC_ID=$(terraform output -raw vpc_id)

# 3. Optional: Run pre-destroy script (if available)
# ./scripts/pre-destroy.sh --profile your-aws-profile --region us-west-2

# 4. Destroy in reverse dependency order
terraform destroy -target=module.user_assignment
terraform destroy -target=module.unity_catalog
terraform destroy -target=module.databricks_workspace
terraform destroy  # Destroys remaining: KMS, IAM, storage, networking

# 5. Verify cleanup (should return "VPC not found")
aws ec2 describe-vpcs --vpc-ids $VPC_ID --profile your-aws-profile --region your-region
```

**Resources Destroyed (in order):**
1. User assignment (workspace admin permissions)
2. Unity Catalog (metastore, catalogs, external locations)
3. Databricks workspace (MWS resources, workspace)
4. KMS keys (if encryption enabled)
5. IAM roles and policies
6. S3 buckets (with `force_destroy = true`)
7. Networking (VPC endpoints, security groups, NAT gateways, subnets, VPC)

---

## Troubleshooting Tips

1. **Always check Terraform output first**: `terraform output`
2. **Use AWS Console**: Visual interface can help identify stuck resources
3. **Enable debug logging**: `export TF_LOG=DEBUG` before running terraform
4. **Check CloudTrail**: See what API calls are being made
5. **Wait between steps**: AWS eventual consistency can cause timing issues

---

## Need Help?

If you continue to have issues:

1. Check AWS Console → VPC → Your VPC → Resource Map
2. Look for any remaining resources attached to your VPC
3. Delete them manually in this order:
   - EC2 Instances
   - Network Interfaces
   - NAT Gateways
   - Internet Gateways
   - Subnets
   - Security Groups
   - VPC

---

**Last Updated**: 2025-12-22

