-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Databricks in 5 minutes

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Create a quickstart cluster
-- MAGIC 
-- MAGIC 1. In the sidebar, right-click the **Clusters** button and open the link in a new window.
-- MAGIC 1. On the Clusters page, click **Create Cluster**.
-- MAGIC 1. Name the cluster **Quickstart**.
-- MAGIC 1. In the Databricks Runtime Version drop-down, select **5.2 (Scala 11, Spark 2.4.0)**.
-- MAGIC 1. Click **Create Cluster**.
-- MAGIC 
-- MAGIC <img src="http://docs.databricks.com/_static/images/getting-started/quickstart-cluster.png"/></a>

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Attach the notebook to the cluster and run all commands in the notebook
-- MAGIC 
-- MAGIC 1. Return to this notebook. 
-- MAGIC 1. In the notebook menu bar, select **<img src="http://docs.databricks.com/_static/images/notebooks/detached.png"/></a> > Quickstart**.
-- MAGIC 1. When the cluster changes from <img src="http://docs.databricks.com/_static/images/clusters/cluster-starting.png"/></a> to <img src="http://docs.databricks.com/_static/images/clusters/cluster-running.png"/></a>, click **<img src="http://docs.databricks.com/_static/images/notebooks/run-all.png"/></a> Run All**.

-- COMMAND ----------

-- MAGIC %md 
-- MAGIC ## The next command creates a table from a Databricks dataset

-- COMMAND ----------

DROP TABLE IF EXISTS diamonds;

CREATE TABLE diamonds
USING csv
OPTIONS (path "/databricks-datasets/Rdatasets/data-001/csv/ggplot2/diamonds.csv", header "true")


-- COMMAND ----------

SELECT * from diamonds

-- COMMAND ----------

-- MAGIC %python
-- MAGIC diamonds = spark.read.csv("/databricks-datasets/Rdatasets/data-001/csv/ggplot2/diamonds.csv", header="true", inferSchema="true")
-- MAGIC diamonds.write.format("delta").save("/delta/diamonds")

-- COMMAND ----------

DROP TABLE IF EXISTS diamonds;

CREATE TABLE diamonds USING DELTA LOCATION '/delta/diamonds/'

-- COMMAND ----------

SELECT * from diamonds

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## The next command manipulates the data and displays the results 
-- MAGIC 
-- MAGIC Specifically, the command:
-- MAGIC 1. Selects color and price columns, averages the price, and groups and orders by color.
-- MAGIC 1. Displays a table of the results.

-- COMMAND ----------

SELECT color, avg(price) AS price FROM diamonds GROUP BY color ORDER BY color

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Convert the table to a chart
-- MAGIC 
-- MAGIC Under the table, click the bar chart <img src="http://docs.databricks.com/_static/images/notebooks/chart-button.png"/></a> icon. 

-- COMMAND ----------

-- MAGIC %md 
-- MAGIC ## Repeat the same operations using Python DataFrame API. 
-- MAGIC This is a SQL notebook; by default command statements are passed to a SQL interpreter. To pass command statements to a Python interpreter, include the `%python` magic command.

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## The next command creates a DataFrame from a Databricks dataset

-- COMMAND ----------

-- MAGIC %python
-- MAGIC diamonds = spark.read.csv("/databricks-datasets/Rdatasets/data-001/csv/ggplot2/diamonds.csv", header="true", inferSchema="true")

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## The next command manipulates the data and displays the results

-- COMMAND ----------

-- MAGIC %python
-- MAGIC from pyspark.sql.functions import avg
-- MAGIC 
-- MAGIC display(diamonds.select("color","price").groupBy("color").agg(avg("price")).sort("color"))