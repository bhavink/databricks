#!/bin/bash
# Quick Destroy - One-liner cleanup and destroy
# Usage: ./quick-destroy.sh

set -e

PROFILE="${1:-cis-sandbox-admin}"
REGION="${2:-us-west-2}"

echo "🚀 Quick Destroy Script"
echo "Profile: $PROFILE"
echo "Region: $REGION"
echo ""

# Run pre-destroy cleanup if script exists
if [ -f "./scripts/pre-destroy.sh" ]; then
  echo "🧹 Running pre-destroy cleanup..."
  ./scripts/pre-destroy.sh --profile "$PROFILE" --region "$REGION"
else
  echo "⚠️  Pre-destroy script not found, attempting direct destroy..."
fi

echo ""
echo "🗑️  Destroying Terraform resources..."

# Destroy in order
terraform destroy -target=module.unity_catalog -auto-approve
terraform destroy -target=module.databricks_workspace -auto-approve  
terraform destroy -auto-approve

echo ""
echo "✅ Destroy complete!"

