from __future__ import print_function

import argparse
import sys
from nlp.reviews.utils import *
from mlflow import mlflow

spark = get_spark()
logger = get_logger()

try:
    mlflow_tracking_uri = sys.argv[1]  ***REMOVED*** "databricks://adb-field-eng"
    data_file_location = sys.argv[2]  ***REMOVED*** "/databricks-datasets/amazon/data20K"
    scoring_data_file_location = sys.argv[3]  ***REMOVED*** "/databricks-datasets/amazon/test4K"
except:
    ***REMOVED*** parser.print_help()
    logger.warn("the following arguments are required: mlflow_tracking_uri, data_file_location, scoring_data_file_location")
    logger.warn("received no args at runtime, using defaults")
    logger.warn("\n")
    mlflow_tracking_uri = "databricks://adb-field-eng"
    data_file_location = "/databricks-datasets/amazon/data20K"
    scoring_data_file_location = "/databricks-datasets/amazon/test4K"


'''
- Tests connectivity to hosted mlflow server using a databricks cli profile configured on your local system
    - check_mlflow_connectivity("databricks://adb-field-eng")
- Checks if datasets used are available
    - check_datasets_availability("/databricks-datasets/amazon/data20K","/databricks-datasets/amazon/test4K")
- Checks if mlflow lib (PyPi) is installed on the cluster
    - check_if_libs_installed()
'''

def check_if_libs_installed():
    print("\n *********** checking if mlflow is installed ***************")
    if(len(mlflow.version.VERSION) > 0):
        print("\nMLflow Version installed on databricks cluster:", mlflow.version.VERSION)
    else:
        logger.error("mlflow lib not found on databricks cluster, please install mlflow lib")
        assert False



def check_datasets_availability(data_file_location,scoring_data_file_location):
    print("\n *********** checking if datasets exists ***************")
    raw_data = spark.read.parquet(data_file_location).select("rating","review")
    if(raw_data.count() > 0):
        print(data_file_location + " exists and contains " + str(raw_data.count()) + " records")
    else:
        logger.error("couldn't locate " + data_file_location )
        assert False

    scoring_data = spark.read.parquet(scoring_data_file_location).select("review")
    if (scoring_data.count() > 0):
        print(scoring_data_file_location + " exists and contains " + str(scoring_data.count()) + " records")
    else:
        logger.error("couldn't locate " + scoring_data_file_location)
        assert False


def check_mlflow_connectivity(mlflow_tracking_uri):
    print("\n *********** checking mlflow connectivity ***************")
    mlflow_tracking_uri = mlflow_tracking_uri
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    client = mlflow.tracking.MlflowClient()
    print("There are in total " + str(len(client.list_experiments())) + " experiments on your mlflow tracking server")
    print("You are connected to databricks hosted tracking server using ******" + mlflow_tracking_uri)

***REMOVED*** check_if_libs_installed()
***REMOVED*** check_mlflow_connectivity("databricks://adb-field-eng")

def validate_env_setup(data_file_location, scoring_data_file_location,mlflow_tracking_uri):
    print("***************** running environment setup tests ********************")
    check_datasets_availability(data_file_location, scoring_data_file_location)
    check_if_libs_installed()
    check_mlflow_connectivity(mlflow_tracking_uri)

***REMOVED***validate setup

if __name__ == "__main__":
    validate_env_setup(data_file_location, scoring_data_file_location, mlflow_tracking_uri)
