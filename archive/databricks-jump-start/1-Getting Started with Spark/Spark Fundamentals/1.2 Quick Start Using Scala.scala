// Databricks notebook source
// MAGIC %md ## Quick Start Using Scala
// MAGIC * Using a Databricks notebook to showcase Dataset operations using Scala
// MAGIC * Reference http://spark.apache.org/docs/latest/quick-start.html

// COMMAND ----------

// Take a look at the file system
display(dbutils.fs.ls("/databricks-datasets/samples/docs/"))

// COMMAND ----------

// MAGIC %md Datasets have ***transformations***, which return pointers to new Datasets and ***actions***, which return values.

// COMMAND ----------

// transformation
val textFile = spark.read.textFile("/databricks-datasets/samples/docs/README.md")

// COMMAND ----------

// action
textFile.count()

// COMMAND ----------

// Output the first line from the text file
textFile.first()

// COMMAND ----------

// MAGIC %md 
// MAGIC Now we're using a filter ***transformation*** to return a new Dataset with a subset of the items in the file.

// COMMAND ----------

// Filter all of the lines within the Dataset
val linesWithSpark = textFile.filter(line => line.contains("Spark"))

// COMMAND ----------

// MAGIC %md Notice that this completes quickly because it is a transformation but lacks any action.  
// MAGIC * But when performing the actions below (e.g. count, take) then you will see the executions.

// COMMAND ----------

// Perform a count (action) 
linesWithSpark.count()

// COMMAND ----------

// Output the first five rows
linesWithSpark.collect().take(5).foreach(println)