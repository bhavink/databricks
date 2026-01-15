***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md ***REMOVED*** SFO Survey Machine Learning Example
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Each year, San Francisco Airport (SFO) conducts a customer satisfaction survey to find out what they are doing well and where they can improve. The survey gauges satisfaction with SFO facilities, services, and amenities. SFO compares results to previous surveys to discover elements of the guest experience that are not satisfactory.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC The 2013 SFO Survey Results consists of customer responses to survey questions and an overall satisfaction rating with the airport. We investigated whether we could use machine learning to predict a customer's overall response given their responses to the individual questions. That in and of itself is not very useful because the customer has already provided an overall rating as well as individual ratings for various aspects of the airport such as parking, food quality and restroom cleanliness. However, we didn't stop at prediction instead we asked the question: 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***What factors drove the customer to give the overall rating?***

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC Here is an outline of our data flow:
***REMOVED*** MAGIC * *Load data*: Load the data as a DataFrame
***REMOVED*** MAGIC * *Understand the data*: Compute statistics and create visualizations to get a better understanding of the data to see if we can use basic statistics to answer the question above.
***REMOVED*** MAGIC * *Create Model* On the training dataset:
***REMOVED*** MAGIC   * *Evaluate the model*: Now look at the test dataset.  Compare the initial model with the tuned model to see the benefit of tuning parameters.
***REMOVED*** MAGIC   * *Feature Importance*: Determine the importance of each of the individual ratings in determining the overall rating by the customer
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This dataset is available as a public dataset from https://catalog.data.gov/dataset/2013-sfo-customer-survey-d3541.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED***Load the Data

***REMOVED*** COMMAND ----------

survey = spark.read.csv("dbfs:/databricks-datasets/sfo_customer_survey/2013_SFO_Customer_Survey.csv", header="true", inferSchema="true")

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Use ```display()``` to confirm the data has been loaded.

***REMOVED*** COMMAND ----------

display(survey)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Understand the Data

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Gain a basic understanding of the data by looking at the schema.

***REMOVED*** COMMAND ----------

survey.printSchema()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md As you can see above there are many questions in the survey including what airline the customer flew on, where do they live, etc. For the purposes of answering the above, focus on the Q7A, Q7B, Q7C .. Q7O questions since they directly related to customer satisfaction, which is what you want to measure. If you drill down on those variables you get the following:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Column Name|Data Type|Description
***REMOVED*** MAGIC ---|---|---|---
***REMOVED*** MAGIC Q7B_FOOD|INTEGER|Restaurants 
***REMOVED*** MAGIC Q7C_SHOPS|INTEGER|Retail shops and concessions
***REMOVED*** MAGIC Q7D_SIGNS|INTEGER|Signs and Directions inside SFO
***REMOVED*** MAGIC Q7E_WALK|INTEGER|Escalators / elevators / moving walkways
***REMOVED*** MAGIC Q7F_SCREENS|INTEGER|Information on screens and monitors
***REMOVED*** MAGIC Q7G_INFOARR|INTEGER|Information booth near arrivals area 
***REMOVED*** MAGIC Q7H_INFODEP|INTEGER|Information booth near departure areas
***REMOVED*** MAGIC Q7I_WIFI|INTEGER|Airport WiFi
***REMOVED*** MAGIC Q7J_ROAD|INTEGER|Signs and directions on SFO airport roadways
***REMOVED*** MAGIC Q7K_PARK|INTEGER|Airport parking facilities
***REMOVED*** MAGIC Q7L_AIRTRAIN|INTEGER|AirTrain
***REMOVED*** MAGIC Q7M_LTPARK|INTEGER|Long term parking lot shuttle
***REMOVED*** MAGIC Q7N_RENTAL|INTEGER|Airport rental car center
***REMOVED*** MAGIC Q7O_WHOLE|INTEGER|SFO Airport as a whole
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC The possible values for the above are:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 0 = no answer, 1 = Unacceptable, 2 = Below Average, 3 = Average, 4 = Good, 5 = Outstanding, 6 = Not visited or not applicable
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Select only the fields you are interested in.

