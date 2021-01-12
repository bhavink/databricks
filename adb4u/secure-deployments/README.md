Secure Deployments
==============
Documenting and sharing security best practices related to platform deployment and configuration.


Topics covered
------------
-  Deploy a workspace using your own VNET
-  Enable cluster with No Public IP's (i.e. databricks cluster will only have priavte ip addresses)
-  Configure an egress appliance to filter outgoing traffic from databricks clusters

Guide
-------------
-  
-  [Data Exfiltration Prevention Blog](https://databricks.com/blog/2020/03/27/data-exfiltration-protection-with-azure-databricks.html)


Documentation
-------------

For the latest CLI documentation, see

- [Databricks](https://docs.databricks.com/user-guide/dev-tools/databricks-cli.html)
- [Azure Databricks](https://docs.azuredatabricks.net/user-guide/dev-tools/databricks-cli.html)


Databricks Connect
------------------
Allows you to connect your favorite IDE (IntelliJ, Eclipse, PyCharm, and so on), notebook server (Zeppelin, Jupyter, RStudio, etc.), and other custom applications to Azure Databricks clusters and run Spark code.

To install databricks dbconnect please follow instructions mentioned over here

- [Databricks](https://docs.databricks.com/user-guide/dev-tools/db-connect.html)
- [Azure Databricks](https://docs.azuredatabricks.net/user-guide/dev-tools/db-connect.html)

Databricks Token
------------------
To authenticate and access Databricks REST/CLI APIs, you use personal access tokens. Tokens are similar to passwords; you should treat them with care. Tokens expire and can be revoked.

Please follow instructions mentioned over here to get one

- [Databricks](https://docs.azuredatabricks.net/api/latest/authentication.html#token-management)
- [Azure Databricks](https://docs.azuredatabricks.net/api/latest/authentication.html#token-management)

Projects
------------------
Under /databricks you shall find various spark projects, each project contains a readme.txt file with details on
- `requirements`
- `how to build, run and deploy`
