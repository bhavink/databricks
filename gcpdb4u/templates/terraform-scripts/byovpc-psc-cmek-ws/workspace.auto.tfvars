databricks_account_id = "e11exxxxxxxxxxxx21612" ***REMOVED***prod
databricks_account_console_url = "https://accounts.gcp.databricks.com" ***REMOVED***prod

databricks_workspace_name = "labs-psc-cmek-ws1"
databricks_admin_user = "bhavin.kukadia@databricks.com" 


google_shared_vpc_project = "bk-demo-host-prj"
google_vpc_id = "psc-vpc-svc-prj2-xpn"
gke_node_subnet = "node-subnet2"
gke_pod_subnet = "pod-subnet2"
gke_service_subnet = "service-subnet2"
gke_master_ip_range = "10.32.0.0/28" ***REMOVED*** needs to be /28

cmek_resource_id = "projects/bk-demo-service-prj2/locations/us-central1/keyRings/databricks-keyring/cryptoKeys/databricks-cmek"

google_pe_subnet = "psc-endpoint-subnet" ***REMOVED*** private endpoint subnet
api_pe = "usc1-frontend-ep" ***REMOVED*** user to webapp and dataplane to control plane api service
relay_pe = "usc1-backend-ep" ***REMOVED*** dataplane to control plane relay service





