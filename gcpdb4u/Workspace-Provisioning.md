# Create Databricks Workspace

## Objective
Create Databricks workspace in a **customer managed VPC**. VPC could be a shared vpc or a customer managed stand alone vpc.
![](./images/customer-managed-vpc.png)

## FAQ
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

## Quick sizing guideline

| Subnet Size                                                                 | Total Nodes Per Workspace |
|-----------------------------------------------------------------------------|---------------------------|
| Nodes subnet size   /25, Pods subnet size    /20, Services subnet size    /22 |             60            |
| Nodes subnet size   /24, Pods subnet size    /19, Services subnet size    /22 |            120            |
| Nodes subnet size   /23, Pods subnet size    /18, Services subnet size    /22 |            250            |
| Nodes subnet size   /22, Pods subnet size    /17, Services subnet size    /22 |            500            |
| Nodes subnet size   /21, Pods subnet size    /16, Services subnet size    /22 |            1000           |
| Nodes subnet size   /20, Pods subnet size    /15, Services subnet size    /21 |            2000           |
| Nodes subnet size   /19, Pods subnet size    /14, Services subnet size    /20 |            4000           |



## Subnet CIDR ranges

<table class="docutils align-default">
<colgroup>
<col style="width: 33%">
<col style="width: 33%">
<col style="width: 33%">
</colgroup>
<thead>
<tr class="row-odd"><th class="head"><p>Network resource or attribute</p></th>
<th class="head"><p>Description</p></th>
<th class="head"><p>Valid range</p></th>
</tr>
</thead>
<tbody>
<tr class="row-even"><td><p>Subnet</p></td>
<td><p>Your VPC’s IP range from which to allocate your workspace’s GKE cluster nodes.</p></td>
<td><p>The range from <code class="docutils literal notranslate"><span class="pre">/29</span></code> to <code class="docutils literal notranslate"><span class="pre">/9</span></code>.</p></td>
</tr>
<tr class="row-odd"><td><p>Secondary range for GKE pods</p></td>
<td><p>Your VPC’s IP range from which to allocate your workspace’s GKE cluster pods.</p></td>
<td><p>The range from <code class="docutils literal notranslate"><span class="pre">/21</span></code> to <code class="docutils literal notranslate"><span class="pre">/9</span></code>.</p></td>
</tr>
<tr class="row-even"><td><p>Secondary range for GKE Services</p></td>
<td><p>Your VPC’s IP range from which to allocate your workspace’s GKE cluster services.</p></td>
<td><p>The range from <code class="docutils literal notranslate"><span class="pre">/27</span></code> to <code class="docutils literal notranslate"><span class="pre">/16</span></code>.</p></td>
</tr>
<tr class="row-odd"><td><p>Region</p></td>
<td><p>Region of the VPC.</p></td>
<td><p>Your VPC’s region must match your workspace’s <a class="reference internal" href="regions.html"><span class="doc">supported region</span></a>.</p></td>
</tr>
</tbody>
</table>

## Recommendation

* Pay close attention to subnet CIDR ranges, they cannot be changed (increase or decrease) after the workspace is created.
* Review and Increase [GCP resource quota](https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/quotas.html) appropiately.
* Use Customer Managed VPC
* Enable [Private Google Access](./security/Configure-PrivateGoogleAccess.md) on your vpc
* Double check DNS is properly configured to resolve to restricted.googleapis.com correctly (part of private google access configuration)
* Verify that VPC has an egress path to databricks control plane and managed hive metastore, this is typically achieved by attaching a Cloud NAT to your VPC.
* Relax your GCP organization policy so that it allows you to create Databricks workspace in your GCP Project.
  * Allows you to create GCP resources (GKE/GCS)
  * Enable `Workload Identity` is set to `true`
  * Enable `serial port logging` is set to `true`

* If you have VPC SC configured than please make sure you read through [this](./security/Configure-VPC-SC.md) section.
* Optional - Post workspace creation you may want to:
  * Enable [Binary Authorization](./security/Enable-Binary-Authorization.md)
  * Change Default [Compute SA role](./security/Customize-Default-ComputeSA-Role.md)


## Create Workspace (using UI)
Step by Step [guide](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/customer-managed-vpc.html)

## Create Workspace (using Terraform)
TODO

## Validate setup
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


## Troubleshooting

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

