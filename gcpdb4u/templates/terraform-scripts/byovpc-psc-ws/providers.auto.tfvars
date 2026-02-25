/*
Make sure that the service account:
- Is added to databricks account console with admin role
- Has permissions listed over here 
https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/customer-managed-vpc.html#role-requirements
*/

google_service_account_email = "automation-sa@<gcp_service_project>.iam.gserviceaccount.com"

/*
Service or Consumer Project, it contains Databricks managed:
Data plane (GCE)
DBFS Storage (GCS)
*/
google_project_name = "<gcp_service_project>"
/*
Host project aka Shared VPC
if not using shared vpc then use same project as google_project_name
*/
google_shared_vpc_project = "<gcp_host_project>"
google_region             = "us-central1"