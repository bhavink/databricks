# Databricks notebook source
# MAGIC %md
# MAGIC 
# MAGIC # Spark interfaces
# MAGIC There are three key Spark interfaces that you should know about.
# MAGIC 
# MAGIC #### Resilient Distributed Dataset (RDD)
# MAGIC Apache Spark’s first abstraction was the RDD. It is an interface to a sequence of data objects that consist of one or more types that are located across a collection of machines (a cluster). RDDs can be created in a variety of ways and are the “lowest level” API available. While this is the original data structure for Apache Spark, you should focus on the DataFrame API, which is a superset of the RDD functionality. The RDD API is available in the Java, Python, and Scala languages.
# MAGIC #### DataFrame
# MAGIC These are similar in concept to the DataFrame you may be familiar with in the pandas Python library and the R language. The DataFrame API is available in the Java, Python, R, and Scala languages.
# MAGIC #### Dataset
# MAGIC A combination of DataFrame and RDD. It provides the typed interface that is available in RDDs while providing the convenience of the DataFrame. The Dataset API is available in the Java and Scala languages.
# MAGIC In many scenarios, especially with the performance optimizations embedded in DataFrames and Datasets, it will not be necessary to work with RDDs. But it is important to understand the RDD abstraction because:
# MAGIC 
# MAGIC The RDD is the underlying infrastructure that allows Spark to run so fast and provide data lineage.
# MAGIC If you are diving into more advanced components of Spark, it may be necessary to use RDDs.
# MAGIC The visualizations within the Spark UI reference RDDs.
# MAGIC When you develop Spark applications, you typically use **DataFrames** and **Datasets**.

# COMMAND ----------

# MAGIC %md
# MAGIC 
# MAGIC # Databricks datasets
# MAGIC Databricks includes a variety of datasets within the Workspace that you can use to learn Spark or test out algorithms. 
# MAGIC <br>You’ll see these throughout the getting started guide. 
# MAGIC <br>The datasets are available in the **/databricks-datasets** folder

# COMMAND ----------

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