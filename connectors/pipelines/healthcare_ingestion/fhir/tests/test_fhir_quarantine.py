"""
FHIR Quarantine and Error Handling Tests

These tests verify that invalid/failed FHIR resources are properly
quarantined with appropriate error information for debugging and reprocessing.

The quarantine system should:
1. Capture original resource data
2. Record detailed error information
3. Classify error types (PARSE, VALIDATION, SCHEMA, TRANSFORM)
4. Support reprocessing workflows
5. Track quarantine metadata (timestamp, attempts)

Run: pytest -v test_fhir_quarantine.py
"""

import pytest
import json
import sys
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the implemented module
from transformations.fhir_parser import (
    QuarantineHandler,
    QuarantineRecord,
    FhirParser,
    FhirValidator,
)


# =============================================================================
# QuarantineHandler Contract Tests
# =============================================================================

class TestQuarantineHandlerContract:
    """Tests that define the QuarantineHandler interface contract."""
    
    def test_handler_exists(self):
        """QuarantineHandler class must exist."""
        assert QuarantineHandler is not None
    
    def test_handler_has_process_method(self):
        """QuarantineHandler must have a process() method."""
        handler = QuarantineHandler()
        assert hasattr(handler, 'process')
        assert callable(handler.process)
    
    def test_process_returns_quarantine_record(self):
        """process() must return a QuarantineRecord."""
        handler = QuarantineHandler()
        resource = {"resourceType": "Patient", "id": "test"}
        record = handler.process(resource, "Test error")
        
        assert isinstance(record, QuarantineRecord)
    
    def test_quarantine_record_has_required_fields(self):
        """QuarantineRecord must have required fields."""
        handler = QuarantineHandler()
        resource = {"resourceType": "Patient", "id": "test"}
        record = handler.process(resource, "Test error")
        
        assert hasattr(record, 'quarantine_id')
        assert hasattr(record, 'raw_data')
        assert hasattr(record, 'error_message')
        assert hasattr(record, 'error_type')
        assert hasattr(record, 'timestamp')


# =============================================================================
# QuarantineRecord Structure Tests
# =============================================================================

class TestQuarantineRecordStructure:
    """Tests for QuarantineRecord data structure."""
    
    def test_record_has_unique_id(self):
        """Each record should have a unique quarantine_id."""
        handler = QuarantineHandler()
        resource = {"resourceType": "Patient", "id": "test"}
        
        record1 = handler.process(resource, "Error 1")
        record2 = handler.process(resource, "Error 2")
        
        assert record1.quarantine_id != record2.quarantine_id
    
    def test_record_preserves_raw_data(self):
        """Record should preserve original resource data."""
        handler = QuarantineHandler()
        resource = {"resourceType": "Patient", "id": "test-001", "custom": "data"}
        record = handler.process(resource, "Test error")
        
        # raw_data should be JSON string of original resource
        parsed = json.loads(record.raw_data)
        assert parsed["id"] == "test-001"
        assert parsed["custom"] == "data"
    
    def test_record_captures_error_message(self):
        """Record should capture error message."""
        handler = QuarantineHandler()
        error_msg = "Missing required field: status"
        record = handler.process({}, error_msg)
        
        assert record.error_message == error_msg
    
    def test_record_captures_timestamp(self):
        """Record should have timestamp."""
        handler = QuarantineHandler()
        before = datetime.utcnow()
        record = handler.process({}, "Error")
        after = datetime.utcnow()
        
        assert before <= record.timestamp <= after
    
    def test_record_can_handle_string_input(self):
        """Record can handle string (raw JSON) input."""
        handler = QuarantineHandler()
        json_str = '{"resourceType": "Patient"}'
        record = handler.process(json_str, "Parse error")
        
        assert record.raw_data == json_str
    
    def test_record_to_dict(self):
        """Record should be convertible to dictionary."""
        handler = QuarantineHandler()
        record = handler.process({"test": "data"}, "Error")
        
        record_dict = record.to_dict()
        assert isinstance(record_dict, dict)
        assert "quarantine_id" in record_dict
        assert "error_message" in record_dict
        assert "timestamp" in record_dict


# =============================================================================
# Error Type Classification Tests
# =============================================================================

