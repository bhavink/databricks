# databricks rest api collections

- Here in this repo you'll find common databricks REST API's documented. Most of them are platform agnostic, should work with [Azure](https://docs.azuredatabricks.net) as well [AWS](https://docs.databricks.com) based databricks deployments.
- In order to use these collections you'll first need to define a [postman environment](https://learning.postman.com/docs/postman/variables-and-environments/variables/) with certain global variables, these variables are then referenced through out the collection, this way you can decouple API calls from environments.

## Authentication

### Azure / AWS Databricks:
- Generate a databricks platform token aka PAT for [azure](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/authentication#authentication) or [aws](https://docs.databricks.com/dev-tools/api/latest/authentication.html#generate-a-token)

### Azure Databricks
- [Authenticate using Azure AAD tokens](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/aad/)
  - [Get an Azure Active Directory token using a service principal](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/aad/service-prin-aad-token)

### Using postman collections
- Every collection (*.postman_collection.json) file has an associated environment file (*.postman_environment.json)
- Import collections as explained over [here](https://learning.postman.com/docs/postman/collections/intro-to-collections/)
- Edit postman collection and add an [environment](https://learning.postman.com/docs/postman/variables-and-environments/variables/#variables-quick-start)

![Add Environment](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/1.png)

- Add `db_host` and `pat` or `access_token` variables, these are used within the collection.
  example: db_host = https://eastus2.azuredatabricks.net and pat = dapiXXXXXXXXXXXXXXXX

![Add Environment Variables](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/2.png) - Use PAT as an authentication bearer token to invoke API's - db_host variable is used to decouple cloud specific databricks control plane endpoints e.g. https://[your-az-region].azuredatabricks.net

![Update Collection](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/3.png)

![Use global var {{pat}} or {{access_token}}for authentication](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/4.png)
