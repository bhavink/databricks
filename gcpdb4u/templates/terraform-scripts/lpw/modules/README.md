# Modules

## `prereqs/`

Prerequisite infrastructure that must exist before the Databricks workspace is
created. Called once from the root as `module.prereqs` (see `../cmk.tf`).

**Active** (`main.tf`, `network.tf`):
- KMS key ring + crypto key
- CMK `cryptoKeyEncrypterDecrypter` grant to the GCP-managed service agents
- Workspace subnet under the existing VPC + intra-subnet firewall rule

**Commented reference** (managed OUTSIDE this config, kept for documentation):
- `iam-roles.tf` — the `lpw.databricks.*.role.v2` custom roles
- `account-admin.tf` — bootstrap note: the workspace-creator GSA must be a
  Databricks account admin before Terraform can create the workspace

Outputs consumed by the root: `crypto_key_id`, `subnet_name`, `subnet_id`.

Groups are defined inline in the root (`../groups.tf` + `../groups.yaml`), not as
a module.
