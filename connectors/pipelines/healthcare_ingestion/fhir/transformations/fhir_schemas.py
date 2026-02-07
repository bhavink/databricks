"""
FHIR Pipeline Schema Definitions

This module defines schema structures for FHIR tables in the medallion architecture.
Designed for use with Spark Declarative Pipelines (SDP/DLT).

Key Design Decisions:
1. VARIANT type for semi-structured data (extensions, nested structures)
2. Typed columns for frequently queried fields
3. Schema evolution friendly
4. Liquid Clustering configuration

Usage in SDP:
    from fhir_schemas import BRONZE_SCHEMA, SILVER_PATIENT_SCHEMA
    
    @dlt.table(
        schema=SILVER_PATIENT_SCHEMA,
        cluster_by=["id", "gender"]
    )
    def silver_fhir_patient():
        ...

Reference: https://learn.microsoft.com/en-us/azure/databricks/sql/language-manual/data-types/variant-type
"""

from typing import Dict, List, Any


# =============================================================================
# Schema Field Definitions (for documentation and validation)
# =============================================================================

# Bronze layer schema - raw FHIR resources with minimal transformation
BRONZE_FHIR_FIELDS = {
    # Core metadata
    "ingestion_timestamp": "TIMESTAMP",
    "source_file": "STRING",
    "source_line_number": "LONG",
    
    # Raw resource stored as VARIANT for schema evolution
    "raw_resource": "VARIANT",  # Full FHIR resource
    
    # Extracted core fields for efficient filtering
    "resource_type": "STRING",
    "resource_id": "STRING",
    "meta_version_id": "STRING",
    "meta_last_updated": "TIMESTAMP",
    
    # Data quality tracking
    "is_valid": "BOOLEAN",
    "validation_errors": "ARRAY<STRING>",
}

# Quarantine table schema
QUARANTINE_FHIR_FIELDS = {
    "quarantine_id": "STRING",
    "ingestion_timestamp": "TIMESTAMP",
    "source_file": "STRING",
    "source_line_number": "LONG",
    
    # Raw data preserved
    "raw_data": "STRING",  # Original JSON string
    
    # Error information
    "error_type": "STRING",  # PARSE, VALIDATION, SCHEMA, TRANSFORM
    "error_message": "STRING",
    
    # Resource metadata (if extractable)
    "resource_type": "STRING",
    "resource_id": "STRING",
    
    # Reprocessing tracking
    "reprocess_attempts": "INT",
    "last_reprocess_timestamp": "TIMESTAMP",
    "resolved": "BOOLEAN",
}

# Silver Patient schema - flattened with VARIANT for complex fields
SILVER_PATIENT_FIELDS = {
    # Identity
    "id": "STRING",
    "resource_type": "STRING",
    
    # Core demographics (typed for efficient queries)
    "gender": "STRING",
    "birth_date": "DATE",
    "deceased": "BOOLEAN",
    "deceased_datetime": "TIMESTAMP",
    "active": "BOOLEAN",
    
    # Name (flattened primary)
    "name_family": "STRING",
    "name_given": "STRING",
    "name_prefix": "STRING",
    "name_suffix": "STRING",
    
    # Identifiers (flattened common types)
    "identifier_mrn": "STRING",
    "identifier_ssn": "STRING",
    
    # Address (flattened primary)
    "address_line": "STRING",
    "address_city": "STRING",
    "address_state": "STRING",
    "address_postal_code": "STRING",
    "address_country": "STRING",
    
    # Contact (flattened)
    "phone_home": "STRING",
    "phone_work": "STRING",
    "phone_mobile": "STRING",
    "email": "STRING",
    
    # Organization references
    "managing_organization_id": "STRING",
    "general_practitioner_id": "STRING",
    
    # Marital status
    "marital_status_code": "STRING",
    "marital_status_display": "STRING",
    
    # Language
    "preferred_language": "STRING",
    
    # VARIANT fields for complex/nested structures
    "raw_resource": "VARIANT",  # Full original resource
    "meta": "VARIANT",  # FHIR meta element
    "identifiers": "VARIANT",  # All identifiers array
    "names": "VARIANT",  # All names array
    "addresses": "VARIANT",  # All addresses array
    "telecoms": "VARIANT",  # All telecom array
    "contacts": "VARIANT",  # Emergency contacts
    "extensions": "VARIANT",  # FHIR extensions
    
    # Processing metadata
    "meta_version_id": "STRING",
    "meta_last_updated": "TIMESTAMP",
    "meta_source": "STRING",
    "processing_timestamp": "TIMESTAMP",
}

