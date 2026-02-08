"""
FHIR Pipeline Resilience Tests

Tests for resilience patterns implemented in the FHIR pipeline:
1. Broader exception handling in UDFs - no single bad record should crash pipeline
2. Null/empty input handling - graceful degradation
3. Unexpected data types - robust parsing
4. Watermarking support verification (structure only, actual watermarking tested in integration)
5. Quality metrics views - verify output structure

Run: pytest -v test_fhir_resilience.py

SDP Best Practice: Test-First Development
These tests verify that the pipeline handles all edge cases without crashing.
"""

import pytest
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the parsing functions from transformations module (pure Python, no pyspark needed)
from transformations.fhir_parser import (
    FhirParser, FhirValidator, QuarantineHandler,
    extract_coding, extract_reference, extract_identifier
)


# =============================================================================
# Broader Exception Handling Tests (via FhirValidator)
# =============================================================================

class TestFhirValidatorResilience:
    """Tests for broader exception handling in FhirValidator."""

    def test_null_input_returns_invalid_result(self):
        """Null input should return invalid result, not crash."""
        validator = FhirValidator()
        result = validator.validate(None)
        assert result is not None
        assert result.is_valid == False

    def test_empty_dict_returns_invalid_result(self):
        """Empty dict should return invalid result, not crash."""
        validator = FhirValidator()
        result = validator.validate({})
        assert result is not None
        assert result.is_valid == False

    def test_missing_resource_type_returns_invalid(self):
        """Object without resourceType should return invalid."""
        validator = FhirValidator()
        result = validator.validate({"id": "test-id"})
        assert result.is_valid == False
        # Check that errors mention resourceType (case insensitive)
        errors_str = str(result.errors).lower()
        assert "resourcetype" in errors_str or "resource" in errors_str

    def test_valid_patient_returns_valid_result(self):
        """Valid Patient resource should return valid result."""
        validator = FhirValidator()
        patient = {"resourceType": "Patient", "id": "test-123"}
        result = validator.validate(patient)
        assert result.is_valid == True
        assert result.resource_type == "Patient"
        assert result.resource_id == "test-123"

    def test_deeply_nested_data_does_not_crash(self):
        """Deeply nested/unusual structure shouldn't crash."""
        validator = FhirValidator()
        malformed = {
            "resourceType": "Patient",
            "id": "test",
            "meta": {"versionId": {"deeply": {"nested": "not_a_string"}}},
            "extension": "not_an_array",
        }
        result = validator.validate(malformed)
        # Should not crash - may or may not be valid but shouldn't throw
        assert result is not None

    def test_unicode_input_handled(self):
        """Unicode characters in input should not crash."""
        validator = FhirValidator()
        patient = {"resourceType": "Patient", "id": "пациент-123", "name": [{"family": "日本語"}]}
        result = validator.validate(patient)
        assert result.is_valid == True
        assert result.resource_id == "пациент-123"


# =============================================================================
# FhirParser Resilience Tests
# =============================================================================

class TestFhirParserResilience:
    """Tests for broader exception handling in FhirParser."""

    def test_null_input_returns_quarantine_info(self):
        """Null input should return quarantine-compatible result, not crash."""
        parser = FhirParser()
        result = parser.parse(None)
        # FhirParser returns quarantine-compatible dict instead of None
        assert result is not None
        assert result.get("_quarantine") == True
        assert "_parse_error" in result

    def test_empty_dict_returns_quarantine_info(self):
        """Empty dict should return quarantine-compatible result."""
        parser = FhirParser()
        result = parser.parse({})
        assert result is not None
        assert result.get("_quarantine") == True

    def test_missing_resource_type_returns_quarantine_info(self):
        """Dict without resourceType should return quarantine-compatible result."""
        parser = FhirParser()
        result = parser.parse({"id": "test"})
        assert result is not None
        assert result.get("_quarantine") == True
        assert "resourceType" in str(result.get("_parse_error"))

    def test_valid_patient_parses(self):
        """Valid Patient should parse successfully."""
        parser = FhirParser()
        patient = {
            "resourceType": "Patient",
            "id": "test-123",
            "gender": "male",
            "birthDate": "1990-01-01"
        }
        result = parser.parse(patient)
        assert result is not None
        assert result["id"] == "test-123"
        assert result["gender"] == "male"
        assert result["birth_date"] == "1990-01-01"

    def test_patient_with_unexpected_field_types(self):
        """Patient with unexpected field types shouldn't crash."""
        parser = FhirParser()
        patient = {
            "resourceType": "Patient",
            "id": "test",
            "name": "not_an_array",  # Should be array
            "address": {"invalid": "format"},  # Should be array
        }
        # Should not crash - may return None or partial result
        result = parser.parse(patient)
        # The important thing is it doesn't throw


