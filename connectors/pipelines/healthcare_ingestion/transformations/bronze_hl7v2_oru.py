# Bronze Layer: HL7v2 ORU Messages (Results)

dbutils.import_notebook("utilities.healthcare_connector")

import dlt
from pyspark.sql.functions import col, explode

STORAGE_PATH = spark.conf.get("healthcare.storage_path", "/Volumes/main/default/healthcare_data/hl7v2")
FILE_PATTERN = spark.conf.get("healthcare.file_pattern", "*.hl7")
ERROR_HANDLING = spark.conf.get("healthcare.error_handling", "skip")


@dlt.table(
    name="bronze_hl7v2_oru",
    comment="Bronze layer for HL7v2 ORU (Result) messages",
    table_properties={"quality": "bronze"},
)
@dlt.expect_or_drop("valid_message_type", "message_type = 'ORU'")
@dlt.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
def bronze_hl7v2_oru():
    connector = HealthcareConnector({
        "storage_path": STORAGE_PATH,
        "file_pattern": FILE_PATTERN,
    })
    
    records, _ = connector.read_table("oru_messages", None, {"error_handling": ERROR_HANDLING})
    records_list = list(records)
    
    if not records_list:
        return spark.createDataFrame([], SCHEMAS["oru_messages"])
    
    return spark.createDataFrame(records_list, SCHEMAS["oru_messages"])


@dlt.table(
    name="bronze_hl7v2_oru_observations",
    comment="Flattened OBX observations from ORU messages",
    table_properties={"quality": "bronze"},
)
def bronze_hl7v2_oru_observations():
    return (
        dlt.read("bronze_hl7v2_oru")
        .filter(col("observations").isNotNull())
        .select(
            col("message_control_id"),
            col("message_datetime"),
            col("patient_id"),
            col("universal_service_id"),
            explode(col("observations")).alias("obs"),
        )
        .select(
            col("message_control_id"),
            col("message_datetime"),
            col("patient_id"),
            col("universal_service_id"),
            col("obs.set_id").alias("set_id"),
            col("obs.value_type").alias("value_type"),
            col("obs.observation_id").alias("observation_id"),
            col("obs.observation_value").alias("observation_value"),
            col("obs.units").alias("units"),
            col("obs.reference_range").alias("reference_range"),
            col("obs.abnormal_flags").alias("abnormal_flags"),
            col("obs.result_status").alias("result_status"),
        )
    )
