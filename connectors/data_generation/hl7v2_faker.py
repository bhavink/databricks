"""
HL7v2 Message Generator (Faker)

Generates realistic HL7v2 test messages for ADT, ORM, ORU, SIU, and VXU message types.

Usage:
    # Run directly on Databricks cluster:
    python hl7v2_faker.py --output /Volumes/catalog/schema/volume/hl7v2 --count 50
    
    # Or import and use programmatically:
    from hl7v2_faker import HL7v2Generator
    gen = HL7v2Generator()
    messages = gen.generate_batch(count=10, message_types=["ADT", "ORU"])
"""

import argparse
import json
import os
import random
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


# =============================================================================
# Sample Data for Realistic Generation
# =============================================================================

FIRST_NAMES_MALE = [
    "James", "John", "Robert", "Michael", "William", 
    "David", "Joseph", "Charles", "Thomas", "Daniel",
    "Matthew", "Anthony", "Mark", "Donald", "Steven"
]

FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", 
    "Barbara", "Susan", "Jessica", "Sarah", "Karen",
    "Nancy", "Lisa", "Betty", "Margaret", "Sandra"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", 
    "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"
]

FACILITIES = [
    "MERCY_HOSPITAL", "CITY_MEDICAL", "ST_JOSEPH", 
    "GENERAL_HOSPITAL", "UNIVERSITY_HEALTH", "REGIONAL_MED"
]

APPLICATIONS = ["EPIC", "CERNER", "MEDITECH", "ALLSCRIPTS", "ATHENA"]

PATIENT_CLASSES = ["I", "O", "E", "P", "R"]  # Inpatient, Outpatient, Emergency, Preadmit, Recurring
ADMISSION_TYPES = ["E", "U", "C", "N"]  # Emergency, Urgent, Elective, Newborn

LOCATIONS = [
    "ICU^101^A", "ICU^102^B", "MED^201^A", "MED^202^B", "SURG^301^A",
    "SURG^302^B", "PEDS^401^A", "ER^001^A", "ER^002^B", "OB^501^A"
]

PHYSICIANS = [
    "1234567^SMITH^JANE^^^DR",
    "2345678^JOHNSON^ROBERT^^^DR",
    "3456789^WILLIAMS^SARAH^^^DR",
    "4567890^BROWN^MICHAEL^^^DR",
    "5678901^DAVIS^EMILY^^^DR"
]

# Lab test codes and results
LAB_TESTS = {
    "CBC": "CBC^Complete Blood Count^L",
    "BMP": "BMP^Basic Metabolic Panel^L",
    "CMP": "CMP^Comprehensive Metabolic Panel^L",
    "LFT": "LFT^Liver Function Tests^L",
    "TSH": "TSH^Thyroid Stimulating Hormone^L",
    "UA": "UA^Urinalysis^L",
    "PT": "PT^Prothrombin Time^L",
    "LIPID": "LIPID^Lipid Panel^L",
}

LAB_RESULTS = {
    "CBC": [
        ("WBC^White Blood Cell Count^L", "NM", 4.5, 11.0, "10*3/uL"),
        ("RBC^Red Blood Cell Count^L", "NM", 4.5, 5.5, "10*6/uL"),
        ("HGB^Hemoglobin^L", "NM", 13.5, 17.5, "g/dL"),
        ("HCT^Hematocrit^L", "NM", 38.0, 50.0, "%"),
        ("PLT^Platelet Count^L", "NM", 150, 400, "10*3/uL"),
    ],
    "BMP": [
        ("GLU^Glucose^L", "NM", 70, 100, "mg/dL"),
        ("BUN^Blood Urea Nitrogen^L", "NM", 7, 20, "mg/dL"),
        ("CREAT^Creatinine^L", "NM", 0.7, 1.3, "mg/dL"),
        ("NA^Sodium^L", "NM", 136, 145, "mEq/L"),
        ("K^Potassium^L", "NM", 3.5, 5.0, "mEq/L"),
        ("CL^Chloride^L", "NM", 98, 106, "mEq/L"),
        ("CO2^Carbon Dioxide^L", "NM", 23, 29, "mEq/L"),
    ],
    "CMP": [
        ("GLU^Glucose^L", "NM", 70, 100, "mg/dL"),
        ("BUN^Blood Urea Nitrogen^L", "NM", 7, 20, "mg/dL"),
        ("CREAT^Creatinine^L", "NM", 0.7, 1.3, "mg/dL"),
        ("ALT^Alanine Aminotransferase^L", "NM", 7, 56, "U/L"),
        ("AST^Aspartate Aminotransferase^L", "NM", 10, 40, "U/L"),
        ("ALB^Albumin^L", "NM", 3.5, 5.0, "g/dL"),
        ("TBIL^Total Bilirubin^L", "NM", 0.1, 1.2, "mg/dL"),
    ],
}