# Silver Observation schema
SILVER_OBSERVATION_FIELDS = {
    # Identity
    "id": "STRING",
    "resource_type": "STRING",
    
    # Core observation fields (typed)
    "status": "STRING",
    "category_code": "STRING",
    "category_display": "STRING",
    "code_code": "STRING",
    "code_display": "STRING",
    "code_system": "STRING",
    "code_text": "STRING",
    
    # Subject and context
    "patient_id": "STRING",
    "encounter_id": "STRING",
    
    # Timing
    "effective_datetime": "TIMESTAMP",
    "effective_period_start": "TIMESTAMP",
    "effective_period_end": "TIMESTAMP",
    "issued": "TIMESTAMP",
    
    # Value (typed for common patterns)
    "value_quantity": "DOUBLE",
    "value_string": "STRING",
    "value_unit": "STRING",
    
    # Interpretation
    "interpretation_code": "STRING",
    "interpretation_display": "STRING",
    
    # Reference range
    "reference_range_low": "DOUBLE",
    "reference_range_high": "DOUBLE",
    "reference_range_text": "STRING",
    
    # Performer
    "performer_id": "STRING",
    
    # VARIANT fields
    "raw_resource": "VARIANT",
    "meta": "VARIANT",
    "code": "VARIANT",  # Full CodeableConcept
    "categories": "VARIANT",
    "value": "VARIANT",  # Polymorphic value
    "interpretation": "VARIANT",
    "reference_range": "VARIANT",
    "components": "VARIANT",  # For multi-component obs like BP
    "extensions": "VARIANT",
    
    # Processing metadata
    "meta_version_id": "STRING",
    "meta_last_updated": "TIMESTAMP",
    "processing_timestamp": "TIMESTAMP",
}

# Silver Encounter schema
SILVER_ENCOUNTER_FIELDS = {
    # Identity
    "id": "STRING",
    "resource_type": "STRING",
    
    # Core fields (typed)
    "status": "STRING",
    "class_code": "STRING",
    "class_display": "STRING",
    "type_code": "STRING",
    "type_display": "STRING",
    "priority_code": "STRING",
    
    # Subject
    "patient_id": "STRING",
    
    # Timing
    "period_start": "TIMESTAMP",
    "period_end": "TIMESTAMP",
    "length_minutes": "INT",
    
    # Reason
    "reason_code_code": "STRING",
    "reason_display": "STRING",
    
    # Hospitalization
    "admit_source_code": "STRING",
    "admit_source_display": "STRING",
    "discharge_disposition_code": "STRING",
    "discharge_disposition_display": "STRING",
    
    # Location
    "location_id": "STRING",
    "location_display": "STRING",
    
    # Participants
    "attending_practitioner_id": "STRING",
    "service_provider_id": "STRING",
    
    # VARIANT fields
    "raw_resource": "VARIANT",
    "meta": "VARIANT",
    "type": "VARIANT",
    "reason_code": "VARIANT",
    "hospitalization": "VARIANT",
    "locations": "VARIANT",
    "participants": "VARIANT",
    "extensions": "VARIANT",
    
    # Processing metadata
    "meta_version_id": "STRING",
    "meta_last_updated": "TIMESTAMP",
    "processing_timestamp": "TIMESTAMP",
}

# Silver MedicationRequest schema
SILVER_MEDICATION_REQUEST_FIELDS = {
    # Identity
    "id": "STRING",
    "resource_type": "STRING",
    
    # Core fields (typed)
    "status": "STRING",
    "intent": "STRING",
    
    # Medication
    "medication_code": "STRING",
    "medication_display": "STRING",
    "medication_system": "STRING",
    "medication_id": "STRING",  # If medicationReference
    
    # Subject and context
    "patient_id": "STRING",
    "encounter_id": "STRING",
    "requester_id": "STRING",
    
    # Timing
    "authored_on": "TIMESTAMP",
    
    # Dosage (flattened primary)
    "dosage_text": "STRING",
    "dosage_route_code": "STRING",
    "dosage_route_display": "STRING",
    "dose_value": "DOUBLE",
    "dose_unit": "STRING",
    
    # Reason
    "reason_code": "STRING",
    "reason_display": "STRING",
    
    # VARIANT fields
    "raw_resource": "VARIANT",
    "meta": "VARIANT",
    "medication": "VARIANT",  # Full medication[x]
    "dosage_instructions": "VARIANT",
    "extensions": "VARIANT",
    
    # Processing metadata
    "meta_version_id": "STRING",
    "meta_last_updated": "TIMESTAMP",
    "processing_timestamp": "TIMESTAMP",
}

