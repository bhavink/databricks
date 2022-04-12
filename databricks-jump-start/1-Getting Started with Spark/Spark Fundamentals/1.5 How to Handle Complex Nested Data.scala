// Databricks notebook source
// MAGIC %md ***REMOVED******REMOVED***Five Spark SQL Helper Utility Functions to Extract and Explore Complex Data Types

// COMMAND ----------

// MAGIC %md While this [in-depth blog lays out and explains the concepts and motivations](https://databricks.com/blog/2017/02/23/working-complex-data-formats-structured-streaming-apache-spark-2-1.html) for processing and handling complex data types and formats, this notebook example examines how you can apply them, with a few concrete examples, for data types that you might encounter in your use cases. This short notebook tutorial shows ways in which you can explore and employ a number of new helper Spark SQL utility functions and APIs as part of [`org.apache.spark.sql.functions`](https://spark.apache.org/docs/latest/api/scala/index.html***REMOVED***org.apache.spark.sql.functions$) package. In particular, they come in handy while doing Streaming ETL, in which data are JSON objects with complex and nested structures: Map and Structs embedded as JSON:
// MAGIC 
// MAGIC * `get_json_object()`
// MAGIC * `from_json()`
// MAGIC * `to_json()`
// MAGIC * `explode()`
// MAGIC * `selectExpr()`
// MAGIC 
// MAGIC The takeaway from this short tutorial is myriad ways to slice and dice nested JSON structures with Spark SQL utility functions.

// COMMAND ----------

// MAGIC %md Let's create a simple JSON schema with attributes and values, without any nested structures.

// COMMAND ----------

import org.apache.spark.sql.types._                         // include the Spark Types to define our schema
import org.apache.spark.sql.functions._                     // include the Spark helper functions

val jsonSchema = new StructType()
        .add("battery_level", LongType)
        .add("c02_level", LongType)
        .add("cca3",StringType)
        .add("cn", StringType)
        .add("device_id", LongType)
        .add("device_type", StringType)
        .add("signal", LongType)
        .add("ip", StringType)
        .add("temp", LongType)
        .add("timestamp", TimestampType)

// COMMAND ----------

// MAGIC %md Using the schema above, create a Dataset, represented as a Scala case type, and generate some JSON data associated with it. In all likelihood, this JSON might as well be a stream of device events read off a Kafka topic. Note that the case class has two fields: integer (as a device id) and a string (as a JSON string representing device events).

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED******REMOVED******REMOVED*** Create a Dataset from the above schema

// COMMAND ----------

