"""
Pytest fixtures and configuration for FHIR pipeline tests.

This file provides:
- Common test fixtures
- Sample FHIR resources (valid, invalid, edge cases)
- Test utility functions
- Mock configurations

Usage:
    Fixtures are automatically available in all test files.
    Access them as function parameters:
    
    def test_something(valid_patient_resource, invalid_fhir_json):
        assert valid_patient_resource["resourceType"] == "Patient"
"""

import pytest
import json
from datetime import datetime
from typing import Dict, Any, List


# =============================================================================
# Test Configuration
# =============================================================================

@pytest.fixture
def fhir_version() -> str:
    """FHIR version we support (R4)."""
    return "4.0.1"


@pytest.fixture
def supported_resource_types() -> List[str]:
    """List of FHIR resource types our pipeline should support."""
    return [
        "Patient",
        "Observation",
        "Encounter",
        "MedicationRequest",
        "DiagnosticReport",
        "Immunization",
        "Procedure",
        "Condition",
        "AllergyIntolerance",
        "Bundle",
    ]


# =============================================================================
# Valid FHIR Resources - PATIENT
# =============================================================================

@pytest.fixture
def valid_patient_minimal() -> Dict[str, Any]:
    """Minimal valid Patient resource - only required fields."""
    return {
        "resourceType": "Patient",
        "id": "patient-001"
    }


@pytest.fixture
def valid_patient_full() -> Dict[str, Any]:
    """Full Patient resource with all common fields."""
    return {
        "resourceType": "Patient",
        "id": "patient-002",
        "meta": {
            "versionId": "1",
            "lastUpdated": "2024-01-15T10:30:00Z",
            "source": "urn:ehr:hospital-a",
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"]
        },
        "identifier": [
            {
                "use": "official",
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "MR",
                        "display": "Medical Record Number"
                    }]
                },
                "system": "urn:oid:1.2.3.4.5.6.7",
                "value": "MRN123456",
                "assigner": {"display": "Hospital A"}
            },
            {
                "use": "official",
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "SS",
                        "display": "Social Security Number"
                    }]
                },
                "system": "http://hl7.org/fhir/sid/us-ssn",
                "value": "999-99-9999"
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "family": "Doe",
                "given": ["John", "William"],
                "prefix": ["Mr."],
                "suffix": ["Jr."]
            },
            {
                "use": "nickname",
                "given": ["Johnny"]
            }
        ],
        "telecom": [
            {
                "system": "phone",
                "value": "555-123-4567",
                "use": "home"
            },
            {
                "system": "email",
                "value": "john.doe@email.com",
                "use": "home"
            }
        ],
        "gender": "male",
        "birthDate": "1985-03-15",
        "deceasedBoolean": False,
        "address": [
            {
                "use": "home",
                "type": "physical",
                "line": ["123 Main Street", "Apt 4B"],
                "city": "Springfield",
                "state": "IL",
                "postalCode": "62701",
                "country": "USA"
            }
        ],
        "maritalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                "code": "M",
                "display": "Married"
            }]
        },
        "multipleBirthBoolean": False,
        "contact": [
            {
                "relationship": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0131",
                        "code": "N",
                        "display": "Next-of-Kin"
                    }]
                }],
                "name": {
                    "family": "Doe",
                    "given": ["Jane"]
                },
                "telecom": [{
                    "system": "phone",
                    "value": "555-987-6543"
                }]
            }
        ],
        "communication": [
            {
                "language": {
                    "coding": [{
                        "system": "urn:ietf:bcp:47",
                        "code": "en",
                        "display": "English"
                    }]
                },
                "preferred": True
            }
        ],
        "generalPractitioner": [
            {"reference": "Practitioner/pract-001", "display": "Dr. Smith"}
        ],
        "managingOrganization": {
            "reference": "Organization/org-001",
            "display": "Springfield General Hospital"
        }
    }


