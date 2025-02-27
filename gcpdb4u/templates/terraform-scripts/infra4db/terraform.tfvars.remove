vpc_project_id = "psc-host" ***REMOVED*** gcp project id where the vpc is created
network_name = "databricks-vpc" ***REMOVED*** name of the vpc
create_psc_resources = true ***REMOVED*** when true, creates psc subnets, routes, and firewall rules
create_cmk_resources = false


***REMOVED*** databricks regional control plane destination ips for egress firewall rules
***REMOVED*** applies to non psc workspace only
***REMOVED*** https://docs.databricks.com/gcp/en/resources/ip-domain-region***REMOVED***inbound-ips-to-databricks-control-plane
destination_ips = {
    "us-central1" = "34.72.196.197, 34.128.32.16/28, 34.8.0.0/28"
    "us-east1"    = "34.139.33.52, 34.138.66.176/28, 34.8.0.0/28"
    "us-west1"    = "35.185.196.216, 34.118.194.80/28, 34.8.0.0/28"
  }

databricks_hive_ips = {
    "us-central1" = "34.72.196.197"
    "us-east1"    = "34.74.134.43"
    "us-west1"    = "35.185.196.216"
  }

subnet_configs = {
  ***REMOVED*** us-central1 = {
  ***REMOVED***   region = "us-central1"
  ***REMOVED***   cidr   = "10.0.0.0/26"
  ***REMOVED*** }
  us-east1 = {
    region = "us-east1"
    cidr   = "10.0.0.64/26"
  }
  ***REMOVED*** us-west1 = {
  ***REMOVED***   region = "us-west1"
  ***REMOVED***   cidr   = "10.0.0.128/26"
  ***REMOVED*** }
 } 

psc_subnet_configs = {
  ***REMOVED*** us-central1 = {
  ***REMOVED***   region = "us-central1"
  ***REMOVED***   cidr   = "10.1.255.0/26"
  ***REMOVED*** }
  us-east1 = {
    region = "us-east1"
    cidr   = "10.2.255.64/26"
  }
  ***REMOVED*** us-west1 = {
  ***REMOVED***   region = "us-west1"
  ***REMOVED***   cidr   = "10.3.255.128/26"
  ***REMOVED*** }
 } 

***REMOVED***https://docs.databricks.com/gcp/en/resources/ip-domain-region***REMOVED***private-service-connect-psc-attachment-uris-and-project-numbers
psc_attachments = {
  ***REMOVED*** "us-central1" = {
  ***REMOVED***   workspace_attachment = "projects/prod-gcp-us-central1/regions/us-central1/serviceAttachments/plproxy-psc-endpoint-all-ports"
  ***REMOVED***   relay_attachment     = "projects/prod-gcp-us-central1/regions/us-central1/serviceAttachments/ngrok-psc-endpoint"
  ***REMOVED*** }
  "us-east1" = {
    workspace_attachment = "projects/prod-gcp-us-east1/regions/us-east1/serviceAttachments/plproxy-psc-endpoint-all-ports"
    relay_attachment     = "projects/prod-gcp-us-east1/regions/us-east1/serviceAttachments/ngrok-psc-endpoint"
  }
  ***REMOVED*** "us-west1" = {
  ***REMOVED***   workspace_attachment = "projects/prod-gcp-us-west1/regions/us-west1/serviceAttachments/plproxy-psc-endpoint-all-ports"
  ***REMOVED***   relay_attachment     = "projects/prod-gcp-us-west1/regions/us-west1/serviceAttachments/ngrok-psc-endpoint"
  ***REMOVED*** }
}