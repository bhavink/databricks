# Regional Unity Catalog metastore — one-time, out of band

A metastore is a **regional, account-level** construct shared by **all** workspaces
in that region. It is kept **separate** from the per-workspace config (`../`) with
its **own Terraform state**, because:

- It is created **once per region**, not once per workspace.
- If it lived in the workspace config, every workspace deploy would fight to own it,
  and destroying one demo workspace could delete the metastore for the whole region.

## First: does a metastore already exist for the region?

Only **one** metastore is allowed per region. Check the account console (Catalog >
Metastores) or the account API first.

- **None exists** → `apply` (below) creates it.
- **One already exists** → do **NOT** apply (it would error/duplicate). Either just
  use it as-is, or import it into this state to manage it here:

  ```bash
  terraform import databricks_metastore.this <metastore-id>
  ```

## Create (only if none exists)

```bash
cd metastore/
cp terraform.tfvars.example terraform.tfvars   # fill in values
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
terraform init
terraform apply
```

The impersonated GSA must be a **Databricks account admin** (same prereq as the
workspace deploy — see ../PREREQUISITES.md).

## Auto-assign new workspaces (MANUAL — not in Terraform)

The setting that makes a metastore the **default for its region** so **new**
workspaces attach automatically is **not exposed by the Terraform provider**. Set it
**once** via the account console or REST API:

- **Console:** Account console > Catalog / Metastores > the regional metastore >
  enable "automatically assign new workspaces in this region."
- **REST API:** account-level metastore-assignment default endpoint (see the
  Databricks account API docs for your provider version).

This config can assign **specific existing** workspaces (`assign_workspace_ids`), but
"all future workspaces" is the account-level default-assignment setting above.

## Relationship to the workspace deploy

The workspace config (`../`) does **not** touch the metastore. Order:

1. Run this once per region (or confirm the metastore already exists + auto-assign on).
2. Deploy workspaces (`../deploy.sh`). With auto-assign enabled, each new workspace
   attaches to the regional metastore on creation — no per-workspace assignment step.
