"""
End-to-End Test: FHIR REST API Ingestion → SDP Pipeline Processing

This test validates the complete flow:
1. Fetch FHIR resources from public HAPI server
2. Write to local directory (simulating UC Volume)
3. Parse using the SAME logic from bronze_fhir.py
4. Validate each resource type is correctly processed

Run:
    pytest test_e2e_api_to_pipeline.py -v -s

This test hits real servers - use sparingly.
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ingestion.fhir_client import FHIRClient, FHIRClientConfig
from ingestion.fhir_ingestion import FHIRIngestion


# =============================================================================
# FHIR Parsing Logic (Extracted from bronze_fhir.py for validation)
# =============================================================================

def parse_fhir_resource(raw_json: str) -> Dict[str, Any]:
    """
    Parse FHIR resource - SAME LOGIC as SDP pipeline UDF.
    This validates that API-fetched data is compatible with pipeline processing.
    """
    import json
    from datetime import datetime
    
    def safe_get(obj, *keys, default=None):
        """Safely navigate nested dictionaries"""
        current = obj
        for key in keys:
            if current is None:
                return default
            if isinstance(key, int):
                if isinstance(current, list) and len(current) > key:
                    current = current[key]
                else:
                    return default
            else:
                current = current.get(key) if isinstance(current, dict) else default
        return current if current is not None else default
    
    def extract_reference_id(reference: str) -> str:
        """Extract ID from FHIR reference (e.g., 'Patient/123' → '123')"""
        if reference and '/' in reference:
            return reference.split('/')[-1]
        return reference
    
    def extract_coding(codeable_concept: Dict) -> Dict:
        """Extract first coding from CodeableConcept"""
        if not codeable_concept:
            return {}
        codings = codeable_concept.get("coding", [])
        if codings:
            c = codings[0]
            return {
                "system": c.get("system"),
                "code": c.get("code"),
                "display": c.get("display")
            }
        return {"text": codeable_concept.get("text")}
    
    try:
        resource = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        resource_type = resource.get("resourceType")
        
        base_result = {
            "resource_id": resource.get("id"),
            "resource_type": resource_type,
            "is_valid": True,
            "parse_error": None,
            "meta_version_id": safe_get(resource, "meta", "versionId"),
            "meta_last_updated": safe_get(resource, "meta", "lastUpdated"),
        }
        
        # Type-specific parsing
        if resource_type == "Patient":
            names = resource.get("name", [])
            name = names[0] if names else {}
            
            base_result.update({
                "patient_id": resource.get("id"),
                "gender": resource.get("gender"),
                "birth_date": resource.get("birthDate"),
                "deceased_boolean": resource.get("deceasedBoolean"),
                "deceased_datetime": resource.get("deceasedDateTime"),
                "name_family": name.get("family"),
                "name_given": ", ".join(name.get("given", [])),
                "name_use": name.get("use"),
                "active": resource.get("active"),
                "identifier_count": len(resource.get("identifier", [])),
                "address_count": len(resource.get("address", [])),
                "telecom_count": len(resource.get("telecom", [])),
            })
            
        elif resource_type == "Observation":
            code = extract_coding(resource.get("code"))
            value_quantity = resource.get("valueQuantity", {})
            
            base_result.update({
                "observation_id": resource.get("id"),
                "status": resource.get("status"),
                "subject_id": extract_reference_id(safe_get(resource, "subject", "reference")),
                "encounter_id": extract_reference_id(safe_get(resource, "encounter", "reference")),
                "effective_datetime": resource.get("effectiveDateTime"),
                "code_system": code.get("system"),
                "code_code": code.get("code"),
                "code_display": code.get("display"),
                "value_quantity_value": value_quantity.get("value"),
                "value_quantity_unit": value_quantity.get("unit"),
                "value_string": resource.get("valueString"),
                "category_count": len(resource.get("category", [])),
            })
            
        elif resource_type == "Encounter":
            type_coding = extract_coding(safe_get(resource, "type", 0))
            class_coding = resource.get("class", {})
            period = resource.get("period", {})
            
            base_result.update({
                "encounter_id": resource.get("id"),
                "status": resource.get("status"),
                "class_code": class_coding.get("code"),
                "class_display": class_coding.get("display"),
                "type_code": type_coding.get("code"),
                "type_display": type_coding.get("display"),
                "subject_id": extract_reference_id(safe_get(resource, "subject", "reference")),
                "period_start": period.get("start"),
                "period_end": period.get("end"),
                "participant_count": len(resource.get("participant", [])),
                "reason_count": len(resource.get("reasonCode", [])),
            })
            
        elif resource_type == "Condition":
            code = extract_coding(resource.get("code"))
            category = extract_coding(safe_get(resource, "category", 0))
            
            base_result.update({
                "condition_id": resource.get("id"),
                "clinical_status": safe_get(resource, "clinicalStatus", "coding", 0, "code"),
                "verification_status": safe_get(resource, "verificationStatus", "coding", 0, "code"),
                "category_code": category.get("code"),
                "category_display": category.get("display"),
                "code_system": code.get("system"),
                "code_code": code.get("code"),
                "code_display": code.get("display"),
                "subject_id": extract_reference_id(safe_get(resource, "subject", "reference")),
                "encounter_id": extract_reference_id(safe_get(resource, "encounter", "reference")),
                "onset_datetime": resource.get("onsetDateTime"),
                "recorded_date": resource.get("recordedDate"),
            })
            
        elif resource_type == "MedicationRequest":
            medication = extract_coding(resource.get("medicationCodeableConcept"))
            
            base_result.update({
                "medication_request_id": resource.get("id"),
                "status": resource.get("status"),
                "intent": resource.get("intent"),
                "medication_code": medication.get("code"),
                "medication_display": medication.get("display"),
                "medication_system": medication.get("system"),
                "subject_id": extract_reference_id(safe_get(resource, "subject", "reference")),
                "encounter_id": extract_reference_id(safe_get(resource, "encounter", "reference")),
                "requester_id": extract_reference_id(safe_get(resource, "requester", "reference")),
                "authored_on": resource.get("authoredOn"),
                "dosage_instruction_count": len(resource.get("dosageInstruction", [])),
            })
            
        elif resource_type == "Immunization":
            vaccine = extract_coding(resource.get("vaccineCode"))
            
            base_result.update({
                "immunization_id": resource.get("id"),
                "status": resource.get("status"),
                "vaccine_code": vaccine.get("code"),
                "vaccine_display": vaccine.get("display"),
                "vaccine_system": vaccine.get("system"),
                "patient_id": extract_reference_id(safe_get(resource, "patient", "reference")),
                "encounter_id": extract_reference_id(safe_get(resource, "encounter", "reference")),
                "occurrence_datetime": resource.get("occurrenceDateTime"),
                "primary_source": resource.get("primarySource"),
                "lot_number": resource.get("lotNumber"),
            })
        
        return base_result
        
    except Exception as e:
        return {
            "resource_id": None,
            "resource_type": None,
            "is_valid": False,
            "parse_error": str(e),
        }


# =============================================================================
# E2E Test Fixtures
# =============================================================================

@pytest.fixture
def temp_volume():
    """Temporary directory simulating UC Volume"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def ingestion_service(temp_volume):
    """Configured ingestion service"""
    return FHIRIngestion(
        base_url="http://hapi.fhir.org/baseR4",
        output_volume=temp_volume,
        output_subdir="api_extracts",
        use_dbutils=False,
    )


