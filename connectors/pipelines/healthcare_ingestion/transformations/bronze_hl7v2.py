# Healthcare HL7v2 Bronze Ingestion Pipeline
# ============================================
#
# Spark Declarative Pipeline (SDP) for HL7v2 message ingestion.
# Uses Auto Loader for streaming file ingestion from UC Volumes.
#
# Message Types (~95% coverage):
# - ADT: Admit/Discharge/Transfer (~40%)
# - ORU: Lab Results (~30%)
# - ORM: Orders (~15%)
# - SIU: Scheduling (~8%)
# - VXU: Vaccinations (~2%)

import dlt
from pyspark.sql.functions import col, udf, explode, from_json
from pyspark.sql.types import ArrayType, StructType, StructField, StringType

# Add pipeline root to path for utility imports
import sys
sys.path.append("/Workspace/Users/bhavin.kukadia@databricks.com/healthcare_ingestion")

# Import schemas from utilities (driver-side import)
from utilities.hl7v2_schemas import (
    SCHEMAS,
    MESSAGE_TYPES,
    get_json_schema,
    PARSE_RESULT_SCHEMA,
)

# ---------------------------------------------------------------------------
# Pipeline Configuration (from pipeline settings)
# ---------------------------------------------------------------------------
STORAGE_PATH = spark.conf.get("healthcare.storage_path", "/Volumes/main/default/healthcare_data/hl7v2")
FILE_PATTERN = spark.conf.get("healthcare.file_pattern", "*.hl7")
ERROR_HANDLING = spark.conf.get("healthcare.error_handling", "skip")
BATCH_SIZE = int(spark.conf.get("healthcare.batch_size", "1000"))


# ---------------------------------------------------------------------------
# HL7v2 Parsing Functions (inlined for UDF - executors can't import workspace files)
# ---------------------------------------------------------------------------

def split_hl7_batch(text: str):
    """Split batch file into individual HL7v2 messages."""
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    messages, current = [], []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("MSH"):
            if current:
                messages.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        messages.append("\n".join(current))
    return messages


