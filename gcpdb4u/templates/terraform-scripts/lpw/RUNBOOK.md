# RUNBOOK — deploy the workspace

Run these in order, top to bottom. Details: README.md.

## 0. Once per GCP project (a project admin does this)
```bash
./prereqs.sh                       # enables APIs, service agents, deployer-GSA roles
```
Then, in the Databricks **account console**, make your deployer GSA an **account
admin** (add it as a *user*, not a service principal). This is the only click-op.

## 1. Once per account — create groups
```bash
cd identities
cp terraform.tfvars.example terraform.tfvars
#   OPEN terraform.tfvars and set EVERY value in it (the example lists them all)
#   edit groups.yaml if you want different groups (don't name any "admins"/"users")
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
terraform init && terraform apply
cd ..
```

## 2. Metastore — get its name
Use your existing regional metastore's name, or create one: `cd metastore` and follow
`metastore/README.md`. You just need the **name** for the next step.

## 3. Deploy the workspace
```bash
cp terraform.tfvars.example terraform.tfvars
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
terraform init
./deploy.sh
```
**Before `./deploy.sh`: open `terraform.tfvars` and set EVERY value.** The example
file is the checklist — required values (account id, project id/number, region, GSA
email, VPC + subnet names) are uncommented; optional ones are commented with their
defaults. For this run also set:
- `workspace_groups = { platform_admins = "ADMIN", data_engineers = "USER" }`
- `metastore_name   = "<name from step 2>"`

Optional (all default off/lean, toggle in `terraform.tfvars`):
- `enable_ip_access_list = true` — restrict workspace access by IP. Put your ranges
  in `ip_access_list.yaml` first, and include your own egress IP or you lock
  yourself out. Applied automatically **after** the workspace is RUNNING (apply 2).
- `enable_network_policy = true` — restrict serverless egress (anti-exfil). Off =
  the workspace uses the account `default-policy` (open). When on, creates a per-ws
  RESTRICTED policy from `network_policy.yaml`, in `DRY_RUN` (logs only) until you
  flip to `ENFORCED`. Read the README "Serverless egress control" section first —
  turning it back OFF has an update-only lifecycle gotcha (rebind to `default-policy`
  before deleting the custom policy).

Wait for `Done. Workspace is RUNNING.` Your workspace URL prints at the end.

## 3b. Prefer raw Terraform (no deploy.sh)?
`deploy.sh` just runs two applies. To do it by hand (after editing `terraform.tfvars`):
```bash
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
terraform init
terraform apply -var expected_workspace_status=PROVISIONING   # apply 1: build everything, workspace bare
terraform apply -var expected_workspace_status=RUNNING        # apply 2: attach network/CMK/PSC/NCC/metastore
terraform output                                              # workspace URL + ids
```
Both applies are required, in this order — the workspace can't be created straight to
RUNNING. Re-running either is safe. (Full detail: README.md "Deploy without deploy.sh".)

## If something fails
Re-run the same command — it's safe and resumes. A `403` means a missing GCP
permission: add it to `prereqs.sh`, re-run step 0, then retry.
