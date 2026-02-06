"""
HL7v2 Schema Definitions for Spark Declarative Pipelines.

Defines PySpark schemas for all supported HL7v2 message types:
- ADT: Admit/Discharge/Transfer (~40% of traffic)
- ORU: Lab Results (~30%)
- ORM: Orders (~15%)
- SIU: Scheduling (~8%)
- VXU: Vaccinations (~2%)

Usage:
    from utilities.hl7v2_schemas import SCHEMAS, get_schema
    
    schema = get_schema("ADT")
"""

from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    ArrayType,
)


# ---------------------------------------------------------------------------
# Reusable Nested Schemas
# ---------------------------------------------------------------------------

OBX_SCHEMA = ArrayType(StructType([
    StructField("set_id", StringType(), nullable=True),
    StructField("value_type", StringType(), nullable=True),
    StructField("observation_id", StringType(), nullable=True),
    StructField("observation_value", StringType(), nullable=True),
    StructField("units", StringType(), nullable=True),
    StructField("reference_range", StringType(), nullable=True),
    StructField("abnormal_flags", StringType(), nullable=True),
    StructField("result_status", StringType(), nullable=True),
]))

APPOINTMENT_RESOURCE_SCHEMA = ArrayType(StructType([
    StructField("resource_type", StringType(), nullable=True),
    StructField("set_id", StringType(), nullable=True),
    StructField("universal_service_id", StringType(), nullable=True),
    StructField("personnel_id", StringType(), nullable=True),
    StructField("location_id", StringType(), nullable=True),
    StructField("resource_role", StringType(), nullable=True),
    StructField("start_datetime", StringType(), nullable=True),
    StructField("duration", StringType(), nullable=True),
]))

VACCINATION_SCHEMA = ArrayType(StructType([
    StructField("order_control", StringType(), nullable=True),
    StructField("placer_order_number", StringType(), nullable=True),
    StructField("filler_order_number", StringType(), nullable=True),
    StructField("administration_start_datetime", StringType(), nullable=True),
    StructField("vaccine_code", StringType(), nullable=True),
    StructField("vaccine_name", StringType(), nullable=True),
    StructField("vaccine_coding_system", StringType(), nullable=True),
    StructField("administered_amount", StringType(), nullable=True),
    StructField("administered_units", StringType(), nullable=True),
    StructField("manufacturer_code", StringType(), nullable=True),
    StructField("manufacturer_name", StringType(), nullable=True),
    StructField("lot_number", StringType(), nullable=True),
    StructField("expiration_date", StringType(), nullable=True),
    StructField("completion_status", StringType(), nullable=True),
    StructField("route_code", StringType(), nullable=True),
    StructField("route_name", StringType(), nullable=True),
    StructField("site_code", StringType(), nullable=True),
    StructField("site_name", StringType(), nullable=True),
]))

VXU_OBX_SCHEMA = ArrayType(StructType([
    StructField("set_id", StringType(), nullable=True),
    StructField("value_type", StringType(), nullable=True),
    StructField("observation_id", StringType(), nullable=True),
    StructField("observation_value", StringType(), nullable=True),
    StructField("units", StringType(), nullable=True),
    StructField("observation_result_status", StringType(), nullable=True),
]))


# ---------------------------------------------------------------------------
# Message Type Schemas
# ---------------------------------------------------------------------------

