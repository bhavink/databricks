"""
FHIR Resource Parser Tests

These tests verify that our FHIR parser correctly extracts and flattens
data from FHIR R4 resources.

The parser should:
1. Parse individual FHIR resources (JSON)
2. Extract key fields into a flattened structure
3. Handle all supported resource types
4. Preserve data integrity during transformation
5. Handle edge cases gracefully

Run: pytest -v test_fhir_parser.py
"""

import pytest
import json
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the implemented module
from transformations.fhir_parser import (
    FhirParser,
    FhirValidator,
    QuarantineHandler,
    extract_coding,
    extract_reference,
    extract_identifier,
    extract_quantity,
    extract_name,
    extract_address,
    extract_telecom,
)


# =============================================================================
# FhirParser Contract Tests
# =============================================================================

class TestFhirParserContract:
    """Tests that define the FhirParser interface contract."""
    
    def test_parser_exists(self):
        """FhirParser class must exist."""
        assert FhirParser is not None
    
    def test_parser_has_parse_method(self):
        """FhirParser must have a parse() method."""
        parser = FhirParser()
        assert hasattr(parser, 'parse')
        assert callable(parser.parse)
    
    def test_parse_returns_dict(self, valid_patient_minimal):
        """parse() must return a dictionary."""
        parser = FhirParser()
        result = parser.parse(valid_patient_minimal)
        assert isinstance(result, dict)
    
    def test_parse_preserves_resource_type(self, valid_patient_minimal):
        """Parsed result must include resource_type."""
        parser = FhirParser()
        result = parser.parse(valid_patient_minimal)
        assert result.get("resource_type") == "Patient"
    
    def test_parse_preserves_id(self, valid_patient_minimal):
        """Parsed result must include resource id."""
        parser = FhirParser()
        result = parser.parse(valid_patient_minimal)
        assert result.get("id") == valid_patient_minimal["id"]


# =============================================================================
# Patient Parsing Tests
# =============================================================================

class TestPatientParsing:
    """Tests for parsing Patient resources."""
    
    def test_parse_patient_minimal(self, valid_patient_minimal):
        """Parse minimal Patient (just resourceType and id)."""
        parser = FhirParser()
        result = parser.parse(valid_patient_minimal)
        assert result["resource_type"] == "Patient"
        assert result["id"] == valid_patient_minimal["id"]
    
    def test_parse_patient_full_demographics(self, valid_patient_full):
        """Parse Patient with full demographic information."""
        parser = FhirParser()
        result = parser.parse(valid_patient_full)
        
        # Core demographics
        assert result["gender"] == "male"
        assert result["birth_date"] == "1985-03-15"
        assert result["deceased"] == False
        
        # Name (flattened from first official name)
        assert result["name_family"] == "Doe"
        assert result["name_given"] == "John"  # First given name
    
    def test_parse_patient_identifiers(self, valid_patient_full):
        """Parse Patient identifiers (MRN, SSN, etc.)."""
        parser = FhirParser()
        result = parser.parse(valid_patient_full)
        
        # Should extract primary identifier (MRN)
        assert result.get("identifier_mrn") == "MRN123456"
        # Identifiers preserved as VARIANT
        assert "identifiers" in result
    
    def test_parse_patient_address(self, valid_patient_full):
        """Parse Patient address fields."""
        parser = FhirParser()
        result = parser.parse(valid_patient_full)
        
        # Address (flattened from first home address)
        assert result.get("address_city") == "Springfield"
        assert result.get("address_state") == "IL"
        assert result.get("address_postal_code") == "62701"
        assert result.get("address_country") == "USA"
    
    def test_parse_patient_telecom(self, valid_patient_full):
        """Parse Patient telecom (phone, email)."""
        parser = FhirParser()
        result = parser.parse(valid_patient_full)
        
        # Should extract phone and email
        assert result.get("phone_home") == "555-123-4567"
        assert result.get("email") == "john.doe@email.com"
    
    def test_parse_patient_deceased_datetime(self, valid_patient_deceased):
        """Parse Patient with deceasedDateTime."""
        parser = FhirParser()
        result = parser.parse(valid_patient_deceased)
        
        assert result["deceased"] == True
        assert result.get("deceased_datetime") == "2023-12-01T14:30:00Z"
    
    def test_parse_patient_preserves_raw_names(self, valid_patient_full):
        """Parse Patient preserves full names array as VARIANT."""
        parser = FhirParser()
        result = parser.parse(valid_patient_full)
        
        # Should preserve full names array for VARIANT column
        assert "names" in result
        assert isinstance(result["names"], list)