def parse_hl7v2_message(msg: str):
    """Parse a single HL7v2 message into a dictionary."""
    if not msg or not msg.strip():
        return None
    msg = msg.replace("\r\n", "\n").replace("\r", "\n")
    lines = [l for l in msg.strip().split("\n") if l]
    if not lines or not lines[0].startswith("MSH"):
        return None
    
    result = {}
    
    # Parse MSH segment (header)
    msh = lines[0].split("|")
    result["sending_application"] = msh[2] if len(msh) > 2 else ""
    result["sending_facility"] = msh[3] if len(msh) > 3 else ""
    result["message_datetime"] = msh[6] if len(msh) > 6 else ""
    msg_type_field = msh[8] if len(msh) > 8 else ""
    result["message_type"] = msg_type_field.split("^")[0] if msg_type_field else ""
    result["trigger_event"] = msg_type_field.split("^")[1] if "^" in msg_type_field else ""
    result["message_control_id"] = msh[9] if len(msh) > 9 else ""
    
    # Parse PID segment (patient identification)
    for line in lines:
        if line.startswith("PID"):
            pf = line.split("|")
            pid_field = pf[3] if len(pf) > 3 else ""
            result["patient_id"] = pid_field.split("^")[0] if pid_field else ""
            name_field = pf[5] if len(pf) > 5 else ""
            np = name_field.split("^")
            result["patient_name_family"] = np[0] if np else ""
            result["patient_name_given"] = np[1] if len(np) > 1 else ""
            result["date_of_birth"] = pf[7] if len(pf) > 7 else ""
            result["gender"] = pf[8] if len(pf) > 8 else ""
            break
    
    mt = result.get("message_type", "")
    
    # Parse message-type specific segments
    if mt == "ADT":
        for line in lines:
            if line.startswith("EVN"):
                ef = line.split("|")
                result["event_type_code"] = ef[1] if len(ef) > 1 else ""
                result["event_datetime"] = ef[2] if len(ef) > 2 else ""
            elif line.startswith("PV1"):
                pf = line.split("|")
                result["patient_class"] = pf[2] if len(pf) > 2 else ""
                result["assigned_location"] = pf[3] if len(pf) > 3 else ""
                result["admission_type"] = pf[4] if len(pf) > 4 else ""
    
    elif mt == "ORM":
        for line in lines:
            if line.startswith("ORC"):
                of = line.split("|")
                result["order_control"] = of[1] if len(of) > 1 else ""
                result["order_id"] = of[2] if len(of) > 2 else ""
                result["filler_order_number"] = of[3] if len(of) > 3 else ""
                result["order_status"] = of[5] if len(of) > 5 else ""
            elif line.startswith("OBR"):
                bf = line.split("|")
                result["placer_order_number"] = bf[2] if len(bf) > 2 else ""
                result["universal_service_id"] = bf[4] if len(bf) > 4 else ""
    
    elif mt == "ORU":
        obs = []
        for line in lines:
            if line.startswith("OBR"):
                bf = line.split("|")
                result["placer_order_number"] = bf[2] if len(bf) > 2 else ""
                result["filler_order_number"] = bf[3] if len(bf) > 3 else ""
                result["universal_service_id"] = bf[4] if len(bf) > 4 else ""
            elif line.startswith("OBX"):
                xf = line.split("|")
                obs.append({
                    "set_id": xf[1] if len(xf) > 1 else "",
                    "value_type": xf[2] if len(xf) > 2 else "",
                    "observation_id": xf[3] if len(xf) > 3 else "",
                    "observation_value": xf[5] if len(xf) > 5 else "",
                    "units": xf[6] if len(xf) > 6 else "",
                    "reference_range": xf[7] if len(xf) > 7 else "",
                    "abnormal_flags": xf[8] if len(xf) > 8 else "",
                    "result_status": xf[11] if len(xf) > 11 else "",
                })
        result["observations"] = obs
    
    elif mt == "SIU":
        resources = []
        for line in lines:
            if line.startswith("SCH"):
                sf = line.split("|")
                result["placer_appointment_id"] = sf[1] if len(sf) > 1 else ""
                result["filler_appointment_id"] = sf[2] if len(sf) > 2 else ""
                result["schedule_id"] = sf[5] if len(sf) > 5 else ""
                result["event_reason"] = sf[6] if len(sf) > 6 else ""
                result["appointment_reason"] = sf[7] if len(sf) > 7 else ""
                result["appointment_type"] = sf[8] if len(sf) > 8 else ""
                result["appointment_duration"] = sf[9] if len(sf) > 9 else ""
                timing = sf[11] if len(sf) > 11 else ""
                tp = timing.split("^")
                result["appointment_start_datetime"] = tp[0] if tp else ""
                result["appointment_end_datetime"] = tp[1] if len(tp) > 1 else ""
                result["filler_status_code"] = sf[25] if len(sf) > 25 else ""
            elif line.startswith("AIS"):
                af = line.split("|")
                resources.append({
                    "resource_type": "service",
                    "set_id": af[1] if len(af) > 1 else "",
                    "universal_service_id": af[3] if len(af) > 3 else "",
                    "personnel_id": None,
                    "location_id": None,
                    "resource_role": None,
                    "start_datetime": af[4] if len(af) > 4 else "",
                    "duration": af[7] if len(af) > 7 else "",
                })
            elif line.startswith("AIP"):
                af = line.split("|")
                resources.append({
                    "resource_type": "personnel",
                    "set_id": af[1] if len(af) > 1 else "",
                    "universal_service_id": None,
                    "personnel_id": af[3] if len(af) > 3 else "",
                    "location_id": None,
                    "resource_role": af[4] if len(af) > 4 else "",
                    "start_datetime": af[6] if len(af) > 6 else "",
                    "duration": af[8] if len(af) > 8 else "",
                })
            elif line.startswith("AIL"):
                af = line.split("|")
                resources.append({
                    "resource_type": "location",
                    "set_id": af[1] if len(af) > 1 else "",
                    "universal_service_id": None,
                    "personnel_id": None,
                    "location_id": af[3] if len(af) > 3 else "",
                    "resource_role": af[4] if len(af) > 4 else "",
                    "start_datetime": af[6] if len(af) > 6 else "",
                    "duration": af[8] if len(af) > 8 else "",
                })
        result["appointment_resources"] = resources
    
    elif mt == "VXU":
        vaxes, vax_obs, cur = [], [], None
        for line in lines:
            if line.startswith("ORC"):
                if cur:
                    vaxes.append(cur)
                of = line.split("|")
                cur = {
                    "order_control": of[1] if len(of) > 1 else "",
                    "placer_order_number": of[2] if len(of) > 2 else "",
                    "filler_order_number": of[3] if len(of) > 3 else "",
                }
            elif line.startswith("RXA"):
                rf = line.split("|")
                if cur is None:
                    cur = {}
                cur["administration_start_datetime"] = rf[3] if len(rf) > 3 else ""
                vc = rf[5] if len(rf) > 5 else ""
                vcp = vc.split("^")
                cur["vaccine_code"] = vcp[0] if vcp else ""
                cur["vaccine_name"] = vcp[1] if len(vcp) > 1 else ""
                cur["vaccine_coding_system"] = vcp[2] if len(vcp) > 2 else ""
                cur["administered_amount"] = rf[6] if len(rf) > 6 else ""
                cur["administered_units"] = rf[7] if len(rf) > 7 else ""
                mf = rf[17] if len(rf) > 17 else ""
                mfp = mf.split("^")
                cur["manufacturer_code"] = mfp[0] if mfp else ""
                cur["manufacturer_name"] = mfp[1] if len(mfp) > 1 else ""
                cur["lot_number"] = rf[15] if len(rf) > 15 else ""
                cur["expiration_date"] = rf[16] if len(rf) > 16 else ""
                cur["completion_status"] = rf[20] if len(rf) > 20 else ""
            elif line.startswith("RXR"):
                rrf = line.split("|")
                if cur:
                    rt = rrf[1] if len(rrf) > 1 else ""
                    rtp = rt.split("^")
                    cur["route_code"] = rtp[0] if rtp else ""
                    cur["route_name"] = rtp[1] if len(rtp) > 1 else ""
                    st = rrf[2] if len(rrf) > 2 else ""
                    stp = st.split("^")
                    cur["site_code"] = stp[0] if stp else ""
                    cur["site_name"] = stp[1] if len(stp) > 1 else ""
            elif line.startswith("OBX"):
                xf = line.split("|")
                vax_obs.append({
                    "set_id": xf[1] if len(xf) > 1 else "",
                    "value_type": xf[2] if len(xf) > 2 else "",
                    "observation_id": xf[3] if len(xf) > 3 else "",
                    "observation_value": xf[5] if len(xf) > 5 else "",
                    "units": xf[6] if len(xf) > 6 else "",
                    "observation_result_status": xf[11] if len(xf) > 11 else "",
                })
        if cur:
            vaxes.append(cur)
        result["vaccinations"] = vaxes
        result["observations"] = vax_obs
    
    return result