@pytest.fixture
def valid_patient_deceased() -> Dict[str, Any]:
    """Patient with deceased information using deceasedDateTime."""
    return {
        "resourceType": "Patient",
        "id": "patient-003",
        "name": [{"family": "Smith", "given": ["Alice"]}],
        "gender": "female",
        "birthDate": "1940-06-20",
        "deceasedDateTime": "2023-12-01T14:30:00Z"
    }


# =============================================================================
# Valid FHIR Resources - OBSERVATION
# =============================================================================

@pytest.fixture
def valid_observation_vital_sign() -> Dict[str, Any]:
    """Valid vital sign Observation (blood pressure)."""
    return {
        "resourceType": "Observation",
        "id": "obs-bp-001",
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-blood-pressure"]
        },
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel with all children optional"
            }],
            "text": "Blood pressure"
        },
        "subject": {"reference": "Patient/patient-002"},
        "encounter": {"reference": "Encounter/enc-001"},
        "effectiveDateTime": "2024-01-15T10:00:00Z",
        "issued": "2024-01-15T10:05:00Z",
        "performer": [{"reference": "Practitioner/pract-001"}],
        "component": [
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": 120,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            },
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8462-4",
                        "display": "Diastolic blood pressure"
                    }]
                },
                "valueQuantity": {
                    "value": 80,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                }
            }
        ]
    }


@pytest.fixture
def valid_observation_lab_result() -> Dict[str, Any]:
    """Valid lab result Observation (glucose)."""
    return {
        "resourceType": "Observation",
        "id": "obs-lab-001",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "2345-7",
                "display": "Glucose [Mass/volume] in Serum or Plasma"
            }]
        },
        "subject": {"reference": "Patient/patient-002"},
        "effectiveDateTime": "2024-01-15T08:30:00Z",
        "valueQuantity": {
            "value": 95,
            "unit": "mg/dL",
            "system": "http://unitsofmeasure.org",
            "code": "mg/dL"
        },
        "referenceRange": [{
            "low": {"value": 70, "unit": "mg/dL"},
            "high": {"value": 100, "unit": "mg/dL"},
            "text": "70-100 mg/dL"
        }],
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "N",
                "display": "Normal"
            }]
        }]
    }


@pytest.fixture
def valid_observation_abnormal() -> Dict[str, Any]:
    """Valid abnormal lab result Observation (high glucose)."""
    return {
        "resourceType": "Observation",
        "id": "obs-lab-002",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "2345-7",
                "display": "Glucose"
            }]
        },
        "subject": {"reference": "Patient/patient-002"},
        "effectiveDateTime": "2024-01-16T08:30:00Z",
        "valueQuantity": {
            "value": 180,
            "unit": "mg/dL",
            "system": "http://unitsofmeasure.org",
            "code": "mg/dL"
        },
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "H",
                "display": "High"
            }]
        }]
    }


# =============================================================================
# Valid FHIR Resources - ENCOUNTER
# =============================================================================

@pytest.fixture
def valid_encounter_inpatient() -> Dict[str, Any]:
    """Valid inpatient Encounter."""
    return {
        "resourceType": "Encounter",
        "id": "enc-001",
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "IMP",
            "display": "inpatient encounter"
        },
        "type": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "183452005",
                "display": "Emergency hospital admission"
            }]
        }],
        "priority": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActPriority",
                "code": "EM",
                "display": "emergency"
            }]
        },
        "subject": {"reference": "Patient/patient-002"},
        "participant": [{
            "type": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                    "code": "ATND",
                    "display": "attender"
                }]
            }],
            "individual": {"reference": "Practitioner/pract-001"}
        }],
        "period": {
            "start": "2024-01-15T08:00:00Z",
            "end": "2024-01-17T14:00:00Z"
        },
        "reasonCode": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "22298006",
                "display": "Myocardial infarction"
            }]
        }],
        "hospitalization": {
            "admitSource": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/admit-source",
                    "code": "emd",
                    "display": "From accident/emergency department"
                }]
            },
            "dischargeDisposition": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/discharge-disposition",
                    "code": "home",
                    "display": "Home"
                }]
            }
        },
        "location": [{
            "location": {"reference": "Location/loc-icu-001", "display": "ICU Room 101"},
            "status": "completed",
            "period": {
                "start": "2024-01-15T08:00:00Z",
                "end": "2024-01-16T12:00:00Z"
            }
        }],
        "serviceProvider": {"reference": "Organization/org-001"}
    }


