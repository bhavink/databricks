Project Cryptography
------------
In this project we'll see how to create encrypt and decrypt pyspark UDFs.

Requirements
------------

-  Python Version > 3.5 or > 3.6
-  Databricks CLI
-  Python dev ide's ex: Pycharm
-  Conda - optional (Python package, dependencies and environment management)

Setup
-----
-  ``pip install pycryptodome`` (at the time of writing this I have used py 3.5.6 with pycryptodome 3.8.1)

**highly recommended**

- install `pycharm community edition <https://www.jetbrains.com/pycharm/download>`_.

- create a system environment variable called DB_BEARER_TOKEN or what ever you want, we will use this later in the project along with CURL, value contains token generated earlier during cli profile configuration

``export DB_BEARER_TOKEN = "Authorization: Bearer dapiXXXXXXXXXXXXXXX"``

- REST API client like `postman <https://www.getpostman.com/>`_. [in case if you do not have curl installed]


Executing code
--------------

-  Build an .egg file, attach it as a lib to databricks cluster and then invoke UDF's either inside databricks notebooks our your pyspark/sql code


clone project on local system and run setup test
------------------------------------------------

``git clone https://github.com/bhavink/databricks.git``

``pycharm ide -> file -> open -> browse to the /databricks/cryptography dir``

Run as an egg file attached to databricks cluster
-------------------------------------------------
-  import notebook [DataEncryptionUsingEgg.ipynb] into your databricks instance, it uses py .egg lib file that you'll build in subsequent steps

-  we will be using databricks CLI, REST API and curl commands (or your fav REST API client)

-  run this command from /cryptography

``python setup.py bdist_egg``

- this creates an egg file in the ./dist folder, lets copy .egg to databricks file system aka dbfs

- you may need to adjust the following cli commands so that it uses the right cli profile

``databricks fs cp dist/cryptography-0.0.0-py3.5.egg dbfs:/tmp/jobs/crypto/cryptography-0.0.1-py3.5.egg --overwrite --profile adb-field-eng``


``databricks libraries install --cluster-id 0215-130447-volt965 --egg dbfs:/tmp/db-connect/egg/cryptography-0.0.1-py3.5.egg --profile adb-field-eng``

**if you update code, rebuild egg file then everytime you attach a new file, cluster needs to be restarted**

``databricks clusters restart --cluster-id 0215-130447-volt965 --profile adb-field-eng``
