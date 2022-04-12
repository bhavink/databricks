# Create Databricks Workspace

## Objective
Create Databricks workspace in a **customer managed VPC**. VPC could be a shared vpc or a stand alone vpc.
![](./images/customer-managed-vpc.png)

## FAQ
* How many subnets I need?
  * In total we need 3 subnets
    * Node Subnet (primary)
    * Pod Subnet (secondary1)
    * Service Subnet (secondary2)
* Can I share subnets among different databricks workspace's?
  * No, each workspace requires its own dedicated, 3 subnets.
* Can I share a VPC among different databricks workspace's?
  * Yes
* Supported IP Address Range?
  * `10.0.0.0/8`, `100.64.0.0/10`, `172.16.0.0/12`, `192.168.0.0/16`, and `240.0.0.0/4`
* Is there a VPC/Subnet sizing guide or calculator?
  * Yes, please try [this](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/network-sizing.html).

* Quick sizing guideline
* 
* What are the typical VPC and Subnet CIDR ranges are?
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


## Pre-requistes
Please follow [these](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/customer-managed-vpc.html#requirements-1) steps





