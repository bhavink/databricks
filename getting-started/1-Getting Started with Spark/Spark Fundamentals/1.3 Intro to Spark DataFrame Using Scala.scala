// Databricks notebook source
// DBTITLE 1,Create DataFrames
// Create the case classes for our domain
case class Department(id: String, name: String)
case class Employee(firstName: String, lastName: String, email: String, salary: Int)
case class DepartmentWithEmployees(department: Department, employees: Seq[Employee])

// Create the Departments
val department1 = new Department("123456", "Computer Science")
val department2 = new Department("789012", "Mechanical Engineering")
val department3 = new Department("345678", "Theater and Drama")
val department4 = new Department("901234", "Indoor Recreation")

// Create the Employees
val employee1 = new Employee("michael", "armbrust", "no-reply@berkeley.edu", 100000)
val employee2 = new Employee("xiangrui", "meng", "no-reply@stanford.edu", 120000)
val employee3 = new Employee("matei", null, "no-reply@waterloo.edu", 140000)
val employee4 = new Employee(null, "wendell", "no-reply@princeton.edu", 160000)
val employee5 = new Employee("michael", "jackson", "no-reply@neverla.nd", 80000)

// Create the DepartmentWithEmployees instances from Departments and Employees
val departmentWithEmployees1 = new DepartmentWithEmployees(department1, Seq(employee1, employee2))
val departmentWithEmployees2 = new DepartmentWithEmployees(department2, Seq(employee3, employee4))
val departmentWithEmployees3 = new DepartmentWithEmployees(department3, Seq(employee5, employee4))
val departmentWithEmployees4 = new DepartmentWithEmployees(department4, Seq(employee2, employee3))

// COMMAND ----------

// DBTITLE 1,Create DataFrames from a list of the case classes
val departmentsWithEmployeesSeq1 = Seq(departmentWithEmployees1, departmentWithEmployees2)
val df1 = departmentsWithEmployeesSeq1.toDF()
display(df1)

val departmentsWithEmployeesSeq2 = Seq(departmentWithEmployees3, departmentWithEmployees4)
val df2 = departmentsWithEmployeesSeq2.toDF()
display(df2)

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** Working with DataFrames

// COMMAND ----------

// DBTITLE 1,Union two DataFrames
val unionDF = df1.union(df2)
display(unionDF)

// COMMAND ----------

// DBTITLE 1,Write the unioned DataFrame to a Parquet file
// Remove the file if it exists
dbutils.fs.rm("/tmp/databricks-df-example.parquet", true)
unionDF.write.parquet("/tmp/databricks-df-example.parquet")

// COMMAND ----------

// DBTITLE 1,Read a DataFrame from the Parquet file
val parquetDF = spark.read.parquet("/tmp/databricks-df-example.parquet")

// COMMAND ----------

// DBTITLE 1,Explode the employees column
// https://spark.apache.org/docs/latest/api/scala/index.html***REMOVED***org.apache.spark.sql.functions$

import org.apache.spark.sql.functions._

val explodeDF = parquetDF.select(explode($"employees"))
display(explodeDF)

// COMMAND ----------

// DBTITLE 1,Flatten the fields of the employee class into columns
val flattenDF = explodeDF.select($"col.*")
flattenDF.show()

// COMMAND ----------

// DBTITLE 1,Use filter() to return the rows that match a predicate
val filterDF = flattenDF
  .filter($"firstName" === "xiangrui" || $"firstName" === "michael")
  .sort($"lastName".asc)
display(filterDF)

// COMMAND ----------

// DBTITLE 1,The where() clause is equivalent to filter()
val whereDF = flattenDF
  .where($"firstName" === "xiangrui" || $"firstName" === "michael")
  .sort($"lastName".asc)
display(whereDF)

// COMMAND ----------

// DBTITLE 1,Replace null values with -- using DataFrame Na function
val nonNullDF = flattenDF.na.fill("--")
display(nonNullDF)

// COMMAND ----------

