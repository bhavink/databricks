***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED*** Spark interfaces
***REMOVED*** MAGIC There are three key Spark interfaces that you should know about.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Resilient Distributed Dataset (RDD)
***REMOVED*** MAGIC Apache Spark’s first abstraction was the RDD. It is an interface to a sequence of data objects that consist of one or more types that are located across a collection of machines (a cluster). RDDs can be created in a variety of ways and are the “lowest level” API available. While this is the original data structure for Apache Spark, you should focus on the DataFrame API, which is a superset of the RDD functionality. The RDD API is available in the Java, Python, and Scala languages.
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** DataFrame
***REMOVED*** MAGIC These are similar in concept to the DataFrame you may be familiar with in the pandas Python library and the R language. The DataFrame API is available in the Java, Python, R, and Scala languages.
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED******REMOVED*** Dataset
***REMOVED*** MAGIC A combination of DataFrame and RDD. It provides the typed interface that is available in RDDs while providing the convenience of the DataFrame. The Dataset API is available in the Java and Scala languages.
***REMOVED*** MAGIC In many scenarios, especially with the performance optimizations embedded in DataFrames and Datasets, it will not be necessary to work with RDDs. But it is important to understand the RDD abstraction because:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC The RDD is the underlying infrastructure that allows Spark to run so fast and provide data lineage.
***REMOVED*** MAGIC If you are diving into more advanced components of Spark, it may be necessary to use RDDs.
***REMOVED*** MAGIC The visualizations within the Spark UI reference RDDs.
***REMOVED*** MAGIC When you develop Spark applications, you typically use **DataFrames** and **Datasets**.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED*** Databricks datasets
***REMOVED*** MAGIC Databricks includes a variety of datasets within the Workspace that you can use to learn Spark or test out algorithms. 
***REMOVED*** MAGIC <br>You’ll see these throughout the getting started guide. 
***REMOVED*** MAGIC <br>The datasets are available in the **/databricks-datasets** folder

***REMOVED*** COMMAND ----------

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