# =============================================================================
# Observation Parsing Tests
# =============================================================================

class TestObservationParsing:
    """Tests for parsing Observation resources."""
    
    def test_parse_observation_vital_sign(self, valid_observation_vital_sign):
        """Parse vital sign Observation."""
        parser = FhirParser()
        result = parser.parse(valid_observation_vital_sign)
        
        assert result["resource_type"] == "Observation"
        assert result["status"] == "final"
        assert result.get("category_code") == "vital-signs"
    
    def test_parse_observation_lab_result(self, valid_observation_lab_result):
        """Parse lab result Observation with value."""
        parser = FhirParser()
        result = parser.parse(valid_observation_lab_result)
        
        # Status and code
        assert result["status"] == "final"
        assert result.get("code_code") is not None
        
        # Value quantity
        assert result.get("value_quantity") is not None
        assert result.get("value_unit") is not None
    
    def test_parse_observation_abnormal(self, valid_observation_abnormal):
        """Parse Observation with abnormal flag/interpretation."""
        parser = FhirParser()
        result = parser.parse(valid_observation_abnormal)
        
        # Should have interpretation
        assert "interpretation" in result
    
    def test_parse_observation_preserves_components(self, valid_observation_vital_sign):
        """Parse Observation preserves components as VARIANT."""
        parser = FhirParser()
        result = parser.parse(valid_observation_vital_sign)
        
        # Components field should exist (even if empty)
        assert "components" in result


# =============================================================================
# Encounter Parsing Tests
# =============================================================================

class TestEncounterParsing:
    """Tests for parsing Encounter resources."""
    
    def test_parse_encounter_outpatient(self, valid_encounter_outpatient):
        """Parse outpatient Encounter."""
        parser = FhirParser()
        result = parser.parse(valid_encounter_outpatient)
        
        assert result["resource_type"] == "Encounter"
        assert result.get("status") is not None
        assert result.get("class_code") == "AMB"
    
    def test_parse_encounter_inpatient(self, valid_encounter_inpatient):
        """Parse inpatient Encounter with hospitalization."""
        parser = FhirParser()
        result = parser.parse(valid_encounter_inpatient)
        
        # Core fields
        assert result["status"] == "finished"
        assert result["class_code"] == "IMP"
        
        # Period
        assert result.get("period_start") is not None
        assert result.get("period_end") is not None
        
        # Hospitalization as VARIANT
        assert "hospitalization" in result
    
    def test_parse_encounter_locations(self, valid_encounter_inpatient):
        """Parse Encounter locations."""
        parser = FhirParser()
        result = parser.parse(valid_encounter_inpatient)
        
        # Locations as VARIANT
        assert "locations" in result


# =============================================================================
# MedicationRequest Parsing Tests
# =============================================================================

class TestMedicationRequestParsing:
    """Tests for parsing MedicationRequest resources."""
    
    def test_parse_medication_request(self, valid_medication_request):
        """Parse MedicationRequest."""
        parser = FhirParser()
        result = parser.parse(valid_medication_request)
        
        assert result["resource_type"] == "MedicationRequest"
        assert result["status"] == "active"
        assert result["intent"] == "order"
        
        # Medication
        assert result.get("medication_code") is not None or result.get("medication_ref") is not None
        
        # Subject reference
        assert result.get("patient_id") is not None
    
    def test_parse_medication_request_dosage(self, valid_medication_request):
        """Parse MedicationRequest dosage instructions."""
        parser = FhirParser()
        result = parser.parse(valid_medication_request)
        
        # Dosage as VARIANT
        assert "dosage_instructions" in result