***REMOVED*** COMMAND ----------

dataset = survey.select("Q7A_ART", "Q7B_FOOD", "Q7C_SHOPS", "Q7D_SIGNS", "Q7E_WALK", "Q7F_SCREENS", "Q7G_INFOARR", "Q7H_INFODEP", "Q7I_WIFI", "Q7J_ROAD", "Q7K_PARK", "Q7L_AIRTRAIN", "Q7M_LTPARK", "Q7N_RENTAL", "Q7O_WHOLE")

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Let's get some basic statistics such as looking at the average of each column.

***REMOVED*** COMMAND ----------

a = map(lambda s: "'missingValues(" + s +") " + s + "'",["Q7A_ART", "Q7B_FOOD", "Q7C_SHOPS", "Q7D_SIGNS", "Q7E_WALK", "Q7F_SCREENS", "Q7G_INFOARR", "Q7H_INFODEP", "Q7I_WIFI", "Q7J_ROAD", "Q7K_PARK", "Q7L_AIRTRAIN", "Q7M_LTPARK", "Q7N_RENTAL", "Q7O_WHOLE"])
", ".join(a)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Let's start with the overall rating.

***REMOVED*** COMMAND ----------

from pyspark.sql.functions import *
dataset.selectExpr('avg(Q7O_WHOLE) Q7O_WHOLE').take(1)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md The overall rating is only 3.87, so slightly above average. Let's get the averages of the constituent ratings:

***REMOVED*** COMMAND ----------

avgs = dataset.selectExpr('avg(Q7A_ART) Q7A_ART', 'avg(Q7B_FOOD) Q7B_FOOD', 'avg(Q7C_SHOPS) Q7C_SHOPS', 'avg(Q7D_SIGNS) Q7D_SIGNS', 'avg(Q7E_WALK) Q7E_WALK', 'avg(Q7F_SCREENS) Q7F_SCREENS', 'avg(Q7G_INFOARR) Q7G_INFOARR', 'avg(Q7H_INFODEP) Q7H_INFODEP', 'avg(Q7I_WIFI) Q7I_WIFI', 'avg(Q7J_ROAD) Q7J_ROAD', 'avg(Q7K_PARK) Q7K_PARK', 'avg(Q7L_AIRTRAIN) Q7L_AIRTRAIN', 'avg(Q7M_LTPARK) Q7M_LTPARK', 'avg(Q7N_RENTAL) Q7N_RENTAL')
display(avgs)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Looking at the bar chart above - the overall average rating of the airport is actually lower than all of the individual ratings. This appears clearer using the bar chart visualization below.

***REMOVED*** COMMAND ----------

display(dataset)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md So basic statistics can't seem to answer the question: ***What factors drove the customer to give the overall rating?*** 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC So let's try to use a predictive algorithm to see if these individual ratings can be used to predict an overall rating.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Create Model
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Here use a decision tree algorithm to create a predictive model.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md First need to treat responses of 0 = No Answer and 6 = Not Visited or Not Applicable as missing values. One of the ways you can do this is a technique called *mean impute* which is when we use the mean of the column as a replacement for the missing value. You can use a `replace` function to set all values of 0 or 6 to the average rating of 3. You also need a `label` column of type `double` so do that as well.

***REMOVED*** COMMAND ----------

training = dataset.withColumn("label", dataset['Q7O_WHOLE']*1.0).na.replace(0,3).replace(6,3)

***REMOVED*** COMMAND ----------

display(training)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Define the machine learning pipeline.

***REMOVED*** COMMAND ----------

from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import DecisionTreeRegressor
from pyspark.ml.tuning import ParamGridBuilder, CrossValidator
from pyspark.ml.evaluation import RegressionEvaluator

