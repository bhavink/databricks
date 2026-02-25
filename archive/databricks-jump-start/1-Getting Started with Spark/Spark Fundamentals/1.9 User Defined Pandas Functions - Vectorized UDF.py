# Databricks notebook source
# DBTITLE 1,pandas User-Defined Functions
# A pandas user-defined function (UDF)—also known as vectorized UDF—is a user-defined function 
# that uses Apache Arrow to transfer data and pandas to work with the data. 
# You define a pandas UDF using the keyword pandas_udf as a decorator or to wrap the function; no additional configuration is required.

# There are three types of pandas UDFs: scalar, grouped map, and grouped aggregate.

# For background information, see the blog post Introducing pandas UDFs for PySpark.
# https://databricks.com/blog/2017/10/30/introducing-vectorized-udfs-for-pyspark.html

# PyArrow is installed in Databricks Runtime. For information on the version of PyArrow available in each Databricks Runtime version


# As of Databricks Runtime 5.1 or above, all Apache Spark SQL data types are supported by Arrow-based conversion except MapType, 
# ArrayType of TimestampType, and nested StructType.

# BinaryType is supported only when PyArrow is 0.10.0 or above.




# COMMAND ----------

# DBTITLE 1,Scalar UDF
# You use Scalar UDFs for vectorizing scalar operations. You can be use them with functions such as select and withColumn. 
# The Python function should take pandas.Series as an input and return a pandas.Series of the same length. 
# Internally, Spark executes a pandas UDF by splitting columns into batches, 
# calling the function for each batch as a subset of the data, then concatenating the results.

# The following example shows how to create a scalar pandas UDF that computes the product of 2 columns.

import pandas as pd

from pyspark.sql.functions import col, pandas_udf
from pyspark.sql.types import LongType

# Declare the function and create the UDF
def multiply_func(a, b):
    return a * b

multiply = pandas_udf(multiply_func, returnType=LongType())

# The function for a pandas_udf should be able to execute with local pandas data
x = pd.Series([1, 2, 3])
print(multiply_func(x, x))
# 0    1
# 1    4
# 2    9
# dtype: int64

# Create a Spark DataFrame, 'spark' is an existing SparkSession
df = spark.createDataFrame(pd.DataFrame(x, columns=["x"]))

# Execute function as a Spark vectorized UDF
df.select(multiply(col("x"), col("x"))).show()
# +-------------------+
# |multiply_func(x, x)|
# +-------------------+
# |                  1|
# |                  4|
# |                  9|
# +-------------------+

# COMMAND ----------

# DBTITLE 1,Scalar iterator UDFs
# Databricks Runtime 5.5 and above supports scalar iterator pandas UDF, 
# which is the same as the scalar pandas UDF above except that the underlying 
# Python function takes an iterator of batches as input instead of a single batch and, 
# instead of returning a single output batch, it yields output batches or returns an iterator of output batches. 
# A scalar iterator pandas UDF is useful when the UDF execution requires initializing some state, 
# e.g., loading a machine learning model file to apply inference to every input batch.

# The following example shows how to create scalar iterator pandas UDFs.

import pandas as pd

from pyspark.sql.functions import col, pandas_udf, struct, PandasUDFType

pdf = pd.DataFrame([1, 2, 3], columns=["x"])
df = spark.createDataFrame(pdf)

# When the UDF is called with a single column that is not StructType,
# the input to the underlying function is an iterator of pd.Series.
@pandas_udf("long", PandasUDFType.SCALAR_ITER)
def plus_one(batch_iter):
    for x in batch_iter:
        yield x + 1

df.select(plus_one(col("x"))).show()
# +-----------+
# |plus_one(x)|
# +-----------+
# |          2|
# |          3|
# |          4|
# +-----------+

# When the UDF is called with more than one columns,
# the input to the underlying function is an iterator of pd.Series tuple.
@pandas_udf("long", PandasUDFType.SCALAR_ITER)
def multiply_two_cols(batch_iter):
    for a, b in batch_iter:
        yield a * b

df.select(multiply_two_cols(col("x"), col("x"))).show()
# +-----------------------+
# |multiply_two_cols(x, x)|
# +-----------------------+
# |                      1|
# |                      4|
# |                      9|
# +-----------------------+

# When the UDF is called with a single column that is StructType,
# the input to the underlying function is an iterator of pd.DataFrame.
@pandas_udf("long", PandasUDFType.SCALAR_ITER)
def multiply_two_nested_cols(pdf_iter):
    for pdf in pdf_iter:
        yield pdf["a"] * pdf["b"]

df.select(
    multiply_two_nested_cols(
        struct(col("x").alias("a"), col("x").alias("b"))
    ).alias("y")
).show()
# +---+
# |  y|
# +---+
# |  1|
# |  4|
# |  9|
# +---+

