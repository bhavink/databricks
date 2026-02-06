# Bronze Layer: HL7v2 VXU Messages (Vaccinations)

dbutils.import_notebook("utilities.healthcare_connector")

import dlt
from pyspark.sql.functions import col, explode

STORAGE_PATH = spark.conf.get("healthcare.storage_path", "/Volumes/main/default/healthcare_data/hl7v2")
FILE_PATTERN = spark.conf.get("healthcare.file_pattern", "*.hl7")
ERROR_HANDLING = spark.conf.get("healthcare.error_handling", "skip")


@dlt.table(
    name="bronze_hl7v2_vxu",
    comment="Bronze layer for HL7v2 VXU (Vaccination) messages",
    table_properties={"quality": "bronze"},
)
@dlt.expect_or_drop("valid_message_type", "message_type = 'VXU'")
@dlt.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
def bronze_hl7v2_vxu():
    connector = HealthcareConnector({
        "storage_path": STORAGE_PATH,
        "file_pattern": FILE_PATTERN,
    })
    
    records, _ = connector.read_table("vxu_messages", None, {"error_handling": ERROR_HANDLING})
    records_list = list(records)
    
    if not records_list:
        return spark.createDataFrame([], SCHEMAS["vxu_messages"])
    
    return spark.createDataFrame(records_list, SCHEMAS["vxu_messages"])


@dlt.table(
    name="bronze_hl7v2_vxu_vaccinations",
    comment="Flattened vaccination records from VXU messages",
    table_properties={"quality": "bronze"},
)
def bronze_hl7v2_vxu_vaccinations():
    return (
        dlt.read("bronze_hl7v2_vxu")
        .filter(col("vaccinations").isNotNull())
        .select(
            col("message_control_id"),
            col("message_datetime"),
            col("patient_id"),
            col("patient_name_family"),
            col("patient_name_given"),
            col("date_of_birth"),
            col("gender"),
            explode(col("vaccinations")).alias("vax"),
        )
        .select(
            col("message_control_id"),
            col("message_datetime"),
            col("patient_id"),
            col("patient_name_family"),
            col("patient_name_given"),
            col("date_of_birth"),
            col("gender"),
            col("vax.administration_start_datetime").alias("administration_datetime"),
            col("vax.vaccine_code").alias("cvx_code"),
            col("vax.vaccine_name").alias("vaccine_name"),
            col("vax.vaccine_coding_system").alias("coding_system"),
            col("vax.administered_amount").alias("dose_amount"),
            col("vax.administered_units").alias("dose_units"),
            col("vax.manufacturer_code").alias("mvx_code"),
            col("vax.manufacturer_name").alias("manufacturer_name"),
            col("vax.lot_number").alias("lot_number"),
            col("vax.expiration_date").alias("expiration_date"),
            col("vax.completion_status").alias("completion_status"),
            col("vax.route_code").alias("route_code"),
            col("vax.route_name").alias("route_name"),
            col("vax.site_code").alias("site_code"),
            col("vax.site_name").alias("site_name"),
        )
    )
