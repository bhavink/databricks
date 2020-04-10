***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED*** MLlib + Automated MLflow Tracking
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This notebook demonstrates how to use automated MLflow tracking to track MLlib model tuning. 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC It demonstrates learning a [decision tree](https://en.wikipedia.org/wiki/Decision_tree_learning) using the Apache Spark distributed implementation.  Tracking the learning process in MLflow gives a better understanding of some critical [hyperparameters](https://en.wikipedia.org/wiki/Hyperparameter_optimization) for the tree learning algorithm, using examples to demonstrate how tuning the hyperparameters can improve accuracy.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Data**: The classic MNIST handwritten digit recognition dataset.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Goal**: Learn how to recognize digits (0 - 9) from images of handwriting.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Takeaways**: Decision trees take several hyperparameters that can affect the accuracy of the learned model.  There is no one "best" setting for these for all datasets.  To get the optimal accuracy, you need to tune these hyperparameters based on your data.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Setup
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 1. Create a cluster that runs one of:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC    - Databricks Runtime 5.5 ML  or above 
***REMOVED*** MAGIC    - Databricks Runtime 5.3 ML  or above 
***REMOVED*** MAGIC      - Install the `mlflow` PyPI package.
***REMOVED*** MAGIC    - Databricks Runtime 5.3 or above
***REMOVED*** MAGIC      - Install the `mlflow` PyPI package.
***REMOVED*** MAGIC      - To log the best model to MLflow, install the ``ml.combust.mleap:mleap-spark_2.11`` Maven package and the ``mleap`` PyPI package.
***REMOVED*** MAGIC 1. Attach the notebook to the cluster.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Load MNIST training and test datasets
***REMOVED*** MAGIC 
***REMOVED*** MAGIC The datasets are vectors of pixels representing images of handwritten digits.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC These datasets are stored in the popular LibSVM dataset format.  Load them using MLlib's LibSVM dataset reader utility.

***REMOVED*** COMMAND ----------

training = spark.read.format("libsvm").load("/databricks-datasets/mnist-digits/data-001/mnist-digits-train.txt")
test = spark.read.format("libsvm").load("/databricks-datasets/mnist-digits/data-001/mnist-digits-test.txt")

training.cache()
test.cache()

print("There are {} training images and {} test images.".format(training.count(), test.count()))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Display the data.  Each image has the true label (the `label` column) and a vector of `features` that represent pixel intensities.

***REMOVED*** COMMAND ----------

display(training)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Define an ML Pipeline with a Decision Tree Estimator
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Before training, Use the `StringIndexer` class to convert the labels to the categories 0-9, rather than continuous values. Tie this feature preprocessing together with the tree algorithm using a `Pipeline`.  Pipelines are objects Apache Spark provides for piecing together machine learning algorithms into workflows.  To learn more about Pipelines, check out other ML example notebooks in Databricks and the [ML Pipelines user guide](http://spark.apache.org/docs/latest/ml-guide.html).

***REMOVED*** COMMAND ----------

***REMOVED*** Import the ML classification, indexer, and pipeline classes 
from pyspark.ml.classification import DecisionTreeClassifier, DecisionTreeClassificationModel
from pyspark.ml.feature import StringIndexer
from pyspark.ml import Pipeline

***REMOVED*** COMMAND ----------

***REMOVED*** StringIndexer: Read input column "label" (digits) and annotate them as categorical values.
indexer = StringIndexer(inputCol="label", outputCol="indexedLabel")
***REMOVED*** DecisionTreeClassifier: Learn to predict column "indexedLabel" using the "features" column.
dtc = DecisionTreeClassifier(labelCol="indexedLabel")
***REMOVED*** Chain indexer + dtc together into a single ML Pipeline.
pipeline = Pipeline(stages=[indexer, dtc])

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Automated MLflow Tracking for CrossValidator model tuning
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This section tunes some of the Pipeline's hyperparameters.  While tuning, MLflow automatically tracks the models produced by `CrossValidator`, along with their evaluation metrics.  This allows you to examine the behavior of the following tuning hyperparameters using MLflow:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC * `maxDepth`, which determines how deep (and large) the tree can be.  Train trees at varying depths and see how it affects the accuracy on your held-out test set.
***REMOVED*** MAGIC * `maxBins`, which controls how to discretize (bin) continuous features.  This case bins pixel values; e.g., choosing `maxBins=2` effectively turns your images into black-and-white images.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md **Enable automated MLflow tracking for MLlib**
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Automated MLflow tracking is enabled by default for:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC   - Databricks Runtime 5.4 ML or above
***REMOVED*** MAGIC   - Databricks Runtime 5.4 or above
***REMOVED*** MAGIC   
***REMOVED*** MAGIC To enable it for earlier versions, set the `SparkSession` configuration flag `"spark.databricks.mlflow.trackMLlib.enabled"` to `"true"`.

***REMOVED*** COMMAND ----------

spark.conf.set("spark.databricks.mlflow.trackMLlib.enabled", "true")

***REMOVED*** COMMAND ----------

***REMOVED*** Define an evaluation metric.  In this case, use "weightedPrecision", which is equivalent to 0-1 accuracy.
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
evaluator = MulticlassClassificationEvaluator(labelCol="indexedLabel", metricName="weightedPrecision")

***REMOVED*** COMMAND ----------

from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

***REMOVED*** COMMAND ----------

grid = ParamGridBuilder() \
  .addGrid(dtc.maxDepth, [2, 3, 4, 5, 6, 7, 8]) \
  .addGrid(dtc.maxBins, [2, 4, 8]) \
  .build()

***REMOVED*** COMMAND ----------

cv = CrossValidator(estimator=pipeline, evaluator=evaluator, estimatorParamMaps=grid, numFolds=3)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Run `CrossValidator`.  `CrossValidator` checks to see if an MLflow tracking server is available.  If so, it log runs within MLflow:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC * Under the current active run, log info for `CrossValidator`.  (Create a new run if none are active.)
***REMOVED*** MAGIC * For each submodel (number of folds of cross-validation x number of ParamMaps tested)
***REMOVED*** MAGIC   * Log a run for this submodel, along with the evaluation metric on the held-out data.

***REMOVED*** COMMAND ----------

***REMOVED*** Explicitly create a new run.
***REMOVED*** This allows this cell to be run multiple times.
***REMOVED*** If you omit mlflow.start_run(), then this cell could run once,
***REMOVED*** but a second run would hit conflicts when attempting to overwrite the first run.
import mlflow
import mlflow.mleap
with mlflow.start_run():
  cvModel = cv.fit(training)
  mlflow.set_tag('owner_team', 'UX Data Science') ***REMOVED*** Logs user-defined tags
  test_metric = evaluator.evaluate(cvModel.transform(test))
  mlflow.log_metric('test_' + evaluator.getMetricName(), test_metric) ***REMOVED*** Logs additional metrics
  mlflow.mleap.log_model(spark_model=cvModel.bestModel, sample_input=test, artifact_path='best-model') ***REMOVED*** Logs the best model via mleap


***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md To view the MLflow experiment associated with the notebook, click the **Runs** icon in the notebook context bar on the upper right.  There, you can view all runs. To more easily compare their results, click the button on the upper right that reads "View Experiment UI" when you hover over it.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC To understand the effect of tuning `maxDepth`:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 1. Filter by `params.maxBins = "8"`.
***REMOVED*** MAGIC 1. Select the resulting runs and click **Compare**.
***REMOVED*** MAGIC 1. In the Scatter Plot, select X-axis **maxDepth** and Y-axis **avg_weightedPrecision**.