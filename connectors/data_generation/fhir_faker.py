# Databricks notebook source
# MAGIC %md
# MAGIC # FHIR R4 Test Data Generator
# MAGIC 
# MAGIC Comprehensive test data generation for FHIR R4 ingestion pipeline validation.
# MAGIC 
# MAGIC **Coverage:**
# MAGIC - All supported resource types (Patient, Observation, Encounter, Condition, MedicationRequest, Immunization)
# MAGIC - Positive boundary cases (valid data, edge cases)
# MAGIC - Negative boundary cases (invalid data, missing fields, corrupt files)
# MAGIC - Nested directory structures
# MAGIC - Mixed resource files (multiple types in single file)
# MAGIC - Bundle resources
# MAGIC - Schema evolution scenarios

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import json
import random
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
import time

# Configuration
CATALOG = "main"
SCHEMA = "healthcare"
VOLUME = "raw_data"
FHIR_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/fhir"

# Generation settings
NUM_PATIENTS = 25
NUM_OBSERVATIONS_PER_PATIENT = 4
NUM_ENCOUNTERS_PER_PATIENT = 2
NUM_CONDITIONS_PER_PATIENT = 2
NUM_MEDICATIONS_PER_PATIENT = 2
NUM_IMMUNIZATIONS_PER_PATIENT = 2

# Unique run identifier - ensures each run generates unique data
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_HASH = hashlib.md5(f"{RUN_ID}_{time.time_ns()}".encode()).hexdigest()[:8]

# Use time-based seed for randomness (different each run)
# Set USE_FIXED_SEED=True for reproducible test runs
USE_FIXED_SEED = False
FIXED_SEED = 42

