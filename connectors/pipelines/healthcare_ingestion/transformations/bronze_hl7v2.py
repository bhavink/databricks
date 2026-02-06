# Healthcare HL7v2 Bronze Ingestion Pipeline
# ============================================
#
# Production-grade Spark Declarative Pipeline (SDP) for HL7v2 message ingestion.
# Uses Auto Loader for streaming file ingestion from UC Volumes.
#
# API: Modern pyspark.pipelines (2026 best practice)
# Features:
# - Liquid Clustering for optimal query performance (configurable)
# - Auto-optimization with predictive optimization (configurable)
# - Composite field parsing (Person Location, Coded Elements, etc.)
# - SDP expectations for data quality (configurable)
# - Quarantine table for failed records
# - Fully configurable via pipeline settings
#
# Configuration: All settings are externalized to pipeline configuration.
# See config/pipeline_settings.json for available options.
#
# Message Types (~95% coverage):
# - ADT: Admit/Discharge/Transfer (~40%)
# - ORU: Lab Results (~30%)
# - ORM: Orders (~15%)
# - SIU: Scheduling (~8%)
# - VXU: Vaccinations (~2%)

# Modern SDP API (pyspark.pipelines)
from pyspark import pipelines as dp
from pyspark.sql.functions import col, udf, explode, when, lit, current_timestamp
from pyspark.sql.types import ArrayType, StructType, StructField, StringType

# Note: All schemas and parsing logic are inlined in this file for executor access.
# No workspace file imports needed - UDFs cannot access workspace files on executors.


# ---------------------------------------------------------------------------
# Configuration Helper
# ---------------------------------------------------------------------------
class PipelineConfig:
    """
    Centralized configuration management for the HL7v2 pipeline.
    All settings are read from pipeline configuration (spark.conf).
    """
    
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str, default: str = "") -> str:
        """Get a configuration value with caching."""
        if key not in self._cache:
            self._cache[key] = spark.conf.get(key, default)
        return self._cache[key]
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value."""
        return self.get(key, str(default).lower()) == "true"
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer configuration value."""
        return int(self.get(key, str(default)))
    
    def get_list(self, key: str, default: str = "") -> list:
        """Get a comma-separated list as a Python list."""
        value = self.get(key, default)
        return [v.strip() for v in value.split(",") if v.strip()]
    
    # --- Source Configuration ---
    @property
    def storage_path(self) -> str:
        return self.get("healthcare.storage_path", "/Volumes/main/healthcare/raw_data/hl7v2")
    
    @property
    def file_pattern(self) -> str:
        return self.get("healthcare.file_pattern", "*.hl7")
    
    @property
    def max_files_per_trigger(self) -> str:
        return self.get("healthcare.max_files_per_trigger", "1000")
    
    @property
    def max_bytes_per_trigger(self) -> str:
        return self.get("healthcare.max_bytes_per_trigger", "10g")
    
    # --- Clustering Configuration ---
    @property
    def clustering_enabled(self) -> bool:
        return self.get_bool("healthcare.clustering.enabled", True)
    
    def get_cluster_columns(self, table_name: str) -> list:
        """Get clustering columns for a specific table."""
        key = f"healthcare.clustering.{table_name}.columns"
        return self.get_list(key, "")
    
    # --- Optimization Configuration ---
    @property
    def auto_optimize(self) -> bool:
        return self.get_bool("healthcare.optimization.auto_optimize", True)
    
    @property
    def optimize_write(self) -> bool:
        return self.get_bool("healthcare.optimization.optimize_write", True)
    
    @property
    def auto_compact(self) -> bool:
        return self.get_bool("healthcare.optimization.auto_compact", True)
    
    @property
    def predictive_optimization(self) -> bool:
        return self.get_bool("healthcare.optimization.predictive_optimization", True)
    
    # --- Data Quality Configuration ---
    @property
    def enable_expectations(self) -> bool:
        return self.get_bool("healthcare.quality.enable_expectations", True)
    
    @property
    def quarantine_invalid(self) -> bool:
        return self.get_bool("healthcare.quality.quarantine_invalid_records", True)
    
    # --- Feature Flags ---
    @property
    def parse_composite_fields(self) -> bool:
        return self.get_bool("healthcare.features.parse_composite_fields", True)
    
    @property
    def flatten_observations(self) -> bool:
        return self.get_bool("healthcare.features.flatten_observations", True)
    
    @property
    def flatten_vaccinations(self) -> bool:
        return self.get_bool("healthcare.features.flatten_vaccinations", True)
    
    @property
    def flatten_resources(self) -> bool:
        return self.get_bool("healthcare.features.flatten_resources", True)
    
    # --- Table Enable/Disable ---
    def is_table_enabled(self, table_name: str) -> bool:
        """Check if a specific table is enabled."""
        key = f"healthcare.tables.{table_name}.enabled"
        return self.get_bool(key, True)
    
    # --- Table Properties Builder ---
    def build_table_properties(self, table_name: str, quality: str = "bronze") -> dict:
        """
        Build table properties dict with optimization settings.
        
        Note: When Liquid Clustering (cluster_by) is enabled, we should NOT set
        pipelines.autoOptimize.zOrderCols as they are mutually exclusive.
        Liquid Clustering replaces Z-ordering entirely.
        """
        props = {"quality": quality}
        
        if self.auto_optimize:
            props["pipelines.autoOptimize.managed"] = "true"
        
        if self.optimize_write:
            props["delta.autoOptimize.optimizeWrite"] = "true"
        
        if self.auto_compact:
            props["delta.autoOptimize.autoCompact"] = "true"
        
        # Only add z-order cols as FALLBACK when Liquid Clustering is DISABLED
        # Z-ordering and Liquid Clustering are mutually exclusive
        cluster_cols = self.get_cluster_columns(table_name)
        if cluster_cols and not self.clustering_enabled:
            props["pipelines.autoOptimize.zOrderCols"] = ",".join(cluster_cols)
        
        return props


# Initialize global config
config = PipelineConfig()

# Convenience aliases for backward compatibility
STORAGE_PATH = config.storage_path
FILE_PATTERN = config.file_pattern


# ---------------------------------------------------------------------------
# HL7v2 Composite Field Parsers
# ---------------------------------------------------------------------------
# These helper functions parse HL7v2 composite data types into structured dicts.
# Reference: HL7v2 Data Types (https://hl7-definition.caristix.com/v2/HL7v2.5.1/DataTypes)