# Silver Immunization schema
SILVER_IMMUNIZATION_FIELDS = {
    # Identity
    "id": "STRING",
    "resource_type": "STRING",
    
    # Core fields (typed)
    "status": "STRING",
    
    # Vaccine
    "vaccine_code_code": "STRING",
    "vaccine_display": "STRING",
    "vaccine_system": "STRING",
    "vaccine_cvx_code": "STRING",
    
    # Subject and context
    "patient_id": "STRING",
    "encounter_id": "STRING",
    "location_id": "STRING",
    
    # Timing
    "occurrence_datetime": "TIMESTAMP",
    "occurrence_string": "STRING",
    
    # Administration
    "manufacturer": "STRING",
    "lot_number": "STRING",
    "expiration_date": "DATE",
    "site_code": "STRING",
    "site_display": "STRING",
    "route_code": "STRING",
    "route_display": "STRING",
    "dose_quantity": "DOUBLE",
    "dose_unit": "STRING",
    
    # Protocol
    "dose_number": "INT",
    "series": "STRING",
    
    # VARIANT fields
    "raw_resource": "VARIANT",
    "meta": "VARIANT",
    "vaccine_code": "VARIANT",
    "performers": "VARIANT",
    "protocol_applied": "VARIANT",
    "extensions": "VARIANT",
    
    # Processing metadata
    "meta_version_id": "STRING",
    "meta_last_updated": "TIMESTAMP",
    "processing_timestamp": "TIMESTAMP",
}

# Silver DiagnosticReport schema
SILVER_DIAGNOSTIC_REPORT_FIELDS = {
    # Identity
    "id": "STRING",
    "resource_type": "STRING",
    
    # Core fields (typed)
    "status": "STRING",
    "category_code": "STRING",
    "category_display": "STRING",
    "code_code": "STRING",
    "code_display": "STRING",
    "code_system": "STRING",
    
    # Subject and context
    "patient_id": "STRING",
    "encounter_id": "STRING",
    
    # Timing
    "effective_datetime": "TIMESTAMP",
    "effective_period_start": "TIMESTAMP",
    "effective_period_end": "TIMESTAMP",
    "issued": "TIMESTAMP",
    
    # Performer
    "performer_id": "STRING",
    "performer_display": "STRING",
    
    # Results and conclusion
    "conclusion": "STRING",
    
    # VARIANT fields
    "raw_resource": "VARIANT",
    "meta": "VARIANT",
    "code": "VARIANT",
    "categories": "VARIANT",
    "results": "VARIANT",
    "presented_form": "VARIANT",
    "extensions": "VARIANT",
    
    # Processing metadata
    "meta_version_id": "STRING",
    "meta_last_updated": "TIMESTAMP",
    "processing_timestamp": "TIMESTAMP",
}

# Silver Condition schema
SILVER_CONDITION_FIELDS = {
    # Identity
    "id": "STRING",
    "resource_type": "STRING",
    
    # Status (typed)
    "clinical_status": "STRING",
    "clinical_status_display": "STRING",
    "verification_status": "STRING",
    "verification_status_display": "STRING",
    
    # Category and severity
    "category_code": "STRING",
    "category_display": "STRING",
    "severity_code": "STRING",
    "severity_display": "STRING",
    
    # Code
    "code_code": "STRING",
    "code_display": "STRING",
    "code_system": "STRING",
    "code_text": "STRING",
    
    # Body site
    "body_site_code": "STRING",
    "body_site_display": "STRING",
    
    # Subject and context
    "patient_id": "STRING",
    "encounter_id": "STRING",
    
    # Timing
    "onset_datetime": "TIMESTAMP",
    "onset_string": "STRING",
    "abatement_datetime": "TIMESTAMP",
    "abatement_string": "STRING",
    "recorded_date": "DATE",
    
    # Attribution
    "recorder_id": "STRING",
    "asserter_id": "STRING",
    
    # VARIANT fields
    "raw_resource": "VARIANT",
    "meta": "VARIANT",
    "code": "VARIANT",
    "categories": "VARIANT",
    "clinical_status_obj": "VARIANT",
    "verification_status_obj": "VARIANT",
    "body_site": "VARIANT",
    "evidence": "VARIANT",
    "extensions": "VARIANT",
    
    # Processing metadata
    "meta_version_id": "STRING",
    "meta_last_updated": "TIMESTAMP",
    "processing_timestamp": "TIMESTAMP",
}