print(f"=" * 60)
print(f"FHIR Test Data Generator")
print(f"=" * 60)
print(f"Run ID: {RUN_ID}")
print(f"Run Hash: {RUN_HASH}")
print(f"Target path: {FHIR_PATH}")
print(f"Randomness: {'Fixed (reproducible)' if USE_FIXED_SEED else 'Dynamic (unique each run)'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## FHIR Resource Generators

# COMMAND ----------

class FHIRFaker:
    """Comprehensive FHIR R4 test data generator with boundary testing."""
    
    # Reference data
    GENDERS = ["male", "female", "other", "unknown"]
    OBSERVATION_CATEGORIES = ["vital-signs", "laboratory", "imaging", "procedure", "survey", "exam"]
    ENCOUNTER_CLASSES = ["AMB", "EMER", "IMP", "OBSENC", "PRENC", "SS", "VR", "HH"]
    ENCOUNTER_STATUSES = ["planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled"]
    CONDITION_CLINICAL_STATUSES = ["active", "recurrence", "relapse", "inactive", "remission", "resolved"]
    CONDITION_VERIFICATION_STATUSES = ["unconfirmed", "provisional", "differential", "confirmed", "refuted", "entered-in-error"]
    MEDICATION_STATUSES = ["active", "on-hold", "cancelled", "completed", "entered-in-error", "stopped", "draft", "unknown"]
    IMMUNIZATION_STATUSES = ["completed", "entered-in-error", "not-done"]
    
    # LOINC codes for observations
    LOINC_CODES = [
        ("8867-4", "Heart rate", "vital-signs", "/min", 40, 200),
        ("8310-5", "Body temperature", "vital-signs", "[degF]", 95.0, 106.0),
        ("8480-6", "Systolic blood pressure", "vital-signs", "mm[Hg]", 70, 250),
        ("8462-4", "Diastolic blood pressure", "vital-signs", "mm[Hg]", 40, 150),
        ("29463-7", "Body weight", "vital-signs", "kg", 1, 300),
        ("8302-2", "Body height", "vital-signs", "cm", 30, 250),
        ("2339-0", "Glucose [Mass/volume] in Blood", "laboratory", "mg/dL", 20, 600),
        ("2160-0", "Creatinine [Mass/volume] in Serum", "laboratory", "mg/dL", 0.1, 15.0),
        ("718-7", "Hemoglobin [Mass/volume] in Blood", "laboratory", "g/dL", 4.0, 20.0),
        ("777-3", "Platelet count", "laboratory", "/uL", 50000, 800000),
    ]
    
    # SNOMED codes for conditions
    SNOMED_CONDITIONS = [
        ("38341003", "Hypertensive disorder"),
        ("73211009", "Diabetes mellitus"),
        ("195967001", "Asthma"),
        ("13645005", "Chronic obstructive pulmonary disease"),
        ("22298006", "Myocardial infarction"),
        ("84114007", "Heart failure"),
        ("40930008", "Hypothyroidism"),
        ("68566005", "Urinary tract infection"),
        ("386661006", "Fever"),
        ("49727002", "Cough"),
    ]
    
    # RxNorm codes for medications
    RXNORM_MEDICATIONS = [
        ("197361", "Lisinopril 10 MG Oral Tablet"),
        ("860975", "Metformin hydrochloride 500 MG Oral Tablet"),
        ("312961", "Atorvastatin 20 MG Oral Tablet"),
        ("197380", "Levothyroxine Sodium 0.05 MG Oral Tablet"),
        ("199026", "Amlodipine 5 MG Oral Tablet"),
        ("311995", "Omeprazole 20 MG Delayed Release Oral Capsule"),
        ("197319", "Hydrochlorothiazide 25 MG Oral Tablet"),
        ("310798", "Gabapentin 300 MG Oral Capsule"),
        ("313782", "Acetaminophen 325 MG Oral Tablet"),
        ("197591", "Ibuprofen 200 MG Oral Tablet"),
    ]
    
    # CVX codes for vaccines
    CVX_VACCINES = [
        ("208", "COVID-19, mRNA, LNP-S, PF, 30 mcg/0.3 mL dose"),
        ("140", "Influenza, seasonal, injectable, preservative free"),
        ("33", "pneumococcal polysaccharide PPV23"),
        ("113", "Td (adult) preservative free"),
        ("121", "zoster, live"),
        ("52", "Hep A, adult"),
        ("43", "Hep B, adult"),
        ("62", "HPV, quadrivalent"),
    ]
    
    FIRST_NAMES_MALE = [
        "James", "John", "Robert", "Michael", "William", "David", "Joseph", "Thomas", "Charles", "Daniel",
        "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin",
        "Brian", "George", "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan", "Jacob", "Gary",
        "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin", "Scott", "Brandon", "Benjamin", "Samuel"
    ]
    FIRST_NAMES_FEMALE = [
        "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen",
        "Lisa", "Nancy", "Betty", "Margaret", "Sandra", "Ashley", "Dorothy", "Kimberly", "Emily", "Donna",
        "Michelle", "Carol", "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura", "Cynthia",
        "Kathleen", "Amy", "Angela", "Shirley", "Anna", "Brenda", "Pamela", "Emma", "Nicole", "Helen"
    ]
    LAST_NAMES = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
        "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
        "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
        "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
        "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts"
    ]
    
    CITIES = [
        "Boston", "Cambridge", "Somerville", "Newton", "Brookline", "Quincy", "Medford", "Malden", "Waltham", "Arlington",
        "Worcester", "Springfield", "Lowell", "Brockton", "New Bedford", "Lynn", "Fall River", "Lawrence", "Haverhill", "Framingham",
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "Austin"
    ]
    STATES = ["MA", "NH", "RI", "CT", "ME", "VT", "NY", "NJ", "PA", "CA", "TX", "FL", "IL", "OH", "GA"]
    
    STREET_TYPES = ["St", "Ave", "Rd", "Ln", "Dr", "Blvd", "Ct", "Pl", "Way", "Cir"]
    STREET_NAMES = ["Main", "Oak", "Pine", "Maple", "Cedar", "Elm", "Washington", "Park", "Lake", "Hill",
                    "Forest", "River", "Spring", "Church", "Mill", "School", "North", "South", "East", "West"]
    
    def __init__(self, seed: Optional[int] = None, run_id: Optional[str] = None):
        """
        Initialize the FHIR faker.
        
        Args:
            seed: Optional seed for reproducibility. If None, uses time-based randomness.
            run_id: Optional run identifier for unique IDs. If None, generates one.
        """
        if seed is not None:
            random.seed(seed)
        else:
            # Time-based seed for unique data each run
            random.seed(time.time_ns())
        
        self.run_id = run_id or datetime.now().strftime("%Y%m%d%H%M%S")
        self.run_hash = hashlib.md5(f"{self.run_id}_{time.time_ns()}".encode()).hexdigest()[:6]
        
        self.patient_counter = 0
        self.observation_counter = 0
        self.encounter_counter = 0
        self.condition_counter = 0
        self.medication_counter = 0
        self.immunization_counter = 0
    
    def _generate_id(self, prefix: str, counter: int) -> str:
        """Generate a unique ID with run-specific prefix."""
        # Include run hash to ensure uniqueness across runs
        return f"{prefix}-{self.run_hash}-{counter:05d}"
    
    def _generate_uuid(self) -> str:
        """Generate a random UUID."""
        return str(uuid.uuid4())
    
    def _add_run_metadata(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Add run metadata as a tag for traceability."""
        if "meta" not in resource:
            resource["meta"] = {}
        resource["meta"]["tag"] = resource["meta"].get("tag", []) + [
            {
                "system": "http://example.org/fhir/test-data-generator",
                "code": f"run-{self.run_id}",
                "display": f"Generated by FHIR Faker run {self.run_id}"
            }
        ]
        return resource
    
    def _random_date(self, start_year: int = 1940, end_year: int = 2010) -> str:
        """Generate a random date string."""
        year = random.randint(start_year, end_year)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year:04d}-{month:02d}-{day:02d}"
    
    def _random_datetime(self, days_back: int = 365) -> str:
        """Generate a random datetime within the past N days."""
        now = datetime.now()
        delta = timedelta(days=random.randint(0, days_back), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        dt = now - delta
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    def _random_phone(self) -> str:
        """Generate a random phone number."""
        return f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
    
    def _random_mrn(self) -> str:
        """Generate a unique random MRN with run prefix."""
        return f"MRN-{self.run_hash}-{random.randint(100000, 999999)}"
    
    def _random_ssn(self) -> str:
        """Generate a random SSN (fake)."""
        return f"{random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"
    
    def _random_npi(self) -> str:
        """Generate a random NPI (National Provider Identifier)."""
        return f"{random.randint(1000000000, 9999999999)}"
    
    def _random_encounter_number(self) -> str:
        """Generate a unique encounter number."""
        return f"ENC-{self.run_hash}-{random.randint(100000, 999999)}"
    
    # =========================================================================
    # Patient Generation
    # =========================================================================
    
    def generate_patient(self, 
                         patient_id: Optional[str] = None,
                         include_optional: bool = True,
                         boundary_case: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a FHIR Patient resource.
        
        boundary_case options:
        - "minimal": Only required fields
        - "maximal": All optional fields populated
        - "unicode": Names with unicode characters
        - "long_name": Very long names
        - "special_chars": Special characters in fields
        - "empty_name": Empty name array
        - "multiple_names": Multiple name entries
        - "multiple_identifiers": Many identifiers
        - "deceased": Deceased patient
        - "no_address": Missing address
        - "future_birth": Future birth date (invalid)
        - "ancient_birth": Very old birth date
        """
        self.patient_counter += 1
        pid = patient_id or self._generate_id("patient", self.patient_counter)
        
        gender = random.choice(self.GENDERS)
        first_names = self.FIRST_NAMES_MALE if gender == "male" else self.FIRST_NAMES_FEMALE
        first_name = random.choice(first_names)
        last_name = random.choice(self.LAST_NAMES)
        
        # Base patient
        patient = {
            "resourceType": "Patient",
            "id": pid,
            "meta": {
                "versionId": "1",
                "lastUpdated": self._random_datetime(30)
            }
        }
        
        # Apply boundary case modifications
        if boundary_case == "minimal":
            patient["name"] = [{"family": last_name}]
            return self._add_run_metadata(patient)
        
        if boundary_case == "unicode":
            first_name = "José María"
            last_name = "García-López"
        
        if boundary_case == "long_name":
            first_name = "A" * 200
            last_name = "B" * 200
        
        if boundary_case == "special_chars":
            first_name = "John<script>alert('xss')</script>"
            last_name = "O'Brien-Smith & Sons"
        
        if boundary_case == "empty_name":
            patient["name"] = []
            patient["gender"] = gender
            return self._add_run_metadata(patient)
        
        if boundary_case == "future_birth":
            birth_date = "2030-01-01"
        elif boundary_case == "ancient_birth":
            birth_date = "1850-01-01"
        else:
            birth_date = self._random_date()
        
        # Build name
        names = [{
            "use": "official",
            "family": last_name,
            "given": [first_name]
        }]
        
        if boundary_case == "multiple_names":
            names.append({
                "use": "nickname",
                "given": ["Johnny"]
            })
            names.append({
                "use": "maiden",
                "family": "OriginalLastName"
            })
        
        patient["name"] = names
        patient["gender"] = gender
        patient["birthDate"] = birth_date
        patient["active"] = True
        
        # Identifiers
        identifiers = [{
            "system": "http://hospital.example.org/mrn",
            "value": self._random_mrn()
        }]
        
        if boundary_case == "multiple_identifiers":
            identifiers.extend([
                {"system": "http://hl7.org/fhir/sid/us-ssn", "value": self._random_ssn()},
                {"system": "http://hospital.example.org/ehr", "value": f"EHR{random.randint(1000, 9999)}"},
                {"system": "urn:oid:2.16.840.1.113883.4.1", "value": f"DL{random.randint(100000, 999999)}"},
            ])
        
        patient["identifier"] = identifiers
        
        # Address
        if boundary_case != "no_address" and (include_optional or boundary_case == "maximal"):
            state = random.choice(self.STATES)
            # Generate realistic zip codes based on state
            zip_prefixes = {"MA": "02", "NH": "03", "RI": "02", "CT": "06", "ME": "04", "VT": "05",
                          "NY": "1", "NJ": "07", "PA": "1", "CA": "9", "TX": "7", "FL": "3", "IL": "6", "OH": "4", "GA": "3"}
            zip_prefix = zip_prefixes.get(state, "0")
            patient["address"] = [{
                "use": "home",
                "line": [f"{random.randint(1, 9999)} {random.choice(self.STREET_NAMES)} {random.choice(self.STREET_TYPES)}"],
                "city": random.choice(self.CITIES),
                "state": state,
                "postalCode": f"{zip_prefix}{random.randint(1000, 9999)}"
            }]
        
        # Telecom
        if include_optional or boundary_case == "maximal":
            patient["telecom"] = [
                {"system": "phone", "value": self._random_phone(), "use": "home"},
                {"system": "email", "value": f"{first_name.lower()}.{last_name.lower()}@example.com", "use": "home"}
            ]
        
        # Deceased
        if boundary_case == "deceased":
            patient["deceasedBoolean"] = True
            patient["deceasedDateTime"] = self._random_datetime(365)
        
        # Extensions (for maximal case)
        if boundary_case == "maximal":
            patient["extension"] = [
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
                    "extension": [
                        {"url": "ombCategory", "valueCoding": {"system": "urn:oid:2.16.840.1.113883.6.238", "code": "2106-3", "display": "White"}}
                    ]
                },
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
                    "extension": [
                        {"url": "ombCategory", "valueCoding": {"system": "urn:oid:2.16.840.1.113883.6.238", "code": "2186-5", "display": "Not Hispanic or Latino"}}
                    ]
                }
            ]
        
        return self._add_run_metadata(patient)
    
    # =========================================================================
    # Observation Generation
    # =========================================================================
    
    def generate_observation(self,
                            patient_id: str,
                            observation_id: Optional[str] = None,
                            boundary_case: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a FHIR Observation resource.
        
        boundary_case options:
        - "minimal": Only required fields
        - "extreme_high": Value at upper boundary
        - "extreme_low": Value at lower boundary
        - "zero_value": Value of zero
        - "negative_value": Negative value (invalid for most)
        - "null_value": Missing value
        - "string_value": String instead of numeric
        - "component": Multi-component observation (BP)
        - "no_subject": Missing subject reference
        - "invalid_status": Invalid status code
        - "future_date": Future effective date
        - "text_only": Only text, no coding
        """
        self.observation_counter += 1
        obs_id = observation_id or self._generate_id("obs", self.observation_counter)
        
        loinc_code, display, category, unit, min_val, max_val = random.choice(self.LOINC_CODES)
        
        observation = {
            "resourceType": "Observation",
            "id": obs_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": self._random_datetime(7)
            },
            "status": "final"
        }
        
        # Status variations
        if boundary_case == "invalid_status":
            observation["status"] = "invalid-status-code"
        elif random.random() < 0.1:
            observation["status"] = random.choice(["preliminary", "amended", "corrected"])
        
        # Category
        observation["category"] = [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": category,
                "display": category.replace("-", " ").title()
            }]
        }]
        
        # Code
        if boundary_case == "text_only":
            observation["code"] = {"text": display}
        else:
            observation["code"] = {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": display
                }],
                "text": display
            }
        
        # Subject
        if boundary_case != "no_subject":
            observation["subject"] = {"reference": f"Patient/{patient_id}"}
        
        # Effective datetime
        if boundary_case == "future_date":
            observation["effectiveDateTime"] = "2030-01-01T12:00:00Z"
        else:
            observation["effectiveDateTime"] = self._random_datetime(30)
        
        # Component observation (Blood Pressure)
        if boundary_case == "component" or loinc_code == "85354-9":
            observation["code"] = {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "85354-9",
                    "display": "Blood pressure panel"
                }]
            }
            observation["component"] = [
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic blood pressure"}]},
                    "valueQuantity": {"value": random.randint(90, 180), "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                },
                {
                    "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic blood pressure"}]},
                    "valueQuantity": {"value": random.randint(60, 110), "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}
                }
            ]
            return self._add_run_metadata(observation)
        
        # Value
        if boundary_case == "extreme_high":
            value = max_val * 1.5
        elif boundary_case == "extreme_low":
            value = min_val * 0.5
        elif boundary_case == "zero_value":
            value = 0
        elif boundary_case == "negative_value":
            value = -abs(random.uniform(min_val, max_val))
        elif boundary_case == "null_value":
            # No valueQuantity
            observation["dataAbsentReason"] = {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/data-absent-reason", "code": "not-performed"}]
            }
            return self._add_run_metadata(observation)
        elif boundary_case == "string_value":
            observation["valueString"] = "Positive"
            return self._add_run_metadata(observation)
        else:
            value = round(random.uniform(min_val, max_val), 1)
        
        observation["valueQuantity"] = {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit
        }
        
        return self._add_run_metadata(observation)
    
    # =========================================================================
    # Encounter Generation
    # =========================================================================
    
    def generate_encounter(self,
                          patient_id: str,
                          encounter_id: Optional[str] = None,
                          boundary_case: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a FHIR Encounter resource.
        
        boundary_case options:
        - "minimal": Only required fields
        - "no_period": Missing period
        - "open_ended": Period with no end
        - "long_duration": Very long encounter (years)
        - "zero_duration": Start equals end
        - "invalid_class": Invalid class code
        - "multiple_types": Multiple type codes
        - "no_subject": Missing subject
        """
        self.encounter_counter += 1
        enc_id = encounter_id or self._generate_id("enc", self.encounter_counter)
        
        status = random.choice(self.ENCOUNTER_STATUSES)
        class_code = random.choice(self.ENCOUNTER_CLASSES)
        
        encounter = {
            "resourceType": "Encounter",
            "id": enc_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": self._random_datetime(7)
            },
            "status": status
        }
        
        # Class
        if boundary_case == "invalid_class":
            encounter["class"] = {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "INVALID",
                "display": "Invalid Class"
            }
        else:
            encounter["class"] = {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": class_code,
                "display": class_code
            }
        
        # Type
        types = [{
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "185345009",
                "display": "Encounter for check up"
            }]
        }]
        
        if boundary_case == "multiple_types":
            types.append({
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "50849002",
                    "display": "Emergency room admission"
                }]
            })
        
        encounter["type"] = types
        
        # Subject
        if boundary_case != "no_subject":
            encounter["subject"] = {"reference": f"Patient/{patient_id}"}
        
        # Period
        if boundary_case != "no_period":
            start_time = datetime.now() - timedelta(days=random.randint(1, 365))
            
            if boundary_case == "open_ended" or status == "in-progress":
                encounter["period"] = {"start": start_time.strftime("%Y-%m-%dT%H:%M:%SZ")}
            elif boundary_case == "long_duration":
                end_time = start_time + timedelta(days=730)  # 2 years
                encounter["period"] = {
                    "start": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "end": end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            elif boundary_case == "zero_duration":
                encounter["period"] = {
                    "start": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "end": start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            else:
                end_time = start_time + timedelta(hours=random.randint(1, 72))
                encounter["period"] = {
                    "start": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "end": end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
        
        return self._add_run_metadata(encounter)
    
    # =========================================================================
    # Condition Generation
    # =========================================================================
    
    def generate_condition(self,
                          patient_id: str,
                          condition_id: Optional[str] = None,
                          boundary_case: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a FHIR Condition resource.
        
        boundary_case options:
        - "minimal": Only required fields
        - "no_code": Missing condition code
        - "no_subject": Missing subject
        - "abatement": Resolved condition with abatement
        - "onset_range": Onset as age range
        - "multiple_categories": Multiple categories
        - "severity": Include severity
        """
        self.condition_counter += 1
        cond_id = condition_id or self._generate_id("cond", self.condition_counter)
        
        snomed_code, display = random.choice(self.SNOMED_CONDITIONS)
        clinical_status = random.choice(self.CONDITION_CLINICAL_STATUSES)
        verification_status = random.choice(self.CONDITION_VERIFICATION_STATUSES)
        
        condition = {
            "resourceType": "Condition",
            "id": cond_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": self._random_datetime(7)
            },
            "clinicalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": clinical_status,
                    "display": clinical_status.title()
                }]
            },
            "verificationStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": verification_status,
                    "display": verification_status.title()
                }]
            }
        }
        
        # Category
        categories = [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                "code": "encounter-diagnosis",
                "display": "Encounter Diagnosis"
            }]
        }]
        
        if boundary_case == "multiple_categories":
            categories.append({
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                    "code": "problem-list-item",
                    "display": "Problem List Item"
                }]
            })
        
        condition["category"] = categories
        
        # Code
        if boundary_case != "no_code":
            condition["code"] = {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": snomed_code,
                    "display": display
                }],
                "text": display
            }
        
        # Subject
        if boundary_case != "no_subject":
            condition["subject"] = {"reference": f"Patient/{patient_id}"}
        
        # Onset
        if boundary_case == "onset_range":
            condition["onsetRange"] = {
                "low": {"value": 30, "unit": "years"},
                "high": {"value": 40, "unit": "years"}
            }
        else:
            condition["onsetDateTime"] = self._random_date(2015, 2025)
        
        # Abatement
        if boundary_case == "abatement" or clinical_status == "resolved":
            condition["abatementDateTime"] = self._random_datetime(180)
        
        # Severity
        if boundary_case == "severity":
            condition["severity"] = {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "24484000",
                    "display": "Severe"
                }]
            }
        
        return self._add_run_metadata(condition)
    
    # =========================================================================
    # MedicationRequest Generation
    # =========================================================================
    
    def generate_medication_request(self,
                                   patient_id: str,
                                   medication_id: Optional[str] = None,
                                   boundary_case: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a FHIR MedicationRequest resource.
        
        boundary_case options:
        - "minimal": Only required fields
        - "no_medication": Missing medication
        - "no_subject": Missing subject
        - "complex_dosage": Complex dosing instructions
        - "prn": As-needed medication
        - "dispense_request": Include dispense details
        """
        self.medication_counter += 1
        med_id = medication_id or self._generate_id("medrx", self.medication_counter)
        
        rxnorm_code, display = random.choice(self.RXNORM_MEDICATIONS)
        status = random.choice(self.MEDICATION_STATUSES)
        
        medication = {
            "resourceType": "MedicationRequest",
            "id": med_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": self._random_datetime(7)
            },
            "status": status,
            "intent": "order"
        }
        
        # Medication
        if boundary_case != "no_medication":
            medication["medicationCodeableConcept"] = {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": rxnorm_code,
                    "display": display
                }],
                "text": display
            }
        
        # Subject
        if boundary_case != "no_subject":
            medication["subject"] = {"reference": f"Patient/{patient_id}"}
        
        # Authored on
        medication["authoredOn"] = self._random_datetime(30)
        
        # Dosage instructions
        if boundary_case == "complex_dosage":
            medication["dosageInstruction"] = [
                {
                    "text": "Take 1 tablet in the morning",
                    "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d", "when": ["MORN"]}},
                    "doseAndRate": [{"doseQuantity": {"value": 1, "unit": "tablet"}}]
                },
                {
                    "text": "Take 2 tablets at bedtime",
                    "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d", "when": ["HS"]}},
                    "doseAndRate": [{"doseQuantity": {"value": 2, "unit": "tablet"}}]
                }
            ]
        elif boundary_case == "prn":
            medication["dosageInstruction"] = [{
                "text": "Take 1-2 tablets every 4-6 hours as needed for pain",
                "asNeededBoolean": True,
                "doseAndRate": [{"doseQuantity": {"value": 1, "unit": "tablet"}}],
                "maxDosePerPeriod": {"numerator": {"value": 8, "unit": "tablet"}, "denominator": {"value": 24, "unit": "h"}}
            }]
        else:
            medication["dosageInstruction"] = [{
                "text": "Take one tablet daily",
                "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}},
                "doseAndRate": [{"doseQuantity": {"value": 1, "unit": "tablet"}}]
            }]
        
        # Dispense request
        if boundary_case == "dispense_request":
            medication["dispenseRequest"] = {
                "validityPeriod": {"start": self._random_datetime(30), "end": self._random_datetime(0)},
                "numberOfRepeatsAllowed": 3,
                "quantity": {"value": 90, "unit": "tablet"},
                "expectedSupplyDuration": {"value": 90, "unit": "d"}
            }
        
        return self._add_run_metadata(medication)
    
    # =========================================================================
    # Immunization Generation
    # =========================================================================
    
    def generate_immunization(self,
                             patient_id: str,
                             immunization_id: Optional[str] = None,
                             boundary_case: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a FHIR Immunization resource.
        
        boundary_case options:
        - "minimal": Only required fields
        - "no_vaccine": Missing vaccine code
        - "no_patient": Missing patient reference
        - "not_done": Immunization not given
        - "reaction": Include reaction information
        - "protocol": Include protocol information
        """
        self.immunization_counter += 1
        imm_id = immunization_id or self._generate_id("imm", self.immunization_counter)
        
        cvx_code, display = random.choice(self.CVX_VACCINES)
        status = random.choice(self.IMMUNIZATION_STATUSES)
        
        if boundary_case == "not_done":
            status = "not-done"
        
        immunization = {
            "resourceType": "Immunization",
            "id": imm_id,
            "meta": {
                "versionId": "1",
                "lastUpdated": self._random_datetime(7)
            },
            "status": status
        }
        
        # Vaccine code
        if boundary_case != "no_vaccine":
            immunization["vaccineCode"] = {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/cvx",
                    "code": cvx_code,
                    "display": display
                }],
                "text": display
            }
        
        # Patient
        if boundary_case != "no_patient":
            immunization["patient"] = {"reference": f"Patient/{patient_id}"}
        
        # Occurrence
        immunization["occurrenceDateTime"] = self._random_datetime(365)
        
        # Primary source
        immunization["primarySource"] = True
        
        # Lot number
        immunization["lotNumber"] = f"LOT{random.randint(10000, 99999)}"
        
        # Site
        sites = [("LA", "left arm"), ("RA", "right arm"), ("LT", "left thigh"), ("RT", "right thigh")]
        site_code, site_display = random.choice(sites)
        immunization["site"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActSite",
                "code": site_code,
                "display": site_display
            }]
        }
        
        # Status reason for not-done
        if status == "not-done":
            immunization["statusReason"] = {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActReason",
                    "code": "PATOBJ",
                    "display": "patient objection"
                }]
            }
        
        # Reaction
        if boundary_case == "reaction":
            immunization["reaction"] = [{
                "date": self._random_datetime(7),
                "detail": {"reference": "Observation/reaction-001"},
                "reported": True
            }]
        
        # Protocol
        if boundary_case == "protocol":
            immunization["protocolApplied"] = [{
                "series": "3-dose series",
                "doseNumberPositiveInt": random.randint(1, 3),
                "seriesDosesPositiveInt": 3
            }]
        
        return self._add_run_metadata(immunization)
    
    # =========================================================================
    # Bundle Generation
    # =========================================================================
    
    def generate_bundle(self, 
                       resources: List[Dict[str, Any]],
                       bundle_type: str = "collection") -> Dict[str, Any]:
        """
        Wrap resources in a FHIR Bundle.
        
        bundle_type: collection, document, message, transaction, batch
        """
        bundle = {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "meta": {
                "lastUpdated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "type": bundle_type,
            "total": len(resources),
            "entry": [{"resource": r} for r in resources]
        }
        
        if bundle_type in ["transaction", "batch"]:
            for entry in bundle["entry"]:
                entry["request"] = {
                    "method": "PUT",
                    "url": f"{entry['resource']['resourceType']}/{entry['resource']['id']}"
                }
        
        return bundle
    
    # =========================================================================
    # Invalid/Corrupt Data Generation
    # =========================================================================
    
    def generate_invalid_json(self) -> str:
        """Generate invalid JSON that should fail parsing."""
        invalids = [
            '{"resourceType": "Patient", "id": "test"',  # Missing closing brace
            "{'resourceType': 'Patient'}",  # Single quotes
            '{"resourceType": "Patient", "id": }',  # Missing value
            'not json at all',
            '',  # Empty
            '{"resourceType": "Patient", "id": "test", "name": [{"given": ["test",]}]}',  # Trailing comma
            '\x00\x01\x02',  # Binary garbage
        ]
        return random.choice(invalids)
    
    def generate_invalid_fhir(self) -> Dict[str, Any]:
        """Generate valid JSON but invalid FHIR."""
        invalids = [
            {"resourceType": "InvalidResource", "id": "test"},  # Invalid resource type
            {"id": "test"},  # Missing resourceType
            {"resourceType": "Patient"},  # Missing id
            {"resourceType": "", "id": "test"},  # Empty resourceType
            {"resourceType": "Patient", "id": "", "name": []},  # Empty id
            {"resourceType": 123, "id": "test"},  # Wrong type for resourceType
        ]
        return random.choice(invalids)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Generation Functions

# COMMAND ----------

def clear_fhir_volume(path: str):
    """Clear existing FHIR data from volume."""
    try:
        files = dbutils.fs.ls(path)
        for f in files:
            dbutils.fs.rm(f.path, recurse=True)
        print(f"Cleared {len(files)} items from {path}")
    except Exception as e:
        print(f"Path {path} doesn't exist or is empty: {e}")

def write_ndjson(path: str, resources: List[Dict[str, Any]]):
    """Write resources as NDJSON file (one JSON object per line, no indentation)."""
    content = "\n".join(json.dumps(r) for r in resources)
    dbutils.fs.put(path, content, overwrite=True)
    print(f"Wrote {len(resources)} resources to {path}")

def write_json(path: str, resource: Dict[str, Any]):
    """Write a single JSON resource as single-line JSON (NDJSON compatible)."""
    # Write as single line for NDJSON compatibility (Auto Loader reads line by line)
    content = json.dumps(resource)
    dbutils.fs.put(path, content, overwrite=True)
    print(f"Wrote {resource.get('resourceType', 'resource')} to {path}")

def write_corrupt_file(path: str, content: str):
    """Write corrupt/invalid content."""
    dbutils.fs.put(path, content, overwrite=True)
    print(f"Wrote corrupt file to {path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Comprehensive Test Data

# COMMAND ----------

# Initialize generator with run-specific settings
if USE_FIXED_SEED:
    faker = FHIRFaker(seed=FIXED_SEED, run_id=RUN_ID)
    print(f"Using fixed seed: {FIXED_SEED}")
else:
    faker = FHIRFaker(run_id=RUN_ID)
    print(f"Using dynamic randomness")

print(f"Resource ID prefix: {faker.run_hash}")

# Clear existing data
clear_fhir_volume(FHIR_PATH)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1. Standard Valid Data (Mixed Resources)

# COMMAND ----------

# Generate patients and related resources
all_resources = []
patient_ids = []

print("Generating standard valid data...")

for i in range(NUM_PATIENTS):
    # Patient
    patient = faker.generate_patient()
    all_resources.append(patient)
    patient_ids.append(patient["id"])
    
    # Observations for this patient
    for _ in range(NUM_OBSERVATIONS_PER_PATIENT):
        all_resources.append(faker.generate_observation(patient["id"]))
    
    # Encounters
    for _ in range(NUM_ENCOUNTERS_PER_PATIENT):
        all_resources.append(faker.generate_encounter(patient["id"]))
    
    # Conditions
    for _ in range(NUM_CONDITIONS_PER_PATIENT):
        all_resources.append(faker.generate_condition(patient["id"]))
    
    # Medications
    for _ in range(NUM_MEDICATIONS_PER_PATIENT):
        all_resources.append(faker.generate_medication_request(patient["id"]))
    
    # Immunizations
    for _ in range(NUM_IMMUNIZATIONS_PER_PATIENT):
        all_resources.append(faker.generate_immunization(patient["id"]))

print(f"Generated {len(all_resources)} standard resources for {NUM_PATIENTS} patients")

# Write as single mixed NDJSON file
write_ndjson(f"{FHIR_PATH}/standard/mixed_resources.ndjson", all_resources)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2. Boundary Test Cases - Patients

# COMMAND ----------

print("Generating patient boundary cases...")

patient_boundary_cases = [
    "minimal", "maximal", "unicode", "long_name", "special_chars",
    "empty_name", "multiple_names", "multiple_identifiers", "deceased",
    "no_address", "future_birth", "ancient_birth"
]

boundary_patients = []
for case in patient_boundary_cases:
    patient = faker.generate_patient(boundary_case=case)
    patient["id"] = f"patient-boundary-{case}"
    boundary_patients.append(patient)
    print(f"  - {case}: {patient['id']}")

write_ndjson(f"{FHIR_PATH}/boundaries/patient_boundaries.ndjson", boundary_patients)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 3. Boundary Test Cases - Observations

# COMMAND ----------

print("Generating observation boundary cases...")

observation_boundary_cases = [
    "minimal", "extreme_high", "extreme_low", "zero_value", "negative_value",
    "null_value", "string_value", "component", "no_subject", "invalid_status",
    "future_date", "text_only"
]

boundary_observations = []
for case in observation_boundary_cases:
    obs = faker.generate_observation(patient_ids[0], boundary_case=case)
    obs["id"] = f"obs-boundary-{case}"
    boundary_observations.append(obs)
    print(f"  - {case}: {obs['id']}")

write_ndjson(f"{FHIR_PATH}/boundaries/observation_boundaries.ndjson", boundary_observations)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4. Boundary Test Cases - Encounters

# COMMAND ----------

print("Generating encounter boundary cases...")

encounter_boundary_cases = [
    "minimal", "no_period", "open_ended", "long_duration", "zero_duration",
    "invalid_class", "multiple_types", "no_subject"
]

boundary_encounters = []
for case in encounter_boundary_cases:
    enc = faker.generate_encounter(patient_ids[0], boundary_case=case)
    enc["id"] = f"enc-boundary-{case}"
    boundary_encounters.append(enc)
    print(f"  - {case}: {enc['id']}")

write_ndjson(f"{FHIR_PATH}/boundaries/encounter_boundaries.ndjson", boundary_encounters)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5. Boundary Test Cases - Conditions, Medications, Immunizations

# COMMAND ----------

print("Generating condition boundary cases...")

condition_boundary_cases = ["minimal", "no_code", "no_subject", "abatement", "onset_range", "multiple_categories", "severity"]
boundary_conditions = []
for case in condition_boundary_cases:
    cond = faker.generate_condition(patient_ids[0], boundary_case=case)
    cond["id"] = f"cond-boundary-{case}"
    boundary_conditions.append(cond)

write_ndjson(f"{FHIR_PATH}/boundaries/condition_boundaries.ndjson", boundary_conditions)

print("Generating medication boundary cases...")

medication_boundary_cases = ["minimal", "no_medication", "no_subject", "complex_dosage", "prn", "dispense_request"]
boundary_medications = []
for case in medication_boundary_cases:
    med = faker.generate_medication_request(patient_ids[0], boundary_case=case)
    med["id"] = f"medrx-boundary-{case}"
    boundary_medications.append(med)

write_ndjson(f"{FHIR_PATH}/boundaries/medication_boundaries.ndjson", boundary_medications)

print("Generating immunization boundary cases...")

immunization_boundary_cases = ["minimal", "no_vaccine", "no_patient", "not_done", "reaction", "protocol"]
boundary_immunizations = []
for case in immunization_boundary_cases:
    imm = faker.generate_immunization(patient_ids[0], boundary_case=case)
    imm["id"] = f"imm-boundary-{case}"
    boundary_immunizations.append(imm)

write_ndjson(f"{FHIR_PATH}/boundaries/immunization_boundaries.ndjson", boundary_immunizations)

print(f"Generated boundary cases for all resource types")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 6. Nested Directory Structure

# COMMAND ----------

print("Generating nested directory structure...")

# Create deeply nested directories with different organization patterns

# By date
for year in [2025, 2026]:
    for month in [1, 6, 12]:
        resources = [faker.generate_patient(), faker.generate_observation(patient_ids[0])]
        write_ndjson(f"{FHIR_PATH}/by_date/{year}/{month:02d}/data.ndjson", resources)

# By resource type
for resource_type in ["Patient", "Observation", "Encounter"]:
    if resource_type == "Patient":
        resources = [faker.generate_patient() for _ in range(3)]
    elif resource_type == "Observation":
        resources = [faker.generate_observation(patient_ids[0]) for _ in range(5)]
    else:
        resources = [faker.generate_encounter(patient_ids[0]) for _ in range(2)]
    write_ndjson(f"{FHIR_PATH}/by_type/{resource_type.lower()}/data.ndjson", resources)

# By source system
for source in ["ehr_system_a", "ehr_system_b", "lab_system"]:
    resources = [
        faker.generate_patient(),
        faker.generate_observation(patient_ids[0]),
        faker.generate_encounter(patient_ids[0])
    ]
    write_ndjson(f"{FHIR_PATH}/by_source/{source}/incoming/data.ndjson", resources)

# Very deep nesting
deep_resources = [faker.generate_patient(), faker.generate_observation(patient_ids[0])]
write_ndjson(f"{FHIR_PATH}/deep/level1/level2/level3/level4/level5/data.ndjson", deep_resources)

print("Nested directory structures created")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 7. Bundle Resources

# COMMAND ----------

print("Generating Bundle resources...")

# Collection bundle
collection_resources = [
    faker.generate_patient(),
    faker.generate_observation(patient_ids[0]),
    faker.generate_encounter(patient_ids[0])
]
collection_bundle = faker.generate_bundle(collection_resources, "collection")
write_json(f"{FHIR_PATH}/bundles/collection_bundle.ndjson", collection_bundle)

# Transaction bundle
transaction_resources = [
    faker.generate_patient(),
    faker.generate_condition(patient_ids[0])
]
transaction_bundle = faker.generate_bundle(transaction_resources, "transaction")
write_json(f"{FHIR_PATH}/bundles/transaction_bundle.ndjson", transaction_bundle)

# Large bundle with many resources
large_bundle_resources = []
for _ in range(20):
    large_bundle_resources.append(faker.generate_patient())
    large_bundle_resources.append(faker.generate_observation(patient_ids[0]))
large_bundle = faker.generate_bundle(large_bundle_resources, "collection")
write_json(f"{FHIR_PATH}/bundles/large_bundle.ndjson", large_bundle)

print("Bundle resources created")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 8. Corrupt/Invalid Files (Negative Tests)

# COMMAND ----------

print("Generating corrupt/invalid files...")

# Invalid JSON files
invalid_json_cases = [
    ("missing_brace", '{"resourceType": "Patient", "id": "test"'),
    ("single_quotes", "{'resourceType': 'Patient'}"),
    ("missing_value", '{"resourceType": "Patient", "id": }'),
    ("not_json", 'this is not json at all'),
    ("empty_file", ''),
    ("trailing_comma", '{"resourceType": "Patient", "id": "test", "name": [{"given": ["test",]}]}'),
    ("binary_garbage", '\x00\x01\x02\xff\xfe'),
    ("truncated_unicode", '{"resourceType": "Patient", "name": [{"given": ["José'),
]

for case_name, content in invalid_json_cases:
    write_corrupt_file(f"{FHIR_PATH}/invalid/json_{case_name}.ndjson", content)

# Valid JSON but invalid FHIR
invalid_fhir_cases = [
    ("invalid_resource_type", {"resourceType": "InvalidResource", "id": "test"}),
    ("missing_resource_type", {"id": "test", "name": [{"given": ["John"]}]}),
    ("empty_resource_type", {"resourceType": "", "id": "test"}),
    ("numeric_resource_type", {"resourceType": 123, "id": "test"}),
    ("missing_id", {"resourceType": "Patient", "name": [{"given": ["John"]}]}),
    ("empty_id", {"resourceType": "Patient", "id": "", "name": [{"given": ["John"]}]}),
    ("null_resource_type", {"resourceType": None, "id": "test"}),
]

for case_name, resource in invalid_fhir_cases:
    content = json.dumps(resource)
    write_corrupt_file(f"{FHIR_PATH}/invalid/fhir_{case_name}.ndjson", content)

# Mixed valid and invalid in same file
mixed_content = []
mixed_content.append(json.dumps(faker.generate_patient()))  # Valid
mixed_content.append('{"resourceType": "Patient", "id":')  # Invalid JSON
mixed_content.append(json.dumps(faker.generate_patient()))  # Valid
mixed_content.append(json.dumps({"resourceType": "InvalidType", "id": "bad"}))  # Invalid FHIR
mixed_content.append(json.dumps(faker.generate_observation(patient_ids[0])))  # Valid
write_corrupt_file(f"{FHIR_PATH}/invalid/mixed_valid_invalid.ndjson", "\n".join(mixed_content))

print(f"Created {len(invalid_json_cases)} invalid JSON files")
print(f"Created {len(invalid_fhir_cases)} invalid FHIR files")
print("Created mixed valid/invalid file")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 9. Edge Case Files

# COMMAND ----------

print("Generating edge case files...")

# Single resource file
write_ndjson(f"{FHIR_PATH}/edge_cases/single_resource.ndjson", [faker.generate_patient()])

# Very large file (1000 resources)
large_resources = []
for _ in range(200):
    large_resources.append(faker.generate_patient())
    large_resources.append(faker.generate_observation(patient_ids[0]))
    large_resources.append(faker.generate_encounter(patient_ids[0]))
    large_resources.append(faker.generate_condition(patient_ids[0]))
    large_resources.append(faker.generate_medication_request(patient_ids[0]))
write_ndjson(f"{FHIR_PATH}/edge_cases/large_file_1000.ndjson", large_resources)

# File with duplicate IDs (should be handled by deduplication)
dup_patient = faker.generate_patient()
dup_patient["id"] = "duplicate-patient-001"
dup_resources = []
for i in range(5):
    p = dup_patient.copy()
    p["meta"] = {"versionId": str(i + 1), "lastUpdated": faker._random_datetime(i)}
    if i % 2 == 0:
        p["gender"] = "male"
    else:
        p["gender"] = "female"
    dup_resources.append(p)
write_ndjson(f"{FHIR_PATH}/edge_cases/duplicate_ids.ndjson", dup_resources)

# File with only whitespace lines mixed in
whitespace_content = []
whitespace_content.append(json.dumps(faker.generate_patient()))
whitespace_content.append("")  # Empty line
whitespace_content.append("   ")  # Whitespace only
whitespace_content.append(json.dumps(faker.generate_patient()))
whitespace_content.append("\t\t")  # Tabs
whitespace_content.append(json.dumps(faker.generate_observation(patient_ids[0])))
write_corrupt_file(f"{FHIR_PATH}/edge_cases/whitespace_lines.ndjson", "\n".join(whitespace_content))

# Very long single line (resource with huge text field)
long_patient = faker.generate_patient()
long_patient["text"] = {"status": "generated", "div": "<div>" + "A" * 100000 + "</div>"}
write_ndjson(f"{FHIR_PATH}/edge_cases/very_long_line.ndjson", [long_patient])

# Unicode stress test
unicode_patient = faker.generate_patient()
unicode_patient["id"] = "unicode-stress-test"
unicode_patient["name"] = [{
    "family": "日本語テスト",
    "given": ["Ñoño", "مرحبا", "Привет", "🏥👨‍⚕️💉"]
}]
unicode_patient["address"] = [{
    "line": ["北京市朝阳区", "שד' בן גוריון"],
    "city": "東京"
}]
write_ndjson(f"{FHIR_PATH}/edge_cases/unicode_stress.ndjson", [unicode_patient])

print("Edge case files created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Count all generated files and resources
def count_files_recursive(path):
    """Recursively count files and total size."""
    total_files = 0
    total_size = 0
    try:
        items = dbutils.fs.ls(path)
        for item in items:
            if item.isDir():
                f, s = count_files_recursive(item.path)
                total_files += f
                total_size += s
            else:
                total_files += 1
                total_size += item.size
    except:
        pass
    return total_files, total_size

file_count, total_size = count_files_recursive(FHIR_PATH)

print("=" * 60)
print("FHIR TEST DATA GENERATION COMPLETE")
print("=" * 60)
print(f"\nRun Information:")
print(f"  Run ID: {RUN_ID}")
print(f"  Run Hash: {RUN_HASH}")
print(f"  Resource ID Prefix: {faker.run_hash}")
print(f"  Mode: {'Fixed Seed (Reproducible)' if USE_FIXED_SEED else 'Dynamic (Unique Each Run)'}")
print(f"\nTarget Volume: {FHIR_PATH}")
print(f"Total Files Generated: {file_count}")
print(f"Total Size: {total_size / 1024:.2f} KB")
print(f"\nPatients: {NUM_PATIENTS}")
print(f"Resources per Patient: {NUM_OBSERVATIONS_PER_PATIENT + NUM_ENCOUNTERS_PER_PATIENT + NUM_CONDITIONS_PER_PATIENT + NUM_MEDICATIONS_PER_PATIENT + NUM_IMMUNIZATIONS_PER_PATIENT}")
print(f"\nDirectory Structure:")
print("  - /standard/          : Mixed valid resources")
print("  - /boundaries/        : Boundary test cases for each resource type")
print("  - /by_date/           : Nested by year/month")
print("  - /by_type/           : Nested by resource type")
print("  - /by_source/         : Nested by source system")
print("  - /deep/              : Deeply nested (5 levels)")
print("  - /bundles/           : FHIR Bundle resources")
print("  - /invalid/           : Corrupt JSON and invalid FHIR")
print("  - /edge_cases/        : Edge cases (large files, duplicates, unicode)")
print(f"\nAll resources tagged with: run-{faker.run_id}")
print("\nReady for pipeline validation!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## List Generated Files

# COMMAND ----------

def list_files_recursive(path, indent=0):
    """List all files with indentation for directories."""
    try:
        items = dbutils.fs.ls(path)
        for item in items:
            name = item.path.split("/")[-1] or item.path.split("/")[-2]
            if item.isDir():
                print("  " * indent + f"📁 {name}/")
                list_files_recursive(item.path, indent + 1)
            else:
                size_kb = item.size / 1024
                print("  " * indent + f"📄 {name} ({size_kb:.1f} KB)")
    except Exception as e:
        print(f"Error listing {path}: {e}")

print(f"\nGenerated file structure in {FHIR_PATH}:\n")
list_files_recursive(FHIR_PATH)
