databricks rest api for groups management
=========================================

The Groups API allows you to manage groups of users.
[AWS Databricks](https://docs.databricks.com/dev-tools/api/latest/groups.html***REMOVED***groups-api) and [Azure Databricks](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/groups?toc=https%3A%2F%2Fdocs.microsoft.com%2Fen-us%2Fazure%2Fazure-databricks%2FTOC.json&bc=https%3A%2F%2Fdocs.microsoft.com%2Fen-us%2Fazure%2Fbread%2Ftoc.json)



Update postman collection
===============

- get a databricks platform token aka PAT for [azure](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/authentication***REMOVED***authentication) or [aws](https://docs.databricks.com/dev-tools/api/latest/authentication.html***REMOVED***generate-a-token)
- Use PAT as an authentication bearer token to invoke API's
- db_host variable is used to decouple cloud specific databricks control plane endpoints
e.g. https://[az-region].azuredatabricks.net

- Edit postman collection [global variable](https://learning.postman.com/docs/postman/variables-and-environments/variables/) as as well as [auth header](https://learning.postman.com/docs/postman/sending-api-requests/authorization/***REMOVED***inheriting-auth) to update ``db_host`` and ``bearer token`` variables, these are used within the collection.
