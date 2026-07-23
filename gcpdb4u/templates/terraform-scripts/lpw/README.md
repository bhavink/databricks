# lpw-demo4 — Databricks GCP workspace (clean reference deployment)

Least-privilege Databricks workspace on GCP with CMK, IAM role grants, and
account-level groups. Greenfield layout: prereq primitives live in
`modules/prereqs`, so they can be applied first.

> **In a hurry? Read [RUNBOOK.md](RUNBOOK.md)** — the whole deploy in under 50 lines.
> This README is the full walkthrough.

## Layout

```
providers.tf   variables.tf   workspace.tf   deploy.sh
prereqs.tf     iam-grants.tf  groups.tf (assigns EXISTING groups; see identities/)
dns.tf         (PSC DNS, post-workspace; only when enable_private_access = true)
ip-access-list.tf + ip_access_list.yaml   (IP ACLs; only when enable_ip_access_list = true)
network-policy.tf + network_policy.yaml   (serverless egress; only when enable_network_policy = true)
prereqs.sh     one-time GCP bootstrap (APIs, agents, deployer roles) — see PREREQUISITES.md
PREREQUISITES.md  the full prereq checklist
modules/
  prereqs/   main.tf            CMK keyring/key + service-agent grants (active)
             network.tf         VPC (optional) + subnet + firewall (active)
             iam-roles.tf       3 LPW roles for the workspace COMPUTE SA (active)
             service-account.tf databricks-compute SA + monitoring.viewer (active)
             psc.tf             PSC subnet + IPs + endpoints (enable_private_access)
             routes.tf          default IGW route (enable_private_access + create_vpc)
             account-admin.tf   commented reference (bootstrap done out of band)
identities/    standalone, own-state TF for account groups/users/GSAs (shared, out of band)
metastore/     standalone, own-state TF to create a regional UC metastore (one-time)
register-account-gsa/  standalone reference TF to register + admin a creator GSA (DISABLED; opt-in)
```

**Separate configs, separate states.** Account-level, shared resources are NOT owned
by the per-workspace flow (they outlive any single workspace):
- `identities/` — account groups, users, GSAs, memberships. Created once.
- `metastore/` — regional Unity Catalog metastore. Created once per region.
- `register-account-gsa/` — optional, **disabled by default** reference: register a
  workspace-creator GSA in the account console + grant account_admin (automates a
  manual precursor). Enable only if you choose to use it.
- root (this dir) — the workspace itself; it only **references** the above
  (assigns existing groups, binds to an existing metastore).

## Created by this config

- **Custom IAM roles** (`modules/prereqs/iam-roles.tf`): the three
  `lpw.databricks.*.role.v2` roles, bound to the workspace compute SA by
  `iam-grants.tf`. (These are for the *compute SA*. The identity that RUNS Terraform
  gets predefined roles out of band — see [PREREQUISITES.md](PREREQUISITES.md).)
- **CMK** (`prereqs.tf` + `modules/prereqs/main.tf`): KMS key ring + crypto key,
  service-agent grants, and the `databricks_mws_customer_managed_keys` config. The
  workspace uses it for **both** `storage` and `managed_services` (encryption is
  actually applied, not just provisioned). Attached only at RUNNING.
- **NCC** (`workspace.tf`), only when `enable_ncc = true`: a
  `databricks_mws_network_connectivity_config` (regional, stable egress / private
  connectivity for serverless), attached to the workspace only at RUNNING.
- **Workspace subnet** with Private Google Access, under the VPC.
- **The VPC itself**, when `create_vpc = true` (**default true**; set false to use existing).
- **Databricks-compute service account** (`modules/prereqs/service-account.tf`):
  `databricks-compute@<project>`, the default SA for clusters with no custom SA.
  Bare-minimum privilege: `roles/monitoring.viewer` (read-only metrics). No cost.
- **PSC endpoints** (`modules/prereqs/psc.tf`) + **PSC DNS** (`dns.tf`), only when
  `enable_private_access = true` — see the PSC section below.

