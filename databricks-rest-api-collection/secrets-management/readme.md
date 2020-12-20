databricks rest api for secrets management
=============================================

- [Azure Databricks](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/secrets?toc=https%3A%2F%2Fdocs.microsoft.com%2Fen-us%2Fazure%2Fazure-databricks%2FTOC.json&bc=https%3A%2F%2Fdocs.microsoft.com%2Fen-us%2Fazure%2Fbread%2Ftoc.json)

- [AWS Databricks](https://docs.databricks.com/dev-tools/api/latest/secrets.html#secrets-api)


Update postman collection
===============

- get a databricks platform token aka PAT for [azure](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/authentication#authentication) or [aws](https://docs.databricks.com/dev-tools/api/latest/authentication.html#generate-a-token)
- Use PAT as an authentication bearer token to invoke API's
- workspaceUrl variable is used to decouple cloud specific databricks control plane endpoints
e.g. https://[az-region].azuredatabricks.net

- Edit postman collection [global variable](https://learning.postman.com/docs/postman/variables-and-environments/variables/) as as well as [auth header](https://learning.postman.com/docs/postman/sending-api-requests/authorization/#inheriting-auth) to update ``db_host`` and ``bearer token`` variables, these are used within the collection.
- example: workspaceUrl = https://eastus2.azuredatabricks.net and pat = dapiXXXXXXXXXXXXXXXX
