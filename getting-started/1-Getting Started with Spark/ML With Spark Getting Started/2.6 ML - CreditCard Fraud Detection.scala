// Databricks notebook source
// MAGIC %md
// MAGIC This example shows how to train an MLlib pipeline to produce a PipelineModel that can be applied to transform a streaming DataFrame. We will also identify a few points to keep in mind when creating a pipeline that’s meant to be used for transforming streaming data.
// MAGIC 
// MAGIC To begin, let's consider the case of a credit card company that would like to identify potentially fraudulent transactions as soon as possible so they can follow up with their customers to confirm whether in fact a transaction was fraudulent. This hypothetical credit card company has historical data on transactions and which of those transactions were reported as fraud by their customers. We’d like to train a classifier on this historical data. Once we've trained our classifier we'll apply it to a stream of transactions.
// MAGIC 
// MAGIC This example requires Databricks Runtime 4.0 or above.

// COMMAND ----------

// MAGIC %md
// MAGIC For this example we'll be using a dataset collected and analysed during a research collaboration of Worldline and the Machine Learning Group (http://mlg.ulb.ac.be) of ULB (Université Libre de Bruxelles) on big data mining and fraud detection [1]. More details on current and past projects on related topics are available at http://mlg.ulb.ac.be/BruFence and http://mlg.ulb.ac.be/ARTML.
// MAGIC 
// MAGIC Begin by reading the data and inspecting the schema.

// COMMAND ----------

val data = spark.read.parquet("/databricks-datasets/credit-card-fraud/data")
data.printSchema()

// COMMAND ----------

// MAGIC %md
// MAGIC We'll be using 3 columns of this dataset:
// MAGIC 
// MAGIC 
// MAGIC - `pcaVector`: The PCA transformation of raw transaction data. For this example we'll assume that this PCA transformation occurs as part of some data pipeline before the data reaches us.
// MAGIC - `amountRange`: A value between 0 and 7. The approximate amount of a transaction. The values correspond to 0-1, 1-5, 5-10, 10-20, 20-50, 50-100, 100-200, and 200+ in dollars.
// MAGIC - `label`: 0 or 1. Indicates whether a transaction was fraudulent.
// MAGIC 
// MAGIC We want to build a model that will predict the label using the `pcaVector` and `amountRange` data. We'll do this by using a pipeline with 3 stages.
// MAGIC 
// MAGIC 
// MAGIC 1. A `OneHotEncoderEstimator` to build a vector from the `amountRange` column. 
// MAGIC 2. A `Vector` assembler to merge our `pcaVector` and `amountRange` vector into our `features` vector. 
// MAGIC 3. A `GBTClassifier` to server as our `Estimator`.
// MAGIC 
// MAGIC Let's start by creating the objects that represent these stages.

// COMMAND ----------

import org.apache.spark.ml.feature.{OneHotEncoderEstimator, VectorAssembler}
import org.apache.spark.ml.classification.GBTClassifier

val oneHot = new OneHotEncoderEstimator()
  .setInputCols(Array("amountRange"))
  .setOutputCols(Array("amountVect"))

val vectorAssembler = new VectorAssembler()
  .setInputCols(Array("amountVect", "pcaVector"))
  .setOutputCol("features")

val estimator = new GBTClassifier()
  .setLabelCol("label")
  .setFeaturesCol("features")


// COMMAND ----------