## Prerequisites (outside this config)

**See [PREREQUISITES.md](PREREQUISITES.md) for the full checklist.** Everything
Terraform cannot do itself is automated by `prereqs.sh`, run **once** by a project
admin before the first deploy:

```bash
PROJECT_ID=<workspace-project> \
DEPLOYER_GSA=<sa-terraform-impersonates> \
RUNNER=user:<who-runs-terraform> \
./prereqs.sh
```

In short, it: (1) enables the required APIs, (2) creates the GCP service agents the
CMK grants need, (3) grants the deployer GSA the **predefined** roles to build the
infra, (4) grants the runner impersonation on that GSA. One manual step it can't do:
make the deployer GSA a **Databricks account admin** (console/API).

**Why predefined roles, not a custom role:** the deploy needs
`compute.forwardingRules.pscCreate` (PSC endpoints) and
`dns.networks.bindPrivateDNSZone` (private DNS zone), which **cannot be granted via
custom roles** — gcloud silently drops them. Predefined roles
(`compute.networkAdmin`, `cloudkms.admin`, `dns.admin`, `iam.roleAdmin`,
`iam.serviceAccountAdmin`, `resourcemanager.projectIamAdmin`) include them. This is
the deployer identity; do not confuse it with the 3 LPW least-privilege roles this
config grants to the workspace **compute SA**.

Also: unless `create_vpc = false`, the VPC is created by this config (default
`true`). With `false`, `google_vpc_id` must already exist.

## VPC: non-shared (default) vs Shared VPC

The default deployment is **non-shared VPC**: leave `google_shared_vpc_project`
unset and the subnet, firewall, workspace network, and subnet-level IAM grant are
all created in `google_project_id`. Nothing extra to do.

**Shared VPC** is opt-in — set `google_shared_vpc_project` to the host project.
The same four resources then target the host project instead. A single local drives
this: `vpc_project_id = google_shared_vpc_project != "" ? google_shared_vpc_project : google_project_id`.

If you use Shared VPC, these **host-project prerequisites must exist first** (this
config does NOT manage them — they are host-project-admin operations):

- The workspace project (`google_project_id`) is attached to the host project as a
  **service project**.
- The impersonated creator GSA has permission to create the subnet/firewall in the
  host project (e.g. `roles/compute.networkAdmin` on the host project).
- The Databricks compute service account (`gcp_workspace_sa`) has
  `roles/compute.networkUser` on the subnet in the host project, in addition to the
  `lpw.databricks.network.role.v2` grant this config applies.

Without these, the shared-VPC apply will fail on the subnet/firewall create or the
workspace will fail to provision. Non-shared VPC has none of these requirements.

## Private Access Settings (PSC) — on by default

`enable_private_access` defaults to **true**, so the full PSC path is built. Set it
to `false` for a standard public workspace with no PSC resources.

With it on, a `databricks_mws_private_access_settings` object is created and attached
to the workspace. Like the CMK/NCC attachments, PAS is attached **only at RUNNING**
(apply 2), never at PROVISIONING.

The PAS shape is controlled by two variables that **default to the LPW-safe posture**:
`public_access_enabled = true` (hybrid: public + PSC) and `private_access_level =
"ACCOUNT"`. Both are overridable, but flipping `public_access_enabled = false` with no
working PSC endpoints registered will **lock you out** of the workspace — change it
only deliberately, after the private path is verified.

### What `enable_private_access = true` builds

**Pre-workspace (in `module.prereqs`, `psc.tf` + `routes.tf`):**

- A dedicated **PSC endpoint subnet** (`psc_subnet_cidr`, default `10.1.255.0/26`,
  separate from the workspace subnet).
- Two **internal IPs** — one for the workspace (plproxy) endpoint, one for the SCC
  relay (ngrok) endpoint.
