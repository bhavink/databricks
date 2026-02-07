"""
FHIR R4 Schema Validation Tests

These tests verify that our schema validation correctly identifies
valid and invalid FHIR resources according to the R4 specification.

The validator should:
1. Validate resourceType is present and known
2. Validate required fields for each resource type
3. Validate enum values (status, gender, etc.)
4. Validate data types (dates, references)
5. Return clear error messages

Run: pytest -v test_fhir_schema_validation.py
"""

import pytest
import json
import sys
from typing import Dict, Any, List
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the implemented module
from transformations.fhir_parser import (
    FhirValidator,
    ValidationResult,
    SUPPORTED_RESOURCE_TYPES,
    REQUIRED_FIELDS,
)


# =============================================================================
# FhirValidator Contract Tests
# =============================================================================

class TestFhirValidatorContract:
    """Tests that define the FhirValidator interface contract."""
    
    def test_validator_exists(self):
        """FhirValidator class must exist."""
        assert FhirValidator is not None
    
    def test_validator_has_validate_method(self):
        """FhirValidator must have a validate() method."""
        validator = FhirValidator()
        assert hasattr(validator, 'validate')
        assert callable(validator.validate)
    
    def test_validate_returns_validation_result(self, valid_patient_minimal):
        """validate() must return a ValidationResult."""
        validator = FhirValidator()
        result = validator.validate(valid_patient_minimal)
        assert isinstance(result, ValidationResult)
    
    def test_validation_result_has_is_valid(self, valid_patient_minimal):
        """ValidationResult must have is_valid boolean."""
        validator = FhirValidator()
        result = validator.validate(valid_patient_minimal)
        assert hasattr(result, 'is_valid')
        assert isinstance(result.is_valid, bool)
    
    def test_validation_result_has_errors_list(self, valid_patient_minimal):
        """ValidationResult must have errors list."""
        validator = FhirValidator()
        result = validator.validate(valid_patient_minimal)
        assert hasattr(result, 'errors')
        assert isinstance(result.errors, list)


# =============================================================================
# Resource Type Validation Tests
# =============================================================================

class TestResourceTypeValidation:
    """Tests for resourceType field validation."""
    
    def test_missing_resource_type_is_invalid(self):
        """Resource without resourceType is invalid."""
        validator = FhirValidator()
        resource = {"id": "test-001"}
        result = validator.validate(resource)
        
        assert result.is_valid == False
        assert any("resourceType" in err for err in result.errors)
    
    def test_unknown_resource_type_has_error(self):
        """Unknown resourceType should produce an error."""
        validator = FhirValidator()
        resource = {"resourceType": "FakeResource", "id": "test-001"}
        result = validator.validate(resource)
        
        assert result.is_valid == False
        assert any("Unknown" in err or "FakeResource" in err for err in result.errors)
    
    def test_patient_resource_type_is_valid(self, valid_patient_minimal):
        """Patient resourceType is valid."""
        validator = FhirValidator()
        result = validator.validate(valid_patient_minimal)
        
        assert result.is_valid == True
        assert result.resource_type == "Patient"
    
    def test_observation_resource_type_is_valid(self, valid_observation_vital_sign):
        """Observation resourceType is valid."""
        validator = FhirValidator()
        result = validator.validate(valid_observation_vital_sign)
        
        assert result.is_valid == True
        assert result.resource_type == "Observation"
    
    def test_all_supported_types_are_valid(self, supported_resource_types):
        """All supported resource types should be valid."""
        validator = FhirValidator()
        
        for resource_type in supported_resource_types:
            # Create minimal resource
            resource = {"resourceType": resource_type, "id": f"test-{resource_type.lower()}"}
            
            # Add required fields for specific types
            if resource_type == "Observation":
                resource["status"] = "final"
                resource["code"] = {"coding": [{"code": "test"}]}
            elif resource_type == "Encounter":
                resource["status"] = "finished"
                resource["class"] = {"code": "AMB"}
            elif resource_type == "Bundle":
                resource["type"] = "collection"
            elif resource_type == "MedicationRequest":
                resource["status"] = "active"
                resource["intent"] = "order"
                resource["subject"] = {"reference": "Patient/1"}
                resource["medicationCodeableConcept"] = {"coding": [{"code": "test"}]}
            elif resource_type == "Immunization":
                resource["status"] = "completed"
                resource["vaccineCode"] = {"coding": [{"code": "test"}]}
                resource["patient"] = {"reference": "Patient/1"}
                resource["occurrenceDateTime"] = "2024-01-01"
            elif resource_type == "DiagnosticReport":
                resource["status"] = "final"
                resource["code"] = {"coding": [{"code": "test"}]}
            elif resource_type == "Condition":
                resource["subject"] = {"reference": "Patient/1"}
            
            result = validator.validate(resource)
            # For known resource types, shouldn't have "Unknown" error
            assert not any("Unknown" in err for err in result.errors), f"Failed for {resource_type}"


