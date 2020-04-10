# Databricks notebook source
# MAGIC %md ## Quick Start Using Python
# MAGIC * Using a Databricks notebook to showcase DataFrame operations using Python
# MAGIC * Reference http://spark.apache.org/docs/latest/quick-start.html

# COMMAND ----------

# Take a look at the file system
display(dbutils.fs.ls("/databricks-datasets/samples/docs/"))

# COMMAND ----------

# MAGIC %md DataFrames have ***transformations***, which return pointers to new DataFrames, and ***actions***, which return values.

# COMMAND ----------

# transformation
textFile = spark.read.text("/databricks-datasets/samples/docs/README.md")

# COMMAND ----------

# action
textFile.count()

# COMMAND ----------

# Output the first line from the text file
textFile.first()

# COMMAND ----------

# MAGIC %md 
# MAGIC Now we're using a filter ***transformation*** to return a new DataFrame with a subset of the items in the file.

# COMMAND ----------

# Filter all of the lines within the DataFrame
linesWithSpark = textFile.filter(textFile.value.contains("Spark"))

# COMMAND ----------

# MAGIC %md Notice that this completes quickly because it is a transformation but lacks any action.  
# MAGIC * But when performing the actions below (e.g. count, take) then you will see the executions.

# COMMAND ----------

# Perform a count (action) 
linesWithSpark.count()

# COMMAND ----------

# Output the first five rows
linesWithSpark.take(5)