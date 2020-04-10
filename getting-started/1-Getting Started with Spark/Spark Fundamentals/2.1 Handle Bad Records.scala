// Databricks notebook source
// When reading data from a file-based data source, Apache Spark SQL faces two typical error cases. First, the files may not be readable 
// (for instance, they could be missing, inaccessible or corrupted). Second, even if the files are processable, some records may not be parsable 
// (for example, due to syntax errors and schema mismatch).

// COMMAND ----------

// Creates a json file containing both parsable and corrupted records
Seq("""{"a": 1, "b": 2}""", """{bad-record""").toDF().write.text("/tmp/input/jsonFile")

val df = spark.read
  .option("badRecordsPath", "/tmp/badRecordsPath")
  .schema("a int, b int")
  .json("/tmp/input/jsonFile")

df.show()

// In this example, the DataFrame contains only the first parsable record ({"a": 1, "b": 2}). 
// The second bad record ({bad-record) is recorded in the exception file, which is a 
//                         JSON file located in /tmp/badRecordsPath/20170724T114715/bad_records/xyz. 
//                         The exception file contains the bad record, 
//                         the path of the file containing the record, and the exception/reason message. 
//                         After you locate the exception files, you can use a JSON reader to process them.

// COMMAND ----------

val df = spark.read
  .option("badRecordsPath", "/tmp/badRecordsPath")
  .parquet("/input/parquetFile")

// Delete the input parquet file '/input/parquetFile'
dbutils.fs.rm("/input/parquetFile")

df.show()

// In the above example, since df.show() is unable to find the input file, 
// Spark creates an exception file in JSON format to record the error. 
// For example, /tmp/badRecordsPath/20170724T101153/bad_files/xyz is the path of the exception file. 
// This file is under the specified badRecordsPath director, 
// /tmp/badRecordsPath. 20170724T101153 is the creation time of this DataFrameReader. 
// bad_files is the exception type. xyz is a file that contains a JSON record, 
// which has the path of the bad file and the exception/reason message.