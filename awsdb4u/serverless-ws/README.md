# Serverless workspace (AWS)

A Databricks serverless workspace on AWS: no VPC, no cross-account IAM
role, no root bucket, no AWS provider. Compute runs in the Databricks
serverless compute plane; data lives in default storage, or in your own
buckets through Unity Catalog. A VPC of yours is needed only for a private
front-end (PrivateLink).

> **Maturity: validated.** `terraform validate` and mock-provider tests pass
> in CI. Not yet applied end to end.

```mermaid
flowchart LR
  U["Users and apps"] -->|"HTTPS, your IP ranges only"| W["Serverless workspace"]
  W -->|"runs on"| S["Serverless compute plane"]
  S -->|"enforced network policy: listed destinations only"| D["Allowed destinations"]
  S -->|"Unity Catalog"| C["Default storage or your buckets"]
```

## Use

Apply this root, then [`workspace-guardrails`](../workspace-guardrails) for
the bare minimum: IP access lists (your known ranges), an NCC, an enforced
serverless network policy, and the Unity Catalog metastore assignment.

```bash
# account-admin service principal (or: export DATABRICKS_CONFIG_PROFILE=<account-profile>)
export DATABRICKS_CLIENT_ID=<client-id> DATABRICKS_CLIENT_SECRET=<client-secret>
export TF_VAR_databricks_account_id=<account-id>
terraform init
terraform apply -var workspace_name=<workspace-name> -var region=<region>

cd ../workspace-guardrails   # edit ip_access_list.yaml and network_policy.yaml first
terraform init
terraform apply \
  -var region=<region> \
  -var metastore_id=<metastore-id> \
  -var "workspace_id=$(terraform -chdir=../serverless-ws output -raw workspace_id)" \
  -var "workspace_url=$(terraform -chdir=../serverless-ws output -raw workspace_url)"
```

The Well-Architected Agent generates both steps for you
(`wa-agent new --cloud aws --baseline serverless --build awsdb4u --set allowed_ip_ranges='[...]'`).

| Variable | Default | Meaning |
|---|---|---|
| `workspace_name` | | Name of the new workspace |
| `region` | | AWS region, e.g. `us-west-2` (not GovCloud) |
| `databricks_account_console_url` | `https://accounts.cloud.databricks.com` | Account console |

Changing the compute mode later means a new workspace: `compute_mode` can't
be updated in place.

## Tests

```bash
terraform init -backend=false && terraform test   # mock providers, no credentials
```

## References

- [Serverless workspaces](https://docs.databricks.com/aws/en/admin/workspace/serverless-workspaces)
- [`databricks_mws_workspaces`](https://registry.terraform.io/providers/databricks/databricks/latest/docs/resources/mws_workspaces) (`compute_mode = "SERVERLESS"`)
- [Serverless network policies](https://docs.databricks.com/aws/en/security/network/serverless-network-security/network-policies)