@pytest.fixture
def valid_encounter_outpatient() -> Dict[str, Any]:
    """Valid outpatient/ambulatory Encounter."""
    return {
        "resourceType": "Encounter",
        "id": "enc-002",
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory"
        },
        "type": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "185349003",
                "display": "Encounter for check up"
            }]
        }],
        "subject": {"reference": "Patient/patient-002"},
        "period": {
            "start": "2024-01-20T09:00:00Z",
            "end": "2024-01-20T09:30:00Z"
        }
    }


# =============================================================================
# Valid FHIR Resources - MEDICATION REQUEST
# =============================================================================

@pytest.fixture
def valid_medication_request() -> Dict[str, Any]:
    """Valid MedicationRequest."""
    return {
        "resourceType": "MedicationRequest",
        "id": "medrx-001",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "1049221",
                "display": "acetaminophen 325 MG Oral Tablet"
            }],
            "text": "Tylenol 325mg"
        },
        "subject": {"reference": "Patient/patient-002"},
        "encounter": {"reference": "Encounter/enc-001"},
        "authoredOn": "2024-01-15T10:00:00Z",
        "requester": {"reference": "Practitioner/pract-001"},
        "dosageInstruction": [{
            "text": "Take 2 tablets by mouth every 4-6 hours as needed for pain",
            "timing": {
                "repeat": {
                    "frequency": 1,
                    "period": 4,
                    "periodUnit": "h",
                    "boundsPeriod": {"start": "2024-01-15", "end": "2024-01-22"}
                }
            },
            "route": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "26643006",
                    "display": "Oral route"
                }]
            },
            "doseAndRate": [{
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/dose-rate-type",
                        "code": "ordered"
                    }]
                },
                "doseQuantity": {
                    "value": 650,
                    "unit": "mg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mg"
                }
            }]
        }]
    }


# =============================================================================
# Valid FHIR Resources - DIAGNOSTIC REPORT
# =============================================================================

@pytest.fixture
def valid_diagnostic_report() -> Dict[str, Any]:
    """Valid DiagnosticReport with lab results."""
    return {
        "resourceType": "DiagnosticReport",
        "id": "diag-001",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                "code": "LAB",
                "display": "Laboratory"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "24323-8",
                "display": "Comprehensive metabolic 2000 panel"
            }]
        },
        "subject": {"reference": "Patient/patient-002"},
        "encounter": {"reference": "Encounter/enc-001"},
        "effectiveDateTime": "2024-01-15T08:00:00Z",
        "issued": "2024-01-15T12:00:00Z",
        "performer": [{"reference": "Organization/lab-001", "display": "Hospital Lab"}],
        "result": [
            {"reference": "Observation/obs-lab-001"},
            {"reference": "Observation/obs-lab-002"}
        ],
        "conclusion": "All results within normal limits"
    }


# =============================================================================
# Valid FHIR Resources - IMMUNIZATION
# =============================================================================

