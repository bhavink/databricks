// Databricks notebook source
// MAGIC %md
// MAGIC 
// MAGIC ### This is based on excellent work done by one of our lead instructor Brian Clapper.
// MAGIC ### Source code along with details instructions is located over here https://github.com/bmc/spark-hive-udf/

// COMMAND ----------

// testing az devops

// COMMAND ----------

//register hive udf
spark.sql("CREATE TEMPORARY FUNCTION toHex AS 'com.ardentex.spark.hiveudf.ToHex'");
spark.sql("CREATE TEMPORARY FUNCTION datestring AS 'com.ardentex.spark.hiveudf.FormatTimestamp'");
spark.sql("CREATE TEMPORARY FUNCTION currency AS 'com.ardentex.spark.hiveudf.FormatCurrency'");


// COMMAND ----------

import java.sql.Timestamp
import java.text.SimpleDateFormat
import java.util.Date

case class Person(firstName: String, lastName: String, birthDate: Timestamp, salary: Double, children: Int)

val fmt = new SimpleDateFormat("yyyy-MM-dd")

val people = Array(
    Person("Joe", "Smith", new Timestamp(fmt.parse("1993-10-20").getTime), 70000.0, 2),
    Person("Jenny", "Harmon", new Timestamp(fmt.parse("1987-08-02").getTime), 94000.0, 1)
)

val df = spark.createDataFrame(spark.sparkContext.parallelize(people))

df.createOrReplaceTempView("people")
val df2 = spark.sql("SELECT firstName, lastName, birthDate, datestring(birthDate, 'MMMM dd, yyyy') as birthDateFromUDF, salary, currency(salary, 'en_US') as salaryFromUDF, Children, toHex(children) as ChildrenFromUDF FROM people")

display(df2)

// COMMAND ----------

// MAGIC %python
// MAGIC 
// MAGIC spark.sql("CREATE TEMPORARY FUNCTION to_hex AS 'com.ardentex.spark.hiveudf.ToHex'");
// MAGIC spark.sql("CREATE TEMPORARY FUNCTION datestring AS 'com.ardentex.spark.hiveudf.FormatTimestamp'");
// MAGIC spark.sql("CREATE TEMPORARY FUNCTION currency AS 'com.ardentex.spark.hiveudf.FormatCurrency'");

// COMMAND ----------

// MAGIC %python
// MAGIC 
// MAGIC from datetime import datetime
// MAGIC from collections import namedtuple
// MAGIC from decimal import Decimal
// MAGIC 
// MAGIC Person = namedtuple('Person', ('first_name', 'last_name', 'birth_date', 'salary', 'children'))
// MAGIC 
// MAGIC fmt = "%Y-%m-%d"
// MAGIC 
// MAGIC people = [
// MAGIC     Person('Joe', 'Smith', datetime.strptime("1993-10-20", fmt), 70000.0, 2),
// MAGIC     Person('Jenny', 'Harmon', datetime.strptime("1987-08-02", fmt), 94000.0, 1)
// MAGIC ]
// MAGIC 
// MAGIC df = spark.sparkContext.parallelize(people).toDF()
// MAGIC 
// MAGIC df.createOrReplaceTempView("people")
// MAGIC df2 = spark.sql("SELECT first_name, last_name, datestring(birth_date, 'MMMM dd, yyyy') as birth_date, currency(salary, 'en_US') as salary, to_hex(children) as hex_children FROM people")
// MAGIC 
// MAGIC display(df2)