# ---------------------------------------------------------------------------
# Register UDFs
# ---------------------------------------------------------------------------

split_hl7_batch_udf = udf(split_hl7_batch, ArrayType(StringType()))

# Generic parser UDF that returns message type for filtering
parse_hl7v2_udf = udf(parse_hl7v2_message, StructType([
    StructField("message_control_id", StringType()),
    StructField("message_type", StringType()),
    StructField("trigger_event", StringType()),
    StructField("sending_application", StringType()),
    StructField("sending_facility", StringType()),
    StructField("message_datetime", StringType()),
    StructField("patient_id", StringType()),
    StructField("patient_name_family", StringType()),
    StructField("patient_name_given", StringType()),
    StructField("date_of_birth", StringType()),
    StructField("gender", StringType()),
    # ADT fields
    StructField("event_type_code", StringType()),
    StructField("event_datetime", StringType()),
    StructField("patient_class", StringType()),
    StructField("assigned_location", StringType()),
    StructField("admission_type", StringType()),
    # ORM fields
    StructField("order_control", StringType()),
    StructField("order_id", StringType()),
    StructField("filler_order_number", StringType()),
    StructField("order_status", StringType()),
    StructField("placer_order_number", StringType()),
    StructField("universal_service_id", StringType()),
    # SIU fields
    StructField("placer_appointment_id", StringType()),
    StructField("filler_appointment_id", StringType()),
    StructField("schedule_id", StringType()),
    StructField("event_reason", StringType()),
    StructField("appointment_reason", StringType()),
    StructField("appointment_type", StringType()),
    StructField("appointment_duration", StringType()),
    StructField("appointment_start_datetime", StringType()),
    StructField("appointment_end_datetime", StringType()),
    StructField("filler_status_code", StringType()),
]))


