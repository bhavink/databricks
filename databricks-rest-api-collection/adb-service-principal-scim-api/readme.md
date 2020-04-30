# In `Private Preview` - please reach out to your databricks team to enable this feature

# databricks rest api for General Permissions

This documents the endpoints for the Permissions API which enables you to set permissions on objects in Databricks.
Currently, you can set permissions on the following objects using these APIs - **clusters, jobs, pools, notebooks, instance_pools and directories**.

## Please note that in order to run these collection you'll need at-least one object of each type i.e. cluster, job, notebook, directory, instance-pool.


### What are the goals?

- Retrieve Permissions on an Object {clusters, instance-pools, jobs, notebooks, directories, mlflow-registered-models}
- Add or Modify Permissions on an Object (HTTP Verb PATCH)
- Set or Delete Permissions on an Object (HTTP Verb PUT)
  A PUT request will replace all direct permissions on the cluster object. Delete requests can be made by making a GET request to retrieve the current list of permissions followed by a PUT request by removing entries to be deleted.

### Supported permissions

| Name  | Allowed Objects |
|---|---|
| CAN_MANAGE  | Clusters, Instance-pools, Jobs, Notebooks, Directories, Registered Models  |
| CAN_RESTART | Clusters  |
| CAN_ATTACH_TO  | Clusters, Instance-pools  |
| CAN_MANAGE_RUN  | Jobs  |
| IS_OWNER  | Jobs  |
| CAN_VIEW  | Jobs  |
| CAN_READ  | Notebooks, Directories, Registered Models  |
| CAN_RUN  | Notebooks, Directories  |
| CAN_EDIT  | Notebooks, Directories, Registered Models  |

- These permission levels correlate directly to the permissions that you can configure in the UI.  For details on the abilities associated with these permission levels, check the following links: 
  - Clusters [AWS](https://docs.databricks.com/administration-guide/admin-settings/cluster-acl.html#cluster-access-control) || [Azure](https://docs.azuredatabricks.net/administration-guide/admin-settings/cluster-acl.html#cluster-access-control)
  - Jobs [AWS](https://docs.databricks.com/administration-guide/access-control/jobs-acl.html#jobs-access-control) || [Azure](https://docs.azuredatabricks.net/administration-guide/access-control/jobs-acl.html#jobs-access-control)
  - Instance pools [AWS](https://docs.databricks.com/administration-guide/access-control/pool-acl.html#instance-pool-access-control) || [Azure](https://docs.azuredatabricks.net/administration-guide/access-control/pool-acl.html#instance-pool-access-control)
  - Notebooks [AWS](https://docs.databricks.com/administration-guide/access-control/workspace-acl.html#workspace-access-control) || [Azure](https://docs.azuredatabricks.net/administration-guide/access-control/workspace-acl.html#workspace-access-control)
  - Directories [AWS](https://docs.databricks.com/administration-guide/access-control/workspace-acl.html#workspace-access-control) || [Azure](https://docs.azuredatabricks.net/administration-guide/access-control/workspace-acl.html#workspace-access-control)


### FAQ

- Where can I find object IDs?
  See [How to get Workspace, Cluster, Notebook, and Job Details](https://docs.azuredatabricks.net/user-guide/faq/workspace-details.html#how-to-get-workspace-cluster-notebook-and-job-details) for where to find object ids.

- Can we set permissions on all users?
  - Yes, built in `users` group can be used to set permissions for all users.

- Can I give someone the Can Manage permission on Jobs?
  - The Can Manage permission is reserved for administrators. See Job permissions

- How are Job cluster permissions configured?
  - Clusters created during the run of a Job are initially configured using the permissions set on the Job:
  - Is Owner -> CAN_MANAGE
  - Can Manage Run -> CAN_MANAGE
  - Can View -> CAN_ATTACH_TO
  - These permissions that are inherited from a Job will have inherited set to true, and contain the parent Job’s ACL object_id in its inherited_from_object field in the form of /jobs/\$jobId.
  - If changes are made to a Job’s permissions, any clusters created by that Job will also have those permissions.
  Permissions can also be set directly on the Jobs cluster using the clusters permissions API

- Are there any directories which have some restrictions?
  - Root Directory: The admins group by default has CAN_MANAGE permission on the root directory and this permission cannot be removed.
  - Home directory: Each user has a designated home directory and the user by default has CAN_MANAGE permission on it which cannot be removed.
  - Trash and Shared directories: Modifications to permissions on these directories is not allowed.

### Update postman collection

- get a databricks platform token aka PAT for [azure](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/authentication#authentication) or [aws](https://docs.databricks.com/dev-tools/api/latest/authentication.html#generate-a-token)
- Use PAT as an authentication bearer token to invoke API's
- db_host variable is used to decouple cloud specific databricks control plane endpoints
  - e.g. https://[your-az-region].azuredatabricks.net

- Edit postman collection and add an [environment](https://learning.postman.com/docs/postman/variables-and-environments/variables/#variables-quick-start)
- Add `db_host` and `pat` variables, these are used within the collection.
  example: db_host = https://eastus2.azuredatabricks.net and pat = dapiXXXXXXXXXXXXXXXX
- We set several global variables using [Tests](https://learning.postman.com/docs/postman/scripts/test-scripts/) section of each step, these variables are used with object specific operations (list, update)
