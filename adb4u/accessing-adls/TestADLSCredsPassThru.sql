-- Databricks notebook source
CREATE or REPLACE TEMPORARY VIEW chickmenu1
USING csv 
OPTIONS (
  path 'abfss://container@labsdatalake.dfs.core.windows.net/readonly/chick_menu.csv',
  header true
);

select * from chickmenu1;

-- COMMAND ----------

-- MAGIC %python
-- MAGIC dbutils.fs.refreshMounts()

-- COMMAND ----------

CREATE or REPLACE TEMPORARY VIEW chickmenu2
USING csv 
OPTIONS (
  path '/mnt/labsdatalake/container/listonly/chick_menu.csv',
  header true
);

select * from chickmenu2;

-- COMMAND ----------

select * from csv.`abfss://container@labsdatalake.dfs.core.windows.net/readonly/chick_menu.csv`

-- COMMAND ----------

-- MAGIC %python
-- MAGIC df = spark.read.format('csv')\
-- MAGIC     .options(header='true')\
-- MAGIC     .load('abfss://container@labsdatalake.dfs.core.windows.net/readonly/chick_menu.csv')
-- MAGIC display(df)

-- COMMAND ----------

-- MAGIC %md
-- MAGIC 
-- MAGIC ### ADB with an [egress appliance](https://databricks.com/blog/2020/03/27/data-exfiltration-protection-with-azure-databricks.html) and ADLS access
-- MAGIC 
-- MAGIC #### If you have a firewall in front of ADB then the access pattern would like this:
-- MAGIC 
-- MAGIC   -  AAD Servcie endpoint enabled on ADB subnets
-- MAGIC   -  Storage service endpoint disabled on ADB subnets (yes you have to disable service endpoint)
-- MAGIC   -  Storage service endpoint enabled on subnet hosting firewall
-- MAGIC   -  Firewall subnet whitelisted on ADLS Gen2 --> Netowrking --> Firewall and Virtual Networks --> Selected Networks
-- MAGIC   -  As the firewall, ADB and ADLS are on Azure, traffic will stay on Azure backbone.