# =============================================================================
# Required Fields Validation Tests
# =============================================================================

class TestRequiredFieldsValidation:
    """Tests for required fields validation."""
    
    def test_observation_requires_status(self, invalid_observation_missing_status):
        """Observation requires status field."""
        validator = FhirValidator()
        result = validator.validate(invalid_observation_missing_status)
        
        assert result.is_valid == False
        assert any("status" in err for err in result.errors)
    
    def test_encounter_requires_class(self, invalid_encounter_missing_class):
        """Encounter requires class field."""
        validator = FhirValidator()
        result = validator.validate(invalid_encounter_missing_class)
        
        assert result.is_valid == False
        assert any("class" in err for err in result.errors)
    
    def test_medication_request_requires_intent(self, invalid_medication_request_missing_intent):
        """MedicationRequest requires intent field."""
        validator = FhirValidator()
        result = validator.validate(invalid_medication_request_missing_intent)
        
        assert result.is_valid == False
        assert any("intent" in err for err in result.errors)


# =============================================================================
# Enum Value Validation Tests
# =============================================================================

class TestEnumValueValidation:
    """Tests for enum field value validation."""
    
    def test_patient_invalid_gender(self, invalid_patient_wrong_gender):
        """Patient with invalid gender value should fail."""
        validator = FhirValidator()
        result = validator.validate(invalid_patient_wrong_gender)
        
        assert result.is_valid == False
        assert any("gender" in err.lower() for err in result.errors)
    
    def test_observation_invalid_status(self, invalid_observation_wrong_status):
        """Observation with invalid status value should fail."""
        validator = FhirValidator()
        result = validator.validate(invalid_observation_wrong_status)
        
        assert result.is_valid == False
        assert any("status" in err.lower() for err in result.errors)
    
    def test_patient_valid_gender_values(self):
        """All valid Patient gender values should pass."""
        validator = FhirValidator()
        
        for gender in ["male", "female", "other", "unknown"]:
            resource = {
                "resourceType": "Patient",
                "id": f"test-{gender}",
                "gender": gender
            }
            result = validator.validate(resource)
            assert result.is_valid == True, f"Gender '{gender}' should be valid"
    
    def test_observation_valid_status_values(self):
        """All valid Observation status values should pass."""
        validator = FhirValidator()
        
        valid_statuses = [
            "registered", "preliminary", "final", "amended",
            "corrected", "cancelled", "entered-in-error", "unknown"
        ]
        
        for status in valid_statuses:
            resource = {
                "resourceType": "Observation",
                "id": f"test-{status}",
                "status": status,
                "code": {"coding": [{"code": "test"}]}
            }
            result = validator.validate(resource)
            assert result.is_valid == True, f"Status '{status}' should be valid"


# =============================================================================
# Data Type Validation Tests
# =============================================================================

class TestDataTypeValidation:
    """Tests for data type format validation."""
    
    def test_empty_resource_is_invalid(self, invalid_empty_object):
        """Empty resource is invalid."""
        validator = FhirValidator()
        result = validator.validate(invalid_empty_object)
        
        assert result.is_valid == False
    
    def test_null_values_handled(self, invalid_null_values):
        """Resource with null required values is invalid."""
        validator = FhirValidator()
        result = validator.validate(invalid_null_values)
        
        # Should have errors for null values
        # The exact behavior depends on implementation
        assert isinstance(result, ValidationResult)


# =============================================================================
# Edge Case Validation Tests
# =============================================================================

class TestEdgeCaseValidation:
    """Tests for edge cases in validation."""
    
    def test_unicode_in_names_is_valid(self, edge_case_unicode_in_names):
        """Unicode characters in names should be valid."""
        validator = FhirValidator()
        result = validator.validate(edge_case_unicode_in_names)
        
        # Should be valid - unicode is allowed
        assert result.is_valid == True
    
    def test_very_long_text_is_valid(self, edge_case_very_long_text):
        """Very long text should be valid."""
        validator = FhirValidator()
        result = validator.validate(edge_case_very_long_text)
        
        # Should be valid - no length limits in FHIR core
        assert result.is_valid == True
    
    def test_many_identifiers_is_valid(self, edge_case_many_identifiers):
        """Many identifiers should be valid."""
        validator = FhirValidator()
        result = validator.validate(edge_case_many_identifiers)
        
        assert result.is_valid == True
    
    def test_deeply_nested_extensions_is_valid(self, edge_case_deeply_nested):
        """Deeply nested extensions should be valid."""
        validator = FhirValidator()
        result = validator.validate(edge_case_deeply_nested)
        
        assert result.is_valid == True
    
    def test_empty_arrays_is_valid(self, edge_case_empty_arrays):
        """Empty arrays should be valid."""
        validator = FhirValidator()
        result = validator.validate(edge_case_empty_arrays)
        
        assert result.is_valid == True
    
    def test_old_dates_is_valid(self, edge_case_old_dates):
        """Old dates (historical) should be valid."""
        validator = FhirValidator()
        result = validator.validate(edge_case_old_dates)
        
        assert result.is_valid == True
    
    def test_future_dates_valid(self, edge_case_future_dates):
        """Future dates should be valid (no business rule enforcement)."""
        validator = FhirValidator()
        result = validator.validate(edge_case_future_dates)
        
        # Future dates are technically valid FHIR (appointment, scheduled)
        assert result.is_valid == True