// define a case class
case class DeviceData (id: Int, device: String)
// create some sample data
val eventsDS = Seq (
 (0, """{"device_id": 0, "device_type": "sensor-ipad", "ip": "68.161.225.1", "cca3": "USA", "cn": "United States", "temp": 25, "signal": 23, "battery_level": 8, "c02_level": 917, "timestamp" :1475600496 }"""),
 (1, """{"device_id": 1, "device_type": "sensor-igauge", "ip": "213.161.254.1", "cca3": "NOR", "cn": "Norway", "temp": 30, "signal": 18, "battery_level": 6, "c02_level": 1413, "timestamp" :1475600498 }"""),
 (2, """{"device_id": 2, "device_type": "sensor-ipad", "ip": "88.36.5.1", "cca3": "ITA", "cn": "Italy", "temp": 18, "signal": 25, "battery_level": 5, "c02_level": 1372, "timestamp" :1475600500 }"""),
 (3, """{"device_id": 3, "device_type": "sensor-inest", "ip": "66.39.173.154", "cca3": "USA", "cn": "United States", "temp": 47, "signal": 12, "battery_level": 1, "c02_level": 1447, "timestamp" :1475600502 }"""),
(4, """{"device_id": 4, "device_type": "sensor-ipad", "ip": "203.82.41.9", "cca3": "PHL", "cn": "Philippines", "temp": 29, "signal": 11, "battery_level": 0, "c02_level": 983, "timestamp" :1475600504 }"""),
(5, """{"device_id": 5, "device_type": "sensor-istick", "ip": "204.116.105.67", "cca3": "USA", "cn": "United States", "temp": 50, "signal": 16, "battery_level": 8, "c02_level": 1574, "timestamp" :1475600506 }"""),
(6, """{"device_id": 6, "device_type": "sensor-ipad", "ip": "220.173.179.1", "cca3": "CHN", "cn": "China", "temp": 21, "signal": 18, "battery_level": 9, "c02_level": 1249, "timestamp" :1475600508 }"""),
(7, """{"device_id": 7, "device_type": "sensor-ipad", "ip": "118.23.68.227", "cca3": "JPN", "cn": "Japan", "temp": 27, "signal": 15, "battery_level": 0, "c02_level": 1531, "timestamp" :1475600512 }"""),
(8 ,""" {"device_id": 8, "device_type": "sensor-inest", "ip": "208.109.163.218", "cca3": "USA", "cn": "United States", "temp": 40, "signal": 16, "battery_level": 9, "c02_level": 1208, "timestamp" :1475600514 }"""),
(9,"""{"device_id": 9, "device_type": "sensor-ipad", "ip": "88.213.191.34", "cca3": "ITA", "cn": "Italy", "temp": 19, "signal": 11, "battery_level": 0, "c02_level": 1171, "timestamp" :1475600516 }"""),
(10,"""{"device_id": 10, "device_type": "sensor-igauge", "ip": "68.28.91.22", "cca3": "USA", "cn": "United States", "temp": 32, "signal": 26, "battery_level": 7, "c02_level": 886, "timestamp" :1475600518 }"""),
(11,"""{"device_id": 11, "device_type": "sensor-ipad", "ip": "59.144.114.250", "cca3": "IND", "cn": "India", "temp": 46, "signal": 25, "battery_level": 4, "c02_level": 863, "timestamp" :1475600520 }"""),
(12, """{"device_id": 12, "device_type": "sensor-igauge", "ip": "193.156.90.200", "cca3": "NOR", "cn": "Norway", "temp": 18, "signal": 26, "battery_level": 8, "c02_level": 1220, "timestamp" :1475600522 }"""),
(13, """{"device_id": 13, "device_type": "sensor-ipad", "ip": "67.185.72.1", "cca3": "USA", "cn": "United States", "temp": 34, "signal": 20, "battery_level": 8, "c02_level": 1504, "timestamp" :1475600524 }"""),
(14, """{"device_id": 14, "device_type": "sensor-inest", "ip": "68.85.85.106", "cca3": "USA", "cn": "United States", "temp": 39, "signal": 17, "battery_level": 8, "c02_level": 831, "timestamp" :1475600526 }"""),
(15, """{"device_id": 15, "device_type": "sensor-ipad", "ip": "161.188.212.254", "cca3": "USA", "cn": "United States", "temp": 27, "signal": 26, "battery_level": 5, "c02_level": 1378, "timestamp" :1475600528 }"""),
(16, """{"device_id": 16, "device_type": "sensor-igauge", "ip": "221.3.128.242", "cca3": "CHN", "cn": "China", "temp": 10, "signal": 24, "battery_level": 6, "c02_level": 1423, "timestamp" :1475600530 }"""),
(17, """{"device_id": 17, "device_type": "sensor-ipad", "ip": "64.124.180.215", "cca3": "USA", "cn": "United States", "temp": 38, "signal": 17, "battery_level": 9, "c02_level": 1304, "timestamp" :1475600532 }"""),
(18, """{"device_id": 18, "device_type": "sensor-igauge", "ip": "66.153.162.66", "cca3": "USA", "cn": "United States", "temp": 26, "signal": 10, "battery_level": 0, "c02_level": 902, "timestamp" :1475600534 }"""),
(19, """{"device_id": 19, "device_type": "sensor-ipad", "ip": "193.200.142.254", "cca3": "AUT", "cn": "Austria", "temp": 32, "signal": 27, "battery_level": 5, "c02_level": 1282, "timestamp" :1475600536 }""")).toDF("id", "device").as[DeviceData]

// COMMAND ----------

// MAGIC %md Our Dataset is collection of Scala case classes, and when displayed as DataFrame, there are two columns (id, string)

// COMMAND ----------

display(eventsDS)

// COMMAND ----------

// MAGIC %md Printing the schema atests to two columns of type `integer` and `string`, reflecting the Scala case class.

// COMMAND ----------

eventsDS.printSchema

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** How to use `get_json_object()`

// COMMAND ----------

// MAGIC %md This method extracts a JSON object from a JSON string based on JSON path specified, and returns a JSON string as the extracted JSON object. 
// MAGIC Take the small example of the above dataset, from which we wish to extract portions of data values that make up the JSON object string. 
// MAGIC Say you want to extract only id, device_type, ip, and CCA3 code. Here's a quick way to do it using `get_json_object()`.

// COMMAND ----------