# =============================================================================
# E2E Tests
# =============================================================================

@pytest.mark.integration
class TestE2EApiToPipeline:
    """
    End-to-end tests: API → Volume → Pipeline parsing
    """
    
    def test_e2e_patient_flow(self, ingestion_service, temp_volume):
        """
        E2E: Fetch Patients from HAPI → Write NDJSON → Parse with pipeline logic
        """
        print("\n" + "="*60)
        print("E2E TEST: Patient Flow")
        print("="*60)
        
        # Step 1: Fetch from API
        print("\n[1] Fetching Patients from HAPI...")
        result = ingestion_service.ingest_resources(
            resource_types=["Patient"],
            max_per_resource=10,
        )
        
        assert result.success, f"Ingestion failed: {result.errors}"
        assert result.resources_fetched > 0, "No patients fetched"
        print(f"    ✓ Fetched {result.resources_fetched} patients")
        
        # Step 2: Verify files created
        print("\n[2] Verifying NDJSON files...")
        assert len(result.files_created) > 0, "No files created"
        
        ndjson_file = f"{temp_volume}/api_extracts/{os.path.basename(result.files_created[0])}"
        assert os.path.exists(ndjson_file), f"File not found: {ndjson_file}"
        print(f"    ✓ File created: {os.path.basename(ndjson_file)}")
        
        # Step 3: Parse with pipeline logic
        print("\n[3] Parsing with pipeline logic...")
        parsed_count = 0
        valid_count = 0
        
        with open(ndjson_file) as f:
            for line in f:
                parsed = parse_fhir_resource(line.strip())
                parsed_count += 1
                
                # Validate parsing
                assert parsed["resource_type"] == "Patient", f"Wrong type: {parsed['resource_type']}"
                assert parsed["is_valid"], f"Parse error: {parsed.get('parse_error')}"
                assert parsed["resource_id"], "Missing resource_id"
                
                # Validate Patient-specific fields extracted
                assert "gender" in parsed, "Missing gender field"
                assert "birth_date" in parsed, "Missing birth_date field"
                
                if parsed["is_valid"]:
                    valid_count += 1
        
        print(f"    ✓ Parsed {parsed_count} patients, {valid_count} valid")
        assert valid_count == parsed_count, "Some patients failed parsing"
        
        print("\n✅ E2E Patient flow PASSED")
    
    def test_e2e_observation_flow(self, ingestion_service, temp_volume):
        """
        E2E: Fetch Observations from HAPI → Write NDJSON → Parse with pipeline logic
        """
        print("\n" + "="*60)
        print("E2E TEST: Observation Flow")
        print("="*60)
        
        # Fetch
        print("\n[1] Fetching Observations from HAPI...")
        result = ingestion_service.ingest_resources(
            resource_types=["Observation"],
            max_per_resource=10,
        )
        
        if result.resources_fetched == 0:
            pytest.skip("No observations available on HAPI (transient)")
        
        assert result.success, f"Ingestion failed: {result.errors}"
        print(f"    ✓ Fetched {result.resources_fetched} observations")
        
        # Parse
        print("\n[2] Parsing with pipeline logic...")
        ndjson_file = f"{temp_volume}/api_extracts/{os.path.basename(result.files_created[0])}"
        
        parsed_count = 0
        with_code = 0
        with_value = 0
        
        with open(ndjson_file) as f:
            for line in f:
                parsed = parse_fhir_resource(line.strip())
                parsed_count += 1
                
                assert parsed["resource_type"] == "Observation"
                assert parsed["is_valid"]
                
                # Check Observation-specific fields
                if parsed.get("code_code"):
                    with_code += 1
                if parsed.get("value_quantity_value") or parsed.get("value_string"):
                    with_value += 1
        
        print(f"    ✓ Parsed {parsed_count} observations")
        print(f"    ✓ {with_code} have code, {with_value} have value")
        
        print("\n✅ E2E Observation flow PASSED")
    
    def test_e2e_multi_resource_flow(self, ingestion_service, temp_volume):
        """
        E2E: Fetch multiple resource types → Parse all correctly
        """
        print("\n" + "="*60)
        print("E2E TEST: Multi-Resource Flow")
        print("="*60)
        
        resource_types = ["Patient", "Observation", "Encounter", "Condition"]
        
        print(f"\n[1] Fetching {len(resource_types)} resource types from HAPI...")
        result = ingestion_service.ingest_resources(
            resource_types=resource_types,
            max_per_resource=5,
        )
        
        assert result.success or len(result.errors) < len(resource_types), \
            f"Too many errors: {result.errors}"
        print(f"    ✓ Fetched {result.resources_fetched} total resources")
        print(f"    ✓ Created {len(result.files_created)} files")
        
        # Parse each file
        print("\n[2] Parsing each resource type...")
        resource_counts = {}
        
        for filepath in result.files_created:
            local_path = f"{temp_volume}/api_extracts/{os.path.basename(filepath)}"
            if not os.path.exists(local_path):
                continue
            
            with open(local_path) as f:
                for line in f:
                    parsed = parse_fhir_resource(line.strip())
                    rt = parsed.get("resource_type")
                    
                    if rt not in resource_counts:
                        resource_counts[rt] = {"total": 0, "valid": 0}
                    
                    resource_counts[rt]["total"] += 1
                    if parsed.get("is_valid"):
                        resource_counts[rt]["valid"] += 1
        
        print("\n    Resource Type Summary:")
        for rt, counts in resource_counts.items():
            status = "✓" if counts["valid"] == counts["total"] else "⚠"
            print(f"    {status} {rt}: {counts['valid']}/{counts['total']} valid")
        
        # All should be valid
        for rt, counts in resource_counts.items():
            assert counts["valid"] == counts["total"], f"{rt} has invalid records"
        
        print("\n✅ E2E Multi-Resource flow PASSED")
    
    def test_e2e_incremental_ingestion(self, temp_volume):
        """
        E2E: Test incremental ingestion with _lastUpdated filter
        """
        print("\n" + "="*60)
        print("E2E TEST: Incremental Ingestion")
        print("="*60)
        
        ingestion = FHIRIngestion(
            base_url="http://hapi.fhir.org/baseR4",
            output_volume=temp_volume,
            use_dbutils=False,
        )
        
        # Fetch only recently updated resources
        print("\n[1] Fetching resources updated after 2024-01-01...")
        result = ingestion.ingest_incremental(
            last_updated="2024-01-01T00:00:00Z",
            resource_types=["Patient"],
        )
        
        # May or may not have results, but should not error
        assert result.success or "rate" in str(result.errors).lower(), \
            f"Unexpected error: {result.errors}"
        
        print(f"    ✓ Fetched {result.resources_fetched} recently updated patients")
        print("\n✅ E2E Incremental ingestion PASSED")
    
    def test_e2e_verify_ndjson_format_for_autoloader(self, ingestion_service, temp_volume):
        """
        E2E: Verify NDJSON format is compatible with Auto Loader
        """
        print("\n" + "="*60)
        print("E2E TEST: Auto Loader Compatibility")
        print("="*60)
        
        # Fetch
        result = ingestion_service.ingest_resources(
            resource_types=["Patient"],
            max_per_resource=5,
        )
        
        if result.resources_fetched == 0:
            pytest.skip("No resources fetched")
        
        ndjson_file = f"{temp_volume}/api_extracts/{os.path.basename(result.files_created[0])}"
        
        print("\n[1] Verifying NDJSON format...")
        
        with open(ndjson_file) as f:
            content = f.read()
        
        lines = content.strip().split("\n")
        print(f"    File has {len(lines)} lines")
        
        # Each line must be valid JSON
        for i, line in enumerate(lines):
            try:
                obj = json.loads(line)
                assert isinstance(obj, dict), f"Line {i} is not a JSON object"
                assert "resourceType" in obj, f"Line {i} missing resourceType"
                assert "id" in obj, f"Line {i} missing id"
            except json.JSONDecodeError as e:
                pytest.fail(f"Line {i} is not valid JSON: {e}")
        
        print("    ✓ All lines are valid JSON objects")
        print("    ✓ All have resourceType and id (required for pipeline)")
        
        # Verify no trailing comma (common NDJSON mistake)
        assert not content.endswith(",\n"), "File ends with trailing comma"
        assert not content.endswith(","), "File ends with trailing comma"
        
        print("    ✓ No trailing commas")
        print("\n✅ E2E Auto Loader compatibility PASSED")


