// Databricks notebook source
// MAGIC %md ***REMOVED*** XGBoost Regression with Spark DataFrames

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED*** Prepare Data

// COMMAND ----------

sql("drop table if exists power_plant")
case class PowerPlantTable(AT: Double, V : Double, AP : Double, RH : Double, PE : Double)
val powerPlantData = sc.textFile("dbfs:/databricks-datasets/power-plant/data/")
  .map(x => x.split("\t"))
  .filter(line => line(0) != "AT")
  .map(line => PowerPlantTable(line(0).toDouble, line(1).toDouble, line(2).toDouble, line(3).toDouble, line(4).toDouble))
  .toDF
  .write
  .saveAsTable("power_plant")

val dataset = spark.table("power_plant")

// COMMAND ----------

import org.apache.spark.sql.types.{DoubleType, StringType, StructField, StructType}

val schema = new StructType(Array(
      StructField("AT", DoubleType, true),
      StructField("V", DoubleType, true),
      StructField("AP", DoubleType, true),
      StructField("RH", DoubleType, true),
      StructField("PE", DoubleType, true)))

val rawInput = spark.read.schema(schema).format("csv").option("header", "true").option("sep", "\t").load("dbfs:/databricks-datasets/power-plant/data/")
display(rawInput)

// COMMAND ----------

import org.apache.spark.ml.feature.VectorAssembler

val assembler =  new VectorAssembler()
                  .setInputCols(Array("AT", "V", "AP", "RH"))
                  .setOutputCol("features")

val xgbInput = assembler.transform(rawInput).withColumnRenamed("PE", "label")

// COMMAND ----------

display(xgbInput)

// COMMAND ----------

val Array(split20, split80) = xgbInput.randomSplit(Array(0.20, 0.80), 1800009193L)
val testSet = split20.cache()
val trainingSet = split80.cache()

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Train XGBoost Model with Spark DataFrames

// COMMAND ----------

import ml.dmlc.xgboost4j.scala.spark.{XGBoostRegressionModel,XGBoostRegressor}

val xgbParam = Map("eta" -> 0.3,
      "max_depth" -> 6,
      "objective" -> "reg:squarederror",
      "num_round" -> 10,
      "num_workers" -> 2)

val xgbRegressor = new XGBoostRegressor(xgbParam).setFeaturesCol("features").setLabelCol("label")

// COMMAND ----------

val xgbRegressionModel = xgbRegressor.fit(trainingSet)

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Evaluate Model
// MAGIC 
// MAGIC You can evaluate the XGBoost model using Evaluators from MLlib.

// COMMAND ----------

val predictions = xgbRegressionModel.transform(testSet)

// COMMAND ----------

display(predictions.select("label","prediction"))

// COMMAND ----------

import org.apache.spark.ml.evaluation.RegressionEvaluator

val evaluator = new RegressionEvaluator()
  .setLabelCol("label")
  .setPredictionCol("prediction")
  .setMetricName("rmse")

val rmse = evaluator.evaluate(predictions)

// COMMAND ----------

print("Root mean squared error: " + rmse)

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED*** Tune Model using MLlib Cross Validation

// COMMAND ----------

import org.apache.spark.ml.tuning.{CrossValidator, ParamGridBuilder}

val paramGrid = new ParamGridBuilder()
      .addGrid(xgbRegressor.maxDepth, Array(4, 7))
      .addGrid(xgbRegressor.eta, Array(0.1, 0.6))
      .build()

val cv = new CrossValidator()
      .setEstimator(xgbRegressor)
      .setEvaluator(evaluator)
      .setEstimatorParamMaps(paramGrid)
      .setNumFolds(4)

val cvModel = cv.fit(trainingSet)

// COMMAND ----------

cvModel.bestModel.extractParamMap

// COMMAND ----------

// MAGIC %md The model tuning improved RMSE from 13.46 to 3.25.

// COMMAND ----------

val predictions2 = cvModel.transform(testSet)
val rmse2 = evaluator.evaluate(predictions2)

// COMMAND ----------

print("Root mean squared error: " + rmse2)

// COMMAND ----------

display(predictions2.select("label","prediction"))