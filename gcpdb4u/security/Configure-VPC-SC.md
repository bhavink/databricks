# VPC Service Controls for a Databricks Workspace

[VPC Service Controls](https://cloud.google.com/vpc-service-controls) enables you to isolate your production GCP resources from the internet, unauthorized VPC networks and unauthorized GCP resources.

VPC SC is fully supported by databricks. It works with Shared VPC as well a stand alone VPC.

It improves your ability to mitigate the risk of data exfiltration from Google Cloud services such as Cloud Storage and BigQuery. It also allows you to restrict access to production GCP resources from only clients on authorized networks or devices.

With VPC Service Controls, you create perimeters that protect the resources and data of services that you explicitly specify.

* For all Google Cloud services secured with VPC Service Controls, you can ensure that:

* Resources within a perimeter accessed only from clients within authorized VPC networks using Private Google Access with either Google Cloud or on-premises.

* Clients within a perimeter that have private access to resources do not have access to unauthorized (potentially public) resources outside the perimeter.

* Data cannot be copied to unauthorized resources outside the perimeter using service operations such as gsutil cp or bq mk.

* When enabled, internet access to resources within a perimeter is restricted using whitelisted IPv4 and IPv6 ranges.

VPC Service Controls provides an additional layer of security defense for Google Cloud services that is independent of Identity and Access Management (IAM). While IAM enables granular identity-based access control, VPC Service Controls enables broader context-based perimeter security, including controlling data egress across the perimeter. We recommend using both VPC Service Controls and IAM for defense in depth.

See the image below for an example of what this might look like:

![](./../images/vpc-sc1.png)

## Supported Services
For a list of services supported by VPC SC, please see [Services](https://cloud.google.com/vpc-service-controls/docs/restricted-vip-services) supported by the restricted VIP

## Setting up private connectivity to Google APIs and services
To restrict Private Google Access within a service perimeter to only VPC Service Controls supported Google APIs and services, hosts must send their requests to the `restricted.googleapis.com` domain name instead of `*.googleapis.com`.  The `restricted.googleapis.com` domain resolves to a VIP (virtual IP address) range `199.36.153.4/30`. This IP address range is not announced to the Internet.

See the [link](https://cloud.google.com/vpc-service-controls/docs/set-up-private-connectivity#overview_of_procedure) for an overview of the procedure to set it up

# How to?
Following steps are applicable to:

* Customer Managed VPC: Shared VPC/Stand-alone VPC
* Databricks Managed VPC

## Before you begin
We will be using the following terms, let’s understand them a bit better before we proceed.

* `Consumer Project` = Customer owned GCP Project where Databricks workspace is deployed. In case of a shared vpc we’ll have two projects, host project providing the vpc and service project where workspace i.e. GKE cluster and DBFS related GCS storage accounts  are created.

* `Consumer VPC` = Customer owned GCP VPC used by Databricks workspace (shared or stand alone vpc)

* `Databricks Workspace Creator` = A customer owned and managed GCP identity (User or Service Account Principal) used to create a Databricks workspace, this identity is also known as the `login user`. A login user has `Project Owner or Project Editor` and the `IAM Admin` permission on the Consumer Project (GCP project) where Databricks workspace/GKE is deployed. Please follow [this](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/customer-managed-vpc.html#requirements-1) doc for more details on roles/permissions required.

* `Consumer SA` = A GCP Service Account for the new workspace is created in the Databricks regional control plane project. We use the login user’s (workspace creator) OAuth token to grant the Consumer SA with sufficient permissions to setup and operate Databricks workspaces in the customer’s consumer (GCP) project. Consumer SA follow’s `db-WORKSPACEID@databricks-project.iam.gserviceaccount.com` naming convention. Workspace ID is generated as part of the workspace creation process.
  `example: db-1030565636556919@prod-gcp-us-central1.iam.gserviceaccount.com`

* `Databricks Owned GCP Projects` = There are several GCP projects involved, one each for `Databricks Regional Control Plane`, `Databricks Central Service` (required during workspace creation only), `Databricks audit log delivery` and `Databricks Artifacts` (runtime image) Repository.

* `Databricks Owned GCP Projects Identities` = There are three GCP Service Accounts in use, for ex: US East4 we have: 
  * `shard-sa@prod-gcp-us-east4.iam.gserviceaccount.com`
  * `shard-sa@prod-gcp-us-central1.iam.gserviceaccount.com` (only required during workspace creation)
  * `us-gcr-access-sa@databricks-prod-artifacts.iam.gserviceaccount.com`
  * `log-delivery@databricks-prod-master.iam.gserviceaccount.com`

## List of Databricks Regional Projects and Identities

**Table1**

|     |     |     |
| --- | --- | --- |
| **GCP Region** | **Project Number** | **Identities** |
| asia-southeast1 | Shard: 163855694937 & 68422481410  Artifact: 643670579914  AuditLogDelivery: 85638097580 | <ul><li> shard-sa@prod-gcp-**asia-southeast1**.iam.gserviceaccount.com (Shard SA)  </li><li>shard-sa@prod-gcp-**us-central1**.iam.gserviceaccount.com (Backend Service SA) </li> <li> **log-delivery**@databricks-prod-master.iam.gserviceaccount.com (Audit Log Delivery Service Account)</li>  <li>**as-gcr-access-sa**@databricks-prod-artifacts.iam.gserviceaccount.com (GCR Service Account)</li>  <li>db-**WORKSPACEID**@prod-gcp-**asia-southeast1**.iam.gserviceaccount.com (Consumer SA)<li> </ul> |
| australia-southeast1 | Shard: 890675851652 & 68422481410  Artifact: 643670579914  AuditLogDelivery: 85638097580 | shard-sa@prod-gcp-**australia-southeast1**.iam.gserviceaccount.com (Shard SA)  shard-sa@prod-gcp-**us-central1**.iam.gserviceaccount.com (Backend Service SA)  **log-delivery**@databricks-prod-master.iam.gserviceaccount.com (Audit Log Delivery Service Account)  **au-gcr-access-sa**@databricks-prod-artifacts.iam.gserviceaccount.com (GCR Service Account)  db-**WORKSPACEID**@prod-gcp-**australia-southeast1**.iam.gserviceaccount.com (Consumer SA) |
| europe-west1 | Shard: 623104702041 & 68422481410  Artifact: 643670579914  AuditLogDelivery: 85638097580 | shard-sa@prod-gcp-**europe-west1**.iam.gserviceaccount.com (Shard SA)  shard-sa@prod-gcp-**us-central1**.iam.gserviceaccount.com (Backend Service SA)  **log-delivery**@databricks-prod-master.iam.gserviceaccount.com (Audit Log Delivery Service Account)  **eu-gcr-access-sa**@databricks-prod-artifacts.iam.gserviceaccount.com (GCR Service Account)  db-**WORKSPACEID**@prod-gcp-**europe-west1**.iam.gserviceaccount.com (Consumer SA) |
| europe-west2 | Shard: 204760216014 & 68422481410  Artifact: 643670579914  AuditLogDelivery: 85638097580 | shard-sa@prod-gcp-**europe-west2**.iam.gserviceaccount.com (Shard SA)  shard-sa@prod-gcp-**us-central1**.iam.gserviceaccount.com (Backend Service SA)  **log-delivery**@databricks-prod-master.iam.gserviceaccount.com (Audit Log Delivery Service Account)  **eu-gcr-access-sa**@databricks-prod-artifacts.iam.gserviceaccount.com (GCR Service Account)  db-**WORKSPACEID**@prod-gcp-**europe-west2**.iam.gserviceaccount.com (Consumer SA) |
| europe-west3 | Shard: 622303457766 & 68422481410  Artifact: 643670579914  AuditLogDelivery: 85638097580 | shard-sa@**prod-gcp-europe-west3**.iam.gserviceaccount.com (Shard SA)  shard-sa@prod-gcp-**us-central1**.iam.gserviceaccount.com (Backend Service SA)  **log-delivery**@databricks-prod-master.iam.gserviceaccount.com (Audit Log Delivery Service Account)  **eu-gcr-access-sa@**[databricks-prod-artifacts.iam.gserviceaccount.com](http://databricks-prod-artifacts.iam.gserviceaccount.com) (GCR Service Account)  db-**WORKSPACEID**@prod-gcp-**europe-west3**.iam.gserviceaccount.com (Consumer SA) |
| us-central1 | Shard: 68422481410 & 68422481410  Artifact: 643670579914  AuditLogDelivery: 85638097580 | shard-sa@prod-gcp-**us-central1**.iam.gserviceaccount.com (Shard & Backend Service SA)  **log-delivery**@databricks-prod-master.iam.gserviceaccount.com (Audit Log Delivery Service Account)  [**us-gcr-access-sa**@databricks-prod-artifacts.iam.gserviceaccount.com](mailto:us-gcr-access-sa@databricks-prod-artifacts.iam.gserviceaccount.com)  db-**WORKSPACEID**@prod-gcp-**us-central1**.iam.gserviceaccount.com (Consumer SA) |
| us-east1 | Shard: 51066298900 & 68422481410  Artifact: 643670579914  AuditLogDelivery: 85638097580 | shard-sa@prod-gcp-**us-east1**.iam.gserviceaccount.com (Shard SA)  shard-sa@prod-gcp-**us-central1**.iam.gserviceaccount.com (Backend Service SA)  **log-delivery**@databricks-prod-master.iam.gserviceaccount.com (Audit Log Delivery Service Account)  [**us-gcr-access-sa**@databricks-prod-artifacts.iam.gserviceaccount.com](mailto:us-gcr-access-sa@databricks-prod-artifacts.iam.gserviceaccount.com)  db-**WORKSPACEID**@prod-gcp-**us-east1**.iam.gserviceaccount.com (Consumer SA) |
| us-east4 | Shard: 121886670913 & 68422481410  Artifact: 643670579914  AuditLogDelivery: 85638097580 | shard-sa@prod-gcp-**us-east4**.iam.gserviceaccount.com (Shard SA)  shard-sa@prod-gcp-**us-central1**.iam.gserviceaccount.com (Backend Service SA)  **log-delivery**@databricks-prod-master.iam.gserviceaccount.com (Audit Log Delivery Service Account)  [**us-gcr-access-sa**@databricks-prod-artifacts.iam.gserviceaccount.com](mailto:us-gcr-access-sa@databricks-prod-artifacts.iam.gserviceaccount.com)  db-**WORKSPACEID**@prod-gcp-**us-east4**.iam.gserviceaccount.com (Consumer SA) |
| us-west1 | Shard: 646990673688 & 68422481410  Artifact: 643670579914  AuditLogDelivery: 85638097580 | shard-sa@prod-gcp-**us-west1**.iam.gserviceaccount.com (Shard SA)  shard-sa@prod-gcp-**us-central1**.iam.gserviceaccount.com (Backend Service SA)  **log-delivery**@databricks-prod-master.iam.gserviceaccount.com (Audit Log Delivery Service Account)  [**us-gcr-access-sa**@databricks-prod-artifacts.iam.gserviceaccount.com](mailto:us-gcr-access-sa@databricks-prod-artifacts.iam.gserviceaccount.com)  db-**WORKSPACEID**@prod-gcp-**us-west1**.iam.gserviceaccount.com (Consumer SA) |
| us-west4 | Shard: 321004414578 & 68422481410  Artifact: 643670579914 | shard-sa@prod-gcp-**us-west4**.iam.gserviceaccount.com (Shard SA)  shard-sa@prod-gcp-**us-central1**.iam.gserviceaccount.com (Backend Service SA)  **log-delivery**@databricks-prod-master.iam.gserviceaccount.com (Audit Log Delivery Service Account)  [us-gcr-access-sa@databricks-prod-artifacts.iam.gserviceaccount.com](mailto:us-gcr-access-sa@databricks-prod-artifacts.iam.gserviceaccount.com)  db-**WORKSPACEID**@prod-gcp-**us-west4**.iam.gserviceaccount.com (Consumer SA) |

We also need to know:

* Ingress & Egress (calls made into customers GCP project from databricks GCP projects)

* Databricks managed GCP identities (see Table 1 above , Service Accounts)

* Google API’s and Methods invoked

<table data-number-column="false"><colgroup><col style="width: 305px;"><col style="width: 153px;"><col style="width: 457px;"><col style="width: 305px;"><col style="width: 305px;"></colgroup><tbody><tr><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="6581"><strong data-renderer-mark="true">Created and Managed By</strong></p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="180"><p data-renderer-start-pos="6607"><strong data-renderer-mark="true">Identity Type</strong></p><p data-renderer-start-pos="6622"><strong data-renderer-mark="true">Service Account (SA) or User Principal (UP)</strong></p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="538"><p data-renderer-start-pos="6669"><strong data-renderer-mark="true">Example</strong></p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="6680"><strong data-renderer-mark="true">Used For</strong></p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="6692"><strong data-renderer-mark="true">Ingress into / Egress from Customers Project</strong></p></td></tr><tr><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="6742">Databricks</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="180"><p data-renderer-start-pos="6756">SA</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="538"><p data-renderer-start-pos="6762">shard-sa@[databricks-supported-gcp-region].iam.gserviceaccount.com</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="6832">Accessing Databricks Control Plane</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="6870">Egress</p></td></tr><tr><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="6882">Databricks</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="180"><p data-renderer-start-pos="6896">SA</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="538"><p data-renderer-start-pos="6902">[region]-gcr-access-sa@databricks-prod-artifacts.iam.gserviceaccount.com&nbsp;</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="6980">Accessing Databricks runtime images from GCR</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="7028">Egress</p></td></tr><tr><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="7040">Databricks</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="180"><p data-renderer-start-pos="7054">SA</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="538"><p data-renderer-start-pos="7060"><a class="sc-iYUSvU ijndOf" href="mailto:db-WORKSPACEID@databricks-project.iam.gserviceaccount.com" title="mailto:db-WORKSPACEID@databricks-project.iam.gserviceaccount.com" data-renderer-mark="true">db-WORKSPACEID@databricks-project.iam.gserviceaccount.com</a></p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="7121">Databricks created per workspace consumer SA added to customers project</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="7196">Ingress</p></td></tr>

<tr><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="7209">Databricks</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="180"><p data-renderer-start-pos="7221">SA&nbsp;</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="538"><p data-renderer-start-pos="7234"><a class="sc-iYUSvU ijndOf" href="mailto:log-delivery@databricks-prod-master.iam.gserviceaccount.com" title="mailto:log-delivery@databricks-prod-master.iam.gserviceaccount.com" data-renderer-mark="true">log-delivery@databricks-prod-master.iam.gserviceaccount.com</a>&nbsp;</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="7299">SA used to delivery audit logs to your storage accout</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="7321">Ingress</p></td></tr>

<tr><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="7209">Customer</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="180"><p data-renderer-start-pos="7221">UP or SA&nbsp;</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="538"><p data-renderer-start-pos="7234"><a class="sc-iYUSvU ijndOf" href="mailto:abc@company.com" title="mailto:abc@company.com" data-renderer-mark="true">abc@company.com</a> or <a class="sc-iYUSvU ijndOf" href="mailto:mysa@cust-project.iam.gserviceaccount.com" title="mailto:mysa@cust-project.iam.gserviceaccount.com" data-renderer-mark="true">mysa@cust-project.iam.gserviceaccount.com</a>&nbsp;</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="7299">Workspace Creation</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="359"><p data-renderer-start-pos="7321">Ingress</p></td></tr></tbody></table>

## Two Step Process

Configuring VPC SC involves two step process
*   Ingress and Egress policy at workspace creation
*   Ingress and Egress policy after the workspace is created

### Ingress Policy At  Workspace Creation:

* Login User Id (Customer Owned, User Principal or SA creating Databricks workspace
* Consumer Project ID (Customer Owned, GCP Project where Databricks workspace is created)
* Databricks Project Numbers & Identities - see Table 1 above for your chosen GCP region

Note: when deploying a workspace, irrespective of the GCP region (e.g. europe-west1 or us-east4), the ingress policy at workspace creation needs to contain ingress allowance from both the regional control plane or shard (e.g. europe-west1), as well as Databricks Central Service, this includes both the project number, as well as the service accounts.

### Ingress Policy After Workspace Creation:

* Consumer SA e.g. db-WORKSPACEID@databricks-project.iam.gserviceaccount.com
* Workspace ID is available only after the workspace is created, for databricks-project please see `Table 1` Identities column > `db-WORKSPACEID@*` above for your chosen GCP region, make sure to substitute WORKSPACEID with your Databricks Workspace ID

Note: As opposed to workspace provisioning (creation step discussed earlier), the rest of the operations i.e after the workspace is created, workspace only require access via the regional control plane, and access from the central service (us-central1) is no longer required.

### Egress Policy
It remains same during and after the workspace is created except for one difference i.e after the workspace is created we do not need `databricks central service` project and identity in our policy definition.

Note: when deploying a workspace outside of us-central1 (e.g. europe-west1), the egress policy at workspace creation needs to contain egress allowance from both the regional control plane (e.g. europe-west1), as well as Databricks US-Central control plane (always us-central1), this includes the project numbers for both of the regional control plane.

**Sample YAML files**

* Used during workspace creation: [ingress.yaml](./../templates/vpcsc-ingress-policy.yaml) & [egress.yaml](./../templates/vpcsc-egress-policy.yaml)
* Used after workspace is created: [ingress-updated.yaml](./../templates/vpcsc-ingress-updated-policy.yaml) & [egress-updated.yaml](./../templates/vpcsc-egress-updated-policy.yaml)

Before you proceed `please make sure to update` policy yaml files with your relevant project numbers and identities

And also update the policy after the workspace is created such that:

* Update identities section to use workspace specific Service Account instead of ANY_SERVICE_ACCOUN
* Remove calls to google.storage.buckets.create ,  we do not need this after workspace is created.

## GCLOUD commands

When using gcloud commands we need to use access-context-policy-id, for more details please see GCP help [docs](https://cloud.google.com/vpc-service-controls/docs/service-perimeters#create-access-policy).

<table data-number-column="false"><colgroup><col style="width: 339px;"><col style="width: 339px;"></colgroup><tbody><tr><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="9762"><strong data-renderer-mark="true">Action</strong></p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="9772"><strong data-renderer-mark="true">Gcloud command</strong></p></td></tr><tr><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="9792">Create Dry Run</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="9810">gcloud access-context-manager perimeters <strong data-renderer-mark="true">dry-run</strong> <strong data-renderer-mark="true">create</strong> <strong data-renderer-mark="true">[POLICY_NAME]</strong> \</p><p data-renderer-start-pos="9883">--perimeter-title="svpc_dbx_dryrun" --perimeter-resources=projects/<strong data-renderer-mark="true">[shared-vpc-project]</strong>,projects/<strong data-renderer-mark="true">[workspace-project]</strong> \</p><p data-renderer-start-pos="10003">--perimeter-restricted-services=<a class="sc-iYUSvU ijndOf" href="http://storage.googleapis.com" title="http://storage.googleapis.com" data-renderer-mark="true">storage.googleapis.com</a>,<a class="sc-iYUSvU ijndOf" href="http://container.googleapis.com" title="http://container.googleapis.com" data-renderer-mark="true">container.googleapis.com</a>,<a class="sc-iYUSvU ijndOf" href="http://compute.googleapis.com" title="http://compute.googleapis.com" data-renderer-mark="true">compute.googleapis.com</a>,<a class="sc-iYUSvU ijndOf" href="http://containerregistry.googleapis.com" title="http://containerregistry.googleapis.com" data-renderer-mark="true">containerregistry.googleapis.com</a>,<a class="sc-iYUSvU ijndOf" href="http://logging.googleapis.com" title="http://logging.googleapis.com" data-renderer-mark="true">logging.googleapis.com</a>,<a class="sc-iYUSvU ijndOf" href="http://iam.googleapis.com" title="http://iam.googleapis.com" data-renderer-mark="true">iam.googleapis.com</a>,<a class="sc-iYUSvU ijndOf" href="http://cloudresourcemanager.googleapis.com" title="http://cloudresourcemanager.googleapis.com" data-renderer-mark="true">cloudresourcemanager.googleapis.com</a> \</p><p data-renderer-start-pos="10220">--perimeter-ingress-policies=ingress.yaml \</p><p data-renderer-start-pos="10265">--perimeter-egress-policies=egress.yaml \</p><p data-renderer-start-pos="10308">--policy=<strong data-renderer-mark="true">[</strong><a class="sc-iYUSvU ijndOf" href="https://cloud.google.com/vpc-service-controls/docs/service-perimeters#create-access-policy" title="https://cloud.google.com/vpc-service-controls/docs/service-perimeters#create-access-policy" data-renderer-mark="true"><strong data-renderer-mark="true"><u data-renderer-mark="true">access-context-policy-id</u></strong></a><strong data-renderer-mark="true">]</strong> --perimeter-type=regular</p></td></tr><tr><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="10374">Enforce Policy</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="10392">gcloud access-context-manager perimeters <strong data-renderer-mark="true">dry-run</strong> <strong data-renderer-mark="true">enforce</strong> <strong data-renderer-mark="true">[POLICY_NAME]</strong> --policy=<strong data-renderer-mark="true">[</strong><a class="sc-iYUSvU ijndOf" href="https://cloud.google.com/vpc-service-controls/docs/service-perimeters#create-access-policy" title="https://cloud.google.com/vpc-service-controls/docs/service-perimeters#create-access-policy" data-renderer-mark="true"><strong data-renderer-mark="true"><u data-renderer-mark="true">access-context-policy-id</u></strong></a><strong data-renderer-mark="true">]</strong></p></td></tr><tr><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="10504">List Policies</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="10521">gcloud access-context-manager perimeters list --format=yaml --policy=<strong data-renderer-mark="true">[</strong><a class="sc-iYUSvU ijndOf" href="https://cloud.google.com/vpc-service-controls/docs/service-perimeters#create-access-policy" title="https://cloud.google.com/vpc-service-controls/docs/service-perimeters#create-access-policy" data-renderer-mark="true"><strong data-renderer-mark="true"><u data-renderer-mark="true">access-context-policy-id</u></strong></a><strong data-renderer-mark="true">]</strong></p></td></tr><tr><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="10622">Delete Policy</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="10639">gcloud access-context-manager perimeters delete <strong data-renderer-mark="true">[POLICY_NAME]</strong> --policy=<strong data-renderer-mark="true">[</strong><a class="sc-iYUSvU ijndOf" href="https://cloud.google.com/vpc-service-controls/docs/service-perimeters#create-access-policy" title="https://cloud.google.com/vpc-service-controls/docs/service-perimeters#create-access-policy" data-renderer-mark="true"><strong data-renderer-mark="true"><u data-renderer-mark="true">access-context-policy-id</u></strong></a><strong data-renderer-mark="true">]</strong></p></td></tr><tr><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="10742">Update Policy</p></td><td rowspan="1" colspan="1" colorname="" data-colwidth="340"><p data-renderer-start-pos="10759">Delete Policy and then Run Create Policycall&nbsp; using Ingress-Updated-Policy.yaml, Egress policy remains the same.</p></td></tr></tbody></table>

# Troubleshooting

## During workspace creation, Why do we need to use ANY_SERVICE_ACCOUNT in order to create databricks workspace specific buckets?

At ws creation we create two storage buckets:

`projects/[cust-project-id]/buckets/databricks-[workspace-id]`

`projects/[cust-project-id]/buckets/databricks-[workspace-id]-system`

Using

`db-[workspace-id]@[databricks-project].iam.gserviceaccount.com`

This is an automatically generated Google service account created at WS creation and hence we cannot add this workspace specific service account to our ingress policy. If you notice it carefully, although we are using ANY_SERVICE_ACCOUNT, this identity still needs to originate from the databricks control plane project rather than any arbitrary source.