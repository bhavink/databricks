***REMOVED*** Objectives
Databricks provides two flavors of compute
- Clasic compute
- Serverless compute

* Each workspace is provisioned within the customer's GCP project. [Classic compute](https://docs.gcp.databricks.com/clusters/index.html) resides within customers project and utlizes customers vpc.
* Life cycle of a databricks cluster (classic or serverless) is managed by Databricks Control Plane.
* Compute instance type aka `node's` used by a Databricks cluster is backed by GCE instances aka nodes
* Nodes have Private IP addresses only (classic and serverless compute)
  
* To provide a secure logical isolation between databricks clusters within same workspace (classic or serverless) Databricks implements logical namespace’s i.e no two clusters can talk to each other directly, communication is always managed thru databricks control plane.

***REMOVED******REMOVED*** Optionally
* Configure [VPC Service Control](./security/Configure-VPC-SC.md) to prevent data exfiltration
* Lock down [VPC firewall rules](./security/LockDown-VPC-Firewall-Rules.md)
  