def parse_pl(value: str) -> dict:
    """
    Parse PL (Person Location) data type.
    Format: PointOfCare^Room^Bed^Facility^LocationStatus^PersonLocationType^Building^Floor^LocationDescription
    Used in: PV1-3 (Assigned Patient Location), PV1-6 (Prior Patient Location)
    """
    if not value:
        return {"unit": "", "room": "", "bed": "", "facility": "", "building": "", "floor": ""}
    parts = value.split("^")
    return {
        "unit": parts[0] if len(parts) > 0 else "",
        "room": parts[1] if len(parts) > 1 else "",
        "bed": parts[2] if len(parts) > 2 else "",
        "facility": parts[3] if len(parts) > 3 else "",
        "building": parts[6] if len(parts) > 6 else "",
        "floor": parts[7] if len(parts) > 7 else "",
    }


def parse_xcn(value: str) -> dict:
    """
    Parse XCN (Extended Composite ID Number and Name for Persons) data type.
    Format: ID^FamilyName^GivenName^MiddleName^Suffix^Prefix^Degree^SourceTable^AssigningAuthority
    Used in: PV1-7 (Attending Doctor), PV1-8 (Referring Doctor), ORC-12 (Ordering Provider)
    """
    if not value:
        return {"id": "", "family_name": "", "given_name": "", "degree": ""}
    parts = value.split("^")
    return {
        "id": parts[0] if len(parts) > 0 else "",
        "family_name": parts[1] if len(parts) > 1 else "",
        "given_name": parts[2] if len(parts) > 2 else "",
        "degree": parts[6] if len(parts) > 6 else "",
    }


def parse_cx(value: str) -> dict:
    """
    Parse CX (Extended Composite ID with Check Digit) data type.
    Format: ID^CheckDigit^CheckDigitScheme^AssigningAuthority^IDType^AssigningFacility
    Used in: PID-3 (Patient ID), PID-2 (External Patient ID)
    """
    if not value:
        return {"id": "", "assigning_authority": "", "id_type": ""}
    parts = value.split("^")
    return {
        "id": parts[0] if len(parts) > 0 else "",
        "assigning_authority": parts[3] if len(parts) > 3 else "",
        "id_type": parts[4] if len(parts) > 4 else "",
    }


def parse_ce(value: str) -> dict:
    """
    Parse CE/CWE (Coded Element) data type.
    Format: Code^Text^CodingSystem^AltCode^AltText^AltCodingSystem
    Used in: OBR-4 (Universal Service ID), OBX-3 (Observation ID), DG1-3 (Diagnosis Code)
    """
    if not value:
        return {"code": "", "text": "", "coding_system": ""}
    parts = value.split("^")
    return {
        "code": parts[0] if len(parts) > 0 else "",
        "text": parts[1] if len(parts) > 1 else "",
        "coding_system": parts[2] if len(parts) > 2 else "",
    }


def parse_xpn(value: str) -> dict:
    """
    Parse XPN (Extended Person Name) data type.
    Format: FamilyName^GivenName^MiddleName^Suffix^Prefix^Degree^NameType
    Used in: PID-5 (Patient Name)
    """
    if not value:
        return {"family": "", "given": "", "middle": "", "suffix": "", "prefix": ""}
    parts = value.split("^")
    return {
        "family": parts[0] if len(parts) > 0 else "",
        "given": parts[1] if len(parts) > 1 else "",
        "middle": parts[2] if len(parts) > 2 else "",
        "suffix": parts[3] if len(parts) > 3 else "",
        "prefix": parts[4] if len(parts) > 4 else "",
    }


def parse_xad(value: str) -> dict:
    """
    Parse XAD (Extended Address) data type.
    Format: StreetAddress^OtherDesignation^City^State^Zip^Country^AddressType
    Used in: PID-11 (Patient Address)
    """
    if not value:
        return {"street": "", "city": "", "state": "", "zip": "", "country": ""}
    parts = value.split("^")
    return {
        "street": parts[0] if len(parts) > 0 else "",
        "city": parts[2] if len(parts) > 2 else "",
        "state": parts[3] if len(parts) > 3 else "",
        "zip": parts[4] if len(parts) > 4 else "",
        "country": parts[5] if len(parts) > 5 else "",
    }


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
    """
    Parse a single HL7v2 message into a dictionary with composite field parsing.
    Returns None for invalid messages (will be quarantined).
    """
    if not msg or not msg.strip():
        return None
    msg = msg.replace("\r\n", "\n").replace("\r", "\n")
    lines = [l for l in msg.strip().split("\n") if l]
    if not lines or not lines[0].startswith("MSH"):
        return None
    
    result = {
        "_parse_error": None,
        "_raw_message": msg[:500] if len(msg) > 500 else msg,  # Truncate for debugging
    }
    
    try:
        # Parse MSH segment (header)
        msh = lines[0].split("|")
        result["sending_application"] = msh[2] if len(msh) > 2 else ""
        result["sending_facility"] = msh[3] if len(msh) > 3 else ""
        result["receiving_application"] = msh[4] if len(msh) > 4 else ""
        result["receiving_facility"] = msh[5] if len(msh) > 5 else ""
        result["message_datetime"] = msh[6] if len(msh) > 6 else ""
        msg_type_field = msh[8] if len(msh) > 8 else ""
        result["message_type"] = msg_type_field.split("^")[0] if msg_type_field else ""
        result["trigger_event"] = msg_type_field.split("^")[1] if "^" in msg_type_field else ""
        result["message_control_id"] = msh[9] if len(msh) > 9 else ""
        result["processing_id"] = msh[10] if len(msh) > 10 else ""
        result["version_id"] = msh[11] if len(msh) > 11 else ""
        
        # Parse PID segment (patient identification) with composite field parsing
        for line in lines:
            if line.startswith("PID"):
                pf = line.split("|")
                
                # PID-3: Patient ID (CX type)
                pid_field = pf[3] if len(pf) > 3 else ""
                pid_parsed = parse_cx(pid_field)
                result["patient_id"] = pid_parsed["id"]
                result["patient_id_assigning_authority"] = pid_parsed["assigning_authority"]
                result["patient_id_type"] = pid_parsed["id_type"]
                
                # PID-5: Patient Name (XPN type)
                name_field = pf[5] if len(pf) > 5 else ""
                name_parsed = parse_xpn(name_field)
                result["patient_name_family"] = name_parsed["family"]
                result["patient_name_given"] = name_parsed["given"]
                result["patient_name_middle"] = name_parsed["middle"]
                result["patient_name_suffix"] = name_parsed["suffix"]
                result["patient_name_prefix"] = name_parsed["prefix"]
                
                result["date_of_birth"] = pf[7] if len(pf) > 7 else ""
                result["gender"] = pf[8] if len(pf) > 8 else ""
                
                # PID-11: Patient Address (XAD type)
                addr_field = pf[11] if len(pf) > 11 else ""
                addr_parsed = parse_xad(addr_field)
                result["patient_address_street"] = addr_parsed["street"]
                result["patient_address_city"] = addr_parsed["city"]
                result["patient_address_state"] = addr_parsed["state"]
                result["patient_address_zip"] = addr_parsed["zip"]
                result["patient_address_country"] = addr_parsed["country"]
                
                break
        
        mt = result.get("message_type", "")
        
        # Parse message-type specific segments
        if mt == "ADT":
            _parse_adt_segments(lines, result)
        elif mt == "ORM":
            _parse_orm_segments(lines, result)
        elif mt == "ORU":
            _parse_oru_segments(lines, result)
        elif mt == "SIU":
            _parse_siu_segments(lines, result)
        elif mt == "VXU":
            _parse_vxu_segments(lines, result)
        
        return result
        
    except Exception as e:
        result["_parse_error"] = str(e)
        return result


