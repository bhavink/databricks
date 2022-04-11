# Objectives
As part of workspace creation process, Databricks creates a GKE cluster with in your GCP Project and utilizes your own VPC. In this section we'll focus on:
* Default features
* Customizations


# Default Features

* Each workspace is provisioned to a single GKE in the customer's GCP project. On this GKE we spin up [Databricks clusters](https://docs.gcp.databricks.com/clusters/index.html).
* Life cycle of a GKE cluster is managed by Databricks Control Plane.
* Compute instance type aka `node's` used by a Databricks cluster is backed by GKE [node pools](https://cloud.google.com/kubernetes-engine/docs/concepts/node-pools)
* Each node type is backed a GKE node pool
* Node pool's are shared by different Databricks cluster's
* Spark Driver and Executor's are deployed as `pods` inside GKE nodes.
* Nodes have Private IP addresses only
* Databricks clusters are GKE tenants
  
* To provide a secure logical isolation between tenants that are on the same GKE cluster, Databricks implements [GKE namespace’s](https://cloud.google.com/kubernetes-engine/docs/best-practices/enterprise-multitenancy#create-namespaces).

  * Databricks automatically creates a GKE namespace for each Databricks cluster

  * Follows [guidelines](https://cloud.google.com/kubernetes-engine/docs/best-practices/enterprise-multitenancy#network-policies) provided by GKE

    * To control network communication between Pods in each of your cluster's namespaces [network policies](https://cloud.google.com/kubernetes-engine/docs/best-practices/enterprise-multitenancy#network-policies) are created which by default deny traffic across different namespaces.
    * To securely grant workloads access to Google Cloud services, [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity) is enabled. Workload Identity helps administrators manage Kubernetes service accounts that Kubernetes workloads use to access Google Cloud services.
    * To protect your GKE control plane, restrict access to authorized networks. Databricks by default enable [authorized networks](https://cloud.google.com/kubernetes-engine/docs/how-to/authorized-networks), this way we authorize CIDR ranges and allow IP addresses only in those ranges to access your control plane. GKE already uses Transport Layer Security (TLS) and authentication to provide secure access to your control plane endpoint from the public internet. By using authorized networks, we can further restrict access to specified sets of IP addresses.
  
  ![default-cis-guidelines](./images/GCP-CIS-DefaultGuidelines.png)

## CIS Recommended Best Practices
The Center for Internet Security (CIS) releases benchmarks for best practice security recommendations. The [CIS GKE Benchmark](https://cloud.google.com/kubernetes-engine/docs/concepts/cis-benchmarks#accessing-gke-benchmark) is child benchmark of the CIS [Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes), meant specifically to be applied to the GKE distribution is a set of recommendations for configuring Kubernetes to support a strong security posture.

Databricks Data Plane (cluster’s) on GCP runs on Google Kubernetes Engine (GKE) and hence compliance to CIS GKE benchmark recommendations is of great interest to our customers. This not only instills confidence into our offering  but also demonstrates that we have a strong security posture by providing a ready to use, hardened compute engine.

The purpose of the following table is to list relevant CIS GKE benchmark recommendations and map to whats available in Databricks. The scope of this analysis is limited to Databricks data plane only.

<table style="width: 798px;" data-number-column="false" data-layout="default" data-autosize="false" data-table-local-id="a68b379c-d7c3-4e65-83ee-dbf75af66ad0"><colgroup><col style="width: 190px;" /><col style="width: 190px;" /><col style="width: 190px;" /><col style="width: 190px;" /></colgroup>
<tbody>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<div class="pm-table-column-controls-decoration ProseMirror-widget" contenteditable="false" data-start-index="0" data-end-index="1">&nbsp;</div>
<p><strong>Recommendation</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<div class="pm-table-column-controls-decoration ProseMirror-widget" contenteditable="false" data-start-index="2" data-end-index="3">&nbsp;</div>
<p><strong>Enabled by Defaults</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<div class="pm-table-column-controls-decoration ProseMirror-widget" contenteditable="false" data-start-index="3" data-end-index="4">&nbsp;</div>
<p><strong>Comments</strong></p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 769px;" colspan="3" data-colwidth="190,190,190,190">
<div class="fabric-editor-block-mark fabric-editor-align-center" data-align="center">
<div class="pm-table-column-controls-decoration ProseMirror-widget" contenteditable="false" data-start-index="1" data-end-index="2">&nbsp;</div>
<p><em><strong>Managed Services</strong></em></p>
</div>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Image Vulnerability Scanning using GCR Container Analysis or a third party provider</p>
</td>
<td class="pm-table-cell-content-wrap selectedCell" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap selectedCell" style="width: 299px;" data-colwidth="190">By Default Container images are scanned by a 3rd party Vulnerability Scanning solution.</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Minimize user access to GCR</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
<p>&nbsp;</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>Only Databricks approved Google Service Account have read only access to GCR from customers Project.</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Minimize cluster access to read-only for GCR</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
<p>&nbsp;</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>The GCR storage hosting Databricks runtime images are shared with customer GCP project hosting Databricks workspace with readonly permission</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Minimize Container Registries to only those approved</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
<p>&nbsp;</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>The access to Databricks GCR is via a read only service account&nbsp;<a href="mailto:us-gcr-access-sa@databricks-prod-artifacts.iam.gserviceaccount.com">&lt;REGION&gt;-gcr-access-sa@databricks-prod-artifacts.iam.gserviceaccount.com</a></p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 769px;" colspan="3" data-colwidth="190,190,190,190">
<div class="fabric-editor-block-mark fabric-editor-align-center" data-align="center">
<p><em><strong>Identity and Access Management (IAM)</strong></em></p>
</div>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Prefer not running GKE clusters using the Compute Engine default service account</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Supported, needs customization</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p><a href="/wiki/spaces/KB/pages/2080115282">Customize default SA role</a></p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Prefer using dedicated GCP Service Accounts and Workload Identity</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p><a href="/wiki/spaces/KB/pages/2083192893">Workload Identities</a></p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 769px;" colspan="3" data-colwidth="190,190,190,190">
<div class="fabric-editor-block-mark fabric-editor-align-center" data-align="center">
<p><strong>Cloud Key Management Service (Cloud KMS)</strong></p>
</div>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Consider encrypting Kubernetes Secrets using keys managed in Cloud KMS</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">For K8s secrets we use the GKE default (where GKE manages the keys and encrypts them)</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 769px;" colspan="3" data-colwidth="190,190,190,190">
<div class="fabric-editor-block-mark fabric-editor-align-center" data-align="center">
<p><strong>Node Metadata</strong></p>
</div>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure the GKE Metadata Server is Enabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Not Applicable</strong><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>This is not applicable to Databricks because <a href="https://cloud.google.com/kubernetes-engine/docs/how-to/protecting-cluster-metadata#concealment">as per GCP</a> "attacks against Kubernetes rely on access to the VM's metadata server to extract credentials. These attacks are blocked if you are using Workload identity or Metadata Concealment." , we use both of these features and hence we do not need to enabled this.</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Container-Optimized OS (COS) is used for GKE node images</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>Enabled by default</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Node Auto-Repair is enabled for GKE nodes</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Node Auto-Upgrade is enabled for GKE nodes</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><br /><strong>Not Applicable</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>Databricks&nbsp;manage's GKE version upgrade which are typically upgraded every 2 weeks and requires no user intervention . The nodepool version is upgraded a week after cluster version (GKE Master) upgrades in-order to catch issues with new GKE versions.</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Consider automating GKE version management using Release Channels</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Not Applicable</strong><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>GKE Versioning is managed by Databricks in order to properly vet and test out new versions before releasing.</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure <span class="search-match">Shiel</span>ded GKE Nodes are Enabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>Enabled by default with GKE 1.18 version. Command to do it manually in case if you are on an older GKE version e.g. GKE 1.17.x</p>
<p><em><span class="code" spellcheck="false">gcloud container clusters update GKE_CLUSTER_NAME --enable-<span class="search-match">shiel</span>ded-nodes</span></em></p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Integrity Monitoring for <span class="search-match selected-search-match">Shiel</span>ded GKE Nodes is Enabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><br /><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Secure Boot for <span class="search-match">Shiel</span>ded GKE Nodes is Enabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>Enabled by default</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 769px;" colspan="3" data-colwidth="190,190,190,190">
<div class="fabric-editor-block-mark fabric-editor-align-center" data-align="center">
<p><strong>Cluster Networking</strong></p>
</div>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Consider enabling VPC Flow Logs and Intranode Visibility</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Prefer VPC-native clusters</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Master Authorized Networks is Enabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure clusters are created with Private Endpoint Enabled and Public Access Disabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>GKE Cluster is created with a private endpoint and there is only a single ingress access point which is used by Databricks control plane and is allowed via the Master Authorized Network.</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure clusters are created with Private Nodes</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Network Policy is Enabled and set as appropriate</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Consider using Google-managed SSL Certificates</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>From this doc&nbsp;<a href="https://www.google.com/url?q=https://cloud.google.com/kubernetes-engine/docs/how-to/managed-certs&amp;sa=D&amp;source=editors&amp;ust=1618944546463000&amp;usg=AOvVaw127pKJichJ-_XoA8hxskCw">https://cloud.google.com/kubernetes-engine/docs/how-to/managed-certs</a>, looks like CIS meant certs on ingress and in that case its a Google managed certs that are used by API Server to communicate with Databricks control plane.</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 769px;" colspan="3" data-colwidth="190,190,190,190">
<div class="fabric-editor-block-mark fabric-editor-align-center" data-align="center">
<p><strong>Logging</strong></p>
</div>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Stackdriver Kubernetes Logging and Monitoring is Enabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>&nbsp;</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Consider enabling <a href="https://cloud.google.com/kubernetes-engine/docs/how-to/linux-auditd-logging">Linux auditd </a>logging</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Not applicable</strong><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>This recommendation deals with how to enable verbose&nbsp;<a href="http://man7.org/linux/man-pages/man7/audit.rules.7.html">operating system audit logs</a>&nbsp;on Google Kubernetes Engine nodes running&nbsp;<a href="https://cloud.google.com/kubernetes-engine/docs/concepts/node-images#container-optimized_os">Container-Optimized OS</a>. Databricks workspaces have <a href="https://docs.gcp.databricks.com/administration-guide/account-settings-gcp/log-delivery.html">audit logging enabled</a> and hence this is a nice to have, complementary capability rather than a must have requirement.</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 769px;" colspan="3" data-colwidth="190,190,190,190">
<div class="fabric-editor-block-mark fabric-editor-align-center" data-align="center">
<p><strong>Authentication and Authorization</strong></p>
</div>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Basic Authentication using static passwords is Disabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>Enabled by default</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure authentication using Client Certificates is Disabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>Enabled by default</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Consider managing Kubernetes RBAC users with Google Groups for GKE</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>This is still in BETA mode, we will consider it after it goes GA on GKE side</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Legacy Authorization (ABAC) is Disabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>Disabled by default</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 769px;" colspan="3" data-colwidth="190,190,190,190">
<div class="fabric-editor-block-mark fabric-editor-align-center" data-align="center">
<p><strong>Storage</strong></p>
</div>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Consider enabling Customer-Managed Encryption Keys (CMK GKE persistent disks (PDs)</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>By <a href="https://cloud.google.com/kubernetes-engine/docs/how-to/using-cmek#overview">default </a>GKE PDs are encrypted using Google managed key</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 769px;" colspan="3" data-colwidth="190,190,190,190">
<div class="fabric-editor-block-mark fabric-editor-align-center" data-align="center">
<p><strong>Other Cluster Configurations</strong></p>
</div>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Kubernetes Web UI is Disabled</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>Disabled by default</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure that Alpha clusters are not used for production workloads</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Yes</strong><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>We use only GA GKE features for Databricks clusters</p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Ensure Pod Security Policy is Enabled and set as appropriate</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Not Applicable</strong><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p>This feature is related to multi-tenant GKE cluster, i.e., many users/teams are sharing the same GKE cluster and are trying to deploy different kinds of workloads. They want to control the security policy on the Pods and reject the Pods if they don't meet certain criteria. However, the databricks managed GKE serves a different purpose because only Databricks is solely using the GKE APIs and provides multi-tenancy using the databricks platform at the application level i.e. via Databricks Clusters isolated by GKE Namespace and <a href="https://docs.gcp.databricks.com/security/access-control/cluster-acl.html">Databricks Access Controls</a></p>
</td>
</tr>
<tr>
<td class="pm-table-cell-content-wrap" style="width: 136px;" data-colwidth="190">
<p>Prefer enabling Binary Authorization and configuring policy as appropriate</p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 253.93px;" data-colwidth="190">
<p style="text-align: center;"><strong>Supported, needs customization</strong><br /><br class="ProseMirror-trailingBreak" /></p>
</td>
<td class="pm-table-cell-content-wrap" style="width: 299px;" data-colwidth="190">
<p><a href="/wiki/spaces/KB/pages/2080181134">Enable Binary Authorization</a></p>
</td>
</tr>
</tbody>
</table>

# Customizations

## Hardening GKE