val eventsFromJSONDF = Seq (
 (0, """{"device_id": 0, "device_type": "sensor-ipad", "ip": "68.161.225.1", "cca3": "USA", "cn": "United States", "temp": 25, "signal": 23, "battery_level": 8, "c02_level": 917, "timestamp" :1475600496 }"""),
 (1, """{"device_id": 1, "device_type": "sensor-igauge", "ip": "213.161.254.1", "cca3": "NOR", "cn": "Norway", "temp": 30, "signal": 18, "battery_level": 6, "c02_level": 1413, "timestamp" :1475600498 }"""),
 (2, """{"device_id": 2, "device_type": "sensor-ipad", "ip": "88.36.5.1", "cca3": "ITA", "cn": "Italy", "temp": 18, "signal": 25, "battery_level": 5, "c02_level": 1372, "timestamp" :1475600500 }"""),
 (3, """{"device_id": 3, "device_type": "sensor-inest", "ip": "66.39.173.154", "cca3": "USA", "cn": "United States", "temp": 47, "signal": 12, "battery_level": 1, "c02_level": 1447, "timestamp" :1475600502 }"""),
(4, """{"device_id": 4, "device_type": "sensor-ipad", "ip": "203.82.41.9", "cca3": "PHL", "cn": "Philippines", "temp": 29, "signal": 11, "battery_level": 0, "c02_level": 983, "timestamp" :1475600504 }"""),
(5, """{"device_id": 5, "device_type": "sensor-istick", "ip": "204.116.105.67", "cca3": "USA", "cn": "United States", "temp": 50, "signal": 16, "battery_level": 8, "c02_level": 1574, "timestamp" :1475600506 }"""),
(6, """{"device_id": 6, "device_type": "sensor-ipad", "ip": "220.173.179.1", "cca3": "CHN", "cn": "China", "temp": 21, "signal": 18, "battery_level": 9, "c02_level": 1249, "timestamp" :1475600508 }"""),
(7, """{"device_id": 7, "device_type": "sensor-ipad", "ip": "118.23.68.227", "cca3": "JPN", "cn": "Japan", "temp": 27, "signal": 15, "battery_level": 0, "c02_level": 1531, "timestamp" :1475600512 }"""),
(8 ,""" {"device_id": 8, "device_type": "sensor-inest", "ip": "208.109.163.218", "cca3": "USA", "cn": "United States", "temp": 40, "signal": 16, "battery_level": 9, "c02_level": 1208, "timestamp" :1475600514 }"""),
(9,"""{"device_id": 9, "device_type": "sensor-ipad", "ip": "88.213.191.34", "cca3": "ITA", "cn": "Italy", "temp": 19, "signal": 11, "battery_level": 0, "c02_level": 1171, "timestamp" :1475600516 }""")).toDF("id", "json")

// COMMAND ----------

display(eventsFromJSONDF)

// COMMAND ----------

val jsDF = eventsFromJSONDF.select($"id", get_json_object($"json", "$.device_type").alias("device_type"),
                                          get_json_object($"json", "$.ip").alias("ip"),
                                         get_json_object($"json", "$.cca3").alias("cca3"))

// COMMAND ----------

display(jsDF)

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** How to use `from_json()`

// COMMAND ----------

// MAGIC %md A variation of `get_json_object()`, this function uses schema to extract individual columns. Using [_from_json()_](https://spark.apache.org/docs/latest/api/scala/index.html***REMOVED***org.apache.spark.sql.functions$) helper function within the _select()_ Dataset API call, I can extract or decode data's attributes and values from a JSON string into a DataFrame as columns, dictated by a schema. As well using the schema, I ascribe all associated atrributes and values within this JSON to represent as an entity *devices*. As such, not only can you use the `device.attribute` to retrieve its respective value but also all values using the *** notation.
// MAGIC 
// MAGIC In example below:
// MAGIC * Uses the schema above to extract from the JSON string attributes and values and represent them as individual columns as part of `devices`
// MAGIC * `select()` all its columns
// MAGIC * Filters on desired attributes using the `.` notation

// COMMAND ----------

// MAGIC %md Once you have extracted data from a JSON string into its respective DataFrame columns, you can apply DataFrame/Dataset APIs calls to select, filter, and subsequtly display, to your satisfaction.

// COMMAND ----------

val devicesDF = eventsDS.select(from_json($"device", jsonSchema) as "devices")
.select($"devices.*")
.filter($"devices.temp" > 10 and $"devices.signal" > 15)

// COMMAND ----------

display(devicesDF)

// COMMAND ----------

val devicesUSDF = devicesDF.select($"*").where($"cca3" === "USA").orderBy($"signal".desc, $"temp".desc)

// COMMAND ----------

display(devicesUSDF)

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** How to use `to_json()`

// COMMAND ----------

// MAGIC %md Now, let's do the reverse: you can convert or encode our filtered devices into JSON string using [`to_json()`](https://spark.apache.org/docs/latest/api/scala/index.html***REMOVED***org.apache.spark.sql.functions$). That is, convert a JSON struct into a string. The result can be republished, for instance, to Kafka or saved on disk as parquet files. To learn how to write to Kafka and other sinks, [read this blog](https://databricks.com/blog/2017/04/04/real-time-end-to-end-integration-with-apache-kafka-in-apache-sparks-structured-streaming.html) and our series on [Structured Streaming blogs.](https://databricks.com/blog/2017/01/19/real-time-streaming-etl-structured-streaming-apache-spark-2-1.html)

