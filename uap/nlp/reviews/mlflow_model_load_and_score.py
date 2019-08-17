from __future__ import print_function
from nlp.reviews import utils
from mlflow import spark as mlflow_spark, mlflow

run_uuid_list = []

# mlflow.set_tracking_uri(mlflow_tracking_uri)
# mlflow.set_experiment(mlflow_experiment_file_path)
# client = mlflow.tracking.MlflowClient()
# experiment_id = client.get_experiment_by_name(mlflow_experiment_file_path).experiment_id


def search(client,exp_ids, query):
    logger = utils.get_logger()
    print("Query:",query)
    runs = client.search_runs(exp_ids,query)
    print("Found {} matching runs in mlflow:".format(len(runs)))
    if(len(runs) > 0):
        for run in runs:
            print("  run_uuid:",run.info.run_uuid," metrics:",run.data.metrics)
            run_uuid_list.append(run.info.run_uuid)

        return run_uuid_list
    else:
        logger.error("There are no runs for this experiment in mlflow, please rerun your experiment and log atleast 1 run in mlflow")
        exit(1)


def load_and_score_using_spark(mlflow_experiment_file_path, mlflow_tracking_uri, mlflow_search_query,in_test_data_for_scoring):
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(mlflow_experiment_file_path)
    client = mlflow.tracking.MlflowClient()
    experiment_id = client.get_experiment_by_name(mlflow_experiment_file_path).experiment_id
    runs_list = search(client, [experiment_id], mlflow_search_query)

    test_data_for_scoring = in_test_data_for_scoring
    spark=utils.get_spark()
    test_df = spark.read.parquet(test_data_for_scoring).select("review")
    spark_pipeline_model = mlflow.spark.load_model("spark-cv-model",runs_list.pop(0))
    spark_prediction = spark_pipeline_model.transform(test_df)
    print("\nspark prediction")
    spark_prediction.show(n=10)

def load_and_score_using_pyfunc(mlflow_experiment_file_path, mlflow_tracking_uri, mlflow_search_query,in_test_data_for_scoring):
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(mlflow_experiment_file_path)
    client = mlflow.tracking.MlflowClient()
    experiment_id = client.get_experiment_by_name(mlflow_experiment_file_path).experiment_id
    runs_list = search(client,[experiment_id], mlflow_search_query)

    test_data_for_scoring = in_test_data_for_scoring
    spark=utils.get_spark()
    test_df = spark.read.parquet(test_data_for_scoring).select("review")
    pandas_test_df = test_df.toPandas()

    pipeline_model_as_pyfunc = mlflow.pyfunc.load_pyfunc("spark-cv-model",runs_list.pop(0))
    pyfunc_prediction = pipeline_model_as_pyfunc.predict(pandas_test_df)
    print("\npyfunc prediction")
    print(pyfunc_prediction)


def list_artifacts():
    print("\n mlflow artifacts logged at: " + mlflow.get_artifact_uri())


# here for test purpose

# mlflow_experiment_file_path = "/Shared/experiments/bk-uap-reviews-dbconnect-exp"
# mlflow_tracking_uri = "databricks://adb-field-eng"
# mlflow_search_query = "metrics.accuracy >= 0.80"
# scoring_data_file_location = "/databricks-datasets/amazon/test4K"

# load_and_score_using_pyfunc(mlflow_experiment_file_path, mlflow_tracking_uri, mlflow_search_query,scoring_data_file_location)

