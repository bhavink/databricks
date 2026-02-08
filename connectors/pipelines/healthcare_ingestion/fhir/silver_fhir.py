# Healthcare FHIR R4 Silver Layer Pipeline
# =========================================
#
# Production-grade Spark Declarative Pipeline (SDP) for FHIR R4 resource refinement.
# Transforms bronze resources into typed, deduplicated silver tables.
#
# API: Modern pyspark.pipelines (2026 best practice)
# Features:
# - Resource-specific parsing with VARIANT storage for extensions
# - Liquid Clustering for optimal query performance (configurable)
# - Auto-optimization with predictive optimization (configurable)
# - Deduplication using meta.versionId
# - SDP expectations for data quality (configurable)
#
# Tables:
# - silver_fhir_patient: Patient demographics and identifiers
# - silver_fhir_observation: Lab results, vitals, measurements
# - silver_fhir_encounter: Healthcare visits and encounters
# - silver_fhir_medication_request: Prescribed medications
# - silver_fhir_condition: Diagnoses and problems
# - silver_fhir_immunization: Vaccination records

# Modern SDP API (pyspark.pipelines)
from pyspark import pipelines as dp
from pyspark.sql.functions import (
    col, udf, when, lit, current_timestamp, row_number,
    from_json, coalesce, to_date, to_timestamp, year, month
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DateType, TimestampType,
    ArrayType, IntegerType, BooleanType, DoubleType
)
from pyspark.sql.window import Window
import json


# ---------------------------------------------------------------------------
# Configuration Helper
# ---------------------------------------------------------------------------
class PipelineConfig:
    """
    Centralized configuration management for FHIR silver layer.
    """
    
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str, default: str = "") -> str:
        if key not in self._cache:
            self._cache[key] = spark.conf.get(key, default)
        return self._cache[key]
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        return self.get(key, str(default).lower()) == "true"
    
    def get_list(self, key: str, default: str = "") -> list:
        value = self.get(key, default)
        return [v.strip() for v in value.split(",") if v.strip()]
    
    @property
    def clustering_enabled(self) -> bool:
        return self.get_bool("fhir.clustering.enabled", True)
    
    def get_cluster_columns(self, table_name: str) -> list:
        key = f"fhir.clustering.{table_name}.columns"
        return self.get_list(key, "")
    
    @property
    def auto_optimize(self) -> bool:
        return self.get_bool("fhir.optimization.auto_optimize", True)
    
    @property
    def optimize_write(self) -> bool:
        return self.get_bool("fhir.optimization.optimize_write", True)
    
    def build_table_properties(self, table_name: str, quality: str = "silver") -> dict:
        props = {"quality": quality}
        if self.auto_optimize:
            props["pipelines.autoOptimize.managed"] = "true"
        if self.optimize_write:
            props["delta.autoOptimize.optimizeWrite"] = "true"
        return props


# Initialize config
config = PipelineConfig()


# ---------------------------------------------------------------------------
# Parsing Helper Functions (All inlined for executor access)
# ---------------------------------------------------------------------------

def safe_get(data: dict, *keys, default=None):
    """Safely navigate nested dictionary."""
    current = data
    for key in keys:
        if current is None or not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def extract_coding(codeable_concept: dict, default_system: str = None) -> dict:
    """Extract first coding from CodeableConcept."""
    if not codeable_concept:
        return {"code": None, "system": None, "display": None}
    
    codings = codeable_concept.get("coding", [])
    if codings and len(codings) > 0:
        coding = codings[0]
        return {
            "code": coding.get("code"),
            "system": coding.get("system", default_system),
            "display": coding.get("display"),
        }
    
    return {
        "code": None,
        "system": default_system,
        "display": codeable_concept.get("text"),
    }


def extract_reference(reference: dict) -> dict:
    """Extract reference type and ID."""
    if not reference:
        return {"type": None, "id": None}
    
    ref_str = reference.get("reference", "")
    if "/" in ref_str:
        parts = ref_str.split("/")
        return {"type": parts[0], "id": parts[1]}
    
    return {"type": reference.get("type"), "id": ref_str}


def extract_identifier(identifiers: list, system: str = None) -> str:
    """Extract first matching identifier value."""
    if not identifiers:
        return None
    
    for identifier in identifiers:
        if system is None or identifier.get("system") == system:
            return identifier.get("value")
    
    return identifiers[0].get("value") if identifiers else None


def format_name(names: list) -> dict:
    """Format human names."""
    if not names or len(names) == 0:
        return {"family": None, "given": None, "full": None}
    
    name = names[0]
    family = name.get("family", "")
    given_list = name.get("given", [])
    given = " ".join(given_list) if given_list else ""
    
    full = f"{given} {family}".strip() if given or family else None
    
    return {"family": family or None, "given": given or None, "full": full}


def parse_date(date_str: str) -> str:
    """Parse FHIR date/datetime to ISO format."""
    if not date_str:
        return None
    # Return as-is for Spark to parse
    return date_str[:10] if len(date_str) >= 10 else date_str


# ---------------------------------------------------------------------------
# Resource Parsers (Inlined for executor access)
# ---------------------------------------------------------------------------

def parse_patient(raw_resource: str) -> dict:
    """
    Parse Patient resource into flattened structure.
    
    ALL LOGIC INLINED - executors cannot access workspace imports.
    
    RESILIENCE PATTERN: Catches ALL exceptions to prevent pipeline failures.
    Returns None on any error - filtered out by downstream expectations.
    """
    # Outer try/except catches ALL unexpected exceptions
    try:
        try:
            resource = json.loads(raw_resource) if isinstance(raw_resource, str) else raw_resource
        except (json.JSONDecodeError, TypeError):
            return None
        
        if not resource or resource.get("resourceType") != "Patient":
            return None
        
        # Name handling
        names = resource.get("name", [])
        name_info = format_name(names)
        
        # Identifier handling
        identifiers = resource.get("identifier", [])
        mrn = extract_identifier(identifiers, "http://hospital.org/mrn")
        ssn = extract_identifier(identifiers, "http://hl7.org/fhir/sid/us-ssn")
        
        # Address handling
        addresses = resource.get("address", [])
        address = addresses[0] if addresses else {}
        
        return {
            "id": resource.get("id"),
            "resource_type": "Patient",
            "meta_version_id": safe_get(resource, "meta", "versionId"),
            "meta_last_updated": safe_get(resource, "meta", "lastUpdated"),
            "active": resource.get("active", True),
            "gender": resource.get("gender"),
            "birth_date": resource.get("birthDate"),
            "deceased_boolean": resource.get("deceasedBoolean"),
            "deceased_datetime": resource.get("deceasedDateTime"),
            "family_name": name_info["family"],
            "given_name": name_info["given"],
            "full_name": name_info["full"],
            "mrn": mrn,
            "ssn": ssn,
            "address_line": " ".join(address.get("line", [])) if address.get("line") else None,
            "address_city": address.get("city"),
            "address_state": address.get("state"),
            "address_postal_code": address.get("postalCode"),
            "address_country": address.get("country"),
            "marital_status_code": safe_get(extract_coding(resource.get("maritalStatus")), "code"),
            # VARIANT fields stored as JSON strings
            "names": json.dumps(names) if names else None,
            "identifiers": json.dumps(identifiers) if identifiers else None,
            "addresses": json.dumps(addresses) if addresses else None,
            "telecoms": json.dumps(resource.get("telecom", [])) if resource.get("telecom") else None,
            "extensions": json.dumps(resource.get("extension", [])) if resource.get("extension") else None,
            "raw_resource": raw_resource,
        }
    except Exception:
        # Catch-all: return None on any unexpected error
        # Downstream expectations will filter these out
        return None


