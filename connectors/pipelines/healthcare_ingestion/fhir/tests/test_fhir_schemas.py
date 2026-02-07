"""
FHIR Table Schema Tests

These tests verify that our schema definitions correctly implement
the VARIANT type strategy for semi-structured FHIR data.

Design principles:
1. Use VARIANT for complex/nested structures (extensions, arrays)
2. Use typed columns for frequently queried fields
3. Support schema evolution
4. Enable efficient Liquid Clustering

Run: pytest -v test_fhir_schemas.py
"""

import pytest
import sys
from typing import Dict, Any, List
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import schema definitions
from transformations.fhir_schemas import (
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


# =============================================================================
# Bronze Schema Tests
# =============================================================================

class TestBronzeSchema:
    """Tests for Bronze layer schema."""
    
    def test_bronze_has_raw_resource_variant(self):
        """Bronze must have raw_resource as VARIANT."""
        assert "raw_resource" in BRONZE_FHIR_FIELDS
        assert BRONZE_FHIR_FIELDS["raw_resource"] == "VARIANT"
    
    def test_bronze_has_resource_type(self):
        """Bronze must have resource_type for filtering."""
        assert "resource_type" in BRONZE_FHIR_FIELDS
        assert BRONZE_FHIR_FIELDS["resource_type"] == "STRING"
    
    def test_bronze_has_resource_id(self):
        """Bronze must have resource_id for deduplication."""
        assert "resource_id" in BRONZE_FHIR_FIELDS
        assert BRONZE_FHIR_FIELDS["resource_id"] == "STRING"
    
    def test_bronze_has_ingestion_metadata(self):
        """Bronze must have ingestion metadata."""
        assert "ingestion_timestamp" in BRONZE_FHIR_FIELDS
        assert "source_file" in BRONZE_FHIR_FIELDS
    
    def test_bronze_has_validation_fields(self):
        """Bronze must have validation tracking fields."""
        assert "is_valid" in BRONZE_FHIR_FIELDS
        assert "validation_errors" in BRONZE_FHIR_FIELDS


# =============================================================================
# Quarantine Schema Tests
# =============================================================================

class TestQuarantineSchema:
    """Tests for Quarantine table schema."""
    
    def test_quarantine_has_raw_data(self):
        """Quarantine must preserve original raw data."""
        assert "raw_data" in QUARANTINE_FHIR_FIELDS
        # Raw data is STRING (JSON string) for maximum compatibility
        assert QUARANTINE_FHIR_FIELDS["raw_data"] == "STRING"
    
    def test_quarantine_has_error_info(self):
        """Quarantine must have error information."""
        assert "error_type" in QUARANTINE_FHIR_FIELDS
        assert "error_message" in QUARANTINE_FHIR_FIELDS
    
    def test_quarantine_has_reprocessing_fields(self):
        """Quarantine must have reprocessing tracking."""
        assert "reprocess_attempts" in QUARANTINE_FHIR_FIELDS
        assert "last_reprocess_timestamp" in QUARANTINE_FHIR_FIELDS
        assert "resolved" in QUARANTINE_FHIR_FIELDS
    
    def test_quarantine_has_source_tracking(self):
        """Quarantine must track source file and line."""
        assert "source_file" in QUARANTINE_FHIR_FIELDS
        assert "source_line_number" in QUARANTINE_FHIR_FIELDS


# =============================================================================
# Silver Patient Schema Tests
# =============================================================================

class TestSilverPatientSchema:
    """Tests for Silver Patient schema."""
    
    def test_patient_has_typed_demographics(self):
        """Patient must have typed demographic fields."""
        assert SILVER_PATIENT_FIELDS["gender"] == "STRING"
        assert SILVER_PATIENT_FIELDS["birth_date"] == "DATE"
        assert SILVER_PATIENT_FIELDS["deceased"] == "BOOLEAN"
    
    def test_patient_has_variant_for_names(self):
        """Patient names array should be VARIANT."""
        assert "names" in SILVER_PATIENT_FIELDS
        assert SILVER_PATIENT_FIELDS["names"] == "VARIANT"
    
    def test_patient_has_variant_for_identifiers(self):
        """Patient identifiers array should be VARIANT."""
        assert "identifiers" in SILVER_PATIENT_FIELDS
        assert SILVER_PATIENT_FIELDS["identifiers"] == "VARIANT"
    
    def test_patient_has_variant_for_extensions(self):
        """Patient extensions should be VARIANT."""
        assert "extensions" in SILVER_PATIENT_FIELDS
        assert SILVER_PATIENT_FIELDS["extensions"] == "VARIANT"
    
    def test_patient_has_flattened_name(self):
        """Patient should have flattened primary name."""
        assert "name_family" in SILVER_PATIENT_FIELDS
        assert "name_given" in SILVER_PATIENT_FIELDS
        assert SILVER_PATIENT_FIELDS["name_family"] == "STRING"
    
    def test_patient_has_flattened_address(self):
        """Patient should have flattened primary address."""
        assert "address_city" in SILVER_PATIENT_FIELDS
        assert "address_state" in SILVER_PATIENT_FIELDS
        assert "address_postal_code" in SILVER_PATIENT_FIELDS
    
    def test_patient_preserves_raw_resource(self):
        """Patient should preserve raw_resource as VARIANT."""
        assert "raw_resource" in SILVER_PATIENT_FIELDS
        assert SILVER_PATIENT_FIELDS["raw_resource"] == "VARIANT"


# =============================================================================
# Silver Observation Schema Tests
# =============================================================================

class TestSilverObservationSchema:
    """Tests for Silver Observation schema."""
    
    def test_observation_has_typed_status(self):
        """Observation must have typed status field."""
        assert SILVER_OBSERVATION_FIELDS["status"] == "STRING"
    
    def test_observation_has_typed_value(self):
        """Observation must have typed value fields."""
        assert "value_quantity" in SILVER_OBSERVATION_FIELDS
        assert SILVER_OBSERVATION_FIELDS["value_quantity"] == "DOUBLE"
        assert "value_string" in SILVER_OBSERVATION_FIELDS
        assert "value_unit" in SILVER_OBSERVATION_FIELDS
    
    def test_observation_has_variant_for_value(self):
        """Observation polymorphic value should be VARIANT."""
        assert "value" in SILVER_OBSERVATION_FIELDS
        assert SILVER_OBSERVATION_FIELDS["value"] == "VARIANT"
    
    def test_observation_has_variant_for_components(self):
        """Observation components should be VARIANT."""
        assert "components" in SILVER_OBSERVATION_FIELDS
        assert SILVER_OBSERVATION_FIELDS["components"] == "VARIANT"
    
    def test_observation_has_patient_reference(self):
        """Observation must have patient_id reference."""
        assert "patient_id" in SILVER_OBSERVATION_FIELDS
        assert SILVER_OBSERVATION_FIELDS["patient_id"] == "STRING"


# =============================================================================
# Silver Encounter Schema Tests
# =============================================================================

class TestSilverEncounterSchema:
    """Tests for Silver Encounter schema."""
    
    def test_encounter_has_typed_status(self):
        """Encounter must have typed status field."""
        assert SILVER_ENCOUNTER_FIELDS["status"] == "STRING"
    
    def test_encounter_has_typed_period(self):
        """Encounter must have typed period fields."""
        assert "period_start" in SILVER_ENCOUNTER_FIELDS
        assert "period_end" in SILVER_ENCOUNTER_FIELDS
        assert SILVER_ENCOUNTER_FIELDS["period_start"] == "TIMESTAMP"
    
    def test_encounter_has_variant_for_hospitalization(self):
        """Encounter hospitalization should be VARIANT."""
        assert "hospitalization" in SILVER_ENCOUNTER_FIELDS
        assert SILVER_ENCOUNTER_FIELDS["hospitalization"] == "VARIANT"
    
    def test_encounter_has_variant_for_locations(self):
        """Encounter locations should be VARIANT."""
        assert "locations" in SILVER_ENCOUNTER_FIELDS
        assert SILVER_ENCOUNTER_FIELDS["locations"] == "VARIANT"


# =============================================================================
# Other Silver Resource Schema Tests
# =============================================================================

class TestOtherSilverSchemas:
    """Tests for other Silver resource schemas."""
    
    def test_medication_request_has_dosage_variant(self):
        """MedicationRequest dosage_instructions should be VARIANT."""
        assert "dosage_instructions" in SILVER_MEDICATION_REQUEST_FIELDS
        assert SILVER_MEDICATION_REQUEST_FIELDS["dosage_instructions"] == "VARIANT"
    
    def test_immunization_has_vaccine_code_variant(self):
        """Immunization vaccine_code should be VARIANT."""
        assert "vaccine_code" in SILVER_IMMUNIZATION_FIELDS
        assert SILVER_IMMUNIZATION_FIELDS["vaccine_code"] == "VARIANT"
    
    def test_diagnostic_report_has_results_variant(self):
        """DiagnosticReport results should be VARIANT."""
        assert "results" in SILVER_DIAGNOSTIC_REPORT_FIELDS
        assert SILVER_DIAGNOSTIC_REPORT_FIELDS["results"] == "VARIANT"
    
    def test_condition_has_evidence_variant(self):
        """Condition evidence should be VARIANT."""
        assert "evidence" in SILVER_CONDITION_FIELDS
        assert SILVER_CONDITION_FIELDS["evidence"] == "VARIANT"
    
    def test_all_silver_have_raw_resource(self):
        """All Silver tables should preserve raw_resource."""
        schemas = [
            SILVER_PATIENT_FIELDS,
            SILVER_OBSERVATION_FIELDS,
            SILVER_ENCOUNTER_FIELDS,
            SILVER_MEDICATION_REQUEST_FIELDS,
            SILVER_IMMUNIZATION_FIELDS,
            SILVER_DIAGNOSTIC_REPORT_FIELDS,
            SILVER_CONDITION_FIELDS,
        ]
        for schema in schemas:
            assert "raw_resource" in schema
            assert schema["raw_resource"] == "VARIANT"


# =============================================================================
# Liquid Clustering Configuration Tests
# =============================================================================

class TestLiquidClusteringConfig:
    """Tests for Liquid Clustering configuration."""
    
    def test_bronze_clustering_config(self):
        """Bronze should cluster by resource_type and resource_id."""
        config = LIQUID_CLUSTERING_CONFIG.get("bronze_fhir", [])
        assert "resource_type" in config
        assert "resource_id" in config
    
    def test_quarantine_clustering_config(self):
        """Quarantine should cluster by error_type."""
        config = LIQUID_CLUSTERING_CONFIG.get("quarantine_fhir", [])
        assert "error_type" in config
    
    def test_patient_clustering_config(self):
        """Patient should cluster by id and gender."""
        config = LIQUID_CLUSTERING_CONFIG.get("silver_fhir_patient", [])
        assert "id" in config
    
    def test_observation_clustering_config(self):
        """Observation should cluster by patient_id and code."""
        config = LIQUID_CLUSTERING_CONFIG.get("silver_fhir_observation", [])
        assert "patient_id" in config


# =============================================================================
# VARIANT Fields Registry Tests
# =============================================================================

class TestVariantFieldsRegistry:
    """Tests for VARIANT fields registry."""
    
    def test_bronze_variant_fields(self):
        """Bronze VARIANT fields should be registered."""
        fields = VARIANT_FIELDS.get("bronze_fhir", [])
        assert "raw_resource" in fields
    
    def test_patient_variant_fields(self):
        """Patient VARIANT fields should be registered."""
        fields = VARIANT_FIELDS.get("silver_fhir_patient", [])
        assert "raw_resource" in fields
        assert "identifiers" in fields
        assert "names" in fields
        assert "extensions" in fields
    
    def test_observation_variant_fields(self):
        """Observation VARIANT fields should be registered."""
        fields = VARIANT_FIELDS.get("silver_fhir_observation", [])
        assert "value" in fields
        assert "components" in fields


# =============================================================================
# Schema Utility Function Tests
# =============================================================================

class TestSchemaUtilities:
    """Tests for schema utility functions."""
    
    def test_get_schema_fields(self):
        """get_schema_fields returns correct schema."""
        fields = get_schema_fields("silver_fhir_patient")
        assert "id" in fields
        assert "gender" in fields
        assert fields["raw_resource"] == "VARIANT"
    
    def test_get_schema_fields_unknown(self):
        """get_schema_fields returns empty for unknown table."""
        fields = get_schema_fields("unknown_table")
        assert fields == {}
    
    def test_get_cluster_by(self):
        """get_cluster_by returns clustering columns."""
        cols = get_cluster_by("silver_fhir_patient")
        assert isinstance(cols, list)
        assert len(cols) > 0
    
    def test_get_variant_fields(self):
        """get_variant_fields returns VARIANT column names."""
        fields = get_variant_fields("silver_fhir_patient")
        assert isinstance(fields, list)
        assert "raw_resource" in fields
    
    def test_is_variant_field_true(self):
        """is_variant_field returns True for VARIANT fields."""
        assert is_variant_field("silver_fhir_patient", "raw_resource") == True
        assert is_variant_field("silver_fhir_patient", "extensions") == True
    
    def test_is_variant_field_false(self):
        """is_variant_field returns False for non-VARIANT fields."""
        assert is_variant_field("silver_fhir_patient", "id") == False
        assert is_variant_field("silver_fhir_patient", "gender") == False


# =============================================================================
# Schema Evolution Tests
# =============================================================================

class TestSchemaEvolution:
    """Tests for schema evolution support."""
    
    def test_variant_allows_new_extensions(self):
        """VARIANT type allows adding new extensions without schema change."""
        # This is a design validation - VARIANT columns support any JSON structure
        assert SILVER_PATIENT_FIELDS["extensions"] == "VARIANT"
        # Extensions can evolve without DDL changes
    
    def test_variant_allows_complex_nested_data(self):
        """VARIANT type allows deeply nested structures."""
        # Components in Observation can have arbitrary nesting
        assert SILVER_OBSERVATION_FIELDS["components"] == "VARIANT"
    
    def test_raw_resource_preserves_all_data(self):
        """raw_resource VARIANT preserves all original FHIR data."""
        # Even as FHIR R4 adds new fields, raw_resource captures everything
        assert BRONZE_FHIR_FIELDS["raw_resource"] == "VARIANT"


# =============================================================================
# VARIANT Query Pattern Tests (Documentation Verification)
# =============================================================================

class TestVariantQueryPatterns:
    """Tests to verify VARIANT query pattern documentation."""
    
    def test_patient_schema_supports_variant_access(self):
        """Patient schema should support VARIANT path access patterns.
        
        Example queries that should work:
        - raw_resource:id
        - raw_resource:name[0]:family
        - extensions[0]:url
        """
        # Verify the fields that enable VARIANT access exist
        assert "raw_resource" in SILVER_PATIENT_FIELDS
        assert "extensions" in SILVER_PATIENT_FIELDS
    
    def test_observation_schema_supports_value_variant(self):
        """Observation schema should support polymorphic value access.
        
        Example queries that should work:
        - value:value (for Quantity)
        - value:unit (for Quantity)
        - value:code (for CodeableConcept)
        - value (as string for string values)
        """
        assert "value" in SILVER_OBSERVATION_FIELDS
        assert SILVER_OBSERVATION_FIELDS["value"] == "VARIANT"
    
    def test_encounter_schema_supports_hospitalization_access(self):
        """Encounter schema should support hospitalization VARIANT access.
        
        Example queries that should work:
        - hospitalization:admitSource:coding[0]:code
        - hospitalization:dischargeDisposition:text
        """
        assert "hospitalization" in SILVER_ENCOUNTER_FIELDS
        assert SILVER_ENCOUNTER_FIELDS["hospitalization"] == "VARIANT"