# Scheduling resources for SIU
RESOURCES = [
    "DR_SMITH^CARDIOLOGY", "DR_JONES^ONCOLOGY", "DR_WILLIAMS^ORTHOPEDICS",
    "ROOM_101^EXAM", "ROOM_102^PROCEDURE", "MRI_1^IMAGING", "CT_1^IMAGING"
]

APPOINTMENT_TYPES = ["FOLLOWUP", "NEW_PATIENT", "PROCEDURE", "IMAGING", "CONSULTATION"]

# Vaccines for VXU
VACCINES = [
    ("CVX^207^COVID-19, mRNA, LNP-S, PF, 100 mcg/0.5 mL dose", "MODERNA", "MOD12345"),
    ("CVX^208^COVID-19, mRNA, LNP-S, PF, 30 mcg/0.3 mL dose", "PFIZER", "PFI67890"),
    ("CVX^140^Influenza, seasonal, injectable, preservative free", "SANOFI", "FLU23456"),
    ("CVX^115^Tdap", "GSK", "TDAP7890"),
    ("CVX^33^Pneumococcal polysaccharide PPV23", "MERCK", "PNE34567"),
]


# =============================================================================
# Helper Functions
# =============================================================================

def generate_mrn() -> str:
    """Generate a random MRN."""
    return f"MRN{random.randint(100000, 999999)}"


def generate_message_id() -> str:
    """Generate a unique message control ID."""
    return f"MSG{random.randint(10000000, 99999999)}"


def generate_order_id() -> str:
    """Generate a unique order ID."""
    return f"ORD{random.randint(100000, 999999)}"


def generate_datetime(days_back: int = 30) -> str:
    """Generate a random datetime within the past N days."""
    base = datetime.now() - timedelta(days=random.randint(0, days_back))
    return base.strftime("%Y%m%d%H%M%S")


def generate_dob(min_age: int = 18, max_age: int = 85) -> str:
    """Generate a date of birth."""
    age = random.randint(min_age, max_age)
    birth_year = datetime.now().year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    return f"{birth_year}{birth_month:02d}{birth_day:02d}"


def generate_patient() -> Dict[str, str]:
    """Generate random patient demographics."""
    gender = random.choice(["M", "F"])
    first_name = random.choice(FIRST_NAMES_MALE if gender == "M" else FIRST_NAMES_FEMALE)
    
    return {
        "mrn": generate_mrn(),
        "first_name": first_name,
        "last_name": random.choice(LAST_NAMES),
        "gender": gender,
        "dob": generate_dob(),
        "phone": f"(555){random.randint(100,999)}-{random.randint(1000,9999)}",
        "address": f"{random.randint(100, 9999)} MAIN ST^^ANYTOWN^NY^{random.randint(10000, 99999)}",
    }


# =============================================================================
# Message Generators
# =============================================================================