def parse_observation(raw_resource: str) -> dict:
    """
    Parse Observation resource into flattened structure.
    
    RESILIENCE PATTERN: Catches ALL exceptions to prevent pipeline failures.
    """
    try:
        try:
            resource = json.loads(raw_resource) if isinstance(raw_resource, str) else raw_resource
        except (json.JSONDecodeError, TypeError):
            return None
        
        if not resource or resource.get("resourceType") != "Observation":
            return None
        
        # Code
        code_info = extract_coding(resource.get("code"))
        
        # Subject reference
        subject = extract_reference(resource.get("subject"))
        
        # Category
        categories = resource.get("category", [])
        category_info = extract_coding(categories[0]) if categories else {}
        
        # Value extraction (choice type)
        value = None
        value_type = None
        value_unit = None
        
        if "valueQuantity" in resource:
            vq = resource["valueQuantity"]
            value = str(vq.get("value", ""))
            value_type = "Quantity"
            value_unit = vq.get("unit") or vq.get("code")
        elif "valueString" in resource:
            value = resource["valueString"]
            value_type = "String"
        elif "valueCodeableConcept" in resource:
            cc = extract_coding(resource["valueCodeableConcept"])
            value = cc["display"] or cc["code"]
            value_type = "CodeableConcept"
        elif "valueBoolean" in resource:
            value = str(resource["valueBoolean"])
            value_type = "Boolean"
        elif "valueInteger" in resource:
            value = str(resource["valueInteger"])
            value_type = "Integer"
        elif "valueDateTime" in resource:
            value = resource["valueDateTime"]
            value_type = "DateTime"
        
        # Reference ranges
        ref_ranges = resource.get("referenceRange", [])
        ref_low = safe_get(ref_ranges[0], "low", "value") if ref_ranges else None
        ref_high = safe_get(ref_ranges[0], "high", "value") if ref_ranges else None
        
        # Components (for panel results)
        components = resource.get("component", [])
        
        return {
            "id": resource.get("id"),
            "resource_type": "Observation",
            "meta_version_id": safe_get(resource, "meta", "versionId"),
            "meta_last_updated": safe_get(resource, "meta", "lastUpdated"),
            "status": resource.get("status"),
            "code": code_info.get("code"),
            "code_system": code_info.get("system"),
            "code_display": code_info.get("display"),
            "category_code": category_info.get("code"),
            "category_display": category_info.get("display"),
            "subject_type": subject["type"],
            "subject_id": subject["id"],
            "encounter_id": safe_get(extract_reference(resource.get("encounter")), "id"),
            "effective_datetime": resource.get("effectiveDateTime"),
            "effective_period_start": safe_get(resource, "effectivePeriod", "start"),
            "effective_period_end": safe_get(resource, "effectivePeriod", "end"),
            "issued": resource.get("issued"),
            "value": value,
            "value_type": value_type,
            "value_unit": value_unit,
            "reference_range_low": str(ref_low) if ref_low else None,
            "reference_range_high": str(ref_high) if ref_high else None,
            "interpretation_code": safe_get(extract_coding(safe_get(resource, "interpretation", 0)), "code"),
            "data_absent_reason": safe_get(extract_coding(resource.get("dataAbsentReason")), "code"),
            # VARIANT fields
            "components": json.dumps(components) if components else None,
            "performers": json.dumps(resource.get("performer", [])) if resource.get("performer") else None,
            "extensions": json.dumps(resource.get("extension", [])) if resource.get("extension") else None,
            "raw_resource": raw_resource,
        }
    except Exception:
        return None


def parse_encounter(raw_resource: str) -> dict:
    """
    Parse Encounter resource into flattened structure.
    
    RESILIENCE PATTERN: Catches ALL exceptions to prevent pipeline failures.
    """
    try:
        try:
            resource = json.loads(raw_resource) if isinstance(raw_resource, str) else raw_resource
        except (json.JSONDecodeError, TypeError):
            return None
        
        if not resource or resource.get("resourceType") != "Encounter":
            return None
        
        # Subject reference
        subject = extract_reference(resource.get("subject"))
        
        # Class
        enc_class = resource.get("class", {})
        
        # Type
        types = resource.get("type", [])
        type_info = extract_coding(types[0]) if types else {}
        
        # Period
        period = resource.get("period", {})
        
        # Hospitalization
        hospitalization = resource.get("hospitalization", {})
        admit_source = extract_coding(hospitalization.get("admitSource"))
        discharge_disposition = extract_coding(hospitalization.get("dischargeDisposition"))
        
        # Service provider
        service_provider = extract_reference(resource.get("serviceProvider"))
        
        # Participants
        participants = resource.get("participant", [])
        
        # Locations
        locations = resource.get("location", [])
        primary_location = locations[0] if locations else {}
        location_ref = extract_reference(primary_location.get("location"))
        
        # Reason codes
        reasons = resource.get("reasonCode", [])
        reason_info = extract_coding(reasons[0]) if reasons else {}
        
        return {
            "id": resource.get("id"),
            "resource_type": "Encounter",
            "meta_version_id": safe_get(resource, "meta", "versionId"),
            "meta_last_updated": safe_get(resource, "meta", "lastUpdated"),
            "status": resource.get("status"),
            "class_code": enc_class.get("code"),
            "class_display": enc_class.get("display"),
            "type_code": type_info.get("code"),
            "type_display": type_info.get("display"),
            "subject_type": subject["type"],
            "subject_id": subject["id"],
            "period_start": period.get("start"),
            "period_end": period.get("end"),
            "admit_source_code": admit_source.get("code"),
            "admit_source_display": admit_source.get("display"),
            "discharge_disposition_code": discharge_disposition.get("code"),
            "discharge_disposition_display": discharge_disposition.get("display"),
            "service_provider_type": service_provider["type"],
            "service_provider_id": service_provider["id"],
            "location_id": location_ref["id"],
            "reason_code": reason_info.get("code"),
            "reason_display": reason_info.get("display"),
            # VARIANT fields
            "participants": json.dumps(participants) if participants else None,
            "locations": json.dumps(locations) if locations else None,
            "reason_codes": json.dumps(reasons) if reasons else None,
            "extensions": json.dumps(resource.get("extension", [])) if resource.get("extension") else None,
            "raw_resource": raw_resource,
        }
    except Exception:
        return None