// COMMAND ----------

val stringJsonDF = eventsDS.select(to_json(struct($"*"))).toDF("devices")

// COMMAND ----------

display(stringJsonDF)

// COMMAND ----------

// MAGIC %md Assuming you have a Kafka cluster running at specified port and the respective topic, let's write to Kafka topic.

// COMMAND ----------

// stringJsonDF.write
//             .format("kafka")
//             .option("kafka.bootstrap.servers", "your_host_name:9092")
//             .option("topic", "iot-devices")
//             .save()

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** How to use `selectExpr()`

// COMMAND ----------

// MAGIC %md Another way to convert or encode a column into a JSON object as string is to use the _selectExpr()_ utility function. For instance, I can convert the "device" column of our DataFrame from above into a JSON String

// COMMAND ----------

val stringsDF = eventsDS.selectExpr("CAST(id AS INT)", "CAST(device AS STRING)")

// COMMAND ----------

stringsDF.printSchema

// COMMAND ----------

display(stringsDF)

// COMMAND ----------

// MAGIC %md Another use of `selectExpr()` is its ability, as the function name suggests, take expressions as arguments and convert them into respective columns. For instance, say I want to express c02 levels and temperature ratios. 

// COMMAND ----------

display(devicesDF.selectExpr("c02_level", "round(c02_level/temp) as ratio_c02_temperature").orderBy($"ratio_c02_temperature" desc))

// COMMAND ----------

// MAGIC %md The above query could as easily be expressed in Spark SQL as in DataFrame API. The power of _selectExpr()_ lies in dealing with or working 
// MAGIC with numerical values. Let's try to create a tempoary view and express the same query, except this time we use SQL.

// COMMAND ----------

devicesDF.createOrReplaceTempView("devicesDFT")

// COMMAND ----------

// MAGIC %md Notice the output from **cmd 42** is not different from **cmd** 38. Both undergo the same Spark SQL engine's Catalyst and generate equivalent underlying compact code.

// COMMAND ----------

// MAGIC %sql select c02_level, 
// MAGIC         round(c02_level/temp) as ratio_c02_temperature 
// MAGIC         from devicesDFT
// MAGIC         order by ratio_c02_temperature desc

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** To verify that all your string conversions are preserved in the above DataFrame `stringJsonDF`, let's save to blob storage as Parquet.

// COMMAND ----------

stringJsonDF
  .write
  .mode("overwrite")
  .format("parquet")
  .save("/tmp/iot")

// COMMAND ----------

// MAGIC %md Check if all files were written.

// COMMAND ----------

// MAGIC %fs ls /tmp/iot

// COMMAND ----------

// MAGIC %md Now let's verify what was saved—devices as each indivdual strings encoded from above—are actual strings.

// COMMAND ----------

val parquetDF = spark.read.parquet("/tmp/iot")

// COMMAND ----------

// MAGIC %md Let's check the schema to ensure what was written is not different from what is read, namely the JSON string.

// COMMAND ----------

parquetDF.printSchema

// COMMAND ----------

display(parquetDF)

// COMMAND ----------

// MAGIC %md So far this tutorial has explored ways to use `get_json_object()`, `from_json()`, `to_json()`, `selectExpr()`, and `explode()` helper functions handling less complex JSON objects.
// MAGIC 
// MAGIC Let's turn focus to a more nested structures and examine how these same APIs as applied to a complex JSON as simple one.

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED*** Nested Structures
// MAGIC It's not unreasonable to assume that your JSON nested structures may have Maps as well as nested JSON. For illustration, let's use a single string comprised of  complex and nested data types, including a Map. In a real life scenario, this could be a reading from a device event, with dangerous levels of C02 emissions or high temperature readings, that needs Network Operation Center (NOC) notification for some immediate action. 

// COMMAND ----------

import org.apache.spark.sql.types._

val schema = new StructType()
  .add("dc_id", StringType)                               // data center where data was posted to Kafka cluster
  .add("source",                                          // info about the source of alarm
    MapType(                                              // define this as a Map(Key->value)
      StringType,
      new StructType()
      .add("description", StringType)
      .add("ip", StringType)
      .add("id", LongType)
      .add("temp", LongType)
      .add("c02_level", LongType)
      .add("geo", 
         new StructType()
          .add("lat", DoubleType)
          .add("long", DoubleType)
        )
      )
    )

