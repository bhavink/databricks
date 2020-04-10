***REMOVED*** Databricks notebook source
***REMOVED*** DBTITLE 1,pandas User-Defined Functions
***REMOVED*** A pandas user-defined function (UDF)—also known as vectorized UDF—is a user-defined function 
***REMOVED*** that uses Apache Arrow to transfer data and pandas to work with the data. 
***REMOVED*** You define a pandas UDF using the keyword pandas_udf as a decorator or to wrap the function; no additional configuration is required.

***REMOVED*** There are three types of pandas UDFs: scalar, grouped map, and grouped aggregate.

***REMOVED*** For background information, see the blog post Introducing pandas UDFs for PySpark.
***REMOVED*** https://databricks.com/blog/2017/10/30/introducing-vectorized-udfs-for-pyspark.html

***REMOVED*** PyArrow is installed in Databricks Runtime. For information on the version of PyArrow available in each Databricks Runtime version


***REMOVED*** As of Databricks Runtime 5.1 or above, all Apache Spark SQL data types are supported by Arrow-based conversion except MapType, 
***REMOVED*** ArrayType of TimestampType, and nested StructType.

***REMOVED*** BinaryType is supported only when PyArrow is 0.10.0 or above.




***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Scalar UDF
***REMOVED*** You use Scalar UDFs for vectorizing scalar operations. You can be use them with functions such as select and withColumn. 
***REMOVED*** The Python function should take pandas.Series as an input and return a pandas.Series of the same length. 
***REMOVED*** Internally, Spark executes a pandas UDF by splitting columns into batches, 
***REMOVED*** calling the function for each batch as a subset of the data, then concatenating the results.

***REMOVED*** The following example shows how to create a scalar pandas UDF that computes the product of 2 columns.

import pandas as pd

from pyspark.sql.functions import col, pandas_udf
from pyspark.sql.types import LongType

***REMOVED*** Declare the function and create the UDF
def multiply_func(a, b):
    return a * b

multiply = pandas_udf(multiply_func, returnType=LongType())

***REMOVED*** The function for a pandas_udf should be able to execute with local pandas data
x = pd.Series([1, 2, 3])
print(multiply_func(x, x))
***REMOVED*** 0    1
***REMOVED*** 1    4
***REMOVED*** 2    9
***REMOVED*** dtype: int64

***REMOVED*** Create a Spark DataFrame, 'spark' is an existing SparkSession
df = spark.createDataFrame(pd.DataFrame(x, columns=["x"]))

***REMOVED*** Execute function as a Spark vectorized UDF
df.select(multiply(col("x"), col("x"))).show()
***REMOVED*** +-------------------+
***REMOVED*** |multiply_func(x, x)|
***REMOVED*** +-------------------+
***REMOVED*** |                  1|
***REMOVED*** |                  4|
***REMOVED*** |                  9|
***REMOVED*** +-------------------+

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Scalar iterator UDFs
***REMOVED*** Databricks Runtime 5.5 and above supports scalar iterator pandas UDF, 
***REMOVED*** which is the same as the scalar pandas UDF above except that the underlying 
***REMOVED*** Python function takes an iterator of batches as input instead of a single batch and, 
***REMOVED*** instead of returning a single output batch, it yields output batches or returns an iterator of output batches. 
***REMOVED*** A scalar iterator pandas UDF is useful when the UDF execution requires initializing some state, 
***REMOVED*** e.g., loading a machine learning model file to apply inference to every input batch.

***REMOVED*** The following example shows how to create scalar iterator pandas UDFs.

import pandas as pd

from pyspark.sql.functions import col, pandas_udf, struct, PandasUDFType

pdf = pd.DataFrame([1, 2, 3], columns=["x"])
df = spark.createDataFrame(pdf)

***REMOVED*** When the UDF is called with a single column that is not StructType,
***REMOVED*** the input to the underlying function is an iterator of pd.Series.
@pandas_udf("long", PandasUDFType.SCALAR_ITER)
def plus_one(batch_iter):
    for x in batch_iter:
        yield x + 1

df.select(plus_one(col("x"))).show()
***REMOVED*** +-----------+
***REMOVED*** |plus_one(x)|
***REMOVED*** +-----------+
***REMOVED*** |          2|
***REMOVED*** |          3|
***REMOVED*** |          4|
***REMOVED*** +-----------+

***REMOVED*** When the UDF is called with more than one columns,
***REMOVED*** the input to the underlying function is an iterator of pd.Series tuple.
@pandas_udf("long", PandasUDFType.SCALAR_ITER)
def multiply_two_cols(batch_iter):
    for a, b in batch_iter:
        yield a * b

df.select(multiply_two_cols(col("x"), col("x"))).show()
***REMOVED*** +-----------------------+
***REMOVED*** |multiply_two_cols(x, x)|
***REMOVED*** +-----------------------+
***REMOVED*** |                      1|
***REMOVED*** |                      4|
***REMOVED*** |                      9|
***REMOVED*** +-----------------------+

***REMOVED*** When the UDF is called with a single column that is StructType,
***REMOVED*** the input to the underlying function is an iterator of pd.DataFrame.
@pandas_udf("long", PandasUDFType.SCALAR_ITER)
def multiply_two_nested_cols(pdf_iter):
    for pdf in pdf_iter:
        yield pdf["a"] * pdf["b"]

df.select(
    multiply_two_nested_cols(
        struct(col("x").alias("a"), col("x").alias("b"))
    ).alias("y")
).show()
***REMOVED*** +---+
***REMOVED*** |  y|
***REMOVED*** +---+
***REMOVED*** |  1|
***REMOVED*** |  4|
***REMOVED*** |  9|
***REMOVED*** +---+

