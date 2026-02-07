"""
FHIR R4 Parser and Validator

This module provides comprehensive parsing and validation for FHIR R4 resources.
Designed for use in Spark Declarative Pipelines (SDP/DLT).

Key Design Decisions:
1. ALL parsing logic is inlined (no external imports) for executor access
2. Validation follows FHIR R4 specification
3. Returns structured results suitable for Delta tables
4. Supports schema evolution via VARIANT-friendly output

Usage:
    validator = FhirValidator()
    result = validator.validate(resource)
    
    parser = FhirParser()
    parsed = parser.parse(resource)

Reference: https://hl7.org/fhir/R4/
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
import re


# =============================================================================
# Data Classes for Results
# =============================================================================

@dataclass
class ValidationResult:
    """Result of FHIR resource validation."""
    is_valid: bool
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def __str__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return f"ValidationResult({status}, {self.resource_type}/{self.resource_id}, errors={len(self.errors)}, warnings={len(self.warnings)})"


@dataclass
class QuarantineRecord:
    """Record for quarantined (failed) resources."""
    quarantine_id: str
    raw_data: str  # JSON string of original data
    error_message: str
    error_type: str  # PARSE, VALIDATION, SCHEMA, TRANSFORM
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reprocess_attempts: int = 0
    last_reprocess_time: Optional[datetime] = None
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        # Convert datetime to ISO string for JSON compatibility
        result['timestamp'] = self.timestamp.isoformat() if self.timestamp else None
        result['last_reprocess_time'] = self.last_reprocess_time.isoformat() if self.last_reprocess_time else None
        return result
    
    def mark_reprocess_attempt(self, error_message: str) -> None:
        """Mark a reprocessing attempt."""
        self.reprocess_attempts += 1
        self.last_reprocess_time = datetime.utcnow()
        self.error_message = error_message


# =============================================================================
# FHIR R4 Constants (Inlined for executor access)
# =============================================================================

# Supported resource types (FHIR R4)
SUPPORTED_RESOURCE_TYPES = {
    "Patient", "Observation", "Encounter", "MedicationRequest",
    "DiagnosticReport", "Immunization", "Procedure", "Condition",
    "AllergyIntolerance", "Bundle", "Practitioner", "Organization",
    "Location", "Medication", "ServiceRequest", "CarePlan",
    "CareTeam", "Goal", "Device", "DocumentReference",
    "Composition", "Coverage", "Claim", "ExplanationOfBenefit",
}

# Required fields by resource type (FHIR R4 specification)
REQUIRED_FIELDS = {
    "Patient": [],  # Patient has no required fields beyond resourceType
    "Observation": ["status", "code"],
    "Encounter": ["status", "class"],
    "MedicationRequest": ["status", "intent", "subject"],  # medication[x] is choice
    "DiagnosticReport": ["status", "code"],
    "Immunization": ["status", "vaccineCode", "patient"],  # occurrence[x] is choice
    "Procedure": ["status", "subject"],  # code is 0..1 in R4
    "Condition": ["subject"],  # clinicalStatus only if not entered-in-error
    "AllergyIntolerance": ["patient"],
    "Bundle": ["type"],
}

# Valid enum values for common fields
VALID_OBSERVATION_STATUS = {
    "registered", "preliminary", "final", "amended", 
    "corrected", "cancelled", "entered-in-error", "unknown"
}

VALID_ENCOUNTER_STATUS = {
    "planned", "arrived", "triaged", "in-progress",
    "onleave", "finished", "cancelled", "entered-in-error", "unknown"
}

VALID_MEDICATION_REQUEST_STATUS = {
    "active", "on-hold", "cancelled", "completed",
    "entered-in-error", "stopped", "draft", "unknown"
}

VALID_MEDICATION_REQUEST_INTENT = {
    "proposal", "plan", "order", "original-order",
    "reflex-order", "filler-order", "instance-order", "option"
}

VALID_IMMUNIZATION_STATUS = {
    "completed", "entered-in-error", "not-done"
}

VALID_PATIENT_GENDER = {
    "male", "female", "other", "unknown"
}

VALID_CONDITION_CLINICAL_STATUS = {
    "active", "recurrence", "relapse", "inactive", "remission", "resolved"
}

VALID_CONDITION_VERIFICATION_STATUS = {
    "unconfirmed", "provisional", "differential", "confirmed",
    "refuted", "entered-in-error"
}

VALID_DIAGNOSTIC_REPORT_STATUS = {
    "registered", "partial", "preliminary", "final",
    "amended", "corrected", "appended", "cancelled", "entered-in-error", "unknown"
}

VALID_BUNDLE_TYPE = {
    "document", "message", "transaction", "transaction-response",
    "batch", "batch-response", "history", "searchset", "collection"
}


# =============================================================================
# Helper Functions (Inlined)
# =============================================================================

def extract_coding(codeable_concept: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract code, display, system from a CodeableConcept.
    
    Args:
        codeable_concept: FHIR CodeableConcept structure
        
    Returns:
        Dict with code, display, system, text fields
    """
    if not codeable_concept:
        return {"code": None, "display": None, "system": None, "text": None}
    
    result = {
        "code": None,
        "display": None,
        "system": None,
        "text": codeable_concept.get("text")
    }
    
    codings = codeable_concept.get("coding", [])
    if codings and len(codings) > 0:
        first_coding = codings[0]
        result["code"] = first_coding.get("code")
        result["display"] = first_coding.get("display")
        result["system"] = first_coding.get("system")
    
    return result


