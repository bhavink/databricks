# Databricks notebook source
# DBTITLE 1,Create DataFrames
# import pyspark class Row from module sql
from pyspark.sql import *

# Create Example Data - Departments and Employees

# Create the Departments
department1 = Row(id='123456', name='Computer Science')
department2 = Row(id='789012', name='Mechanical Engineering')
department3 = Row(id='345678', name='Theater and Drama')
department4 = Row(id='901234', name='Indoor Recreation')

# Create the Employees
Employee = Row("firstName", "lastName", "email", "salary")
employee1 = Employee('michael', 'armbrust', 'no-reply@berkeley.edu', 100000)
employee2 = Employee('xiangrui', 'meng', 'no-reply@stanford.edu', 120000)
employee3 = Employee('matei', None, 'no-reply@waterloo.edu', 140000)
employee4 = Employee(None, 'wendell', 'no-reply@berkeley.edu', 160000)
employee5 = Employee('michael', 'jackson', 'no-reply@neverla.nd', 80000)

# Create the DepartmentWithEmployees instances from Departments and Employees
departmentWithEmployees1 = Row(department=department1, employees=[employee1, employee2])
departmentWithEmployees2 = Row(department=department2, employees=[employee3, employee4])
departmentWithEmployees3 = Row(department=department3, employees=[employee5, employee4])
departmentWithEmployees4 = Row(department=department4, employees=[employee2, employee3])

print(department1)
print(employee2)
print(departmentWithEmployees1.employees[0].email)

# COMMAND ----------

# DBTITLE 1,Create DataFrames from a list of the rows
departmentsWithEmployeesSeq1 = [departmentWithEmployees1, departmentWithEmployees2]
df1 = spark.createDataFrame(departmentsWithEmployeesSeq1)

display(df1)

departmentsWithEmployeesSeq2 = [departmentWithEmployees3, departmentWithEmployees4]
df2 = spark.createDataFrame(departmentsWithEmployeesSeq2)

display(df2)

# COMMAND ----------

# DBTITLE 1,Union two DataFrames
unionDF = df1.union(df2)
display(unionDF)

# COMMAND ----------

# DBTITLE 1,Write the unioned DataFrame to a Parquet file
# Remove the file if it exists
dbutils.fs.rm("/tmp/databricks-df-example.parquet", True)
unionDF.write.parquet("/tmp/databricks-df-example.parquet")

# COMMAND ----------

# DBTITLE 1,Read a DataFrame from the Parquet file
parquetDF = spark.read.parquet("/tmp/databricks-df-example.parquet")
display(parquetDF)

# COMMAND ----------

# DBTITLE 1,Explode the employees column
#https://spark.apache.org/docs/latest/api/python/_modules/pyspark/sql/functions.html#explode

from pyspark.sql.functions import explode

explodeDF = unionDF.select(explode("employees").alias("e"))
flattenDF = explodeDF.selectExpr("e.firstName", "e.lastName", "e.email", "e.salary")

flattenDF.show()

# COMMAND ----------

# DBTITLE 1,Use filter() to return the rows that match a predicate
filterDF = flattenDF.filter(flattenDF.firstName == "xiangrui").sort(flattenDF.lastName)
display(filterDF)

# COMMAND ----------

from pyspark.sql.functions import col, asc

# Use `|` instead of `or`
filterDF = flattenDF.filter((col("firstName") == "xiangrui") | (col("firstName") == "michael")).sort(asc("lastName"))
display(filterDF)

# COMMAND ----------

# DBTITLE 1,The where() clause is equivalent to filter()
whereDF = flattenDF.where((col("firstName") == "xiangrui") | (col("firstName") == "michael")).sort(asc("lastName"))
display(whereDF)

# COMMAND ----------

# DBTITLE 1,Replace null values with -- using DataFrame Na function
nonNullDF = flattenDF.fillna("--")
display(nonNullDF)

# COMMAND ----------

# DBTITLE 1,Retrieve only rows with missing firstName or lastName
filterNonNullDF = flattenDF.filter(col("firstName").isNull() | col("lastName").isNull()).sort("email")
display(filterNonNullDF)

# COMMAND ----------

# DBTITLE 1,Example aggregations using agg() and countDistinct()
from pyspark.sql.functions import countDistinct

countDistinctDF = nonNullDF.select("firstName", "lastName")\
  .groupBy("firstName")\
  .agg(countDistinct("lastName").alias("distinct_last_names"))

display(countDistinctDF)

# COMMAND ----------

# DBTITLE 1,Compare the DataFrame and SQL query physical plans
countDistinctDF.explain()

# COMMAND ----------

# register the DataFrame as a temp table so that we can query it using SQL
nonNullDF.createOrReplaceTempView("databricks_df_example")

# Perform the same query as the DataFrame above and return ``explain``
countDistinctDF_sql = spark.sql('''
  SELECT firstName, count(distinct lastName) AS distinct_last_names
  FROM databricks_df_example
  GROUP BY firstName
''')

countDistinctDF_sql.explain()

# COMMAND ----------

# DBTITLE 1,Sum up all the salaries
salarySumDF = nonNullDF.agg({"salary" : "sum"})
display(salarySumDF)

# COMMAND ----------

type(nonNullDF.salary)

# COMMAND ----------

# DBTITLE 1,Print the summary statistics for the salaries
nonNullDF.describe("salary").show()

# COMMAND ----------

# DBTITLE 1,An example using pandas and Matplotlib integration
import pandas as pd
import matplotlib.pyplot as plt
plt.clf()
pdDF = nonNullDF.toPandas()
pdDF.plot(x='firstName', y='salary', kind='bar', rot=45)
display()