inputCols = ['Q7A_ART', 'Q7B_FOOD', 'Q7C_SHOPS', 'Q7D_SIGNS', 'Q7E_WALK', 'Q7F_SCREENS', 'Q7G_INFOARR', 'Q7H_INFODEP', 'Q7I_WIFI', 'Q7J_ROAD', 'Q7K_PARK', 'Q7L_AIRTRAIN', 'Q7M_LTPARK', 'Q7N_RENTAL']
va = VectorAssembler(inputCols=inputCols,outputCol="features")
dt = DecisionTreeRegressor(labelCol="label", featuresCol="features", maxDepth=4)
evaluator = RegressionEvaluator(metricName = "rmse", labelCol="label")
grid = ParamGridBuilder().addGrid(dt.maxDepth, [3, 5, 7, 10]).build()
cv = CrossValidator(estimator=dt, estimatorParamMaps=grid, evaluator=evaluator, numFolds = 10)
pipeline = Pipeline(stages=[va, dt])

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Now call ```fit``` to build the model.

***REMOVED*** COMMAND ----------

model = pipeline.fit(training)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Now call `display` to view the tree.

***REMOVED*** COMMAND ----------

display(model.stages[-1])

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Call `transform` to view the predictions.

***REMOVED*** COMMAND ----------

predictions = model.transform(training)
display(predictions)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED***Evaluate the model

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Validate the model using root mean squared error (RMSE).

***REMOVED*** COMMAND ----------

from pyspark.ml.evaluation import RegressionEvaluator

evaluator = RegressionEvaluator()

evaluator.evaluate(predictions, {evaluator.metricName: "rmse"})

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Save the model.

***REMOVED*** COMMAND ----------

dbutils.fs.rm("/tmp/sfo_survey_model", True)
model.save("/tmp/sfo_survey_model")

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED***Feature Importance

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Now let's look at the feature importances. The variable is shown below.

***REMOVED*** COMMAND ----------

model.stages[1].featureImportances

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Feature importance is a measure of information gain. It is scaled from 0.0 to 1.0. As an example, feature 1 in the example above is rated as 0.0826 or 8.26% of the total importance for all the features.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Let's map the features to their proper names to make them easier to read.

***REMOVED*** COMMAND ----------

featureImportance = model.stages[1].featureImportances.toArray()
featureNames = map(lambda s: s.name, dataset.schema.fields)
featureImportanceMap = zip(featureImportance, featureNames)

***REMOVED*** COMMAND ----------

featureImportanceMap

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Let's convert this to a DataFrame so you can view it and save it so other users can rely on this information.

***REMOVED*** COMMAND ----------

importancesDf = spark.createDataFrame(sc.parallelize(featureImportanceMap).map(lambda r: [r[1], float(r[0])]))

***REMOVED*** COMMAND ----------

importancesDf = importancesDf.withColumnRenamed("_1", "Feature").withColumnRenamed("_2", "Importance")

***REMOVED*** COMMAND ----------

display(importancesDf.orderBy(desc("Importance")))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md As you can see below, the 3 most important features are:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 1. Signs 
***REMOVED*** MAGIC 2. Screens
***REMOVED*** MAGIC 3. Food
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This is useful information for the airport management. It means that people want to first know where they are going. Second, they check the airport screens and monitors so they can find their gate and be on time for their flight.  Third, they like to have good quality food.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC This is especially interesting considering that taking the average of these feature variables told us nothing about the importance of the variables in determining the overall rating by the survey responder.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC These 3 features combine to make up 65% of the overall rating.

***REMOVED*** COMMAND ----------

importancesDf.orderBy(desc("Importance")).limit(3).agg(sum("Importance")).take(1)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md You can also show this graphically.

***REMOVED*** COMMAND ----------

display(importancesDf.orderBy(desc("Importance")))

***REMOVED*** COMMAND ----------

display(importancesDf.orderBy(desc("Importance")).limit(5))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md So if you run SFO, artwork and shopping are nice-to-haves but signs, monitors, and food are what keep airport customers happy!