# =============================================================================
# Liquid Clustering Configuration
# =============================================================================

LIQUID_CLUSTERING_CONFIG = {
    "bronze_fhir": ["resource_type", "resource_id"],
    "quarantine_fhir": ["error_type", "resource_type"],
    "silver_fhir_patient": ["id", "gender"],
    "silver_fhir_observation": ["patient_id", "code_code"],
    "silver_fhir_encounter": ["patient_id", "status"],
    "silver_fhir_medication_request": ["patient_id", "status"],
    "silver_fhir_immunization": ["patient_id", "vaccine_cvx_code"],
    "silver_fhir_diagnostic_report": ["patient_id", "code_code"],
    "silver_fhir_condition": ["patient_id", "clinical_status"],
}


# =============================================================================
# VARIANT-specific Fields (for query optimization documentation)
# =============================================================================

VARIANT_FIELDS = {
    "bronze_fhir": ["raw_resource"],
    "silver_fhir_patient": [
        "raw_resource", "meta", "identifiers", "names", 
        "addresses", "telecoms", "contacts", "extensions"
    ],
    "silver_fhir_observation": [
        "raw_resource", "meta", "code", "categories", 
        "value", "interpretation", "reference_range", "components", "extensions"
    ],
    "silver_fhir_encounter": [
        "raw_resource", "meta", "type", "reason_code",
        "hospitalization", "locations", "participants", "extensions"
    ],
    "silver_fhir_medication_request": [
        "raw_resource", "meta", "medication", "dosage_instructions", "extensions"
    ],
    "silver_fhir_immunization": [
        "raw_resource", "meta", "vaccine_code", "performers", 
        "protocol_applied", "extensions"
    ],
    "silver_fhir_diagnostic_report": [
        "raw_resource", "meta", "code", "categories", 
        "results", "presented_form", "extensions"
    ],
    "silver_fhir_condition": [
        "raw_resource", "meta", "code", "categories",
        "clinical_status_obj", "verification_status_obj", 
        "body_site", "evidence", "extensions"
    ],
}


# =============================================================================
# Schema Utilities
# =============================================================================

def get_schema_fields(table_name: str) -> Dict[str, str]:
    """
    Get schema fields for a table.
    
    Args:
        table_name: Table name (e.g., "silver_fhir_patient")
        
    Returns:
        Dictionary of field name to data type
    """
    schemas = {
        "bronze_fhir": BRONZE_FHIR_FIELDS,
        "quarantine_fhir": QUARANTINE_FHIR_FIELDS,
        "silver_fhir_patient": SILVER_PATIENT_FIELDS,
        "silver_fhir_observation": SILVER_OBSERVATION_FIELDS,
        "silver_fhir_encounter": SILVER_ENCOUNTER_FIELDS,
        "silver_fhir_medication_request": SILVER_MEDICATION_REQUEST_FIELDS,
        "silver_fhir_immunization": SILVER_IMMUNIZATION_FIELDS,
        "silver_fhir_diagnostic_report": SILVER_DIAGNOSTIC_REPORT_FIELDS,
        "silver_fhir_condition": SILVER_CONDITION_FIELDS,
    }
    return schemas.get(table_name, {})


def get_cluster_by(table_name: str) -> List[str]:
    """
    Get Liquid Clustering columns for a table.
    
    Args:
        table_name: Table name
        
    Returns:
        List of column names for clustering
    """
    return LIQUID_CLUSTERING_CONFIG.get(table_name, [])


def get_variant_fields(table_name: str) -> List[str]:
    """
    Get VARIANT column names for a table.
    
    Args:
        table_name: Table name
        
    Returns:
        List of VARIANT column names
    """
    return VARIANT_FIELDS.get(table_name, [])


def is_variant_field(table_name: str, field_name: str) -> bool:
    """
    Check if a field is a VARIANT type.
    
    Args:
        table_name: Table name
        field_name: Field name
        
    Returns:
        True if field is VARIANT type
    """
    return field_name in VARIANT_FIELDS.get(table_name, [])


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
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
    "get_schema_fields",
    "get_cluster_by",
    "get_variant_fields",
    "is_variant_field",
]
