import mlflow
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from nlp.reviews.data_science import *
from nlp.reviews.data_engg import *
import mlflow.spark as mlflow_spark

spark = get_spark()
spark.sparkContext.setLogLevel("warn")
logger = get_logger()

"""
   we are using databricks cli profile called "adb-field-eng", this way I can connect to an existing
   databricks subscription and use databricks hosted tracking service.
   To create a databricks cli profile please visit: [1]
   [1]: https://docs.azuredatabricks.net/user-guide/dev-tools/databricks-cli.html***REMOVED***connection-profiles
   For more options on mlflow tracking server please check out: [2] 
   [2]: https://mlflow.org/docs/latest/tracking.html***REMOVED***where-runs-are-recorded
"""


def set_mlflow_tracking_uri(mlflow_tracking_uri):
    mlflow.set_tracking_uri(mlflow_tracking_uri)


"""
Location where experiment runs are logged on databricks, this is the absolute path on databricks workspace
ex: /Users/<your name or email id>/some-folder/file

below I am using /Shared/experiments/ folder to log runs
"""


def set_mlflow_experiment(mlflow_experiment_file_path):
    ***REMOVED*** experiment file resides on dbfs
    logger = get_logger()
    logger.info("logging mlflow experiment on dbfs at: " + mlflow_experiment_file_path)
    mlflow.set_experiment(mlflow_experiment_file_path)


def model_selection_via_crossvalidation(num_features, reg_param, net_param, cv_num_folds):
    ***REMOVED*** hyper parameters for the cross validator
    num_features = num_features
    reg_param = reg_param
    net_param = net_param
    cv_num_folds = cv_num_folds

    ***REMOVED*** Start a new MLflow run
    with mlflow.start_run():
        tokenizer, remover, counts, lr = build_ml_pipeline()
        pipeline = Pipeline().setStages([tokenizer, remover, counts, lr])
        evaluator = BinaryClassificationEvaluator(rawPredictionCol="rawPrediction")

        paramGrid = ParamGridBuilder() \
            .addGrid(counts.numFeatures, num_features) \
            .addGrid(lr.regParam, reg_param) \
            .addGrid(lr.elasticNetParam, net_param) \
            .build()

        crossval = CrossValidator(estimator=pipeline,
                                  estimatorParamMaps=paramGrid,
                                  evaluator=evaluator,
                                  numFolds=cv_num_folds)

        ***REMOVED*** Run cross-validation, and choose the best set of parameters.
        training_df, validate_df, test_df = prepare_data()
        logger.warn("training classifier")
        cv_model = crossval.fit(training_df)

        ***REMOVED*** cv_best_pipeline_model == Pipeline model, this holds the best pipeline model based out of cross validation run
        cv_best_pipeline_model = cv_model.bestModel

        logger.info("evaluate trained classifier")
        prediction = cv_model.transform(validate_df)
        prediction.show(n=10)

        area_under_ROC = evaluator.evaluate(prediction)
        logger.info("Area under the curve metric for the best model selected out of CV: " + str(area_under_ROC))
        print("\n area_under_ROC: " + str(area_under_ROC))

        accuracy = cv_best_pipeline_model.stages[-1].summary.accuracy
        logger.info("Accuracy metric for the best model selected out of CV: " + str(accuracy))
        print("\n accuracy: " + str(accuracy))

        ***REMOVED*** save trained model to a local directory, in this case under your local system /uap/nlp/
        mlflow_spark.save_model(cv_best_pipeline_model, path="pyfunc-cv-model", conda_env=None)

        ***REMOVED*** save trained model to a dbfs
        mlflow_spark.log_model(cv_best_pipeline_model, artifact_path="/dbfs/tmp/dbconnect-demo/uap/reviews/pyfunc-cv-model", conda_env=None)

        ***REMOVED*** save model as spark flavor
        logger.info("logging cv_best_pipeline_model as a spark flavor on hosted mlflow server")
        spark_cv_model_path = "spark-cv-model"
        mlflow_spark.log_model(cv_best_pipeline_model, spark_cv_model_path)

        ***REMOVED*** save model as mleap flavor
        ***REMOVED*** mleap_cv_model_path = "mleap-cv-model"
        ***REMOVED*** mlflow.mleap.log_model(cv_best_pipeline_model, test_df, mleap_cv_model_path)

        mlflow.log_param("max_iterations", cv_best_pipeline_model.stages[-1]._java_obj.getMaxIter())
        mlflow.log_param("reg_param", cv_best_pipeline_model.stages[-1]._java_obj.getRegParam())

        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("area_under_ROC", area_under_ROC)

        cv_runid = mlflow.active_run().info.run_uuid
        cv_artifactUri = mlflow.get_artifact_uri()

        logger.warn("\ncv_runid: " + str(cv_runid))
        logger.warn("\ncv_artifactUri: " + str(cv_artifactUri))

        return cv_runid, cv_artifactUri

***REMOVED*** this is here for a quick test of hosted mlflow server connectivity
def test_mlflow():
    with mlflow.start_run():
        ***REMOVED*** Log a parameter (key-value pair)
        mlflow.log_param("param1", 5)

        ***REMOVED*** Log a metric; metrics can be updated throughout the run
        mlflow.log_metric("foo", 11)
        mlflow.log_metric("foo", 22)
        mlflow.log_metric("foo", 33)

        ***REMOVED*** Log an artifact (output file)
        with open("bk-output.txt", "w") as f:
            f.write("Hello world!")
        mlflow.log_artifact("bk-output.txt")