def _parse_adt_segments(lines, result):
    """Parse ADT-specific segments (EVN, PV1) with composite field parsing."""
    for line in lines:
        if line.startswith("EVN"):
            ef = line.split("|")
            result["event_type_code"] = ef[1] if len(ef) > 1 else ""
            result["event_datetime"] = ef[2] if len(ef) > 2 else ""
            result["event_reason_code"] = ef[4] if len(ef) > 4 else ""
            
        elif line.startswith("PV1"):
            pf = line.split("|")
            result["patient_class"] = pf[2] if len(pf) > 2 else ""
            
            # PV1-3: Assigned Patient Location (PL type)
            loc_field = pf[3] if len(pf) > 3 else ""
            loc_parsed = parse_pl(loc_field)
            result["assigned_location"] = loc_field  # Keep original
            result["location_unit"] = loc_parsed["unit"]
            result["location_room"] = loc_parsed["room"]
            result["location_bed"] = loc_parsed["bed"]
            result["location_facility"] = loc_parsed["facility"]
            result["location_building"] = loc_parsed["building"]
            result["location_floor"] = loc_parsed["floor"]
            
            result["admission_type"] = pf[4] if len(pf) > 4 else ""
            result["preadmit_number"] = pf[5] if len(pf) > 5 else ""
            
            # PV1-6: Prior Patient Location (PL type)
            prior_loc = pf[6] if len(pf) > 6 else ""
            prior_parsed = parse_pl(prior_loc)
            result["prior_location_unit"] = prior_parsed["unit"]
            result["prior_location_room"] = prior_parsed["room"]
            result["prior_location_bed"] = prior_parsed["bed"]
            
            # PV1-7: Attending Doctor (XCN type)
            attending = pf[7] if len(pf) > 7 else ""
            attending_parsed = parse_xcn(attending)
            result["attending_doctor_id"] = attending_parsed["id"]
            result["attending_doctor_family"] = attending_parsed["family_name"]
            result["attending_doctor_given"] = attending_parsed["given_name"]
            
            # PV1-8: Referring Doctor (XCN type)
            referring = pf[8] if len(pf) > 8 else ""
            referring_parsed = parse_xcn(referring)
            result["referring_doctor_id"] = referring_parsed["id"]
            result["referring_doctor_family"] = referring_parsed["family_name"]
            result["referring_doctor_given"] = referring_parsed["given_name"]
            
            result["hospital_service"] = pf[10] if len(pf) > 10 else ""
            result["admit_source"] = pf[14] if len(pf) > 14 else ""
            result["patient_type"] = pf[18] if len(pf) > 18 else ""
            result["visit_number"] = pf[19] if len(pf) > 19 else ""
            result["discharge_disposition"] = pf[36] if len(pf) > 36 else ""
            result["admit_datetime"] = pf[44] if len(pf) > 44 else ""
            result["discharge_datetime"] = pf[45] if len(pf) > 45 else ""


def _parse_orm_segments(lines, result):
    """Parse ORM-specific segments (ORC, OBR) with composite field parsing."""
    for line in lines:
        if line.startswith("ORC"):
            of = line.split("|")
            result["order_control"] = of[1] if len(of) > 1 else ""
            result["order_id"] = of[2] if len(of) > 2 else ""
            result["filler_order_number"] = of[3] if len(of) > 3 else ""
            result["order_status"] = of[5] if len(of) > 5 else ""
            result["order_datetime"] = of[9] if len(of) > 9 else ""
            
            # ORC-12: Ordering Provider (XCN type)
            provider = of[12] if len(of) > 12 else ""
            provider_parsed = parse_xcn(provider)
            result["ordering_provider_id"] = provider_parsed["id"]
            result["ordering_provider_family"] = provider_parsed["family_name"]
            result["ordering_provider_given"] = provider_parsed["given_name"]
            
        elif line.startswith("OBR"):
            bf = line.split("|")
            result["placer_order_number"] = bf[2] if len(bf) > 2 else ""
            
            # OBR-4: Universal Service Identifier (CE type)
            service = bf[4] if len(bf) > 4 else ""
            service_parsed = parse_ce(service)
            result["universal_service_id"] = service  # Keep original
            result["service_code"] = service_parsed["code"]
            result["service_text"] = service_parsed["text"]
            result["service_coding_system"] = service_parsed["coding_system"]
            
            result["observation_datetime"] = bf[7] if len(bf) > 7 else ""
            result["specimen_received_datetime"] = bf[14] if len(bf) > 14 else ""
            result["result_status"] = bf[25] if len(bf) > 25 else ""


def _parse_oru_segments(lines, result):
    """Parse ORU-specific segments (OBR, OBX) with composite field parsing."""
    observations = []
    for line in lines:
        if line.startswith("OBR"):
            bf = line.split("|")
            result["placer_order_number"] = bf[2] if len(bf) > 2 else ""
            result["filler_order_number"] = bf[3] if len(bf) > 3 else ""
            
            # OBR-4: Universal Service Identifier (CE type)
            service = bf[4] if len(bf) > 4 else ""
            service_parsed = parse_ce(service)
            result["universal_service_id"] = service
            result["service_code"] = service_parsed["code"]
            result["service_text"] = service_parsed["text"]
            result["service_coding_system"] = service_parsed["coding_system"]
            
            result["observation_datetime"] = bf[7] if len(bf) > 7 else ""
            result["result_status"] = bf[25] if len(bf) > 25 else ""
            
        elif line.startswith("OBX"):
            xf = line.split("|")
            
            # OBX-3: Observation Identifier (CE type)
            obs_id = xf[3] if len(xf) > 3 else ""
            obs_id_parsed = parse_ce(obs_id)
            
            # OBX-6: Units (CE type)
            units = xf[6] if len(xf) > 6 else ""
            units_parsed = parse_ce(units)
            
            obs = {
                "set_id": xf[1] if len(xf) > 1 else "",
                "value_type": xf[2] if len(xf) > 2 else "",
                "observation_id": obs_id,
                "observation_code": obs_id_parsed["code"],
                "observation_text": obs_id_parsed["text"],
                "observation_coding_system": obs_id_parsed["coding_system"],
                "observation_value": xf[5] if len(xf) > 5 else "",
                "units": units,
                "units_code": units_parsed["code"],
                "units_text": units_parsed["text"],
                "reference_range": xf[7] if len(xf) > 7 else "",
                "abnormal_flags": xf[8] if len(xf) > 8 else "",
                "observation_result_status": xf[11] if len(xf) > 11 else "",
                "observation_datetime": xf[14] if len(xf) > 14 else "",
            }
            observations.append(obs)
    result["observations"] = observations