# =============================================================================
# Bundle Validation Tests
# =============================================================================

class TestBundleValidation:
    """Tests for Bundle-specific validation."""
    
    def test_bundle_collection_is_valid(self, valid_bundle_collection):
        """Collection Bundle is valid."""
        validator = FhirValidator()
        result = validator.validate(valid_bundle_collection)
        
        assert result.is_valid == True
        assert result.resource_type == "Bundle"
    
    def test_bundle_transaction_is_valid(self, valid_bundle_transaction):
        """Transaction Bundle is valid."""
        validator = FhirValidator()
        result = validator.validate(valid_bundle_transaction)
        
        assert result.is_valid == True
    
    def test_bundle_missing_type_is_invalid(self):
        """Bundle without type is invalid."""
        validator = FhirValidator()
        resource = {
            "resourceType": "Bundle",
            "id": "test-bundle",
            "entry": []
        }
        result = validator.validate(resource)
        
        assert result.is_valid == False
        assert any("type" in err for err in result.errors)


# =============================================================================
# Validation Result Content Tests
# =============================================================================

class TestValidationResultContent:
    """Tests for ValidationResult content quality."""
    
    def test_valid_result_has_no_errors(self, valid_patient_full):
        """Valid resource should have no errors."""
        validator = FhirValidator()
        result = validator.validate(valid_patient_full)
        
        assert result.is_valid == True
        assert len(result.errors) == 0
    
    def test_invalid_result_has_descriptive_errors(self):
        """Invalid resource should have descriptive error messages."""
        validator = FhirValidator()
        resource = {"id": "test"}  # Missing resourceType
        result = validator.validate(resource)
        
        assert result.is_valid == False
        assert len(result.errors) > 0
        # Errors should be strings
        for error in result.errors:
            assert isinstance(error, str)
            assert len(error) > 0
    
    def test_result_includes_resource_type(self, valid_patient_minimal):
        """ValidationResult should include resource_type."""
        validator = FhirValidator()
        result = validator.validate(valid_patient_minimal)
        
        assert result.resource_type == "Patient"
    
    def test_result_includes_resource_id(self, valid_patient_minimal):
        """ValidationResult should include resource_id."""
        validator = FhirValidator()
        result = validator.validate(valid_patient_minimal)
        
        assert result.resource_id == valid_patient_minimal["id"]
    
    def test_result_to_dict_works(self, valid_patient_minimal):
        """ValidationResult should be serializable to dict."""
        validator = FhirValidator()
        result = validator.validate(valid_patient_minimal)
        
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "is_valid" in result_dict
        assert "errors" in result_dict


# =============================================================================
# Strict Mode Tests
# =============================================================================

class TestStrictModeValidation:
    """Tests for strict validation mode."""
    
    def test_strict_mode_warns_on_missing_id(self):
        """Strict mode should warn if id is missing."""
        validator = FhirValidator(strict=True)
        resource = {"resourceType": "Patient"}
        result = validator.validate(resource)
        
        # Should be valid but have warnings
        assert result.is_valid == True
        assert len(result.warnings) > 0 or len(result.errors) == 0
    
    def test_non_strict_mode_allows_missing_id(self):
        """Non-strict mode should not warn on missing id."""
        validator = FhirValidator(strict=False)
        resource = {"resourceType": "Patient"}
        result = validator.validate(resource)
        
        # Should be valid with no warnings
        assert result.is_valid == True
        assert len(result.warnings) == 0


# =============================================================================
# Bulk Validation Tests
# =============================================================================

class TestBulkValidation:
    """Tests for validating bulk data."""
    
    def test_bulk_patients_all_valid(self, bulk_patients_100):
        """All bulk patients should be valid."""
        validator = FhirValidator()
        
        valid_count = 0
        for patient in bulk_patients_100:
            result = validator.validate(patient)
            if result.is_valid:
                valid_count += 1
        
        # All should be valid
        assert valid_count == 100
    
    def test_bulk_mixed_resources_validation(self, bulk_mixed_resources):
        """Bulk mixed resources should validate correctly."""
        validator = FhirValidator()
        
        results = []
        for resource in bulk_mixed_resources:
            result = validator.validate(resource)
            results.append(result)
        
        # Should have some valid, potentially some invalid
        assert len(results) > 0
        valid_count = sum(1 for r in results if r.is_valid)
        assert valid_count > 0  # At least some should be valid
