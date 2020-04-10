# Databricks notebook source
# MAGIC %md # Tracking ML Model Training with MLflow and Delta Lake
# MAGIC 
# MAGIC It's a common story - a data team trains a model, deploys it to production, and all is good for a time. Then the model begins to make strange predictions, and it quickly becomes necessary to inspect and debug the model.
# MAGIC 
# MAGIC This notebook demonstrates how to use [MLflow](http://mlflow.org) and [Delta Lake](http://delta.io) to easily track, visualize, and reproduce model training runs for ease of debugging. It demonstrates how to:
# MAGIC 
# MAGIC 1. Track and reproduce the exact snapshot of data used to build an ML pipeline.
# MAGIC 2. Identify models that were trained on a particular snapshot of data.
# MAGIC 3. Rerun training on a past snapshot of data (e.g. to reproduce an old model).
# MAGIC 
# MAGIC The notebook uses Delta Lake to provide data versioning and "time-travel" capabilities (restoring old versions of data), and MLflow to track data and query for runs that used a particular dataset.
# MAGIC 
# MAGIC **Prerequisites**:
# MAGIC * Databricks Runtime 6.1 ML or above
# MAGIC * Python 3

# COMMAND ----------

# MAGIC %md ## Setup

# COMMAND ----------

# MAGIC %md 
# MAGIC 1. Ensure you are using or create a cluster specifying 
# MAGIC   * **Databricks Runtime Version:** Databricks Runtime 5.0 or above 
# MAGIC   * **Python Version:** Python 3
# MAGIC 1. Install a library with Source **PyPI** and enter `mlflow`.
# MAGIC 1. Attach this notebook to the cluster.

# COMMAND ----------

# MAGIC %md
# MAGIC 
# MAGIC ## Problem Statement: Classifying "bad loans" for a lender
# MAGIC 
# MAGIC This notebook tackles a classification problem on the Lending Club dataset, with the goal of identifying "bad loans" (loans likely to be unprofitable) based on a combination of credit scores, credit history, and other features.
# MAGIC 
# MAGIC The end goal is to produce an interpretable model that a loan officer can use before deciding whether to approve a loan. Such a model provides an informative view for the lender as well as an immediate estimate and response for the prospective borrower.

# COMMAND ----------

# MAGIC %md
# MAGIC 
# MAGIC ### The Data
# MAGIC 
# MAGIC The data used is public data from Lending Club. It includes all funded loans from 2012 to 2017. Each loan includes applicant information provided by the applicant as well as the current loan status (Current, Late, Fully Paid, etc.) and latest payment information. For a full view of the data view the [data dictionary](https://resources.lendingclub.com/LCDataDictionary.xlsx).
# MAGIC 
# MAGIC ![Loan_Data](https://preview.ibb.co/d3tQ4R/Screen_Shot_2018_02_02_at_11_21_51_PM.png)
# MAGIC 
# MAGIC 
# MAGIC https://www.kaggle.com/wendykan/lending-club-loan-data

# COMMAND ----------

# MAGIC %md ## 1. Tracking Data Version and Location For Reproducibility
# MAGIC 
# MAGIC This notebook accepts data version and data path as input parameters via widgets, allowing for reproducing a run of the notebook against an explicitly-specified data version and path in the future. The ability to specify data version is an advantage of using Delta Lake, which preserves previous versions of datasets so that you can restore them later.

# COMMAND ----------

# Pull data path and version from notebook params
dbutils.widgets.text(name="deltaVersion", defaultValue="", label="Table version, default=latest")
dbutils.widgets.text(name="deltaPath", defaultValue="", label="Table path")

data_version = None if dbutils.widgets.get("deltaVersion") == "" else int(dbutils.widgets.get("deltaVersion"))
DELTA_TABLE_DEFAULT_PATH = "/ml/loan_stats.delta"
data_path = DELTA_TABLE_DEFAULT_PATH if dbutils.widgets.get("deltaPath")  == "" else dbutils.widgets.get("deltaPath")

# COMMAND ----------