SCHEMAS = {
    "ADT": StructType([
        StructField("message_control_id", StringType(), nullable=False),
        StructField("message_type", StringType(), nullable=False),
        StructField("trigger_event", StringType(), nullable=True),
        StructField("sending_application", StringType(), nullable=True),
        StructField("sending_facility", StringType(), nullable=True),
        StructField("message_datetime", StringType(), nullable=True),
        StructField("patient_id", StringType(), nullable=True),
        StructField("patient_name_family", StringType(), nullable=True),
        StructField("patient_name_given", StringType(), nullable=True),
        StructField("date_of_birth", StringType(), nullable=True),
        StructField("gender", StringType(), nullable=True),
        StructField("event_type_code", StringType(), nullable=True),
        StructField("event_datetime", StringType(), nullable=True),
        StructField("patient_class", StringType(), nullable=True),
        StructField("assigned_location", StringType(), nullable=True),
        StructField("admission_type", StringType(), nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),
    
    "ORM": StructType([
        StructField("message_control_id", StringType(), nullable=False),
        StructField("message_type", StringType(), nullable=False),
        StructField("trigger_event", StringType(), nullable=True),
        StructField("sending_application", StringType(), nullable=True),
        StructField("sending_facility", StringType(), nullable=True),
        StructField("message_datetime", StringType(), nullable=True),
        StructField("patient_id", StringType(), nullable=True),
        StructField("patient_name_family", StringType(), nullable=True),
        StructField("patient_name_given", StringType(), nullable=True),
        StructField("order_control", StringType(), nullable=True),
        StructField("order_id", StringType(), nullable=True),
        StructField("filler_order_number", StringType(), nullable=True),
        StructField("order_status", StringType(), nullable=True),
        StructField("placer_order_number", StringType(), nullable=True),
        StructField("universal_service_id", StringType(), nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),
    
    "ORU": StructType([
        StructField("message_control_id", StringType(), nullable=False),
        StructField("message_type", StringType(), nullable=False),
        StructField("trigger_event", StringType(), nullable=True),
        StructField("sending_application", StringType(), nullable=True),
        StructField("sending_facility", StringType(), nullable=True),
        StructField("message_datetime", StringType(), nullable=True),
        StructField("patient_id", StringType(), nullable=True),
        StructField("patient_name_family", StringType(), nullable=True),
        StructField("patient_name_given", StringType(), nullable=True),
        StructField("placer_order_number", StringType(), nullable=True),
        StructField("filler_order_number", StringType(), nullable=True),
        StructField("universal_service_id", StringType(), nullable=True),
        StructField("observations", OBX_SCHEMA, nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),
    
    "SIU": StructType([
        StructField("message_control_id", StringType(), nullable=False),
        StructField("message_type", StringType(), nullable=False),
        StructField("trigger_event", StringType(), nullable=True),
        StructField("sending_application", StringType(), nullable=True),
        StructField("sending_facility", StringType(), nullable=True),
        StructField("message_datetime", StringType(), nullable=True),
        StructField("patient_id", StringType(), nullable=True),
        StructField("patient_name_family", StringType(), nullable=True),
        StructField("patient_name_given", StringType(), nullable=True),
        StructField("placer_appointment_id", StringType(), nullable=True),
        StructField("filler_appointment_id", StringType(), nullable=True),
        StructField("schedule_id", StringType(), nullable=True),
        StructField("event_reason", StringType(), nullable=True),
        StructField("appointment_reason", StringType(), nullable=True),
        StructField("appointment_type", StringType(), nullable=True),
        StructField("appointment_duration", StringType(), nullable=True),
        StructField("appointment_start_datetime", StringType(), nullable=True),
        StructField("appointment_end_datetime", StringType(), nullable=True),
        StructField("filler_status_code", StringType(), nullable=True),
        StructField("appointment_resources", APPOINTMENT_RESOURCE_SCHEMA, nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),
    
    "VXU": StructType([
        StructField("message_control_id", StringType(), nullable=False),
        StructField("message_type", StringType(), nullable=False),
        StructField("trigger_event", StringType(), nullable=True),
        StructField("sending_application", StringType(), nullable=True),
        StructField("sending_facility", StringType(), nullable=True),
        StructField("message_datetime", StringType(), nullable=True),
        StructField("patient_id", StringType(), nullable=True),
        StructField("patient_name_family", StringType(), nullable=True),
        StructField("patient_name_given", StringType(), nullable=True),
        StructField("date_of_birth", StringType(), nullable=True),
        StructField("gender", StringType(), nullable=True),
        StructField("vaccinations", VACCINATION_SCHEMA, nullable=True),
        StructField("observations", VXU_OBX_SCHEMA, nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),
}


# Parse result schema (used by UDF)
PARSE_RESULT_SCHEMA = StructType([
    StructField("success", StringType(), nullable=False),
    StructField("data", StringType(), nullable=True),
    StructField("error", StringType(), nullable=True),
    StructField("msg_type", StringType(), nullable=True),
])


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_schema(message_type: str) -> StructType:
    """
    Get the schema for a specific message type.
    
    Args:
        message_type: One of "ADT", "ORM", "ORU", "SIU", "VXU"
        
    Returns:
        PySpark StructType schema
        
    Raises:
        ValueError: If message type is not supported
    """
    msg_type = message_type.upper()
    if msg_type not in SCHEMAS:
        raise ValueError(f"Unsupported message type: {message_type}. "
                        f"Supported types: {list(SCHEMAS.keys())}")
    return SCHEMAS[msg_type]


def get_json_schema(message_type: str) -> StructType:
    """
    Get schema for JSON parsing (excludes _source_file which is added later).
    
    Args:
        message_type: One of "ADT", "ORM", "ORU", "SIU", "VXU"
        
    Returns:
        PySpark StructType schema without _source_file field
    """
    full_schema = get_schema(message_type)
    return StructType([f for f in full_schema.fields if f.name != "_source_file"])


# Supported message types (for iteration)
MESSAGE_TYPES = list(SCHEMAS.keys())
