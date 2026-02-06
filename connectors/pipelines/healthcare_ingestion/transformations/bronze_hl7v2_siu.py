# Bronze Layer: HL7v2 SIU Messages (Scheduling)

dbutils.import_notebook("utilities.healthcare_connector")

import dlt
from pyspark.sql.functions import col, explode

STORAGE_PATH = spark.conf.get("healthcare.storage_path", "/Volumes/main/default/healthcare_data/hl7v2")
FILE_PATTERN = spark.conf.get("healthcare.file_pattern", "*.hl7")
ERROR_HANDLING = spark.conf.get("healthcare.error_handling", "skip")


@dlt.table(
    name="bronze_hl7v2_siu",
    comment="Bronze layer for HL7v2 SIU (Scheduling) messages",
    table_properties={"quality": "bronze"},
)
@dlt.expect_or_drop("valid_message_type", "message_type = 'SIU'")
@dlt.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
def bronze_hl7v2_siu():
    connector = HealthcareConnector({
        "storage_path": STORAGE_PATH,
        "file_pattern": FILE_PATTERN,
    })
    
    records, _ = connector.read_table("siu_messages", None, {"error_handling": ERROR_HANDLING})
    records_list = list(records)
    
    if not records_list:
        return spark.createDataFrame([], SCHEMAS["siu_messages"])
    
    return spark.createDataFrame(records_list, SCHEMAS["siu_messages"])


@dlt.table(
    name="bronze_hl7v2_siu_resources",
    comment="Flattened appointment resources from SIU messages",
    table_properties={"quality": "bronze"},
)
def bronze_hl7v2_siu_resources():
    return (
        dlt.read("bronze_hl7v2_siu")
        .filter(col("appointment_resources").isNotNull())
        .select(
            col("message_control_id"),
            col("placer_appointment_id"),
            col("filler_appointment_id"),
            col("appointment_start_datetime"),
            col("patient_id"),
            explode(col("appointment_resources")).alias("resource"),
        )
        .select(
            col("message_control_id"),
            col("placer_appointment_id"),
            col("filler_appointment_id"),
            col("appointment_start_datetime"),
            col("patient_id"),
            col("resource.resource_type").alias("resource_type"),
            col("resource.set_id").alias("set_id"),
            col("resource.universal_service_id").alias("service_id"),
            col("resource.personnel_id").alias("personnel_id"),
            col("resource.location_id").alias("location_id"),
            col("resource.resource_role").alias("resource_role"),
            col("resource.start_datetime").alias("resource_start_datetime"),
            col("resource.duration").alias("duration"),
        )
    )
