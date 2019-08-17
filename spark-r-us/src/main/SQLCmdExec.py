result = spark.sql("select * from bk.delta limit 3")
result.take(3)
