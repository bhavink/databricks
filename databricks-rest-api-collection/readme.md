# In `Private Preview` - please reach out to your databricks team to enable this feature

# databricks rest api collections

- This documents the endpoints for the common databricks REST API's. This should work with [Azure](https://docs.azuredatabricks.net) as well [AWS](https://docs.databricks.com) based databricks deployments.
- In order to use these collections you'll first need to define a postman environment with certain global variables, these variables are then referenced through out the collection, this way you can decouple API calls from environments.

* Edit postman collection and add an [environment](https://learning.postman.com/docs/postman/variables-and-environments/variables/#variables-quick-start)

![Add Environment](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/1.png)

- Add `db_host` and `pat` variables, these are used within the collection.
  example: db_host = https://eastus2.azuredatabricks.net and pat = dapiXXXXXXXXXXXXXXXX

![Add Environment Variables](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/2.png)

![Update Collection](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/3.png)

![Use global var {{pat}} for authentication](https://github.com/bhavink/databricks/blob/master/databricks-rest-api-collection/images/4.png)