class HL7v2Generator:
    """Generator for various HL7v2 message types."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize generator with optional random seed for reproducibility."""
        if seed is not None:
            random.seed(seed)
    
    def generate_adt(self, event_type: str = "A01") -> Tuple[str, Dict]:
        """
        Generate an ADT message.
        
        Event types:
        - A01: Admit/Visit Notification
        - A02: Transfer
        - A03: Discharge
        - A04: Register a Patient
        - A08: Update Patient Information
        """
        patient = generate_patient()
        msg_datetime = generate_datetime()
        msg_id = generate_message_id()
        facility = random.choice(FACILITIES)
        application = random.choice(APPLICATIONS)
        physician = random.choice(PHYSICIANS)
        location = random.choice(LOCATIONS)
        patient_class = random.choice(PATIENT_CLASSES)
        admission_type = random.choice(ADMISSION_TYPES)
        
        message = (
            f"MSH|^~\\&|{application}|{facility}|LABADT|{facility}|{msg_datetime}||ADT^{event_type}|{msg_id}|P|2.4\n"
            f"EVN|{event_type}|{msg_datetime}\n"
            f"PID|1||{patient['mrn']}^^^{facility}^MR||{patient['last_name']}^{patient['first_name']}^||"
            f"{patient['dob']}|{patient['gender']}|||{patient['address']}||{patient['phone']}\n"
            f"PV1|1|{patient_class}|{location}|{admission_type}|||{physician}|||MED||||1|||{physician}|IN||||||||||||||||||{facility}|||{msg_datetime}"
        )
        
        metadata = {
            "message_type": "ADT",
            "event_type": event_type,
            "message_id": msg_id,
            "patient_mrn": patient["mrn"],
        }
        
        return message, metadata
    
    def generate_orm(self, order_control: str = "NW") -> Tuple[str, Dict]:
        """
        Generate an ORM (Order) message.
        
        Order controls:
        - NW: New Order
        - CA: Cancel Order
        - XO: Change Order
        - SC: Status Changed
        """
        patient = generate_patient()
        msg_datetime = generate_datetime()
        msg_id = generate_message_id()
        order_id = generate_order_id()
        facility = random.choice(FACILITIES)
        application = random.choice(APPLICATIONS)
        physician = random.choice(PHYSICIANS)
        test_key = random.choice(list(LAB_TESTS.keys()))
        test_code = LAB_TESTS[test_key]
        
        message = (
            f"MSH|^~\\&|{application}|{facility}|LAB|{facility}|{msg_datetime}||ORM^O01|{msg_id}|P|2.4\n"
            f"PID|1||{patient['mrn']}^^^{facility}^MR||{patient['last_name']}^{patient['first_name']}^||"
            f"{patient['dob']}|{patient['gender']}\n"
            f"ORC|{order_control}|{order_id}|LAB{order_id}||SC|||{msg_datetime}|||{physician}\n"
            f"OBR|1|{order_id}|LAB{order_id}|{test_code}|||{msg_datetime}||||||||{physician}"
        )
        
        metadata = {
            "message_type": "ORM",
            "order_control": order_control,
            "message_id": msg_id,
            "order_id": order_id,
            "test_type": test_key,
        }
        
        return message, metadata
    
    def generate_oru(self) -> Tuple[str, Dict]:
        """Generate an ORU (Observation Result) message."""
        patient = generate_patient()
        msg_datetime = generate_datetime()
        msg_id = generate_message_id()
        order_id = generate_order_id()
        facility = random.choice(FACILITIES)
        application = random.choice(APPLICATIONS)
        
        test_key = random.choice(["CBC", "BMP", "CMP"])
        test_code = LAB_TESTS[test_key]
        results = LAB_RESULTS[test_key]
        
        # Build OBX segments
        obx_segments = []
        for i, (obs_id, value_type, low, high, units) in enumerate(results, 1):
            # Generate a value (sometimes abnormal)
            if random.random() < 0.2:  # 20% chance of abnormal
                if random.random() < 0.5:
                    value = round(low * random.uniform(0.7, 0.95), 1)
                    flag = "L"
                else:
                    value = round(high * random.uniform(1.05, 1.3), 1)
                    flag = "H"
            else:
                value = round(random.uniform(low, high), 1)
                flag = "N"
            
            ref_range = f"{low}-{high}"
            obx = f"OBX|{i}|{value_type}|{obs_id}||{value}|{units}|{ref_range}|{flag}|||F"
            obx_segments.append(obx)
        
        obx_text = "\n".join(obx_segments)
        
        message = (
            f"MSH|^~\\&|LAB|{facility}|EMR|{facility}|{msg_datetime}||ORU^R01|{msg_id}|P|2.4\n"
            f"PID|1||{patient['mrn']}^^^{facility}^MR||{patient['last_name']}^{patient['first_name']}^||"
            f"{patient['dob']}|{patient['gender']}\n"
            f"OBR|1|{order_id}|LAB{order_id}|{test_code}|||{msg_datetime}\n"
            f"{obx_text}"
        )
        
        metadata = {
            "message_type": "ORU",
            "message_id": msg_id,
            "test_type": test_key,
            "num_observations": len(results),
        }
        
        return message, metadata
    
    def generate_siu(self, action_code: str = "S12") -> Tuple[str, Dict]:
        """
        Generate an SIU (Scheduling) message.
        
        Action codes:
        - S12: Notification of new appointment booking
        - S13: Notification of appointment rescheduling
        - S14: Notification of appointment modification
        - S15: Notification of appointment cancellation
        """
        patient = generate_patient()
        msg_datetime = generate_datetime()
        msg_id = generate_message_id()
        facility = random.choice(FACILITIES)
        application = random.choice(APPLICATIONS)
        
        appt_id = f"APT{random.randint(100000, 999999)}"
        appt_datetime = generate_datetime(days_back=0)  # Future appointments
        duration = random.choice([15, 30, 45, 60])
        appt_type = random.choice(APPOINTMENT_TYPES)
        resource = random.choice(RESOURCES)
        
        message = (
            f"MSH|^~\\&|{application}|{facility}|SCHEDULING|{facility}|{msg_datetime}||SIU^{action_code}|{msg_id}|P|2.4\n"
            f"SCH|{appt_id}|{appt_id}||||{appt_type}|{appt_type}^{appt_type}|||{duration}|MIN||||||||||{resource}\n"
            f"PID|1||{patient['mrn']}^^^{facility}^MR||{patient['last_name']}^{patient['first_name']}^||"
            f"{patient['dob']}|{patient['gender']}\n"
            f"AIG|1||{resource}||SCHEDULED"
        )
        
        metadata = {
            "message_type": "SIU",
            "action_code": action_code,
            "message_id": msg_id,
            "appointment_id": appt_id,
            "appointment_type": appt_type,
        }
        
        return message, metadata
    
    def generate_vxu(self) -> Tuple[str, Dict]:
        """Generate a VXU (Vaccination Update) message."""
        patient = generate_patient()
        msg_datetime = generate_datetime()
        msg_id = generate_message_id()
        facility = random.choice(FACILITIES)
        application = random.choice(APPLICATIONS)
        
        vaccine_code, manufacturer, lot = random.choice(VACCINES)
        admin_datetime = generate_datetime(days_back=7)
        admin_site = random.choice(["LA", "RA", "LT", "RT"])  # Left/Right Arm/Thigh
        dose_number = random.randint(1, 3)
        
        message = (
            f"MSH|^~\\&|{application}|{facility}|IMMUNIZATION|{facility}|{msg_datetime}||VXU^V04|{msg_id}|P|2.5.1\n"
            f"PID|1||{patient['mrn']}^^^{facility}^MR||{patient['last_name']}^{patient['first_name']}^||"
            f"{patient['dob']}|{patient['gender']}\n"
            f"ORC|RE||{generate_order_id()}||CM\n"
            f"RXA|0|1|{admin_datetime}||{vaccine_code}|0.5|mL|{admin_site}|00^New Immunization Record||||||"
            f"{lot}|{manufacturer}|||||CP|A\n"
            f"OBX|1|NM|30973-2^Dose number in series||{dose_number}||||||F"
        )
        
        metadata = {
            "message_type": "VXU",
            "message_id": msg_id,
            "vaccine_manufacturer": manufacturer,
            "lot_number": lot,
            "dose_number": dose_number,
        }
        
        return message, metadata
    
    def generate_batch(
        self, 
        count: int = 10,
        message_types: Optional[List[str]] = None
    ) -> List[Tuple[str, Dict]]:
        """
        Generate a batch of mixed messages.
        
        Args:
            count: Number of messages to generate
            message_types: List of types to include (default: all types)
        
        Returns:
            List of (message, metadata) tuples
        """
        if message_types is None:
            message_types = ["ADT", "ORM", "ORU", "SIU", "VXU"]
        
        generators = {
            "ADT": lambda: self.generate_adt(random.choice(["A01", "A02", "A03", "A04", "A08"])),
            "ORM": lambda: self.generate_orm(random.choice(["NW", "CA", "XO", "SC"])),
            "ORU": self.generate_oru,
            "SIU": lambda: self.generate_siu(random.choice(["S12", "S13", "S14", "S15"])),
            "VXU": self.generate_vxu,
        }
        
        messages = []
        for _ in range(count):
            msg_type = random.choice(message_types)
            if msg_type in generators:
                messages.append(generators[msg_type]())
        
        return messages