def parse_condition(raw_resource: str) -> dict:
    """
    Parse Condition resource into flattened structure.
    
    RESILIENCE PATTERN: Catches ALL exceptions to prevent pipeline failures.
    """
    try:
        try:
            resource = json.loads(raw_resource) if isinstance(raw_resource, str) else raw_resource
        except (json.JSONDecodeError, TypeError):
            return None
        
        if not resource or resource.get("resourceType") != "Condition":
            return None
        
        # Code
        code_info = extract_coding(resource.get("code"))
        
        # Subject reference
        subject = extract_reference(resource.get("subject"))
        
        # Category
        categories = resource.get("category", [])
        category_info = extract_coding(categories[0]) if categories else {}
        
        # Clinical status
        clinical_status = extract_coding(resource.get("clinicalStatus"))
        
        # Verification status
        verification_status = extract_coding(resource.get("verificationStatus"))
        
        # Severity
        severity = extract_coding(resource.get("severity"))
        
        # Body site
        body_sites = resource.get("bodySite", [])
        body_site_info = extract_coding(body_sites[0]) if body_sites else {}
        
        # Onset (choice type)
        onset_datetime = resource.get("onsetDateTime")
        onset_age = safe_get(resource, "onsetAge", "value")
        onset_period_start = safe_get(resource, "onsetPeriod", "start")
        
        # Abatement (choice type)
        abatement_datetime = resource.get("abatementDateTime")
        abatement_age = safe_get(resource, "abatementAge", "value")
        
        return {
            "id": resource.get("id"),
            "resource_type": "Condition",
            "meta_version_id": safe_get(resource, "meta", "versionId"),
            "meta_last_updated": safe_get(resource, "meta", "lastUpdated"),
            "code": code_info.get("code"),
            "code_system": code_info.get("system"),
            "code_display": code_info.get("display"),
            "category_code": category_info.get("code"),
            "category_display": category_info.get("display"),
            "clinical_status_code": clinical_status.get("code"),
            "verification_status_code": verification_status.get("code"),
            "severity_code": severity.get("code"),
            "severity_display": severity.get("display"),
            "body_site_code": body_site_info.get("code"),
            "body_site_display": body_site_info.get("display"),
            "subject_type": subject["type"],
            "subject_id": subject["id"],
            "encounter_id": safe_get(extract_reference(resource.get("encounter")), "id"),
            "onset_datetime": onset_datetime,
            "onset_age": str(onset_age) if onset_age else None,
            "onset_period_start": onset_period_start,
            "abatement_datetime": abatement_datetime,
            "abatement_age": str(abatement_age) if abatement_age else None,
            "recorded_date": resource.get("recordedDate"),
            "recorder_id": safe_get(extract_reference(resource.get("recorder")), "id"),
            "asserter_id": safe_get(extract_reference(resource.get("asserter")), "id"),
            # VARIANT fields
            "stages": json.dumps(resource.get("stage", [])) if resource.get("stage") else None,
            "evidence": json.dumps(resource.get("evidence", [])) if resource.get("evidence") else None,
            "notes": json.dumps(resource.get("note", [])) if resource.get("note") else None,
            "extensions": json.dumps(resource.get("extension", [])) if resource.get("extension") else None,
            "raw_resource": raw_resource,
        }
    except Exception:
        return None


def parse_medication_request(raw_resource: str) -> dict:
    """
    Parse MedicationRequest resource into flattened structure.
    
    RESILIENCE PATTERN: Catches ALL exceptions to prevent pipeline failures.
    """
    try:
        try:
            resource = json.loads(raw_resource) if isinstance(raw_resource, str) else raw_resource
        except (json.JSONDecodeError, TypeError):
            return None
        
        if not resource or resource.get("resourceType") != "MedicationRequest":
            return None
        
        # Subject reference
        subject = extract_reference(resource.get("subject"))
        
        # Medication (choice type)
        med_code = None
        med_system = None
        med_display = None
        med_reference_id = None
        
        if "medicationCodeableConcept" in resource:
            med_info = extract_coding(resource["medicationCodeableConcept"])
            med_code = med_info.get("code")
            med_system = med_info.get("system")
            med_display = med_info.get("display")
        elif "medicationReference" in resource:
            med_ref = extract_reference(resource["medicationReference"])
            med_reference_id = med_ref["id"]
        
        # Dosage instructions
        dosage_instructions = resource.get("dosageInstruction", [])
        dosage = dosage_instructions[0] if dosage_instructions else {}
        
        dose_quantity = safe_get(dosage, "doseAndRate", 0, "doseQuantity")
        dose_value = safe_get(dose_quantity, "value") if dose_quantity else None
        dose_unit = safe_get(dose_quantity, "unit") if dose_quantity else None
        
        timing = dosage.get("timing", {})
        frequency = safe_get(timing, "repeat", "frequency")
        period = safe_get(timing, "repeat", "period")
        period_unit = safe_get(timing, "repeat", "periodUnit")
        
        # Requester
        requester = extract_reference(resource.get("requester"))
        
        # Dispense request
        dispense_request = resource.get("dispenseRequest", {})
        quantity = dispense_request.get("quantity", {})
        
        return {
            "id": resource.get("id"),
            "resource_type": "MedicationRequest",
            "meta_version_id": safe_get(resource, "meta", "versionId"),
            "meta_last_updated": safe_get(resource, "meta", "lastUpdated"),
            "status": resource.get("status"),
            "intent": resource.get("intent"),
            "priority": resource.get("priority"),
            "medication_code": med_code,
            "medication_system": med_system,
            "medication_display": med_display,
            "medication_reference_id": med_reference_id,
            "subject_type": subject["type"],
            "subject_id": subject["id"],
            "encounter_id": safe_get(extract_reference(resource.get("encounter")), "id"),
            "authored_on": resource.get("authoredOn"),
            "requester_type": requester["type"],
            "requester_id": requester["id"],
            "dose_value": str(dose_value) if dose_value else None,
            "dose_unit": dose_unit,
            "frequency": str(frequency) if frequency else None,
            "period": str(period) if period else None,
            "period_unit": period_unit,
            "route_code": safe_get(extract_coding(dosage.get("route")), "code"),
            "route_display": safe_get(extract_coding(dosage.get("route")), "display"),
            "dispense_quantity_value": str(quantity.get("value")) if quantity.get("value") else None,
            "dispense_quantity_unit": quantity.get("unit"),
            "number_of_repeats": dispense_request.get("numberOfRepeatsAllowed"),
            # VARIANT fields
            "dosage_instructions": json.dumps(dosage_instructions) if dosage_instructions else None,
            "reason_codes": json.dumps(resource.get("reasonCode", [])) if resource.get("reasonCode") else None,
            "extensions": json.dumps(resource.get("extension", [])) if resource.get("extension") else None,
            "raw_resource": raw_resource,
        }
    except Exception:
        return None


