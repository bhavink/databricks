
databricks rest api for cluster policy
=========================================

This documents the endpoints for the Cluster Policy API

### What are Cluster Policies
A Cluster Policy (aka Cluster Blueprint or Cluster Template) limits the ability to create clusters based on a set of rules. A policy defines those rules as of limitations on the attributes used for the cluster creation. Cluster Policies define ACLs to limit their usage to a specific set of users and or groups. Users who have access to a specific cluster policy can create clusters of these policy without having additionally the create cluster permission.

### What are the goals
- Limiting users to create clusters with prescribed settings
- Simplifying the user interface and enabling more users to start own clusters (by fixing and hiding some values).
- Basic cost control through limiting per cluster maximum costs (by setting limits on attributes which values contribute to hourly price)

### How Policies are defined
- For the private preview the policies will be defined by Databricks based on customer requirements. The policy rules take the form of a JSON structured document.

### Supported rules
- Fixed value with disabled control element
- Fixed value with control hidden in the UI (value will still be visible on the cluster configuration detail page)
- Attribute value limited to a certain set of values (either whitelist or blacklist)
- Attribute value matching a given regex
- Numeric attribute limited to a certain range

### Policies API and Cluster Permissions API documentation with the customer.
- [Policy feature details](https://docs.databricks.com/administration-guide/clusters/policies.html)
- [REST API](https://docs.databricks.com/dev-tools/api/latest/policies.html)


### Update postman collection


- get a databricks platform token aka PAT for [azure](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/authentication#authentication) or [aws](https://docs.databricks.com/dev-tools/api/latest/authentication.html#generate-a-token)
- Use PAT as an authentication bearer token to invoke API's
- db_host variable is used to decouple cloud specific databricks control plane endpoints
e.g. https://[your-az-region].azuredatabricks.net

- Edit postman collection and add an [environment](https://learning.postman.com/docs/postman/variables-and-environments/variables/#variables-quick-start)

![Add Environment](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/1.png)

- Add ``db_host`` and ``pat`` variables, these are used within the collection.
example: db_host = https://eastus2.azuredatabricks.net and pat = dapiXXXXXXXXXXXXXXXX

![Add Environment Variables](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/2.png)

![Update Collection](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/3.png)

![Use global var {{pat}} for authentication](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/4.png)
