# Databricks notebook source
# MAGIC %md # SFO Survey Machine Learning Example
# MAGIC 
# MAGIC Each year, San Francisco Airport (SFO) conducts a customer satisfaction survey to find out what they are doing well and where they can improve. The survey gauges satisfaction with SFO facilities, services, and amenities. SFO compares results to previous surveys to discover elements of the guest experience that are not satisfactory.
# MAGIC 
# MAGIC The 2013 SFO Survey Results consists of customer responses to survey questions and an overall satisfaction rating with the airport. We investigated whether we could use machine learning to predict a customer's overall response given their responses to the individual questions. That in and of itself is not very useful because the customer has already provided an overall rating as well as individual ratings for various aspects of the airport such as parking, food quality and restroom cleanliness. However, we didn't stop at prediction instead we asked the question: 
# MAGIC 
# MAGIC ***What factors drove the customer to give the overall rating?***

# COMMAND ----------

# MAGIC %md 
# MAGIC Here is an outline of our data flow:
# MAGIC * *Load data*: Load the data as a DataFrame
# MAGIC * *Understand the data*: Compute statistics and create visualizations to get a better understanding of the data to see if we can use basic statistics to answer the question above.
# MAGIC * *Create Model* On the training dataset:
# MAGIC   * *Evaluate the model*: Now look at the test dataset.  Compare the initial model with the tuned model to see the benefit of tuning parameters.
# MAGIC   * *Feature Importance*: Determine the importance of each of the individual ratings in determining the overall rating by the customer
# MAGIC 
# MAGIC This dataset is available as a public dataset from https://catalog.data.gov/dataset/2013-sfo-customer-survey-d3541.

# COMMAND ----------

# MAGIC %md ##Load the Data

# COMMAND ----------

survey = spark.read.csv("dbfs:/databricks-datasets/sfo_customer_survey/2013_SFO_Customer_Survey.csv", header="true", inferSchema="true")

# COMMAND ----------

# MAGIC %md Use ```display()``` to confirm the data has been loaded.

# COMMAND ----------

display(survey)

# COMMAND ----------

# MAGIC %md ## Understand the Data

# COMMAND ----------

# MAGIC %md Gain a basic understanding of the data by looking at the schema.

# COMMAND ----------

survey.printSchema()

# COMMAND ----------

# MAGIC %md As you can see above there are many questions in the survey including what airline the customer flew on, where do they live, etc. For the purposes of answering the above, focus on the Q7A, Q7B, Q7C .. Q7O questions since they directly related to customer satisfaction, which is what you want to measure. If you drill down on those variables you get the following:
# MAGIC 
# MAGIC Column Name|Data Type|Description
# MAGIC ---|---|---|---
# MAGIC Q7B_FOOD|INTEGER|Restaurants 
# MAGIC Q7C_SHOPS|INTEGER|Retail shops and concessions
# MAGIC Q7D_SIGNS|INTEGER|Signs and Directions inside SFO
# MAGIC Q7E_WALK|INTEGER|Escalators / elevators / moving walkways
# MAGIC Q7F_SCREENS|INTEGER|Information on screens and monitors
# MAGIC Q7G_INFOARR|INTEGER|Information booth near arrivals area 
# MAGIC Q7H_INFODEP|INTEGER|Information booth near departure areas
# MAGIC Q7I_WIFI|INTEGER|Airport WiFi
# MAGIC Q7J_ROAD|INTEGER|Signs and directions on SFO airport roadways
# MAGIC Q7K_PARK|INTEGER|Airport parking facilities
# MAGIC Q7L_AIRTRAIN|INTEGER|AirTrain
# MAGIC Q7M_LTPARK|INTEGER|Long term parking lot shuttle
# MAGIC Q7N_RENTAL|INTEGER|Airport rental car center
# MAGIC Q7O_WHOLE|INTEGER|SFO Airport as a whole
# MAGIC 
# MAGIC 
# MAGIC The possible values for the above are:
# MAGIC 
# MAGIC 0 = no answer, 1 = Unacceptable, 2 = Below Average, 3 = Average, 4 = Good, 5 = Outstanding, 6 = Not visited or not applicable
# MAGIC 
# MAGIC Select only the fields you are interested in.

# COMMAND ----------

dataset = survey.select("Q7A_ART", "Q7B_FOOD", "Q7C_SHOPS", "Q7D_SIGNS", "Q7E_WALK", "Q7F_SCREENS", "Q7G_INFOARR", "Q7H_INFODEP", "Q7I_WIFI", "Q7J_ROAD", "Q7K_PARK", "Q7L_AIRTRAIN", "Q7M_LTPARK", "Q7N_RENTAL", "Q7O_WHOLE")

# COMMAND ----------

# MAGIC %md Let's get some basic statistics such as looking at the average of each column.

# COMMAND ----------

a = map(lambda s: "'missingValues(" + s +") " + s + "'",["Q7A_ART", "Q7B_FOOD", "Q7C_SHOPS", "Q7D_SIGNS", "Q7E_WALK", "Q7F_SCREENS", "Q7G_INFOARR", "Q7H_INFODEP", "Q7I_WIFI", "Q7J_ROAD", "Q7K_PARK", "Q7L_AIRTRAIN", "Q7M_LTPARK", "Q7N_RENTAL", "Q7O_WHOLE"])
", ".join(a)

# COMMAND ----------

# MAGIC %md Let's start with the overall rating.

# COMMAND ----------

from pyspark.sql.functions import *
dataset.selectExpr('avg(Q7O_WHOLE) Q7O_WHOLE').take(1)

# COMMAND ----------

# MAGIC %md The overall rating is only 3.87, so slightly above average. Let's get the averages of the constituent ratings:

# COMMAND ----------

