
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
