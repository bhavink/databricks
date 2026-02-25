# Databricks notebook source
# MAGIC %md ##MLflow Deployment: Train PySpark Model and Log in MLeap Format
# MAGIC 
# MAGIC This notebook walks through the process of:
# MAGIC 
# MAGIC 1. Training a PySpark pipeline model
# MAGIC 2. Saving the model in MLeap format with MLflow
# MAGIC 
# MAGIC The notebook contains the following sections:
# MAGIC 
# MAGIC #### Setup
# MAGIC * Launch a Python 3 cluster running Databricks Runtime 5.0 or above
# MAGIC * Install MLflow
# MAGIC 
# MAGIC #### Train a PySpark Pipeline model
# MAGIC * Load pipeline training data
# MAGIC * Define the PySpark Pipeline structure
# MAGIC * Train the Pipeline model and log it within an MLflow run

# COMMAND ----------

# MAGIC %md ## Setup

# COMMAND ----------

# MAGIC %md 
# MAGIC 1. Ensure you are using or create a cluster specifying 
# MAGIC   * **Databricks Runtime Version:** Databricks Runtime 5.0 or above 
# MAGIC   * **Python Version:** Python 3
# MAGIC 1. Install required library or if using Databricks Runtime 5.1 or above (but not Databricks Runtime for ML), run Cmd 4.
# MAGIC    * Create library with Source **PyPI** and enter `mlflow[extras]`.
# MAGIC 1. Create library with Source **Maven Coordinate** and the fully-qualified Maven artifact coordinate:    
# MAGIC    * `ml.combust.mleap:mleap-spark_2.11:0.13.0`
# MAGIC 1. Install the libraries into the cluster.
# MAGIC 1. Attach this notebook to the cluster.

# COMMAND ----------

#dbutils.library.installPyPI("mlflow[extras]")
#dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md ## Train a PySpark Pipeline model

# COMMAND ----------

# MAGIC %md ### Load pipeline training data
# MAGIC 
# MAGIC Load data that will be used to train the PySpark Pipeline model. This model uses the [20 Newsgroups dataset](http://kdd.ics.uci.edu/databases/20newsgroups/20newsgroups.html) which consists of articles from 20 Usenet newsgroups.

# COMMAND ----------

df = spark.read.parquet("/databricks-datasets/news20.binary/data-001/training").select("text", "topic")
df.cache()
display(df)

# COMMAND ----------

# MAGIC %md ### Define the PySpark Pipeline structure
# MAGIC 
# MAGIC Define a PySpark Pipeline that featurizes samples from our dataset and classifies them using decision trees.

# COMMAND ----------

from pyspark.ml import Pipeline
from pyspark.ml.classification import DecisionTreeClassifier
from pyspark.ml.feature import StringIndexer, Tokenizer, HashingTF
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

# COMMAND ----------

# Define pipeline components
labelIndexer = StringIndexer(inputCol="topic", outputCol="label", handleInvalid="keep")
tokenizer = Tokenizer(inputCol="text", outputCol="words")
hashingTF = HashingTF(inputCol="words", outputCol="features")
dt = DecisionTreeClassifier()

# Construct a Pipeline object using the defined components
pipeline = Pipeline(stages=[labelIndexer, tokenizer, hashingTF, dt])

# COMMAND ----------

# MAGIC %md ### Train the Pipeline model and log it within an MLflow run with MLeap flavor
# MAGIC 
# MAGIC Train the PySpark Pipeline on the [20 Newsgroups](http://kdd.ics.uci.edu/databases/20newsgroups/20newsgroups.html) data that was loaded previously. The training process will execute within an MLflow run.

# COMMAND ----------

import mlflow
import mlflow.mleap

def fit_model():
  # Start a new MLflow run
  with mlflow.start_run() as run:
    # Fit the model, performing cross validation to improve accuracy
    paramGrid = ParamGridBuilder().addGrid(hashingTF.numFeatures, [1000, 2000]).build()
    cv = CrossValidator(estimator=pipeline, evaluator=MulticlassClassificationEvaluator(), estimatorParamMaps=paramGrid)
    cvModel = cv.fit(df)
    model = cvModel.bestModel
  
    # Log the model within the MLflow run
    mlflow.mleap.log_model(spark_model=model, sample_input=df, artifact_path="model")

# COMMAND ----------

# Train the PySpark Pipeline model within a new MLflow run
fit_model()