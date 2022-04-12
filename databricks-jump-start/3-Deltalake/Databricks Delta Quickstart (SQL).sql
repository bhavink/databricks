-- Databricks notebook source
DROP TABLE IF EXISTS events;

-- COMMAND ----------

-- DBTITLE 1,Read Databricks switch action dataset  
CREATE TABLE events
USING delta
PARTITIONED BY (date)
SELECT action, from_unixtime(time, 'yyyy-MM-dd') as date
FROM json.`/databricks-datasets/structured-streaming/events/`;

-- COMMAND ----------

SELECT * FROM events

-- COMMAND ----------

-- DBTITLE 1,Query the table
SELECT count(*) FROM events

-- COMMAND ----------

-- DBTITLE 1,Visualize data
SELECT date, action, count(action) AS action_count FROM events GROUP BY action, date ORDER BY date, action

-- COMMAND ----------

-- DBTITLE 1,Generate historical data - original data shifted backwards 2 days
INSERT INTO events
SELECT action, from_unixtime(time-172800, 'yyyy-MM-dd') as date
FROM json.`/databricks-datasets/structured-streaming/events/`;

-- COMMAND ----------

-- DBTITLE 1,Count rows
SELECT count(*) FROM events

-- COMMAND ----------

-- DBTITLE 1,Visualize final data
SELECT date, action, count(action) AS action_count FROM events GROUP BY action, date ORDER BY date, action

-- COMMAND ----------

DESCRIBE EXTENDED events PARTITION (date='2016-07-25')

-- COMMAND ----------

OPTIMIZE events

-- COMMAND ----------

-- DBTITLE 1,Show table history
DESCRIBE HISTORY events

-- COMMAND ----------

-- DBTITLE 1,Show table details
DESCRIBE DETAIL events

-- COMMAND ----------

-- DBTITLE 1,Show the table format
DESCRIBE FORMATTED events