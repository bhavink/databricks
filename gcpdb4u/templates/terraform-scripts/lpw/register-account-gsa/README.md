# Register a workspace-creator GSA as an account admin (optional, out of band)

> **DISABLED by default.** The Terraform lives in `main.tf.disabled` so this config
> is inert and never runs. It is provided as a reference for end users who want to
> automate this step. To use it: `mv main.tf.disabled main.tf`, then follow "Run"
> below. We do not run it as part of the standard flow.

Automates the otherwise-manual step of adding a GSA to the Databricks account
console and granting it `account_admin`. A workspace-creator GSA must be an account
admin before it can create workspaces; this config does that in Terraform instead of
by hand.

## The chain

```
bootstrap admin GSA   ──(manual, once)──▶  account console + account_admin
      │
      │ (this config impersonates it)
      ▼
workspace-creator GSA(s)  ──▶  registered + account_admin
      │
      ▼
used by ../deploy.sh to create workspaces
```

One bootstrap GSA is added by hand once (nothing can grant the very first admin —
true chicken-and-egg). From then on, this config uses it to admit the other GSAs.

## Run

```bash
cd register-account-gsa
cp terraform.tfvars.example terraform.tfvars   # set account id, bootstrap GSA, target GSA(s)
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
terraform init && terraform apply
```

Idempotent: `force = true` adopts a GSA that already exists; re-run to add more.
Destroy **deactivates** the GSA users (`disable_as_user_deletion = true`), never
hard-deletes them.

## Where it fits

Optional precursor to workspace creation. If you use it, run it before the workspace
deploy so the creator GSA is admin-ready. If you'd rather add the GSA manually (a
one-off), skip this entirely — it changes nothing about the workspace config.

## ⚠️ Security

`account_admin` is the highest privilege in Databricks: full control of the entire
account (every workspace, billing, identities, network/security, audit). Granting it
to a workspace-creator GSA is a large blast radius and a standing escalation path if
that GSA's credentials leak. Use only if account-admin is genuinely required for your
creation flow; otherwise scope the GSA to workspace-level ADMIN (see `../groups.tf`).