// COMMAND ----------

// MAGIC %md Let's create a single complex JSON with complex data types.

// COMMAND ----------

//create a single entry with id and its complex and nested data types

val dataDS = Seq("""
{
"dc_id": "dc-101",
"source": {
    "sensor-igauge": {
      "id": 10,
      "ip": "68.28.91.22",
      "description": "Sensor attached to the container ceilings",
      "temp":35,
      "c02_level": 1475,
      "geo": {"lat":38.00, "long":97.00}                        
    },
    "sensor-ipad": {
      "id": 13,
      "ip": "67.185.72.1",
      "description": "Sensor ipad attached to carbon cylinders",
      "temp": 34,
      "c02_level": 1370,
      "geo": {"lat":47.41, "long":-122.00}
    },
    "sensor-inest": {
      "id": 8,
      "ip": "208.109.163.218",
      "description": "Sensor attached to the factory ceilings",
      "temp": 40,
      "c02_level": 1346,
      "geo": {"lat":33.61, "long":-111.89}
    },
    "sensor-istick": {
      "id": 5,
      "ip": "204.116.105.67",
      "description": "Sensor embedded in exhaust pipes in the ceilings",
      "temp": 40,
      "c02_level": 1574,
      "geo": {"lat":35.93, "long":-85.46}
    }
  }
}""").toDS()
// should only be one item
dataDS.count()

// COMMAND ----------

display(dataDS)

// COMMAND ----------

// MAGIC %md Let's process it. Note that we have nested structure `geo`.

// COMMAND ----------

val df = spark                  // spark session 
.read                           // get DataFrameReader
.schema(schema)                 // use the defined schema above and read format as JSON
.json(dataDS.rdd)               // RDD[String]

// COMMAND ----------

// MAGIC %md Let's examine its nested and complex schema.

// COMMAND ----------

df.printSchema

// COMMAND ----------

display(df)

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** How to use `explode()`

// COMMAND ----------

// MAGIC %md The [`explode()`](https://spark.apache.org/docs/latest/api/scala/index.html***REMOVED***org.apache.spark.sql.functions$) function is used to show how to extract nested structures. Plus, it sheds more light when we see how it works alongside `to_json()` and `from_json()` functions, when extracting attributes and values from complex JSON structures. So on occasion, you will want to use `explode()`, alongside `to_json()` and `from_json()` functions. And here's one case where we do.
// MAGIC 
// MAGIC The `explode()` function creates a new row for each element in the given map column. In this case, the map column is `source`. Note that for each key-value in the map, you have a respective Row, in this case four.

// COMMAND ----------

// select from DataFrame with a single entry, and explode its column source, which is Map, with nested structure.
val explodedDF = df.select($"dc_id", explode($"source"))
display(explodedDF)

// COMMAND ----------

// MAGIC %md When you look at the schema, notice that `source` now has been expanded.

// COMMAND ----------

explodedDF.printSchema

// COMMAND ----------

// MAGIC %md A single string aggregated with  complex data types, including a Map. This could be a recording that needs Network Operation Center (NOC) attention 
// MAGIC for action, since both the temperature and C02 levels are alarming.

// COMMAND ----------

// MAGIC %md Let's access the data from our exploded data using Map.

// COMMAND ----------

//case class to denote our desired Scala object
case class DeviceAlert(dcId: String, deviceType:String, ip:String, deviceId:Long, temp:Long, c02_level: Long, lat: Double, lon: Double)
//access all values using getItem() method on value, by providing the "key," which is attribute in our JSON object.
val notifydevicesDS = explodedDF.select( $"dc_id" as "dcId",
                        $"key" as "deviceType",
                        'value.getItem("ip") as 'ip,
                        'value.getItem("id") as 'deviceId,
                        'value.getItem("c02_level") as 'c02_level,
                        'value.getItem("temp") as 'temp,
                        'value.getItem("geo").getItem("lat") as 'lat,                //note embedded level requires yet another level of fetching.
                        'value.getItem("geo").getItem("long") as 'lon)
                        .as[DeviceAlert]  // return as a Dataset

// COMMAND ----------

notifydevicesDS.printSchema

// COMMAND ----------

display(notifydevicesDS)

// COMMAND ----------

// MAGIC %md Suppose as part of our ETL, you have a need to notify or send alerts based on certain alarming conditions. One way is to write a user functtion at iterates over your filtered dataset and sends individual notifications. In other cases you can send the message to Kafka topic as an additional option.
// MAGIC 
// MAGIC Once you have exploded your nested JSON into a simple case class, we can send alerts to a NOC for action. On way to this is using a `foreach()` DataFrame 
// MAGIC method. But to do that we need a high-level function; given a case class it can extract its alarming attributes dispurse an alert. Although this simple example writes to stdout, in a real scenario, you will want to send alerts via SNMP or HTTP POST or some API to a PagerAlert.

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** Function for alert notifications