- Two **PSC consumer endpoints** (forwarding rules) targeting the Databricks
  service attachments. Defaults are **us-central1**
  (`workspace_service_attachment`, `relay_service_attachment`); override for other
  regions using the values at the docs link above.
- A **default internet-gateway route**, only when `create_vpc = true` (an existing
  VPC already has one).

**Databricks-side registration (`workspace.tf`):**

- Two `databricks_mws_vpc_endpoint` resources registering the forwarding rules with
  Databricks, bound into the network's `vpc_endpoints` block (back-end PSC). See
  below.

**Post-workspace (root `dns.tf`):**

- A private **DNS zone for `gcp.databricks.com`** bound to the VPC, with A records:
  - `<workspace-host>` -> plproxy endpoint IP (front-end)
  - `dp-<workspace-host>` -> plproxy endpoint IP (back-end / data plane)
  - `tunnel.<region>.gcp.databricks.com` -> ngrok relay endpoint IP
  - `<region>.psc-auth.gcp.databricks.com` -> plproxy endpoint IP (front-end PSC auth)

  These live in the root (not the module) because they need the workspace URL,
  which only exists after the workspace object is created.

### Region

Service-attachment defaults are **us-central1**. For another region, override
`workspace_service_attachment` and `relay_service_attachment` with that region's URIs
from the docs link above, and set `google_region` accordingly.

### Back-end PSC: `databricks_mws_vpc_endpoint`

When `enable_private_access = true`, this config also registers the two GCP
forwarding rules with Databricks as `databricks_mws_vpc_endpoint` resources
(`workspace_vpce`, `relay_vpce`) and binds them into the network's `vpc_endpoints`
block (`rest_api` = workspace/plproxy, `dataplane_relay` = SCC relay/ngrok). This is
the back-end PSC path — required on GCP for the workspace to use the private
endpoints, not just the front-end DNS.

## NCC (`enable_ncc`) — bare config only on GCP

`enable_ncc = true` creates a `databricks_mws_network_connectivity_config` and
attaches it at RUNNING. It does **not** add NCC private endpoint rules: the
`databricks_mws_ncc_private_endpoint_rule` resource only supports Azure and AWS
today — it has no GCP fields. Serverless-PSC egress rules on GCP are a
console/API step, out of scope for this Terraform.

## IP access lists (`enable_ip_access_list`) — optional, default off

Set `enable_ip_access_list = true` to restrict workspace UI/API access by IP. Two
steps, handled automatically in order (`ip-access-list.tf`):
1. `databricks_workspace_conf` enables the feature (`enableIpAccessLists = true`).
2. `databricks_ip_access_list` applies each entry from `ip_access_list.yaml`.

Edit `ip_access_list.yaml` to set your entries (`<label>: {list_type: ALLOW|BLOCK,
ip_addresses: [...]}`). Default is **off** — no lists, no restriction.

⚠️ An **ALLOW** list restricts the workspace to the listed IPs only. Include your own
egress IP/CIDR or you will lock yourself out of the UI/API. These resources use the
workspace-level provider, so they apply once the workspace is RUNNING.

## Serverless egress control (`enable_network_policy`) — optional, default OFF

Restricts where **serverless** compute can egress, to guard against accidental data
exfiltration. **Off by default**: the workspace uses the account's built-in
`default-policy`, which is `FULL_ACCESS` (open egress). This is BYO-policy — opt in
only when you want restriction.

When `enable_network_policy = true`, this flow creates a **per-workspace**
`databricks_account_network_policy` (`RESTRICTED_ACCESS`) from `network_policy.yaml`
(allowed internet DNS names + GCS buckets) and binds the workspace to it via
`databricks_workspace_network_option`. Enforcement defaults to **`DRY_RUN`** (logs
violations, blocks nothing) — set `network_policy_enforcement_mode = "ENFORCED"` only
after you've confirmed the allow-list covers everything serverless needs. To bind an
existing **shared** policy instead of creating a per-workspace one, set
`shared_network_policy_id`.

