***REMOVED*** databricks_account_id     = "9fcbb245-7c44-4522-9870-e38324104cf8" ***REMOVED***staging
***REMOVED*** databricks_account_console_url = "https://accounts.staging.gcp.databricks.com"

databricks_account_id = "<databricks_account_id>" ***REMOVED***prod
databricks_account_console_url = "https://accounts.gcp.databricks.com" ***REMOVED***prod

databricks_workspace_name = "labs-psc-ws1"
databricks_admin_user = "user@dcompany.com" 

google_vpc_id = "databricks-vpc-xpn"
gke_node_subnet = "node-subnet"
gke_pod_subnet = "pod-subnet"
gke_service_subnet = "service-subnet"
gke_master_ip_range = "10.32.0.0/28" ***REMOVED*** fixed size of /28

/*
Databricks PSC endpoints name
workspace_pe = user to webapp/api's and dataplane to api's
relay_pe = dataplane to relay service
*/
workspace_pe = "us-c1-frontend-ep" 
relay_pe = "us-c1-backend-ep" 

***REMOVED*** primary subnet providing ip addresses to PSC endpoints
google_pe_subnet = "psc-endpoint-subnet"

***REMOVED*** Private ip address assigned to PSC endpoints
relay_pe_ip_name = "backend-pe-ip"
workspace_pe_ip_name = "frontend-pe-ip"

/*
Databricks PSC service attachments
https://docs.gcp.databricks.com/resources/supported-regions.html***REMOVED***psc
*/
relay_service_attachment = "projects/prod-gcp-us-central1/regions/us-central1/serviceAttachments/ngrok-psc-endpoint"
workspace_service_attachment = "projects/prod-gcp-us-central1/regions/us-central1/serviceAttachments/plproxy-psc-endpoint"

***REMOVED*** DNS Configs
private_zone_name  = "databricks"
dns_name = "gcp.databricks.com." ***REMOVED***trailing dot(.) is required
