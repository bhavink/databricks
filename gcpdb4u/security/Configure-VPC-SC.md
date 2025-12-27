***REMOVED*** VPC Service Controls (VPC SC) for Databricks on GCP 🔒

VPC Service Controls (VPC SC) lets you create security perimeters around Google Cloud resources to reduce the risk of data exfiltration and to restrict access to only authorized networks and identities. Databricks supports VPC SC for both Customer-Managed VPCs (Shared VPC or standalone) and Databricks-managed VPCs.

---

***REMOVED******REMOVED*** Why use VPC SC for Databricks
- Adds an extra layer of perimeter security independent of IAM (defense-in-depth).
- Helps mitigate data exfiltration from services such as Cloud Storage and BigQuery.
- Restricts access so that resources can be accessed only from authorized networks, devices, or identities.

> Note: Use VPC SC together with IAM and Private Google Access (PGA) for a robust security posture.

![](./../images/vpc-sc1.png)

---

***REMOVED******REMOVED*** Quick checklist ✅
- [ ] Define Access Levels (Access Context Manager) to allow Databricks control plane NAT IPs
- [ ] Create and test a perimeter (dry-run) before enforcement
- [ ] Configure Private Google Access or `restricted.googleapis.com` where required
- [ ] Update DNS, routes and firewall rules as per the perimeter requirements
- [ ] Validate workspace creation and runtime access patterns