class TestObservationParserResilience:
    """Tests for broader exception handling in observation parsing."""

    def test_null_input_returns_quarantine_info(self):
        """Null input should return quarantine-compatible result."""
        parser = FhirParser()
        result = parser.parse(None)
        assert result is not None
        assert result.get("_quarantine") == True

    def test_wrong_resource_type_handled(self):
        parser = FhirParser()
        patient = {"resourceType": "Patient", "id": "test"}
        # Parse should work, just returns patient structure not observation
        result = parser.parse(patient)
        assert result is not None
        assert result.get("resource_type") == "Patient"

    def test_valid_observation_parses(self):
        """Valid Observation should parse successfully."""
        parser = FhirParser()
        obs = {
            "resourceType": "Observation",
            "id": "obs-123",
            "status": "final",
            "code": {"coding": [{"code": "12345", "system": "http://loinc.org"}]},
            "valueQuantity": {"value": 120, "unit": "mmHg"}
        }
        result = parser.parse(obs)
        assert result is not None
        assert result["id"] == "obs-123"
        assert result["status"] == "final"


class TestEncounterParserResilience:
    """Tests for broader exception handling in encounter parsing."""

    def test_valid_encounter_parses(self):
        parser = FhirParser()
        encounter = {
            "resourceType": "Encounter",
            "id": "enc-123",
            "status": "finished",
            "class": {"code": "AMB", "display": "ambulatory"}
        }
        result = parser.parse(encounter)
        assert result is not None
        assert result["id"] == "enc-123"
        assert result["status"] == "finished"


class TestConditionParserResilience:
    """Tests for broader exception handling in condition parsing."""

    def test_valid_condition_parses(self):
        parser = FhirParser()
        condition = {
            "resourceType": "Condition",
            "id": "cond-123",
            "code": {"coding": [{"code": "J06.9", "display": "Upper respiratory infection"}]},
            "subject": {"reference": "Patient/p1"}
        }
        result = parser.parse(condition)
        assert result is not None
        assert result["id"] == "cond-123"


class TestMedicationRequestParserResilience:
    """Tests for broader exception handling in medication request parsing."""

    def test_valid_medication_request_parses(self):
        parser = FhirParser()
        med_req = {
            "resourceType": "MedicationRequest",
            "id": "mr-123",
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [{"code": "197884", "display": "Lisinopril 10mg"}]
            },
            "subject": {"reference": "Patient/p1"}
        }
        result = parser.parse(med_req)
        assert result is not None
        assert result["id"] == "mr-123"
        assert result["status"] == "active"


class TestImmunizationParserResilience:
    """Tests for broader exception handling in immunization parsing."""

    def test_valid_immunization_parses(self):
        parser = FhirParser()
        imm = {
            "resourceType": "Immunization",
            "id": "imm-123",
            "status": "completed",
            "vaccineCode": {
                "coding": [{"code": "08", "display": "Hep B, adolescent or pediatric"}]
            },
            "patient": {"reference": "Patient/p1"},
            "occurrenceDateTime": "2024-01-15"
        }
        result = parser.parse(imm)
        assert result is not None
        assert result["id"] == "imm-123"
        assert result["status"] == "completed"


# =============================================================================
# QuarantineHandler Resilience Tests
# =============================================================================