def _parse_siu_segments(lines, result):
    """Parse SIU-specific segments (SCH, AIS, AIP, AIL) with composite field parsing."""
    resources = []
    for line in lines:
        if line.startswith("SCH"):
            sf = line.split("|")
            result["placer_appointment_id"] = sf[1] if len(sf) > 1 else ""
            result["filler_appointment_id"] = sf[2] if len(sf) > 2 else ""
            
            # SCH-7: Appointment Reason (CE type)
            reason = sf[7] if len(sf) > 7 else ""
            reason_parsed = parse_ce(reason)
            result["appointment_reason"] = reason
            result["appointment_reason_code"] = reason_parsed["code"]
            result["appointment_reason_text"] = reason_parsed["text"]
            
            # SCH-8: Appointment Type (CE type)
            appt_type = sf[8] if len(sf) > 8 else ""
            type_parsed = parse_ce(appt_type)
            result["appointment_type"] = appt_type
            result["appointment_type_code"] = type_parsed["code"]
            result["appointment_type_text"] = type_parsed["text"]
            
            result["appointment_duration"] = sf[9] if len(sf) > 9 else ""
            result["appointment_duration_units"] = sf[10] if len(sf) > 10 else ""
            
            # SCH-11: Appointment Timing (TQ type - complex)
            timing = sf[11] if len(sf) > 11 else ""
            timing_parts = timing.split("^")
            result["appointment_start_datetime"] = timing_parts[3] if len(timing_parts) > 3 else ""
            result["appointment_end_datetime"] = timing_parts[4] if len(timing_parts) > 4 else ""
            
            result["filler_status_code"] = sf[25] if len(sf) > 25 else ""
            
        elif line.startswith("AIS"):
            af = line.split("|")
            # AIS-3: Universal Service Identifier (CE type)
            service = af[3] if len(af) > 3 else ""
            service_parsed = parse_ce(service)
            resources.append({
                "resource_type": "service",
                "set_id": af[1] if len(af) > 1 else "",
                "service_code": service_parsed["code"],
                "service_text": service_parsed["text"],
                "start_datetime": af[4] if len(af) > 4 else "",
                "duration": af[7] if len(af) > 7 else "",
                "filler_status_code": af[10] if len(af) > 10 else "",
            })
            
        elif line.startswith("AIP"):
            af = line.split("|")
            # AIP-3: Personnel Resource ID (XCN type)
            personnel = af[3] if len(af) > 3 else ""
            personnel_parsed = parse_xcn(personnel)
            resources.append({
                "resource_type": "personnel",
                "set_id": af[1] if len(af) > 1 else "",
                "personnel_id": personnel_parsed["id"],
                "personnel_family": personnel_parsed["family_name"],
                "personnel_given": personnel_parsed["given_name"],
                "resource_role": af[4] if len(af) > 4 else "",
                "start_datetime": af[6] if len(af) > 6 else "",
                "duration": af[8] if len(af) > 8 else "",
            })
            
        elif line.startswith("AIL"):
            af = line.split("|")
            # AIL-3: Location Resource ID (PL type)
            location = af[3] if len(af) > 3 else ""
            location_parsed = parse_pl(location)
            resources.append({
                "resource_type": "location",
                "set_id": af[1] if len(af) > 1 else "",
                "location_unit": location_parsed["unit"],
                "location_room": location_parsed["room"],
                "location_bed": location_parsed["bed"],
                "location_facility": location_parsed["facility"],
                "location_type": af[4] if len(af) > 4 else "",
                "start_datetime": af[6] if len(af) > 6 else "",
                "duration": af[8] if len(af) > 8 else "",
            })
    result["appointment_resources"] = resources


def _parse_vxu_segments(lines, result):
    """Parse VXU-specific segments (RXA, RXR, OBX) with composite field parsing."""
    vaccinations = []
    observations = []
    current_vax = None
    
    for line in lines:
        if line.startswith("ORC"):
            if current_vax:
                vaccinations.append(current_vax)
            of = line.split("|")
            current_vax = {
                "order_control": of[1] if len(of) > 1 else "",
                "placer_order_number": of[2] if len(of) > 2 else "",
                "filler_order_number": of[3] if len(of) > 3 else "",
            }
            
        elif line.startswith("RXA"):
            rf = line.split("|")
            if current_vax is None:
                current_vax = {}
            
            current_vax["administration_start_datetime"] = rf[3] if len(rf) > 3 else ""
            current_vax["administration_end_datetime"] = rf[4] if len(rf) > 4 else ""
            
            # RXA-5: Administered Code (CE type - CVX vaccine code)
            vaccine = rf[5] if len(rf) > 5 else ""
            vaccine_parsed = parse_ce(vaccine)
            current_vax["vaccine_code"] = vaccine_parsed["code"]
            current_vax["vaccine_name"] = vaccine_parsed["text"]
            current_vax["vaccine_coding_system"] = vaccine_parsed["coding_system"]
            
            current_vax["administered_amount"] = rf[6] if len(rf) > 6 else ""
            current_vax["administered_units"] = rf[7] if len(rf) > 7 else ""
            current_vax["lot_number"] = rf[15] if len(rf) > 15 else ""
            current_vax["expiration_date"] = rf[16] if len(rf) > 16 else ""
            
            # RXA-17: Manufacturer (CE type - MVX code)
            mfr = rf[17] if len(rf) > 17 else ""
            mfr_parsed = parse_ce(mfr)
            current_vax["manufacturer_code"] = mfr_parsed["code"]
            current_vax["manufacturer_name"] = mfr_parsed["text"]
            
            current_vax["completion_status"] = rf[20] if len(rf) > 20 else ""
            current_vax["action_code"] = rf[21] if len(rf) > 21 else ""
            
        elif line.startswith("RXR"):
            rf = line.split("|")
            if current_vax:
                # RXR-1: Route (CE type)
                route = rf[1] if len(rf) > 1 else ""
                route_parsed = parse_ce(route)
                current_vax["route_code"] = route_parsed["code"]
                current_vax["route_name"] = route_parsed["text"]
                
                # RXR-2: Administration Site (CWE type)
                site = rf[2] if len(rf) > 2 else ""
                site_parsed = parse_ce(site)
                current_vax["site_code"] = site_parsed["code"]
                current_vax["site_name"] = site_parsed["text"]
                
        elif line.startswith("OBX"):
            xf = line.split("|")
            obs_id = xf[3] if len(xf) > 3 else ""
            obs_parsed = parse_ce(obs_id)
            observations.append({
                "set_id": xf[1] if len(xf) > 1 else "",
                "value_type": xf[2] if len(xf) > 2 else "",
                "observation_code": obs_parsed["code"],
                "observation_text": obs_parsed["text"],
                "observation_value": xf[5] if len(xf) > 5 else "",
                "observation_result_status": xf[11] if len(xf) > 11 else "",
            })
    
    if current_vax:
        vaccinations.append(current_vax)
    
    result["vaccinations"] = vaccinations
    result["observations"] = observations


