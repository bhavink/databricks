***REMOVED***!/bin/bash
***REMOVED*** =============================================================================
***REMOVED*** Pre-Destroy Script - Cleanup Databricks Resources
***REMOVED*** =============================================================================
***REMOVED*** This script ensures all Databricks-managed resources are terminated before
***REMOVED*** running terraform destroy to prevent dependency issues.
***REMOVED***
***REMOVED*** Usage: ./scripts/pre-destroy.sh [--profile PROFILE] [--region REGION]
***REMOVED*** =============================================================================

set -e

***REMOVED*** Default values
PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-us-west-2}"
VPC_ID=""

***REMOVED*** Parse arguments
while [[ $***REMOVED*** -gt 0 ]]; do
  case $1 in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --vpc-id)
      VPC_ID="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "================================================"
echo "Pre-Destroy Cleanup Script"
echo "================================================"
echo "Profile: $PROFILE"
echo "Region:  $REGION"
echo ""

***REMOVED*** Get VPC ID from Terraform state if not provided
if [ -z "$VPC_ID" ]; then
  echo "Getting VPC ID from Terraform state..."
  VPC_ID=$(terraform output -raw vpc_id 2>/dev/null || echo "")
  
  if [ -z "$VPC_ID" ]; then
    echo "⚠️  Could not find VPC ID. Searching for VPCs with databricks tags..."
    VPC_ID=$(aws ec2 describe-vpcs \
      --filters "Name=tag:Name,Values=*databricks*" \
      --profile "$PROFILE" \
      --region "$REGION" \
      --query 'Vpcs[0].VpcId' \
      --output text 2>/dev/null || echo "")
  fi
fi

if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "None" ]; then
  echo "✅ No VPC found. Nothing to clean up."
  exit 0
fi

echo "VPC ID: $VPC_ID"
echo ""

***REMOVED*** =============================================================================
***REMOVED*** Step 1: Terminate all EC2 instances in the VPC
***REMOVED*** =============================================================================
echo "🔍 Checking for EC2 instances in VPC..."
INSTANCE_IDS=$(aws ec2 describe-instances \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=instance-state-name,Values=running,pending,stopping,stopped" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text)

if [ -n "$INSTANCE_IDS" ]; then
  echo "🛑 Terminating EC2 instances: $INSTANCE_IDS"
  aws ec2 terminate-instances \
    --instance-ids $INSTANCE_IDS \
    --profile "$PROFILE" \
    --region "$REGION" > /dev/null
  
  echo "⏳ Waiting for instances to terminate..."
  aws ec2 wait instance-terminated \
    --instance-ids $INSTANCE_IDS \
    --profile "$PROFILE" \
    --region "$REGION"
  echo "✅ All instances terminated"
else
  echo "✅ No running EC2 instances found"
fi

echo ""

***REMOVED*** =============================================================================
***REMOVED*** Step 2: Delete all unattached ENIs in the VPC
***REMOVED*** =============================================================================
echo "🔍 Checking for network interfaces in VPC..."
ENI_IDS=$(aws ec2 describe-network-interfaces \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=status,Values=available" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --query 'NetworkInterfaces[*].NetworkInterfaceId' \
  --output text)

if [ -n "$ENI_IDS" ]; then
  echo "🗑️  Deleting unattached network interfaces..."
  for ENI in $ENI_IDS; do
    echo "   Deleting ENI: $ENI"
    aws ec2 delete-network-interface \
      --network-interface-id "$ENI" \
      --profile "$PROFILE" \
      --region "$REGION" 2>/dev/null || echo "   ⚠️  Failed to delete $ENI (may be in use)"
  done
  echo "✅ Network interfaces cleaned up"
else
  echo "✅ No unattached network interfaces found"
fi

echo ""

***REMOVED*** =============================================================================
***REMOVED*** Step 3: Wait a few seconds for AWS to propagate changes
***REMOVED*** =============================================================================
echo "⏳ Waiting for AWS to propagate changes (5 seconds)..."
sleep 5

echo ""
echo "================================================"
echo "✅ Pre-destroy cleanup complete!"
echo "================================================"
echo ""
echo "You can now safely run: terraform destroy"
echo ""

