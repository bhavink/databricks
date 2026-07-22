#!/usr/bin/env bash
# lpw-demo4 — staged Databricks workspace deploy.
#
# Runs TWO applies in ONE invocation (you do NOT run this twice):
#   Apply 1: prereqs (roles, VPC/subnet, CMK) + workspace @ PROVISIONING + grants.
#            Terraform's dependency graph orders these automatically.
#   Apply 2: flip workspace to RUNNING (needs the compute-SA role bindings from 1).
#
# Why not one apply: creating the workspace straight at RUNNING deadlocks — RUNNING
# needs IAM roles on the compute SA, which doesn't exist until the create returns.
# PROVISIONING breaks the cycle.
set -euo pipefail

DRYRUN=false

usage() {
  cat <<'EOF'
Usage: ./deploy.sh [--dryrun] [-h|--help]

Deploys the Databricks workspace in ONE run (the two terraform applies happen
inside this script — you do NOT run it twice):

  Apply 1/2  prereqs (roles, VPC/subnet, CMK) + workspace @ PROVISIONING + grants
  Apply 2/2  flip the workspace to RUNNING

Options:
  --dryrun     Show what each stage WOULD do (terraform plan), change nothing.
  -h, --help   Show this help and exit.

Before running:
  1. cp terraform.tfvars.example terraform.tfvars   # fill in real values
  2. (out of band, once) apply identities/ and metastore/, then reference them
     in terraform.tfvars (workspace_groups, metastore_id)
  3. terraform init

Idempotent: if a stage fails, just re-run ./deploy.sh — completed work shows
"no changes" and it continues from the break.
EOF
}

case "${1:-}" in
  -h | --help)
    usage
    exit 0
    ;;
  --dryrun)
    DRYRUN=true
    ;;
  "") ;; # no args: real deploy
  *)
    echo "Unknown argument: $1" >&2
    usage
    exit 2
    ;;
esac

# ------------------------------------------------------------------
# Pre-flight: fail fast with a clear message if the basics are missing.
# ------------------------------------------------------------------
preflight() {
  local ok=true
  command -v terraform >/dev/null || { echo "  ! terraform not found on PATH" >&2; ok=false; }
  command -v gcloud    >/dev/null || { echo "  ! gcloud not found on PATH" >&2; ok=false; }
  [[ -f terraform.tfvars ]] || { echo "  ! terraform.tfvars missing (cp terraform.tfvars.example terraform.tfvars)" >&2; ok=false; }
  [[ -d .terraform ]]       || { echo "  ! not initialized (run: terraform init)" >&2; ok=false; }
  if ! $ok; then
    echo "Pre-flight checks failed. Fix the above and re-run ./deploy.sh." >&2
    exit 1
  fi
}

# ------------------------------------------------------------------
# Run one stage; on failure print which stage failed + a triage checklist.
# ------------------------------------------------------------------
run_stage() {
  local label="$1"; shift
  echo "==> $label"
  if ! "$@"; then
    cat >&2 <<EOF

########################################################################
FAILED: $label
########################################################################
The Terraform error is shown above. Common causes for this deploy:

  * Auth/token expired            -> re-run ./deploy.sh (refreshes the token)
  * "custom role already exists"  -> the lpw.databricks.* roles pre-exist;
                                     terraform import them, or delete the old ones
  * Prereqs not run               -> run ./prereqs.sh once as a project admin
                                     (APIs, service agents, deployer roles)
  * Workspace GSA "does not exist" -> IAM propagation lag; the time_sleep normally
                                     covers it, else just re-run ./deploy.sh
  * Shared VPC permission denied  -> grant compute.networkUser on the host
                                     project (see README "Shared VPC")
  * Account-admin 403             -> creator GSA must be a Databricks account
                                     admin first (see PREREQUISITES.md)
  * PSC forwarding-rule failed    -> wrong service attachment URI for the region,
                                     or psc_subnet_cidr overlaps (see README "PSC")

This script is idempotent: re-running continues from where it stopped.
########################################################################
EOF
    exit 1
  fi
}

preflight

# Databricks account API calls authenticate via a fresh GCP token.
export GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)"

if $DRYRUN; then
  echo "== DRY RUN — terraform plan only, no changes will be made =="
  run_stage "Plan 1/2: prereqs + workspace (PROVISIONING) + IAM grants" \
    terraform plan -var expected_workspace_status=PROVISIONING
  echo
  echo "NOTE: Plan 2/2 (flip to RUNNING) can only be planned accurately AFTER"
  echo "apply 1 exists — the workspace object it flips is created in stage 1."
  echo "Dry run complete. No changes made."
  exit 0
fi

run_stage "Apply 1/2: prereqs + workspace (PROVISIONING) + IAM grants" \
  terraform apply -auto-approve -var expected_workspace_status=PROVISIONING

run_stage "Apply 2/2: flip workspace to RUNNING" \
  terraform apply -auto-approve -var expected_workspace_status=RUNNING

echo "==> Done. Workspace is RUNNING."
terraform output