# ---------------------------------------------------------------------------
# UDF Registration
# ---------------------------------------------------------------------------

split_hl7_batch_udf = udf(split_hl7_batch, ArrayType(StringType()))

# Full parser UDF schema with all fields including composite parsed fields
FULL_PARSE_SCHEMA = StructType([
    # Metadata
    StructField("_parse_error", StringType(), nullable=True),
    StructField("_raw_message", StringType(), nullable=True),
    # MSH fields
    StructField("message_control_id", StringType(), nullable=True),
    StructField("message_type", StringType(), nullable=True),
    StructField("trigger_event", StringType(), nullable=True),
    StructField("sending_application", StringType(), nullable=True),
    StructField("sending_facility", StringType(), nullable=True),
    StructField("receiving_application", StringType(), nullable=True),
    StructField("receiving_facility", StringType(), nullable=True),
    StructField("message_datetime", StringType(), nullable=True),
    StructField("processing_id", StringType(), nullable=True),
    StructField("version_id", StringType(), nullable=True),
    # PID fields - parsed composites
    StructField("patient_id", StringType(), nullable=True),
    StructField("patient_id_assigning_authority", StringType(), nullable=True),
    StructField("patient_id_type", StringType(), nullable=True),
    StructField("patient_name_family", StringType(), nullable=True),
    StructField("patient_name_given", StringType(), nullable=True),
    StructField("patient_name_middle", StringType(), nullable=True),
    StructField("patient_name_suffix", StringType(), nullable=True),
    StructField("patient_name_prefix", StringType(), nullable=True),
    StructField("date_of_birth", StringType(), nullable=True),
    StructField("gender", StringType(), nullable=True),
    StructField("patient_address_street", StringType(), nullable=True),
    StructField("patient_address_city", StringType(), nullable=True),
    StructField("patient_address_state", StringType(), nullable=True),
    StructField("patient_address_zip", StringType(), nullable=True),
    StructField("patient_address_country", StringType(), nullable=True),
    # ADT fields - parsed composites
    StructField("event_type_code", StringType(), nullable=True),
    StructField("event_datetime", StringType(), nullable=True),
    StructField("event_reason_code", StringType(), nullable=True),
    StructField("patient_class", StringType(), nullable=True),
    StructField("assigned_location", StringType(), nullable=True),
    StructField("location_unit", StringType(), nullable=True),
    StructField("location_room", StringType(), nullable=True),
    StructField("location_bed", StringType(), nullable=True),
    StructField("location_facility", StringType(), nullable=True),
    StructField("location_building", StringType(), nullable=True),
    StructField("location_floor", StringType(), nullable=True),
    StructField("admission_type", StringType(), nullable=True),
    StructField("preadmit_number", StringType(), nullable=True),
    StructField("prior_location_unit", StringType(), nullable=True),
    StructField("prior_location_room", StringType(), nullable=True),
    StructField("prior_location_bed", StringType(), nullable=True),
    StructField("attending_doctor_id", StringType(), nullable=True),
    StructField("attending_doctor_family", StringType(), nullable=True),
    StructField("attending_doctor_given", StringType(), nullable=True),
    StructField("referring_doctor_id", StringType(), nullable=True),
    StructField("referring_doctor_family", StringType(), nullable=True),
    StructField("referring_doctor_given", StringType(), nullable=True),
    StructField("hospital_service", StringType(), nullable=True),
    StructField("admit_source", StringType(), nullable=True),
    StructField("patient_type", StringType(), nullable=True),
    StructField("visit_number", StringType(), nullable=True),
    StructField("discharge_disposition", StringType(), nullable=True),
    StructField("admit_datetime", StringType(), nullable=True),
    StructField("discharge_datetime", StringType(), nullable=True),
    # ORM/ORU fields
    StructField("order_control", StringType(), nullable=True),
    StructField("order_id", StringType(), nullable=True),
    StructField("filler_order_number", StringType(), nullable=True),
    StructField("order_status", StringType(), nullable=True),
    StructField("order_datetime", StringType(), nullable=True),
    StructField("ordering_provider_id", StringType(), nullable=True),
    StructField("ordering_provider_family", StringType(), nullable=True),
    StructField("ordering_provider_given", StringType(), nullable=True),
    StructField("placer_order_number", StringType(), nullable=True),
    StructField("universal_service_id", StringType(), nullable=True),
    StructField("service_code", StringType(), nullable=True),
    StructField("service_text", StringType(), nullable=True),
    StructField("service_coding_system", StringType(), nullable=True),
    StructField("observation_datetime", StringType(), nullable=True),
    StructField("specimen_received_datetime", StringType(), nullable=True),
    StructField("result_status", StringType(), nullable=True),
    # ORU observations array
    StructField("observations", ArrayType(StructType([
        StructField("set_id", StringType(), nullable=True),
        StructField("value_type", StringType(), nullable=True),
        StructField("observation_id", StringType(), nullable=True),
        StructField("observation_code", StringType(), nullable=True),
        StructField("observation_text", StringType(), nullable=True),
        StructField("observation_coding_system", StringType(), nullable=True),
        StructField("observation_value", StringType(), nullable=True),
        StructField("units", StringType(), nullable=True),
        StructField("units_code", StringType(), nullable=True),
        StructField("units_text", StringType(), nullable=True),
        StructField("reference_range", StringType(), nullable=True),
        StructField("abnormal_flags", StringType(), nullable=True),
        StructField("observation_result_status", StringType(), nullable=True),
        StructField("observation_datetime", StringType(), nullable=True),
    ])), nullable=True),
    # SIU fields
    StructField("placer_appointment_id", StringType(), nullable=True),
    StructField("filler_appointment_id", StringType(), nullable=True),
    StructField("appointment_reason", StringType(), nullable=True),
    StructField("appointment_reason_code", StringType(), nullable=True),
    StructField("appointment_reason_text", StringType(), nullable=True),
    StructField("appointment_type", StringType(), nullable=True),
    StructField("appointment_type_code", StringType(), nullable=True),
    StructField("appointment_type_text", StringType(), nullable=True),
    StructField("appointment_duration", StringType(), nullable=True),
    StructField("appointment_duration_units", StringType(), nullable=True),
    StructField("appointment_start_datetime", StringType(), nullable=True),
    StructField("appointment_end_datetime", StringType(), nullable=True),
    StructField("filler_status_code", StringType(), nullable=True),
    StructField("appointment_resources", ArrayType(StructType([
        StructField("resource_type", StringType(), nullable=True),
        StructField("set_id", StringType(), nullable=True),
        StructField("service_code", StringType(), nullable=True),
        StructField("service_text", StringType(), nullable=True),
        StructField("personnel_id", StringType(), nullable=True),
        StructField("personnel_family", StringType(), nullable=True),
        StructField("personnel_given", StringType(), nullable=True),
        StructField("resource_role", StringType(), nullable=True),
        StructField("location_unit", StringType(), nullable=True),
        StructField("location_room", StringType(), nullable=True),
        StructField("location_bed", StringType(), nullable=True),
        StructField("location_facility", StringType(), nullable=True),
        StructField("location_type", StringType(), nullable=True),
        StructField("start_datetime", StringType(), nullable=True),
        StructField("duration", StringType(), nullable=True),
        StructField("filler_status_code", StringType(), nullable=True),
    ])), nullable=True),
    # VXU fields
    StructField("vaccinations", ArrayType(StructType([
        StructField("order_control", StringType(), nullable=True),
        StructField("placer_order_number", StringType(), nullable=True),
        StructField("filler_order_number", StringType(), nullable=True),
        StructField("administration_start_datetime", StringType(), nullable=True),
        StructField("administration_end_datetime", StringType(), nullable=True),
        StructField("vaccine_code", StringType(), nullable=True),
        StructField("vaccine_name", StringType(), nullable=True),
        StructField("vaccine_coding_system", StringType(), nullable=True),
        StructField("administered_amount", StringType(), nullable=True),
        StructField("administered_units", StringType(), nullable=True),
        StructField("lot_number", StringType(), nullable=True),
        StructField("expiration_date", StringType(), nullable=True),
        StructField("manufacturer_code", StringType(), nullable=True),
        StructField("manufacturer_name", StringType(), nullable=True),
        StructField("completion_status", StringType(), nullable=True),
        StructField("action_code", StringType(), nullable=True),
        StructField("route_code", StringType(), nullable=True),
        StructField("route_name", StringType(), nullable=True),
        StructField("site_code", StringType(), nullable=True),
        StructField("site_name", StringType(), nullable=True),
    ])), nullable=True),
])

