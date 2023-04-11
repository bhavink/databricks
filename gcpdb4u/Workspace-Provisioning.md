***REMOVED*** Create Databricks Workspace

***REMOVED******REMOVED*** Objective
Create Databricks workspace in a **customer managed VPC**. VPC could be a shared vpc or a customer managed stand alone vpc.
![](./images/customer-managed-vpc.png)

***REMOVED******REMOVED*** FAQ
* Can I use Terraform to create workspace
  * Yes you can, more details [here](https://registry.terraform.io/providers/databricks/databricks/latest/docs/guides/gcp-workspace).
* How many subnets I need?
  * In total we need 4 subnets
    * Node Subnet (primary)
    * Pod Subnet (secondary1)
    * Service Subnet (secondary2)
    * Kube Master VPC - created and managed by GCP and is of fix size /28
* Can I share subnets among different databricks workspace's?
  * No, each workspace requires its own dedicated, 3 subnets.
* Can I change Subnet address space after the workspace is created?
  * No
* Can I share a VPC among different databricks workspace's?
  * Yes, as long as you do not use existing subnets being used by databricks.
* Supported IP Address Range?
  * `10.0.0.0/8`, `100.64.0.0/10`, `172.16.0.0/12`, `192.168.0.0/16`, and `240.0.0.0/4`
* Is there a VPC/Subnet sizing guide or calculator?
  * Yes, please try [this](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/network-sizing.html).
* User creating the workspace is automatically added to the workspace as an admin.

***REMOVED******REMOVED*** Quick sizing guideline

| Subnet Size                                                                 | Total Nodes Per Workspace |
|-----------------------------------------------------------------------------|---------------------------|
| Nodes subnet size   /25, Pods subnet size    /20, Services subnet size    /22 |             60            |
| Nodes subnet size   /24, Pods subnet size    /19, Services subnet size    /22 |            120            |
| Nodes subnet size   /23, Pods subnet size    /18, Services subnet size    /22 |            250            |
| Nodes subnet size   /22, Pods subnet size    /17, Services subnet size    /22 |            500            |
| Nodes subnet size   /21, Pods subnet size    /16, Services subnet size    /22 |            1000           |
| Nodes subnet size   /20, Pods subnet size    /15, Services subnet size    /21 |            2000           |
| Nodes subnet size   /19, Pods subnet size    /14, Services subnet size    /20 |            4000           |



***REMOVED******REMOVED*** Subnet CIDR ranges


| Network resource or attribute   |      Description      |  Range |
|----------|:-------------:|------:|
| Primary subnet |  GKE cluster nodes | between /29 to /9 |
| Secondary range for GKE pods |    GKE pods   |   between /21 to /9 |
| Secondary range for GKE Services | GKE services |    between /27 to /16 |
| Region | VPC Region |    [Workspace and VPC region](https://github.com/bhavink/databricks/blob/master/gcpdb4u/regions.html) must match |

***REMOVED******REMOVED*** Recommendation

* Pay close attention to subnet CIDR ranges, they cannot be changed (increase or decrease) after the workspace is created.
* Review and Increase [GCP resource quota](https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/quotas.html) appropiately.
* Use Customer Managed VPC
* Enable [Private Google Access](./security/Configure-PrivateGoogleAccess.md) on your vpc
* Double check DNS is properly configured to resolve to restricted.googleapis.com correctly (part of private google access configuration)
* Verify that VPC has an egress path to databricks control plane and managed hive metastore, this is typically achieved by attaching a Cloud NAT to your VPC.
* If your Google Cloud organization policy enables domain restricted sharing, ensure that both the Google Cloud customer IDs for Databricks (C01p0oudw) and your own organization’s customer ID are in the policy’s allowed list.
* Please make sure that you are allowed to: 
  * Create GCP resources (GKE/GCS)
  * Enable `Workload Identity` is set to `true`
  * Enable `serial port logging` is set to `true`

* If you have VPC SC configured than please make sure you read through [this](./security/Configure-VPC-SC.md) section.
* Optional - Post workspace creation you may want to:
  * Change Default [Compute SA role](./security/Customize-Default-ComputeSA-Role.md)


***REMOVED******REMOVED*** Create Workspace (using UI)
Step by Step [guide](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/customer-managed-vpc.html)

***REMOVED******REMOVED*** Create Workspace (using Terraform)
Please follow public [documentation](https://registry.terraform.io/providers/databricks/databricks/latest/docs/guides/gcp-workspace). Here's a few sample [TF script](./templates/terraform-scripts/readme.md) to deploy a bring your VPC based workspace using Terraform

* create a [PSC + CMEK enabled workspace and attach a custom SA](./templates/terraform-scripts/byovpc-psc-cmek-ws). Please note that PSC is in preview, follow [instructions](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/private-service-connect.html***REMOVED***step-1-enable-your-account-for-private-service-connect) to sign up for this feature
  
***REMOVED******REMOVED*** Validate setup
- Create a Databricks cluster to validate n/w setup
- Databricks Cluster comes up fine
![](./images/test-cluster-comesup1.png)
![](./images/test-cluatser-comesup2.png)


* Upon creation of workspace, immediately test it by creating a databricks cluster and run a test command in databricks notebook like:
  ```
  %sql
  show tables
  ```
  make sure that commands runs successfully.


***REMOVED******REMOVED*** Troubleshooting

* Not able to create Network Configuration
  * Follow steps mentioned over [here](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/customer-managed-vpc.html), pay close attention to required roles and permissions.
  * If VPC SC is configured on the GCP project used by Databricks than please make sure that you have followed steps mentioned over here
* Workspace creation fails
  * Verify that there is no organization policy blocking workspace creation process, please see recommendations section above
  * If VPC SC is configured on the GCP project used by Databricks than please make sure that you have followed steps mentioned over [here](./security/Configure-VPC-SC.md)
  * Verify that you have required role and permissions
* Databricks Cluster Creation fails with:
  ```
  {
  "reason": {
    "code": "K8S_DBR_CLUSTER_LAUNCH_TIMEOUT",
    "type": "SERVICE_FAULT",
    "parameters": {
      "databricks_error_message": "Cluster launch timeout."
    }
  }
  }
  ```
  or you see ![cluster-launch-failure](./images/cluster-launch-failure1.png)
  Verify that you have egress/outbound network connectivity from your VPC to Databricks Control plane.
    - Most likely VPC firewall is blocking egress communication
    - You do not have a n/w route set for vpc to communicate with Databricks control plane
    - Make sure an egress appliance like Cloud NAT is attached to subnets used by Databricks

* Databricks Cluster Creation fails with:
![cluster-launch-failure2](./images/cluster-launch-failure2.png)
  - Verify that you have adequate GCP resource quota limit set, follow steps mentioned over [here](https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/quotas.html).

