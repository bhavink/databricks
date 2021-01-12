Secure Deployments
==============
Documenting and sharing security best practices related to platform deployment and configuration.


Projects
------------

-  Python Version > 3.5 and greater
-  Databricks CLI
-  Databricks dbconnect
-  Databricks platform token
-  Python dev ide's ex: Pycharm
-  Scala dev ide's ex: intellij
-  Conda (Python package, dependencies and environment management)

Conda environments
------------------

-  conda yml files are provided for py projects and it takes care of creating the required environment to run these projects
-  make sure you have conda installed and then using ``conda env create -f environment.yml`` you'll be able to create required environments, this takes care of installing databricks cli, mlflow and dbconnect libs automatically for you.

Databricks CLI
---------------

To install databricks cli simply run
``pip install --upgrade databricks-cli``

Then set up authentication using username/password or 

[authentication token](https://docs.databricks.com/api/latest/authentication.html#token-management) Credentials are stored at ``~/.databrickscfg``.

- ``databricks configure`` (enter hostname/username/password at prompt)
- ``databricks configure --token`` (enter hostname/auth-token at prompt)

Multiple connection profiles are also supported with ``databricks configure --profile <profile> [--token]``.
The connection profile can be used as such: ``databricks workspace ls --profile <profile>``.

To test that your authentication information is working, try a quick test like ``databricks workspace ls``.

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