# COMMAND ----------

# DBTITLE 1,Cleanup: remove the Parquet file
dbutils.fs.rm("/tmp/databricks-df-example.parquet", True)

# COMMAND ----------

# DBTITLE 1,How can I get better performance with DataFrame UDFs?
# PySpark documentation - https://spark.apache.org/docs/latest/api/python/pyspark.sql.html#pyspark.sql.DataFrame
# How can I get better performance with DataFrame UDFs?

# If the functionality exists in the available built-in functions, using these will perform better. 
# Example usage below. Also see the pyspark.sql.function documentation. We use the built-in functions and the withColumn() API to add new columns. 
# We could have also used withColumnRenamed() to replace an existing column after the transformation.

from pyspark.sql import functions as F
from pyspark.sql.types import *

# Build an example DataFrame dataset to work with.
dbutils.fs.rm("/tmp/dataframe_sample.csv", True)
dbutils.fs.put("/tmp/dataframe_sample.csv", """id|end_date|start_date|location
1|2015-10-14 00:00:00|2015-09-14 00:00:00|CA-SF
2|2015-10-15 01:00:20|2015-08-14 00:00:00|CA-SD
3|2015-10-16 02:30:00|2015-01-14 00:00:00|NY-NY
4|2015-10-17 03:00:20|2015-02-14 00:00:00|NY-NY
5|2015-10-18 04:30:00|2014-04-14 00:00:00|CA-SD
""", True)

df = spark.read.format("csv").options(header='true', delimiter = '|').load("/tmp/dataframe_sample.csv")
df.printSchema()


# COMMAND ----------

# Instead of registering a UDF, call the builtin functions to perform operations on the columns.
# This will provide a performance improvement as the builtins compile and run in the platform's JVM.

# Convert to a Date type
df = df.withColumn('date', F.to_date(df.end_date))

# Parse out the date only
df = df.withColumn('date_only', F.regexp_replace(df.end_date,' (\d+)[:](\d+)[:](\d+).*$', ''))

# Split a string and index a field
df = df.withColumn('city', F.split(df.location, '-')[1])

# Perform a date diff function
df = df.withColumn('date_diff', F.datediff(F.to_date(df.end_date), F.to_date(df.start_date)))

# COMMAND ----------

df.registerTempTable("sample_df")
display(sql("select * from sample_df"))

# COMMAND ----------

# DBTITLE 1,I want to convert the DataFrame back to JSON strings to send back to Kafka.
# There is an underlying toJSON() function that returns an RDD of JSON strings using the column names and schema to produce the JSON records.

rdd_json = df.toJSON()
rdd_json.take(2)

# COMMAND ----------

# DBTITLE 1,My UDF takes a parameter including the column to operate on. How do I pass this parameter?
# There is a function available called lit() that creates a constant column.
from pyspark.sql import functions as F

add_n = udf(lambda x, y: x + y, IntegerType())

# We register a UDF that adds a column to the DataFrame, and we cast the id column to an Integer type.
df = df.withColumn('id_offset', add_n(F.lit(1000), df.id.cast(IntegerType())))
display(df)

# COMMAND ----------

# any constants used by UDF will automatically pass through to workers
N = 90
last_n_days = udf(lambda x: x < N, BooleanType())

df_filtered = df.filter(last_n_days(df.date_diff))
display(df_filtered)

# COMMAND ----------

# DBTITLE 1,I have a table in the Hive metastore and I’d like to access to table as a DataFrame.
# There are multiple ways to define a DataFrame from a registered table. Syntax show below. 
# Call table(tableName) or select and filter specific columns using an SQL query.

# Both return DataFrame types
df_1 = table("sample_df")
df_2 = spark.sql("select * from sample_df")


# COMMAND ----------

# DBTITLE 1,I’d like to clear all the cached tables on the current cluster.
sqlContext.clearCache()
sqlContext.cacheTable("sample_df")
sqlContext.uncacheTable("sample_df")

# COMMAND ----------

# DBTITLE 1,I’d like to compute aggregates on columns. What’s the best way to do this?
# There’s an API named agg(*exprs) that takes a list of column names and expressions for the type of aggregation you’d like to compute. 
# You can leverage the built-in functions that mentioned above as part of the expressions for each column.

# Provide the min, count, and avg and groupBy the location column. Diplay the results
agg_df = df.groupBy("location").agg(F.min("id"), F.count("id"), F.avg("date_diff"))
display(agg_df)

# COMMAND ----------

# DBTITLE 1,I’d like to write out the DataFrames to Parquet, but would like to partition on a particular column.
# You can use the following APIs to accomplish this. 
# Ensure the code does not create a large number of partition columns with the datasets otherwise the overhead of the metadata can cause significant slow downs. 
# If there is a SQL table back by this directory, you will need to call refresh table <table-name> to update the metadata prior to the query.

df = df.withColumn('end_month', F.month('end_date'))
df = df.withColumn('end_year', F.year('end_date'))
df.write.partitionBy("end_year", "end_month").parquet("/tmp/sample_table")
display(dbutils.fs.ls("/tmp/sample_table"))

# COMMAND ----------

# DBTITLE 1,How do I properly handle cases where I want to filter out NULL data?
null_item_schema = StructType([StructField("col1", StringType(), True),
                               StructField("col2", IntegerType(), True)])
null_df = spark.createDataFrame([("test", 1), (None, 2)], null_item_schema)
display(null_df.filter("col1 IS NOT NULL"))

# COMMAND ----------

