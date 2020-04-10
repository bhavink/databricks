// Databricks notebook source
import org.apache.spark.sql._
import org.apache.spark.sql.functions._

val events = spark.read 
  .option("inferSchema", "true") 
  .json("/databricks-datasets/structured-streaming/events/") 
  .withColumn("date", expr("time"))
  .drop("time")
  .withColumn("date", from_unixtime($"date", "yyyy-MM-dd"))
  
display(events)

// COMMAND ----------

// DBTITLE 1,Write out DataFrame as Databricks Delta data
import org.apache.spark.sql.SaveMode

events.write.format("delta").mode("overwrite").partitionBy("date").save("/delta/events/")

// COMMAND ----------

val events_delta = spark.read.format("delta").load("/delta/events/")
display(events_delta)

// COMMAND ----------

// DBTITLE 1,Create table
display(spark.sql("DROP TABLE IF EXISTS events"))
        
display(spark.sql("CREATE TABLE events USING DELTA LOCATION '/delta/events/'"))

// COMMAND ----------

// DBTITLE 1,Query the table
events_delta.count()

// COMMAND ----------

// DBTITLE 1,Visualize data
import org.apache.spark.sql._
import org.apache.spark.sql.functions._

display(events_delta.groupBy("action","date").agg(count("action").alias("action_count")).orderBy("date", "action"))

// COMMAND ----------

// DBTITLE 1,Generate historical data - original data shifted backwards 2 days
val historical_events = spark.read 
  .option("inferSchema", "true") 
  .json("/databricks-datasets/structured-streaming/events/") 
  .withColumn("date", expr("time-172800")) 
  .drop("time")
  .withColumn("date", from_unixtime($"date", "yyyy-MM-dd"))

// COMMAND ----------

// DBTITLE 1,Append historical data
historical_events.write.format("delta").mode("append").partitionBy("date").save("/delta/events/")

// COMMAND ----------

// DBTITLE 1,Count rows
events_delta.count()

// COMMAND ----------

// DBTITLE 1,Visualize final data
display(events_delta.groupBy("action","date").agg(count("action").alias("action_count")).orderBy("date", "action"))

// COMMAND ----------

// DBTITLE 1,Show the contents of a partition
dbutils.fs.ls("dbfs:/delta/events/date=2016-07-25/")

// COMMAND ----------

display(spark.sql("OPTIMIZE events"))

// COMMAND ----------

// DBTITLE 1,Show table history
display(spark.sql("DESCRIBE HISTORY events"))

// COMMAND ----------

// DBTITLE 1,Show table details
display(spark.sql("DESCRIBE DETAIL events"))

// COMMAND ----------

// DBTITLE 1,Show the table format
display(spark.sql("DESCRIBE FORMATTED events"))