@pytest.fixture
def valid_immunization() -> Dict[str, Any]:
    """Valid Immunization record."""
    return {
        "resourceType": "Immunization",
        "id": "imm-001",
        "status": "completed",
        "vaccineCode": {
            "coding": [{
                "system": "http://hl7.org/fhir/sid/cvx",
                "code": "208",
                "display": "COVID-19, mRNA, LNP-S, PF, 30 mcg/0.3 mL dose"
            }],
            "text": "Pfizer COVID-19 Vaccine"
        },
        "patient": {"reference": "Patient/patient-002"},
        "encounter": {"reference": "Encounter/enc-002"},
        "occurrenceDateTime": "2024-01-20T09:15:00Z",
        "primarySource": True,
        "location": {"reference": "Location/loc-clinic-001"},
        "manufacturer": {"display": "Pfizer-BioNTech"},
        "lotNumber": "EW0171",
        "expirationDate": "2024-06-30",
        "site": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActSite",
                "code": "LA",
                "display": "Left arm"
            }]
        },
        "route": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-RouteOfAdministration",
                "code": "IM",
                "display": "Intramuscular"
            }]
        },
        "doseQuantity": {
            "value": 0.3,
            "unit": "mL",
            "system": "http://unitsofmeasure.org",
            "code": "mL"
        },
        "performer": [{
            "function": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0443",
                    "code": "AP",
                    "display": "Administering Provider"
                }]
            },
            "actor": {"reference": "Practitioner/pract-001"}
        }],
        "protocolApplied": [{
            "series": "COVID-19 2-Dose Series",
            "doseNumberPositiveInt": 1
        }]
    }


# =============================================================================
# Valid FHIR Resources - CONDITION
# =============================================================================

@pytest.fixture
def valid_condition() -> Dict[str, Any]:
    """Valid Condition (diagnosis)."""
    return {
        "resourceType": "Condition",
        "id": "cond-001",
        "clinicalStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": "active"
            }]
        },
        "verificationStatus": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "code": "confirmed"
            }]
        },
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "problem-list-item",
                "display": "Problem List Item"
            }]
        }],
        "severity": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "24484000",
                "display": "Severe"
            }]
        },
        "code": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "44054006",
                "display": "Type 2 diabetes mellitus"
            }],
            "text": "Type 2 Diabetes"
        },
        "bodySite": [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "38266002",
                "display": "Entire body as a whole"
            }]
        }],
        "subject": {"reference": "Patient/patient-002"},
        "encounter": {"reference": "Encounter/enc-001"},
        "onsetDateTime": "2020-05-15",
        "recordedDate": "2020-05-15",
        "recorder": {"reference": "Practitioner/pract-001"},
        "asserter": {"reference": "Practitioner/pract-001"}
    }


# =============================================================================
# Valid FHIR Resources - BUNDLE
# =============================================================================

@pytest.fixture
def valid_bundle_transaction(valid_patient_full, valid_observation_lab_result) -> Dict[str, Any]:
    """Valid transaction Bundle with multiple resources."""
    return {
        "resourceType": "Bundle",
        "id": "bundle-001",
        "type": "transaction",
        "timestamp": "2024-01-15T10:00:00Z",
        "entry": [
            {
                "fullUrl": "urn:uuid:patient-002",
                "resource": valid_patient_full,
                "request": {
                    "method": "PUT",
                    "url": "Patient/patient-002"
                }
            },
            {
                "fullUrl": "urn:uuid:obs-lab-001",
                "resource": valid_observation_lab_result,
                "request": {
                    "method": "POST",
                    "url": "Observation"
                }
            }
        ]
    }


@pytest.fixture
def valid_bundle_collection(valid_patient_minimal, valid_encounter_outpatient) -> Dict[str, Any]:
    """Valid collection Bundle."""
    return {
        "resourceType": "Bundle",
        "id": "bundle-002",
        "type": "collection",
        "timestamp": "2024-01-20T12:00:00Z",
        "entry": [
            {"resource": valid_patient_minimal},
            {"resource": valid_encounter_outpatient}
        ]
    }


# =============================================================================
# INVALID FHIR Resources - For testing error handling
# =============================================================================

@pytest.fixture
def invalid_missing_resource_type() -> Dict[str, Any]:
    """Invalid: Missing resourceType field."""
    return {
        "id": "bad-001",
        "name": [{"family": "Test"}]
    }


@pytest.fixture
def invalid_wrong_resource_type() -> Dict[str, Any]:
    """Invalid: Unknown resourceType."""
    return {
        "resourceType": "NotARealResource",
        "id": "bad-002"
    }