Scope + defaults:
- **Serverless only** — classic compute egress is governed by the VPC/PSC/VPC-SC
  layer, not this.
- `default-policy` **exists automatically** in every account (Databricks-managed,
  cannot be deleted). A workspace with no explicit binding uses it — so "default off
  = do nothing" leaves the workspace on `default-policy`. No resource needed.
- Start in `DRY_RUN`. `RESTRICTED_ACCESS` + `ENFORCED` **will** break serverless jobs
  until the allow-list includes everything they reach (control plane, DBFS/GCS, PyPI).

### ⚠️ Lifecycle gotchas (learned the hard way)

`databricks_workspace_network_option` is **update-only** — every workspace always has
one (defaulting to `default-policy`). Consequences when tearing a custom policy down:

- **Deleting the binding resource does NOT revert the workspace to `default-policy`.**
  The workspace stays pinned to the custom policy on the backend. You must explicitly
  re-bind it to `default-policy` first (set `shared_network_policy_id = "default-policy"`
  and apply the binding), *then* remove the custom policy.
- **A custom policy cannot be deleted while any running workspace is still attached**
  — the API returns `attached to N running workspace(s)`. Detach (rebind to
  `default-policy`) before deleting. There is also brief propagation lag after
  detaching before the delete succeeds.
- To fully turn this off after using it: rebind to `default-policy`, confirm, then
  delete the custom policy (Terraform, or account console → Network policies).

## Setup

```bash
# 1. Variables
cp terraform.tfvars.example terraform.tfvars   # fill in real values

# 2. Identities + metastore (out of band, ONCE — see identities/ and metastore/).
#    Groups/users/GSAs are created in identities/; the metastore in metastore/.
#    Then reference them here via terraform.tfvars:
#      workspace_groups = { platform_admins = "ADMIN", data_engineers = "USER" }
#      metastore_name   = "<existing-regional-metastore-name>"

# 3. Auth + init
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
terraform init
```

## Deploy

```bash
./deploy.sh            # full deploy (see below)
./deploy.sh --dryrun   # terraform plan only — changes nothing
./deploy.sh --help     # usage
```

Run `./deploy.sh` **once** — it performs the two required applies in sequence
within the single run (you do not run it twice):

1. **Apply 1** — prereqs (custom roles, VPC/subnet, CMK, compute SA, PSC endpoints)
   + workspace at `PROVISIONING` + IAM role grants + groups. Terraform's dependency
   graph orders these in a single apply: prereqs → workspace object →
   `gcp_workspace_sa` → grants. The workspace is created **bare** — the LPW API
   rejects all cloud-resource-configuration IDs at creation, so none of the fields
   below are attached yet.
2. **Apply 2** — flips the workspace to `RUNNING`, the update step where all the
   config IDs attach: **network_id**, **CMK** (storage + managed_services), **PAS**
   (`enable_private_access`), and **NCC** (`enable_ncc`). Each is null during
   PROVISIONING and set only at RUNNING. If `metastore_id` is set, the workspace is
   also bound to that regional Unity Catalog metastore here.

**Unity Catalog:** set `metastore_id` to an existing regional metastore's ID to bind
this workspace to it (see `metastore/` for creating one out of band). Only one
metastore per region per account. Do **not** also enable account-level auto-assign
for the region — the explicit binding and auto-assign collide.

Two applies are required, not one: creating the workspace straight to `RUNNING`
deadlocks (RUNNING needs IAM roles on the compute SA, but that SA doesn't exist
until the workspace is created). Creating at `PROVISIONING` first breaks the cycle.

**Pre-flight:** the script checks for `terraform`/`gcloud`, `terraform.tfvars`,
and an initialized `.terraform/` before doing anything, and exits
with a clear message if something is missing.

**On failure:** the failing stage is named and a short triage checklist is printed
(the raw Terraform error is shown above it). `deploy.sh` is idempotent — re-run it;
completed work shows "no changes" and it continues from the break.

