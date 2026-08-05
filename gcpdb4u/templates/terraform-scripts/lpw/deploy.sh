#!/usr/bin/env bash
# lpw-demo4 — Databricks LPW workspace lifecycle wrapper.
#
# One entry point for deploy / destroy / inspect. Every command exports a fresh
# GCP token and passes the right -var so you never have to remember either.
#
# DEPLOY runs TWO applies in ONE invocation (you do NOT run deploy twice):
#   Apply 1: prereqs (roles, VPC/subnet, CMK) + workspace @ PROVISIONING + grants.
#            Terraform's dependency graph orders these automatically.
#   Apply 2: flip workspace to RUNNING (needs the compute-SA role bindings from 1).
#
# Why not one apply: creating the workspace straight at RUNNING deadlocks — RUNNING
# needs IAM roles on the compute SA, which doesn't exist until the create returns.
# PROVISIONING breaks the cycle.
set -euo pipefail

# expected_workspace_status for anything that touches an existing workspace
# (destroy/plan-running). A live workspace is RUNNING, so target that.
RUNNING_VAR=(-var expected_workspace_status=RUNNING)

usage() {
  cat <<'EOF'
Usage: ./deploy.sh [COMMAND] [options]

Commands:
  deploy            (default) Build the workspace: two applies, PROVISIONING then
                    RUNNING. Idempotent — safe to re-run; completed work shows
                    "no changes" and it continues from any break.
  destroy [--target ADDR] [--yes]
                    Tear down. Prompts for confirmation (destroy is irreversible).
                    --target ADDR  destroy just one resource (repeatable).
                    --yes          skip the confirmation prompt (for automation).
  state             List every resource in state (terraform state list).
  show [ADDR]       Show one resource's state (terraform state show ADDR).
                    No ADDR: lists resources + how to pick one.
  output            Print outputs (workspace URL + resource ids).
  plan              Dry run: terraform plan for apply 1 (PROVISIONING). No changes.
  plan-running      Dry run: terraform plan for apply 2 (RUNNING). Only accurate
                    AFTER a deploy exists (it plans the flip of a live workspace).

Options:
  --dryrun          Alias for `plan` (back-compat).
  -h, --help        Show this help and exit.

Before deploying:
  1. cp terraform.tfvars.example terraform.tfvars   # fill in real values
  2. (out of band, once) apply identities/ and metastore/, then reference them
     in terraform.tfvars (workspace_groups, metastore_id)
  3. terraform init

Every command exports GOOGLE_OAUTH_ACCESS_TOKEN from `gcloud auth print-access-token`
and passes the correct -var — raw `terraform` calls won't authenticate without it.
EOF
}

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

# Databricks account/workspace API calls authenticate via a fresh GCP token.
auth() { export GOOGLE_OAUTH_ACCESS_TOKEN="$(gcloud auth print-access-token)"; }

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

  * Auth/token expired            -> re-run the command (refreshes the token)
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

Deploy is idempotent: re-running continues from where it stopped.
########################################################################
EOF
    exit 1
  fi
}

# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------
cmd_deploy() {
  preflight; auth
  run_stage "Apply 1/2: prereqs + workspace (PROVISIONING) + IAM grants" \
    terraform apply -auto-approve -var expected_workspace_status=PROVISIONING
  run_stage "Apply 2/2: flip workspace to RUNNING" \
    terraform apply -auto-approve -var expected_workspace_status=RUNNING
  echo "==> Done. Workspace is RUNNING."
  terraform output
}

cmd_plan() {
  preflight; auth
  echo "== DRY RUN — terraform plan (PROVISIONING), no changes will be made =="
  run_stage "Plan 1/2: prereqs + workspace (PROVISIONING) + IAM grants" \
    terraform plan -var expected_workspace_status=PROVISIONING
  echo
  echo "NOTE: apply 2 (flip to RUNNING) can only be planned accurately AFTER"
  echo "apply 1 exists. Once deployed, use: ./deploy.sh plan-running"
  echo "Dry run complete. No changes made."
}

cmd_plan_running() {
  preflight; auth
  echo "== DRY RUN — terraform plan (RUNNING), no changes will be made =="
  run_stage "Plan 2/2: flip workspace to RUNNING" \
    terraform plan "${RUNNING_VAR[@]}"
  echo "Dry run complete. No changes made."
}

cmd_destroy() {
  local skip_confirm=false
  local targets=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --yes|-y)   skip_confirm=true; shift ;;
      --target)   targets+=(-target "$2"); shift 2 ;;
      --target=*) targets+=(-target "${1#*=}"); shift ;;
      *) echo "destroy: unknown option: $1" >&2; exit 2 ;;
    esac
  done
  preflight; auth

  if [[ ${#targets[@]} -gt 0 ]]; then
    echo "==> Selective destroy: ${targets[*]}"
  else
    echo "==> FULL destroy: every resource in this state will be torn down."
  fi

  if ! $skip_confirm; then
    read -r -p "Type 'yes' to proceed: " reply
    [[ "$reply" == "yes" ]] || { echo "Aborted."; exit 1; }
  fi

  # Expanding an empty array trips `set -u` on bash 3.2 (macOS stock bash),
  # so guard the expansion instead of inlining "${targets[@]}".
  run_stage "Destroy" \
    terraform destroy -auto-approve "${RUNNING_VAR[@]}" ${targets[@]+"${targets[@]}"}
  echo "==> Destroy complete."
}

cmd_state() {
  preflight
  terraform state list
}

cmd_show() {
  preflight
  if [[ $# -eq 0 ]]; then
    echo "Usage: ./deploy.sh show <resource-address>"
    echo "Resources currently in state:"
    terraform state list
    exit 0
  fi
  terraform state show "$1"
}

cmd_output() {
  preflight
  terraform output "$@"
}

# ------------------------------------------------------------------
# Dispatch
# ------------------------------------------------------------------
case "${1:-deploy}" in
  -h | --help)   usage; exit 0 ;;
  --dryrun|plan) cmd_plan ;;
  plan-running)  cmd_plan_running ;;
  deploy|"")     cmd_deploy ;;
  destroy)       shift; cmd_destroy "$@" ;;
  state)         cmd_state ;;
  show)          shift; cmd_show "$@" ;;
  output)        shift; cmd_output "$@" ;;
  *)
    echo "Unknown command: $1" >&2
    usage
    exit 2
    ;;
esac