// MAGIC %md
// MAGIC 
// MAGIC So far this should be familiar to anyone who has used MLlib's pipelines, but because we intend to use this model in a streaming context there a few things we should be aware of.
// MAGIC 
// MAGIC First you may notice that we used a `OneHotEncoderEstimator`, which is new in Spark 2.3.0, and not a `OneHotEncoder`, which has now been deprecated. This new estimator fixes several issues related of the `OneHotEncoder` and will also allow you to apply one hot encoding to streaming DataFrames.
// MAGIC 
// MAGIC The second thing to be aware of when using MLlib with Structured Streaming is that `VectorAssembler` has some limitations in a streaming context. Specifically, `VectorAssembler` can only work on Vector columns of known size. This is not an issue on batch DataFrames because we can simply inspect the contents of the dataframe to determine the size of the Vectors. 
// MAGIC 
// MAGIC If we intend to use our pipeline to transform streaming DataFrames, we can explicitly specify the size of the pcaVector column by including a `VectorSizeHint` stage in our pipeline. The other input to our `VectorAssembler` stage, `amountVect`, is also a vector column, but because this column is the output of an MLlib transformer, it already contains the appropriate size information so we don't need to do anything additional for this column.

// COMMAND ----------

import org.apache.spark.ml.feature.VectorSizeHint

val vectorSizeHint = new VectorSizeHint()
  .setInputCol("pcaVector")
  .setSize(28)

// COMMAND ----------

// MAGIC %md
// MAGIC Before we fit our model, let's split our dataset into two parts for training and validation.

// COMMAND ----------

val Array(train, test) = data.randomSplit(weights=Array(.8, .2))

// COMMAND ----------

// MAGIC %md
// MAGIC Now we're ready to build a pipeline and fit it.

// COMMAND ----------

import org.apache.spark.ml.Pipeline
import org.apache.spark.sql.functions.col

val pipeline = new Pipeline()
  .setStages(Array(oneHot, vectorSizeHint, vectorAssembler, estimator))

val pipelineModel = pipeline.fit(train)

// COMMAND ----------

// MAGIC %md
// MAGIC Since we don't have an actual stream to read from, we can simulate a stream by saving the test data and then using Spark to read it as a stream. We'll use this simulated stream to do some validation of our model. To validate the model we'll write the confusion matrix to a table, but because we're using Spark Structured Streaming this table will update in real time as more data is read from the stream.

// COMMAND ----------

val testDataPath = "/tmp/credit-card-frauld-test-data"

test.repartition(20).write
  .mode("overwrite")
  .parquet(testDataPath)

// COMMAND ----------

import org.apache.spark.sql.types._
import org.apache.spark.ml.linalg.SQLDataTypes.VectorType

val schema = new StructType()
  .add(StructField("time", IntegerType))
  .add(StructField("amountRange", IntegerType))
  .add(StructField("label", IntegerType))
  .add(StructField("pcaVector", VectorType))

val streamingData = sqlContext.readStream
  .schema(schema)
  .option("maxFilesPerTrigger", 1)
  .parquet(testDataPath)


// COMMAND ----------

// MAGIC %md
// MAGIC To validate our model, let's calculate the true positive and true negative rates, often called the sensitivity and specificity respectively, for our validation data. Because we’re reading the validation dataset as a stream these values will update as we read more transactions from the stream.

// COMMAND ----------

import org.apache.spark.sql.functions.{count, sum, when}

val streamingRates = pipelineModel.transform(streamingData)
  .groupBy('label)
  .agg(
    (sum(when('prediction === 'label, 1)) / count('label)).alias("true prediction rate"),
    count('label).alias("count")
  )

display(streamingRates)

// COMMAND ----------

// MAGIC %md
// MAGIC In this example we are using Spark Structured Streaming to incrementally update our validation metric. An actual credit card processor might want to use Spark Structured Streaming to do something more useful. For example, they might aggregate the number of possibly fraudulent transactions for each account over some window period, say 30 days, and alert their fraud prevention department if that number is greater than some threshold. To implement this kind of streaming job you would use a process similar to what’s outlined in this notebook.

// COMMAND ----------

// MAGIC %md
// MAGIC [1] Andrea Dal Pozzolo, Olivier Caelen, Reid A. Johnson and Gianluca Bontempi. Calibrating Probability with Undersampling for Unbalanced Classification. In Symposium on Computational Intelligence and Data Mining (CIDM), IEEE, 2015 https://www3.nd.edu/~dial/publications/dalpozzolo2015calibrating.pdf.