// COMMAND ----------

// define a Scala Notification Object
object DeviceNOCAlerts {

  def sendTwilio(message: String): Unit = {
    //TODO: fill as necessary
    println("Twilio:" + message)
  }

  def sendSNMP(message: String): Unit = {
    //TODO: fill as necessary
    println("SNMP:" + message)
  }
  
  def sendKafka(message: String): Unit = {
    //TODO: fill as necessary
     println("KAFKA:" + message)
  }
}
def logAlerts(log: java.io.PrintStream = Console.out, deviceAlert: DeviceAlert, alert: String, notify: String ="twilio"): Unit = {
val message = "[***ALERT***: %s; data_center: %s, device_name: %s, temperature: %d; device_id: %d ; ip: %s ; c02: %d]" format(alert, deviceAlert.dcId, deviceAlert.deviceType,deviceAlert.temp, deviceAlert.deviceId, deviceAlert.ip, deviceAlert.c02_level)                                                                                                                                                                                                                                                            
  //default log to Stderr/Stdout
  log.println(message)
  // use an appropriate notification method
  val notifyFunc = notify match {
      case "twilio" => DeviceNOCAlerts.sendTwilio _
      case "snmp" => DeviceNOCAlerts.sendSNMP _
      case "kafka" => DeviceNOCAlerts.sendKafka _
  }
  //send the appropriate alert
  notifyFunc(message)
}

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** Iterate over alert devices and take action

// COMMAND ----------

notifydevicesDS.foreach(d => logAlerts(Console.err, d, "ACTION NEED! HIGH TEPERATURE AND C02 LEVLES", "kafka"))

// COMMAND ----------

// MAGIC %md To view where the messages are logged, go to the **Clusters-->Spark-->Logs**.

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** Send alerts as JSON to Apache Kafka topic

// COMMAND ----------

// MAGIC %md What if you wanted to write these Devices' alerts to a Kafka topic on which a monitoring subscriber is awaiting for events to take action.
// MAGIC 
// MAGIC Here's a simple way to nofity listeners on your Kafka topic: "device_alerts." To read further how to use Structured Streaming in detail with Apache Kafka, read our [part 3 of the blog series on Structure Streaming](https://databricks.com/blog/2017/04/26/processing-data-in-apache-kafka-with-structured-streaming-in-apache-spark-2-2.html).
// MAGIC 
// MAGIC **Note:** See yet another use of `selectExpr()` function we explored above.

// COMMAND ----------

// val deviceAlertQuery = notifydevicesDS
//                        .selectExpr("CAST(dcId AS STRING) AS key", "to_json(struct(*)) AS value")
//                        .writeStream
//                        .format("kafka")
//                        .option("kafka.bootstrap.servers", "host1:port1,host2:port2")
//                        .option("toipic", "device_alerts")
//                        .start()                  

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED*** Nest Device Data

// COMMAND ----------

// MAGIC %md Let's look at another complex real-life data from [Nest's readings](https://developers.nest.com/documentation/api-reference). A Nest devices emits many JSON events to its collector. That collector could be at 
// MAGIC a nearby data center, a neighborhood-central data collector or an aggregator, or it could be a device installed at home, which on regular intervals sends device
// MAGIC readings to a central data center connected via a secured internet connection. For illusration, I have curbed some of the attributes, but it still shows how complex data can be processed—and relevant attributes extracted.
// MAGIC 
// MAGIC Let's define its complicated schema first. At close observation, you will notice it's not dissimilar to the `schema` we defined above, except 
// MAGIC it has not one __map__ but three __maps__: thermostats, cameras, and smoke alarms.

// COMMAND ----------

import org.apache.spark.sql.types._

