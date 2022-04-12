***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md ***REMOVED******REMOVED***MLflow Deployment: Train PySpark Model and Log in MLeap Format
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This notebook walks through the process of:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 1. Training a PySpark pipeline model
***REMOVED*** MAGIC 2. Saving the model in MLeap format with MLflow
***REMOVED*** MAGIC 
***REMOVED*** MAGIC The notebook contains the following sections:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Setup
***REMOVED*** MAGIC * Launch a Python 3 cluster running Databricks Runtime 5.0 or above
***REMOVED*** MAGIC * Install MLflow
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Train a PySpark Pipeline model
***REMOVED*** MAGIC * Load pipeline training data
***REMOVED*** MAGIC * Define the PySpark Pipeline structure
***REMOVED*** MAGIC * Train the Pipeline model and log it within an MLflow run

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Setup

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC 1. Ensure you are using or create a cluster specifying 
***REMOVED*** MAGIC   * **Databricks Runtime Version:** Databricks Runtime 5.0 or above 
***REMOVED*** MAGIC   * **Python Version:** Python 3
***REMOVED*** MAGIC 1. Install required library or if using Databricks Runtime 5.1 or above (but not Databricks Runtime for ML), run Cmd 4.
***REMOVED*** MAGIC    * Create library with Source **PyPI** and enter `mlflow[extras]`.
***REMOVED*** MAGIC 1. Create library with Source **Maven Coordinate** and the fully-qualified Maven artifact coordinate:    
***REMOVED*** MAGIC    * `ml.combust.mleap:mleap-spark_2.11:0.13.0`
***REMOVED*** MAGIC 1. Install the libraries into the cluster.
***REMOVED*** MAGIC 1. Attach this notebook to the cluster.

***REMOVED*** COMMAND ----------

***REMOVED***dbutils.library.installPyPI("mlflow[extras]")
***REMOVED***dbutils.library.restartPython()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Train a PySpark Pipeline model

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Load pipeline training data
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Load data that will be used to train the PySpark Pipeline model. This model uses the [20 Newsgroups dataset](http://kdd.ics.uci.edu/databases/20newsgroups/20newsgroups.html) which consists of articles from 20 Usenet newsgroups.

***REMOVED*** COMMAND ----------

df = spark.read.parquet("/databricks-datasets/news20.binary/data-001/training").select("text", "topic")
df.cache()
display(df)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Define the PySpark Pipeline structure
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Define a PySpark Pipeline that featurizes samples from our dataset and classifies them using decision trees.

***REMOVED*** COMMAND ----------

from pyspark.ml import Pipeline
from pyspark.ml.classification import DecisionTreeClassifier
from pyspark.ml.feature import StringIndexer, Tokenizer, HashingTF
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

***REMOVED*** COMMAND ----------

***REMOVED*** Define pipeline components
labelIndexer = StringIndexer(inputCol="topic", outputCol="label", handleInvalid="keep")
tokenizer = Tokenizer(inputCol="text", outputCol="words")
hashingTF = HashingTF(inputCol="words", outputCol="features")
dt = DecisionTreeClassifier()

***REMOVED*** Construct a Pipeline object using the defined components
pipeline = Pipeline(stages=[labelIndexer, tokenizer, hashingTF, dt])

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Train the Pipeline model and log it within an MLflow run with MLeap flavor
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Train the PySpark Pipeline on the [20 Newsgroups](http://kdd.ics.uci.edu/databases/20newsgroups/20newsgroups.html) data that was loaded previously. The training process will execute within an MLflow run.

***REMOVED*** COMMAND ----------

import mlflow
import mlflow.mleap

def fit_model():
  ***REMOVED*** Start a new MLflow run
  with mlflow.start_run() as run:
    ***REMOVED*** Fit the model, performing cross validation to improve accuracy
    paramGrid = ParamGridBuilder().addGrid(hashingTF.numFeatures, [1000, 2000]).build()
    cv = CrossValidator(estimator=pipeline, evaluator=MulticlassClassificationEvaluator(), estimatorParamMaps=paramGrid)
    cvModel = cv.fit(df)
    model = cvModel.bestModel
  
    ***REMOVED*** Log the model within the MLflow run
    mlflow.mleap.log_model(spark_model=model, sample_input=df, artifact_path="model")

***REMOVED*** COMMAND ----------

***REMOVED*** Train the PySpark Pipeline model within a new MLflow run
fit_model()