val crimeDF = spark.read
  .option("delimiter", "\t")
  .option("header", true)
  .option("timestampFormat", "mm/dd/yyyy hh:mm:ss a")
  .option("inferSchema", true)
  .csv("/mnt/training/Chicago-Crimes-2018.csv")

display(crimeDF)

==== JDBC ======
import org.apache.spark.sql.functions.{min, max}

val dfMin = accountDF.select(min("insertID")).first()(0).asInstanceOf[Long]
val dfMax = accountDF.select(max("insertID")).first()(0).asInstanceOf[Long]

println(s"DataFrame minimum: $dfMin \nDataFrame maximum: $dfMax")

import org.apache.spark.sql.functions.{min, max}

val dfMin = accountDF.select(min("insertID")).first()(0).asInstanceOf[Long]
val dfMax = accountDF.select(max("insertID")).first()(0).asInstanceOf[Long]

println(s"DataFrame minimum: $dfMin \nDataFrame maximum: $dfMax")


println(accountDF.rdd.getNumPartitions)
println(accountDFParallel.rdd.getNumPartitions)

def timeIt[T](op: => T): Float = {
  val start = System.currentTimeMillis
  val res = op
  val end = System.currentTimeMillis
  (end - start) / 1000f
}

val time1 = timeIt(accountDF.describe())
val time2 = timeIt(accountDFParallel.describe())

println(s"Serial read completed in $time1 seconds vs $time2 seconds for parallel read")

===== Date ====

val res = df.select($"id", $"date", unix_timestamp($"date", "yyyy/MM/dd HH:mm:ss").cast(TimestampType).as("timestamp"), current_timestamp(), current_date())





