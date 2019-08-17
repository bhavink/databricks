import sys
from nlp.reviews import data_engg, test_env_setup, data_science, mlflow_experiments
from nlp.reviews.mlflow_model_load_and_score import *

'''
This is the main file or the entry point to this project.
There are several section relating to data_engg, data_science and ml life cycle management
Before running this code please make sure that required variables are set properly and it passes sanity tests
We will be using:
 - public datasets available on databricks workspace
 - hosted mlflow server
 - mlflow lib - installed via pypi, version used 0.9.1 and greater
 
'''


if __name__ == "__main__":
    '''
        data is located on databricks file system
        params passed at runtime to the py script    
        
        mlflow_tracking_uri = sys.argv[1]
        data_file_location = sys.argv[2]
        scoring_data_file_location = sys.argv[3]
        
        mlflow_experiment_file_path = sys.argv[4]
        mlflow_search_query = sys.argv[5]
        
        numFeatures = map(int, sys.argv[3].strip('[]').split(','))
        regParam = map(float, sys.argv[4].strip('[]').split(','))
        netParam = map(float, sys.argv[5].strip('[]').split(','))
        cvNumFolds = int(sys.argv[6])
        
    '''
    data_file_location = "/databricks-datasets/amazon/data20K"
    scoring_data_file_location = "/databricks-datasets/amazon/test4K"

    numFeatures = [1000]
    regParam = [0.01]
    netParam = [0.1]
    cvNumFolds = 3

    '''
        set mlflow server tracking uri, this is where the metrics, params and models are logged
        we are using databricks cli profile called "adb-field-eng", this way I can connect to an existing
        databricks subscription and use databricks hosted tracking service.
        To create a databricks cli profile please visit: [1]
        [1]: https://docs.azuredatabricks.net/user-guide/dev-tools/databricks-cli.html#connection-profiles
        For more options on mlflow tracking server please check out: [2] 
        [2]: https://mlflow.org/docs/latest/tracking.html#where-runs-are-recorded
    '''
    mlflow_experiment_file_path = "/Shared/experiments/bk-uap-reviews-dbconnect-exp"
    mlflow_tracking_uri = "databricks://adb-field-eng"

    # mlflow_tracking_uri = "databricks"
    mlflow_search_query = "metrics.accuracy >= 0.80"

    '''
    uncomment below block to run:
        - ingest
        - analyze
        - train and score lr model (does not use crossvalidation as well as mlflow)        
    '''
    # print("\n********************* Running data_engg and data_science.py *********************")
    data_engg.ingest_data(data_file_location)
    data_engg.analyze_data()
    # data_science.nostradamus()

    '''
        uncomment below block to run ml pipeline which will
            - ingest
            - prepare feature vector
            - runs a spark pipeline using cross validation to scan thru hyperparameter space
            - run ml experiments and track using mlflow tracking service
            - log best model from based on cross validation to mlflow model logging service
            
        Location where experiment runs are logged on databricks, this is the absolute path on databricks workspace
        ex: /Users/<your name or email id>/some-folder/file
        below I am using /Shared/experiments/bk-uap-reviews-dbconnect-exp folder to log runs
    '''
    # print("\n********************* Running mlflow_experiments.py ******************************")
    # data_engg.ingest_data(data_file_location)
    # mlflow_experiments.set_mlflow_tracking_uri(mlflow_tracking_uri)
    # mlflow_experiments.set_mlflow_experiment(mlflow_experiment_file_path)
    # cv_runid, cv_artifactUri = mlflow_experiments.model_selection_via_crossvalidation(numFeatures, regParam, netParam, cvNumFolds)
    # print("\ncv best model saved at: " + cv_artifactUri)


    '''
       uncomment below block to run ml pipeline which will load an exising mlflow logged model into memory and score    
    '''
    print("\n********************* Running mlflow_model_load_score.py ******************************")
    # load_and_score_using_spark(mlflow_experiment_file_path, mlflow_tracking_uri, mlflow_search_query,
    #                            scoring_data_file_location)
    # load_and_score_using_pyfunc(mlflow_experiment_file_path, mlflow_tracking_uri, mlflow_search_query,
    #                             scoring_data_file_location)