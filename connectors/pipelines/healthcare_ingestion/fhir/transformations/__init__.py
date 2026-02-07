"""
FHIR Transformations Module

This module contains:
- FhirParser: Parse FHIR R4 resources
- FhirValidator: Validate against FHIR R4 schema
- QuarantineHandler: Handle invalid records
- Helper functions for FHIR data extraction
- Schema definitions with VARIANT type support

Implementation Status: COMPLETE
"""

from .fhir_parser import (
    ValidationResult,
    QuarantineRecord,
    FhirValidator,
    FhirParser,
    QuarantineHandler,
    extract_coding,
    extract_reference,
    extract_identifier,
    extract_quantity,
    extract_period,
    extract_name,
    extract_address,
    extract_telecom,
    SUPPORTED_RESOURCE_TYPES,
    REQUIRED_FIELDS,
)

from .fhir_schemas import (
    BRONZE_FHIR_FIELDS,
    QUARANTINE_FHIR_FIELDS,
    SILVER_PATIENT_FIELDS,
    SILVER_OBSERVATION_FIELDS,
    SILVER_ENCOUNTER_FIELDS,
    SILVER_MEDICATION_REQUEST_FIELDS,
    SILVER_IMMUNIZATION_FIELDS,
    SILVER_DIAGNOSTIC_REPORT_FIELDS,
    SILVER_CONDITION_FIELDS,
    LIQUID_CLUSTERING_CONFIG,
    VARIANT_FIELDS,
    get_schema_fields,
    get_cluster_by,
    get_variant_fields,
    is_variant_field,
)

__all__ = [
    # Parser classes
    "ValidationResult",
    "QuarantineRecord",
    "FhirValidator",
    "FhirParser",
    "QuarantineHandler",
    # Helper functions
    "extract_coding",
    "extract_reference",
    "extract_identifier",
    "extract_quantity",
    "extract_period",
    "extract_name",
    "extract_address",
    "extract_telecom",
    # Constants
    "SUPPORTED_RESOURCE_TYPES",
    "REQUIRED_FIELDS",
    # Schema definitions
    "BRONZE_FHIR_FIELDS",
    "QUARANTINE_FHIR_FIELDS",
    "SILVER_PATIENT_FIELDS",
    "SILVER_OBSERVATION_FIELDS",
    "SILVER_ENCOUNTER_FIELDS",
    "SILVER_MEDICATION_REQUEST_FIELDS",
    "SILVER_IMMUNIZATION_FIELDS",
    "SILVER_DIAGNOSTIC_REPORT_FIELDS",
    "SILVER_CONDITION_FIELDS",
    "LIQUID_CLUSTERING_CONFIG",
    "VARIANT_FIELDS",
    # Schema utilities
    "get_schema_fields",
    "get_cluster_by",
    "get_variant_fields",
    "is_variant_field",
]
