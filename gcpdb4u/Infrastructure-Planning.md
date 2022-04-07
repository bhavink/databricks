# Consuming Databricks on GCP
Databricks service is available as a GCP market place offering and the unit of deployment is called a [`workspace`](https://docs.gcp.databricks.com/getting-started/concepts.html#workspace), from here onwards we'll be using `workspace` to refer to databricks service through out this guide.

Databricks is a `Managed Service` and is fully hosted, managed, and supported by the Databricks. Although you register with the Databricks to use the service, Google handles all billing.

# Try Databricks
* Trying databricks in an indidvidual capacity? here's your 14 days free [trial](https://docs.gcp.databricks.com/getting-started/try-databricks-gcp.html#start-a-databricks-free-trial) Please note that free trial requires credit card and the trial is converted to a pay-as-you-go subscription after 14 days. Not ready for this? then check out our [community edition](https://community.cloud.databricks.com/login.html), no credit card required.
* If your company has a contract subscription in place with GCP, you have two options:
  *  start the free trial and at the end of trial become a pay-as-you-go customer or end the trial.
  *  have a need to extend the trial then reach out to your databricks representative or send an email to `sales@databricks.com` about how to create/extend your subscription with a Google Marketplace Private Offer.
*  At the end of the trial, you are automatically subscribed to the plan that you have been on during the free trial. You can cancel your subscription at any time.

# Databricks to GCP mapping

| Databricks  | Relationship  | GCP  |
|---|---|---|
| Account  |  1:1 maps to | [Billing Account](https://cloud.google.com/billing/docs/concepts#overview)  |
| Subscription | maps to | Entitlements* |
| Workspaces | resides in | [Consumer Project](https://cloud.google.com/resource-manager/docs/creating-managing-projects) |
| Worker Environment (dataplane) | 1:1 maps to | GKE cluster |
| Databricks Cluster | 1:1 maps to | GKE namespace |
*Represents purchase, pricing, and payment mechanism for an account

# Availability Regions
Please refer to public doc site for [supported regions](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/regions.html)

# Things to remember

* Each Databricks account is mapped to one GCP Billing Account (1:1)
* Customer can have more than one account with Databricks
* Subscription is a Databricks concept, it represent various [tiers](https://databricks.com/product/gcp-pricing) available to our customers.
* Subscription tiers dictates workspace features as well [pricing](https://databricks.com/product/gcp-pricing/instance-types)
* Subscription [cost](https://databricks.com/product/pricing) does not include cloud resource cost (storage, compute, network)
* Databricks pricing is based on your compute usage called DBU. Storage, networking and related costs will vary depending on the services you choose and your cloud service provider.
* A Databricks Unit (DBU) is a normalized unit of processing power on the Databricks Lakehouse Platform used for measurement and pricing purposes. The number of DBUs a workload consumes is driven by processing metrics, which may include the compute resources used and the amount of data processed.
* Databricks Unit (DBU), which is a unit of processing capability per hour, billed on per-second usage. See [pricing](https://databricks.com/product/gcp-pricing) for more details

# Recommendations

* Read thru pricing and subscription tiers details before your begin.
* Premium tier includes security features like [Customer Managed VPC](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/customer-managed-vpc.html) and [IP Access List](https://docs.gcp.databricks.com/security/network/ip-access-list.html) which are are a must have for most of the enterprises.
* Subscription tiers could be changed but once you are on a higher tier you cannot downgrade to a lower one.
* Subscription tier applies at account level so all of the workspace belonging to the account have same features.
* Take advantage of [free training](https://docs.gcp.databricks.com/getting-started/free-training.html) to familiarize yourself with the offering.

# Workspace Architecture
From [here](https://docs.gcp.databricks.com/getting-started/overview.html#high-level-architecture): Databricks is built on GCP and operates out of a `control plane` and a `data plane`.

The `control plane` includes the backend services that Databricks manages in its own Google Cloud account. Notebook commands and many other workspace configurations are stored in the control plane and encrypted at rest.

The `data plane` is managed by `your` Google Cloud account and is where `your data resides`. This is also where `data is processed`. You can use Databricks [connectors](https://docs.gcp.databricks.com/data/data-sources/index.html) so that your databricks clusters can `connect to data sources` to ingest data or for storage. You can also ingest data from external streaming data sources, such as events data, streaming data, IoT data, and more.

The following diagram represents the flow of data for Databricks on Google Cloud:

![workspace-architecture](https://docs.gcp.databricks.com/_images/databricks-architecture-gcp.png)

*Things to remember*
* There's a 1:1 mapping between a workspace and GKE cluster and a workspace can atmost have 1 GKE cluster
* GKE cluster is managed by Databricks and runs under Customer's GCP Project, using customer's vpc
* Workspace use GKE cluster in a multi-tenant fashion i.e. each Databricks cluster is mapped to a GKE namespace and is isolated from other databricks clusters running within same GKE, more details under `Data Plane Architecture` section
* There's a:
  * 1:1 mapping between a workspace and GCP Project
  * A workspace  

# Workspace Deployment Considerations
* How many workspaces do I need?
* Do I need workspace per project or a team or a buisness unit?
* Can I share workspaces among teams?
