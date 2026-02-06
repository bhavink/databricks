# Databricks notebook source
# MAGIC %md
# MAGIC # HL7v2 Data Exploration
# MAGIC 
# MAGIC Ad-hoc exploration of ingested HL7v2 data from the healthcare pipeline.

# COMMAND ----------

# MAGIC %md
# MAGIC ## View Bronze Tables

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ADT Messages (Admit/Discharge/Transfer)
# MAGIC SELECT 
# MAGIC   message_control_id,
# MAGIC   trigger_event,
# MAGIC   patient_id,
# MAGIC   patient_name_family,
# MAGIC   patient_name_given,
# MAGIC   event_type_code,
# MAGIC   assigned_location,
# MAGIC   _ingested_at
# MAGIC FROM bronze_hl7v2_adt
# MAGIC ORDER BY _ingested_at DESC
# MAGIC LIMIT 100

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ORM Messages (Orders)
# MAGIC SELECT 
# MAGIC   message_control_id,
# MAGIC   patient_id,
# MAGIC   order_control,
# MAGIC   order_id,
# MAGIC   order_status,
# MAGIC   universal_service_id,
# MAGIC   _ingested_at
# MAGIC FROM bronze_hl7v2_orm
# MAGIC ORDER BY _ingested_at DESC
# MAGIC LIMIT 100

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ORU Messages (Results)
# MAGIC SELECT 
# MAGIC   message_control_id,
# MAGIC   patient_id,
# MAGIC   universal_service_id,
# MAGIC   size(observations) as num_observations,
# MAGIC   _ingested_at
# MAGIC FROM bronze_hl7v2_oru
# MAGIC ORDER BY _ingested_at DESC
# MAGIC LIMIT 100

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Flattened Observations
# MAGIC SELECT 
# MAGIC   message_control_id,
# MAGIC   patient_id,
# MAGIC   observation_id,
# MAGIC   observation_value,
# MAGIC   units,
# MAGIC   reference_range,
# MAGIC   abnormal_flags
# MAGIC FROM bronze_hl7v2_oru_observations
# MAGIC WHERE abnormal_flags IS NOT NULL AND abnormal_flags != ''
# MAGIC LIMIT 100

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Summary

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Message counts by type
# MAGIC SELECT 'ADT' as message_type, COUNT(*) as count FROM bronze_hl7v2_adt
# MAGIC UNION ALL
# MAGIC SELECT 'ORM' as message_type, COUNT(*) as count FROM bronze_hl7v2_orm
# MAGIC UNION ALL
# MAGIC SELECT 'ORU' as message_type, COUNT(*) as count FROM bronze_hl7v2_oru

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ADT events by type
# MAGIC SELECT 
# MAGIC   trigger_event,
# MAGIC   COUNT(*) as count
# MAGIC FROM bronze_hl7v2_adt
# MAGIC GROUP BY trigger_event
# MAGIC ORDER BY count DESC

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Abnormal lab results
# MAGIC SELECT 
# MAGIC   abnormal_flags,
# MAGIC   COUNT(*) as count
# MAGIC FROM bronze_hl7v2_oru_observations
# MAGIC WHERE abnormal_flags IS NOT NULL AND abnormal_flags != ''
# MAGIC GROUP BY abnormal_flags
# MAGIC ORDER BY count DESC

# COMMAND ----------

# MAGIC %md
# MAGIC ## Source File Analysis

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Messages per source file (batch file detection)
# MAGIC SELECT 
# MAGIC   _source_file,
# MAGIC   COUNT(*) as messages_in_file,
# MAGIC   COLLECT_SET(message_type) as message_types
# MAGIC FROM (
# MAGIC   SELECT _source_file, 'ADT' as message_type FROM bronze_hl7v2_adt
# MAGIC   UNION ALL
# MAGIC   SELECT _source_file, 'ORM' as message_type FROM bronze_hl7v2_orm
# MAGIC   UNION ALL
# MAGIC   SELECT _source_file, 'ORU' as message_type FROM bronze_hl7v2_oru
# MAGIC )
# MAGIC GROUP BY _source_file
# MAGIC HAVING COUNT(*) > 1
# MAGIC ORDER BY messages_in_file DESC
