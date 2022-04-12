***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** MLflow Quick Start: Inference
***REMOVED*** MAGIC In this tutorial, we’ll:
***REMOVED*** MAGIC * Install the MLflow library on a Databricks cluster
***REMOVED*** MAGIC * View the training results in the MLflow experiment UI
***REMOVED*** MAGIC * Load the trained model as a scikit-learn model
***REMOVED*** MAGIC * Export the model as a PySpark UDF
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This notebook uses a model trained on the `diabetes` dataset using the scikit-learn ElasticNet linear regression model. For more information on ElasticNet, refer to:
***REMOVED*** MAGIC   * [Elastic net regularization](https://en.wikipedia.org/wiki/Elastic_net_regularization)
***REMOVED*** MAGIC   * [Regularization and Variable Selection via the Elastic Net](https://web.stanford.edu/~hastie/TALKS/enet_talk.pdf)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Prerequisites
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ElasticNet models from part 1: MLflow Quick Start: Training and Logging.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Setup

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC 1. Ensure you are using or create a cluster specifying 
***REMOVED*** MAGIC   * **Databricks Runtime Version:** Databricks Runtime 5.0 or above 
***REMOVED*** MAGIC   * **Python Version:** Python 3
***REMOVED*** MAGIC 1. Install required libraries or if using Databricks Runtime 5.1 or above (but not Databricks Runtime for ML), run Cmd 6.
***REMOVED*** MAGIC    1. Create required libraries.
***REMOVED*** MAGIC     * Source **PyPI** and enter `mlflow[extras]`.
***REMOVED*** MAGIC    1. Install the libraries into the cluster.
***REMOVED*** MAGIC 1. Attach this notebook to the cluster.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Choose a run ID associated with an ElasticNet training run from of the Quick Start training and logging. You can find a run ID and model path from the experiment run, which can be found on the run details page:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ![image](https://docs.databricks.com/_static/images/mlflow/mlflow-deployment-example-run-info.png)

***REMOVED*** COMMAND ----------

run_id1 = "<run-id1>"
model_uri = "runs:/" + run_id1 + "/model"

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Load MLflow Model as a scikit-learn Model
***REMOVED*** MAGIC You can use the MLflow API to load the model from the MLflow server that was produced by a given run.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Once you load it, it is a just a scikit-learn model and you can explore it or use it.

***REMOVED*** COMMAND ----------

import mlflow.sklearn
model = mlflow.sklearn.load_model(model_uri=model_uri)
model.coef_

***REMOVED*** COMMAND ----------

***REMOVED*** Import various libraries including sklearn, mlflow, numpy, pandas

from sklearn import datasets
import numpy as np
import pandas as pd

***REMOVED*** Load Diabetes datasets
diabetes = datasets.load_diabetes()
X = diabetes.data
y = diabetes.target

***REMOVED*** Create pandas DataFrame for sklearn ElasticNet linear_model
Y = np.array([y]).transpose()
d = np.concatenate((X, Y), axis=1)
cols = ['age', 'sex', 'bmi', 'bp', 's1', 's2', 's3', 's4', 's5', 's6', 'progression']
data = pd.DataFrame(d, columns=cols)

***REMOVED*** COMMAND ----------

***REMOVED***Get a prediction for a row of the dataset
model.predict(data[0:1].drop(["progression"], axis=1))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Use an MLflow Model for Batch Inference
***REMOVED*** MAGIC You can get a PySpark UDF to do some batch inference using one of the models.

***REMOVED*** COMMAND ----------

***REMOVED*** Create a Spark DataFrame from the original pandas DataFrame minus the column you want to predict.
***REMOVED*** Use this to simulate what this would be like if you had a big data set e.g. click logs that was 
***REMOVED*** regularly being updated that you wanted to score.
dataframe = spark.createDataFrame(data.drop(["progression"], axis=1))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Use the MLflow API to create a PySpark UDF from a run. See [Export a python_function model as an Apache Spark UDF](https://mlflow.org/docs/latest/models.html***REMOVED***export-a-python-function-model-as-an-apache-spark-udf).

***REMOVED*** COMMAND ----------

import mlflow.pyfunc
pyfunc_udf = mlflow.pyfunc.spark_udf(spark, model_uri=model_uri)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Add a column to the data by applying the PySpark UDF to the DataFrame.

***REMOVED*** COMMAND ----------

predicted_df = dataframe.withColumn("prediction", pyfunc_udf('age', 'sex', 'bmi', 'bp', 's1', 's2', 's3', 's4', 's5', 's6'))
display(predicted_df)