# =============================================================================
# Resource-Specific Validation Tests
# =============================================================================

@pytest.mark.integration
class TestResourceTypeValidation:
    """
    Validate that each resource type can be fetched and parsed correctly
    """
    
    @pytest.mark.parametrize("resource_type,expected_fields", [
        ("Patient", ["gender", "birth_date", "name_family"]),
        ("Observation", ["status", "code_code", "subject_id"]),
        ("Encounter", ["status", "class_code", "subject_id"]),
        ("Condition", ["clinical_status", "code_code", "subject_id"]),
    ])
    def test_resource_type_parsing(self, resource_type, expected_fields, temp_volume):
        """
        Fetch and parse specific resource type, validate expected fields
        """
        print(f"\nTesting {resource_type}...")
        
        ingestion = FHIRIngestion(
            base_url="http://hapi.fhir.org/baseR4",
            output_volume=temp_volume,
            use_dbutils=False,
        )
        
        result = ingestion.ingest_resources(
            resource_types=[resource_type],
            max_per_resource=3,
        )
        
        if result.resources_fetched == 0:
            pytest.skip(f"No {resource_type} resources available")
        
        # Parse and validate
        ndjson_file = f"{temp_volume}/api_extracts/{os.path.basename(result.files_created[0])}"
        
        with open(ndjson_file) as f:
            for line in f:
                parsed = parse_fhir_resource(line.strip())
                
                assert parsed["resource_type"] == resource_type
                assert parsed["is_valid"], f"Parse error: {parsed.get('parse_error')}"
                
                # Check expected fields are present (may be None but key exists)
                for field in expected_fields:
                    assert field in parsed, f"Missing field: {field}"
        
        print(f"  ✓ {resource_type}: All expected fields present")


# =============================================================================
# Run directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
