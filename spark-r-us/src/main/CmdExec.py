df = spark.read.format("json").load("/databricks-datasets/iot/iot_devices.json")
result = df.toJSON().take(10)
result