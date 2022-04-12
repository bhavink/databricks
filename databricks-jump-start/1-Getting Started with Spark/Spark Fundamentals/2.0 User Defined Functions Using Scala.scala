// Databricks notebook source
// DBTITLE 1,Register a function as a UDF
val squared = (s: Long) => {
  s * s
}
spark.udf.register("square", squared)

// COMMAND ----------

// DBTITLE 1,Call UDF
spark.range(1, 20).createOrReplaceTempView("test")

// COMMAND ----------

// MAGIC %sql select id, square(id) as id_squared from test

// COMMAND ----------

// DBTITLE 1,Use with DataFrame
import org.apache.spark.sql.functions.{col, udf}
val squared = udf((s: Long) => s * s)
display(spark.range(1, 20).select(squared(col("id")) as "id_squared"))

// COMMAND ----------

spark.udf.register("strlen", (s: String) => s.length)
val df = spark.sql("select id from test where id is not null and strlen(id) > 1")

// COMMAND ----------

display(df)

// COMMAND ----------

// To perform proper null checking, we recommend that you do either of the following:

// Make the UDF itself null-aware and do null checking inside the UDF itself
// Use IF or CASE WHEN expressions to do the null check and invoke the UDF in a conditional branch

spark.udf.register("strlen_nullsafe", (s: String) => if (s != null) s.length else -1)
val df1 = spark.sql("select id from test where id is not null and strlen_nullsafe(id) > 1") // ok
val df2 = spark.sql("select id from test where if(id is not null, strlen(id), null) > 1")   // ok

// COMMAND ----------

display(df1)

// COMMAND ----------

display(df2)

// COMMAND ----------