# ---------------------------------------------------------------------------
# Bronze Tables - ADT Messages
# ---------------------------------------------------------------------------

@dlt.table(
    name="bronze_hl7v2_adt",
    comment="Bronze layer for HL7v2 ADT (Admit/Discharge/Transfer) messages",
    table_properties={"quality": "bronze"},
)
@dlt.expect_or_drop("valid_message_type", "message_type = 'ADT'")
@dlt.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
def bronze_hl7v2_adt():
    # Read HL7 files using Auto Loader
    raw_files = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "text")
        .option("wholetext", "true")
        .option("pathGlobFilter", FILE_PATTERN)
        .load(STORAGE_PATH)
    )
    
    # Split batch files into individual messages and parse
    return (
        raw_files
        .withColumn("_source_file", col("_metadata.file_path"))
        .withColumn("messages", split_hl7_batch_udf(col("value")))
        .withColumn("message", explode(col("messages")))
        .withColumn("parsed", parse_hl7v2_udf(col("message")))
        .filter(col("parsed.message_type") == "ADT")
        .select(
            col("parsed.message_control_id").alias("message_control_id"),
            col("parsed.message_type").alias("message_type"),
            col("parsed.trigger_event").alias("trigger_event"),
            col("parsed.sending_application").alias("sending_application"),
            col("parsed.sending_facility").alias("sending_facility"),
            col("parsed.message_datetime").alias("message_datetime"),
            col("parsed.patient_id").alias("patient_id"),
            col("parsed.patient_name_family").alias("patient_name_family"),
            col("parsed.patient_name_given").alias("patient_name_given"),
            col("parsed.date_of_birth").alias("date_of_birth"),
            col("parsed.gender").alias("gender"),
            col("parsed.event_type_code").alias("event_type_code"),
            col("parsed.event_datetime").alias("event_datetime"),
            col("parsed.patient_class").alias("patient_class"),
            col("parsed.assigned_location").alias("assigned_location"),
            col("parsed.admission_type").alias("admission_type"),
            col("_source_file"),
        )
    )


# ---------------------------------------------------------------------------
# Bronze Tables - ORM Messages
# ---------------------------------------------------------------------------

@dlt.table(
    name="bronze_hl7v2_orm",
    comment="Bronze layer for HL7v2 ORM (Order) messages",
    table_properties={"quality": "bronze"},
)
@dlt.expect_or_drop("valid_message_type", "message_type = 'ORM'")
@dlt.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
def bronze_hl7v2_orm():
    raw_files = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "text")
        .option("wholetext", "true")
        .option("pathGlobFilter", FILE_PATTERN)
        .load(STORAGE_PATH)
    )
    
    return (
        raw_files
        .withColumn("_source_file", col("_metadata.file_path"))
        .withColumn("messages", split_hl7_batch_udf(col("value")))
        .withColumn("message", explode(col("messages")))
        .withColumn("parsed", parse_hl7v2_udf(col("message")))
        .filter(col("parsed.message_type") == "ORM")
        .select(
            col("parsed.message_control_id").alias("message_control_id"),
            col("parsed.message_type").alias("message_type"),
            col("parsed.trigger_event").alias("trigger_event"),
            col("parsed.sending_application").alias("sending_application"),
            col("parsed.sending_facility").alias("sending_facility"),
            col("parsed.message_datetime").alias("message_datetime"),
            col("parsed.patient_id").alias("patient_id"),
            col("parsed.patient_name_family").alias("patient_name_family"),
            col("parsed.patient_name_given").alias("patient_name_given"),
            col("parsed.order_control").alias("order_control"),
            col("parsed.order_id").alias("order_id"),
            col("parsed.filler_order_number").alias("filler_order_number"),
            col("parsed.order_status").alias("order_status"),
            col("parsed.placer_order_number").alias("placer_order_number"),
            col("parsed.universal_service_id").alias("universal_service_id"),
            col("_source_file"),
        )
    )