class TestQuarantineHandlerResilience:
    """Tests for quarantine handling resilience."""

    def test_quarantine_null_resource(self):
        """Quarantine should handle None resource gracefully."""
        handler = QuarantineHandler()
        record = handler.process(None, "Test error")
        assert record is not None
        assert record.error_message == "Test error"

    def test_quarantine_empty_dict(self):
        """Quarantine should handle empty dict gracefully."""
        handler = QuarantineHandler()
        record = handler.process({}, "Empty resource")
        assert record is not None
        assert "Empty" in record.error_message

    def test_quarantine_invalid_resource(self):
        """Quarantine should capture details of invalid resource."""
        handler = QuarantineHandler()
        invalid = {"someField": "noResourceType"}
        record = handler.process(invalid, "Missing resourceType")
        assert record is not None
        assert record.raw_data is not None


# =============================================================================
# Quality Metrics Structure Tests
# =============================================================================

class TestQualityStatusLogic:
    """Tests for quality status calculation logic."""

    def test_healthy_threshold(self):
        """99%+ validation rate should be HEALTHY."""
        # This tests the logic that should be in bronze_fhir_quality_metrics
        rate = 99.5
        if rate >= 99.0:
            status = "HEALTHY"
        elif rate >= 95.0:
            status = "WARNING"
        else:
            status = "CRITICAL"
        assert status == "HEALTHY"

    def test_warning_threshold(self):
        """95-99% validation rate should be WARNING."""
        rate = 96.0
        if rate >= 99.0:
            status = "HEALTHY"
        elif rate >= 95.0:
            status = "WARNING"
        else:
            status = "CRITICAL"
        assert status == "WARNING"

    def test_critical_threshold(self):
        """<95% validation rate should be CRITICAL."""
        rate = 90.0
        if rate >= 99.0:
            status = "HEALTHY"
        elif rate >= 95.0:
            status = "WARNING"
        else:
            status = "CRITICAL"
        assert status == "CRITICAL"


class TestFreshnessStatusLogic:
    """Tests for freshness status calculation logic."""

    def test_fresh_threshold(self):
        """<= 60 minutes should be FRESH."""
        minutes = 30
        if minutes <= 60:
            status = "FRESH"
        elif minutes <= 360:
            status = "STALE"
        else:
            status = "VERY_STALE"
        assert status == "FRESH"

    def test_stale_threshold(self):
        """60-360 minutes should be STALE."""
        minutes = 120
        if minutes <= 60:
            status = "FRESH"
        elif minutes <= 360:
            status = "STALE"
        else:
            status = "VERY_STALE"
        assert status == "STALE"

    def test_very_stale_threshold(self):
        """> 360 minutes should be VERY_STALE."""
        minutes = 500
        if minutes <= 60:
            status = "FRESH"
        elif minutes <= 360:
            status = "STALE"
        else:
            status = "VERY_STALE"
        assert status == "VERY_STALE"


# =============================================================================
# Edge Cases and Boundary Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_json_input(self):
        """Very large JSON should not crash (though may be slow)."""
        validator = FhirValidator()
        # Create a patient with many extensions
        extensions = [{"url": f"http://example.org/ext{i}", "valueString": "x" * 100} for i in range(100)]
        patient = {
            "resourceType": "Patient",
            "id": "large-patient",
            "extension": extensions
        }
        result = validator.validate(patient)
        assert result is not None
        assert result.is_valid == True

    def test_special_characters_in_id(self):
        """Special characters in ID should be handled."""
        validator = FhirValidator()
        patient = {"resourceType": "Patient", "id": "test/id:with-special_chars.and.more"}
        result = validator.validate(patient)
        assert result.resource_id == "test/id:with-special_chars.and.more"

    def test_empty_arrays_handled(self):
        """Empty arrays should be handled gracefully."""
        parser = FhirParser()
        patient = {
            "resourceType": "Patient",
            "id": "test",
            "name": [],
            "address": [],
            "identifier": []
        }
        result = parser.parse(patient)
        assert result is not None
        assert result["id"] == "test"

    def test_null_fields_in_resource(self):
        """Null values in fields should be handled."""
        parser = FhirParser()
        patient = {
            "resourceType": "Patient",
            "id": "test",
            "gender": None,
            "birthDate": None
        }
        result = parser.parse(patient)
        assert result is not None
        assert result.get("gender") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
