***REMOVED*** Databricks notebook source
***REMOVED*** DBTITLE 1,Read Databricks switch action dataset  
from pyspark.sql.functions import expr
from pyspark.sql.functions import from_unixtime

events = spark.read \
  .option("inferSchema", "true") \
  .json("/databricks-datasets/structured-streaming/events/") \
  .withColumn("date", expr("time")) \
  .drop("time") \
  .withColumn("date", from_unixtime("date", 'yyyy-MM-dd'))
  
display(events)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Write out DataFrame as Databricks Delta data
events.write.format("delta").mode("overwrite").partitionBy("date").save("/delta/events/")

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Query the data file path
events_delta = spark.read.format("delta").load("/delta/events/")

display(events_delta)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Create table
display(spark.sql("DROP TABLE IF EXISTS events"))

display(spark.sql("CREATE TABLE events USING DELTA LOCATION '/delta/events/'"))

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Query the table
events_delta.count()

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Visualize data
from pyspark.sql.functions import count
display(events_delta.groupBy("action","date").agg(count("action").alias("action_count")).orderBy("date", "action"))

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Generate historical data - original data shifted backwards 2 days
historical_events = spark.read \
  .option("inferSchema", "true") \
  .json("/databricks-datasets/structured-streaming/events/") \
  .withColumn("date", expr("time-172800")) \
  .drop("time") \
  .withColumn("date", from_unixtime("date", 'yyyy-MM-dd'))

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Append historical data
historical_events.write.format("delta").mode("append").partitionBy("date").save("/delta/events/")

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Visualize final data
display(events_delta.groupBy("action","date").agg(count("action").alias("action_count")).orderBy("date", "action"))

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Count rows
events_delta.count()

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Show contents of a partition
dbutils.fs.ls("dbfs:/delta/events/date=2016-07-25/")

***REMOVED*** COMMAND ----------

display(spark.sql("OPTIMIZE events"))

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Show table history
display(spark.sql("DESCRIBE HISTORY events"))

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Show table details
display(spark.sql("DESCRIBE DETAIL events"))

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Show the table format
display(spark.sql("DESCRIBE FORMATTED events"))