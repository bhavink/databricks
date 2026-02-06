# Bronze Layer: HL7v2 ADT Messages (Admit/Discharge/Transfer)

dbutils.import_notebook("utilities.healthcare_connector")

import dlt
from pyspark.sql.functions import col

STORAGE_PATH = spark.conf.get("healthcare.storage_path", "/Volumes/main/default/healthcare_data/hl7v2")
FILE_PATTERN = spark.conf.get("healthcare.file_pattern", "*.hl7")
ERROR_HANDLING = spark.conf.get("healthcare.error_handling", "skip")


@dlt.table(
    name="bronze_hl7v2_adt",
    comment="Bronze layer for HL7v2 ADT (Admit/Discharge/Transfer) messages",
    table_properties={"quality": "bronze"},
)
@dlt.expect_or_drop("valid_message_type", "message_type = 'ADT'")
@dlt.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
def bronze_hl7v2_adt():
    connector = HealthcareConnector({
        "storage_path": STORAGE_PATH,
        "file_pattern": FILE_PATTERN,
    })
    
    records, _ = connector.read_table("adt_messages", None, {"error_handling": ERROR_HANDLING})
    records_list = list(records)
    
    if not records_list:
        return spark.createDataFrame([], SCHEMAS["adt_messages"])
    
    return spark.createDataFrame(records_list, SCHEMAS["adt_messages"])