parse_hl7v2_udf = udf(parse_hl7v2_message, FULL_PARSE_SCHEMA)


# ---------------------------------------------------------------------------
# Raw Ingestion Table (All Messages) - Single Parse Pass
# ---------------------------------------------------------------------------

# Build table configuration dynamically
_raw_cluster_cols = config.get_cluster_columns("raw") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_raw",
    comment="Raw parsed HL7v2 messages - all types, single parse pass for efficiency",
    table_properties=config.build_table_properties("raw"),
    cluster_by=_raw_cluster_cols,
)
def bronze_hl7v2_raw():
    """
    Ingest all HL7v2 files and parse once. Downstream tables filter by message type.
    This avoids re-parsing the same files for each message type.
    
    Clustering: Configurable via healthcare.clustering.raw.columns
    """
    raw_files = (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "text")
        .option("wholetext", "true")
        .option("pathGlobFilter", FILE_PATTERN)
        .option("cloudFiles.maxFilesPerTrigger", config.max_files_per_trigger)
        .option("cloudFiles.maxBytesPerTrigger", config.max_bytes_per_trigger)
        .load(STORAGE_PATH)
    )
    
    return (
        raw_files
        .withColumn("_source_file", col("_metadata.file_path"))
        .withColumn("_ingestion_timestamp", current_timestamp())
        .withColumn("messages", split_hl7_batch_udf(col("value")))
        .withColumn("message", explode(col("messages")))
        .withColumn("parsed", parse_hl7v2_udf(col("message")))
        .select(
            col("_source_file"),
            col("_ingestion_timestamp"),
            col("message").alias("_raw_message_full"),
            col("parsed.*"),
        )
    )


# ---------------------------------------------------------------------------
# Quarantine Table (Failed Messages)
# ---------------------------------------------------------------------------

_quarantine_cluster_cols = config.get_cluster_columns("quarantine") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_quarantine",
    comment="Quarantined messages that failed parsing or validation",
    table_properties=config.build_table_properties("quarantine"),
    cluster_by=_quarantine_cluster_cols,
)
def bronze_hl7v2_quarantine():
    """
    Capture messages that failed parsing or don't meet expectations.
    Per SDP best practice: use quarantine pattern instead of dropping silently.
    
    Clustering: Configurable via healthcare.clustering.quarantine.columns
    """
    return (
        spark.read.table("bronze_hl7v2_raw")
        .filter(
            (col("message_control_id").isNull()) |
            (col("message_control_id") == "") |
            (col("message_type").isNull()) |
            (col("message_type") == "") |
            (col("_parse_error").isNotNull())
        )
        .select(
            col("_source_file"),
            col("_ingestion_timestamp"),
            col("_raw_message_full"),
            col("_parse_error"),
            col("message_type"),
            col("message_control_id"),
        )
    )


# ---------------------------------------------------------------------------
# ADT Messages (Admit/Discharge/Transfer)
# ---------------------------------------------------------------------------