# ---------------------------------------------------------------------------
# Bronze Tables - ORU Messages (with nested observations)
# ---------------------------------------------------------------------------

# ORU needs special handling for nested observations array
oru_parse_result_schema = StructType([
    StructField("message_control_id", StringType()),
    StructField("message_type", StringType()),
    StructField("trigger_event", StringType()),
    StructField("sending_application", StringType()),
    StructField("sending_facility", StringType()),
    StructField("message_datetime", StringType()),
    StructField("patient_id", StringType()),
    StructField("patient_name_family", StringType()),
    StructField("patient_name_given", StringType()),
    StructField("placer_order_number", StringType()),
    StructField("filler_order_number", StringType()),
    StructField("universal_service_id", StringType()),
    StructField("observations", ArrayType(StructType([
        StructField("set_id", StringType()),
        StructField("value_type", StringType()),
        StructField("observation_id", StringType()),
        StructField("observation_value", StringType()),
        StructField("units", StringType()),
        StructField("reference_range", StringType()),
        StructField("abnormal_flags", StringType()),
        StructField("result_status", StringType()),
    ]))),
])

parse_hl7v2_oru_udf = udf(parse_hl7v2_message, oru_parse_result_schema)


@dlt.table(
    name="bronze_hl7v2_oru",
    comment="Bronze layer for HL7v2 ORU (Observation Result) messages",
    table_properties={"quality": "bronze"},
)
@dlt.expect_or_drop("valid_message_type", "message_type = 'ORU'")
@dlt.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
def bronze_hl7v2_oru():
    raw_files = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "text")
        .option("wholetext", "true")
        .option("pathGlobFilter", FILE_PATTERN)
        .load(STORAGE_PATH)
    )
    
    return (
        raw_files
        .withColumn("_source_file", col("_metadata.file_path"))
        .withColumn("messages", split_hl7_batch_udf(col("value")))
        .withColumn("message", explode(col("messages")))
        .withColumn("parsed", parse_hl7v2_oru_udf(col("message")))
        .filter(col("parsed.message_type") == "ORU")
        .select(
            col("parsed.message_control_id").alias("message_control_id"),
            col("parsed.message_type").alias("message_type"),
            col("parsed.trigger_event").alias("trigger_event"),
            col("parsed.sending_application").alias("sending_application"),
            col("parsed.sending_facility").alias("sending_facility"),
            col("parsed.message_datetime").alias("message_datetime"),
            col("parsed.patient_id").alias("patient_id"),
            col("parsed.patient_name_family").alias("patient_name_family"),
            col("parsed.patient_name_given").alias("patient_name_given"),
            col("parsed.placer_order_number").alias("placer_order_number"),
            col("parsed.filler_order_number").alias("filler_order_number"),
            col("parsed.universal_service_id").alias("universal_service_id"),
            col("parsed.observations").alias("observations"),
            col("_source_file"),
        )
    )


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
            explode(col("observations")).alias("obs")
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


# ---------------------------------------------------------------------------
# Bronze Tables - SIU Messages (with nested resources)
# ---------------------------------------------------------------------------

siu_parse_result_schema = StructType([
    StructField("message_control_id", StringType()),
    StructField("message_type", StringType()),
    StructField("trigger_event", StringType()),
    StructField("sending_application", StringType()),
    StructField("sending_facility", StringType()),
    StructField("message_datetime", StringType()),
    StructField("patient_id", StringType()),
    StructField("patient_name_family", StringType()),
    StructField("patient_name_given", StringType()),
    StructField("placer_appointment_id", StringType()),
    StructField("filler_appointment_id", StringType()),
    StructField("schedule_id", StringType()),
    StructField("event_reason", StringType()),
    StructField("appointment_reason", StringType()),
    StructField("appointment_type", StringType()),
    StructField("appointment_duration", StringType()),
    StructField("appointment_start_datetime", StringType()),
    StructField("appointment_end_datetime", StringType()),
    StructField("filler_status_code", StringType()),
    StructField("appointment_resources", ArrayType(StructType([
        StructField("resource_type", StringType()),
        StructField("set_id", StringType()),
        StructField("universal_service_id", StringType()),
        StructField("personnel_id", StringType()),
        StructField("location_id", StringType()),
        StructField("resource_role", StringType()),
        StructField("start_datetime", StringType()),
        StructField("duration", StringType()),
    ]))),
])

