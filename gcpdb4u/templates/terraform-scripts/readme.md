***REMOVED*** Terraform examples

***REMOVED******REMOVED******REMOVED*** Google Terraform Provider Auth Config
- Create a Google Service Account
- Assign project Owner role (service and shared vpc project's)
- run the following commands on your terminal
```
gcloud config set auth/impersonate_service_account <GSA-NAME>@<PROJECT>.iam.gserviceaccount.com
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
```
- In order to create a Databricks workspace the required roles are explained over [here](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/customer-managed-vpc.html***REMOVED***role-requirements). As the GSA could provision additional resource's beyond Databricks workspace ex private DNS zone, A records, PSC endpoints etc, it is better to have Owner role to avoid any permission related issues.

- If you are using service account impersonation then please follow this [run book](../terraform-scripts/sa-impersonation.md)
***REMOVED******REMOVED******REMOVED*** BYO VPC workspace
[sample](../terraform-scripts/byovpc-ws/workspace.tf)
***REMOVED******REMOVED******REMOVED*** BYO VPC + PSC workspace
[sample](../terraform-scripts/byovpc-psc-ws/workspace.tf)
***REMOVED******REMOVED******REMOVED*** BYO VPC + PSC + CMEK workspace
[sample](../terraform-scripts/byovpc-psc-cmek-ws/workspace.tf)
***REMOVED******REMOVED******REMOVED*** BYO VPC + CMEK workspace
[sample](../terraform-scripts/byovpc-cmek-ws/workspace.tf)