# =============================================================================
# Immunization Parsing Tests
# =============================================================================

class TestImmunizationParsing:
    """Tests for parsing Immunization resources."""
    
    def test_parse_immunization(self, valid_immunization):
        """Parse Immunization."""
        parser = FhirParser()
        result = parser.parse(valid_immunization)
        
        assert result["resource_type"] == "Immunization"
        assert result["status"] == "completed"
        
        # Vaccine code
        assert result.get("vaccine_code_code") is not None
        
        # Occurrence
        assert result.get("occurrence_datetime") is not None
        
        # Patient
        assert result.get("patient_id") is not None


# =============================================================================
# DiagnosticReport Parsing Tests
# =============================================================================

class TestDiagnosticReportParsing:
    """Tests for parsing DiagnosticReport resources."""
    
    def test_parse_diagnostic_report(self, valid_diagnostic_report):
        """Parse DiagnosticReport."""
        parser = FhirParser()
        result = parser.parse(valid_diagnostic_report)
        
        assert result["resource_type"] == "DiagnosticReport"
        assert result["status"] == "final"
        
        # Code
        assert result.get("code_code") is not None
        
        # Results
        assert "results" in result


# =============================================================================
# Condition Parsing Tests
# =============================================================================

class TestConditionParsing:
    """Tests for parsing Condition resources."""
    
    def test_parse_condition(self, valid_condition):
        """Parse Condition."""
        parser = FhirParser()
        result = parser.parse(valid_condition)
        
        assert result["resource_type"] == "Condition"
        
        # Clinical status
        assert result.get("clinical_status") is not None
        
        # Code
        assert result.get("code_code") is not None
        
        # Subject
        assert result.get("patient_id") is not None


# =============================================================================
# Bundle Parsing Tests
# =============================================================================

