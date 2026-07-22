#!/usr/bin/env bash
# ==================================================================
# lpw-demo4 PREREQ BOOTSTRAP — run ONCE by a PROJECT ADMIN before deploy.sh.
#
# This is the repeatable, foolproof setup for everything Terraform CANNOT do
# itself (chicken-and-egg: the deploy runs AS the creator GSA, so the GSA's own
# enablement must exist first). Every step here was discovered the hard way and
# is now captured so the next deploy is one clean run.
#
# What it does, in order:
#   1. Enable required Google APIs on the project.
#   2. Create the GCP-managed service agents (KMS/GCS/Compute) the CMK grants need.
#   3. Grant the deployer GSA the PREDEFINED roles needed to build the infra.
#      (Predefined, not a custom role: PSC + private-DNS perms such as
#       compute.forwardingRules.pscCreate and dns.networks.bindPrivateDNSZone are
#       NOT grantable via custom roles — gcloud silently drops them. Predefined
#       roles include them and are stable across GCP changes.)
#   4. Grant the terraform-runner identity impersonation on the deployer GSA.
#
# NOT done here (must be done manually, see PREREQUISITES.md):
#   - Make the deployer GSA a DATABRICKS account admin (Databricks console/API).
#
# Usage:
#   PROJECT_ID=my-gcp-project \
#   DEPLOYER_GSA=deployer-sa@my-gcp-project.iam.gserviceaccount.com \
#   RUNNER=user:you@example.com \        # who runs terraform (impersonates DEPLOYER_GSA)
#   ./prereqs.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?set PROJECT_ID (the workspace GCP project)}"
DEPLOYER_GSA="${DEPLOYER_GSA:?set DEPLOYER_GSA (the SA Terraform impersonates)}"
RUNNER="${RUNNER:-}"   # optional: member (user:.../serviceAccount:...) that runs terraform

# ---- 1. APIs -----------------------------------------------------
echo "==> 1/4 Enabling required APIs on ${PROJECT_ID}"
gcloud services enable \
  compute.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  cloudresourcemanager.googleapis.com \
  serviceusage.googleapis.com \
  cloudkms.googleapis.com \
  dns.googleapis.com \
  storage.googleapis.com \
  --project="${PROJECT_ID}"

# ---- 2. Service agents ------------------------------------------
# CMK grants reference the GCS + Compute service agents, which don't exist until
# first "touched". Create them explicitly so the CMK IAM bindings don't 400.
echo "==> 2/4 Creating GCP-managed service agents"
gcloud storage service-agent --project="${PROJECT_ID}" >/dev/null || true
gcloud beta services identity create --service=compute.googleapis.com --project="${PROJECT_ID}" >/dev/null || true
# KMS agent (harmless if it already exists):
gcloud beta services identity create --service=cloudkms.googleapis.com --project="${PROJECT_ID}" >/dev/null || true

# ---- 3. Deployer GSA project roles (PREDEFINED) -----------------
# These cover: VPC/subnet/firewall/route/addresses/PSC forwarding rules, KMS,
# DNS (incl private-zone bind), custom-role management, SA creation, project IAM.
echo "==> 3/4 Granting predefined roles to ${DEPLOYER_GSA}"
DEPLOYER_ROLES=(
  roles/compute.networkAdmin          # VPC, subnet, firewall, route, addresses, PSC forwarding rules
  roles/compute.securityAdmin         # firewall rules (belt-and-suspenders with networkAdmin)
  roles/cloudkms.admin                # KMS key ring/key + setIamPolicy
  roles/dns.admin                     # DNS managed zones, records, private-zone VPC bind
  roles/iam.roleAdmin                 # create/update the 3 LPW custom roles
  roles/iam.serviceAccountAdmin       # create the databricks-compute SA
  roles/resourcemanager.projectIamAdmin # project-level role bindings
  roles/serviceusage.serviceUsageConsumer # read/verify enabled services
)
for R in "${DEPLOYER_ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${DEPLOYER_GSA}" --role="$R" --condition=None >/dev/null
  echo "    + $R"
done

# ---- 4. Impersonation for the terraform runner ------------------
if [[ -n "${RUNNER}" ]]; then
  echo "==> 4/4 Granting ${RUNNER} tokenCreator on ${DEPLOYER_GSA}"
  gcloud iam service-accounts add-iam-policy-binding "${DEPLOYER_GSA}" \
    --member="${RUNNER}" \
    --role="roles/iam.serviceAccountTokenCreator" >/dev/null
else
  echo "==> 4/4 SKIPPED (no RUNNER set) — grant tokenCreator manually if needed:"
  echo "    gcloud iam service-accounts add-iam-policy-binding ${DEPLOYER_GSA} \\"
  echo "      --member='user:YOU@example.com' --role='roles/iam.serviceAccountTokenCreator'"
fi

cat <<EOF

==> GCP prereqs done. REMAINING MANUAL STEP (not automatable here):
    Make ${DEPLOYER_GSA} a DATABRICKS ACCOUNT ADMIN in the account console/API
    (register it as a USER principal, not a service principal — GCP GSAs do not
    federate to Databricks SPs). See PREREQUISITES.md.

    Then: export GOOGLE_OAUTH_ACCESS_TOKEN=\$(gcloud auth print-access-token)
          ./deploy.sh
EOF