class TestErrorTypeClassification:
    """Tests for error type classification."""
    
    def test_parse_error_type(self):
        """PARSE error type for JSON parsing failures."""
        handler = QuarantineHandler()
        record = handler.process("invalid json", "JSON parse error", error_type="PARSE")
        
        assert record.error_type == "PARSE"
    
    def test_validation_error_type(self):
        """VALIDATION error type for schema validation failures."""
        handler = QuarantineHandler()
        record = handler.process(
            {"resourceType": "Patient", "gender": "invalid"},
            "Invalid gender value",
            error_type="VALIDATION"
        )
        
        assert record.error_type == "VALIDATION"
    
    def test_schema_error_type(self):
        """SCHEMA error type for unknown resource types."""
        handler = QuarantineHandler()
        record = handler.process(
            {"resourceType": "Unknown"},
            "Unknown resourceType",
            error_type="SCHEMA"
        )
        
        assert record.error_type == "SCHEMA"
    
    def test_transform_error_type(self):
        """TRANSFORM error type for transformation failures."""
        handler = QuarantineHandler()
        record = handler.process(
            {"resourceType": "Patient"},
            "Transformation failed",
            error_type="TRANSFORM"
        )
        
        assert record.error_type == "TRANSFORM"
    
    def test_classify_error_json_decode(self):
        """classify_error should identify JSON errors."""
        handler = QuarantineHandler()
        
        try:
            json.loads("invalid json")
        except json.JSONDecodeError as e:
            error_type = handler.classify_error(e)
            assert error_type == "PARSE"
    
    def test_classify_error_validation(self):
        """classify_error should identify validation errors."""
        handler = QuarantineHandler()
        
        class ValidationError(Exception):
            pass
        
        error = ValidationError("Missing required field: status")
        error_type = handler.classify_error(error)
        assert error_type == "VALIDATION"


# =============================================================================
# Quarantine Processing Tests
# =============================================================================

class TestQuarantineProcessing:
    """Tests for processing resources into quarantine."""
    
    def test_process_invalid_json(self, invalid_json_malformed):
        """Process malformed JSON into quarantine."""
        handler = QuarantineHandler()
        record = handler.process(invalid_json_malformed, "Malformed JSON", error_type="PARSE")
        
        assert record.error_type == "PARSE"
        assert record.raw_data == invalid_json_malformed
    
    def test_process_missing_resource_type(self, invalid_missing_resource_type):
        """Process resource missing resourceType."""
        handler = QuarantineHandler()
        record = handler.process(
            invalid_missing_resource_type,
            "Missing resourceType",
            error_type="VALIDATION"
        )
        
        assert record.error_type == "VALIDATION"
        assert "resourceType" in record.error_message
    
    def test_process_with_source_file(self):
        """Process with source file metadata."""
        handler = QuarantineHandler()
        record = handler.process(
            {"resourceType": "Patient"},
            "Error",
            source_file="/data/fhir/batch001.ndjson"
        )
        
        assert record.source_file == "/data/fhir/batch001.ndjson"
    
    def test_process_with_source_line(self):
        """Process with source line number."""
        handler = QuarantineHandler()
        record = handler.process(
            {"resourceType": "Patient"},
            "Error",
            source_line=42
        )
        
        assert record.source_line == 42
    
    def test_process_extracts_resource_type(self):
        """Process should extract resource_type if present."""
        handler = QuarantineHandler()
        record = handler.process(
            {"resourceType": "Observation", "id": "obs-001"},
            "Error"
        )
        
        assert record.resource_type == "Observation"
    
    def test_process_extracts_resource_id(self):
        """Process should extract resource_id if present."""
        handler = QuarantineHandler()
        record = handler.process(
            {"resourceType": "Patient", "id": "patient-001"},
            "Error"
        )
        
        assert record.resource_id == "patient-001"


# =============================================================================
# Reprocessing Tests
# =============================================================================

class TestReprocessing:
    """Tests for reprocessing workflow support."""
    
    def test_record_tracks_reprocess_attempts(self):
        """Record should track reprocess attempts."""
        handler = QuarantineHandler()
        record = handler.process({"test": "data"}, "Error")
        
        assert record.reprocess_attempts == 0
        
        record.mark_reprocess_attempt("Still failing")
        assert record.reprocess_attempts == 1
        
        record.mark_reprocess_attempt("Still failing")
        assert record.reprocess_attempts == 2
    
    def test_record_tracks_last_reprocess_time(self):
        """Record should track last reprocess time."""
        handler = QuarantineHandler()
        record = handler.process({"test": "data"}, "Error")
        
        assert record.last_reprocess_time is None
        
        record.mark_reprocess_attempt("Error")
        assert record.last_reprocess_time is not None
    
    def test_record_resolved_flag(self):
        """Record should have resolved flag."""
        handler = QuarantineHandler()
        record = handler.process({"test": "data"}, "Error")
        
        assert record.resolved == False
        record.resolved = True
        assert record.resolved == True