**`--dryrun` caveat:** it plans stage 1 only. Stage 2 ("flip to RUNNING") can't be
planned in a fresh environment because it acts on a workspace object that stage 1
hasn't created yet. For an already-deployed env, use `terraform plan` for full drift.

## Deploy without deploy.sh (raw Terraform)

`deploy.sh` is only a convenience wrapper around two `terraform apply` calls. If you
prefer to run Terraform directly (assuming `terraform`, `gcloud`, and auth are
already set up), the two stages are:

```bash
# Export a fresh token for the Databricks account API (deploy.sh does this for you).
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)

terraform init

# --- Apply 1: prereqs + workspace @ PROVISIONING + IAM grants + groups ---
terraform apply -var expected_workspace_status=PROVISIONING

# --- Apply 2: flip the workspace to RUNNING ---
terraform apply -var expected_workspace_status=RUNNING

terraform output
```

Notes:
- **Two applies are mandatory**, in this order, for the reason above (the RUNNING
  deadlock). Do not try to reach RUNNING in a single apply.
- **`expected_workspace_status` is passed with `-var`**, not set in
  `terraform.tfvars` — the deploy owns the phase, so the two don't conflict.
- Drop `-auto-approve` (shown omitted here) to review each plan before applying, or
  add it to match `deploy.sh`'s hands-off behavior.
- **Preview a stage** without changing anything:
  `terraform plan -var expected_workspace_status=PROVISIONING`.
- **Re-running is safe** — Terraform is idempotent; a completed stage re-plans to
  "no changes." If apply 1 succeeds but apply 2 is interrupted, just run apply 2
  again (or re-run both).
- **Targeting prereqs only** (optional): `terraform apply -target=module.prereqs`
  provisions just the roles/VPC/subnet/CMK. Not required — apply 1 already creates
  them first via the dependency graph.

## Changing groups / membership later

Group **membership** (who is in `platform_admins`, etc.) is managed in `identities/`
— edit `identities/groups.yaml` and re-apply there. It is account-level and shared,
so the change applies to every workspace referencing that group.

Which groups **this workspace** grants, and at what level, is `var.workspace_groups`
in this config's `terraform.tfvars` — edit it and re-run `./deploy.sh`.

## Gotchas / known behaviors

Lessons baked into this config (so you don't rediscover them):

- **Reserved group names.** `admins` and `users` are built-in Databricks groups; you
  cannot create groups with those names. Use distinct names (e.g. `platform_admins`)
  in `identities/groups.yaml` and `workspace_groups`.
- **Workspace GSA propagation lag.** The workspace emits its compute SA at creation,
  but GCP IAM is eventually consistent — binding roles immediately can 400 "service
  account does not exist." A `time_sleep.wait_for_workspace_gsa` (60s) gates **every**
  grant that references the GSA (project/resource/network roles *and* the CMK grant).
  If you add another GSA-referencing resource, wire it to that sleep too.
- **LPW rejects config IDs at creation.** `network_id`, CMK, PAS, NCC all attach only
  at RUNNING (apply 2), never at PROVISIONING — this is the LPW API contract.
- **Metastore is per-region, one per account.** Bind by `metastore_name` (region is
  validated at plan) or `metastore_id`. Don't also enable account-level auto-assign.
- **Your own admin user is protected.** In `identities/`, users use
  `disable_as_user_deletion = true`, so `terraform destroy` deactivates rather than
  hard-deletes a real account — you can't accidentally delete yourself.
- **Network policy binding is update-only.** `databricks_workspace_network_option`
  can't be created/destroyed, only updated — every workspace always has one
  (`default-policy` by default). Deleting the TF binding does NOT revert the workspace
  to `default-policy`, and a custom policy can't be deleted while a running workspace
  is still attached. To turn it off: rebind to `default-policy`
  (`shared_network_policy_id = "default-policy"`), then delete the custom policy. See
  "Serverless egress control" above. This is why it defaults OFF (BYO policy).