***REMOVED*** In the UDF, you can initialize some state before processing batches.
***REMOVED*** Wrap your code with try/finally or use context managers to ensure
***REMOVED*** the release of resources at the end.
y_bc = spark.sparkContext.broadcast(1)

@pandas_udf("long", PandasUDFType.SCALAR_ITER)
def plus_y(batch_iter):
    y = y_bc.value  ***REMOVED*** initialize states
    try:
        for x in batch_iter:
            yield x + y
    finally:
        pass  ***REMOVED*** release resources here, if any

df.select(plus_y(col("x"))).show()
***REMOVED*** +---------+
***REMOVED*** |plus_y(x)|
***REMOVED*** +---------+
***REMOVED*** |        2|
***REMOVED*** |        3|
***REMOVED*** |        4|
***REMOVED*** +---------+

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Grouped map UDFs
***REMOVED*** You use grouped map pandas UDFs with groupBy().apply() to implement the “split-apply-combine” pattern. Split-apply-combine consists of three steps:

***REMOVED*** Split the data into groups by using DataFrame.groupBy.
***REMOVED*** Apply a function on each group. The input and output of the function are both pandas.DataFrame. The input data contains all the rows and columns for each group.
***REMOVED*** Combine the results into a new DataFrame.
***REMOVED*** To use groupBy().apply(), you must define the following:

***REMOVED*** A Python function that defines the computation for each group
***REMOVED*** A StructType object or a string that defines the schema of the output DataFrame
***REMOVED*** The column labels of the returned pandas.DataFrame must either match the field names in the defined output schema if specified as strings, or match the field data types by position if not strings, for example, integer indices

***REMOVED*** All data for a group is loaded into memory before the function is applied. 
***REMOVED*** This can lead to out of memory exceptions, especially if the group sizes are skewed. 
***REMOVED*** The configuration for maxRecordsPerBatch is not applied on groups and it is up to you to ensure that the grouped data will fit into the available memory.

***REMOVED*** The following example shows how to use groupby().apply() to subtract the mean from each value in the group.

***REMOVED*** https://spark.apache.org/docs/latest/api/python/pyspark.sql.html***REMOVED***pyspark.sql.GroupedData.apply


from pyspark.sql.functions import pandas_udf, PandasUDFType

df = spark.createDataFrame(
    [(1, 1.0), (1, 2.0), (2, 3.0), (2, 5.0), (2, 10.0)],
    ("id", "v"))

@pandas_udf("id long, v double", PandasUDFType.GROUPED_MAP)
def subtract_mean(pdf):
    ***REMOVED*** pdf is a pandas.DataFrame
    v = pdf.v
    return pdf.assign(v=v - v.mean())

df.groupby("id").apply(subtract_mean).show()
***REMOVED*** +---+----+
***REMOVED*** | id|   v|
***REMOVED*** +---+----+
***REMOVED*** |  1|-0.5|
***REMOVED*** |  1| 0.5|
***REMOVED*** |  2|-3.0|
***REMOVED*** |  2|-1.0|
***REMOVED*** |  2| 4.0|
***REMOVED*** +---+----+

***REMOVED*** COMMAND ----------

***REMOVED*** DBTITLE 1,Grouped aggregate UDFs
***REMOVED*** Grouped aggregate pandas UDFs are similar to Spark aggregate functions. 
***REMOVED*** You use grouped aggregate pandas UDFs with groupBy().agg() and pyspark.sql.Window. 
***REMOVED*** A grouped aggregate UDF defines an aggregation from one or more pandas.Series to a scalar value, 
***REMOVED*** where each pandas.Series represents a column within the group or window.

***REMOVED*** This type of UDF does not support partial aggregation and all data for a group or window is loaded into memory. 
***REMOVED*** Also, only unbounded window is supported with grouped aggregate pandas UDFs.

***REMOVED*** The following example shows how to use this type of UDF to compute mean with groupBy and window operations:

from pyspark.sql.functions import pandas_udf, PandasUDFType
from pyspark.sql import Window

df = spark.createDataFrame(
    [(1, 1.0), (1, 2.0), (2, 3.0), (2, 5.0), (2, 10.0)],
    ("id", "v"))

@pandas_udf("double", PandasUDFType.GROUPED_AGG)
def mean_udf(v):
    return v.mean()

df.groupby("id").agg(mean_udf(df['v'])).show()
***REMOVED*** +---+-----------+
***REMOVED*** | id|mean_udf(v)|
***REMOVED*** +---+-----------+
***REMOVED*** |  1|        1.5|
***REMOVED*** |  2|        6.0|
***REMOVED*** +---+-----------+

w = Window \
    .partitionBy('id') \
    .rowsBetween(Window.unboundedPreceding, Window.unboundedFollowing)
df.withColumn('mean_v', mean_udf(df['v']).over(w)).show()
***REMOVED*** +---+----+------+
***REMOVED*** | id|   v|mean_v|
***REMOVED*** +---+----+------+
***REMOVED*** |  1| 1.0|   1.5|
***REMOVED*** |  1| 2.0|   1.5|
***REMOVED*** |  2| 3.0|   6.0|
***REMOVED*** |  2| 5.0|   6.0|
***REMOVED*** |  2|10.0|   6.0|
***REMOVED*** +---+----+------+

***REMOVED*** COMMAND ----------

***REMOVED*** Setting Arrow batch size
***REMOVED*** Data partitions in Spark are converted into Arrow record batches, which can temporarily lead to high memory usage in the JVM. To avoid possible out of memory exceptions, the size of the Arrow record batches can be adjusted by setting the spark.sql.execution.arrow.maxRecordsPerBatch configuration to an integer that determines the maximum number of rows for each batch. The default value is 10,000 records per batch. If the number of columns is large, the value should be adjusted accordingly. Using this limit, each data partition is divided into 1 or more record batches for processing.