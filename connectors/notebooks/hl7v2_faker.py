# Databricks notebook source
# MAGIC %md
# MAGIC # HL7v2 Message Generator (Faker)
# MAGIC 
# MAGIC Generates realistic HL7v2 test messages for ADT, ORM, and ORU message types.
# MAGIC 
# MAGIC **Output**: Files saved to UC Volume at `/Volumes/main/default/healthcare_data/hl7v2/`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# UC Volume Configuration
CATALOG = "main"
SCHEMA = "default"
VOLUME = "healthcare_data"

VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
HL7_PATH = f"{VOLUME_PATH}/hl7v2"

# Number of messages to generate per type
NUM_ADT_MESSAGES = 10
NUM_ORM_MESSAGES = 5
NUM_ORU_MESSAGES = 5

print(f"Output Path: {HL7_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## HL7v2 Message Generator

# COMMAND ----------

import random
import os
from datetime import datetime, timedelta

# Sample data for generating realistic messages
FIRST_NAMES_MALE = ["James", "John", "Robert", "Michael", "William", "David", "Joseph", "Charles", "Thomas", "Daniel"]
FIRST_NAMES_FEMALE = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

FACILITIES = ["MERCY_HOSPITAL", "CITY_MEDICAL", "ST_JOSEPH", "GENERAL_HOSPITAL", "UNIVERSITY_HEALTH"]
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

# Lab test codes
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

# Lab results with reference ranges
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


def generate_mrn():
    """Generate a random MRN."""
    return f"MRN{random.randint(100000, 999999)}"


def generate_message_id():
    """Generate a unique message control ID."""
    return f"MSG{random.randint(10000000, 99999999)}"


def generate_order_id():
    """Generate a unique order ID."""
    return f"ORD{random.randint(100000, 999999)}"


def generate_datetime(days_back=30):
    """Generate a random datetime within the past N days."""
    base = datetime.now() - timedelta(days=random.randint(0, days_back))
    return base.strftime("%Y%m%d%H%M%S")


def generate_dob(min_age=18, max_age=85):
    """Generate a date of birth."""
    age = random.randint(min_age, max_age)
    birth_year = datetime.now().year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    return f"{birth_year}{birth_month:02d}{birth_day:02d}"


def generate_patient():
    """Generate random patient demographics."""
    gender = random.choice(["M", "F"])
    if gender == "M":
        first_name = random.choice(FIRST_NAMES_MALE)
    else:
        first_name = random.choice(FIRST_NAMES_FEMALE)
    
    last_name = random.choice(LAST_NAMES)
    mrn = generate_mrn()
    dob = generate_dob()
    
    return {
        "mrn": mrn,
        "first_name": first_name,
        "last_name": last_name,
        "gender": gender,
        "dob": dob,
    }


def generate_adt_message(event_type="A01"):
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
    
    message = f"""MSH|^~\\&|{application}|{facility}|LABADT|{facility}|{msg_datetime}||ADT^{event_type}|{msg_id}|P|2.4
EVN|{event_type}|{msg_datetime}
PID|1||{patient['mrn']}^^^{facility}^MR||{patient['last_name']}^{patient['first_name']}^||{patient['dob']}|{patient['gender']}|||123 MAIN ST^^ANYTOWN^NY^12345||(555){random.randint(100,999)}-{random.randint(1000,9999)}
PV1|1|{patient_class}|{location}|{admission_type}|||{physician}|||MED||||1|||{physician}|IN||||||||||||||||||{facility}|||{msg_datetime}"""
    
    return message, msg_id, event_type


def generate_orm_message(order_control="NW"):
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
    
    message = f"""MSH|^~\\&|{application}|{facility}|LAB|{facility}|{msg_datetime}||ORM^O01|{msg_id}|P|2.4
PID|1||{patient['mrn']}^^^{facility}^MR||{patient['last_name']}^{patient['first_name']}^||{patient['dob']}|{patient['gender']}
ORC|{order_control}|{order_id}|LAB{order_id}||SC|||{msg_datetime}|||{physician}
OBR|1|{order_id}|LAB{order_id}|{test_code}|||{msg_datetime}||||||||{physician}"""
    
    return message, msg_id, order_control, test_key


def generate_oru_message():
    """Generate an ORU (Observation Result) message."""
    patient = generate_patient()
    msg_datetime = generate_datetime()
    msg_id = generate_message_id()
    order_id = generate_order_id()
    facility = random.choice(FACILITIES)
    application = random.choice(APPLICATIONS)
    
    # Pick a test type that has results defined
    test_key = random.choice(["CBC", "BMP", "CMP"])
    test_code = LAB_TESTS[test_key]
    results = LAB_RESULTS[test_key]
    
    # Build OBX segments
    obx_segments = []
    for i, (obs_id, value_type, low, high, units) in enumerate(results, 1):
        # Generate a value (sometimes abnormal)
        if random.random() < 0.2:  # 20% chance of abnormal
            if random.random() < 0.5:
                value = round(low * random.uniform(0.7, 0.95), 1)  # Low
                flag = "L"
            else:
                value = round(high * random.uniform(1.05, 1.3), 1)  # High
                flag = "H"
        else:
            value = round(random.uniform(low, high), 1)
            flag = "N"
        
        ref_range = f"{low}-{high}"
        obx = f"OBX|{i}|{value_type}|{obs_id}||{value}|{units}|{ref_range}|{flag}|||F"
        obx_segments.append(obx)
    
    obx_text = "\n".join(obx_segments)
    
    message = f"""MSH|^~\\&|LAB|{facility}|EMR|{facility}|{msg_datetime}||ORU^R01|{msg_id}|P|2.4
PID|1||{patient['mrn']}^^^{facility}^MR||{patient['last_name']}^{patient['first_name']}^||{patient['dob']}|{patient['gender']}
OBR|1|{order_id}|LAB{order_id}|{test_code}|||{msg_datetime}
{obx_text}"""
    
    return message, msg_id, test_key, len(results)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Messages

# COMMAND ----------

import os

# Create output directory
os.makedirs(HL7_PATH, exist_ok=True)

generated_files = []

# Generate ADT messages
print("📋 Generating ADT Messages...")
adt_events = ["A01", "A02", "A03", "A04", "A08"]
for i in range(NUM_ADT_MESSAGES):
    event_type = random.choice(adt_events)
    message, msg_id, event = generate_adt_message(event_type)
    filename = f"adt_{event}_{i+1:03d}.hl7"
    filepath = f"{HL7_PATH}/{filename}"
    
    with open(filepath, "w") as f:
        f.write(message)
    
    generated_files.append(("ADT", event, filename))
    print(f"  ✅ ADT^{event}: {filename}")

# Generate ORM messages
print("\n📋 Generating ORM Messages...")
order_controls = ["NW", "CA", "XO", "SC"]
for i in range(NUM_ORM_MESSAGES):
    order_control = random.choice(order_controls)
    message, msg_id, oc, test = generate_orm_message(order_control)
    filename = f"orm_{oc}_{i+1:03d}.hl7"
    filepath = f"{HL7_PATH}/{filename}"
    
    with open(filepath, "w") as f:
        f.write(message)
    
    generated_files.append(("ORM", f"{oc} ({test})", filename))
    print(f"  ✅ ORM^O01 ({oc}): {filename}")

# Generate ORU messages
print("\n📋 Generating ORU Messages...")
for i in range(NUM_ORU_MESSAGES):
    message, msg_id, test, num_results = generate_oru_message()
    filename = f"oru_{test}_{i+1:03d}.hl7"
    filepath = f"{HL7_PATH}/{filename}"
    
    with open(filepath, "w") as f:
        f.write(message)
    
    generated_files.append(("ORU", f"{test} ({num_results} results)", filename))
    print(f"  ✅ ORU^R01 ({test}): {filename}")

print(f"\n🎉 Generated {len(generated_files)} HL7v2 messages!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Show summary
print("=" * 70)
print("GENERATED FILES SUMMARY")
print("=" * 70)
print(f"\n📂 Location: {HL7_PATH}\n")

# Count by type
from collections import Counter
type_counts = Counter(f[0] for f in generated_files)

print("📊 Message Counts:")
for msg_type, count in type_counts.items():
    print(f"   {msg_type}: {count} messages")

print(f"\n📄 Total Files: {len(generated_files)}")

# COMMAND ----------

# List all files
print(f"\n📁 Files in {HL7_PATH}:")
for f in sorted(os.listdir(HL7_PATH)):
    if f.endswith(".hl7"):
        filepath = f"{HL7_PATH}/{f}"
        size = os.path.getsize(filepath)
        print(f"   {f} ({size} bytes)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Preview Generated Messages

# COMMAND ----------

# Preview one of each type
print("=" * 70)
print("SAMPLE ADT MESSAGE")
print("=" * 70)
sample_adt, _, _ = generate_adt_message("A01")
print(sample_adt)

print("\n" + "=" * 70)
print("SAMPLE ORM MESSAGE")
print("=" * 70)
sample_orm, _, _, _ = generate_orm_message("NW")
print(sample_orm)

print("\n" + "=" * 70)
print("SAMPLE ORU MESSAGE (with lab results)")
print("=" * 70)
sample_oru, _, _, _ = generate_oru_message()
print(sample_oru)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC 
# MAGIC Now run the **test_hl7v2_file_mode** notebook to parse these messages!
# MAGIC 
# MAGIC ```python
# MAGIC # In the other notebook, set:
# MAGIC HL7_PATH = "/Volumes/main/default/healthcare_data/hl7v2"
# MAGIC ```
