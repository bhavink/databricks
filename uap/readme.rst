Project UAP
------------
In this project we'll see how to build pyspark code locally using an IDE like pycharm and then run it on a remote databricks spark cluster.

**Predictive Analytics using Databricks UAP, dbconnect and MLFlow**

- Data engineering
  - Ingest -> Prepare -> Deliver
- Data science
  - Feature engineering
  - Model Training
  - Model Life Cycle Management
    - Experiment Tracking
    - Artifact Packaging
    - ML Model Serving
  - Model Scoring
  
Requirements
------------

-  Python Version > 3.5 or > 3.6
-  Databricks CLI
-  Databricks dbconnect
-  Databricks platform token
-  Python dev ide's ex: Pycharm
-  Conda (Python package, dependencies and environment management)

Setup
-----

-  create conda environment based on .yml files. 
-  there are 2 yml files available with all of the required dependencies.
-  dbconnect-3.5.6.yml is based on py 3.5 and dbconnect-3.6.5 is based on py 3.6
-  to create conda environment run ``conda env create -f dbconnect-3.5.6.yml``

-  **configure dbconnect within your conda environment**

  -  `configure dbconnect azure <https://docs.azuredatabricks.net/user-guide/dev-tools/db-connect.html***REMOVED***step-2-configure-connection-properties>`_.

  -  `dbconnect on aws databricks <https://docs.databricks.com/user-guide/dev-tools/db-connect.html***REMOVED***step-2-configure-connection-properties>`_.

-  **highly recommended**

- install `pycharm community edition <https://www.jetbrains.com/pycharm/download>`_.

- create a system environment variable called DB_BEARER_TOKEN or what ever you want, we will use this later in the project along with CURL, value contains token generated earlier during cli profile configuration

``export DB_BEARER_TOKEN = "Authorization: Bearer REDACTED_DATABRICKS_PAT"``

- REST API client like `postman <https://www.getpostman.com/>`_. [in case if you do not have curl installed]


Executing code
--------------

-  There are 2 options available to run it
  -  Run review_main.py as a py script i.e. execute on your local box using conda env created
  -  Build an .egg file, attach it as a lib to databricks cluster and then invoke reviews_main.py as a python job on databricks cluster

clone project on local system and run setup test
------------------------------------------------


``git clone https://github.com/bhavink/databricks.git``

``pycharm ide -> file -> open -> browse to the /databricks/uap dir``

``navigate to test_env_setup.py in the UI -> Run``

-  this will ask you to create a configuration, create a run config where

  -  Script path = path to test_env_setup.py
  -  Parameters = "databricks://adb-field-eng" "/databricks-datasets/amazon/data20K" "/databricks-datasets/amazon/test4K"
  -  Environment -> Python interpretor = your dbconnect conda environment
  
``click run``

-  after your test is successful you are ready to run rest of the programs
-  reviews_main.py is well documented with all of the neccessary information, please follow instructions to execute project
-  you have to follow same steps to run reviews_main.py in pychamr as mentioned above, the only diff is that it wont take any parameters at runtime as all of the required variables are supplied within the file.

Run as a py script
------------------
-  Update the following variables in reviews_main.py so that it reflects right values for:

**datasets used are already available on databricks platform, both azure and aws**

- ``data_file_location = "/databricks-datasets/amazon/data20K"``
- ``scoring_data_file_location = "/databricks-datasets/amazon/test4K"``

**mlflow server is hosted on databricks and is available to all of its customers, I have not tested this on community edition**

- ``mlflow_experiment_file_path = "/Shared/experiments/bk-uap-reviews-dbconnect-exp"``
- ``mlflow_tracking_uri = "databricks://adb-field-eng"`` **adb-field-eng** is my databricks cli profile name
- ``mlflow_tracking_uri = "databricks"`` **remove cli profile from the uri if runinng via an egg file**
- ``mlflow_search_query = "metrics.accuracy >= 0.80"``

**ML pipeline hyper parameters**

- ``numFeatures = [500,1000]``
- ``regParam = [0.01,0.1]``
- ``netParam = [0.1,02]``
- ``cvNumFolds = 3`` **takes an integer**
    

Run as an egg file attached to databricks cluster
-------------------------------------------------
-  all of the required files are located inside ``/uap/run_as_egg_file``

-  here we will be using databricks CLI, REST API and curl commands (or your fav REST API client)

-  activate conda env configured with dbconnect, my conda env is called **dbconnect**

``source activate dbconnect``

-  run this command from /uap

``python setup.py bdist_egg``

-  this creates an egg file in the /uap/dist folder, lets copy .egg and reviews_main.py to databricks file system aka dbfs

- you may need to adjust the following cli commands so that it uses the right cli profile

``databricks fs cp nlp/reviews_main.py dbfs:/tmp/jobs/uap/reviews_main.py --overwrite --profile adb-field-eng``

``databricks fs cp dist/uap_nlp_dbconnect-0.0.0-py3.5.egg dbfs:/tmp/jobs/uap/uap_nlp_dbconnect-0.0.0-py3.5.egg --overwrite --profile adb-field-eng``

**if you update code, rebuild egg file then everytime you attach a new file, cluster needs to be restarted**

``curl -X POST -H $ADB_FIELD_ENGG_TOKEN" -d @restart_cluster.json https://eastus2.azuredatabricks.net/api/2.0/clusters/restart``

-  submit a py job which utilizes attached egg file

-  $ADB_FIELD_ENGG_TOKEN == databricks platform token saved as a local system environment variable

``export ADB_FIELD_ENGG_TOKEN="Authorization: Bearer REDACTED_DATABRICKS_PAT"``

``curl -X POST -H "$ADB_FIELD_ENGG_TOKEN" -d @runs_submit.json  https://eastus2.azuredatabricks.net/api/2.0/jobs/runs/submit``

-  the above command returns a job_id, we use it to get job status

-  get job status

``curl -X GET -H "$ADB_FIELD_ENGG_TOKEN"  https://eastus2.azuredatabricks.net/api/2.0/jobs/runs/get?run_id=XXXX``
