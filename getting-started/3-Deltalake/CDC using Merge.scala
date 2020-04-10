// Databricks notebook source
// MAGIC %md 
// MAGIC Change data capture (CDC) is a type of workload where you want to merge the reported row changes from another database into your database. 
// MAGIC Change data come in the form of (key, key deleted or not, updated value if not deleted, timestamp).
// MAGIC 
// MAGIC You can update a target Delta table with a series of ordered row changes using MERGE and its extended syntax support. 
// MAGIC This notebook illustrates change data capture using the extended MERGE syntax (i.e. support for delete, conditions in MATCHED and NOT MATCHED clauses). 

// COMMAND ----------

case class Data(key: String, value: String)

// Changes in Data defined as follows
// newValue = new value for key, or null if the key was deleted
// deleted = whether the key was deleted
// time = timestamp needed for ordering the changes, useful collapsing multiple changes to the same key by finding the latest effective change
case class ChangeData(key: String, newValue: String, deleted: Boolean, time: Long) {
  assert(newValue != null ^ deleted)
}

// COMMAND ----------

// MAGIC %md **Target Delta table**
// MAGIC 
// MAGIC This is the table where we want to apply all the change data.

// COMMAND ----------

sql("drop table if exists target")

val target = Seq(
  Data("a", "0"),
  Data("b", "1"),
  Data("c", "2"),
  Data("d", "3")
).toDF().write.format("delta").mode("overwrite").saveAsTable("target")

display(table("target").orderBy("key"))

// COMMAND ----------

// MAGIC %md **Change Data**
// MAGIC 
// MAGIC This table contains all the changes that need to applied. Note that the same key may have been changed multiple timess. 
// MAGIC Multiple changes are ordered by their timestamp.

// COMMAND ----------

val changeDataSource = Seq(
  ChangeData("a", "10", deleted = false, time = 0),
  ChangeData("a", null, deleted = true, time = 1),   // a was updated and then deleted
  
  ChangeData("b", null, deleted = true, time = 2),   // b was just deleted once
  
  ChangeData("c", null, deleted = true, time = 3),   // c was deleted and then updated twice
  ChangeData("c", "20", deleted = false, time = 4),
  ChangeData("c", "200", deleted = false, time = 5)
).toDF().createOrReplaceTempView("changes")

display(table("changes").orderBy("key"))

// COMMAND ----------

// MAGIC %md **MERGE query to apply the changes**
// MAGIC 
// MAGIC This MERGE query does the following
// MAGIC - Figures out the latest change for every key based on the maximum timestamp using subquery
// MAGIC - Merges the latest change for each key into the target table.

// COMMAND ----------

// DBTITLE 1,SQL example
// MAGIC %sql 
// MAGIC -- ========================================
// MAGIC -- Merge SQL API is available since DBR 5.1
// MAGIC -- ========================================
// MAGIC 
// MAGIC MERGE INTO target t
// MAGIC USING (
// MAGIC   -- Find the latest change for each key based on the timestamp
// MAGIC   SELECT key, latest.newValue as newValue, latest.deleted as deleted FROM (    
// MAGIC     -- Note: For nested structs, max on struct is computed as 
// MAGIC     -- max on first struct field, if equal fall back to second fields, and so on.
// MAGIC     SELECT key, max(struct(time, newValue, deleted)) as latest FROM changes GROUP BY key
// MAGIC   )
// MAGIC ) s
// MAGIC ON s.key = t.key
// MAGIC WHEN MATCHED AND s.deleted = true THEN DELETE
// MAGIC WHEN MATCHED THEN UPDATE SET key = s.key, value = s.newValue
// MAGIC WHEN NOT MATCHED AND s.deleted = false THEN INSERT (key, value) VALUES (key, newValue)

// COMMAND ----------

// DBTITLE 1,Scala example
// MAGIC %scala 
// MAGIC 
// MAGIC // ==========================================
// MAGIC // Merge Scala API is available since DBR 6.0
// MAGIC // ==========================================
// MAGIC 
// MAGIC import io.delta.tables._
// MAGIC import org.apache.spark.sql.functions._
// MAGIC 
// MAGIC val deltaTable = DeltaTable.forName("target")
// MAGIC 
// MAGIC // DataFrame with changes having following columns
// MAGIC // - key: key of the change
// MAGIC // - time: time of change for ordering between changes (can replaced by other ordering id)
// MAGIC // - newValue: updated or inserted value if key was not deleted
// MAGIC // - deleted: true if the key was deleted, false if the key was inserted or updated
// MAGIC val changesDF = spark.table("changes")
// MAGIC 
// MAGIC // Find the latest change for each key based on the timestamp
// MAGIC // Note: For nested structs, max on struct is computed as
// MAGIC // max on first struct field, if equal fall back to second fields, and so on.
// MAGIC val latestChangeForEachKey = changesDF
// MAGIC   .selectExpr("key", "struct(time, newValue, deleted) as otherCols" )
// MAGIC   .groupBy("key")
// MAGIC   .agg(max("otherCols").as("latest"))
// MAGIC   .selectExpr("key", "latest.*")
// MAGIC 
// MAGIC latestChangeForEachKey.show() // shows the latest change for each key
// MAGIC 
// MAGIC deltaTable.as("t")
// MAGIC   .merge(
// MAGIC     latestChangeForEachKey.as("s"),
// MAGIC     "s.key = t.key")
// MAGIC   .whenMatched("s.deleted = true")
// MAGIC   .delete()
// MAGIC   .whenMatched()
// MAGIC   .updateExpr(Map("key" -> "s.key", "value" -> "s.newValue"))
// MAGIC   .whenNotMatched("s.deleted = false")
// MAGIC   .insertExpr(Map("key" -> "s.key", "value" -> "s.newValue"))
// MAGIC   .execute()

// COMMAND ----------

// MAGIC %md **Updated target table**
// MAGIC 
// MAGIC Keys "a" and "b" were effectively deleted, "c" was updated, and "d" remains unchanged

// COMMAND ----------

display(table("target").orderBy("key"))