class TestBundleParsing:
    """Tests for parsing Bundle resources."""
    
    def test_parse_bundle_collection(self, valid_bundle_collection):
        """parse_bundle() returns a list of parsed resources."""
        parser = FhirParser()
        results = parser.parse_bundle(valid_bundle_collection)
        
        assert isinstance(results, list)
        assert len(results) > 0
    
    def test_parse_bundle_extracts_entries(self, valid_bundle_collection):
        """parse_bundle() extracts individual resources from entries."""
        parser = FhirParser()
        results = parser.parse_bundle(valid_bundle_collection)
        
        # Each result should be a parsed resource
        for result in results:
            assert "resource_type" in result
    
    def test_parse_bundle_adds_metadata(self, valid_bundle_collection):
        """parse_bundle() adds bundle metadata to each resource."""
        parser = FhirParser()
        results = parser.parse_bundle(valid_bundle_collection)
        
        # Each result should have bundle metadata
        for result in results:
            assert "_bundle_entry_index" in result
    
    def test_parse_bundle_transaction(self, valid_bundle_transaction):
        """Parse transaction Bundle."""
        parser = FhirParser()
        results = parser.parse_bundle(valid_bundle_transaction)
        
        assert isinstance(results, list)
        # Transaction bundles have entries with resources
        for result in results:
            assert "_bundle_type" in result
            assert result["_bundle_type"] == "transaction"


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Tests for helper extraction functions."""
    
    def test_extract_coding_from_codeable_concept(self):
        """extract_coding extracts code from CodeableConcept."""
        codeable_concept = {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "29463-7",
                    "display": "Body Weight"
                }
            ],
            "text": "Body Weight"
        }
        
        result = extract_coding(codeable_concept)
        
        assert result["code"] == "29463-7"
        assert result["display"] == "Body Weight"
        assert result["system"] == "http://loinc.org"
        assert result["text"] == "Body Weight"
    
    def test_extract_coding_empty(self):
        """extract_coding handles None/empty input."""
        result = extract_coding(None)
        assert result["code"] is None
        assert result["display"] is None
    
    def test_extract_reference_parses_type_and_id(self):
        """extract_reference parses type and id from reference string."""
        reference = {
            "reference": "Patient/patient-001",
            "display": "John Doe"
        }
        
        result = extract_reference(reference)
        
        assert result["reference"] == "Patient/patient-001"
        assert result["type"] == "Patient"
        assert result["id"] == "patient-001"
        assert result["display"] == "John Doe"
    
    def test_extract_reference_empty(self):
        """extract_reference handles None/empty input."""
        result = extract_reference(None)
        assert result["reference"] is None
        assert result["type"] is None
        assert result["id"] is None
    
    def test_extract_identifier_first_value(self):
        """extract_identifier returns first identifier value."""
        identifiers = [
            {"system": "http://hospital.org/mrn", "value": "12345"},
            {"system": "http://ssa.gov/ssn", "value": "999-99-9999"}
        ]
        
        result = extract_identifier(identifiers)
        assert result == "12345"
    
    def test_extract_identifier_by_type(self):
        """extract_identifier can filter by type code."""
        identifiers = [
            {
                "type": {
                    "coding": [{"code": "MR"}]
                },
                "value": "MRN123456"
            },
            {
                "type": {
                    "coding": [{"code": "SS"}]
                },
                "value": "999-99-9999"
            }
        ]
        
        result = extract_identifier(identifiers, "MR")
        assert result == "MRN123456"
    
    def test_extract_name_official(self):
        """extract_name extracts official name by default."""
        names = [
            {
                "use": "official",
                "family": "Doe",
                "given": ["John", "William"]
            }
        ]
        
        result = extract_name(names)
        assert result["family"] == "Doe"
        assert result["given"] == "John"
    
    def test_extract_address_home(self):
        """extract_address extracts home address by default."""
        addresses = [
            {
                "use": "home",
                "line": ["123 Main St"],
                "city": "Springfield",
                "state": "IL",
                "postalCode": "62701"
            }
        ]
        
        result = extract_address(addresses)
        assert result["city"] == "Springfield"
        assert result["state"] == "IL"
        assert result["postal_code"] == "62701"
    
    def test_extract_telecom_phone_and_email(self):
        """extract_telecom extracts phone and email."""
        telecoms = [
            {"system": "phone", "use": "home", "value": "555-1234"},
            {"system": "email", "value": "test@example.com"}
        ]
        
        result = extract_telecom(telecoms)
        assert result["phone_home"] == "555-1234"
        assert result["email"] == "test@example.com"


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestParserEdgeCases:
    """Tests for parser edge cases and error handling."""
    
    def test_parse_empty_resource(self):
        """Parser handles empty/None resource gracefully."""
        parser = FhirParser()
        
        result = parser.parse(None)
        assert result.get("_quarantine") == True
        
        result = parser.parse({})
        assert result.get("_quarantine") == True
    
    def test_parse_missing_resource_type(self):
        """Parser handles missing resourceType."""
        parser = FhirParser()
        resource = {"id": "test-001", "someField": "value"}
        
        result = parser.parse(resource)
        assert result.get("_quarantine") == True
        assert "_parse_error" in result
    
    def test_parse_unknown_resource_type(self):
        """Parser handles unknown resourceType with warning."""
        parser = FhirParser()
        resource = {"resourceType": "UnknownResource", "id": "test-001"}
        
        result = parser.parse(resource)
        assert result.get("_parse_warning") is not None
    
    def test_parse_preserves_raw_resource(self):
        """Parser preserves raw resource for VARIANT column."""
        parser = FhirParser()
        resource = {"resourceType": "Patient", "id": "test-001", "custom": "data"}
        
        result = parser.parse(resource)
        assert result.get("raw_resource") == resource
    
    def test_parse_json_string(self):
        """Parser handles JSON string input."""
        parser = FhirParser()
        json_str = '{"resourceType": "Patient", "id": "test-001"}'
        
        result = parser.parse_json_string(json_str)
        assert result["resource_type"] == "Patient"
        assert result["id"] == "test-001"
    
    def test_parse_invalid_json_string(self):
        """Parser handles invalid JSON gracefully."""
        parser = FhirParser()
        invalid_json = '{"resourceType": "Patient", invalid}'
        
        result = parser.parse_json_string(invalid_json)
        assert result.get("_quarantine") == True
        assert "JSON" in result.get("_parse_error", "")
    
    def test_parse_unicode_content(self, edge_case_unicode_in_names):
        """Parser handles unicode content correctly."""
        parser = FhirParser()
        result = parser.parse(edge_case_unicode_in_names)
        
        assert result.get("_quarantine") == False
        assert result.get("name_family") is not None  # Should have a name
    
    def test_parse_deeply_nested_extensions(self, edge_case_deeply_nested):
        """Parser handles deeply nested extensions."""
        parser = FhirParser()
        result = parser.parse(edge_case_deeply_nested)
        
        # Extensions preserved as VARIANT
        assert "extensions" in result
        assert result.get("_quarantine") == False
    
    def test_parse_very_long_text(self, edge_case_very_long_text):
        """Parser handles very long text fields."""
        parser = FhirParser()
        result = parser.parse(edge_case_very_long_text)
        
        assert result.get("_quarantine") == False
        # The fixture is an Observation with long text
        assert result.get("resource_type") in ["Patient", "Observation"]
    
    def test_parse_many_identifiers(self, edge_case_many_identifiers):
        """Parser handles many identifiers."""
        parser = FhirParser()
        result = parser.parse(edge_case_many_identifiers)
        
        assert result.get("_quarantine") == False
        assert "identifiers" in result
        # Should preserve all identifiers as VARIANT
        assert isinstance(result["identifiers"], list)


# =============================================================================
# Performance and Consistency Tests
# =============================================================================

class TestParserConsistency:
    """Tests for consistent parsing behavior."""
    
    def test_parse_same_resource_twice_same_result(self, valid_patient_full):
        """Parsing same resource twice gives same result."""
        parser = FhirParser()
        
        result1 = parser.parse(valid_patient_full)
        result2 = parser.parse(valid_patient_full)
        
        # Core fields should be identical
        assert result1["id"] == result2["id"]
        assert result1["resource_type"] == result2["resource_type"]
        assert result1["gender"] == result2["gender"]
    
    def test_parser_does_not_modify_input(self, valid_patient_full):
        """Parsing does not modify the input resource."""
        import copy
        parser = FhirParser()
        
        original = copy.deepcopy(valid_patient_full)
        parser.parse(valid_patient_full)
        
        assert valid_patient_full == original


# =============================================================================
# Bulk Data Tests
# =============================================================================

class TestBulkParsing:
    """Tests for bulk data parsing."""
    
    def test_parse_bulk_patients(self, bulk_patients_100):
        """Parse 100 patients from bulk fixture."""
        parser = FhirParser()
        
        results = []
        for patient in bulk_patients_100:
            result = parser.parse(patient)
            results.append(result)
        
        # All should parse successfully
        assert len(results) == 100
        for result in results:
            assert result.get("_quarantine") == False
            assert result.get("resource_type") == "Patient"
    
    def test_parse_bulk_mixed_resources(self, bulk_mixed_resources):
        """Parse mixed resource types from bulk fixture."""
        parser = FhirParser()
        
        results = []
        for resource in bulk_mixed_resources:
            result = parser.parse(resource)
            results.append(result)
        
        # All should parse (valid ones at least)
        assert len(results) > 0
        
        # Count by resource type
        resource_types = [r.get("resource_type") for r in results if r.get("resource_type")]
        assert len(resource_types) > 0
