databricks rest api for ip access control
=========================================

This documents the endpoints for the IP access list API which enables you to configure IP
whitelist/blacklist for Databricks. This applies to databricks workspaces or web front end, command line interface as well as rest api endpoints.

Customers have a security requirement to restrict access to the DB Control plane to specific IP addresses. The use case from the customer stand point is that it requires all access to DB to be routed through their data centers. They ensure that employees VPN or connect through their data center which enforces their policies before connecting to our control plane.

This means they want to be able to add/remove IP addresses that can connect to databricks control plane as and when they make network changes or add a new datacenter.

This is what this feature enables. It will provide admins a way to set a whitelist and blacklist for CIDR / IPs that can access Databricks. 


Update postman collection
===============

- get a databricks platform token aka PAT for [azure](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/authentication#authentication) or [aws](https://docs.databricks.com/dev-tools/api/latest/authentication.html#generate-a-token)
- Use PAT as an authentication bearer token to invoke API's
- workspaceUrl variable is used to decouple cloud specific databricks control plane endpoints
e.g. https://[your-az-region].azuredatabricks.net

- Edit postman collection and add an [environment](https://learning.postman.com/docs/postman/variables-and-environments/variables/#variables-quick-start)
- Add ``workspaceUrl`` and ``pat`` variables, these are used within the collection.
example: db_host = https://eastus2.azuredatabricks.net and pat = dapiXXXXXXXXXXXXXXXX
