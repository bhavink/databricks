***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md ***REMOVED******REMOVED*** Quick Start Using Python
***REMOVED*** MAGIC * Using a Databricks notebook to showcase DataFrame operations using Python
***REMOVED*** MAGIC * Reference http://spark.apache.org/docs/latest/quick-start.html

***REMOVED*** COMMAND ----------

***REMOVED*** Take a look at the file system
display(dbutils.fs.ls("/databricks-datasets/samples/docs/"))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md DataFrames have ***transformations***, which return pointers to new DataFrames, and ***actions***, which return values.

***REMOVED*** COMMAND ----------

***REMOVED*** transformation
textFile = spark.read.text("/databricks-datasets/samples/docs/README.md")

***REMOVED*** COMMAND ----------

***REMOVED*** action
textFile.count()

***REMOVED*** COMMAND ----------

***REMOVED*** Output the first line from the text file
textFile.first()

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC Now we're using a filter ***transformation*** to return a new DataFrame with a subset of the items in the file.

***REMOVED*** COMMAND ----------

***REMOVED*** Filter all of the lines within the DataFrame
linesWithSpark = textFile.filter(textFile.value.contains("Spark"))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Notice that this completes quickly because it is a transformation but lacks any action.  
***REMOVED*** MAGIC * But when performing the actions below (e.g. count, take) then you will see the executions.

***REMOVED*** COMMAND ----------

***REMOVED*** Perform a count (action) 
linesWithSpark.count()

***REMOVED*** COMMAND ----------

***REMOVED*** Output the first five rows
linesWithSpark.take(5)