parse_hl7v2_siu_udf = udf(parse_hl7v2_message, siu_parse_result_schema)


@dlt.table(
    name="bronze_hl7v2_siu",
    comment="Bronze layer for HL7v2 SIU (Scheduling) messages",
    table_properties={"quality": "bronze"},
)
@dlt.expect_or_drop("valid_message_type", "message_type = 'SIU'")
@dlt.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
def bronze_hl7v2_siu():
    raw_files = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "text")
        .option("wholetext", "true")
        .option("pathGlobFilter", FILE_PATTERN)
        .load(STORAGE_PATH)
    )
    
    return (
        raw_files
        .withColumn("_source_file", col("_metadata.file_path"))
        .withColumn("messages", split_hl7_batch_udf(col("value")))
        .withColumn("message", explode(col("messages")))
        .withColumn("parsed", parse_hl7v2_siu_udf(col("message")))
        .filter(col("parsed.message_type") == "SIU")
        .select(
            col("parsed.message_control_id").alias("message_control_id"),
            col("parsed.message_type").alias("message_type"),
            col("parsed.trigger_event").alias("trigger_event"),
            col("parsed.sending_application").alias("sending_application"),
            col("parsed.sending_facility").alias("sending_facility"),
            col("parsed.message_datetime").alias("message_datetime"),
            col("parsed.patient_id").alias("patient_id"),
            col("parsed.patient_name_family").alias("patient_name_family"),
            col("parsed.patient_name_given").alias("patient_name_given"),
            col("parsed.placer_appointment_id").alias("placer_appointment_id"),
            col("parsed.filler_appointment_id").alias("filler_appointment_id"),
            col("parsed.schedule_id").alias("schedule_id"),
            col("parsed.event_reason").alias("event_reason"),
            col("parsed.appointment_reason").alias("appointment_reason"),
            col("parsed.appointment_type").alias("appointment_type"),
            col("parsed.appointment_duration").alias("appointment_duration"),
            col("parsed.appointment_start_datetime").alias("appointment_start_datetime"),
            col("parsed.appointment_end_datetime").alias("appointment_end_datetime"),
            col("parsed.filler_status_code").alias("filler_status_code"),
            col("parsed.appointment_resources").alias("appointment_resources"),
            col("_source_file"),
        )
    )


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
            col("appointment_start_datetime"),
            col("patient_id"),
            explode(col("appointment_resources")).alias("r")
        )
        .select(
            col("message_control_id"),
            col("placer_appointment_id"),
            col("appointment_start_datetime"),
            col("patient_id"),
            col("r.resource_type").alias("resource_type"),
            col("r.set_id").alias("set_id"),
            col("r.universal_service_id").alias("service_id"),
            col("r.personnel_id").alias("personnel_id"),
            col("r.location_id").alias("location_id"),
            col("r.resource_role").alias("resource_role"),
            col("r.start_datetime").alias("resource_start_datetime"),
            col("r.duration").alias("duration"),
        )
    )


# ---------------------------------------------------------------------------
# Bronze Tables - VXU Messages (with nested vaccinations)
# ---------------------------------------------------------------------------

