// Databricks notebook source
// MAGIC %md Aggregators provide a mechanism for adding up all of the elements in a DataSet (or in each group of a GroupedDataset), returning a single result.  An `Aggregator` is similar to a UDAF, but the interface is expressed in terms of JVM objects instead of as a `Row`.  Any class that extends `Aggregator[A, B, C]` can be used, where:
// MAGIC  - `A` - specifies the input type to the aggregator
// MAGIC  - `B` - specifies the intermediate type during aggregation
// MAGIC  - `C` - specifies the final type output by the aggregation
// MAGIC  
// MAGIC Before using an `Aggregator` in a `Dataset` operation, you must call `toColumn`, passing any encoders that can't be infered automatically by the compiler.

// COMMAND ----------

import org.apache.spark.sql.functions._
import org.apache.spark.sql.{Encoder, Encoders}
import org.apache.spark.sql.expressions.Aggregator
import org.apache.spark.sql.TypedColumn

// COMMAND ----------

// MAGIC %md In the next example, we construct a simple Aggregator that sums up a collection of `Int`s.

// COMMAND ----------

val simpleSum = new Aggregator[Int, Int, Int] with Serializable {
  def zero: Int = 0                     // The initial value.
  def reduce(b: Int, a: Int) = b + a    // Add an element to the running total
  def merge(b1: Int, b2: Int) = b1 + b2 // Merge intermediate values.
  def finish(b: Int) = b                // Return the final result.
  def bufferEncoder: Encoder[Int] = Encoders.scalaInt
  def outputEncoder: Encoder[Int] = Encoders.scalaInt}.toColumn

val ds = Seq(1, 2, 3, 4).toDS()
ds.select(simpleSum).collect

// COMMAND ----------

// MAGIC %md Using generics you can also construct a flexible `Aggregator` that can operate on many types of `Dataset`s.  In the next example, we construct an aggregator that can operate on any type that has a Scala `Numeric` defined on it.

// COMMAND ----------

/** An `Aggregator` that adds up any numeric type returned by the given function. */
class SumOf[I, N : Numeric : Encoder](f: I => N) extends Aggregator[I, N, N] with Serializable {

  private val numeric = implicitly[Numeric[N]]
  override def zero: N = numeric.zero
  override def reduce(b: N, a: I): N = numeric.plus(b, f(a))
  override def merge(b1: N, b2: N): N = numeric.plus(b1, b2)
  override def finish(reduction: N): N = reduction
  override def bufferEncoder: Encoder[N] = implicitly[Encoder[N]]
  override def outputEncoder: Encoder[N] = implicitly[Encoder[N]]
};

// COMMAND ----------

// MAGIC %md Aggregators can be used alongside built-in SQL/DataFrame aggregations.

// COMMAND ----------

def sum = new SumOf[(String, Int), Double](_._2.toDouble).toColumn;
val ds = Seq("a" -> 1, "a" -> 3, "b" -> 3).toDS()
ds.groupByKey(_._1).agg(sum).collect()

// COMMAND ----------

def sum = new SumOf[(Int, Long), (Int)](_._2.toInt).toColumn;
val ds = Seq((1, 2L), (2, 3L), (3, 4L), (1, 5L)).toDS()
ds.groupByKey(_._1).agg(sum).collect()

// COMMAND ----------

def sum[I, N : Numeric : Encoder](f: I => N): TypedColumn[I, N] = new SumOf(f).toColumn
val ds = Seq((1, 2L), (2, 3L), (3, 4L), (1, 5L)).toDS()
ds.select(sum[(Int, Long), Long](_._1), sum[(Int, Long), Long](_._2)).collect()