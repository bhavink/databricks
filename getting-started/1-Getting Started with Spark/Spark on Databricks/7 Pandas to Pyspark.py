***REMOVED*** Databricks notebook source
***REMOVED*** DBTITLE 1,Create a sample csv file
***REMOVED*** Build an example DataFrame dataset to work with.
dbutils.fs.rm("/tmp/dataframe_sample.csv", True)
dbutils.fs.put("/tmp/dataframe_sample.csv", """id|end_date|start_date|location
1|2015-10-14 00:00:00|2015-09-14 00:00:00|CA-SF
2|2015-10-15 01:00:20|2015-08-14 00:00:00|CA-SD
3|2015-10-16 02:30:00|2015-01-14 00:00:00|NY-NY
4|2015-10-17 03:00:20|2015-02-14 00:00:00|NY-NY
5|2015-10-18 04:30:00|2014-04-14 00:00:00|CA-SD
""", True)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Create pandas df from csv
import pandas as pd

pdDF = pd.read_csv("/dbfs/tmp/dataframe_sample.csv", delimiter='|')
pdDF.describe(include = 'all')

***REMOVED*** COMMAND ----------

pdDF.head(5)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Convert pandas dataframe to spark dataframe
sparkDF = spark.createDataFrame(pdDF)
display(sparkDF)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Create spark dataframe reading csv file
df = spark.read.format("csv").options(header='true', delimiter = '|').load("/tmp/dataframe_sample.csv")
display(df.describe())

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Create DataFrames with Python
***REMOVED*** import pyspark class Row from module sql
from pyspark.sql import *

***REMOVED*** Create Example Data - Departments and Employees

***REMOVED*** Create the Departments
department1 = Row(id='123456', name='Computer Science')
department2 = Row(id='789012', name='Mechanical Engineering')
department3 = Row(id='345678', name='Theater and Drama')
department4 = Row(id='901234', name='Indoor Recreation')

***REMOVED*** Create the Employees
Employee = Row("firstName", "lastName", "email", "salary")
employee1 = Employee('michael', 'armbrust', 'no-reply@berkeley.edu', 100000)
employee2 = Employee('xiangrui', 'meng', 'no-reply@stanford.edu', 120000)
employee3 = Employee('matei', None, 'no-reply@waterloo.edu', 140000)
employee4 = Employee(None, 'wendell', 'no-reply@berkeley.edu', 160000)

***REMOVED*** Create the DepartmentWithEmployees instances from Departments and Employees
departmentWithEmployees1 = Row(department=department1, employees=[employee1, employee2])
departmentWithEmployees2 = Row(department=department2, employees=[employee3, employee4])
departmentWithEmployees3 = Row(department=department3, employees=[employee1, employee4])
departmentWithEmployees4 = Row(department=department4, employees=[employee2, employee3])

print department1
print employee2
print departmentWithEmployees1.employees[0].email

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Create DataFrames from a list of the rows
departmentsWithEmployeesSeq1 = [departmentWithEmployees1, departmentWithEmployees2]
df1 = spark.createDataFrame(departmentsWithEmployeesSeq1)

display(df1)

departmentsWithEmployeesSeq2 = [departmentWithEmployees3, departmentWithEmployees4]
df2 = spark.createDataFrame(departmentsWithEmployeesSeq2)

display(df2)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Union two DataFrames
unionDF = df1.unionAll(df2)
display(unionDF)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Write the unioned DataFrame to a Parquet file
***REMOVED*** Remove the file if it exists
dbutils.fs.rm("/tmp/databricks-df-example.parquet", True)
unionDF.write.parquet("/tmp/databricks-df-example.parquet")

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Read a DataFrame from the Parquet file
parquetDF = spark.read.parquet("/tmp/databricks-df-example.parquet")
display(parquetDF)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Explode the employees column
from pyspark.sql.functions import explode

df = parquetDF.select(explode("employees").alias("e"))
explodeDF = df.selectExpr("e.firstName", "e.lastName", "e.email", "e.salary")

display(explodeDF)

***REMOVED*** COMMAND ----------

explodeDF

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Use filter() to return only the rows that match a predicate
filterDF = explodeDF.filter(explodeDF.firstName == "xiangrui").sort(explodeDF.lastName)
display(filterDF)

***REMOVED*** COMMAND ----------

from pyspark.sql.functions import col, asc

***REMOVED*** Use `|` instead of `or`
filterDF = explodeDF.filter((col("firstName") == "xiangrui") | (col("firstName") == "michael")).sort(asc("lastName"))
display(filterDF)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,The where() clause is equivalent to filter()
whereDF = explodeDF.where((col("firstName") == "xiangrui") | (col("firstName") == "michael")).sort(asc("lastName"))
display(whereDF)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Replace null values with -- using DataFrame Na function
nonNullDF = explodeDF.fillna("--")
display(nonNullDF)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Retrieve only rows with missing firstName or lastName
filterNonNullDF = explodeDF.filter(col("firstName").isNull() | col("lastName").isNull()).sort("email")
display(filterNonNullDF)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Example aggregations using agg() and countDistinct()
from pyspark.sql.functions import countDistinct

countDistinctDF = explodeDF.select("firstName", "lastName")\
  .groupBy("firstName", "lastName")\
  .agg(countDistinct("firstName"))

display(countDistinctDF)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Compare the DataFrame and SQL query physical plans
countDistinctDF.explain()

***REMOVED*** COMMAND ----------

***REMOVED*** register the DataFrame as a temp table so that we can query it using SQL
explodeDF.registerTempTable("databricks_df_example")

***REMOVED*** Perform the same query as the DataFrame above and return ``explain``
countDistinctDF_sql = spark.sql("SELECT firstName, lastName, count(distinct firstName) as distinct_first_names FROM databricks_df_example GROUP BY firstName, lastName")

countDistinctDF_sql.explain()

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Sum up all the salaries
salarySumDF = explodeDF.agg({"salary" : "sum"})
display(salarySumDF)

***REMOVED*** COMMAND ----------

type(explodeDF.salary)

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Print the summary statistics for the salaries
explodeDF.describe("salary").show()

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,An example using pandas and Matplotlib integration
import pandas as pd
import matplotlib.pyplot as plt
plt.clf()
pdDF = nonNullDF.toPandas()
pdDF.plot(x='firstName', y='salary', kind='bar', rot=45)
display()

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Cleanup: remove the Parquet file
dbutils.fs.rm("/tmp/databricks-df-example.parquet", True)