# =============================================================================
# Error Message Quality Tests
# =============================================================================

class TestErrorMessageQuality:
    """Tests for error message quality and usefulness."""
    
    def test_error_message_is_string(self):
        """Error message should be a string."""
        handler = QuarantineHandler()
        record = handler.process({}, "Test error")
        
        assert isinstance(record.error_message, str)
    
    def test_error_message_not_empty(self):
        """Error message should not be empty."""
        handler = QuarantineHandler()
        record = handler.process({}, "Validation failed: missing status")
        
        assert len(record.error_message) > 0
    
    def test_error_message_preserves_details(self):
        """Error message should preserve error details."""
        handler = QuarantineHandler()
        detailed_error = "Invalid gender value 'xyz'. Expected one of: male, female, other, unknown"
        record = handler.process({}, detailed_error)
        
        assert "gender" in record.error_message
        assert "xyz" in record.error_message


# =============================================================================
# Parser Integration Tests
# =============================================================================

class TestParserQuarantineIntegration:
    """Tests for parser's quarantine integration."""
    
    def test_parser_flags_invalid_for_quarantine(self):
        """Parser should flag invalid resources for quarantine."""
        parser = FhirParser()
        result = parser.parse({})
        
        assert result.get("_quarantine") == True
    
    def test_parser_includes_parse_error(self):
        """Parser should include parse error message."""
        parser = FhirParser()
        result = parser.parse({"id": "test"})  # Missing resourceType
        
        assert result.get("_quarantine") == True
        assert result.get("_parse_error") is not None
    
    def test_parser_valid_resource_not_quarantined(self, valid_patient_minimal):
        """Valid resources should not be quarantined."""
        parser = FhirParser()
        result = parser.parse(valid_patient_minimal)
        
        assert result.get("_quarantine") == False
    
    def test_parser_json_parse_error_quarantined(self):
        """JSON parse errors should be quarantined."""
        parser = FhirParser()
        result = parser.parse_json_string("invalid json")
        
        assert result.get("_quarantine") == True
        assert "JSON" in result.get("_parse_error", "")


# =============================================================================
# Quarantine Record Serialization Tests
# =============================================================================

class TestQuarantineRecordSerialization:
    """Tests for quarantine record serialization."""
    
    def test_record_to_dict_serializable(self):
        """Record dict should be JSON serializable."""
        handler = QuarantineHandler()
        record = handler.process({"test": "data"}, "Error")
        record_dict = record.to_dict()
        
        # Should not raise
        json_str = json.dumps(record_dict)
        assert isinstance(json_str, str)
    
    def test_record_preserves_complex_resource(self):
        """Record should preserve complex resource structure."""
        handler = QuarantineHandler()
        complex_resource = {
            "resourceType": "Patient",
            "id": "test",
            "name": [{"family": "Doe", "given": ["John"]}],
            "address": [{"city": "Springfield", "state": "IL"}],
            "extension": [{"url": "http://example.org/ext", "valueString": "test"}]
        }
        record = handler.process(complex_resource, "Error")
        
        # Parse raw_data back
        restored = json.loads(record.raw_data)
        assert restored["name"][0]["family"] == "Doe"
        assert restored["extension"][0]["valueString"] == "test"
    
    def test_record_handles_unicode(self):
        """Record should handle unicode characters."""
        handler = QuarantineHandler()
        unicode_resource = {
            "resourceType": "Patient",
            "name": [{"family": "佐藤", "given": ["太郎"]}]
        }
        record = handler.process(unicode_resource, "Error with 日本語")
        
        # Should preserve unicode
        restored = json.loads(record.raw_data)
        assert restored["name"][0]["family"] == "佐藤"


# =============================================================================
# Performance Tests
# =============================================================================

class TestQuarantinePerformance:
    """Tests for quarantine system performance."""
    
    def test_process_many_records(self):
        """Handler should process many records efficiently."""
        handler = QuarantineHandler()
        
        records = []
        for i in range(1000):
            record = handler.process(
                {"resourceType": "Patient", "id": f"patient-{i}"},
                f"Error {i}"
            )
            records.append(record)
        
        # All should have unique IDs
        ids = [r.quarantine_id for r in records]
        assert len(set(ids)) == 1000
    
    def test_handler_maintains_counter(self):
        """Handler should maintain unique counter."""
        handler = QuarantineHandler()
        
        id1 = handler.process({}, "Error 1").quarantine_id
        id2 = handler.process({}, "Error 2").quarantine_id
        
        # IDs should be different and incrementing
        assert id1 != id2
