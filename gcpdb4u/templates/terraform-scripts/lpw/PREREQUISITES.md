# Prerequisites — lpw-demo4

Everything Terraform **cannot** do itself, in order. Terraform runs *as* the
deployer GSA, so the GSA's own enablement must exist first (chicken-and-egg).
`prereqs.sh` automates steps 1–4; step 5 is a manual Databricks step.

> Status: the deploy path (prereqs → identities → metastore → workspace) has been
> run successfully, and every permission/API/agent below was discovered by running
> it. A fully clean first-run from an untouched project has not been re-verified end
> to end — expect the permission list here to be complete, but treat a brand-new
> project as the real acceptance test.

Run `prereqs.sh` **once per project**, as a **project admin** (not as the deployer
GSA — it lacks the rights to grant itself these).

```bash
PROJECT_ID=<workspace-project> \
DEPLOYER_GSA=<sa-terraform-impersonates> \
RUNNER=user:<who-runs-terraform> \
./prereqs.sh
```

## 1. Enable APIs

`compute`, `iam`, `iamcredentials`, `cloudresourcemanager`, `serviceusage`,
`cloudkms`, `dns`, `storage`.

*Why:* KMS/DNS/Storage were disabled and failed the deploy. Enabling propagates in
a few minutes — a KMS "API not used yet" error right after enabling is lag, not a
real failure; re-running clears it.

## 2. Create GCP-managed service agents

`storage`, `compute`, `cloudkms` service agents.

*Why:* the CMK IAM bindings grant `cryptoKeyEncrypterDecrypter` to the GCS and
Compute service agents. Those agents don't exist until first "touched", so the
grant 400s with *"service account …@gs-project-accounts… does not exist"*. Creating
them explicitly fixes it.

## 3. Deployer GSA — PREDEFINED roles (NOT a custom role)

| Role | Covers |
|---|---|
| `roles/compute.networkAdmin` | VPC, subnet, firewall, route, addresses, **PSC forwarding rules** |
| `roles/compute.securityAdmin` | firewall rules |
| `roles/cloudkms.admin` | KMS key ring/key + setIamPolicy |
| `roles/dns.admin` | DNS zones, records, **private-zone VPC bind** |
| `roles/iam.roleAdmin` | create/update the 3 LPW custom roles |
| `roles/iam.serviceAccountAdmin` | create the databricks-compute SA |
| `roles/resourcemanager.projectIamAdmin` | project-level role bindings |
| `roles/serviceusage.serviceUsageConsumer` | read/verify enabled services |

**Why predefined and not a hand-curated custom role:** two permissions the deploy
needs — `compute.forwardingRules.pscCreate` (PSC endpoints) and
`dns.networks.bindPrivateDNSZone` (private DNS zone) — are **NOT grantable via
custom roles**. `gcloud iam roles update` accepts them but *silently drops* them, so
the deploy keeps 403-ing no matter how many times you add them. Predefined roles
include these perms and are stable across GCP changes. This ends the whack-a-mole.

## 4. Impersonation for the terraform runner

Grant the runner identity `roles/iam.serviceAccountTokenCreator` on the deployer GSA.

*Why:* the `databricks` and `google` providers impersonate the deployer GSA
(`gcloud ... --impersonate-service-account` / provider `google_service_account`).
Without tokenCreator, impersonation fails on the first call.

## 5. MANUAL — Databricks account admin (not automatable here)

Make the deployer GSA a **Databricks account admin**, registered as a **USER
principal, not a service principal** (GCP GSAs do not federate to Databricks SPs).
Do this in the Databricks account console or via API.

*Why:* the Databricks provider creates the workspace/network/CMK/PAS/NCC objects via
the account API; the impersonated GSA must hold account_admin or those calls 403.

*Optional automation:* if you have one bootstrap GSA that is already an account
admin, you can register + grant account_admin to the deployer GSA(s) with Terraform
instead of by hand — see `register-account-gsa/`. The very first bootstrap admin
still has to be added manually once (nothing can grant the first admin).

---

## After prereqs — full deploy order

These are separate configs with separate state; do them in order the first time:

```bash
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)

# 6. Account identities (groups/users/GSAs) — once, shared across workspaces.
#    NOTE: "admins"/"users" are reserved built-in names; use custom names.
cd identities && terraform init && terraform apply && cd ..

# 7. Regional metastore — once per region. Reuse if one already exists (import),
#    else create it. (metastore/ is the tool.) Note its name/id for the workspace.
#    cd metastore && terraform init && terraform apply && cd ..

# 8. The workspace. Reference the above in terraform.tfvars:
#      workspace_groups = { platform_admins = "ADMIN", ... }
#      metastore_name   = "<regional-metastore-name>"
terraform init
./deploy.sh            # two applies: PROVISIONING -> RUNNING
```

## What Terraform still manages (NOT prereqs)

The 3 **LPW least-privilege roles** (`lpw.databricks.{project,resource,network}
.role.v2`) bound to the **workspace compute SA** — these are the LPW design itself
and stay in `modules/prereqs/iam-roles.tf`. Do not confuse them with the deployer
GSA's roles above: the deployer *builds* the infra; the compute SA *runs* the
workspace with least privilege.
