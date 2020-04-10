***REMOVED*** Databricks notebook source
***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC ***REMOVED***Stream-Stream Joins using Structured Streaming (Python)
***REMOVED*** MAGIC Apache Spark 2.3.0 introduced support for stream-stream joins in Structured Streaming and this notebook illustrates different ways of joining streams. To run this notebook, import it into your Databricks workspace and run it on a cluster with Databricks Runtime 6.0 (which includes Apache Spark 2.3.0) or above. 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC We are going to use the the canonical example of ad monetization, where we want to find out which ad impressions led to user clicks. 
***REMOVED*** MAGIC Typically, in such scenarios, there are two streams of data from different sources - ad impressions and ad clicks. 
***REMOVED*** MAGIC Both type of events have a common ad identifier (say, `adId`), and we want to match clicks with impressions based on the `adId`. 
***REMOVED*** MAGIC In addition, each event also has a timestamp, which we will use to specify additional conditions in the query to limit the streaming state.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md In absence of actual data streams, we are going to generate fake data streams using our built-in "rate stream", that generates data at a given fixed rate.

***REMOVED*** COMMAND ----------

from pyspark.sql.functions import rand

spark.conf.set("spark.sql.shuffle.partitions", "1")

impressions = (
  spark
    .readStream.format("rate").option("rowsPerSecond", "5").option("numPartitions", "1").load()
    .selectExpr("value AS adId", "timestamp AS impressionTime")
)

clicks = (
  spark
  .readStream.format("rate").option("rowsPerSecond", "5").option("numPartitions", "1").load()
  .where((rand() * 100).cast("integer") < 10)      ***REMOVED*** 10 out of every 100 impressions result in a click
  .selectExpr("(value - 50) AS adId ", "timestamp AS clickTime")      ***REMOVED*** -50 so that a click with same id as impression is generated later (i.e. delayed data).
  .where("adId > 0")
)    
  

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC Let's see what data these two streaming DataFrames generate.

***REMOVED*** COMMAND ----------

display(impressions)

***REMOVED*** COMMAND ----------

display(clicks)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md Note: 
***REMOVED*** MAGIC - If you get an error saying the join is not supported, then you are running this notebook in an older version of Spark. Run this notebook in Databricks Runtime 4.0 (includes Apache Spark 2.3.0) or above.
***REMOVED*** MAGIC - If you are running on Community Edition, click Cancel above to stop the streams, as you do not have enough cores to run many streams simultaneously.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED*** Inner Join
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Let's join these two data streams. This is exactly the same as joining two batch DataFrames/Datasets by their common key `adId`.

***REMOVED*** COMMAND ----------

display(impressions.join(clicks, "adId"))

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC After you start this query, within a minute, you will start getting joined impressions and clicks. The delays of a minute is due to the fact that clicks are being generated with delay over the corresponding impressions.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC In addition, if you expand the details of the query above, you will find a few timelines of query metrics - the processing rates, the micro-batch durations, and the size of the state. 
***REMOVED*** MAGIC If you keep running this query, you will notice that the state will keep growing in an unbounded manner. This is because the query must buffer all past input as any new input can match with any input from the past. 

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED*** Inner Join with Watermarking
***REMOVED*** MAGIC 
***REMOVED*** MAGIC To avoid unbounded state, you have to define additional join conditions such that indefinitely old inputs cannot match with future inputs and therefore can be cleared from the state. In other words, you will have to do the following additional steps in the join.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 1. Define watermark delays on both inputs such that the engine knows how delayed the input can be. 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 1. Define a constraint on event-time across the two inputs such that the engine can figure out when old rows of one input is not going to be required (i.e. will not satisfy the time constraint) for matches with the other input. This constraint can be defined in one of the two ways.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC   a. Time range join conditions (e.g. `...JOIN ON leftTime BETWEN rightTime AND rightTime + INTERVAL 1 HOUR`),
***REMOVED*** MAGIC   
***REMOVED*** MAGIC   b. Join on event-time windows (e.g. `...JOIN ON leftTimeWindow = rightTimeWindow`).
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Let's apply these steps to our use case. 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 1. Watermark delays: Say, the impressions and the corresponding clicks can be delayed/late in event-time by at most "10 seconds" and "20 seconds", respectively. This is specified in the query as watermarks delays using `withWatermark`.
***REMOVED*** MAGIC 
***REMOVED*** MAGIC 1. Event-time range condition: Say, a click can occur within a time range of 0 seconds to 1 minute after the corresponding impression. This is specified in the query as a join condition between `impressionTime` and `clickTime`.

***REMOVED*** COMMAND ----------

from pyspark.sql.functions import expr

***REMOVED*** Define watermarks
impressionsWithWatermark = impressions \
  .selectExpr("adId AS impressionAdId", "impressionTime") \
  .withWatermark("impressionTime", "10 seconds ")
clicksWithWatermark = clicks \
  .selectExpr("adId AS clickAdId", "clickTime") \
  .withWatermark("clickTime", "20 seconds")        ***REMOVED*** max 20 seconds late


***REMOVED*** Inner join with time range conditions
display(
  impressionsWithWatermark.join(
    clicksWithWatermark,
    expr(""" 
      clickAdId = impressionAdId AND 
      clickTime >= impressionTime AND 
      clickTime <= impressionTime + interval 1 minutes    
      """
    )
  )
)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC We are getting the similar results as the previous simple join query. However, if you look at the query metrics now, you will find that after about a couple of minutes of running the query, the size of the state will stabilize as the old buffered events will start getting cleared up.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED*** Outer Joins with Watermarking 
***REMOVED*** MAGIC 
***REMOVED*** MAGIC Let's extend this use case to illustrate outer joins. Not all ad impressions will lead to clicks and you may want to keep track of impressions that did not produce clicks. This can be done by applying a left outer join on the impressions and clicks. The joined output will not have the matched clicks, but also the unmatched ones (with clicks data being NULL).
***REMOVED*** MAGIC 
***REMOVED*** MAGIC While the watermark + event-time constraints is optional for inner joins, for left and right outer joins they must be specified. This is because for generating the NULL results in outer join, the engine must know when an input row is not going to match with anything in future. Hence, the watermark + event-time constraints must be specified for generating correct results. 

***REMOVED*** COMMAND ----------

from pyspark.sql.functions import expr

***REMOVED*** Inner join with time range conditions
display(
  impressionsWithWatermark.join(
    clicksWithWatermark,
    expr(""" 
      clickAdId = impressionAdId AND 
      clickTime >= impressionTime AND 
      clickTime <= impressionTime + interval 1 minutes    
      """
    ),
    "leftOuter"
  )
)

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md After starting this query, you will start getting the inner results within a minute. But after a couple of minutes, you will also start getting the outer NULL results.

***REMOVED*** COMMAND ----------

***REMOVED*** MAGIC %md 
***REMOVED*** MAGIC ***REMOVED******REMOVED******REMOVED*** Further Information
***REMOVED*** MAGIC You can read more about stream-stream joins in the following places:
***REMOVED*** MAGIC 
***REMOVED*** MAGIC - Databricks blog post on stream-stream joins - https://databricks.com/blog/2018/03/13/introducing-stream-stream-joins-in-apache-spark-2-3.html
***REMOVED*** MAGIC - Apache Programming Guide on Structured Streaming - https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html***REMOVED***stream-stream-joins
***REMOVED*** MAGIC - Talk at Spark Summit Europe 2017 - https://databricks.com/session/deep-dive-into-stateful-stream-processing-in-structured-streaming