@pytest.fixture
def invalid_observation_missing_status() -> Dict[str, Any]:
    """Invalid: Observation missing required 'status' field."""
    return {
        "resourceType": "Observation",
        "id": "bad-obs-001",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2345-7"}]
        },
        "subject": {"reference": "Patient/patient-002"}
        # Missing required "status" field
    }


@pytest.fixture
def invalid_observation_wrong_status() -> Dict[str, Any]:
    """Invalid: Observation with invalid status value."""
    return {
        "resourceType": "Observation",
        "id": "bad-obs-002",
        "status": "not-a-valid-status",  # Invalid enum value
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2345-7"}]
        },
        "subject": {"reference": "Patient/patient-002"}
    }


@pytest.fixture
def invalid_patient_wrong_gender() -> Dict[str, Any]:
    """Invalid: Patient with invalid gender value."""
    return {
        "resourceType": "Patient",
        "id": "bad-patient-001",
        "gender": "invalid-gender"  # Should be male/female/other/unknown
    }


@pytest.fixture
def invalid_encounter_missing_class() -> Dict[str, Any]:
    """Invalid: Encounter missing required 'class' field."""
    return {
        "resourceType": "Encounter",
        "id": "bad-enc-001",
        "status": "finished",
        # Missing required "class" field
        "subject": {"reference": "Patient/patient-002"}
    }


@pytest.fixture
def invalid_medication_request_missing_intent() -> Dict[str, Any]:
    """Invalid: MedicationRequest missing required fields."""
    return {
        "resourceType": "MedicationRequest",
        "id": "bad-medrx-001",
        "status": "active",
        # Missing required "intent" field
        "medicationCodeableConcept": {"text": "Aspirin"},
        "subject": {"reference": "Patient/patient-002"}
    }


@pytest.fixture
def invalid_json_malformed() -> str:
    """Malformed JSON string (not parseable)."""
    return '{"resourceType": "Patient", "id": "bad-json-001", "name": [}'


@pytest.fixture
def invalid_empty_object() -> Dict[str, Any]:
    """Empty JSON object."""
    return {}


@pytest.fixture
def invalid_null_values() -> Dict[str, Any]:
    """Resource with null where not allowed."""
    return {
        "resourceType": "Patient",
        "id": None,  # ID should be string, not null
        "name": None  # Name should be array or omitted
    }


# =============================================================================
# EDGE CASES - Unusual but valid or problematic resources
# =============================================================================

@pytest.fixture
def edge_case_unicode_in_names() -> Dict[str, Any]:
    """Patient with unicode characters in names."""
    return {
        "resourceType": "Patient",
        "id": "unicode-001",
        "name": [{
            "family": "Müller",
            "given": ["José", "María"]
        }],
        "address": [{
            "city": "北京",
            "country": "中国"
        }]
    }


@pytest.fixture
def edge_case_very_long_text() -> Dict[str, Any]:
    """Resource with very long text fields."""
    return {
        "resourceType": "Observation",
        "id": "long-text-001",
        "status": "final",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "47420-5"}],
            "text": "Clinical notes " + "x" * 10000  # Very long text
        },
        "subject": {"reference": "Patient/patient-002"},
        "note": [{"text": "A" * 50000}]  # Very long note
    }


@pytest.fixture
def edge_case_many_identifiers() -> Dict[str, Any]:
    """Patient with many identifiers (100+)."""
    identifiers = []
    for i in range(150):
        identifiers.append({
            "system": f"urn:system:{i}",
            "value": f"ID-{i:05d}"
        })
    return {
        "resourceType": "Patient",
        "id": "many-ids-001",
        "identifier": identifiers,
        "name": [{"family": "Test"}]
    }


