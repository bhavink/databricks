# Databricks notebook source
# DBTITLE 1,Register a function as a UDF
def squared(s):
  return s * s
spark.udf.register("squaredWithPython", squared)

# COMMAND ----------

from pyspark.sql.types import LongType
def squared_typed(s):
  return s * s
spark.udf.register("squaredWithPython", squared_typed, LongType())

# COMMAND ----------

# DBTITLE 1,Call the UDF in Spark SQL
spark.range(1, 20).registerTempTable("test")

# COMMAND ----------

# MAGIC %sql 
# MAGIC select id, squaredWithPython(id) as id_squared from test

# COMMAND ----------

# DBTITLE 1,Use UDF with DataFrames
from pyspark.sql.functions import udf
from pyspark.sql.types import LongType
squared_udf = udf(squared, LongType())
df = spark.table("test")
display(df.select("id", squared_udf("id").alias("id_squared")))

# COMMAND ----------

# DBTITLE 1,Alternatively, you can declare the same UDF using annotation syntax:
from pyspark.sql.functions import udf
@udf("long")
def squared_udf(s):
  return s * s
df = spark.table("test")
display(df.select("id", squared_udf("id").alias("id_squared")))

# COMMAND ----------

