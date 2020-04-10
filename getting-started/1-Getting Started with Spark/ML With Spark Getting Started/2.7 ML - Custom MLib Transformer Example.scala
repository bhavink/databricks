// Databricks notebook source
import org.apache.spark.ml.Transformer
import org.apache.spark.ml.param.{Param, ParamMap}
import org.apache.spark.sql.{DataFrame, Dataset}
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.{col, explode, udf}
import org.apache.spark.sql.types.{DataTypes, StructType}

/**
 * An example demonstrating how to write a custom Transformer in a 3rd-party application.
 * This example intentionally avoids using any private Spark APIs.
 *
 * @param uid  All types inheriting from `Identifiable` require a `uid`.
 *             This includes Transformers, Estimators, and Models.
 */
class MyFlatMapTransformer(override val uid: String) extends Transformer {

  // Transformer Params
  // Defining a Param requires 3 elements:
  //  - Param definition
  //  - Param getter method
  //  - Param setter method
  // (The getter and setter are technically not required, but they are nice standards to follow.)

  /**
   * Param for input column name.
   */
  final val inputCol: Param[String] = new Param[String](this, "inputCol", "input column name")

  final def getInputCol: String = $(inputCol)

  final def setInputCol(value: String): MyFlatMapTransformer = set(inputCol, value)

  /**
   * Param for output column name.
   */
  final val outputCol: Param[String] = new Param[String](this, "outputCol", "output column name")

  final def getOutputCol: String = $(outputCol)

  final def setOutputCol(value: String): MyFlatMapTransformer = set(outputCol, value)

  // (Optional) You can set defaults for Param values if you like.
  setDefault(inputCol -> "myInputCol", outputCol -> "myOutputCol")

  // Transformer requires 3 methods:
  //  - transform
  //  - transformSchema
  //  - copy

  // Our flatMap will split strings by commas.
  private val myFlatMapFunction: String => Seq[String] = { input: String =>
    input.split(",")
  }

  /**
   * This method implements the main transformation.
   * Its required semantics are fully defined by the method API: take a Dataset or DataFrame,
   * and return a DataFrame.
   *
   * Most Transformers are 1-to-1 row mappings which add one or more new columns and do not
   * remove any columns.  However, this restriction is not required.  This example does a flatMap,
   * so we could either (a) drop other columns or (b) keep other columns, making copies of values
   * in each row as it expands to multiple rows in the flatMap.  We do (a) for simplicity.
   */
  override def transform(dataset: Dataset[_]): DataFrame = {
    val flatMapUdf = udf(myFlatMapFunction)
    dataset.select(explode(flatMapUdf(col($(inputCol)))).as($(outputCol)))
  }

  /**
   * Check transform validity and derive the output schema from the input schema.
   *
   * We check validity for interactions between parameters during `transformSchema` and
   * raise an exception if any parameter value is invalid. Parameter value checks which
   * do not depend on other parameters are handled by `Param.validate()`.
   *
   * Typical implementation should first conduct verification on schema change and parameter
   * validity, including complex parameter interaction checks.
   */
  override def transformSchema(schema: StructType): StructType = {
    // Validate input type.
    // Input type validation is technically optional, but it is a good practice since it catches
    // schema errors early on.
    val actualDataType = schema($(inputCol)).dataType
    require(actualDataType.equals(DataTypes.StringType),
      s"Column ${$(inputCol)} must be StringType but was actually $actualDataType.")

    // Compute output type.
    // This is important to do correctly when plugging this Transformer into a Pipeline,
    // where downstream Pipeline stages may expect use this Transformer's output as their input.
    DataTypes.createStructType(
      Array(
        DataTypes.createStructField($(outputCol), DataTypes.StringType, false)
      )
    )
  }

  /**
   * Creates a copy of this instance.
   * Requirements:
   *  - The copy must have the same UID.
   *  - The copy must have the same Params, with some possibly overwritten by the `extra`
   *    argument.
   *  - This should do a deep copy of any data members which are mutable.  That said,
   *    Transformers should generally be immutable (except for Params), so the `defaultCopy`
   *    method often suffices.
   * @param extra  Param values which will overwrite Params in the copy.
   */
  override def copy(extra: ParamMap): Transformer = defaultCopy(extra)
}

// COMMAND ----------

val data = spark.createDataFrame(Seq(
  ("hi,there", 1),
  ("a,b,c", 2),
  ("no", 3)
)).toDF("myInputCol", "id")
val myTransformer = new MyFlatMapTransformer("myFlatMapper")
println(s"Original data has ${data.count()} rows.")

// COMMAND ----------

display(data)

// COMMAND ----------

val output = myTransformer.transform(data)
println(s"Output data has ${output.count()} rows.")

// COMMAND ----------

display(output)