# =============================================================================
# File Writers
# =============================================================================

def write_messages_to_files(
    output_dir: str,
    messages: List[Tuple[str, Dict]],
    separate_files: bool = True,
    batch_filename: str = "batch.hl7"
) -> List[str]:
    """
    Write generated messages to files.
    
    Args:
        output_dir: Directory to write files to
        messages: List of (message, metadata) tuples
        separate_files: If True, write each message to a separate file
        batch_filename: Filename for batch mode (when separate_files=False)
    
    Returns:
        List of created file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    created_files = []
    
    if separate_files:
        for i, (message, metadata) in enumerate(messages):
            msg_type = metadata.get("message_type", "UNK").lower()
            event = metadata.get("event_type", metadata.get("action_code", ""))
            if event:
                filename = f"{msg_type}_{event}_{i+1:04d}.hl7"
            else:
                filename = f"{msg_type}_{i+1:04d}.hl7"
            
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w") as f:
                f.write(message)
            created_files.append(filepath)
    else:
        # Write all messages to a single batch file
        filepath = os.path.join(output_dir, batch_filename)
        with open(filepath, "w") as f:
            for message, _ in messages:
                f.write(message)
                f.write("\n")  # Separator between messages
        created_files.append(filepath)
    
    return created_files


def print_summary(messages: List[Tuple[str, Dict]], files: List[str]):
    """Print generation summary."""
    print("=" * 60)
    print("HL7v2 MESSAGE GENERATION SUMMARY")
    print("=" * 60)
    
    type_counts = Counter(m[1].get("message_type", "UNK") for m in messages)
    
    print(f"\nTotal messages: {len(messages)}")
    print("\nBy type:")
    for msg_type, count in sorted(type_counts.items()):
        print(f"  {msg_type}: {count}")
    
    print(f"\nFiles created: {len(files)}")
    if len(files) <= 10:
        for f in files:
            print(f"  - {os.path.basename(f)}")
    else:
        for f in files[:5]:
            print(f"  - {os.path.basename(f)}")
        print(f"  ... and {len(files) - 5} more files")
    
    print("=" * 60)


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate fake HL7v2 messages for testing"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output directory for generated files"
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=20,
        help="Number of messages to generate (default: 20)"
    )
    parser.add_argument(
        "--types", "-t",
        nargs="+",
        choices=["ADT", "ORM", "ORU", "SIU", "VXU"],
        default=None,
        help="Message types to generate (default: all)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Write all messages to a single batch file"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    
    args = parser.parse_args()
    
    print(f"\nGenerating {args.count} HL7v2 messages...")
    
    generator = HL7v2Generator(seed=args.seed)
    messages = generator.generate_batch(count=args.count, message_types=args.types)
    
    files = write_messages_to_files(
        output_dir=args.output,
        messages=messages,
        separate_files=not args.batch
    )
    
    print_summary(messages, files)
    print(f"\nOutput directory: {args.output}")


if __name__ == "__main__":
    main()