vxu_parse_result_schema = StructType([
    StructField("message_control_id", StringType()),
    StructField("message_type", StringType()),
    StructField("trigger_event", StringType()),
    StructField("sending_application", StringType()),
    StructField("sending_facility", StringType()),
    StructField("message_datetime", StringType()),
    StructField("patient_id", StringType()),
    StructField("patient_name_family", StringType()),
    StructField("patient_name_given", StringType()),
    StructField("date_of_birth", StringType()),
    StructField("gender", StringType()),
    StructField("vaccinations", ArrayType(StructType([
        StructField("order_control", StringType()),
        StructField("placer_order_number", StringType()),
        StructField("filler_order_number", StringType()),
        StructField("administration_start_datetime", StringType()),
        StructField("vaccine_code", StringType()),
        StructField("vaccine_name", StringType()),
        StructField("vaccine_coding_system", StringType()),
        StructField("administered_amount", StringType()),
        StructField("administered_units", StringType()),
        StructField("manufacturer_code", StringType()),
        StructField("manufacturer_name", StringType()),
        StructField("lot_number", StringType()),
        StructField("expiration_date", StringType()),
        StructField("completion_status", StringType()),
        StructField("route_code", StringType()),
        StructField("route_name", StringType()),
        StructField("site_code", StringType()),
        StructField("site_name", StringType()),
    ]))),
    StructField("observations", ArrayType(StructType([
        StructField("set_id", StringType()),
        StructField("value_type", StringType()),
        StructField("observation_id", StringType()),
        StructField("observation_value", StringType()),
        StructField("units", StringType()),
        StructField("observation_result_status", StringType()),
    ]))),
])

parse_hl7v2_vxu_udf = udf(parse_hl7v2_message, vxu_parse_result_schema)


@dlt.table(
    name="bronze_hl7v2_vxu",
    comment="Bronze layer for HL7v2 VXU (Vaccination) messages",
    table_properties={"quality": "bronze"},
)
@dlt.expect_or_drop("valid_message_type", "message_type = 'VXU'")
@dlt.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
def bronze_hl7v2_vxu():
    raw_files = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "text")
        .option("wholetext", "true")
        .option("pathGlobFilter", FILE_PATTERN)
        .load(STORAGE_PATH)
    )
    
    return (
        raw_files
        .withColumn("_source_file", col("_metadata.file_path"))
        .withColumn("messages", split_hl7_batch_udf(col("value")))
        .withColumn("message", explode(col("messages")))
        .withColumn("parsed", parse_hl7v2_vxu_udf(col("message")))
        .filter(col("parsed.message_type") == "VXU")
        .select(
            col("parsed.message_control_id").alias("message_control_id"),
            col("parsed.message_type").alias("message_type"),
            col("parsed.trigger_event").alias("trigger_event"),
            col("parsed.sending_application").alias("sending_application"),
            col("parsed.sending_facility").alias("sending_facility"),
            col("parsed.message_datetime").alias("message_datetime"),
            col("parsed.patient_id").alias("patient_id"),
            col("parsed.patient_name_family").alias("patient_name_family"),
            col("parsed.patient_name_given").alias("patient_name_given"),
            col("parsed.date_of_birth").alias("date_of_birth"),
            col("parsed.gender").alias("gender"),
            col("parsed.vaccinations").alias("vaccinations"),
            col("parsed.observations").alias("observations"),
            col("_source_file"),
        )
    )


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
            explode(col("vaccinations")).alias("v")
        )
        .select(
            col("message_control_id"),
            col("message_datetime"),
            col("patient_id"),
            col("patient_name_family"),
            col("patient_name_given"),
            col("date_of_birth"),
            col("gender"),
            col("v.administration_start_datetime").alias("administration_datetime"),
            col("v.vaccine_code").alias("cvx_code"),
            col("v.vaccine_name").alias("vaccine_name"),
            col("v.vaccine_coding_system").alias("coding_system"),
            col("v.administered_amount").alias("dose_amount"),
            col("v.administered_units").alias("dose_units"),
            col("v.manufacturer_code").alias("mvx_code"),
            col("v.manufacturer_name").alias("manufacturer_name"),
            col("v.lot_number").alias("lot_number"),
            col("v.expiration_date").alias("expiration_date"),
            col("v.completion_status").alias("completion_status"),
            col("v.route_code").alias("route_code"),
            col("v.route_name").alias("route_name"),
            col("v.site_code").alias("site_code"),
            col("v.site_name").alias("site_name"),
        )
    )
