***REMOVED*** Goal:
Demonstrate databricks platform integration with vsts

***REMOVED*** Pre-req's:
- <B>[Make sure you read this before you proceed](https://databricks.com/blog/2017/10/30/continuous-integration-continuous-delivery-databricks.html)</B>
- [git tools on your system](https://git-scm.com/download/mac)
- [databricks-cli](https://docs.azuredatabricks.net/user-guide/dev-tools/index.html)
- [databricks-rest-api](https://docs.azuredatabricks.net/api/latest/index.html***REMOVED***rest-api-v2)
- [vsts cli](https://docs.microsoft.com/en-us/cli/vsts/overview?view=vsts-cli-latest)
- [visual code](https://code.visualstudio.com/download)  (optional) 

***REMOVED*** UseCase:
- Sharing code developed using databricks hosted notebook environment via vsts/git.
- we start with a user project called "spark-r-us", we'll have scala/r/py/java code created using databricks and scm is vsts.

***REMOVED*** Key Terms:
- <b>Local dev repo</b> (aka local repo) = remote repo that is on an end user system, this is the user dev environment
- <b>VSTS repo</b> (aka vsts) = master repo (or a branch) where the local repo sync's
- <b>Databricks workspace</b> (aka workspace) = databricks hosted notebook environment used by users to author, test and run spark code
- <b>DBFS</b> (aka dbfs) = Databricks File System, this is based on Azure BLOB storage, for this discussion I have created a mount point point on DBFS which points to a ADLS, we use this ADLS location as our dependencies/libraries repo.

***REMOVED*** Development in databricks 
![development in databricks](https://databricks.com/wp-content/uploads/2017/10/CI-CD-BLOG3B@2x-300x247.png)

***REMOVED*** High level design, workflow and project structure:
- Code could be built inside databricks hosted notebooks or using your fav IDE installed on local dev box.
- Dependencies like jars, py .egg or .whl files, r packages used by your code is saved and utilized from Azure ADLS or BLOB storage.
- Dependencies could also be provided via maven coordinates, cran repo's or PyPi packages
- databricks Command Line Interface (CLI) will be used to manage/sync following assets between databricks workspace/dbfs and local repo
    - databricks workspaces = /Users/bhavin.kukadia@databricks.com/cicd/spark-r-us            
    - databricks file system (dbfs)
        - dbfs:/mnt/bhavin/adls/cicd/spark-r-us/env-config/ = init scripts, cluster and jobs templates
        - dbfs:/mnt/bhavin/adls/cicd/spark-r-us/libraries/ = lib's / dependencies used our code
        - dbfs:/mnt/bhavin/adls/cicd/spark-r-us/target = code to move to higher environments, compiled/tested/built code        
    - local repo (remote) = dev environment, synced with azure vsts = /0-vsts/spark-r-us
    - vsts repo (master) = /field-eng/spark-r-us

***REMOVED*** Development approach
The recommended approach is to set up a development environment per user. Each user pushes the notebook to their own personal folders in the interactive workspace. They work on their own copies of the source code in the interactive workspace. They then export it via API/CLI to their local development environment and then check-in to their own branch before making a pull request against the master branch. They also have their own small clusters for the development.
![local development](https://databricks.com/wp-content/uploads/2017/10/CI-CD-BLOG2@2x-1024x547.png)

***REMOVED*** Steps:
- subscribe to azure vsts and create a team project backed by git, in this case it's called field-eng.
- configure vsts to utilize git alias (https://docs.microsoft.com/en-us/cli/vsts/git?view=vsts-cli-latest***REMOVED***configure-vsts-cli-to-add-git-aliases)

- ***REMOVED******REMOVED******REMOVED***To setup the dev environment, users can do the following:

    - Create a branch and checkout the code to their computer.
    - Copy the notebooks from local directory to Databricks’ workspace using the workspace command line interface (CLI)
        
        `databricks workspace import_dir /spark-r-us/src/ /Users/bhavin@databricks.com/cicd/spark-r-us`

    - Copy the libraries from local directory to DBFS using the DBFS CLI

        `databricks fs cp /spark-r-us/libraries/jars/etl-2.1-assembly.jar dbfs:/mnt/bhavin/adls/cicd/spark-r-us/libraries/jars/etl-2.1-assembly.jar`

    - Create a cluster using the API or UI.
    - Attach the libraries in DBFS to a cluster using the libraries API

- ***REMOVED******REMOVED******REMOVED***Iterative development
    - It is easy to modify and test the change in the Databricks workspace and iteratively test your code on a sample data set. After the iterative development, when you want to check in your changes, you can do the following:

    - Download the notebooks
       
       `cd /0-vsts/field-eng`

       `databricks workspace export_dir /Users/bhavin@databricks.com/cicd/ . --profile adb-field-eng`


    - this exports all of the contents including dir structure from databricks workspace to local repo.

    - Download the notebooks
    - Create a commit and make a pull request in version control for code review.

***REMOVED******REMOVED******REMOVED*** Usefull commands:
`mkdir /0-vsts/`

`cd /0-vsts/` 

`git clone https://bhavink.visualstudio.com/field-eng/_git/field-eng` 


username: yourUname

password: ********


`cd 0-vsts/field-eng`

- field-eng is synced up with vsts on azure, which is backed by git, this is the central repo for databricks projects
- using databricks cli we will sync databricks workspace/notebooks with our local repo


`databricks fs ls dbfs:/mnt/bhavin/adls/cicd/libs --profile adb-field-eng`

`databricks fs cp --recursive /spark-r-us/libraries/ dbfs:/mnt/bhavin/adls/cicd/spark-r-us/ --profile adb-field-eng`


***REMOVED******REMOVED******REMOVED*** install lib from dbfs on cluster

`databricks libraries install --cluster-id 0412-183021-joule152 --jar dbfs:/mnt/bhavin/adls/cicd/spark-r-us/libraries/jars/spark-hive-udf_2.11-0.1.0.jar --profile adb-field-eng`

`databricks libraries list --cluster-id 0412-183021-joule152 --profile adb-field-eng`


***REMOVED******REMOVED******REMOVED*** export databricks workspace to local dev repo
databricks workspace export_dir /Users/bhavin.kukadia@databricks.com/cicd/spark-r-us ./spark-r-us --profile adb-field-eng

- Copy local files to dbfs

`databricks fs cp -r ./env-config/init-scripts/ dbfs:/mnt/bhavin/adls/cicd/spark-r-us/env-config/init-scripts/ --profile adb-field-eng`

- Copy local libs (jars, packages, egg, who files) to dbfs

`databricks fs cp -r ./libraries dbfs:/mnt/bhavin/adls/cicd/spark-r-us/libraries/ --profile adb-field-eng`

***REMOVED******REMOVED******REMOVED*** cluster creation

- Create a new cluster, persist cluster logs to adls location

```
curl -n \
-X POST -H 'Content-Type: application/json' \
-d '{
"cluster_name": "bk-etl-job-server",
"spark_version": "4.1.x-scala2.11",
      "spark_conf": {
          "spark.databricks.io.cache.enabled": "true",
          "spark.rdd.compress": "true",
          "spark.sql.crossJoin.enabled": "true"
      },
      "node_type_id": "Standard_L4s",
      "driver_node_type_id": "Standard_L4s",
      "autoscale": {
        "min_workers": 2,
        "max_workers": 10
        },
      "cluster_log_conf": {
          "dbfs": {
              "destination": "dbfs:/mnt/bhavin/adls/cluster-logs"
          }
      },
      "custom_tags": {
            "Team": "ETLProd",
            "Project": "Overnight Data Feed Extraction Prod",
            "CostCenter": "Prod101",
            "Env": "Prod"
        },      
      "autotermination_minutes": 120,
      "enable_elastic_disk": true
}' \
https://eastus2.azuredatabricks.net/api/2.0/dbfs/put -H "Authorization: Bearer your-token"
```
- attach libs to cluster just created

```
curl -n \
-X POST -H 'Content-Type: application/json' \
-d '
{
  "cluster_id": "10201-my-cluster",
  "libraries": [
    {
      "jar": "dbfs:/mnt/libraries/library.jar"
    },
    {
      "egg": "dbfs:/mnt/libraries/library.egg"
    },
    {
      "whl": "dbfs:/mnt/libraries/mlflow-0.0.1.dev0-py2-none-any.whl"
    },
    {
      "whl": "dbfs:/mnt/libraries/wheel-libraries.wheelhouse.zip"
    },
    {
      "maven": {
        "coordinates": "org.jsoup:jsoup:1.7.2",
        "exclusions": ["slf4j:slf4j"]
      }
    },
    {
      "pypi": {
        "package": "simplejson",
        "repo": "http://my-pypi-mirror.com"
      }
    },
    {
      "cran": {
        "package: "ada",
        "repo": "http://cran.us.r-project.org"
      }
    }
  ]
}' \
https://eastus2.azuredatabricks.net/api/2.0/dbfs/put -H "Authorization: Bearer your-token"
```