# MAGIC %md ### Set up: create a Delta table in DBFS
# MAGIC 
# MAGIC Generate some example data in Delta Lake format by converting an existing Parquet table stored in DBFS.

# COMMAND ----------

from pyspark.sql.functions import *

# Remove table if it exists
dbutils.fs.rm(DELTA_TABLE_DEFAULT_PATH, recurse=True)
# Load & munge Lending Club data, then write to DBFS in Delta Lake format
lspq_path = "/databricks-datasets/samples/lending_club/parquet/"
data = spark.read.parquet(lspq_path)
# Select only the columns needed & apply other preprocessing
features = ["loan_amnt",  "annual_inc", "dti", "delinq_2yrs","total_acc", "total_pymnt", "issue_d", "earliest_cr_line"]
raw_label = "loan_status"
loan_stats_ce = data.select(*(features + [raw_label]))
print("------------------------------------------------------------------------------------------------")
print("Create bad loan label, this will include charged off, defaulted, and late repayments on loans...")
loan_stats_ce = loan_stats_ce.filter(loan_stats_ce.loan_status.isin(["Default", "Charged Off", "Fully Paid"]))\
                       .withColumn("bad_loan", (~(loan_stats_ce.loan_status == "Fully Paid")).cast("string"))
loan_stats_ce = loan_stats_ce.orderBy(rand()).limit(10000) # Limit rows loaded to facilitate running on Community Edition
print("------------------------------------------------------------------------------------------------")
print("Casting numeric columns into the appropriate types...")
loan_stats_ce = loan_stats_ce.withColumn('issue_year',  substring(loan_stats_ce.issue_d, 5, 4).cast('double')) \
                       .withColumn('earliest_year', substring(loan_stats_ce.earliest_cr_line, 5, 4).cast('double')) \
                       .withColumn('total_pymnt', loan_stats_ce.total_pymnt.cast('double'))
loan_stats_ce = loan_stats_ce.withColumn('credit_length_in_years', (loan_stats_ce.issue_year - loan_stats_ce.earliest_year))   
# Save table in Delta Lake format
loan_stats_ce.write.format("delta").mode("overwrite").save(DELTA_TABLE_DEFAULT_PATH)

# COMMAND ----------

# MAGIC %md ### Load Data From Delta Table
# MAGIC Load data back in Delta Lake format, using the data path and version specified in the widgets.

# COMMAND ----------

# Use the latest version of the table by default, unless a version parameter is explicitly provided
if data_version is None:
  from delta.tables import DeltaTable  
  delta_table = DeltaTable.forPath(spark, data_path)
  version_to_load = delta_table.history(1).select("version").collect()[0].version  
else:
  version_to_load = data_version

loan_stats = spark.read.format("delta").option("versionAsOf", version_to_load).load(data_path)  

# Review data
display(loan_stats)

# COMMAND ----------

# MAGIC %md ### Review Delta Table History
# MAGIC All the transactions for this table are stored within this table including the initial set of insertions, update, delete, merge, and inserts.

# COMMAND ----------

spark.sql("DROP TABLE IF EXISTS loan_stats")
spark.sql("CREATE TABLE loan_stats USING DELTA LOCATION '" + DELTA_TABLE_DEFAULT_PATH + "'")

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE HISTORY loan_stats

# COMMAND ----------

# MAGIC %md ### Train a Model with Cross Validation for Hyperparameter Tuning
# MAGIC Train an ML pipeline using Spark MLlib. The metrics and params from your tuning runs are automatically tracked to MLflow for later inspection.

# COMMAND ----------

from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, VectorAssembler, OneHotEncoder, StandardScaler, Imputer
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

import mlflow