# In the UDF, you can initialize some state before processing batches.
# Wrap your code with try/finally or use context managers to ensure
# the release of resources at the end.
y_bc = spark.sparkContext.broadcast(1)

@pandas_udf("long", PandasUDFType.SCALAR_ITER)
def plus_y(batch_iter):
    y = y_bc.value  # initialize states
    try:
        for x in batch_iter:
            yield x + y
    finally:
        pass  # release resources here, if any

df.select(plus_y(col("x"))).show()
# +---------+
# |plus_y(x)|
# +---------+
# |        2|
# |        3|
# |        4|
# +---------+

# COMMAND ----------

# DBTITLE 1,Grouped map UDFs
# You use grouped map pandas UDFs with groupBy().apply() to implement the “split-apply-combine” pattern. Split-apply-combine consists of three steps:

# Split the data into groups by using DataFrame.groupBy.
# Apply a function on each group. The input and output of the function are both pandas.DataFrame. The input data contains all the rows and columns for each group.
# Combine the results into a new DataFrame.
# To use groupBy().apply(), you must define the following:

# A Python function that defines the computation for each group
# A StructType object or a string that defines the schema of the output DataFrame
# The column labels of the returned pandas.DataFrame must either match the field names in the defined output schema if specified as strings, or match the field data types by position if not strings, for example, integer indices

# All data for a group is loaded into memory before the function is applied. 
# This can lead to out of memory exceptions, especially if the group sizes are skewed. 
# The configuration for maxRecordsPerBatch is not applied on groups and it is up to you to ensure that the grouped data will fit into the available memory.

# The following example shows how to use groupby().apply() to subtract the mean from each value in the group.

# https://spark.apache.org/docs/latest/api/python/pyspark.sql.html#pyspark.sql.GroupedData.apply


from pyspark.sql.functions import pandas_udf, PandasUDFType

df = spark.createDataFrame(
    [(1, 1.0), (1, 2.0), (2, 3.0), (2, 5.0), (2, 10.0)],
    ("id", "v"))

@pandas_udf("id long, v double", PandasUDFType.GROUPED_MAP)
def subtract_mean(pdf):
    # pdf is a pandas.DataFrame
    v = pdf.v
    return pdf.assign(v=v - v.mean())

df.groupby("id").apply(subtract_mean).show()
# +---+----+
# | id|   v|
# +---+----+
# |  1|-0.5|
# |  1| 0.5|
# |  2|-3.0|
# |  2|-1.0|
# |  2| 4.0|
# +---+----+

# COMMAND ----------

# DBTITLE 1,Grouped aggregate UDFs
# Grouped aggregate pandas UDFs are similar to Spark aggregate functions. 
# You use grouped aggregate pandas UDFs with groupBy().agg() and pyspark.sql.Window. 
# A grouped aggregate UDF defines an aggregation from one or more pandas.Series to a scalar value, 
# where each pandas.Series represents a column within the group or window.

# This type of UDF does not support partial aggregation and all data for a group or window is loaded into memory. 
# Also, only unbounded window is supported with grouped aggregate pandas UDFs.

# The following example shows how to use this type of UDF to compute mean with groupBy and window operations:

from pyspark.sql.functions import pandas_udf, PandasUDFType
from pyspark.sql import Window

df = spark.createDataFrame(
    [(1, 1.0), (1, 2.0), (2, 3.0), (2, 5.0), (2, 10.0)],
    ("id", "v"))

@pandas_udf("double", PandasUDFType.GROUPED_AGG)
def mean_udf(v):
    return v.mean()

df.groupby("id").agg(mean_udf(df['v'])).show()
# +---+-----------+
# | id|mean_udf(v)|
# +---+-----------+
# |  1|        1.5|
# |  2|        6.0|
# +---+-----------+

w = Window \
    .partitionBy('id') \
    .rowsBetween(Window.unboundedPreceding, Window.unboundedFollowing)
df.withColumn('mean_v', mean_udf(df['v']).over(w)).show()
# +---+----+------+
# | id|   v|mean_v|
# +---+----+------+
# |  1| 1.0|   1.5|
# |  1| 2.0|   1.5|
# |  2| 3.0|   6.0|
# |  2| 5.0|   6.0|
# |  2|10.0|   6.0|
# +---+----+------+

# COMMAND ----------

# Setting Arrow batch size
# Data partitions in Spark are converted into Arrow record batches, which can temporarily lead to high memory usage in the JVM. To avoid possible out of memory exceptions, the size of the Arrow record batches can be adjusted by setting the spark.sql.execution.arrow.maxRecordsPerBatch configuration to an integer that determines the maximum number of rows for each batch. The default value is 10,000 records per batch. If the number of columns is large, the value should be adjusted accordingly. Using this limit, each data partition is divided into 1 or more record batches for processing.