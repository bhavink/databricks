// Databricks notebook source
// DBTITLE 1,Implement the UserDefinedAggregateFunction
import org.apache.spark.sql.expressions.MutableAggregationBuffer
import org.apache.spark.sql.expressions.UserDefinedAggregateFunction
import org.apache.spark.sql.Row
import org.apache.spark.sql.types._

class GeometricMean extends UserDefinedAggregateFunction {
  // This is the input fields for your aggregate function.
  override def inputSchema: org.apache.spark.sql.types.StructType =
    StructType(StructField("value", DoubleType) :: Nil)

  // This is the internal fields you keep for computing your aggregate.
  override def bufferSchema: StructType = StructType(
    StructField("count", LongType) ::
    StructField("product", DoubleType) :: Nil
  )

  // This is the output type of your aggregatation function.
  override def dataType: DataType = DoubleType

  override def deterministic: Boolean = true

  // This is the initial value for your buffer schema.
  override def initialize(buffer: MutableAggregationBuffer): Unit = {
    buffer(0) = 0L
    buffer(1) = 1.0
  }

  // This is how to update your buffer schema given an input.
  override def update(buffer: MutableAggregationBuffer, input: Row): Unit = {
    buffer(0) = buffer.getAs[Long](0) + 1
    buffer(1) = buffer.getAs[Double](1) * input.getAs[Double](0)
  }

  // This is how to merge two objects with the bufferSchema type.
  override def merge(buffer1: MutableAggregationBuffer, buffer2: Row): Unit = {
    buffer1(0) = buffer1.getAs[Long](0) + buffer2.getAs[Long](0)
    buffer1(1) = buffer1.getAs[Double](1) * buffer2.getAs[Double](1)
  }

  // This is where you output the final value, given the final value of your bufferSchema.
  override def evaluate(buffer: Row): Any = {
    math.pow(buffer.getDouble(1), 1.toDouble / buffer.getLong(0))
  }
}

// COMMAND ----------

// DBTITLE 1,Register the UDAF with Spark SQL
spark.udf.register("gm", new GeometricMean)

// COMMAND ----------

// DBTITLE 1,Use your UDAF
// Create a DataFrame and Spark SQL table
import org.apache.spark.sql.functions._

val ids = spark.range(1, 20)
ids.createOrReplaceTempView("ids")
val df = spark.sql("select id, id % 3 as group_id from ids")
df.createOrReplaceTempView("simple")

// COMMAND ----------

// MAGIC %sql
// MAGIC 
// MAGIC -- Use a group_by statement and call the UDAF.
// MAGIC select group_id, gm(id) from simple group by group_id

// COMMAND ----------

// Or use DataFrame syntax to call the aggregate function.

// Create an instance of UDAF GeometricMean.
val gm = new GeometricMean

// Show the geometric mean of values of column "id".
df.groupBy("group_id").agg(gm(col("id")).as("GeometricMean")).show()

// Invoke the UDAF by its assigned name.
df.groupBy("group_id").agg(expr("gm(id) as GeometricMean")).show()

// COMMAND ----------