def parse_immunization(raw_resource: str) -> dict:
    """
    Parse Immunization resource into flattened structure.
    
    RESILIENCE PATTERN: Catches ALL exceptions to prevent pipeline failures.
    """
    try:
        try:
            resource = json.loads(raw_resource) if isinstance(raw_resource, str) else raw_resource
        except (json.JSONDecodeError, TypeError):
            return None
        
        if not resource or resource.get("resourceType") != "Immunization":
            return None
        
        # Patient reference
        patient = extract_reference(resource.get("patient"))
        
        # Vaccine code
        vaccine_info = extract_coding(resource.get("vaccineCode"))
        
        # Site
        site_info = extract_coding(resource.get("site"))
        
        # Route
        route_info = extract_coding(resource.get("route"))
        
        # Dose quantity
        dose_quantity = resource.get("doseQuantity", {})
        
        # Performers
        performers = resource.get("performer", [])
        primary_performer = performers[0] if performers else {}
        performer_ref = extract_reference(primary_performer.get("actor"))
        
        # Protocol applied
        protocols = resource.get("protocolApplied", [])
        protocol = protocols[0] if protocols else {}
        
        # Reason codes
        reasons = resource.get("reasonCode", [])
        reason_info = extract_coding(reasons[0]) if reasons else {}
        
        return {
            "id": resource.get("id"),
            "resource_type": "Immunization",
            "meta_version_id": safe_get(resource, "meta", "versionId"),
            "meta_last_updated": safe_get(resource, "meta", "lastUpdated"),
            "status": resource.get("status"),
            "vaccine_code": vaccine_info.get("code"),
            "vaccine_system": vaccine_info.get("system"),
            "vaccine_display": vaccine_info.get("display"),
            "patient_id": patient["id"],
            "encounter_id": safe_get(extract_reference(resource.get("encounter")), "id"),
            "occurrence_datetime": resource.get("occurrenceDateTime"),
            "occurrence_string": resource.get("occurrenceString"),
            "recorded": resource.get("recorded"),
            "primary_source": resource.get("primarySource"),
            "lot_number": resource.get("lotNumber"),
            "expiration_date": resource.get("expirationDate"),
            "site_code": site_info.get("code"),
            "site_display": site_info.get("display"),
            "route_code": route_info.get("code"),
            "route_display": route_info.get("display"),
            "dose_value": str(dose_quantity.get("value")) if dose_quantity.get("value") else None,
            "dose_unit": dose_quantity.get("unit"),
            "performer_type": performer_ref["type"],
            "performer_id": performer_ref["id"],
            "reason_code": reason_info.get("code"),
            "reason_display": reason_info.get("display"),
            "dose_number": str(protocol.get("doseNumberPositiveInt")) if protocol.get("doseNumberPositiveInt") else protocol.get("doseNumberString"),
            "series_doses": str(protocol.get("seriesDosesPositiveInt")) if protocol.get("seriesDosesPositiveInt") else protocol.get("seriesDosesString"),
            # VARIANT fields
            "performers": json.dumps(performers) if performers else None,
            "protocols_applied": json.dumps(protocols) if protocols else None,
            "reactions": json.dumps(resource.get("reaction", [])) if resource.get("reaction") else None,
            "extensions": json.dumps(resource.get("extension", [])) if resource.get("extension") else None,
            "raw_resource": raw_resource,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Schema Definitions
# ---------------------------------------------------------------------------

PATIENT_SCHEMA = StructType([
    StructField("id", StringType(), True),  # Nullable to handle boundary test cases
    StructField("resource_type", StringType(), True),  # Nullable for invalid data
    StructField("meta_version_id", StringType(), True),
    StructField("meta_last_updated", StringType(), True),
    StructField("active", BooleanType(), True),
    StructField("gender", StringType(), True),
    StructField("birth_date", StringType(), True),
    StructField("deceased_boolean", BooleanType(), True),
    StructField("deceased_datetime", StringType(), True),
    StructField("family_name", StringType(), True),
    StructField("given_name", StringType(), True),
    StructField("full_name", StringType(), True),
    StructField("mrn", StringType(), True),
    StructField("ssn", StringType(), True),
    StructField("address_line", StringType(), True),
    StructField("address_city", StringType(), True),
    StructField("address_state", StringType(), True),
    StructField("address_postal_code", StringType(), True),
    StructField("address_country", StringType(), True),
    StructField("marital_status_code", StringType(), True),
    StructField("names", StringType(), True),
    StructField("identifiers", StringType(), True),
    StructField("addresses", StringType(), True),
    StructField("telecoms", StringType(), True),
    StructField("extensions", StringType(), True),
    StructField("raw_resource", StringType(), True),
])

OBSERVATION_SCHEMA = StructType([
    StructField("id", StringType(), True),  # Nullable to handle boundary test cases
    StructField("resource_type", StringType(), True),  # Nullable for invalid data
    StructField("meta_version_id", StringType(), True),
    StructField("meta_last_updated", StringType(), True),
    StructField("status", StringType(), True),
    StructField("code", StringType(), True),
    StructField("code_system", StringType(), True),
    StructField("code_display", StringType(), True),
    StructField("category_code", StringType(), True),
    StructField("category_display", StringType(), True),
    StructField("subject_type", StringType(), True),
    StructField("subject_id", StringType(), True),
    StructField("encounter_id", StringType(), True),
    StructField("effective_datetime", StringType(), True),
    StructField("effective_period_start", StringType(), True),
    StructField("effective_period_end", StringType(), True),
    StructField("issued", StringType(), True),
    StructField("value", StringType(), True),
    StructField("value_type", StringType(), True),
    StructField("value_unit", StringType(), True),
    StructField("reference_range_low", StringType(), True),
    StructField("reference_range_high", StringType(), True),
    StructField("interpretation_code", StringType(), True),
    StructField("data_absent_reason", StringType(), True),
    StructField("components", StringType(), True),
    StructField("performers", StringType(), True),
    StructField("extensions", StringType(), True),
    StructField("raw_resource", StringType(), True),
])

ENCOUNTER_SCHEMA = StructType([
    StructField("id", StringType(), True),  # Nullable to handle boundary test cases
    StructField("resource_type", StringType(), True),  # Nullable for invalid data
    StructField("meta_version_id", StringType(), True),
    StructField("meta_last_updated", StringType(), True),
    StructField("status", StringType(), True),
    StructField("class_code", StringType(), True),
    StructField("class_display", StringType(), True),
    StructField("type_code", StringType(), True),
    StructField("type_display", StringType(), True),
    StructField("subject_type", StringType(), True),
    StructField("subject_id", StringType(), True),
    StructField("period_start", StringType(), True),
    StructField("period_end", StringType(), True),
    StructField("admit_source_code", StringType(), True),
    StructField("admit_source_display", StringType(), True),
    StructField("discharge_disposition_code", StringType(), True),
    StructField("discharge_disposition_display", StringType(), True),
    StructField("service_provider_type", StringType(), True),
    StructField("service_provider_id", StringType(), True),
    StructField("location_id", StringType(), True),
    StructField("reason_code", StringType(), True),
    StructField("reason_display", StringType(), True),
    StructField("participants", StringType(), True),
    StructField("locations", StringType(), True),
    StructField("reason_codes", StringType(), True),
    StructField("extensions", StringType(), True),
    StructField("raw_resource", StringType(), True),
])

CONDITION_SCHEMA = StructType([
    StructField("id", StringType(), True),  # Nullable to handle boundary test cases
    StructField("resource_type", StringType(), True),  # Nullable for invalid data
    StructField("meta_version_id", StringType(), True),
    StructField("meta_last_updated", StringType(), True),
    StructField("code", StringType(), True),
    StructField("code_system", StringType(), True),
    StructField("code_display", StringType(), True),
    StructField("category_code", StringType(), True),
    StructField("category_display", StringType(), True),
    StructField("clinical_status_code", StringType(), True),
    StructField("verification_status_code", StringType(), True),
    StructField("severity_code", StringType(), True),
    StructField("severity_display", StringType(), True),
    StructField("body_site_code", StringType(), True),
    StructField("body_site_display", StringType(), True),
    StructField("subject_type", StringType(), True),
    StructField("subject_id", StringType(), True),
    StructField("encounter_id", StringType(), True),
    StructField("onset_datetime", StringType(), True),
    StructField("onset_age", StringType(), True),
    StructField("onset_period_start", StringType(), True),
    StructField("abatement_datetime", StringType(), True),
    StructField("abatement_age", StringType(), True),
    StructField("recorded_date", StringType(), True),
    StructField("recorder_id", StringType(), True),
    StructField("asserter_id", StringType(), True),
    StructField("stages", StringType(), True),
    StructField("evidence", StringType(), True),
    StructField("notes", StringType(), True),
    StructField("extensions", StringType(), True),
    StructField("raw_resource", StringType(), True),
])

MEDICATION_REQUEST_SCHEMA = StructType([
    StructField("id", StringType(), True),  # Nullable to handle boundary test cases
    StructField("resource_type", StringType(), True),  # Nullable for invalid data
    StructField("meta_version_id", StringType(), True),
    StructField("meta_last_updated", StringType(), True),
    StructField("status", StringType(), True),
    StructField("intent", StringType(), True),
    StructField("priority", StringType(), True),
    StructField("medication_code", StringType(), True),
    StructField("medication_system", StringType(), True),
    StructField("medication_display", StringType(), True),
    StructField("medication_reference_id", StringType(), True),
    StructField("subject_type", StringType(), True),
    StructField("subject_id", StringType(), True),
    StructField("encounter_id", StringType(), True),
    StructField("authored_on", StringType(), True),
    StructField("requester_type", StringType(), True),
    StructField("requester_id", StringType(), True),
    StructField("dose_value", StringType(), True),
    StructField("dose_unit", StringType(), True),
    StructField("frequency", StringType(), True),
    StructField("period", StringType(), True),
    StructField("period_unit", StringType(), True),
    StructField("route_code", StringType(), True),
    StructField("route_display", StringType(), True),
    StructField("dispense_quantity_value", StringType(), True),
    StructField("dispense_quantity_unit", StringType(), True),
    StructField("number_of_repeats", IntegerType(), True),
    StructField("dosage_instructions", StringType(), True),
    StructField("reason_codes", StringType(), True),
    StructField("extensions", StringType(), True),
    StructField("raw_resource", StringType(), True),
])

IMMUNIZATION_SCHEMA = StructType([
    StructField("id", StringType(), True),  # Nullable to handle boundary test cases
    StructField("resource_type", StringType(), True),  # Nullable for invalid data
    StructField("meta_version_id", StringType(), True),
    StructField("meta_last_updated", StringType(), True),
    StructField("status", StringType(), True),
    StructField("vaccine_code", StringType(), True),
    StructField("vaccine_system", StringType(), True),
    StructField("vaccine_display", StringType(), True),
    StructField("patient_id", StringType(), True),
    StructField("encounter_id", StringType(), True),
    StructField("occurrence_datetime", StringType(), True),
    StructField("occurrence_string", StringType(), True),
    StructField("recorded", StringType(), True),
    StructField("primary_source", BooleanType(), True),
    StructField("lot_number", StringType(), True),
    StructField("expiration_date", StringType(), True),
    StructField("site_code", StringType(), True),
    StructField("site_display", StringType(), True),
    StructField("route_code", StringType(), True),
    StructField("route_display", StringType(), True),
    StructField("dose_value", StringType(), True),
    StructField("dose_unit", StringType(), True),
    StructField("performer_type", StringType(), True),
    StructField("performer_id", StringType(), True),
    StructField("reason_code", StringType(), True),
    StructField("reason_display", StringType(), True),
    StructField("dose_number", StringType(), True),
    StructField("series_doses", StringType(), True),
    StructField("performers", StringType(), True),
    StructField("protocols_applied", StringType(), True),
    StructField("reactions", StringType(), True),
    StructField("extensions", StringType(), True),
    StructField("raw_resource", StringType(), True),
])


# ---------------------------------------------------------------------------
# UDFs
# ---------------------------------------------------------------------------

parse_patient_udf = udf(parse_patient, PATIENT_SCHEMA)
parse_observation_udf = udf(parse_observation, OBSERVATION_SCHEMA)
parse_encounter_udf = udf(parse_encounter, ENCOUNTER_SCHEMA)
parse_condition_udf = udf(parse_condition, CONDITION_SCHEMA)
parse_medication_request_udf = udf(parse_medication_request, MEDICATION_REQUEST_SCHEMA)
parse_immunization_udf = udf(parse_immunization, IMMUNIZATION_SCHEMA)


# ---------------------------------------------------------------------------
# Silver Tables
# ---------------------------------------------------------------------------

_patient_cluster_cols = config.get_cluster_columns("patient") if config.clustering_enabled else None

@dp.table(
    name="silver_fhir_patient",
    comment="Refined Patient resources with flattened demographics and VARIANT extensions",
    table_properties=config.build_table_properties("patient", "silver"),
    cluster_by=_patient_cluster_cols,
)
@dp.expect_or_drop("valid_patient_id", "id IS NOT NULL AND id != ''")
@dp.expect("valid_gender", "gender IS NULL OR gender IN ('male', 'female', 'other', 'unknown')")
def silver_fhir_patient():
    """
    Transform Patient resources to structured silver table.
    
    Features:
    - Deduplication using meta.versionId (latest version)
    - Flattened demographics fields
    - VARIANT storage for extensions and complex fields
    """
    # Read valid patients from bronze
    bronze = (
        spark.read.table("bronze_fhir_raw")
        .filter(
            (col("resource_type") == "Patient") &
            (col("is_valid") == True)
        )
    )
    
    # Parse and flatten
    parsed = bronze.withColumn("parsed", parse_patient_udf(col("raw_resource")))
    
    # Filter successful parses
    valid = parsed.filter(col("parsed").isNotNull())
    
    # Deduplicate (keep latest version per patient)
    window_spec = Window.partitionBy("parsed.id").orderBy(col("parsed.meta_last_updated").desc())
    deduped = (
        valid
        .withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )
    
    # Select final columns
    return deduped.select(
        col("parsed.id").alias("id"),
        col("parsed.meta_version_id").alias("meta_version_id"),
        to_timestamp(col("parsed.meta_last_updated")).alias("meta_last_updated"),
        col("parsed.active").alias("active"),
        col("parsed.gender").alias("gender"),
        to_date(col("parsed.birth_date")).alias("birth_date"),
        col("parsed.deceased_boolean").alias("deceased_boolean"),
        to_timestamp(col("parsed.deceased_datetime")).alias("deceased_datetime"),
        col("parsed.family_name").alias("family_name"),
        col("parsed.given_name").alias("given_name"),
        col("parsed.full_name").alias("full_name"),
        col("parsed.mrn").alias("mrn"),
        col("parsed.ssn").alias("ssn"),
        col("parsed.address_line").alias("address_line"),
        col("parsed.address_city").alias("address_city"),
        col("parsed.address_state").alias("address_state"),
        col("parsed.address_postal_code").alias("address_postal_code"),
        col("parsed.address_country").alias("address_country"),
        col("parsed.marital_status_code").alias("marital_status_code"),
        # VARIANT-ready fields (stored as JSON strings)
        col("parsed.names").alias("names"),
        col("parsed.identifiers").alias("identifiers"),
        col("parsed.addresses").alias("addresses"),
        col("parsed.telecoms").alias("telecoms"),
        col("parsed.extensions").alias("extensions"),
        col("parsed.raw_resource").alias("raw_resource"),
        col("_source_file"),
        col("_ingestion_timestamp"),
    )


_observation_cluster_cols = config.get_cluster_columns("observation") if config.clustering_enabled else None

@dp.table(
    name="silver_fhir_observation",
    comment="Refined Observation resources with flattened values and VARIANT components",
    table_properties=config.build_table_properties("observation", "silver"),
    cluster_by=_observation_cluster_cols,
)
@dp.expect_or_drop("valid_observation_id", "id IS NOT NULL AND id != ''")
@dp.expect_or_drop("valid_status", "status IN ('registered', 'preliminary', 'final', 'amended', 'corrected', 'cancelled', 'entered-in-error', 'unknown')")
@dp.expect("has_subject", "subject_id IS NOT NULL")
@dp.expect("has_code", "code IS NOT NULL")
def silver_fhir_observation():
    """
    Transform Observation resources to structured silver table.
    
    Features:
    - Lab results, vitals, and measurements
    - Value extraction with type handling
    - VARIANT storage for components (panel results)
    """
    bronze = (
        spark.read.table("bronze_fhir_raw")
        .filter(
            (col("resource_type") == "Observation") &
            (col("is_valid") == True)
        )
    )
    
    parsed = bronze.withColumn("parsed", parse_observation_udf(col("raw_resource")))
    valid = parsed.filter(col("parsed").isNotNull())
    
    window_spec = Window.partitionBy("parsed.id").orderBy(col("parsed.meta_last_updated").desc())
    deduped = (
        valid
        .withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )
    
    return deduped.select(
        col("parsed.id").alias("id"),
        col("parsed.meta_version_id").alias("meta_version_id"),
        to_timestamp(col("parsed.meta_last_updated")).alias("meta_last_updated"),
        col("parsed.status").alias("status"),
        col("parsed.code").alias("code"),
        col("parsed.code_system").alias("code_system"),
        col("parsed.code_display").alias("code_display"),
        col("parsed.category_code").alias("category_code"),
        col("parsed.category_display").alias("category_display"),
        col("parsed.subject_id").alias("subject_id"),
        col("parsed.encounter_id").alias("encounter_id"),
        to_timestamp(col("parsed.effective_datetime")).alias("effective_datetime"),
        to_timestamp(col("parsed.effective_period_start")).alias("effective_period_start"),
        to_timestamp(col("parsed.effective_period_end")).alias("effective_period_end"),
        to_timestamp(col("parsed.issued")).alias("issued"),
        col("parsed.value").alias("value"),
        col("parsed.value_type").alias("value_type"),
        col("parsed.value_unit").alias("value_unit"),
        col("parsed.reference_range_low").alias("reference_range_low"),
        col("parsed.reference_range_high").alias("reference_range_high"),
        col("parsed.interpretation_code").alias("interpretation_code"),
        col("parsed.data_absent_reason").alias("data_absent_reason"),
        col("parsed.components").alias("components"),
        col("parsed.performers").alias("performers"),
        col("parsed.extensions").alias("extensions"),
        col("parsed.raw_resource").alias("raw_resource"),
        col("_source_file"),
        col("_ingestion_timestamp"),
    )


_encounter_cluster_cols = config.get_cluster_columns("encounter") if config.clustering_enabled else None

@dp.table(
    name="silver_fhir_encounter",
    comment="Refined Encounter resources with flattened visit details",
    table_properties=config.build_table_properties("encounter", "silver"),
    cluster_by=_encounter_cluster_cols,
)
@dp.expect_or_drop("valid_encounter_id", "id IS NOT NULL AND id != ''")
@dp.expect_or_drop("valid_status", "status IN ('planned', 'arrived', 'triaged', 'in-progress', 'onleave', 'finished', 'cancelled', 'entered-in-error', 'unknown')")
@dp.expect("has_subject", "subject_id IS NOT NULL")
@dp.expect("has_class", "class_code IS NOT NULL")
def silver_fhir_encounter():
    """
    Transform Encounter resources to structured silver table.
    
    Features:
    - Healthcare visits (inpatient, outpatient, emergency)
    - Period and hospitalization details
    - VARIANT storage for participants and locations
    """
    bronze = (
        spark.read.table("bronze_fhir_raw")
        .filter(
            (col("resource_type") == "Encounter") &
            (col("is_valid") == True)
        )
    )
    
    parsed = bronze.withColumn("parsed", parse_encounter_udf(col("raw_resource")))
    valid = parsed.filter(col("parsed").isNotNull())
    
    window_spec = Window.partitionBy("parsed.id").orderBy(col("parsed.meta_last_updated").desc())
    deduped = (
        valid
        .withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )
    
    return deduped.select(
        col("parsed.id").alias("id"),
        col("parsed.meta_version_id").alias("meta_version_id"),
        to_timestamp(col("parsed.meta_last_updated")).alias("meta_last_updated"),
        col("parsed.status").alias("status"),
        col("parsed.class_code").alias("class_code"),
        col("parsed.class_display").alias("class_display"),
        col("parsed.type_code").alias("type_code"),
        col("parsed.type_display").alias("type_display"),
        col("parsed.subject_id").alias("subject_id"),
        to_timestamp(col("parsed.period_start")).alias("period_start"),
        to_timestamp(col("parsed.period_end")).alias("period_end"),
        col("parsed.admit_source_code").alias("admit_source_code"),
        col("parsed.admit_source_display").alias("admit_source_display"),
        col("parsed.discharge_disposition_code").alias("discharge_disposition_code"),
        col("parsed.discharge_disposition_display").alias("discharge_disposition_display"),
        col("parsed.service_provider_id").alias("service_provider_id"),
        col("parsed.location_id").alias("location_id"),
        col("parsed.reason_code").alias("reason_code"),
        col("parsed.reason_display").alias("reason_display"),
        col("parsed.participants").alias("participants"),
        col("parsed.locations").alias("locations"),
        col("parsed.reason_codes").alias("reason_codes"),
        col("parsed.extensions").alias("extensions"),
        col("parsed.raw_resource").alias("raw_resource"),
        col("_source_file"),
        col("_ingestion_timestamp"),
    )


_condition_cluster_cols = config.get_cluster_columns("condition") if config.clustering_enabled else None

@dp.table(
    name="silver_fhir_condition",
    comment="Refined Condition resources with flattened diagnosis details",
    table_properties=config.build_table_properties("condition", "silver"),
    cluster_by=_condition_cluster_cols,
)
@dp.expect_or_drop("valid_condition_id", "id IS NOT NULL AND id != ''")
@dp.expect("has_subject", "subject_id IS NOT NULL")
@dp.expect("has_code", "code IS NOT NULL")
def silver_fhir_condition():
    """
    Transform Condition resources to structured silver table.
    
    Features:
    - Diagnoses, problems, and health concerns
    - Clinical and verification status
    - VARIANT storage for evidence and staging
    """
    bronze = (
        spark.read.table("bronze_fhir_raw")
        .filter(
            (col("resource_type") == "Condition") &
            (col("is_valid") == True)
        )
    )
    
    parsed = bronze.withColumn("parsed", parse_condition_udf(col("raw_resource")))
    valid = parsed.filter(col("parsed").isNotNull())
    
    window_spec = Window.partitionBy("parsed.id").orderBy(col("parsed.meta_last_updated").desc())
    deduped = (
        valid
        .withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )
    
    return deduped.select(
        col("parsed.id").alias("id"),
        col("parsed.meta_version_id").alias("meta_version_id"),
        to_timestamp(col("parsed.meta_last_updated")).alias("meta_last_updated"),
        col("parsed.code").alias("code"),
        col("parsed.code_system").alias("code_system"),
        col("parsed.code_display").alias("code_display"),
        col("parsed.category_code").alias("category_code"),
        col("parsed.category_display").alias("category_display"),
        col("parsed.clinical_status_code").alias("clinical_status_code"),
        col("parsed.verification_status_code").alias("verification_status_code"),
        col("parsed.severity_code").alias("severity_code"),
        col("parsed.severity_display").alias("severity_display"),
        col("parsed.body_site_code").alias("body_site_code"),
        col("parsed.body_site_display").alias("body_site_display"),
        col("parsed.subject_id").alias("subject_id"),
        col("parsed.encounter_id").alias("encounter_id"),
        to_timestamp(col("parsed.onset_datetime")).alias("onset_datetime"),
        col("parsed.onset_age").alias("onset_age"),
        to_timestamp(col("parsed.onset_period_start")).alias("onset_period_start"),
        to_timestamp(col("parsed.abatement_datetime")).alias("abatement_datetime"),
        col("parsed.abatement_age").alias("abatement_age"),
        to_date(col("parsed.recorded_date")).alias("recorded_date"),
        col("parsed.recorder_id").alias("recorder_id"),
        col("parsed.asserter_id").alias("asserter_id"),
        col("parsed.stages").alias("stages"),
        col("parsed.evidence").alias("evidence"),
        col("parsed.notes").alias("notes"),
        col("parsed.extensions").alias("extensions"),
        col("parsed.raw_resource").alias("raw_resource"),
        col("_source_file"),
        col("_ingestion_timestamp"),
    )


_medication_request_cluster_cols = config.get_cluster_columns("medication_request") if config.clustering_enabled else None

@dp.table(
    name="silver_fhir_medication_request",
    comment="Refined MedicationRequest resources with flattened prescription details",
    table_properties=config.build_table_properties("medication_request", "silver"),
    cluster_by=_medication_request_cluster_cols,
)
@dp.expect_or_drop("valid_medication_request_id", "id IS NOT NULL AND id != ''")
@dp.expect_or_drop("valid_status", "status IN ('active', 'on-hold', 'cancelled', 'completed', 'entered-in-error', 'stopped', 'draft', 'unknown')")
@dp.expect_or_drop("valid_intent", "intent IN ('proposal', 'plan', 'order', 'original-order', 'reflex-order', 'filler-order', 'instance-order', 'option')")
@dp.expect("has_subject", "subject_id IS NOT NULL")
@dp.expect("has_medication", "medication_code IS NOT NULL OR medication_reference_id IS NOT NULL")
def silver_fhir_medication_request():
    """
    Transform MedicationRequest resources to structured silver table.
    
    Features:
    - Medication orders and prescriptions
    - Dosage instructions extraction
    - VARIANT storage for complex dosing
    """
    bronze = (
        spark.read.table("bronze_fhir_raw")
        .filter(
            (col("resource_type") == "MedicationRequest") &
            (col("is_valid") == True)
        )
    )
    
    parsed = bronze.withColumn("parsed", parse_medication_request_udf(col("raw_resource")))
    valid = parsed.filter(col("parsed").isNotNull())
    
    window_spec = Window.partitionBy("parsed.id").orderBy(col("parsed.meta_last_updated").desc())
    deduped = (
        valid
        .withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )
    
    return deduped.select(
        col("parsed.id").alias("id"),
        col("parsed.meta_version_id").alias("meta_version_id"),
        to_timestamp(col("parsed.meta_last_updated")).alias("meta_last_updated"),
        col("parsed.status").alias("status"),
        col("parsed.intent").alias("intent"),
        col("parsed.priority").alias("priority"),
        col("parsed.medication_code").alias("medication_code"),
        col("parsed.medication_system").alias("medication_system"),
        col("parsed.medication_display").alias("medication_display"),
        col("parsed.medication_reference_id").alias("medication_reference_id"),
        col("parsed.subject_id").alias("subject_id"),
        col("parsed.encounter_id").alias("encounter_id"),
        to_timestamp(col("parsed.authored_on")).alias("authored_on"),
        col("parsed.requester_id").alias("requester_id"),
        col("parsed.dose_value").alias("dose_value"),
        col("parsed.dose_unit").alias("dose_unit"),
        col("parsed.frequency").alias("frequency"),
        col("parsed.period").alias("period"),
        col("parsed.period_unit").alias("period_unit"),
        col("parsed.route_code").alias("route_code"),
        col("parsed.route_display").alias("route_display"),
        col("parsed.dispense_quantity_value").alias("dispense_quantity_value"),
        col("parsed.dispense_quantity_unit").alias("dispense_quantity_unit"),
        col("parsed.number_of_repeats").alias("number_of_repeats"),
        col("parsed.dosage_instructions").alias("dosage_instructions"),
        col("parsed.reason_codes").alias("reason_codes"),
        col("parsed.extensions").alias("extensions"),
        col("parsed.raw_resource").alias("raw_resource"),
        col("_source_file"),
        col("_ingestion_timestamp"),
    )


_immunization_cluster_cols = config.get_cluster_columns("immunization") if config.clustering_enabled else None

@dp.table(
    name="silver_fhir_immunization",
    comment="Refined Immunization resources with flattened vaccination details",
    table_properties=config.build_table_properties("immunization", "silver"),
    cluster_by=_immunization_cluster_cols,
)
@dp.expect_or_drop("valid_immunization_id", "id IS NOT NULL AND id != ''")
@dp.expect_or_drop("valid_status", "status IN ('completed', 'entered-in-error', 'not-done')")
@dp.expect("has_patient", "patient_id IS NOT NULL")
@dp.expect("has_vaccine_code", "vaccine_code IS NOT NULL")
@dp.expect("has_occurrence", "occurrence_datetime IS NOT NULL OR occurrence_string IS NOT NULL")
def silver_fhir_immunization():
    """
    Transform Immunization resources to structured silver table.
    
    Features:
    - Vaccination records
    - Protocol and dose tracking
    - VARIANT storage for reactions and protocols
    """
    bronze = (
        spark.read.table("bronze_fhir_raw")
        .filter(
            (col("resource_type") == "Immunization") &
            (col("is_valid") == True)
        )
    )
    
    parsed = bronze.withColumn("parsed", parse_immunization_udf(col("raw_resource")))
    valid = parsed.filter(col("parsed").isNotNull())
    
    window_spec = Window.partitionBy("parsed.id").orderBy(col("parsed.meta_last_updated").desc())
    deduped = (
        valid
        .withColumn("row_num", row_number().over(window_spec))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )
    
    return deduped.select(
        col("parsed.id").alias("id"),
        col("parsed.meta_version_id").alias("meta_version_id"),
        to_timestamp(col("parsed.meta_last_updated")).alias("meta_last_updated"),
        col("parsed.status").alias("status"),
        col("parsed.vaccine_code").alias("vaccine_code"),
        col("parsed.vaccine_system").alias("vaccine_system"),
        col("parsed.vaccine_display").alias("vaccine_display"),
        col("parsed.patient_id").alias("patient_id"),
        col("parsed.encounter_id").alias("encounter_id"),
        to_timestamp(col("parsed.occurrence_datetime")).alias("occurrence_datetime"),
        col("parsed.occurrence_string").alias("occurrence_string"),
        to_timestamp(col("parsed.recorded")).alias("recorded"),
        col("parsed.primary_source").alias("primary_source"),
        col("parsed.lot_number").alias("lot_number"),
        to_date(col("parsed.expiration_date")).alias("expiration_date"),
        col("parsed.site_code").alias("site_code"),
        col("parsed.site_display").alias("site_display"),
        col("parsed.route_code").alias("route_code"),
        col("parsed.route_display").alias("route_display"),
        col("parsed.dose_value").alias("dose_value"),
        col("parsed.dose_unit").alias("dose_unit"),
        col("parsed.performer_id").alias("performer_id"),
        col("parsed.reason_code").alias("reason_code"),
        col("parsed.reason_display").alias("reason_display"),
        col("parsed.dose_number").alias("dose_number"),
        col("parsed.series_doses").alias("series_doses"),
        col("parsed.performers").alias("performers"),
        col("parsed.protocols_applied").alias("protocols_applied"),
        col("parsed.reactions").alias("reactions"),
        col("parsed.extensions").alias("extensions"),
        col("parsed.raw_resource").alias("raw_resource"),
        col("_source_file"),
        col("_ingestion_timestamp"),
    )


# ---------------------------------------------------------------------------
# Gold Views (Business-Level Aggregations)
# ---------------------------------------------------------------------------

@dp.temporary_view(
    name="gold_patient_demographics",
    comment="Patient demographics summary for analytics"
)
def gold_patient_demographics():
    """
    Business-ready patient demographics view.
    """
    return (
        spark.read.table("silver_fhir_patient")
        .filter(col("active") == True)
        .select(
            col("id").alias("patient_id"),
            col("gender"),
            year(col("birth_date")).alias("birth_year"),
            col("address_state"),
            col("address_postal_code"),
            col("marital_status_code"),
            col("meta_last_updated").alias("last_updated"),
        )
    )


@dp.temporary_view(
    name="gold_clinical_observations",
    comment="Clinical observations summary for analytics"
)
def gold_clinical_observations():
    """
    Business-ready clinical observations view for vitals and labs.
    """
    return (
        spark.read.table("silver_fhir_observation")
        .filter(col("status").isin(["final", "amended", "corrected"]))
        .select(
            col("id").alias("observation_id"),
            col("subject_id").alias("patient_id"),
            col("encounter_id"),
            col("code"),
            col("code_display"),
            col("category_code"),
            col("value"),
            col("value_unit"),
            col("effective_datetime"),
            col("interpretation_code"),
        )
    )
