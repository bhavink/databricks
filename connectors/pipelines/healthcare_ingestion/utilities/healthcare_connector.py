"""
Healthcare Connector for Lakeflow Declarative Pipelines.

Simplified connector for HL7v2 file ingestion from UC Volumes.
Designed to work with DLT/SDP pipelines.

Features:
- Batch file support (multiple messages per file)
- Error handling (skip, fail, dead_letter)
- ~95% HL7v2 message type coverage (ADT, ORU, ORM, SIU, VXU)
"""

from typing import Iterator, Optional, Tuple, List, Dict, Any
import json
import logging

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, explode
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    ArrayType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema Definitions
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

SCHEMAS = {
    "adt_messages": StructType([
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
    "orm_messages": StructType([
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
    "oru_messages": StructType([
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
    "siu_messages": StructType([
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
        StructField("appointment_resources", ArrayType(StructType([
            StructField("resource_type", StringType(), nullable=True),
            StructField("set_id", StringType(), nullable=True),
            StructField("universal_service_id", StringType(), nullable=True),
            StructField("personnel_id", StringType(), nullable=True),
            StructField("location_id", StringType(), nullable=True),
            StructField("resource_role", StringType(), nullable=True),
            StructField("start_datetime", StringType(), nullable=True),
            StructField("duration", StringType(), nullable=True),
        ])), nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),
    "vxu_messages": StructType([
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
        StructField("vaccinations", ArrayType(StructType([
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
        ])), nullable=True),
        StructField("observations", ArrayType(StructType([
            StructField("set_id", StringType(), nullable=True),
            StructField("value_type", StringType(), nullable=True),
            StructField("observation_id", StringType(), nullable=True),
            StructField("observation_value", StringType(), nullable=True),
            StructField("units", StringType(), nullable=True),
            StructField("observation_result_status", StringType(), nullable=True),
        ])), nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),
}

METADATA = {
    "adt_messages": {"primary_keys": ["message_control_id"], "cursor_field": "message_datetime", "ingestion_type": "append"},
    "orm_messages": {"primary_keys": ["message_control_id"], "cursor_field": "message_datetime", "ingestion_type": "append"},
    "oru_messages": {"primary_keys": ["message_control_id"], "cursor_field": "message_datetime", "ingestion_type": "append"},
    "siu_messages": {"primary_keys": ["message_control_id"], "cursor_field": "message_datetime", "ingestion_type": "append"},
    "vxu_messages": {"primary_keys": ["message_control_id"], "cursor_field": "message_datetime", "ingestion_type": "append"},
}


# ---------------------------------------------------------------------------
# Healthcare Connector
# ---------------------------------------------------------------------------

class HealthcareConnector:
    """
    Lakeflow Connect implementation for Healthcare HL7v2 data.
    
    Usage:
        connector = HealthcareConnector({
            "storage_path": "/Volumes/catalog/schema/volume/hl7v2",
            "file_pattern": "*.hl7"
        })
        records, offset = connector.read_table("adt_messages", None, {})
    """
    
    HL7V2_TABLES = ["adt_messages", "orm_messages", "oru_messages", "siu_messages", "vxu_messages"]
    
    TABLE_TO_HL7_TYPE = {
        "adt_messages": "ADT",
        "orm_messages": "ORM",
        "oru_messages": "ORU",
        "siu_messages": "SIU",
        "vxu_messages": "VXU",
    }
    
    def __init__(self, options: Dict[str, str]) -> None:
        if "storage_path" not in options:
            raise ValueError("storage_path is required")
        self.storage_path = options["storage_path"].rstrip("/")
        self.file_pattern = options.get("file_pattern", "*.hl7")
        self._spark = None
    
    def _get_spark(self) -> SparkSession:
        if self._spark is None:
            self._spark = SparkSession.builder.getOrCreate()
        return self._spark
    
    def list_tables(self) -> List[str]:
        return self.HL7V2_TABLES.copy()
    
    def get_table_schema(self, table_name: str, table_options: Dict) -> StructType:
        if table_name not in self.HL7V2_TABLES:
            raise ValueError(f"Table '{table_name}' not supported")
        return SCHEMAS.get(table_name)
    
    def read_table_metadata(self, table_name: str, table_options: Dict) -> Dict:
        if table_name not in self.HL7V2_TABLES:
            raise ValueError(f"Table '{table_name}' not supported")
        return METADATA.get(table_name)
    
    def read_table(
        self,
        table_name: str,
        start_offset: Optional[Dict],
        table_options: Dict,
    ) -> Tuple[Iterator[Dict], Dict]:
        if table_name not in self.HL7V2_TABLES:
            raise ValueError(f"Table '{table_name}' not supported")
        
        target_type = self.TABLE_TO_HL7_TYPE[table_name]
        spark = self._get_spark()
        
        batch_size = int(table_options.get("batch_size", "1000"))
        error_handling = table_options.get("error_handling", "skip")
        search_path = f"{self.storage_path}/{self.file_pattern}"
        last_file = start_offset.get("last_file") if start_offset else None
        
        try:
            return self._read_hl7v2_batch(spark, search_path, target_type, last_file, batch_size, error_handling, table_options)
        except Exception as e:
            logger.error(f"Error reading HL7v2 files: {e}")
            if error_handling == "fail":
                raise
            return iter([]), start_offset
    
    def _read_hl7v2_batch(self, spark, search_path, target_type, last_file, batch_size, error_handling, table_options):
        PARSE_RESULT_SCHEMA = StructType([
            StructField("success", StringType(), nullable=False),
            StructField("data", StringType(), nullable=True),
            StructField("error", StringType(), nullable=True),
            StructField("msg_type", StringType(), nullable=True),
        ])
        
        try:
            files_df = spark.read.format("binaryFile").load(search_path)
        except Exception as e:
            logger.error(f"Failed to read files: {e}")
            if error_handling == "fail":
                raise
            return iter([]), None
        
        files_df = files_df.orderBy("path")
        if last_file:
            files_df = files_df.filter(col("path") > last_file)
        files_df = files_df.limit(batch_size)
        
        # UDF with fully inlined parsing - executors don't have access to external modules
        @udf(returnType=ArrayType(PARSE_RESULT_SCHEMA))
        def parse_hl7_batch(content: bytes, file_path: str):
            import json as json_mod
            
            def split_batch(text):
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
            
            def parse_msg(msg):
                if not msg or not msg.strip():
                    return None
                msg = msg.replace("\r\n", "\n").replace("\r", "\n")
                lines = [l for l in msg.strip().split("\n") if l]
                if not lines or not lines[0].startswith("MSH"):
                    return None
                
                result = {}
                msh = lines[0].split("|")
                result["sending_application"] = msh[2] if len(msh) > 2 else ""
                result["sending_facility"] = msh[3] if len(msh) > 3 else ""
                result["message_datetime"] = msh[6] if len(msh) > 6 else ""
                msg_type_field = msh[8] if len(msh) > 8 else ""
                result["message_type"] = msg_type_field.split("^")[0] if msg_type_field else ""
                result["trigger_event"] = msg_type_field.split("^")[1] if "^" in msg_type_field else ""
                result["message_control_id"] = msh[9] if len(msh) > 9 else ""
                
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
                            obs.append({"set_id": xf[1] if len(xf) > 1 else "", "value_type": xf[2] if len(xf) > 2 else "", "observation_id": xf[3] if len(xf) > 3 else "", "observation_value": xf[5] if len(xf) > 5 else "", "units": xf[6] if len(xf) > 6 else "", "reference_range": xf[7] if len(xf) > 7 else "", "abnormal_flags": xf[8] if len(xf) > 8 else "", "result_status": xf[11] if len(xf) > 11 else ""})
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
                            resources.append({"resource_type": "service", "set_id": af[1] if len(af) > 1 else "", "universal_service_id": af[3] if len(af) > 3 else "", "personnel_id": None, "location_id": None, "resource_role": None, "start_datetime": af[4] if len(af) > 4 else "", "duration": af[7] if len(af) > 7 else ""})
                        elif line.startswith("AIP"):
                            af = line.split("|")
                            resources.append({"resource_type": "personnel", "set_id": af[1] if len(af) > 1 else "", "universal_service_id": None, "personnel_id": af[3] if len(af) > 3 else "", "location_id": None, "resource_role": af[4] if len(af) > 4 else "", "start_datetime": af[6] if len(af) > 6 else "", "duration": af[8] if len(af) > 8 else ""})
                        elif line.startswith("AIL"):
                            af = line.split("|")
                            resources.append({"resource_type": "location", "set_id": af[1] if len(af) > 1 else "", "universal_service_id": None, "personnel_id": None, "location_id": af[3] if len(af) > 3 else "", "resource_role": af[4] if len(af) > 4 else "", "start_datetime": af[6] if len(af) > 6 else "", "duration": af[8] if len(af) > 8 else ""})
                    result["appointment_resources"] = resources
                
                elif mt == "VXU":
                    vaxes, vax_obs, cur = [], [], None
                    for line in lines:
                        if line.startswith("ORC"):
                            if cur:
                                vaxes.append(cur)
                            of = line.split("|")
                            cur = {"order_control": of[1] if len(of) > 1 else "", "placer_order_number": of[2] if len(of) > 2 else "", "filler_order_number": of[3] if len(of) > 3 else ""}
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
                            vax_obs.append({"set_id": xf[1] if len(xf) > 1 else "", "value_type": xf[2] if len(xf) > 2 else "", "observation_id": xf[3] if len(xf) > 3 else "", "observation_value": xf[5] if len(xf) > 5 else "", "units": xf[6] if len(xf) > 6 else "", "observation_result_status": xf[11] if len(xf) > 11 else ""})
                    if cur:
                        vaxes.append(cur)
                    result["vaccinations"] = vaxes
                    result["observations"] = vax_obs
                
                return result
            
            if content is None:
                return [{"success": "false", "data": None, "error": "Empty", "msg_type": None}]
            
            results = []
            try:
                text = content.decode("utf-8", errors="replace")
                messages = split_batch(text)
                if not messages:
                    return [{"success": "false", "data": None, "error": "No messages", "msg_type": None}]
                for i, msg_text in enumerate(messages):
                    try:
                        parsed = parse_msg(msg_text)
                        if parsed:
                            results.append({"success": "true", "data": json_mod.dumps(parsed), "error": None, "msg_type": parsed.get("message_type", "")})
                        else:
                            results.append({"success": "false", "data": None, "error": f"Parse failed msg {i+1}", "msg_type": None})
                    except Exception as e:
                        results.append({"success": "false", "data": None, "error": str(e), "msg_type": None})
                return results if results else [{"success": "false", "data": None, "error": "No results", "msg_type": None}]
            except Exception as e:
                return [{"success": "false", "data": None, "error": str(e), "msg_type": None}]
        
        parsed_df = (
            files_df
            .withColumn("parse_results", parse_hl7_batch(col("content"), col("path")))
            .select(col("path"), explode(col("parse_results")).alias("pr"))
            .select(col("path"), col("pr.success").alias("success"), col("pr.data").alias("data"), col("pr.error").alias("error"), col("pr.msg_type").alias("msg_type"))
        )
        
        success_df = parsed_df.filter((col("success") == "true") & (col("msg_type") == target_type))
        
        dead_letter_path = table_options.get("dead_letter_path")
        if error_handling == "dead_letter" and dead_letter_path:
            try:
                failed_df = parsed_df.filter(col("success") == "false")
                if failed_df.count() > 0:
                    failed_df.select("path", "error", "msg_type").write.mode("append").json(f"{dead_letter_path}/hl7v2_errors")
            except Exception as e:
                logger.error(f"DLQ write failed: {e}")
        
        records = []
        new_offset = {"processed_files": [], "_stats": {}}
        
        for row in success_df.toLocalIterator():
            try:
                record = json.loads(row.data)
                record["_source_file"] = row.path
                records.append(record)
                new_offset["last_file"] = row.path
                new_offset["processed_files"].append(row.path)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON error: {e}")
                if error_handling == "fail":
                    raise
        
        new_offset["_stats"]["records_returned"] = len(records)
        return iter(records), new_offset if new_offset else None


# Alias
LakeflowConnect = HealthcareConnector
