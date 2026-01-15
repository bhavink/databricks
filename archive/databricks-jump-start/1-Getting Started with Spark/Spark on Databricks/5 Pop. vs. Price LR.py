***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md ***REMOVED*** Population vs. Median Home Prices
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** *Linear Regression with Single Variable*

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** Load and parse the data

***REMOVED*** COMMAND ----------

***REMOVED*** Use the Spark CSV datasource with options specifying:
***REMOVED***  - First line of file is a header
***REMOVED***  - Automatically infer the schema of the data
data = spark.read.csv("/databricks-datasets/samples/population-vs-price/data_geo.csv", header="true", inferSchema="true")
data.cache()  ***REMOVED*** Cache data for faster reuse
data.count()

***REMOVED*** COMMAND ----------

display(data)

***REMOVED*** COMMAND ----------

data = data.dropna()  ***REMOVED*** drop rows with missing values
data.count()

***REMOVED*** COMMAND ----------

from pyspark.sql.functions import col

exprs = [col(column).alias(column.replace(' ', '_')) for column in data.columns]

vdata = data.select(*exprs).selectExpr("2014_Population_estimate as population", "2015_median_sales_price as label")
display(vdata)

***REMOVED*** COMMAND ----------

from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler

stages = []
assembler = VectorAssembler(inputCols=["population"], outputCol="features")
stages += [assembler]
pipeline = Pipeline(stages=stages)
pipelineModel = pipeline.fit(vdata)
dataset = pipelineModel.transform(vdata)
***REMOVED*** Keep relevant columns
selectedcols = ["features", "label"]
display(dataset.select(selectedcols))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Scatterplot of the data using ggplot

***REMOVED*** COMMAND ----------

import numpy as np
from pandas import *
from ggplot import *

x = dataset.rdd.map(lambda p: (p.features[0])).collect()
y = dataset.rdd.map(lambda p: (p.label)).collect()

pydf = DataFrame({'pop':x,'price':y})
p = ggplot(pydf, aes('pop','price')) + \
    geom_point(color='blue') + \
    scale_x_log10() + scale_y_log10()
display(p)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Linear Regression
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **Goal**
***REMOVED*** MAGIC * Predict y = 2015 Median Housing Price
***REMOVED*** MAGIC * Using feature x = 2014 Population Estimate
***REMOVED*** MAGIC 
***REMOVED*** MAGIC **References**
***REMOVED*** MAGIC * [MLlib LinearRegression user guide](http://spark.apache.org/docs/latest/ml-classification-regression.html***REMOVED***linear-regression)
***REMOVED*** MAGIC * [PySpark LinearRegression API](http://spark.apache.org/docs/latest/api/python/pyspark.ml.html***REMOVED***pyspark.ml.regression.LinearRegression)

***REMOVED*** COMMAND ----------

***REMOVED*** Import LinearRegression class
from pyspark.ml.regression import LinearRegression
***REMOVED*** Define LinearRegression algorithm
lr = LinearRegression()

***REMOVED*** COMMAND ----------

***REMOVED*** Fit 2 models, using different regularization parameters
modelA = lr.fit(dataset, {lr.regParam:0.0})
modelB = lr.fit(dataset, {lr.regParam:100.0})
print(">>>> ModelA intercept: %r, coefficient: %r" % (modelA.intercept, modelA.coefficients[0]))
print(">>>> ModelB intercept: %r, coefficient: %r" % (modelB.intercept, modelB.coefficients[0]))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Make predictions
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Calling `transform()` on data adds a new column of predictions.

***REMOVED*** COMMAND ----------

***REMOVED*** Make predictions
predictionsA = modelA.transform(dataset)
display(predictionsA)

***REMOVED*** COMMAND ----------

predictionsB = modelB.transform(dataset)
display(predictionsB)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Evaluate the Model
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Predicted vs. True label

***REMOVED*** COMMAND ----------

from pyspark.ml.evaluation import RegressionEvaluator
evaluator = RegressionEvaluator(metricName="rmse")
RMSE = evaluator.evaluate(predictionsA)
print("ModelA: Root Mean Squared Error = " + str(RMSE))

***REMOVED*** COMMAND ----------

predictionsB = modelB.transform(dataset)
RMSE = evaluator.evaluate(predictionsB)
print("ModelB: Root Mean Squared Error = " + str(RMSE))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Plot residuals versus fitted values

***REMOVED*** COMMAND ----------

display(modelA,dataset)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED*** Linear Regression Plots

***REMOVED*** COMMAND ----------

import numpy as np
from pandas import *
from ggplot import *

pop = dataset.rdd.map(lambda p: (p.features[0])).collect()
price = dataset.rdd.map(lambda p: (p.label)).collect()
predA = predictionsA.select("prediction").rdd.map(lambda r: r[0]).collect()
predB = predictionsB.select("prediction").rdd.map(lambda r: r[0]).collect()

pydf = DataFrame({'pop':pop,'price':price,'predA':predA, 'predB':predB})

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** View the Python Pandas DataFrame (pydf)

***REMOVED*** COMMAND ----------

pydf

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** ggplot figure
***REMOVED*** MAGIC With the Pandas DataFrame (pydf), use ggplot and display the scatterplot and the two regression models

***REMOVED*** COMMAND ----------

p = ggplot(pydf, aes('pop','price')) + \
    geom_point(color='blue') + \
    geom_line(pydf, aes('pop','predA'), color='red') + \
    geom_line(pydf, aes('pop','predB'), color='green') + \
    scale_x_log10() + scale_y_log10()
display(p)