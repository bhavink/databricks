***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED*** The two most commonly used libraries that provide an R interface to Spark are [SparkR](https://spark.apache.org/docs/latest/sparkr.html) and [sparklyr](https://spark.rstudio.com/). 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED*** Databricks notebooks and jobs support both packages, although you cannot use functions from both SparkR and sparklyr with the same object.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** SparkR is an R package that provides a light-weight frontend to use Apache Spark from R. SparkR also supports distributed machine learning using MLlib.

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Create SparkR DataFrames
library(SparkR)
df <- createDataFrame(faithful)

***REMOVED*** Displays the content of the DataFrame to stdout
head(df)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Using Spark DataSource API
library(SparkR)
diamondsDF <- read.df("/databricks-datasets/Rdatasets/data-001/csv/ggplot2/diamonds.csv", source = "csv", header="true", inferSchema = "true")
***REMOVED*** SparkR automatically infers the schema from the CSV file.
head(diamondsDF)

***REMOVED*** COMMAND ----------

***REMOVED***take an existing data.frame, convert to a Spark DataFrame, and save it as an Avro file.
require(SparkR)
irisDF <- createDataFrame(iris)
write.df(irisDF, source = "com.databricks.spark.avro", path = "dbfs:/tmp/iris.avro", mode = "overwrite")

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %fs ls /tmp/iris.avro

***REMOVED*** COMMAND ----------

***REMOVED***now read avro files back

irisDF2 <- read.df(path = "/tmp/iris.avro", source = "com.databricks.spark.avro")
head(irisDF2)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Save DataFrame To Parquet
write.df(irisDF2, path="dbfs:/tmp/iris.parquet", source="parquet", mode="overwrite")

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Query Using SQL
***REMOVED*** Register earlier df as temp view
createOrReplaceTempView(irisDF2, "irisTemp")


***REMOVED*** COMMAND ----------

***REMOVED*** Create a df consisting of only the 'species' column using a Spark SQL query
species <- sql("SELECT distinct(species) FROM irisTemp")
display(species)

***REMOVED*** COMMAND ----------

***REMOVED*** Import SparkR package if this is a new notebook
require(SparkR)

***REMOVED*** Create DataFrame
df <- createDataFrame(faithful)

***REMOVED*** Select only the "eruptions" column
head(select(df, df$eruptions))

***REMOVED*** COMMAND ----------

***REMOVED*** Filter the DataFrame to only retain rows with wait times shorter than 50 mins
head(filter(df, df$waiting < 50))

***REMOVED*** COMMAND ----------

head(count(groupBy(df, df$waiting)))

***REMOVED*** COMMAND ----------

***REMOVED*** You can also sort the output from the aggregation to get the most common waiting times
waiting_counts <- count(groupBy(df, df$waiting))
head(arrange(waiting_counts, desc(waiting_counts$count)))

***REMOVED*** COMMAND ----------

***REMOVED*** Convert waiting time from hours to seconds.
***REMOVED*** You can assign this to a new column in the same DataFrame
df$waiting_secs <- df$waiting * 60
head(df)

***REMOVED*** COMMAND ----------

***REMOVED*** Create the DataFrame
df <- createDataFrame(iris)

***REMOVED*** Fit a linear model over the dataset.
model <- glm(Sepal_Length ~ Sepal_Width + Species, data = df, family = "gaussian")

***REMOVED*** Model coefficients are returned in a similar format to R's native glm().
summary(model)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md ***REMOVED******REMOVED******REMOVED*** ML Using SparkR

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Load diamonds data and split into training and test sets
require(SparkR)

***REMOVED*** Read diamonds.csv dataset as SparkDataFrame
diamonds <- read.df("/databricks-datasets/Rdatasets/data-001/csv/ggplot2/diamonds.csv",
                  source = "com.databricks.spark.csv", header="true", inferSchema = "true")
diamonds <- withColumnRenamed(diamonds, "", "rowID")

***REMOVED*** Split data into Training set and Test set
trainingData <- sample(diamonds, FALSE, 0.7)
testData <- except(diamonds, trainingData)

***REMOVED*** Exclude rowIDs
trainingData <- trainingData[, -1]
testData <- testData[, -1]

print(count(diamonds))
print(count(trainingData))
print(count(testData))
head(trainingData)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Train a linear regression model using glm()
***REMOVED*** This section shows how to predict a diamond’s price from its features by training a linear regression model using the training data.

***REMOVED*** There are mix of categorical features (cut - Ideal, Premium, Very Good…) and continuous features (depth, carat). 
***REMOVED*** Under the hood, SparkR automatically performs one-hot encoding of such features so that it does not have to be done manually.

***REMOVED*** Family = "gaussian" to train a linear regression model
lrModel <- glm(price ~ ., data = trainingData, family = "gaussian")

***REMOVED*** Print a summary of the trained model
summary(lrModel)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Predict
***REMOVED*** Use predict() on the test data to see how well the model works on new data.

***REMOVED*** Syntax: predict(model, newData)

***REMOVED*** Parameters:

***REMOVED*** model: MLlib model
***REMOVED*** newData: SparkDataFrame, typically your test set
***REMOVED*** Output: SparkDataFrame

***REMOVED*** Generate predictions using the trained model
predictions <- predict(lrModel, newData = testData)

***REMOVED*** View predictions against mpg column
display(select(predictions, "price", "prediction"))

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Evaluate
errors <- select(predictions, predictions$price, predictions$prediction, alias(predictions$price - predictions$prediction, "error"))
display(errors)

***REMOVED*** Calculate RMSE
head(select(errors, alias(sqrt(sum(errors$error^2 , na.rm = TRUE) / nrow(errors)), "RMSE")))

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Train a logistic regression model using glm()
***REMOVED*** This section shows how to create a logistic regression on the same dataset to predict a diamond’s cut based on some of its features.

***REMOVED*** Logistic regression in MLlib supports only binary classification. To test the algorithm in this example, subset the data to work with only 2 labels.

***REMOVED*** Subset data to include rows where diamond cut = "Premium" or diamond cut = "Very Good"
trainingDataSub <- subset(trainingData, trainingData$cut %in% c("Premium", "Very Good"))
testDataSub <- subset(testData, testData$cut %in% c("Premium", "Very Good"))

***REMOVED*** COMMAND ----------

***REMOVED*** Family = "binomial" to train a logistic regression model
logrModel <- glm(cut ~ price + color + clarity + depth, data = trainingDataSub, family = "binomial")

***REMOVED*** Print summary of the trained model
summary(logrModel)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Predict
***REMOVED*** Generate predictions using the trained model
predictionsLogR <- predict(logrModel, newData = testDataSub)

***REMOVED*** View predictions against label column
display(select(predictionsLogR, "label", "prediction"))

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Evaluate
errorsLogR <- select(predictionsLogR, predictionsLogR$label, predictionsLogR$prediction, alias(abs(predictionsLogR$label - predictionsLogR$prediction), "error"))
display(errorsLogR)

***REMOVED*** COMMAND ----------