_adt_cluster_cols = config.get_cluster_columns("adt") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_adt",
    comment="HL7v2 ADT messages (Admit/Discharge/Transfer) with parsed location and provider fields",
    table_properties=config.build_table_properties("adt"),
    cluster_by=_adt_cluster_cols,
)
@dp.expect_or_drop("valid_message_control_id", "message_control_id IS NOT NULL AND message_control_id != ''")
@dp.expect_or_drop("valid_message_type", "message_type = 'ADT'")
@dp.expect("has_patient_id", "patient_id IS NOT NULL AND patient_id != ''")
@dp.expect("has_trigger_event", "trigger_event IS NOT NULL AND trigger_event != ''")
def bronze_hl7v2_adt():
    return (
        spark.read.table("bronze_hl7v2_raw")
        .filter(col("message_type") == "ADT")
        .filter(col("_parse_error").isNull())
        .select(
            # Core identifiers
            col("message_control_id"),
            col("message_type"),
            col("trigger_event"),
            col("sending_application"),
            col("sending_facility"),
            col("receiving_application"),
            col("receiving_facility"),
            col("message_datetime"),
            col("processing_id"),
            col("version_id"),
            # Patient demographics
            col("patient_id"),
            col("patient_id_assigning_authority"),
            col("patient_id_type"),
            col("patient_name_family"),
            col("patient_name_given"),
            col("patient_name_middle"),
            col("patient_name_prefix"),
            col("patient_name_suffix"),
            col("date_of_birth"),
            col("gender"),
            col("patient_address_street"),
            col("patient_address_city"),
            col("patient_address_state"),
            col("patient_address_zip"),
            col("patient_address_country"),
            # Event info
            col("event_type_code"),
            col("event_datetime"),
            col("event_reason_code"),
            # Visit info
            col("patient_class"),
            col("admission_type"),
            col("preadmit_number"),
            col("hospital_service"),
            col("admit_source"),
            col("patient_type"),
            col("visit_number"),
            col("discharge_disposition"),
            col("admit_datetime"),
            col("discharge_datetime"),
            # Location - original and parsed components
            col("assigned_location"),
            col("location_unit"),
            col("location_room"),
            col("location_bed"),
            col("location_facility"),
            col("location_building"),
            col("location_floor"),
            # Prior location
            col("prior_location_unit"),
            col("prior_location_room"),
            col("prior_location_bed"),
            # Providers - parsed components
            col("attending_doctor_id"),
            col("attending_doctor_family"),
            col("attending_doctor_given"),
            col("referring_doctor_id"),
            col("referring_doctor_family"),
            col("referring_doctor_given"),
            # Metadata
            col("_source_file"),
            col("_ingestion_timestamp"),
        )
    )


# ---------------------------------------------------------------------------
# ORM Messages (Orders)
# ---------------------------------------------------------------------------

_orm_cluster_cols = config.get_cluster_columns("orm") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_orm",
    comment="HL7v2 ORM messages (Orders) with parsed service and provider fields",
    table_properties=config.build_table_properties("orm"),
    cluster_by=_orm_cluster_cols,
)
@dp.expect_or_drop("valid_message_control_id", "message_control_id IS NOT NULL AND message_control_id != ''")
@dp.expect_or_drop("valid_message_type", "message_type = 'ORM'")
@dp.expect("has_order_id", "order_id IS NOT NULL AND order_id != ''")
@dp.expect("has_order_control", "order_control IS NOT NULL AND order_control != ''")
def bronze_hl7v2_orm():
    return (
        spark.read.table("bronze_hl7v2_raw")
        .filter(col("message_type") == "ORM")
        .filter(col("_parse_error").isNull())
        .select(
            # Core identifiers
            col("message_control_id"),
            col("message_type"),
            col("trigger_event"),
            col("sending_application"),
            col("sending_facility"),
            col("message_datetime"),
            # Patient info
            col("patient_id"),
            col("patient_id_assigning_authority"),
            col("patient_name_family"),
            col("patient_name_given"),
            # Order info
            col("order_control"),
            col("order_id"),
            col("filler_order_number"),
            col("placer_order_number"),
            col("order_status"),
            col("order_datetime"),
            # Service - original and parsed
            col("universal_service_id"),
            col("service_code"),
            col("service_text"),
            col("service_coding_system"),
            # Provider
            col("ordering_provider_id"),
            col("ordering_provider_family"),
            col("ordering_provider_given"),
            # Timing
            col("observation_datetime"),
            col("specimen_received_datetime"),
            col("result_status"),
            # Metadata
            col("_source_file"),
            col("_ingestion_timestamp"),
        )
    )


# ---------------------------------------------------------------------------
# ORU Messages (Lab Results)
# ---------------------------------------------------------------------------

_oru_cluster_cols = config.get_cluster_columns("oru") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_oru",
    comment="HL7v2 ORU messages (Lab Results) with observations array",
    table_properties=config.build_table_properties("oru"),
    cluster_by=_oru_cluster_cols,
)
@dp.expect_or_drop("valid_message_control_id", "message_control_id IS NOT NULL AND message_control_id != ''")
@dp.expect_or_drop("valid_message_type", "message_type = 'ORU'")
@dp.expect("has_patient_id", "patient_id IS NOT NULL AND patient_id != ''")
@dp.expect("has_observations", "observations IS NOT NULL AND size(observations) > 0")
def bronze_hl7v2_oru():
    return (
        spark.read.table("bronze_hl7v2_raw")
        .filter(col("message_type") == "ORU")
        .filter(col("_parse_error").isNull())
        .select(
            col("message_control_id"),
            col("message_type"),
            col("trigger_event"),
            col("sending_application"),
            col("sending_facility"),
            col("message_datetime"),
            col("patient_id"),
            col("patient_id_assigning_authority"),
            col("patient_name_family"),
            col("patient_name_given"),
            col("date_of_birth"),
            col("gender"),
            col("placer_order_number"),
            col("filler_order_number"),
            col("universal_service_id"),
            col("service_code"),
            col("service_text"),
            col("service_coding_system"),
            col("observation_datetime"),
            col("result_status"),
            col("observations"),
            col("_source_file"),
            col("_ingestion_timestamp"),
        )
    )


# ---------------------------------------------------------------------------
# ORU Observations (Flattened Lab Results)
# ---------------------------------------------------------------------------

_oru_obs_cluster_cols = config.get_cluster_columns("oru_observations") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_oru_observations",
    comment="Flattened lab result observations from ORU messages",
    table_properties=config.build_table_properties("oru_observations"),
    cluster_by=_oru_obs_cluster_cols,
)
@dp.expect("has_observation_code", "observation_code IS NOT NULL AND observation_code != ''")
def bronze_hl7v2_oru_observations():
    return (
        spark.read.table("bronze_hl7v2_oru")
        .filter(col("observations").isNotNull())
        .select(
            col("message_control_id"),
            col("message_datetime"),
            col("patient_id"),
            col("patient_name_family"),
            col("patient_name_given"),
            col("placer_order_number"),
            col("filler_order_number"),
            col("service_code"),
            col("service_text"),
            explode(col("observations")).alias("obs"),
            col("_source_file"),
            col("_ingestion_timestamp"),
        )
        .select(
            col("message_control_id"),
            col("message_datetime"),
            col("patient_id"),
            col("patient_name_family"),
            col("patient_name_given"),
            col("placer_order_number"),
            col("filler_order_number"),
            col("service_code"),
            col("service_text"),
            col("obs.set_id").alias("set_id"),
            col("obs.value_type").alias("value_type"),
            col("obs.observation_id").alias("observation_id"),
            col("obs.observation_code").alias("observation_code"),
            col("obs.observation_text").alias("observation_text"),
            col("obs.observation_coding_system").alias("observation_coding_system"),
            col("obs.observation_value").alias("observation_value"),
            col("obs.units").alias("units"),
            col("obs.units_code").alias("units_code"),
            col("obs.units_text").alias("units_text"),
            col("obs.reference_range").alias("reference_range"),
            col("obs.abnormal_flags").alias("abnormal_flags"),
            col("obs.observation_result_status").alias("observation_result_status"),
            col("obs.observation_datetime").alias("observation_datetime"),
            col("_source_file"),
            col("_ingestion_timestamp"),
        )
    )