def _fit_crossvalidator(train, features, target):
  """
  Helper function that fits a CrossValidator model to predict a binary label
  `target` on the passed-in training DataFrame using the columns in `features`
  :param: train: Spark DataFrame containing training data
  :param: features: List of strings containing column names to use as features from `train`
  :param: target: String name of binary target column of `train` to predict
  """
  train = train.select(features + [target])
  model_matrix_stages = [
    Imputer(inputCols = features, outputCols = features),
    VectorAssembler(inputCols=features, outputCol="features"),
    StringIndexer(inputCol="bad_loan", outputCol="label")
  ]
  lr = LogisticRegression(maxIter=10, elasticNetParam=0.5, featuresCol = "features")
  pipeline = Pipeline(stages=model_matrix_stages + [lr])
  paramGrid = ParamGridBuilder().addGrid(lr.regParam, [0.1, 0.01]).build()
  crossval = CrossValidator(estimator=pipeline,
                            estimatorParamMaps=paramGrid,
                            evaluator=BinaryClassificationEvaluator(),
                            numFolds=5)
  with mlflow.start_run():
    mlflow.log_param("data_version", version_to_load)
    mlflow.log_param("data_path", DELTA_TABLE_DEFAULT_PATH)
    cvModel = crossval.fit(train)
    return cvModel.bestModel

# COMMAND ----------

# Fit model & display ROC
features = ["loan_amnt",  "annual_inc", "dti", "delinq_2yrs","total_acc", "credit_length_in_years"]
glm_model = _fit_crossvalidator(loan_stats, features, target="bad_loan")
lr_summary = glm_model.stages[len(glm_model.stages)-1].summary
display(lr_summary.roc)

# COMMAND ----------

print("ML Pipeline accuracy: %s" % lr_summary.accuracy)

# COMMAND ----------

# MAGIC %md
# MAGIC ### View Training Results in the MLflow Runs Sidebar
# MAGIC 
# MAGIC The model training code above automatically logged metrics and params under an MLflow run, which you can view using the [MLflow Runs Sidebar](https://databricks.com/blog/2019/04/30/introducing-mlflow-run-sidebar-in-databricks-notebooks.html).
# MAGIC 
# MAGIC ![](https://pages.databricks.com/rs/094-YMS-629/images/db-mlflow-integration.gif)

# COMMAND ----------

# MAGIC %md ### Feature Engineering: Evolve Data Schema
# MAGIC 
# MAGIC You can do some feature engineering to potentially improve model performance, using Delta Lake to track older versions of the dataset. First, add a feature tracking the total amount of money earned or lost per loan:

# COMMAND ----------

print("------------------------------------------------------------------------------------------------")
print("Calculate the total amount of money earned or lost per loan...")
loan_stats_new = loan_stats.withColumn('net', round( loan_stats.total_pymnt - loan_stats.loan_amnt, 2))

# COMMAND ----------

# MAGIC %md Save the updated table, passing the `mergeSchema` option to safely evolve its schema.

# COMMAND ----------

loan_stats_new.write.option("mergeSchema", "true").format("delta").mode("overwrite").save(DELTA_TABLE_DEFAULT_PATH)

# COMMAND ----------

# See the difference between the original & modified schemas
set(loan_stats_new.schema.fields) - set(loan_stats.schema.fields)

# COMMAND ----------

# MAGIC %md Retrain the model on the updated data and compare its performance to the original.

# COMMAND ----------

# Return ROC
glm_model_new = _fit_crossvalidator(loan_stats_new, features + ["net"], target="bad_loan")
lr_summary_new = glm_model_new.stages[len(glm_model_new.stages)-1].summary
display(lr_summary_new.roc)

# COMMAND ----------

print("ML Pipeline accuracy: %s" % lr_summary_new.accuracy)

# COMMAND ----------

# MAGIC %md ## 2. Find runs that used the original data version
# MAGIC 
# MAGIC Model accuracy improved from ~80% to ~95% after the feature engineering step. You might therefore wonder: what if you retrained all models built off of the original dataset against the feature-engineered dataset? Would there be similar improvements in model performance?
# MAGIC 
# MAGIC To identify other runs launched against the original dataset, use MLflow's `mlflow.search_runs` API:

# COMMAND ----------

mlflow.search_runs(filter_string="params.data_path='{path}' and params.data_version='{version}'".format(path=data_path, version=0))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Load back and reproduce runs against a snapshot of data
# MAGIC Finally, you can load back a specific version of the data for use in model re-training. To do this, simply update the widgets above with a data version of 1 (corresponding to the feature-engineered data) and rerun section 1) of this notebook.