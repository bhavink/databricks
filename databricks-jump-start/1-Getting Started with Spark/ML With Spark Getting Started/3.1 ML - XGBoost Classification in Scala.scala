// Databricks notebook source
// MAGIC %md ***REMOVED*** XGBoost Classification with Spark DataFrames

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED*** Prepare Data

// COMMAND ----------

import org.apache.spark.sql.types.{DoubleType, StringType, StructField, StructType}

val schema = new StructType(Array(
      StructField("item", StringType, true),
      StructField("sepal length", DoubleType, true),
      StructField("sepal width", DoubleType, true),
      StructField("petal length", DoubleType, true),
      StructField("petal width", DoubleType, true),
      StructField("class", StringType, true)))

val rawInput = spark.read.schema(schema).format("csv").option("header", "true").load("dbfs:/databricks-datasets/Rdatasets/data-001/csv/datasets/iris.csv")

// COMMAND ----------

rawInput.createOrReplaceTempView("iristable")

// COMMAND ----------

import org.apache.spark.sql.types._

val rawInput = spark.sql("select * from iristable")

val newInput = rawInput.drop("item")

val Array(trainingRaw, testRaw) = newInput.randomSplit(Array(0.8, 0.2), 123)

display(newInput)

// COMMAND ----------

import ml.dmlc.xgboost4j.scala.spark.{XGBoostClassificationModel,XGBoostClassifier}
import org.apache.spark.ml.feature.{StringIndexer, VectorAssembler}

val newInput = rawInput.drop("item")

// transform class to classIndex to make xgboost happy
val stringIndexer = new StringIndexer().setInputCol("class").setOutputCol("classIndex").fit(newInput)

val labelTransformed = stringIndexer.transform(newInput).drop("class")

// compose all feature columns as vector
val vectorAssembler = new VectorAssembler()
  .setInputCols(Array("sepal length", "sepal width", "petal length", "petal width"))
  .setOutputCol("features")

val xgbInput = vectorAssembler.transform(labelTransformed).select("features","classIndex")

display(xgbInput)

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Train XGBoost Model with Spark DataFrames

// COMMAND ----------

val xgbParam = Map("eta" -> 0.1f,
      "max_depth" -> 2,
      "objective" -> "multi:softprob",
      "num_class" -> 3,
      "num_round" -> 100,
      "num_workers" -> 2)

val xgbClassifier = new XGBoostClassifier(xgbParam).setFeaturesCol("features").setLabelCol("classIndex")

// COMMAND ----------

val xgbClassificationModel = xgbClassifier.fit(xgbInput)

// COMMAND ----------

val results = xgbClassificationModel.transform(xgbInput)

// COMMAND ----------

display(results)

// COMMAND ----------

import org.apache.spark.ml.feature._

val labelConverter = new IndexToString()
    .setInputCol("prediction")
    .setOutputCol("realLabel")
    .setLabels(stringIndexer.labels)

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** Embed XGBoost in ML Pipeline

// COMMAND ----------

import org.apache.spark.ml.Pipeline

val pipeline = new Pipeline().setStages(Array(vectorAssembler, stringIndexer, xgbClassifier, labelConverter))
val model = pipeline.fit(trainingRaw)


// COMMAND ----------

import org.apache.spark.ml.evaluation.MulticlassClassificationEvaluator

val evaluator = new MulticlassClassificationEvaluator()

evaluator.setLabelCol("classIndex")
evaluator.setPredictionCol("prediction")

val prediction = model.transform(testRaw)
val accuracy = evaluator.evaluate(prediction)

// COMMAND ----------

println("The model accuracy is : " + accuracy)

// COMMAND ----------

display(prediction.select("classIndex","prediction"))