// DBTITLE 1,Retrieve rows with missing firstName or lastName
val filterNonNullDF = nonNullDF.filter($"firstName" === "--" || $"lastName" === "--").sort($"email".asc)
display(filterNonNullDF)

// COMMAND ----------

// DBTITLE 1,Example aggregations using agg() and countDistinct()
// Find the distinct last names for each first name
val countDistinctDF = nonNullDF.select($"firstName", $"lastName")
  .groupBy($"firstName")
  .agg(countDistinct($"lastName") as "distinct_last_names")
display(countDistinctDF)

// COMMAND ----------

// DBTITLE 1,Compare the DataFrame and SQL query physical plans
countDistinctDF.explain()

// COMMAND ----------

// register the DataFrame as a temp view so that we can query it using SQL
nonNullDF.createOrReplaceTempView("databricks_df_example")

spark.sql("""
  SELECT firstName, count(distinct lastName) as distinct_last_names
  FROM databricks_df_example
  GROUP BY firstName
""").explain

// COMMAND ----------

// DBTITLE 1,Sum up all the salaries
val salarySumDF = nonNullDF.agg("salary" -> "sum")
display(salarySumDF)

// COMMAND ----------

// DBTITLE 1,Print the summary statistics for the salaries
nonNullDF.describe("salary").show()

// COMMAND ----------

// DBTITLE 1,Cleanup: remove the Parquet file
dbutils.fs.rm("/tmp/databricks-df-example.parquet", true)

// COMMAND ----------

// DBTITLE 1,How can I get better performance with DataFrame UDFs?
// If the functionality exists in the available built-in functions, using these will perform better.

// We use the built-in functions and the withColumn() API to add new columns. 
// We could have also used withColumnRenamed() to replace an existing column after the transformation.

import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.sql._
import org.apache.hadoop.io.LongWritable
import org.apache.hadoop.io.Text
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.mapreduce.lib.input.TextInputFormat

// Build an example DataFrame dataset to work with.
dbutils.fs.rm("/tmp/dataframe_sample.csv", true)
dbutils.fs.put("/tmp/dataframe_sample.csv", """
id|end_date|start_date|location
1|2015-10-14 00:00:00|2015-09-14 00:00:00|CA-SF
2|2015-10-15 01:00:20|2015-08-14 00:00:00|CA-SD
3|2015-10-16 02:30:00|2015-01-14 00:00:00|NY-NY
4|2015-10-17 03:00:20|2015-02-14 00:00:00|NY-NY
5|2015-10-18 04:30:00|2014-04-14 00:00:00|CA-LA
""", true)

val conf = new Configuration
conf.set("textinputformat.record.delimiter", "\n")
val rdd = sc.newAPIHadoopFile("/tmp/dataframe_sample.csv", classOf[TextInputFormat], classOf[LongWritable], classOf[Text], conf).map(_._2.toString).filter(_.nonEmpty)

val header = rdd.first()
// Parse the header line
val rdd_noheader = rdd.filter(x => !x.contains("id"))
// Convert the RDD[String] to an RDD[Rows]. Create an array using the delimiter and use Row.fromSeq()
val row_rdd = rdd_noheader.map(x => x.split('|')).map(x => Row.fromSeq(x))

val df_schema =
  StructType(
    header.split('|').map(fieldName => StructField(fieldName, StringType, true)))

var df = spark.createDataFrame(row_rdd, df_schema)
df.printSchema

// COMMAND ----------

// Instead of registering a UDF, call the builtin functions to perform operations on the columns.
// This will provide a performance improvement as the builtins compile and run in the platform's JVM.

// Convert to a Date type
val timestamp2datetype: (Column) => Column = (x) => { to_date(x) }
df = df.withColumn("date", timestamp2datetype(col("end_date")))

// Parse out the date only
val timestamp2date: (Column) => Column = (x) => { regexp_replace(x," (\\d+)[:](\\d+)[:](\\d+).*$", "") }
df = df.withColumn("date_only", timestamp2date(col("end_date")))

// Split a string and index a field
val parse_city: (Column) => Column = (x) => { split(x, "-")(1) }
df = df.withColumn("city", parse_city(col("location")))