***REMOVED******REMOVED*** Supported Services
For a list of services supported by VPC SC, please see [Services](https://cloud.google.com/vpc-service-controls/docs/restricted-vip-services) supported by the restricted VIP

***REMOVED******REMOVED*** Setting up private connectivity to Google APIs and services
To restrict Private Google Access within a service perimeter to only VPC Service Controls supported Google APIs and services, hosts must send their requests to the `restricted.googleapis.com` domain name instead of `*.googleapis.com`.  The `restricted.googleapis.com` domain resolves to a VIP (virtual IP address) range `199.36.153.4/30`. This IP address range is not announced to the Internet.

See the [link](https://cloud.google.com/vpc-service-controls/docs/set-up-private-connectivity***REMOVED***overview_of_procedure) for an overview of the procedure to set it up

***REMOVED*** How to?
Following steps are applicable to:

* Customer Managed VPC: Shared VPC/Stand-alone VPC
* Databricks Managed VPC

***REMOVED******REMOVED*** Before you begin
We will be using the following terms, let’s understand them a bit better before we proceed.

* `Consumer Project` = Customer owned GCP Project where Databricks workspace is deployed. In case of a shared vpc we’ll have two projects, host project providing the vpc and service project where workspace i.e. GCE cluster and DBFS related GCS storage accounts  are created.

* `Consumer VPC` = Customer owned GCP VPC used by Databricks workspace (shared or stand alone vpc)

* `Databricks Workspace Creator` = A customer owned and managed GCP identity (User or Service Account Principal) used to create a Databricks workspace, this identity is also known as the `login user`. A login user has `Project Owner or Project Editor` and the `IAM Admin` permission on the Consumer Project (GCP project) where Databricks workspace is deployed. Please follow [this](https://docs.databricks.com/gcp/en/security/network/classic/customer-managed-vpc***REMOVED***role-requirements) doc for more details on roles/permissions required.

* `Consumer SA` = A GCP Service Account for the new workspace is created in the Databricks regional control plane project. We use the login user’s (workspace creator) OAuth token to grant the Consumer SA with sufficient permissions to setup and operate Databricks workspaces in the customer’s consumer (GCP) project. Consumer SA is required to manage classic compute plane `db-WORKSPACEID@databricks-project.iam.gserviceaccount.com`. Workspace ID is generated as part of the workspace creation process.
  `example: db-1030565636556919@prod-gcp-us-central1.iam.gserviceaccount.com`

* There's also a regional GSA called `delegate-sa@@prod-gcp-[GEO]-[REGION].iam.gserviceaccount.com` which helps with launching classic compute plane GCE based clusters.
  `example: delegate-sa@prod-gcp-us-central1.iam.gserviceaccount.com`

* `Databricks Owned GCP Projects` = There are several GCP projects involved, one each for `Databricks Regional Control Plane`, `Databricks Central Service` (required during workspace creation only), `Databricks audit log delivery [optional]` , `Databricks Unity Catalog` and `Databricks Artifacts` (databricks runtime image) Repository.

* `Databricks Control Plane IP` = Source IP from where requests into your GCP projects are originating. You may want to configure [Access Context Level](https://cloud.google.com/access-context-manager/docs/create-access-level) so that only requests coming from Databricks control plane is allowed into your GCP project, please follow [this](https://docs.gcp.databricks.com/resources/supported-regions.html***REMOVED***ip-addresses-and-domains) document for regional Control Plane NAT IPs

* `Databricks Owned GCP Projects Identities` = Following GCP Service Accounts are in use, for ex: for US East4 we have: 
  * `cluster-manager-k8s-sa@prod-gcp-us-east4.iam.gserviceaccount.com` **Only applies to legacy GKE based classic compute plane workspaces** 
  * `cluster-manager-k8s-sa@prod-gcp-us-central1.iam.gserviceaccount.com` **Only applies to legacy GKE based classic compute plane workspaces**
  * `us-central1-gar-access@databricks-prod-artifacts.iam.gserviceaccount.com` **Only applies to legacy GKE based classic compute plane workspaces**
  * `log-delivery@databricks-prod-master.iam.gserviceaccount.com`
  *  `delegate-sa@@prod-gcp-[GEO]-[REGION].iam.gserviceaccount.com` [Please visit the public annoucement for more details](https://docs.gcp.databricks.com/en/admin/cloud-configurations/gcp/gce-update.html)
  * `db-uc-storage-UUID@uc-useast4.iam.gserviceaccount.com` (applies to unity catalog, automatically created upon unity catalog initialization)

* Databricks owned Google Service Accounts naming pattern
  * `cluster-manager-k8s-sa@<prod-regional-project>.iam.gserviceaccount.com`
  * `cluster-manager-k8s-sa@<prod-regional-project>.iam.gserviceaccount.com`
  * `us-central1-gar-access@databricks-prod-artifacts.iam.gserviceaccount.com`
  * `log-delivery@databricks-prod-master.iam.gserviceaccount.com`
  * `db-uc-storage-UUID@<uc-prod-regional-project>.iam.gserviceaccount.com`
  * `delegate-sa@@prod-gcp-[GEO]-[REGION].iam.gserviceaccount.com`

A list of Databricks project numbers is listed over [here](https://docs.gcp.databricks.com/resources/supported-regions.html***REMOVED***private-service-connect-psc-attachment-uris-and-project-numbers)

* Steps to configure the perimeter
  * First create access level using Access Context Manager which would allow requests originating from control plane NAT ip into your projects
  * Create perimeter as per the yaml spec
  * As the per workspace service account aka `Consumer SA` is created at workspace creation, I would suggest that you use access level + allow calls using ANY_IDENTITY rather than locking down your VPC SC ingress rules for specific SA.

Here's a bit more info on identities being used:

* Ingress & Egress (calls made into/outof customers GCP project from databricks GCP projects)

* Databricks managed GCP identities (see Table above , Service Accounts)

* Google API’s and Methods invoked

|     |     |     |     |     |
| --- | --- | --- | --- | --- |
| **Created and Managed By** | **Identity Type**<br><br>**Service Account (SA) or User Principal (UP)** | **Example** | **Used For** | **Ingress into / Egress from Customers Project** |
| Databricks | SA  | cluster-manager-k8s-sa@\[databricks-supported-gcp-region\].iam.gserviceaccount.com | Legacy - used by GKE based clusters to access Databricks Control Plane | Egress |
| Databricks | SA  | us-central1-gar-access@databricks-prod-artifacts.iam.gserviceaccount.com | Legacy - used by GKE based clusters to access Databricks runtime images from GAR | Egress |
| Databricks | SA  | delegate-sa@@prod-gcp-[GEO]-[REGION].iam.gserviceaccount.com | used to launch GCE based clusters | Egress |
| Databricks | SA  | [db-WORKSPACEID@databricks-project.iam.gserviceaccount.com](mailto:db-WORKSPACEID@databricks-project.iam.gserviceaccount.com) | Databricks created per workspace consumer SA added to customers project | Ingress |
| Databricks | SA  | [log-delivery@databricks-prod-master.iam.gserviceaccount.com](mailto:log-delivery@databricks-prod-master.iam.gserviceaccount.com) | SA used to delivery audit logs to your storage accout | Ingress |
| Customer | UP or SA | [abc@company.com](mailto:abc@company.com) or [mysa@cust-project.iam.gserviceaccount.com](mailto:mysa@cust-project.iam.gserviceaccount.com) | Workspace Creation | Ingress |

***REMOVED******REMOVED*** **VPC SC YAML files**

Before you proceed `please make sure to update` policy yaml files with your relevant project numbers and identities

***REMOVED******REMOVED******REMOVED*** Used for Workspace Creation
* [create-ws-ingress.yaml](./../templates/vpcsc-policy/create-ws-ingress.yaml) , theres no egress during workspace creation

***REMOVED******REMOVED******REMOVED*** Used after the workspace is created
* [ingress.yaml](./../templates/vpcsc-policy/ingress.yaml) & [egress.yaml](./../templates/vpcsc-policy/egress.yaml)



***REMOVED******REMOVED*** GCLOUD commands

When using gcloud commands we need to use access-context-policy-id, for more details please see GCP help [docs](https://cloud.google.com/vpc-service-controls/docs/service-perimeters***REMOVED***create-access-policy).

|     |     |
| --- | --- |
| **Action** | **Gcloud command** |
| Create Dry Run | Please see gcloud commands sample [file](./../templates/gcloud-cmds/gcloud-run-book.txt) |
| Enforce Policy | gcloud access-context-manager perimeters **dry-run** **enforce** **\[POLICY_NAME\]** --policy=**\[**[**access-context-policy-id**](https://cloud.google.com/vpc-service-controls/docs/service-perimeters***REMOVED***create-access-policy)**\]** |
| List Policies | gcloud access-context-manager perimeters list --format=yaml --policy=**\[**[**access-context-policy-id**](https://cloud.google.com/vpc-service-controls/docs/service-perimeters***REMOVED***create-access-policy)**\]** |
| Delete Policy | gcloud access-context-manager perimeters delete **\[POLICY_NAME\]** --policy=**\[**[**access-context-policy-id**](https://cloud.google.com/vpc-service-controls/docs/service-perimeters***REMOVED***create-access-policy)**\]** |
| Update Policy | Delete Policy and then Run Create Policycall  using Ingress-Updated-Policy.yaml, Egress policy remains the same. |

***REMOVED*** Troubleshooting

***REMOVED******REMOVED*** Why do we need to use ANY_SERVICE_ACCOUNT in the policy?

At ws creation Databricks create's two storage buckets for [DBFS](https://docs.gcp.databricks.com/dbfs/index.html):

`projects/[cust-project-id]/buckets/databricks-[workspace-id]`

`projects/[cust-project-id]/buckets/databricks-[workspace-id]-system`

Using

`db-[workspace-id]@[databricks-project].iam.gserviceaccount.com`

This is an automatically generated Google service account created at WS creation and hence we cannot add this workspace specific service account to our ingress policy. If you notice it carefully, although we are using ANY_SERVICE_ACCOUNT, this identity still needs to originate from the databricks control plane project rather than any arbitrary source.