# ---------------------------------------------------------------------------
# SIU Messages (Scheduling)
# ---------------------------------------------------------------------------

_siu_cluster_cols = config.get_cluster_columns("siu") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_siu",
    comment="HL7v2 SIU messages (Scheduling) with appointment resources",
    table_properties=config.build_table_properties("siu"),
    cluster_by=_siu_cluster_cols,
)
@dp.expect_or_drop("valid_message_control_id", "message_control_id IS NOT NULL AND message_control_id != ''")
@dp.expect_or_drop("valid_message_type", "message_type = 'SIU'")
@dp.expect("has_appointment_id", "placer_appointment_id IS NOT NULL OR filler_appointment_id IS NOT NULL")
def bronze_hl7v2_siu():
    return (
        spark.read.table("bronze_hl7v2_raw")
        .filter(col("message_type") == "SIU")
        .filter(col("_parse_error").isNull())
        .select(
            col("message_control_id"),
            col("message_type"),
            col("trigger_event"),
            col("sending_application"),
            col("sending_facility"),
            col("message_datetime"),
            col("patient_id"),
            col("patient_id_assigning_authority"),
            col("patient_name_family"),
            col("patient_name_given"),
            col("placer_appointment_id"),
            col("filler_appointment_id"),
            col("appointment_reason"),
            col("appointment_reason_code"),
            col("appointment_reason_text"),
            col("appointment_type"),
            col("appointment_type_code"),
            col("appointment_type_text"),
            col("appointment_duration"),
            col("appointment_duration_units"),
            col("appointment_start_datetime"),
            col("appointment_end_datetime"),
            col("filler_status_code"),
            col("appointment_resources"),
            col("_source_file"),
            col("_ingestion_timestamp"),
        )
    )


# ---------------------------------------------------------------------------
# SIU Resources (Flattened Appointment Resources)
# ---------------------------------------------------------------------------

_siu_res_cluster_cols = config.get_cluster_columns("siu_resources") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_siu_resources",
    comment="Flattened appointment resources from SIU messages",
    table_properties=config.build_table_properties("siu_resources"),
    cluster_by=_siu_res_cluster_cols,
)
def bronze_hl7v2_siu_resources():
    return (
        spark.read.table("bronze_hl7v2_siu")
        .filter(col("appointment_resources").isNotNull())
        .select(
            col("message_control_id"),
            col("message_datetime"),
            col("patient_id"),
            col("placer_appointment_id"),
            col("filler_appointment_id"),
            col("appointment_type_code"),
            col("appointment_start_datetime"),
            explode(col("appointment_resources")).alias("r"),
            col("_source_file"),
            col("_ingestion_timestamp"),
        )
        .select(
            col("message_control_id"),
            col("message_datetime"),
            col("patient_id"),
            col("placer_appointment_id"),
            col("filler_appointment_id"),
            col("appointment_type_code"),
            col("appointment_start_datetime"),
            col("r.resource_type").alias("resource_type"),
            col("r.set_id").alias("set_id"),
            col("r.service_code").alias("service_code"),
            col("r.service_text").alias("service_text"),
            col("r.personnel_id").alias("personnel_id"),
            col("r.personnel_family").alias("personnel_family"),
            col("r.personnel_given").alias("personnel_given"),
            col("r.resource_role").alias("resource_role"),
            col("r.location_unit").alias("location_unit"),
            col("r.location_room").alias("location_room"),
            col("r.location_bed").alias("location_bed"),
            col("r.location_facility").alias("location_facility"),
            col("r.location_type").alias("location_type"),
            col("r.start_datetime").alias("resource_start_datetime"),
            col("r.duration").alias("resource_duration"),
            col("r.filler_status_code").alias("resource_filler_status"),
            col("_source_file"),
            col("_ingestion_timestamp"),
        )
    )


# ---------------------------------------------------------------------------
# VXU Messages (Vaccinations)
# ---------------------------------------------------------------------------

_vxu_cluster_cols = config.get_cluster_columns("vxu") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_vxu",
    comment="HL7v2 VXU messages (Vaccinations) with vaccination records",
    table_properties=config.build_table_properties("vxu"),
    cluster_by=_vxu_cluster_cols,
)
@dp.expect_or_drop("valid_message_control_id", "message_control_id IS NOT NULL AND message_control_id != ''")
@dp.expect_or_drop("valid_message_type", "message_type = 'VXU'")
@dp.expect("has_patient_id", "patient_id IS NOT NULL AND patient_id != ''")
@dp.expect("has_vaccinations", "vaccinations IS NOT NULL AND size(vaccinations) > 0")
def bronze_hl7v2_vxu():
    return (
        spark.read.table("bronze_hl7v2_raw")
        .filter(col("message_type") == "VXU")
        .filter(col("_parse_error").isNull())
        .select(
            col("message_control_id"),
            col("message_type"),
            col("trigger_event"),
            col("sending_application"),
            col("sending_facility"),
            col("message_datetime"),
            col("patient_id"),
            col("patient_id_assigning_authority"),
            col("patient_name_family"),
            col("patient_name_given"),
            col("date_of_birth"),
            col("gender"),
            col("vaccinations"),
            col("observations"),
            col("_source_file"),
            col("_ingestion_timestamp"),
        )
    )


# ---------------------------------------------------------------------------
# VXU Vaccinations (Flattened Vaccination Records)
# ---------------------------------------------------------------------------

_vxu_vacc_cluster_cols = config.get_cluster_columns("vxu_vaccinations") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_vxu_vaccinations",
    comment="Flattened vaccination records from VXU messages",
    table_properties=config.build_table_properties("vxu_vaccinations"),
    cluster_by=_vxu_vacc_cluster_cols,
)
@dp.expect("has_vaccine_code", "cvx_code IS NOT NULL AND cvx_code != ''")
def bronze_hl7v2_vxu_vaccinations():
    return (
        spark.read.table("bronze_hl7v2_vxu")
        .filter(col("vaccinations").isNotNull())
        .select(
            col("message_control_id"),
            col("message_datetime"),
            col("patient_id"),
            col("patient_name_family"),
            col("patient_name_given"),
            col("date_of_birth"),
            col("gender"),
            explode(col("vaccinations")).alias("v"),
            col("_source_file"),
            col("_ingestion_timestamp"),
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
            col("v.action_code").alias("action_code"),
            col("v.route_code").alias("route_code"),
            col("v.route_name").alias("route_name"),
            col("v.site_code").alias("site_code"),
            col("v.site_name").alias("site_name"),
            col("_source_file"),
            col("_ingestion_timestamp"),
        )
    )