def extract_reference(reference: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract reference string and parse type/id.
    
    Args:
        reference: FHIR Reference structure
        
    Returns:
        Dict with reference, type, id, display fields
    """
    if not reference:
        return {"reference": None, "type": None, "id": None, "display": None}
    
    result = {
        "reference": reference.get("reference"),
        "type": None,
        "id": None,
        "display": reference.get("display")
    }
    
    ref_str = reference.get("reference", "")
    if ref_str and "/" in ref_str:
        parts = ref_str.split("/")
        if len(parts) >= 2:
            result["type"] = parts[0]
            result["id"] = parts[1]
    
    return result


def extract_identifier(identifiers: Optional[List[Dict[str, Any]]], 
                       type_code: Optional[str] = None) -> Optional[str]:
    """
    Extract identifier value, optionally filtered by type code.
    
    Args:
        identifiers: List of FHIR Identifier structures
        type_code: Optional type code to filter (e.g., "MR" for MRN)
        
    Returns:
        Identifier value string or None
    """
    if not identifiers:
        return None
    
    for identifier in identifiers:
        if type_code:
            # Check type.coding for the specified code
            id_type = identifier.get("type", {})
            codings = id_type.get("coding", [])
            for coding in codings:
                if coding.get("code") == type_code:
                    return identifier.get("value")
        else:
            # Return first identifier value
            return identifier.get("value")
    
    # If type_code specified but not found, return first value
    if type_code and identifiers:
        return identifiers[0].get("value")
    
    return None


def extract_quantity(quantity: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract value and unit from a Quantity.
    
    Args:
        quantity: FHIR Quantity structure
        
    Returns:
        Dict with value, unit, system, code fields
    """
    if not quantity:
        return {"value": None, "unit": None, "system": None, "code": None}
    
    return {
        "value": quantity.get("value"),
        "unit": quantity.get("unit"),
        "system": quantity.get("system"),
        "code": quantity.get("code")
    }


def extract_period(period: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract start and end from a Period.
    
    Args:
        period: FHIR Period structure
        
    Returns:
        Dict with start, end fields
    """
    if not period:
        return {"start": None, "end": None}
    
    return {
        "start": period.get("start"),
        "end": period.get("end")
    }


def extract_name(names: Optional[List[Dict[str, Any]]], 
                 use: str = "official") -> Dict[str, Any]:
    """
    Extract name fields, preferring specified use.
    
    Args:
        names: List of FHIR HumanName structures
        use: Preferred name use (official, usual, nickname, etc.)
        
    Returns:
        Dict with family, given, prefix, suffix fields
    """
    if not names:
        return {"family": None, "given": None, "prefix": None, "suffix": None}
    
    # Try to find name with specified use
    selected = None
    for name in names:
        if name.get("use") == use:
            selected = name
            break
    
    # Fall back to first name
    if not selected:
        selected = names[0]
    
    given_list = selected.get("given", [])
    prefix_list = selected.get("prefix", [])
    suffix_list = selected.get("suffix", [])
    
    return {
        "family": selected.get("family"),
        "given": given_list[0] if given_list else None,
        "given_all": given_list,
        "prefix": prefix_list[0] if prefix_list else None,
        "suffix": suffix_list[0] if suffix_list else None
    }


def extract_address(addresses: Optional[List[Dict[str, Any]]], 
                    use: str = "home") -> Dict[str, Any]:
    """
    Extract address fields, preferring specified use.
    
    Args:
        addresses: List of FHIR Address structures
        use: Preferred address use (home, work, temp, etc.)
        
    Returns:
        Dict with line, city, state, postalCode, country fields
    """
    if not addresses:
        return {
            "line": None, "city": None, "state": None,
            "postal_code": None, "country": None
        }
    
    # Try to find address with specified use
    selected = None
    for addr in addresses:
        if addr.get("use") == use:
            selected = addr
            break
    
    # Fall back to first address
    if not selected:
        selected = addresses[0]
    
    lines = selected.get("line", [])
    
    return {
        "line": lines[0] if lines else None,
        "line_all": lines,
        "city": selected.get("city"),
        "state": selected.get("state"),
        "postal_code": selected.get("postalCode"),
        "country": selected.get("country")
    }


def extract_telecom(telecoms: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Extract phone and email from telecom list.
    
    Args:
        telecoms: List of FHIR ContactPoint structures
        
    Returns:
        Dict with phone_home, phone_work, phone_mobile, email fields
    """
    if not telecoms:
        return {
            "phone_home": None, "phone_work": None, 
            "phone_mobile": None, "email": None
        }
    
    result = {
        "phone_home": None,
        "phone_work": None,
        "phone_mobile": None,
        "email": None
    }
    
    for telecom in telecoms:
        system = telecom.get("system")
        use = telecom.get("use")
        value = telecom.get("value")
        
        if system == "phone":
            if use == "home" and not result["phone_home"]:
                result["phone_home"] = value
            elif use == "work" and not result["phone_work"]:
                result["phone_work"] = value
            elif use == "mobile" and not result["phone_mobile"]:
                result["phone_mobile"] = value
        elif system == "email" and not result["email"]:
            result["email"] = value
    
    return result


def parse_fhir_datetime(dt_string: Optional[str]) -> Optional[str]:
    """
    Parse and normalize FHIR datetime string.
    
    FHIR supports: YYYY, YYYY-MM, YYYY-MM-DD, YYYY-MM-DDThh:mm:ss+zz:zz
    
    Args:
        dt_string: FHIR datetime string
        
    Returns:
        Normalized datetime string or None
    """
    if not dt_string:
        return None
    
    # Already in good format, return as-is
    return dt_string


def is_valid_fhir_date(date_string: Optional[str]) -> bool:
    """
    Check if string is a valid FHIR date format.
    
    Valid formats: YYYY, YYYY-MM, YYYY-MM-DD
    
    Args:
        date_string: Date string to validate
        
    Returns:
        True if valid FHIR date format
    """
    if not date_string:
        return True  # None is valid (optional field)
    
    # YYYY
    if re.match(r"^\d{4}$", date_string):
        return True
    # YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", date_string):
        return True
    # YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_string):
        return True
    
    return False


def is_valid_fhir_datetime(datetime_string: Optional[str]) -> bool:
    """
    Check if string is a valid FHIR datetime format.
    
    Args:
        datetime_string: Datetime string to validate
        
    Returns:
        True if valid FHIR datetime format
    """
    if not datetime_string:
        return True  # None is valid
    
    # Check date formats first
    if is_valid_fhir_date(datetime_string):
        return True
    
    # Full datetime with timezone: YYYY-MM-DDThh:mm:ss+zz:zz or Z
    datetime_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
    if re.match(datetime_pattern, datetime_string):
        return True
    
    return False


# =============================================================================
# FhirValidator Class
# =============================================================================

class FhirValidator:
    """
    Validates FHIR R4 resources against the specification.
    
    Features:
    - Validates resourceType
    - Validates required fields by resource type
    - Validates enum values (status, gender, etc.)
    - Validates data types (dates, references)
    - Supports strict mode for additional checks
    
    Usage:
        validator = FhirValidator()
        result = validator.validate(resource)
        if result.is_valid:
            # Process resource
        else:
            # Handle errors
    """
    
    def __init__(self, strict: bool = False):
        """
        Initialize validator.
        
        Args:
            strict: Enable strict validation mode (more warnings)
        """
        self.strict = strict
    
    def validate(self, resource: Dict[str, Any]) -> ValidationResult:
        """
        Validate a FHIR resource.
        
        Args:
            resource: FHIR resource as dictionary
            
        Returns:
            ValidationResult with is_valid, errors, warnings
        """
        errors = []
        warnings = []
        
        # Check for empty/None input
        if not resource:
            return ValidationResult(
                is_valid=False,
                errors=["Resource is empty or None"]
            )
        
        # Validate resourceType
        resource_type = resource.get("resourceType")
        if not resource_type:
            return ValidationResult(
                is_valid=False,
                errors=["Missing required field: resourceType"]
            )
        
        if resource_type not in SUPPORTED_RESOURCE_TYPES:
            errors.append(f"Unknown resourceType: {resource_type}")
        
        # Get resource ID (for result, not validation error if missing)
        resource_id = resource.get("id")
        if not resource_id and self.strict:
            warnings.append("Missing id (recommended)")
        
        # Validate required fields
        required = REQUIRED_FIELDS.get(resource_type, [])
        for field_name in required:
            if not self._has_field(resource, field_name):
                errors.append(f"Missing required field: {field_name}")
        
        # Validate choice fields (medication[x], occurrence[x], etc.)
        self._validate_choice_fields(resource, resource_type, errors)
        
        # Validate enum values
        self._validate_enum_values(resource, resource_type, errors)
        
        # Validate data types
        self._validate_data_types(resource, resource_type, errors, warnings)
        
        # Bundle-specific validation
        if resource_type == "Bundle":
            self._validate_bundle(resource, errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            resource_type=resource_type,
            resource_id=resource_id,
            errors=errors,
            warnings=warnings
        )
    
    def _has_field(self, resource: Dict[str, Any], field_name: str) -> bool:
        """Check if resource has a non-empty field."""
        value = resource.get(field_name)
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, (list, dict)) and not value:
            return False
        return True
    
    def _validate_choice_fields(self, resource: Dict[str, Any], 
                                 resource_type: str, errors: List[str]) -> None:
        """Validate choice type fields (field[x])."""
        
        if resource_type == "MedicationRequest":
            # Must have medication[x] - medicationCodeableConcept or medicationReference
            has_med = (
                self._has_field(resource, "medicationCodeableConcept") or
                self._has_field(resource, "medicationReference")
            )
            if not has_med:
                errors.append("Missing required field: medication[x] (medicationCodeableConcept or medicationReference)")
        
        if resource_type == "Immunization":
            # Must have occurrence[x] - occurrenceDateTime or occurrenceString
            has_occurrence = (
                self._has_field(resource, "occurrenceDateTime") or
                self._has_field(resource, "occurrenceString")
            )
            if not has_occurrence:
                errors.append("Missing required field: occurrence[x] (occurrenceDateTime or occurrenceString)")
    
    def _validate_enum_values(self, resource: Dict[str, Any],
                               resource_type: str, errors: List[str]) -> None:
        """Validate enum fields have valid values."""
        
        # Patient gender
        if resource_type == "Patient":
            gender = resource.get("gender")
            if gender and gender not in VALID_PATIENT_GENDER:
                errors.append(f"Invalid gender value: {gender}. Must be one of: {', '.join(VALID_PATIENT_GENDER)}")
        
        # Observation status
        if resource_type == "Observation":
            status = resource.get("status")
            if status and status not in VALID_OBSERVATION_STATUS:
                errors.append(f"Invalid status value: {status}. Must be one of: {', '.join(VALID_OBSERVATION_STATUS)}")
        
        # Encounter status
        if resource_type == "Encounter":
            status = resource.get("status")
            if status and status not in VALID_ENCOUNTER_STATUS:
                errors.append(f"Invalid status value: {status}. Must be one of: {', '.join(VALID_ENCOUNTER_STATUS)}")
        
        # MedicationRequest status and intent
        if resource_type == "MedicationRequest":
            status = resource.get("status")
            if status and status not in VALID_MEDICATION_REQUEST_STATUS:
                errors.append(f"Invalid status value: {status}")
            
            intent = resource.get("intent")
            if intent and intent not in VALID_MEDICATION_REQUEST_INTENT:
                errors.append(f"Invalid intent value: {intent}. Must be one of: {', '.join(VALID_MEDICATION_REQUEST_INTENT)}")
        
        # Immunization status
        if resource_type == "Immunization":
            status = resource.get("status")
            if status and status not in VALID_IMMUNIZATION_STATUS:
                errors.append(f"Invalid status value: {status}")
        
        # Condition clinical/verification status
        if resource_type == "Condition":
            clinical = resource.get("clinicalStatus", {})
            if clinical:
                clinical_code = extract_coding(clinical).get("code")
                if clinical_code and clinical_code not in VALID_CONDITION_CLINICAL_STATUS:
                    errors.append(f"Invalid clinicalStatus code: {clinical_code}")
            
            verification = resource.get("verificationStatus", {})
            if verification:
                verification_code = extract_coding(verification).get("code")
                if verification_code and verification_code not in VALID_CONDITION_VERIFICATION_STATUS:
                    errors.append(f"Invalid verificationStatus code: {verification_code}")
        
        # DiagnosticReport status
        if resource_type == "DiagnosticReport":
            status = resource.get("status")
            if status and status not in VALID_DIAGNOSTIC_REPORT_STATUS:
                errors.append(f"Invalid status value: {status}")
        
        # Bundle type
        if resource_type == "Bundle":
            bundle_type = resource.get("type")
            if bundle_type and bundle_type not in VALID_BUNDLE_TYPE:
                errors.append(f"Invalid Bundle type: {bundle_type}")
    
    def _validate_data_types(self, resource: Dict[str, Any],
                              resource_type: str, 
                              errors: List[str],
                              warnings: List[str]) -> None:
        """Validate data type formats (dates, etc.)."""
        
        # Validate date fields
        date_fields = ["birthDate", "deceasedDateTime", "recordedDate", 
                       "onsetDateTime", "abatementDateTime", "authoredOn",
                       "effectiveDateTime", "issued", "occurrenceDateTime"]
        
        for field_name in date_fields:
            value = resource.get(field_name)
            if value:
                if field_name == "birthDate":
                    if not is_valid_fhir_date(value):
                        warnings.append(f"Invalid date format for {field_name}: {value}")
                else:
                    if not is_valid_fhir_datetime(value):
                        warnings.append(f"Invalid datetime format for {field_name}: {value}")
        
        # Validate Period fields
        period_fields = ["period", "effectivePeriod"]
        for field_name in period_fields:
            period = resource.get(field_name)
            if period:
                start = period.get("start")
                end = period.get("end")
                if start and not is_valid_fhir_datetime(start):
                    warnings.append(f"Invalid datetime format for {field_name}.start: {start}")
                if end and not is_valid_fhir_datetime(end):
                    warnings.append(f"Invalid datetime format for {field_name}.end: {end}")
        
        # Check for null values where not expected
        if resource.get("id") is None and "id" in resource:
            # id key exists but is null
            errors.append("id field cannot be null (omit if not present)")
    
    def _validate_bundle(self, bundle: Dict[str, Any], 
                          errors: List[str], warnings: List[str]) -> None:
        """Validate Bundle-specific rules."""
        entries = bundle.get("entry", [])
        
        for i, entry in enumerate(entries):
            resource = entry.get("resource")
            if resource:
                # Validate each entry resource
                entry_result = self.validate(resource)
                if not entry_result.is_valid:
                    for err in entry_result.errors:
                        warnings.append(f"Bundle entry[{i}]: {err}")


# =============================================================================
# FhirParser Class
# =============================================================================

class FhirParser:
    """
    Parses FHIR R4 resources into flattened dictionaries.
    
    Features:
    - Extracts key fields from all supported resource types
    - Flattens nested structures for common queries
    - Preserves complex structures for VARIANT columns
    - Handles edge cases gracefully
    
    Usage:
        parser = FhirParser()
        result = parser.parse(resource)
    """
    
    def __init__(self, quarantine_handler: Optional['QuarantineHandler'] = None):
        """
        Initialize parser.
        
        Args:
            quarantine_handler: Optional handler for failed records
        """
        self.quarantine_handler = quarantine_handler
        self.validator = FhirValidator()
    
    def parse(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a FHIR resource into a flattened dictionary.
        
        Args:
            resource: FHIR resource as dictionary
            
        Returns:
            Flattened dictionary with extracted fields
        """
        # Handle None/empty
        if not resource:
            return {
                "_parse_error": "Resource is empty or None",
                "_quarantine": True
            }
        
        # Get resource type
        resource_type = resource.get("resourceType")
        if not resource_type:
            return {
                "_parse_error": "Missing resourceType",
                "_quarantine": True,
                "_raw_resource": resource
            }
        
        # Base result with common fields
        result = {
            "resource_type": resource_type,
            "id": resource.get("id"),
            "raw_resource": resource,  # Will be VARIANT in Delta
            "_parse_error": None,
            "_parse_warning": None,
            "_quarantine": False,
        }
        
        # Extract meta
        meta = resource.get("meta", {})
        result["meta"] = meta
        result["meta_version_id"] = meta.get("versionId")
        result["meta_last_updated"] = meta.get("lastUpdated")
        result["meta_source"] = meta.get("source")
        
        # Extract extensions (preserve as VARIANT)
        result["extensions"] = resource.get("extension", [])
        
        # Extract contained resources (preserve as VARIANT)
        result["contained"] = resource.get("contained", [])
        
        # Parse based on resource type
        try:
            if resource_type == "Patient":
                self._parse_patient(resource, result)
            elif resource_type == "Observation":
                self._parse_observation(resource, result)
            elif resource_type == "Encounter":
                self._parse_encounter(resource, result)
            elif resource_type == "MedicationRequest":
                self._parse_medication_request(resource, result)
            elif resource_type == "DiagnosticReport":
                self._parse_diagnostic_report(resource, result)
            elif resource_type == "Immunization":
                self._parse_immunization(resource, result)
            elif resource_type == "Condition":
                self._parse_condition(resource, result)
            elif resource_type == "Bundle":
                # Bundle is handled separately
                result["_parse_warning"] = "Bundle should be processed with parse_bundle()"
            elif resource_type not in SUPPORTED_RESOURCE_TYPES:
                result["_parse_warning"] = f"Unknown resource type: {resource_type}"
        except Exception as e:
            result["_parse_error"] = f"Parse error: {str(e)}"
            result["_quarantine"] = True
        
        return result
    
    def parse_json_string(self, json_string: str) -> Dict[str, Any]:
        """
        Parse a JSON string into a FHIR resource.
        
        Args:
            json_string: JSON string
            
        Returns:
            Parsed resource dictionary
        """
        try:
            resource = json.loads(json_string)
            return self.parse(resource)
        except json.JSONDecodeError as e:
            return {
                "_parse_error": f"JSON parse error: {str(e)}",
                "_quarantine": True,
                "_raw_string": json_string[:1000] if len(json_string) > 1000 else json_string
            }
    
    def parse_bundle(self, bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse a Bundle and return individual parsed resources.
        
        Args:
            bundle: FHIR Bundle resource
            
        Returns:
            List of parsed resources
        """
        if not bundle or bundle.get("resourceType") != "Bundle":
            return [{
                "_parse_error": "Not a valid Bundle",
                "_quarantine": True,
                "_raw_resource": bundle
            }]
        
        entries = bundle.get("entry", [])
        results = []
        
        bundle_id = bundle.get("id")
        bundle_type = bundle.get("type")
        bundle_timestamp = bundle.get("timestamp")
        
        for i, entry in enumerate(entries):
            resource = entry.get("resource")
            if resource:
                parsed = self.parse(resource)
                # Add bundle metadata
                parsed["_bundle_id"] = bundle_id
                parsed["_bundle_type"] = bundle_type
                parsed["_bundle_timestamp"] = bundle_timestamp
                parsed["_bundle_entry_index"] = i
                parsed["_bundle_full_url"] = entry.get("fullUrl")
                results.append(parsed)
        
        return results
    
    def _parse_patient(self, resource: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Parse Patient-specific fields."""
        
        # Demographics
        result["gender"] = resource.get("gender")
        result["birth_date"] = resource.get("birthDate")
        result["active"] = resource.get("active")
        
        # Deceased
        result["deceased"] = resource.get("deceasedBoolean", False)
        result["deceased_datetime"] = resource.get("deceasedDateTime")
        if result["deceased_datetime"]:
            result["deceased"] = True
        
        # Name
        names = resource.get("name", [])
        result["names"] = names  # VARIANT
        name_info = extract_name(names)
        result["name_family"] = name_info["family"]
        result["name_given"] = name_info["given"]
        result["name_prefix"] = name_info["prefix"]
        result["name_suffix"] = name_info["suffix"]
        
        # Identifiers
        identifiers = resource.get("identifier", [])
        result["identifiers"] = identifiers  # VARIANT
        result["identifier_mrn"] = extract_identifier(identifiers, "MR")
        result["identifier_ssn"] = extract_identifier(identifiers, "SS")
        
        # Address
        addresses = resource.get("address", [])
        result["addresses"] = addresses  # VARIANT
        addr_info = extract_address(addresses)
        result["address_line"] = addr_info["line"]
        result["address_city"] = addr_info["city"]
        result["address_state"] = addr_info["state"]
        result["address_postal_code"] = addr_info["postal_code"]
        result["address_country"] = addr_info["country"]
        
        # Telecom
        telecoms = resource.get("telecom", [])
        result["telecoms"] = telecoms  # VARIANT
        telecom_info = extract_telecom(telecoms)
        result["phone_home"] = telecom_info["phone_home"]
        result["phone_work"] = telecom_info["phone_work"]
        result["phone_mobile"] = telecom_info["phone_mobile"]
        result["email"] = telecom_info["email"]
        
        # Contacts
        result["contacts"] = resource.get("contact", [])  # VARIANT
        
        # Managing organization
        managing_org = extract_reference(resource.get("managingOrganization"))
        result["managing_organization_ref"] = managing_org["reference"]
        result["managing_organization_id"] = managing_org["id"]
        
        # General practitioner
        gp_list = resource.get("generalPractitioner", [])
        if gp_list:
            gp = extract_reference(gp_list[0])
            result["general_practitioner_ref"] = gp["reference"]
            result["general_practitioner_id"] = gp["id"]
        
        # Marital status
        marital = extract_coding(resource.get("maritalStatus"))
        result["marital_status_code"] = marital["code"]
        result["marital_status_display"] = marital["display"]
        
        # Language
        communications = resource.get("communication", [])
        if communications:
            for comm in communications:
                if comm.get("preferred"):
                    lang = extract_coding(comm.get("language"))
                    result["preferred_language"] = lang["code"]
                    break
    
    def _parse_observation(self, resource: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Parse Observation-specific fields."""
        
        result["status"] = resource.get("status")
        
        # Category
        categories = resource.get("category", [])
        result["categories"] = categories  # VARIANT
        if categories:
            cat = extract_coding(categories[0])
            result["category_code"] = cat["code"]
            result["category_display"] = cat["display"]
        
        # Code
        code = resource.get("code", {})
        result["code"] = code  # VARIANT
        code_info = extract_coding(code)
        result["code_code"] = code_info["code"]
        result["code_display"] = code_info["display"]
        result["code_system"] = code_info["system"]
        result["code_text"] = code_info["text"]
        
        # Subject (patient)
        subject = extract_reference(resource.get("subject"))
        result["subject_ref"] = subject["reference"]
        result["patient_id"] = subject["id"]
        
        # Encounter
        encounter = extract_reference(resource.get("encounter"))
        result["encounter_ref"] = encounter["reference"]
        result["encounter_id"] = encounter["id"]
        
        # Effective date/time
        result["effective_datetime"] = resource.get("effectiveDateTime")
        effective_period = resource.get("effectivePeriod", {})
        result["effective_period_start"] = effective_period.get("start")
        result["effective_period_end"] = effective_period.get("end")
        
        result["issued"] = resource.get("issued")
        
        # Value (polymorphic)
        result["value"] = None  # Will be set based on type - VARIANT
        result["value_quantity"] = None
        result["value_string"] = None
        result["value_unit"] = None
        
        if "valueQuantity" in resource:
            qty = extract_quantity(resource["valueQuantity"])
            result["value"] = resource["valueQuantity"]
            result["value_quantity"] = qty["value"]
            result["value_unit"] = qty["unit"]
        elif "valueString" in resource:
            result["value"] = resource["valueString"]
            result["value_string"] = resource["valueString"]
        elif "valueCodeableConcept" in resource:
            result["value"] = resource["valueCodeableConcept"]
            cc = extract_coding(resource["valueCodeableConcept"])
            result["value_string"] = cc["display"] or cc["code"]
        elif "valueBoolean" in resource:
            result["value"] = resource["valueBoolean"]
            result["value_string"] = str(resource["valueBoolean"])
        
        # Interpretation
        interpretations = resource.get("interpretation", [])
        result["interpretation"] = interpretations  # VARIANT
        if interpretations:
            interp = extract_coding(interpretations[0])
            result["interpretation_code"] = interp["code"]
            result["interpretation_display"] = interp["display"]
        
        # Reference range
        ref_ranges = resource.get("referenceRange", [])
        result["reference_range"] = ref_ranges  # VARIANT
        if ref_ranges:
            rr = ref_ranges[0]
            result["reference_range_low"] = rr.get("low", {}).get("value")
            result["reference_range_high"] = rr.get("high", {}).get("value")
            result["reference_range_text"] = rr.get("text")
        
        # Components (for vital signs like BP)
        components = resource.get("component", [])
        result["components"] = components  # VARIANT
        
        # Performer
        performers = resource.get("performer", [])
        if performers:
            perf = extract_reference(performers[0])
            result["performer_ref"] = perf["reference"]
            result["performer_id"] = perf["id"]
    
    def _parse_encounter(self, resource: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Parse Encounter-specific fields."""
        
        result["status"] = resource.get("status")
        
        # Class
        enc_class = resource.get("class", {})
        result["class_code"] = enc_class.get("code")
        result["class_display"] = enc_class.get("display")
        result["class_system"] = enc_class.get("system")
        
        # Type
        types = resource.get("type", [])
        result["type"] = types  # VARIANT
        if types:
            t = extract_coding(types[0])
            result["type_code"] = t["code"]
            result["type_display"] = t["display"]
        
        # Priority
        priority = extract_coding(resource.get("priority"))
        result["priority_code"] = priority["code"]
        result["priority_display"] = priority["display"]
        
        # Subject (patient)
        subject = extract_reference(resource.get("subject"))
        result["subject_ref"] = subject["reference"]
        result["patient_id"] = subject["id"]
        
        # Period
        period = resource.get("period", {})
        result["period_start"] = period.get("start")
        result["period_end"] = period.get("end")
        
        # Calculate length in minutes
        if result["period_start"] and result["period_end"]:
            try:
                # Parse ISO datetime strings
                start_str = result["period_start"].replace("Z", "+00:00")
                end_str = result["period_end"].replace("Z", "+00:00")
                
                # Handle different datetime formats
                for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
                    try:
                        start_dt = datetime.strptime(start_str[:26] if len(start_str) > 26 else start_str, fmt.replace("%z", ""))
                        end_dt = datetime.strptime(end_str[:26] if len(end_str) > 26 else end_str, fmt.replace("%z", ""))
                        diff = (end_dt - start_dt).total_seconds() / 60
                        result["length_minutes"] = int(diff)
                        break
                    except ValueError:
                        continue
            except Exception:
                result["length_minutes"] = None
        
        # Reason
        reason_codes = resource.get("reasonCode", [])
        result["reason_code"] = reason_codes  # VARIANT
        if reason_codes:
            rc = extract_coding(reason_codes[0])
            result["reason_code_code"] = rc["code"]
            result["reason_code_display"] = rc["display"]
            result["reason_display"] = rc["display"]
        
        # Hospitalization
        hospitalization = resource.get("hospitalization", {})
        result["hospitalization"] = hospitalization  # VARIANT
        
        admit_source = extract_coding(hospitalization.get("admitSource"))
        result["admit_source_code"] = admit_source["code"]
        result["admit_source_display"] = admit_source["display"]
        
        discharge = extract_coding(hospitalization.get("dischargeDisposition"))
        result["discharge_disposition_code"] = discharge["code"]
        result["discharge_disposition_display"] = discharge["display"]
        
        # Locations
        locations = resource.get("location", [])
        result["locations"] = locations  # VARIANT
        if locations:
            loc = locations[0]
            loc_ref = extract_reference(loc.get("location"))
            result["location_ref"] = loc_ref["reference"]
            result["location_display"] = loc_ref["display"]
            result["location_id"] = loc_ref["id"]
        
        # Participants
        participants = resource.get("participant", [])
        result["participants"] = participants  # VARIANT
        for part in participants:
            part_types = part.get("type", [])
            for pt in part_types:
                pt_coding = extract_coding(pt)
                if pt_coding["code"] == "ATND":  # Attender
                    ind = extract_reference(part.get("individual"))
                    result["attending_practitioner_ref"] = ind["reference"]
                    result["attending_practitioner_id"] = ind["id"]
                    break
        
        # Service provider
        sp = extract_reference(resource.get("serviceProvider"))
        result["service_provider_ref"] = sp["reference"]
        result["service_provider_id"] = sp["id"]
    
    def _parse_medication_request(self, resource: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Parse MedicationRequest-specific fields."""
        
        result["status"] = resource.get("status")
        result["intent"] = resource.get("intent")
        
        # Medication (choice type)
        result["medication"] = None  # VARIANT
        result["medication_code"] = None
        result["medication_display"] = None
        result["medication_system"] = None
        
        if "medicationCodeableConcept" in resource:
            med = resource["medicationCodeableConcept"]
            result["medication"] = med
            med_info = extract_coding(med)
            result["medication_code"] = med_info["code"]
            result["medication_display"] = med_info["display"]
            result["medication_system"] = med_info["system"]
        elif "medicationReference" in resource:
            med_ref = extract_reference(resource["medicationReference"])
            result["medication"] = resource["medicationReference"]
            result["medication_ref"] = med_ref["reference"]
            result["medication_id"] = med_ref["id"]
        
        # Subject (patient)
        subject = extract_reference(resource.get("subject"))
        result["subject_ref"] = subject["reference"]
        result["patient_id"] = subject["id"]
        
        # Encounter
        encounter = extract_reference(resource.get("encounter"))
        result["encounter_ref"] = encounter["reference"]
        result["encounter_id"] = encounter["id"]
        
        # Requester
        requester = extract_reference(resource.get("requester"))
        result["requester_ref"] = requester["reference"]
        result["requester_id"] = requester["id"]
        
        # AuthoredOn
        result["authored_on"] = resource.get("authoredOn")
        
        # Dosage instructions
        dosage_instructions = resource.get("dosageInstruction", [])
        result["dosage_instructions"] = dosage_instructions  # VARIANT
        
        if dosage_instructions:
            dosage = dosage_instructions[0]
            result["dosage_text"] = dosage.get("text")
            
            # Route
            route = extract_coding(dosage.get("route"))
            result["dosage_route_code"] = route["code"]
            result["dosage_route_display"] = route["display"]
            
            # Dose and rate
            dose_rate = dosage.get("doseAndRate", [])
            if dose_rate:
                dr = dose_rate[0]
                dose_qty = dr.get("doseQuantity", {})
                result["dose_value"] = dose_qty.get("value")
                result["dose_unit"] = dose_qty.get("unit")
        
        # Reason
        reason_codes = resource.get("reasonCode", [])
        if reason_codes:
            rc = extract_coding(reason_codes[0])
            result["reason_code"] = rc["code"]
            result["reason_display"] = rc["display"]
    
    def _parse_diagnostic_report(self, resource: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Parse DiagnosticReport-specific fields."""
        
        result["status"] = resource.get("status")
        
        # Category
        categories = resource.get("category", [])
        result["categories"] = categories  # VARIANT
        if categories:
            cat = extract_coding(categories[0])
            result["category_code"] = cat["code"]
            result["category_display"] = cat["display"]
        
        # Code
        code = resource.get("code", {})
        result["code"] = code  # VARIANT
        code_info = extract_coding(code)
        result["code_code"] = code_info["code"]
        result["code_display"] = code_info["display"]
        result["code_system"] = code_info["system"]
        
        # Subject (patient)
        subject = extract_reference(resource.get("subject"))
        result["subject_ref"] = subject["reference"]
        result["patient_id"] = subject["id"]
        
        # Encounter
        encounter = extract_reference(resource.get("encounter"))
        result["encounter_ref"] = encounter["reference"]
        result["encounter_id"] = encounter["id"]
        
        # Effective date/time
        result["effective_datetime"] = resource.get("effectiveDateTime")
        effective_period = resource.get("effectivePeriod", {})
        result["effective_period_start"] = effective_period.get("start")
        result["effective_period_end"] = effective_period.get("end")
        
        result["issued"] = resource.get("issued")
        
        # Results
        results = resource.get("result", [])
        result["results"] = results  # VARIANT
        result["result_refs"] = [extract_reference(r)["reference"] for r in results]
        
        # Performer
        performers = resource.get("performer", [])
        if performers:
            perf = extract_reference(performers[0])
            result["performer_ref"] = perf["reference"]
            result["performer_id"] = perf["id"]
            result["performer_display"] = perf["display"]
        
        # Conclusion
        result["conclusion"] = resource.get("conclusion")
        
        # Presented form (attachments)
        result["presented_form"] = resource.get("presentedForm", [])  # VARIANT
    
    def _parse_immunization(self, resource: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Parse Immunization-specific fields."""
        
        result["status"] = resource.get("status")
        
        # Vaccine code
        vaccine_code = resource.get("vaccineCode", {})
        result["vaccine_code"] = vaccine_code  # VARIANT
        vax_info = extract_coding(vaccine_code)
        result["vaccine_code_code"] = vax_info["code"]
        result["vaccine_display"] = vax_info["display"]
        result["vaccine_system"] = vax_info["system"]
        
        # Extract CVX code specifically
        codings = vaccine_code.get("coding", [])
        for coding in codings:
            if coding.get("system") == "http://hl7.org/fhir/sid/cvx":
                result["vaccine_cvx_code"] = coding.get("code")
                break
        else:
            result["vaccine_cvx_code"] = vax_info["code"]
        
        # Patient
        patient = extract_reference(resource.get("patient"))
        result["patient_ref"] = patient["reference"]
        result["patient_id"] = patient["id"]
        
        # Encounter
        encounter = extract_reference(resource.get("encounter"))
        result["encounter_ref"] = encounter["reference"]
        result["encounter_id"] = encounter["id"]
        
        # Occurrence
        result["occurrence_datetime"] = resource.get("occurrenceDateTime")
        result["occurrence_string"] = resource.get("occurrenceString")
        
        # Primary source
        result["primary_source"] = resource.get("primarySource")
        
        # Location
        location = extract_reference(resource.get("location"))
        result["location_ref"] = location["reference"]
        result["location_id"] = location["id"]
        
        # Manufacturer
        manufacturer = resource.get("manufacturer", {})
        result["manufacturer"] = manufacturer.get("display")
        
        # Lot number and expiration
        result["lot_number"] = resource.get("lotNumber")
        result["expiration_date"] = resource.get("expirationDate")
        
        # Site
        site = extract_coding(resource.get("site"))
        result["site_code"] = site["code"]
        result["site_display"] = site["display"]
        
        # Route
        route = extract_coding(resource.get("route"))
        result["route_code"] = route["code"]
        result["route_display"] = route["display"]
        
        # Dose quantity
        dose_qty = extract_quantity(resource.get("doseQuantity"))
        result["dose_quantity"] = dose_qty["value"]
        result["dose_unit"] = dose_qty["unit"]
        
        # Performers
        performers = resource.get("performer", [])
        result["performers"] = performers  # VARIANT
        
        # Protocol applied
        protocol_applied = resource.get("protocolApplied", [])
        result["protocol_applied"] = protocol_applied  # VARIANT
        if protocol_applied:
            protocol = protocol_applied[0]
            result["dose_number"] = protocol.get("doseNumberPositiveInt")
            result["series"] = protocol.get("series")
    
    def _parse_condition(self, resource: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Parse Condition-specific fields."""
        
        # Clinical status
        clinical_status = resource.get("clinicalStatus", {})
        result["clinical_status_obj"] = clinical_status  # VARIANT
        cs = extract_coding(clinical_status)
        result["clinical_status"] = cs["code"]
        result["clinical_status_display"] = cs["display"]
        
        # Verification status
        verification_status = resource.get("verificationStatus", {})
        result["verification_status_obj"] = verification_status  # VARIANT
        vs = extract_coding(verification_status)
        result["verification_status"] = vs["code"]
        result["verification_status_display"] = vs["display"]
        
        # Category
        categories = resource.get("category", [])
        result["categories"] = categories  # VARIANT
        if categories:
            cat = extract_coding(categories[0])
            result["category_code"] = cat["code"]
            result["category_display"] = cat["display"]
        
        # Severity
        severity = extract_coding(resource.get("severity"))
        result["severity_code"] = severity["code"]
        result["severity_display"] = severity["display"]
        
        # Code
        code = resource.get("code", {})
        result["code"] = code  # VARIANT
        code_info = extract_coding(code)
        result["code_code"] = code_info["code"]
        result["code_display"] = code_info["display"]
        result["code_system"] = code_info["system"]
        result["code_text"] = code_info["text"]
        
        # Body site
        body_sites = resource.get("bodySite", [])
        result["body_site"] = body_sites  # VARIANT
        if body_sites:
            bs = extract_coding(body_sites[0])
            result["body_site_code"] = bs["code"]
            result["body_site_display"] = bs["display"]
        
        # Subject (patient)
        subject = extract_reference(resource.get("subject"))
        result["subject_ref"] = subject["reference"]
        result["patient_id"] = subject["id"]
        
        # Encounter
        encounter = extract_reference(resource.get("encounter"))
        result["encounter_ref"] = encounter["reference"]
        result["encounter_id"] = encounter["id"]
        
        # Onset
        result["onset_datetime"] = resource.get("onsetDateTime")
        result["onset_string"] = resource.get("onsetString")
        onset_period = resource.get("onsetPeriod", {})
        result["onset_period_start"] = onset_period.get("start")
        
        # Abatement
        result["abatement_datetime"] = resource.get("abatementDateTime")
        result["abatement_string"] = resource.get("abatementString")
        
        # Recorded date
        result["recorded_date"] = resource.get("recordedDate")
        
        # Recorder
        recorder = extract_reference(resource.get("recorder"))
        result["recorder_ref"] = recorder["reference"]
        result["recorder_id"] = recorder["id"]
        
        # Asserter
        asserter = extract_reference(resource.get("asserter"))
        result["asserter_ref"] = asserter["reference"]
        result["asserter_id"] = asserter["id"]
        
        # Evidence
        result["evidence"] = resource.get("evidence", [])  # VARIANT


# =============================================================================
# QuarantineHandler Class
# =============================================================================

class QuarantineHandler:
    """
    Handles quarantining of failed/invalid FHIR resources.
    
    Features:
    - Creates quarantine records with full context
    - Classifies error types
    - Preserves original data for debugging
    - Supports reprocessing tracking
    
    Usage:
        handler = QuarantineHandler()
        record = handler.process(invalid_resource, "Missing status")
    """
    
    def __init__(self):
        """Initialize quarantine handler."""
        self._counter = 0
    
    def process(self, 
                resource: Union[Dict[str, Any], str],
                error_message: str,
                error_type: str = "VALIDATION",
                source_file: Optional[str] = None,
                source_line: Optional[int] = None) -> QuarantineRecord:
        """
        Create a quarantine record for a failed resource.
        
        Args:
            resource: Original resource (dict or string)
            error_message: Human-readable error message
            error_type: Error category (PARSE, VALIDATION, SCHEMA, TRANSFORM)
            source_file: Source file path
            source_line: Line number in source file
            
        Returns:
            QuarantineRecord
        """
        self._counter += 1
        
        # Generate unique ID
        quarantine_id = f"Q-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._counter:06d}"
        
        # Serialize resource to JSON string
        if isinstance(resource, str):
            raw_data = resource
            resource_type = None
            resource_id = None
        else:
            try:
                raw_data = json.dumps(resource, ensure_ascii=False)
                resource_type = resource.get("resourceType") if resource else None
                resource_id = resource.get("id") if resource else None
            except Exception:
                raw_data = str(resource)
                resource_type = None
                resource_id = None
        
        return QuarantineRecord(
            quarantine_id=quarantine_id,
            raw_data=raw_data,
            error_message=error_message,
            error_type=error_type,
            resource_type=resource_type,
            resource_id=resource_id,
            source_file=source_file,
            source_line=source_line,
            timestamp=datetime.utcnow()
        )
    
    def classify_error(self, exception: Exception) -> str:
        """
        Classify an exception into an error type.
        
        Args:
            exception: The exception that occurred
            
        Returns:
            Error type string (PARSE, VALIDATION, SCHEMA, TRANSFORM)
        """
        exc_type = type(exception).__name__
        exc_message = str(exception).lower()
        
        if exc_type == "JSONDecodeError" or "json" in exc_message:
            return "PARSE"
        elif "required" in exc_message or "missing" in exc_message:
            return "VALIDATION"
        elif "resourcetype" in exc_message or "unknown" in exc_message:
            return "SCHEMA"
        else:
            return "TRANSFORM"


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "ValidationResult",
    "QuarantineRecord",
    "FhirValidator",
    "FhirParser",
    "QuarantineHandler",
    "extract_coding",
    "extract_reference",
    "extract_identifier",
    "extract_quantity",
    "extract_period",
    "extract_name",
    "extract_address",
    "extract_telecom",
    "SUPPORTED_RESOURCE_TYPES",
    "REQUIRED_FIELDS",
]
