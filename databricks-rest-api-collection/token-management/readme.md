databricks rest api for platform token management
=================================================
- Token Management provides Databricks administrators with more insight and control over  Personal Access Tokens in their workspaces. It consists of three pieces: 

- The Token Management API enables Databricks admins to monitor these Personal Access Tokens.

- The Maximum Token Lifetime workspace configuration gives admins the ability to control the lifetime of future tokens in their workspaces. 

- Token Permissions allow admins to control which users can create and use tokens.

- The feature is a <b>Premium or OpSec</b> only





Update postman collection
===============

- get a databricks platform token aka PAT for [azure](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/authentication#authentication) or [aws](https://docs.databricks.com/dev-tools/api/latest/authentication.html#generate-a-token)
- Use PAT as an authentication bearer token to invoke API's
- workspaceUrl variable is used to decouple cloud specific databricks control plane endpoints
e.g. `adb-<workspace-id>.<random-number>.azuredatabricks.net`
- Edit postman collection [global variable](https://learning.postman.com/docs/postman/variables-and-environments/variables/) as as well as [auth header](https://learning.postman.com/docs/postman/sending-api-requests/authorization/#inheriting-auth) to update ``workspaceUrl`` and ``bearer token`` variables, these are used within the collection.
- example: db_host = https://adb-12345678.11.azuredatabricks.net and pat = dapiXXXXXXXXXXXXXXXX