avgs = dataset.selectExpr('avg(Q7A_ART) Q7A_ART', 'avg(Q7B_FOOD) Q7B_FOOD', 'avg(Q7C_SHOPS) Q7C_SHOPS', 'avg(Q7D_SIGNS) Q7D_SIGNS', 'avg(Q7E_WALK) Q7E_WALK', 'avg(Q7F_SCREENS) Q7F_SCREENS', 'avg(Q7G_INFOARR) Q7G_INFOARR', 'avg(Q7H_INFODEP) Q7H_INFODEP', 'avg(Q7I_WIFI) Q7I_WIFI', 'avg(Q7J_ROAD) Q7J_ROAD', 'avg(Q7K_PARK) Q7K_PARK', 'avg(Q7L_AIRTRAIN) Q7L_AIRTRAIN', 'avg(Q7M_LTPARK) Q7M_LTPARK', 'avg(Q7N_RENTAL) Q7N_RENTAL')
display(avgs)

# COMMAND ----------

# MAGIC %md Looking at the bar chart above - the overall average rating of the airport is actually lower than all of the individual ratings. This appears clearer using the bar chart visualization below.

# COMMAND ----------

display(dataset)

# COMMAND ----------

# MAGIC %md So basic statistics can't seem to answer the question: ***What factors drove the customer to give the overall rating?*** 
# MAGIC 
# MAGIC So let's try to use a predictive algorithm to see if these individual ratings can be used to predict an overall rating.

# COMMAND ----------

# MAGIC %md ## Create Model
# MAGIC 
# MAGIC Here use a decision tree algorithm to create a predictive model.

# COMMAND ----------

# MAGIC %md First need to treat responses of 0 = No Answer and 6 = Not Visited or Not Applicable as missing values. One of the ways you can do this is a technique called *mean impute* which is when we use the mean of the column as a replacement for the missing value. You can use a `replace` function to set all values of 0 or 6 to the average rating of 3. You also need a `label` column of type `double` so do that as well.

# COMMAND ----------

training = dataset.withColumn("label", dataset['Q7O_WHOLE']*1.0).na.replace(0,3).replace(6,3)

# COMMAND ----------

display(training)

# COMMAND ----------

# MAGIC %md Define the machine learning pipeline.

# COMMAND ----------

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

# COMMAND ----------

# MAGIC %md Now call ```fit``` to build the model.

# COMMAND ----------

model = pipeline.fit(training)

# COMMAND ----------

# MAGIC %md Now call `display` to view the tree.

# COMMAND ----------

display(model.stages[-1])

# COMMAND ----------

# MAGIC %md Call `transform` to view the predictions.

# COMMAND ----------

predictions = model.transform(training)
display(predictions)

# COMMAND ----------

# MAGIC %md ##Evaluate the model

# COMMAND ----------

# MAGIC %md Validate the model using root mean squared error (RMSE).

# COMMAND ----------

from pyspark.ml.evaluation import RegressionEvaluator

evaluator = RegressionEvaluator()

evaluator.evaluate(predictions, {evaluator.metricName: "rmse"})

# COMMAND ----------

# MAGIC %md Save the model.

# COMMAND ----------

dbutils.fs.rm("/tmp/sfo_survey_model", True)
model.save("/tmp/sfo_survey_model")

# COMMAND ----------

# MAGIC %md ##Feature Importance

# COMMAND ----------

# MAGIC %md Now let's look at the feature importances. The variable is shown below.

# COMMAND ----------

model.stages[1].featureImportances

# COMMAND ----------

# MAGIC %md Feature importance is a measure of information gain. It is scaled from 0.0 to 1.0. As an example, feature 1 in the example above is rated as 0.0826 or 8.26% of the total importance for all the features.

# COMMAND ----------

# MAGIC %md Let's map the features to their proper names to make them easier to read.

# COMMAND ----------

featureImportance = model.stages[1].featureImportances.toArray()
featureNames = map(lambda s: s.name, dataset.schema.fields)
featureImportanceMap = zip(featureImportance, featureNames)

# COMMAND ----------

featureImportanceMap

# COMMAND ----------

# MAGIC %md Let's convert this to a DataFrame so you can view it and save it so other users can rely on this information.

# COMMAND ----------

importancesDf = spark.createDataFrame(sc.parallelize(featureImportanceMap).map(lambda r: [r[1], float(r[0])]))

# COMMAND ----------

importancesDf = importancesDf.withColumnRenamed("_1", "Feature").withColumnRenamed("_2", "Importance")

# COMMAND ----------

display(importancesDf.orderBy(desc("Importance")))

# COMMAND ----------

# MAGIC %md As you can see below, the 3 most important features are:
# MAGIC 
# MAGIC 1. Signs 
# MAGIC 2. Screens
# MAGIC 3. Food
# MAGIC 
# MAGIC This is useful information for the airport management. It means that people want to first know where they are going. Second, they check the airport screens and monitors so they can find their gate and be on time for their flight.  Third, they like to have good quality food.
# MAGIC 
# MAGIC This is especially interesting considering that taking the average of these feature variables told us nothing about the importance of the variables in determining the overall rating by the survey responder.
# MAGIC 
# MAGIC These 3 features combine to make up 65% of the overall rating.

# COMMAND ----------

importancesDf.orderBy(desc("Importance")).limit(3).agg(sum("Importance")).take(1)

# COMMAND ----------

# MAGIC %md You can also show this graphically.

# COMMAND ----------

display(importancesDf.orderBy(desc("Importance")))

# COMMAND ----------

display(importancesDf.orderBy(desc("Importance")).limit(5))

# COMMAND ----------

# MAGIC %md So if you run SFO, artwork and shopping are nice-to-haves but signs, monitors, and food are what keep airport customers happy!