// a bit longish, nested, and convoluted JSON schema :)
val nestSchema2 = new StructType()
      .add("devices", 
        new StructType()
          .add("thermostats", MapType(StringType,
            new StructType()
              .add("device_id", StringType)
              .add("locale", StringType)
              .add("software_version", StringType)
              .add("structure_id", StringType)
              .add("where_name", StringType)
              .add("last_connection", StringType)
              .add("is_online", BooleanType)
              .add("can_cool", BooleanType)
              .add("can_heat", BooleanType)
              .add("is_using_emergency_heat", BooleanType)
              .add("has_fan", BooleanType)
              .add("fan_timer_active", BooleanType)
              .add("fan_timer_timeout", StringType)
              .add("temperature_scale", StringType)
              .add("target_temperature_f", DoubleType)
              .add("target_temperature_high_f", DoubleType)
              .add("target_temperature_low_f", DoubleType)
              .add("eco_temperature_high_f", DoubleType)
              .add("eco_temperature_low_f", DoubleType)
              .add("away_temperature_high_f", DoubleType)
              .add("away_temperature_low_f", DoubleType)
              .add("hvac_mode", StringType)
              .add("humidity", LongType)
              .add("hvac_state", StringType)
              .add("is_locked", StringType)
              .add("locked_temp_min_f", DoubleType)
              .add("locked_temp_max_f", DoubleType)))
           .add("smoke_co_alarms", MapType(StringType,
             new StructType()
             .add("device_id", StringType)
             .add("locale", StringType)
             .add("software_version", StringType)
             .add("structure_id", StringType)
             .add("where_name", StringType)
             .add("last_connection", StringType)
             .add("is_online", BooleanType)
             .add("battery_health", StringType)
             .add("co_alarm_state", StringType)
             .add("smoke_alarm_state", StringType)
             .add("is_manual_test_active", BooleanType)
             .add("last_manual_test_time", StringType)
             .add("ui_color_state", StringType)))
           .add("cameras", MapType(StringType, 
               new StructType()
                .add("device_id", StringType)
                .add("software_version", StringType)
                .add("structure_id", StringType)
                .add("where_name", StringType)
                .add("is_online", BooleanType)
                .add("is_streaming", BooleanType)
                .add("is_audio_input_enabled", BooleanType)
                .add("last_is_online_change", StringType)
                .add("is_video_history_enabled", BooleanType)
                .add("web_url", StringType)
                .add("app_url", StringType)
                .add("is_public_share_enabled", BooleanType)
                .add("activity_zones",
                  new StructType()
                    .add("name", StringType)
                    .add("id", LongType))
                .add("last_event", StringType))))

// COMMAND ----------

// MAGIC %md By creating a simple Dataset, you can then use all [Dataset methods](https://spark.apache.org/docs/latest/api/scala/index.html***REMOVED***org.apache.spark.sql.Dataset) to do ETL, using utility functions from above: `from_json()`, `to_json()`, `explode()` and `selectExpr()`.

// COMMAND ----------

val nestDataDS2 = Seq("""{
    "devices": {
       "thermostats": {
          "peyiJNo0IldT2YlIVtYaGQ": {
            "device_id": "peyiJNo0IldT2YlIVtYaGQ",
            "locale": "en-US",
            "software_version": "4.0",
            "structure_id": "VqFabWH21nwVyd4RWgJgNb292wa7hG_dUwo2i2SG7j3-BOLY0BA4sw",
            "where_name": "Hallway Upstairs",
            "last_connection": "2016-10-31T23:59:59.000Z",
            "is_online": true,
            "can_cool": true,
            "can_heat": true,
            "is_using_emergency_heat": true,
            "has_fan": true,
            "fan_timer_active": true,
            "fan_timer_timeout": "2016-10-31T23:59:59.000Z",
            "temperature_scale": "F",
            "target_temperature_f": 72,
            "target_temperature_high_f": 80,
            "target_temperature_low_f": 65,
            "eco_temperature_high_f": 80,
            "eco_temperature_low_f": 65,
            "away_temperature_high_f": 80,
            "away_temperature_low_f": 65,
            "hvac_mode": "heat",
            "humidity": 40,
            "hvac_state": "heating",
            "is_locked": true,
            "locked_temp_min_f": 65,
            "locked_temp_max_f": 80
            }
          },
          "smoke_co_alarms": {
            "RTMTKxsQTCxzVcsySOHPxKoF4OyCifrs": {
              "device_id": "RTMTKxsQTCxzVcsySOHPxKoF4OyCifrs",
              "locale": "en-US",
              "software_version": "1.01",
              "structure_id": "VqFabWH21nwVyd4RWgJgNb292wa7hG_dUwo2i2SG7j3-BOLY0BA4sw",
              "where_name": "Jane's Room",
              "last_connection": "2016-10-31T23:59:59.000Z",
              "is_online": true,
              "battery_health": "ok",
              "co_alarm_state": "ok",
              "smoke_alarm_state": "ok",
              "is_manual_test_active": true,
              "last_manual_test_time": "2016-10-31T23:59:59.000Z",
              "ui_color_state": "gray"
              }
            },
         "cameras": {
          "awJo6rH0IldT2YlIVtYaGQ": {
            "device_id": "awJo6rH",
            "software_version": "4.0",
            "structure_id": "VqFabWH21nwVyd4RWgJgNb292wa7hG_dUwo2i2SG7j3-BOLY0BA4sw",
            "where_name": "Foyer",
            "is_online": true,
            "is_streaming": true,
            "is_audio_input_enabled": true,
            "last_is_online_change": "2016-12-29T18:42:00.000Z",
            "is_video_history_enabled": true,
            "web_url": "https://home.nest.com/cameras/device_id?auth=access_token",
            "app_url": "nestmobile://cameras/device_id?auth=access_token",
            "is_public_share_enabled": true,
            "activity_zones": { "name": "Walkway", "id": 244083 },
            "last_event": "2016-10-31T23:59:59.000Z"
            }
          }
        }
       }""").toDS