// Perform a date diff function
val dateDiff: (Column, Column) => Column = (x, y) => { datediff(to_date(y), to_date(x)) }
df = df.withColumn("date_diff", dateDiff(col("start_date"), col("end_date")))

// COMMAND ----------

df.registerTempTable("sample_df")
display(sql("select * from sample_df"))

// COMMAND ----------

// DBTITLE 1,I want to convert the DataFrame back to JSON strings to send back to Kafka.
val rdd_json = df.toJSON
rdd_json.take(2).foreach(println)

// COMMAND ----------

// DBTITLE 1,My UDF takes a parameter including the column to operate on. How do I pass this parameter?
// There is a function available called lit() that creates a static column.

val add_n = udf((x: Integer, y: Integer) => x + y)

// We register a UDF that adds a column to the DataFrame, and we cast the id column to an Integer type.
df = df.withColumn("id_offset", add_n(lit(1000), col("id").cast("int")))
display(df)

// COMMAND ----------

val last_n_days = udf((x: Integer, y: Integer) => {
  if (x < y) true else false
})

//last_n_days = udf(lambda x, y: True if x < y else False, BooleanType())

val df_filtered = df.filter(last_n_days(col("date_diff"), lit(90)))
display(df_filtered)

// COMMAND ----------

// DBTITLE 1,I have a table in the Hive metastore and I’d like to access to table as a DataFrame.
// There are multiple ways to define a DataFrame from a registered table. 
// Syntax show below. Call table(tableName) or select and filter specific columns using an SQL query.

// Both return DataFrame types
val df_1 = table("sample_df")
val df_2 = spark.sql("select * from sample_df")

// COMMAND ----------

// DBTITLE 1,I’d like to clear all the cached tables on the current cluster.
// There’s an API available to do this at the global or per table level.

sqlContext.clearCache()
sqlContext.cacheTable("sample_df")
sqlContext.uncacheTable("sample_df")

// COMMAND ----------

// DBTITLE 1,I’d like to compute aggregates on columns. What’s the best way to do this?
// There’s an API named agg(*exprs) that takes a list of column names and expressions for the type of aggregation you’d like to compute. 
// You can leverage the built-in functions mentioned above as part of the expressions for each column.

// Provide the min, count, and avg and groupBy the location column. Diplay the results
var agg_df = df.groupBy("location").agg(min("id"), count("id"), avg("date_diff"))
display(agg_df)

// COMMAND ----------

// DBTITLE 1,I’d like to write out the DataFrames to Parquet, but would like to partition on a particular column.
// You can use the following APIs to accomplish this. 
// Ensure the code does not create a large number of partitioned columns with the datasets otherwise the overhead of the metadata can cause significant slow downs. 
// If there is a SQL table back by this directory, you will need to call refresh table <table-name> to update the metadata prior to the query.

df = df.withColumn("end_month", month(col("end_date")))
df = df.withColumn("end_year", year(col("end_date")))
dbutils.fs.rm("/tmp/sample_table", true)
df.write.partitionBy("end_year", "end_month").parquet("/tmp/sample_table")
display(dbutils.fs.ls("/tmp/sample_table"))

// COMMAND ----------

// DBTITLE 1,How do I properly handle cases where I want to filter out NULL data?
val null_item_schema = StructType(Array(StructField("col1", StringType, true),
                               StructField("col2", IntegerType, true)))

val null_dataset = sc.parallelize(Array(("test", 1 ), (null, 2))).map(x => Row.fromTuple(x))
val null_df = spark.createDataFrame(null_dataset, null_item_schema)
display(null_df.filter("col1 IS NOT NULL"))

// COMMAND ----------

// DBTITLE 1,How do I infer the schema using the csv or spark-avro libraries?
val adult_df = spark.read.
    format("csv").
    option("header", "true").
    option("inferSchema", "true").load("dbfs:/databricks-datasets/adult/adult.data")
adult_df.printSchema()

// COMMAND ----------