@pytest.fixture
def edge_case_deeply_nested() -> Dict[str, Any]:
    """Resource with deeply nested extensions."""
    return {
        "resourceType": "Patient",
        "id": "nested-001",
        "extension": [{
            "url": "http://example.org/level1",
            "extension": [{
                "url": "level2",
                "extension": [{
                    "url": "level3",
                    "extension": [{
                        "url": "level4",
                        "valueString": "deeply nested value"
                    }]
                }]
            }]
        }]
    }


@pytest.fixture
def edge_case_old_dates() -> Dict[str, Any]:
    """Patient with very old dates."""
    return {
        "resourceType": "Patient",
        "id": "old-dates-001",
        "birthDate": "1900-01-01",
        "deceasedDateTime": "1999-12-31T23:59:59Z"
    }


@pytest.fixture
def edge_case_future_dates() -> Dict[str, Any]:
    """Encounter with future dates (scheduled)."""
    return {
        "resourceType": "Encounter",
        "id": "future-001",
        "status": "planned",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB"
        },
        "subject": {"reference": "Patient/patient-002"},
        "period": {
            "start": "2030-06-15T09:00:00Z",
            "end": "2030-06-15T10:00:00Z"
        }
    }


@pytest.fixture
def edge_case_empty_arrays() -> Dict[str, Any]:
    """Patient with empty arrays (should be omitted but might exist)."""
    return {
        "resourceType": "Patient",
        "id": "empty-arrays-001",
        "identifier": [],
        "name": [],
        "telecom": [],
        "address": []
    }


# =============================================================================
# BULK TEST DATA - For integration testing
# =============================================================================

@pytest.fixture
def bulk_patients_100(valid_patient_full) -> List[Dict[str, Any]]:
    """Generate 100 patient resources for bulk testing."""
    patients = []
    first_names = ["John", "Jane", "Robert", "Maria", "James", "Patricia", "Michael", "Jennifer", "William", "Linda"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    
    for i in range(100):
        patient = {
            "resourceType": "Patient",
            "id": f"bulk-patient-{i:04d}",
            "identifier": [{
                "system": "urn:mrn",
                "value": f"MRN{i:06d}"
            }],
            "name": [{
                "family": last_names[i % 10],
                "given": [first_names[i % 10]]
            }],
            "gender": "male" if i % 2 == 0 else "female",
            "birthDate": f"{1950 + (i % 50)}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
        }
        patients.append(patient)
    return patients


@pytest.fixture
def bulk_mixed_resources(valid_patient_minimal, valid_observation_lab_result, valid_encounter_outpatient) -> List[Dict[str, Any]]:
    """Mixed resource types for integration testing."""
    resources = []
    
    # Add 20 patients
    for i in range(20):
        resources.append({
            "resourceType": "Patient",
            "id": f"mixed-patient-{i:03d}"
        })
    
    # Add 30 observations
    for i in range(30):
        resources.append({
            "resourceType": "Observation",
            "id": f"mixed-obs-{i:03d}",
            "status": "final",
            "code": {"text": f"Test {i}"},
            "subject": {"reference": f"Patient/mixed-patient-{i % 20:03d}"}
        })
    
    # Add 10 encounters
    for i in range(10):
        resources.append({
            "resourceType": "Encounter",
            "id": f"mixed-enc-{i:03d}",
            "status": "finished",
            "class": {"code": "AMB"},
            "subject": {"reference": f"Patient/mixed-patient-{i % 20:03d}"}
        })
    
    return resources


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

@pytest.fixture
def json_serializer():
    """Returns a function to safely serialize FHIR resources."""
    def serialize(resource: Dict[str, Any]) -> str:
        return json.dumps(resource, indent=2, ensure_ascii=False)
    return serialize


@pytest.fixture
def resource_validator():
    """Returns a basic validator function."""
    def validate(resource: Dict[str, Any]) -> List[str]:
        """Basic validation - returns list of errors."""
        errors = []
        if not resource:
            errors.append("Resource is empty")
            return errors
        if "resourceType" not in resource:
            errors.append("Missing resourceType")
        if "id" not in resource:
            errors.append("Missing id (warning)")
        return errors
    return validate