// COMMAND ----------

// MAGIC %md Let's create a DataFrame from this single nested structure and use all the above utility functions to process and extract relevant attributes

// COMMAND ----------

val nestDF2 = spark                            // spark session 
            .read                             //  get DataFrameReader
            .schema(nestSchema2)             //  use the defined schema above and read format as JSON
            .json(nestDataDS2.rdd)

// COMMAND ----------

display(nestDF2)

// COMMAND ----------

// MAGIC %md Converting the entire JSON object above into a JSON string as above.

// COMMAND ----------

val stringJsonDF = nestDF2.select(to_json(struct($"*"))).toDF("nestDevice")

// COMMAND ----------

stringJsonDF.printSchema

// COMMAND ----------

display(stringJsonDF)

// COMMAND ----------

// MAGIC %md Given the nested JSON object with three maps, you can get fetch individual map as a columnn, and then access attributes from it using `explode()`.

// COMMAND ----------

val mapColumnsDF = nestDF2.select($"devices".getItem("smoke_co_alarms").alias ("smoke_alarms"),
                                  $"devices".getItem("cameras").alias ("cameras"),
                                  $"devices".getItem("thermostats").alias ("thermostats"))

// COMMAND ----------

display(mapColumnsDF)

// COMMAND ----------

val explodedThermostatsDF = mapColumnsDF.select(explode($"thermostats"))
val explodedCamerasDF = mapColumnsDF.select(explode($"cameras"))
//or you could use the original nestDF2 and use the devices.X notation
val explodedSmokedAlarmsDF =  nestDF2.select(explode($"devices.smoke_co_alarms"))

// COMMAND ----------

display(explodedThermostatsDF)

// COMMAND ----------

// MAGIC %md To extract specific individual fields from map, you can use the `getItem()` method.

// COMMAND ----------


val thermostateDF = explodedThermostatsDF.select($"value".getItem("device_id").alias("device_id"), 
                                                 $"value".getItem("locale").alias("locale"),
                                                 $"value".getItem("where_name").alias("location"),
                                                 $"value".getItem("last_connection").alias("last_connected"),
                                                 $"value".getItem("humidity").alias("humidity"),
                                                 $"value".getItem("target_temperature_f").alias("target_temperature_f"),
                                                 $"value".getItem("hvac_mode").alias("mode"),
                                                 $"value".getItem("software_version").alias("version"))

val cameraDF = explodedCamerasDF.select($"value".getItem("device_id").alias("device_id"),
                                        $"value".getItem("where_name").alias("location"),
                                        $"value".getItem("software_version").alias("version"),
                                        $"value".getItem("activity_zones").getItem("name").alias("name"),
                                        $"value".getItem("activity_zones").getItem("id").alias("id"))
                                         
val smokedAlarmsDF = explodedSmokedAlarmsDF.select($"value".getItem("device_id").alias("device_id"),
                                                   $"value".getItem("where_name").alias("location"),
                                                   $"value".getItem("software_version").alias("version"),
                                                   $"value".getItem("last_connection").alias("last_connected"),
                                                   $"value".getItem("battery_health").alias("battery_health"))
                                                  
                                        

// COMMAND ----------

display(thermostateDF)

// COMMAND ----------

display(cameraDF)

// COMMAND ----------

display(smokedAlarmsDF)

// COMMAND ----------

// MAGIC %md Let's join two DataFrames over column `version`. 
// MAGIC  

// COMMAND ----------

val joineDFs = thermostateDF.join(cameraDF, "version")


// COMMAND ----------

display(joineDFs)

// COMMAND ----------

// MAGIC %md ***REMOVED******REMOVED******REMOVED*** Summary
// MAGIC The point of this short tutorial has been to demonstrate the easy use of utility functions to extract JSON attributes from a complex and nested structure. And once you have exploded or flattened or parsed the desired values into respective DataFrames or Datasets, you can as easily extract and query them as you would any DataFrame or Dataset, using respective APIs. Check our [Structured Streaming series part 3](https://databricks.com/blog/2017/04/26/processing-data-in-apache-kafka-with-structured-streaming-in-apache-spark-2-2.html), where we show how you can read Nest device logs from Apache Kafka and do some ETL on them.