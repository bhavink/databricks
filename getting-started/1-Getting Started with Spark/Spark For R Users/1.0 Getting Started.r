# Databricks notebook source
# MAGIC %md
# MAGIC 
# MAGIC ### The two most commonly used libraries that provide an R interface to Spark are [SparkR](https://spark.apache.org/docs/latest/sparkr.html) and [sparklyr](https://spark.rstudio.com/). 
# MAGIC ### Databricks notebooks and jobs support both packages, although you cannot use functions from both SparkR and sparklyr with the same object.

# COMMAND ----------

# MAGIC %md
# MAGIC 
# MAGIC #### SparkR is an R package that provides a light-weight frontend to use Apache Spark from R. SparkR also supports distributed machine learning using MLlib.

# COMMAND ----------

# DBTITLE 1,Create SparkR DataFrames
library(SparkR)
df <- createDataFrame(faithful)

# Displays the content of the DataFrame to stdout
head(df)

# COMMAND ----------

# DBTITLE 1,Using Spark DataSource API
library(SparkR)
diamondsDF <- read.df("/databricks-datasets/Rdatasets/data-001/csv/ggplot2/diamonds.csv", source = "csv", header="true", inferSchema = "true")
# SparkR automatically infers the schema from the CSV file.
head(diamondsDF)

# COMMAND ----------

#take an existing data.frame, convert to a Spark DataFrame, and save it as an Avro file.
require(SparkR)
irisDF <- createDataFrame(iris)
write.df(irisDF, source = "com.databricks.spark.avro", path = "dbfs:/tmp/iris.avro", mode = "overwrite")

# COMMAND ----------

# MAGIC %fs ls /tmp/iris.avro

# COMMAND ----------

#now read avro files back

irisDF2 <- read.df(path = "/tmp/iris.avro", source = "com.databricks.spark.avro")
head(irisDF2)

# COMMAND ----------

# DBTITLE 1,Save DataFrame To Parquet
write.df(irisDF2, path="dbfs:/tmp/iris.parquet", source="parquet", mode="overwrite")

# COMMAND ----------

# DBTITLE 1,Query Using SQL
# Register earlier df as temp view
createOrReplaceTempView(irisDF2, "irisTemp")


# COMMAND ----------

# Create a df consisting of only the 'species' column using a Spark SQL query
species <- sql("SELECT distinct(species) FROM irisTemp")
display(species)

# COMMAND ----------

# Import SparkR package if this is a new notebook
require(SparkR)

# Create DataFrame
df <- createDataFrame(faithful)

# Select only the "eruptions" column
head(select(df, df$eruptions))

# COMMAND ----------

# Filter the DataFrame to only retain rows with wait times shorter than 50 mins
head(filter(df, df$waiting < 50))

# COMMAND ----------

head(count(groupBy(df, df$waiting)))

# COMMAND ----------

# You can also sort the output from the aggregation to get the most common waiting times
waiting_counts <- count(groupBy(df, df$waiting))
head(arrange(waiting_counts, desc(waiting_counts$count)))

# COMMAND ----------

# Convert waiting time from hours to seconds.
# You can assign this to a new column in the same DataFrame
df$waiting_secs <- df$waiting * 60
head(df)

# COMMAND ----------

# Create the DataFrame
df <- createDataFrame(iris)

# Fit a linear model over the dataset.
model <- glm(Sepal_Length ~ Sepal_Width + Species, data = df, family = "gaussian")

# Model coefficients are returned in a similar format to R's native glm().
summary(model)

# COMMAND ----------

# MAGIC %md ### ML Using SparkR

# COMMAND ----------

# DBTITLE 1,Load diamonds data and split into training and test sets
require(SparkR)

# Read diamonds.csv dataset as SparkDataFrame
diamonds <- read.df("/databricks-datasets/Rdatasets/data-001/csv/ggplot2/diamonds.csv",
                  source = "com.databricks.spark.csv", header="true", inferSchema = "true")
diamonds <- withColumnRenamed(diamonds, "", "rowID")

# Split data into Training set and Test set
trainingData <- sample(diamonds, FALSE, 0.7)
testData <- except(diamonds, trainingData)

# Exclude rowIDs
trainingData <- trainingData[, -1]
testData <- testData[, -1]

print(count(diamonds))
print(count(trainingData))
print(count(testData))
head(trainingData)

# COMMAND ----------

# DBTITLE 1,Train a linear regression model using glm()
# This section shows how to predict a diamond’s price from its features by training a linear regression model using the training data.

# There are mix of categorical features (cut - Ideal, Premium, Very Good…) and continuous features (depth, carat). 
# Under the hood, SparkR automatically performs one-hot encoding of such features so that it does not have to be done manually.

# Family = "gaussian" to train a linear regression model
lrModel <- glm(price ~ ., data = trainingData, family = "gaussian")

# Print a summary of the trained model
summary(lrModel)

# COMMAND ----------

# DBTITLE 1,Predict
# Use predict() on the test data to see how well the model works on new data.

# Syntax: predict(model, newData)

# Parameters:

# model: MLlib model
# newData: SparkDataFrame, typically your test set
# Output: SparkDataFrame

# Generate predictions using the trained model
predictions <- predict(lrModel, newData = testData)

# View predictions against mpg column
display(select(predictions, "price", "prediction"))

# COMMAND ----------

# DBTITLE 1,Evaluate
errors <- select(predictions, predictions$price, predictions$prediction, alias(predictions$price - predictions$prediction, "error"))
display(errors)

# Calculate RMSE
head(select(errors, alias(sqrt(sum(errors$error^2 , na.rm = TRUE) / nrow(errors)), "RMSE")))

# COMMAND ----------

# DBTITLE 1,Train a logistic regression model using glm()
# This section shows how to create a logistic regression on the same dataset to predict a diamond’s cut based on some of its features.

# Logistic regression in MLlib supports only binary classification. To test the algorithm in this example, subset the data to work with only 2 labels.

# Subset data to include rows where diamond cut = "Premium" or diamond cut = "Very Good"
trainingDataSub <- subset(trainingData, trainingData$cut %in% c("Premium", "Very Good"))
testDataSub <- subset(testData, testData$cut %in% c("Premium", "Very Good"))

# COMMAND ----------

# Family = "binomial" to train a logistic regression model
logrModel <- glm(cut ~ price + color + clarity + depth, data = trainingDataSub, family = "binomial")

# Print summary of the trained model
summary(logrModel)

# COMMAND ----------

# DBTITLE 1,Predict
# Generate predictions using the trained model
predictionsLogR <- predict(logrModel, newData = testDataSub)

# View predictions against label column
display(select(predictionsLogR, "label", "prediction"))

# COMMAND ----------

# DBTITLE 1,Evaluate
errorsLogR <- select(predictionsLogR, predictionsLogR$label, predictionsLogR$prediction, alias(abs(predictionsLogR$label - predictionsLogR$prediction), "error"))
display(errorsLogR)

# COMMAND ----------

