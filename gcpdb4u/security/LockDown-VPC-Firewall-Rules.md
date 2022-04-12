***REMOVED*** Limit network egress for your workspace using a firewall

From [here](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/firewall.html): By default Google Cloud allows all egress traffic from your VPC. Optionally you can choose to configure your workspace to limit egress to only the essential services as well as any other destinations that your organization requires. To allow the essential services, you need to modify the Google Cloud network (VPC) and the firewall that Databricks creates for your workspace. For some services, you can set up Private Google Access to communicate with Google APIs over private IP addresses.

***REMOVED*** High Level Steps

* Firewall configuration overview
* Control plane service endpoint IP addresses by region
* Step 1: Plan your network sizing
* Step 2: Create a workspace
* Step 3: Add VPC firewall rules
* Step 4: Update VPC Routes
* Step 5: Create DNS zone for Google APIs so you can enable Google Private Access for GCS and GCR
* Step 6: Validate configuration

Please follow public documentation guide available over [here](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/firewall.html)