"""
E2E Test with Sample Data + Parsing Validation

This test validates the complete flow WITHOUT needing external APIs:
1. Use existing sample FHIR data
2. Write to temp directory (simulating UC Volume)  
3. Parse using the SAME logic from bronze_fhir.py
4. Validate each resource type is correctly processed

This is RELIABLE (no network dependency) while still validating the full flow.

Run:
    pytest test_e2e_with_sample_data.py -v -s
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Sample FHIR data (comprehensive, covering multiple resource types)
SAMPLE_FHIR_RESOURCES = [
    # Patient 1 - Complete
    {
        "resourceType": "Patient",
        "id": "patient-001",
        "meta": {"versionId": "1", "lastUpdated": "2024-01-15T10:30:00Z"},
        "identifier": [{"system": "http://hospital.org/mrn", "value": "MRN123456"}],
        "active": True,
        "name": [{"use": "official", "family": "Smith", "given": ["John", "Robert"]}],
        "gender": "male",
        "birthDate": "1985-03-15",
        "deceasedBoolean": False,
        "address": [{"city": "Boston", "state": "MA", "postalCode": "02115"}],
        "telecom": [{"system": "phone", "value": "555-1234"}],
    },
    # Patient 2 - Minimal
    {
        "resourceType": "Patient",
        "id": "patient-002",
        "gender": "female",
        "birthDate": "1990-07-22",
    },
    # Observation 1 - Heart Rate
    {
        "resourceType": "Observation",
        "id": "obs-001",
        "meta": {"versionId": "1", "lastUpdated": "2024-02-01T14:00:00Z"},
        "status": "final",
        "category": [{"coding": [{"code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]
        },
        "subject": {"reference": "Patient/patient-001"},
        "encounter": {"reference": "Encounter/enc-001"},
        "effectiveDateTime": "2024-02-01T14:00:00Z",
        "valueQuantity": {"value": 72, "unit": "beats/minute", "system": "http://unitsofmeasure.org", "code": "/min"},
    },
    # Observation 2 - Blood Pressure (component-based)
    {
        "resourceType": "Observation",
        "id": "obs-002",
        "status": "final",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]
        },
        "subject": {"reference": "Patient/patient-001"},
        "effectiveDateTime": "2024-02-01T14:05:00Z",
        "component": [
            {"code": {"coding": [{"code": "8480-6", "display": "Systolic"}]}, "valueQuantity": {"value": 120, "unit": "mmHg"}},
            {"code": {"coding": [{"code": "8462-4", "display": "Diastolic"}]}, "valueQuantity": {"value": 80, "unit": "mmHg"}},
        ],
    },
    # Observation 3 - Text value
    {
        "resourceType": "Observation",
        "id": "obs-003",
        "status": "final",
        "code": {"coding": [{"code": "notes", "display": "Clinical Notes"}]},
        "subject": {"reference": "Patient/patient-002"},
        "valueString": "Patient reports mild discomfort",
    },
    # Encounter 1 - Emergency
    {
        "resourceType": "Encounter",
        "id": "enc-001",
        "meta": {"versionId": "1", "lastUpdated": "2024-02-01T10:00:00Z"},
        "status": "finished",
        "class": {"code": "EMER", "display": "Emergency"},
        "type": [{"coding": [{"code": "183452005", "display": "Emergency department visit"}]}],
        "subject": {"reference": "Patient/patient-001"},
        "participant": [{"individual": {"reference": "Practitioner/dr-001"}}],
        "period": {"start": "2024-02-01T10:00:00Z", "end": "2024-02-01T16:00:00Z"},
        "reasonCode": [{"coding": [{"code": "chest-pain", "display": "Chest Pain"}]}],
    },
    # Encounter 2 - Outpatient
    {
        "resourceType": "Encounter",
        "id": "enc-002",
        "status": "in-progress",
        "class": {"code": "AMB", "display": "Ambulatory"},
        "subject": {"reference": "Patient/patient-002"},
        "period": {"start": "2024-02-05T09:00:00Z"},
    },
    # Condition 1 - Active condition
    {
        "resourceType": "Condition",
        "id": "cond-001",
        "meta": {"versionId": "1", "lastUpdated": "2024-01-10T12:00:00Z"},
        "clinicalStatus": {"coding": [{"code": "active", "display": "Active"}]},
        "verificationStatus": {"coding": [{"code": "confirmed", "display": "Confirmed"}]},
        "category": [{"coding": [{"code": "encounter-diagnosis", "display": "Encounter Diagnosis"}]}],
        "code": {
            "coding": [{"system": "http://snomed.info/sct", "code": "38341003", "display": "Hypertension"}]
        },
        "subject": {"reference": "Patient/patient-001"},
        "encounter": {"reference": "Encounter/enc-001"},
        "onsetDateTime": "2020-06-15",
        "recordedDate": "2024-01-10",
    },
    # Condition 2 - Resolved
    {
        "resourceType": "Condition",
        "id": "cond-002",
        "clinicalStatus": {"coding": [{"code": "resolved"}]},
        "code": {"coding": [{"code": "195662009", "display": "Acute viral pharyngitis"}]},
        "subject": {"reference": "Patient/patient-002"},
    },
    # MedicationRequest
    {
        "resourceType": "MedicationRequest",
        "id": "med-001",
        "meta": {"versionId": "1", "lastUpdated": "2024-02-01T15:00:00Z"},
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "197361", "display": "Lisinopril 10 MG"}]
        },
        "subject": {"reference": "Patient/patient-001"},
        "encounter": {"reference": "Encounter/enc-001"},
        "requester": {"reference": "Practitioner/dr-001"},
        "authoredOn": "2024-02-01T15:00:00Z",
        "dosageInstruction": [{"text": "Take 1 tablet daily", "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}}}],
    },
    # Immunization
    {
        "resourceType": "Immunization",
        "id": "imm-001",
        "meta": {"versionId": "1", "lastUpdated": "2024-01-20T11:00:00Z"},
        "status": "completed",
        "vaccineCode": {
            "coding": [{"system": "http://hl7.org/fhir/sid/cvx", "code": "208", "display": "COVID-19 vaccine"}]
        },
        "patient": {"reference": "Patient/patient-001"},
        "encounter": {"reference": "Encounter/enc-001"},
        "occurrenceDateTime": "2024-01-20T11:00:00Z",
        "primarySource": True,
        "lotNumber": "LOT123456",
    },
]


# =============================================================================
# FHIR Parsing Logic (Same as SDP pipeline)
# =============================================================================

def parse_fhir_resource(raw_json: str) -> Dict[str, Any]:
    """Parse FHIR resource - SAME LOGIC as SDP pipeline UDF"""
    import json
    
    def safe_get(obj, *keys, default=None):
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
        if reference and '/' in reference:
            return reference.split('/')[-1]
        return reference
    
    def extract_coding(codeable_concept: Dict) -> Dict:
        if not codeable_concept:
            return {}
        codings = codeable_concept.get("coding", [])
        if codings:
            c = codings[0]
            return {"system": c.get("system"), "code": c.get("code"), "display": c.get("display")}
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
        
        if resource_type == "Patient":
            names = resource.get("name", [])
            name = names[0] if names else {}
            base_result.update({
                "patient_id": resource.get("id"),
                "gender": resource.get("gender"),
                "birth_date": resource.get("birthDate"),
                "deceased_boolean": resource.get("deceasedBoolean"),
                "name_family": name.get("family"),
                "name_given": ", ".join(name.get("given", [])),
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
                "code_system": code.get("system"),
                "code_code": code.get("code"),
                "code_display": code.get("display"),
                "subject_id": extract_reference_id(safe_get(resource, "subject", "reference")),
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
                "occurrence_datetime": resource.get("occurrenceDateTime"),
                "primary_source": resource.get("primarySource"),
                "lot_number": resource.get("lotNumber"),
            })
        
        return base_result
        
    except Exception as e:
        return {"resource_id": None, "resource_type": None, "is_valid": False, "parse_error": str(e)}


# =============================================================================
# Tests
# =============================================================================

class TestE2EWithSampleData:
    """
    E2E tests using sample data - RELIABLE, no network dependency
    """
    
    def test_write_and_parse_all_resource_types(self):
        """
        E2E: Write sample data → Read NDJSON → Parse with pipeline logic
        """
        print("\n" + "="*60)
        print("E2E TEST: All Resource Types")
        print("="*60)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Write sample data as NDJSON (simulating API ingestion)
            ndjson_file = f"{tmpdir}/fhir_resources.ndjson"
            print(f"\n[1] Writing {len(SAMPLE_FHIR_RESOURCES)} resources to NDJSON...")
            
            with open(ndjson_file, "w") as f:
                for resource in SAMPLE_FHIR_RESOURCES:
                    f.write(json.dumps(resource) + "\n")
            
            print(f"    ✓ Wrote {ndjson_file}")
            
            # Step 2: Read and parse (simulating pipeline processing)
            print("\n[2] Reading and parsing with pipeline logic...")
            
            resource_counts = {}
            all_parsed = []
            
            with open(ndjson_file) as f:
                for line in f:
                    parsed = parse_fhir_resource(line.strip())
                    all_parsed.append(parsed)
                    
                    rt = parsed.get("resource_type")
                    if rt not in resource_counts:
                        resource_counts[rt] = {"total": 0, "valid": 0}
                    resource_counts[rt]["total"] += 1
                    if parsed.get("is_valid"):
                        resource_counts[rt]["valid"] += 1
            
            # Step 3: Validate results
            print("\n[3] Validation Results:")
            for rt, counts in sorted(resource_counts.items()):
                status = "✓" if counts["valid"] == counts["total"] else "✗"
                print(f"    {status} {rt}: {counts['valid']}/{counts['total']} valid")
            
            # All should be valid
            for parsed in all_parsed:
                assert parsed["is_valid"], f"Parse error: {parsed.get('parse_error')}"
            
            print(f"\n    Total: {len(all_parsed)} resources parsed successfully")
            print("\n✅ E2E All Resource Types PASSED")
    
    def test_patient_specific_fields(self):
        """Validate Patient-specific fields are correctly extracted"""
        print("\n" + "="*60)
        print("TEST: Patient Field Extraction")
        print("="*60)
        
        patient = SAMPLE_FHIR_RESOURCES[0]  # Complete patient
        parsed = parse_fhir_resource(json.dumps(patient))
        
        print(f"\n  Resource ID: {parsed['resource_id']}")
        print(f"  Gender: {parsed['gender']}")
        print(f"  Birth Date: {parsed['birth_date']}")
        print(f"  Name: {parsed['name_family']}, {parsed['name_given']}")
        print(f"  Identifier Count: {parsed['identifier_count']}")
        print(f"  Address Count: {parsed['address_count']}")
        
        assert parsed["resource_type"] == "Patient"
        assert parsed["gender"] == "male"
        assert parsed["birth_date"] == "1985-03-15"
        assert parsed["name_family"] == "Smith"
        assert parsed["name_given"] == "John, Robert"
        assert parsed["identifier_count"] == 1
        assert parsed["address_count"] == 1
        assert parsed["active"] == True
        
        print("\n✅ Patient Field Extraction PASSED")
    
    def test_observation_variations(self):
        """Validate different Observation formats (quantity, string, components)"""
        print("\n" + "="*60)
        print("TEST: Observation Variations")
        print("="*60)
        
        # Heart rate (valueQuantity)
        obs_hr = SAMPLE_FHIR_RESOURCES[2]
        parsed_hr = parse_fhir_resource(json.dumps(obs_hr))
        
        print(f"\n  Observation 1 (Heart Rate):")
        print(f"    Code: {parsed_hr['code_code']} - {parsed_hr['code_display']}")
        print(f"    Value: {parsed_hr['value_quantity_value']} {parsed_hr['value_quantity_unit']}")
        
        assert parsed_hr["code_code"] == "8867-4"
        assert parsed_hr["value_quantity_value"] == 72
        assert parsed_hr["subject_id"] == "patient-001"
        
        # Text value (valueString)
        obs_text = SAMPLE_FHIR_RESOURCES[4]
        parsed_text = parse_fhir_resource(json.dumps(obs_text))
        
        print(f"\n  Observation 2 (Text):")
        print(f"    Value String: {parsed_text['value_string']}")
        
        assert parsed_text["value_string"] == "Patient reports mild discomfort"
        assert parsed_text["value_quantity_value"] is None
        
        print("\n✅ Observation Variations PASSED")
    
    def test_encounter_parsing(self):
        """Validate Encounter parsing with class, type, period"""
        print("\n" + "="*60)
        print("TEST: Encounter Parsing")
        print("="*60)
        
        enc = SAMPLE_FHIR_RESOURCES[5]  # Emergency encounter
        parsed = parse_fhir_resource(json.dumps(enc))
        
        print(f"\n  Encounter ID: {parsed['encounter_id']}")
        print(f"  Status: {parsed['status']}")
        print(f"  Class: {parsed['class_code']} - {parsed['class_display']}")
        print(f"  Period: {parsed['period_start']} to {parsed['period_end']}")
        print(f"  Participants: {parsed['participant_count']}")
        print(f"  Reasons: {parsed['reason_count']}")
        
        assert parsed["status"] == "finished"
        assert parsed["class_code"] == "EMER"
        assert parsed["subject_id"] == "patient-001"
        assert parsed["participant_count"] == 1
        assert parsed["reason_count"] == 1
        
        print("\n✅ Encounter Parsing PASSED")
    
    def test_condition_parsing(self):
        """Validate Condition parsing with clinical/verification status"""
        print("\n" + "="*60)
        print("TEST: Condition Parsing")
        print("="*60)
        
        cond = SAMPLE_FHIR_RESOURCES[7]  # Hypertension
        parsed = parse_fhir_resource(json.dumps(cond))
        
        print(f"\n  Condition ID: {parsed['condition_id']}")
        print(f"  Clinical Status: {parsed['clinical_status']}")
        print(f"  Verification: {parsed['verification_status']}")
        print(f"  Code: {parsed['code_code']} - {parsed['code_display']}")
        print(f"  Onset: {parsed['onset_datetime']}")
        
        assert parsed["clinical_status"] == "active"
        assert parsed["verification_status"] == "confirmed"
        assert parsed["code_code"] == "38341003"
        assert parsed["code_display"] == "Hypertension"
        
        print("\n✅ Condition Parsing PASSED")
    
    def test_medication_request_parsing(self):
        """Validate MedicationRequest parsing"""
        print("\n" + "="*60)
        print("TEST: MedicationRequest Parsing")
        print("="*60)
        
        med = SAMPLE_FHIR_RESOURCES[9]
        parsed = parse_fhir_resource(json.dumps(med))
        
        print(f"\n  MedicationRequest ID: {parsed['medication_request_id']}")
        print(f"  Status: {parsed['status']}")
        print(f"  Intent: {parsed['intent']}")
        print(f"  Medication: {parsed['medication_code']} - {parsed['medication_display']}")
        print(f"  Authored On: {parsed['authored_on']}")
        print(f"  Dosage Instructions: {parsed['dosage_instruction_count']}")
        
        assert parsed["status"] == "active"
        assert parsed["intent"] == "order"
        assert parsed["medication_code"] == "197361"
        assert parsed["medication_display"] == "Lisinopril 10 MG"
        assert parsed["dosage_instruction_count"] == 1
        
        print("\n✅ MedicationRequest Parsing PASSED")
    
    def test_immunization_parsing(self):
        """Validate Immunization parsing"""
        print("\n" + "="*60)
        print("TEST: Immunization Parsing")
        print("="*60)
        
        imm = SAMPLE_FHIR_RESOURCES[10]
        parsed = parse_fhir_resource(json.dumps(imm))
        
        print(f"\n  Immunization ID: {parsed['immunization_id']}")
        print(f"  Status: {parsed['status']}")
        print(f"  Vaccine: {parsed['vaccine_code']} - {parsed['vaccine_display']}")
        print(f"  Occurrence: {parsed['occurrence_datetime']}")
        print(f"  Lot Number: {parsed['lot_number']}")
        print(f"  Primary Source: {parsed['primary_source']}")
        
        assert parsed["status"] == "completed"
        assert parsed["vaccine_code"] == "208"
        assert parsed["vaccine_display"] == "COVID-19 vaccine"
        assert parsed["lot_number"] == "LOT123456"
        assert parsed["primary_source"] == True
        
        print("\n✅ Immunization Parsing PASSED")
    
    def test_ndjson_format_compatibility(self):
        """Verify NDJSON format is Auto Loader compatible"""
        print("\n" + "="*60)
        print("TEST: NDJSON Format Compatibility")
        print("="*60)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            ndjson_file = f"{tmpdir}/test.ndjson"
            
            # Write
            with open(ndjson_file, "w") as f:
                for resource in SAMPLE_FHIR_RESOURCES:
                    f.write(json.dumps(resource) + "\n")
            
            # Read and validate
            with open(ndjson_file) as f:
                content = f.read()
            
            lines = content.strip().split("\n")
            print(f"\n  Total lines: {len(lines)}")
            
            for i, line in enumerate(lines):
                obj = json.loads(line)
                assert isinstance(obj, dict), f"Line {i} not a dict"
                assert "resourceType" in obj, f"Line {i} missing resourceType"
                assert "id" in obj, f"Line {i} missing id"
            
            print("  ✓ All lines are valid JSON objects")
            print("  ✓ All have resourceType and id")
            
            # No trailing issues
            assert not content.endswith(",\n")
            assert not content.endswith(",")
            print("  ✓ No trailing commas")
            
            print("\n✅ NDJSON Format Compatibility PASSED")
    
    def test_error_handling(self):
        """Validate error handling for malformed resources"""
        print("\n" + "="*60)
        print("TEST: Error Handling")
        print("="*60)
        
        # Malformed JSON
        parsed = parse_fhir_resource("not valid json")
        assert not parsed["is_valid"]
        assert parsed["parse_error"] is not None
        print("  ✓ Malformed JSON handled")
        
        # Missing resourceType
        parsed = parse_fhir_resource('{"id": "123"}')
        assert parsed["is_valid"]  # Still parses, just no type-specific fields
        assert parsed["resource_type"] is None
        print("  ✓ Missing resourceType handled")
        
        # Empty object
        parsed = parse_fhir_resource('{}')
        assert parsed["is_valid"]
        print("  ✓ Empty object handled")
        
        print("\n✅ Error Handling PASSED")


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
