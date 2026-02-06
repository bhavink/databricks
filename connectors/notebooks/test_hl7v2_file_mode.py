# Databricks notebook source
# MAGIC %md
# MAGIC # Healthcare Connector - HL7v2 File Mode Test (UC Volumes)
# MAGIC 
# MAGIC This notebook tests the HL7v2 file-based ingestion from **Unity Catalog Volumes**.
# MAGIC 
# MAGIC **Prerequisites**:
# MAGIC - Unity Catalog enabled workspace
# MAGIC - A Volume created in your catalog/schema

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Configuration
# MAGIC 
# MAGIC Update these values to match your UC environment.

# COMMAND ----------

# UC Volume Configuration (VERIFIED WORKING)
CATALOG = "main"
SCHEMA = "default"
VOLUME = "healthcare_data"

# Derived path
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
HL7_PATH = f"{VOLUME_PATH}/hl7v2"

print(f"UC Volume Path: {VOLUME_PATH}")
print(f"HL7v2 Files Path: {HL7_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Create Volume (if needed)
# MAGIC 
# MAGIC Run this cell to create the volume if it doesn't exist.

# COMMAND ----------

# Create volume if it doesn't exist
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")
print(f"✅ Volume ready: {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Download Sample HL7v2 Data (Optional)
# MAGIC 
# MAGIC Download sample HL7v2 messages from public sources.

# COMMAND ----------

import requests
import os

def download_hl7_sample(url: str, filename: str, dest_dir: str) -> bool:
    """Download HL7v2 sample file from URL to UC Volume."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        os.makedirs(dest_dir, exist_ok=True)
        filepath = f"{dest_dir}/{filename}"
        
        with open(filepath, "wb") as f:
            f.write(response.content)
        
        print(f"✅ Downloaded: {filename}")
        return True
    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")
        return False

# Sample HL7v2 URLs from public sources (VERIFIED WORKING)
SAMPLE_URLS = {
    # AWS Samples - HL7 ADT A01
    "adt_a01.hl7": "https://raw.githubusercontent.com/aws-samples/aws-big-data-blog/master/aws-blog-mirth-healthcare-hub/samples/hl7-adt-a01.txt",
    
    # Add your custom URLs:
    # "my_file.hl7": "https://your-source.com/path/to/file.hl7",
}

# Download samples (set to True to download)
DOWNLOAD_SAMPLES = False

if DOWNLOAD_SAMPLES:
    os.makedirs(HL7_PATH, exist_ok=True)
    for filename, url in SAMPLE_URLS.items():
        download_hl7_sample(url, filename, HL7_PATH)
else:
    print("💡 Set DOWNLOAD_SAMPLES = True to download from URLs")
    print("💡 Or add your own URLs to SAMPLE_URLS dictionary")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Download from Custom URL
# MAGIC 
# MAGIC Use this cell to download from any URL:

# COMMAND ----------

# # Download from a specific URL
# url = "https://your-source.com/path/to/hl7file.hl7"
# filename = "custom_message.hl7"
# 
# download_hl7_sample(url, filename, HL7_PATH)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Create Test HL7v2 Files in UC Volume
# MAGIC 
# MAGIC If you don't have external data, we'll create sample files for testing.

# COMMAND ----------

# Sample HL7v2 messages
SAMPLE_ADT_A01 = """MSH|^~\\&|EPIC|HOSPITAL|LABADT|DH|20240115120000||ADT^A01|MSG00001|P|2.4
EVN|A01|20240115120000
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M|||123 MAIN ST^^ANYTOWN^NY^12345||(555)123-4567
PV1|1|I|ICU^101^A|E|||1234567890^SMITH^JANE^^^DR|||MED||||1|||1234567890^SMITH^JANE^^^DR|IN||||||||||||||||||HOSP|||20240115120000"""

SAMPLE_ADT_A02 = """MSH|^~\\&|EPIC|HOSPITAL|LABADT|DH|20240115130000||ADT^A02|MSG00002|P|2.4
EVN|A02|20240115130000
PID|1||MRN789012^^^HOSPITAL^MR||SMITH^JANE^B||19750620|F|||456 OAK AVE^^SOMEWHERE^CA^90210||(555)987-6543
PV1|1|I|MED^202^B|U|||9876543210^JONES^ROBERT^^^DR|||SUR||||1|||9876543210^JONES^ROBERT^^^DR|IN||||||||||||||||||HOSP|||20240115130000"""

SAMPLE_ORM_O01 = """MSH|^~\\&|CPOE|HOSPITAL|LAB|HOSPITAL|20240115140000||ORM^O01|MSG00003|P|2.4
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M
ORC|NW|ORD001|LAB001||SC|||20240115140000|||1234567890^SMITH^JANE^^^DR
OBR|1|ORD001|LAB001|CBC^Complete Blood Count^L|||20240115140000||||||||1234567890^SMITH^JANE^^^DR"""

SAMPLE_ORU_R01 = """MSH|^~\\&|LAB|HOSPITAL|EMR|HOSPITAL|20240115150000||ORU^R01|MSG00004|P|2.4
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M
OBR|1|ORD001|LAB001|CBC^Complete Blood Count^L|||20240115140000
OBX|1|NM|WBC^White Blood Cell Count^L||7.5|10*3/uL|4.5-11.0|N|||F
OBX|2|NM|RBC^Red Blood Cell Count^L||4.8|10*6/uL|4.5-5.5|N|||F
OBX|3|NM|HGB^Hemoglobin^L||14.2|g/dL|13.5-17.5|N|||F"""

# COMMAND ----------

import os

# Create HL7v2 subdirectory in volume
os.makedirs(HL7_PATH, exist_ok=True)

# Write test files directly using Python file I/O (UC Volumes support this)
def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)
    print(f"✅ Created: {path}")

write_file(f"{HL7_PATH}/adt_001.hl7", SAMPLE_ADT_A01)
write_file(f"{HL7_PATH}/adt_002.hl7", SAMPLE_ADT_A02)
write_file(f"{HL7_PATH}/orm_001.hl7", SAMPLE_ORM_O01)
write_file(f"{HL7_PATH}/oru_001.hl7", SAMPLE_ORU_R01)

# Verify files
print(f"\n📂 Files in {HL7_PATH}:")
for f in os.listdir(HL7_PATH):
    print(f"  - {f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. HL7v2 Parser Implementation

# COMMAND ----------

from typing import Optional


def parse_hl7v2_message(message: str) -> Optional[dict]:
    """Parse an HL7v2 message into a structured dictionary."""
    if not message or not message.strip():
        return None
    
    message = message.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line for line in message.strip().split("\n") if line]
    
    if not lines or not lines[0].startswith("MSH"):
        return None
    
    try:
        result = {}
        
        # Parse MSH segment
        msh = parse_msh_segment(message)
        if not msh:
            return None
        
        result.update(msh)
        
        # Extract message type and trigger
        msg_type_parts = msh.get("message_type", "").split("^")
        result["message_type"] = msg_type_parts[0] if msg_type_parts else ""
        result["trigger_event"] = msg_type_parts[1] if len(msg_type_parts) > 1 else ""
        
        # Parse PID segment
        pid = parse_pid_segment(message)
        if pid:
            result.update(pid)
        
        # Parse type-specific segments
        if result["message_type"] == "ADT":
            result.update(_parse_adt_specific(message))
        elif result["message_type"] == "ORM":
            result.update(_parse_orm_specific(message))
        elif result["message_type"] == "ORU":
            result.update(_parse_oru_specific(message))
        
        return result
        
    except Exception:
        return None


def parse_msh_segment(message: str) -> Optional[dict]:
    """Parse MSH (Message Header) segment."""
    lines = message.replace("\r", "\n").split("\n")
    msh_line = None
    for line in lines:
        if line.startswith("MSH"):
            msh_line = line
            break
    
    if not msh_line:
        return None
    
    fields = msh_line.split("|")
    
    return {
        "sending_application": fields[2] if len(fields) > 2 else "",
        "sending_facility": fields[3] if len(fields) > 3 else "",
        "receiving_application": fields[4] if len(fields) > 4 else "",
        "receiving_facility": fields[5] if len(fields) > 5 else "",
        "message_datetime": fields[6] if len(fields) > 6 else "",
        "message_type": fields[8] if len(fields) > 8 else "",
        "message_control_id": fields[9] if len(fields) > 9 else "",
        "processing_id": fields[10] if len(fields) > 10 else "",
        "version_id": fields[11] if len(fields) > 11 else "",
    }


def parse_pid_segment(message: str) -> Optional[dict]:
    """Parse PID (Patient Identification) segment."""
    lines = message.replace("\r", "\n").split("\n")
    pid_line = None
    for line in lines:
        if line.startswith("PID"):
            pid_line = line
            break
    
    if not pid_line:
        return None
    
    fields = pid_line.split("|")
    
    patient_id_field = fields[3] if len(fields) > 3 else ""
    patient_id = patient_id_field.split("^")[0] if patient_id_field else ""
    
    name_field = fields[5] if len(fields) > 5 else ""
    name_parts = name_field.split("^")
    
    return {
        "patient_id": patient_id,
        "patient_name_family": name_parts[0] if name_parts else "",
        "patient_name_given": name_parts[1] if len(name_parts) > 1 else "",
        "date_of_birth": fields[7] if len(fields) > 7 else "",
        "gender": fields[8] if len(fields) > 8 else "",
    }


def _parse_adt_specific(message: str) -> dict:
    """Parse ADT-specific segments."""
    result = {}
    lines = message.replace("\r", "\n").split("\n")
    
    for line in lines:
        if line.startswith("EVN"):
            fields = line.split("|")
            result["event_type_code"] = fields[1] if len(fields) > 1 else ""
            result["event_datetime"] = fields[2] if len(fields) > 2 else ""
        elif line.startswith("PV1"):
            fields = line.split("|")
            result["patient_class"] = fields[2] if len(fields) > 2 else ""
            result["assigned_location"] = fields[3] if len(fields) > 3 else ""
            result["admission_type"] = fields[4] if len(fields) > 4 else ""
    
    return result


def _parse_orm_specific(message: str) -> dict:
    """Parse ORM-specific segments."""
    result = {}
    lines = message.replace("\r", "\n").split("\n")
    
    for line in lines:
        if line.startswith("ORC"):
            fields = line.split("|")
            result["order_control"] = fields[1] if len(fields) > 1 else ""
            result["order_id"] = fields[2] if len(fields) > 2 else ""
            result["filler_order_number"] = fields[3] if len(fields) > 3 else ""
            result["order_status"] = fields[5] if len(fields) > 5 else ""
        elif line.startswith("OBR"):
            fields = line.split("|")
            result["placer_order_number"] = fields[2] if len(fields) > 2 else ""
            result["universal_service_id"] = fields[4] if len(fields) > 4 else ""
    
    return result


def _parse_oru_specific(message: str) -> dict:
    """Parse ORU-specific segments."""
    result = {}
    observations = []
    lines = message.replace("\r", "\n").split("\n")
    
    for line in lines:
        if line.startswith("OBR"):
            fields = line.split("|")
            result["placer_order_number"] = fields[2] if len(fields) > 2 else ""
            result["filler_order_number"] = fields[3] if len(fields) > 3 else ""
            result["universal_service_id"] = fields[4] if len(fields) > 4 else ""
        elif line.startswith("OBX"):
            fields = line.split("|")
            obs = {
                "set_id": fields[1] if len(fields) > 1 else "",
                "value_type": fields[2] if len(fields) > 2 else "",
                "observation_id": fields[3] if len(fields) > 3 else "",
                "observation_value": fields[5] if len(fields) > 5 else "",
                "units": fields[6] if len(fields) > 6 else "",
                "reference_range": fields[7] if len(fields) > 7 else "",
                "abnormal_flags": fields[8] if len(fields) > 8 else "",
                "result_status": fields[11] if len(fields) > 11 else "",
            }
            observations.append(obs)
    
    result["observations"] = observations
    return result

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Read HL7v2 Files from UC Volume
# MAGIC 
# MAGIC Using Spark to read files from the UC Volume path.

# COMMAND ----------

# Method 1: Using Spark binaryFile format (recommended for HL7v2)
files_df = spark.read.format("binaryFile").load(f"{HL7_PATH}/*.hl7")
print(f"📂 Found {files_df.count()} HL7v2 files in UC Volume")
display(files_df.select("path", "length", "modificationTime"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Parse Files and Create Records

# COMMAND ----------

# Parse all files
all_records = []

for row in files_df.collect():
    file_path = row.path
    content = row.content.decode("utf-8", errors="ignore")
    
    parsed = parse_hl7v2_message(content)
    if parsed:
        parsed["_source_file"] = file_path
        all_records.append(parsed)
        print(f"✅ Parsed: {file_path.split('/')[-1]} -> {parsed['message_type']}^{parsed['trigger_event']}")

print(f"\n📊 Total records parsed: {len(all_records)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Create DataFrames by Message Type

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType, ArrayType

# Filter by message type
adt_records = [r for r in all_records if r.get("message_type") == "ADT"]
orm_records = [r for r in all_records if r.get("message_type") == "ORM"]
oru_records = [r for r in all_records if r.get("message_type") == "ORU"]

print(f"ADT Messages: {len(adt_records)}")
print(f"ORM Messages: {len(orm_records)}")
print(f"ORU Messages: {len(oru_records)}")

# COMMAND ----------

# ADT Messages DataFrame
if adt_records:
    adt_schema = StructType([
        StructField("message_control_id", StringType(), True),
        StructField("message_type", StringType(), True),
        StructField("trigger_event", StringType(), True),
        StructField("message_datetime", StringType(), True),
        StructField("sending_facility", StringType(), True),
        StructField("patient_id", StringType(), True),
        StructField("patient_name_family", StringType(), True),
        StructField("patient_name_given", StringType(), True),
        StructField("gender", StringType(), True),
        StructField("date_of_birth", StringType(), True),
        StructField("patient_class", StringType(), True),
        StructField("assigned_location", StringType(), True),
        StructField("_source_file", StringType(), True),
    ])
    
    adt_df = spark.createDataFrame(adt_records, schema=adt_schema)
    print("📋 ADT Messages (Admit/Discharge/Transfer):")
    display(adt_df.select(
        "message_control_id", "trigger_event", "patient_id", 
        "patient_name_family", "patient_name_given", "patient_class", "assigned_location"
    ))

# COMMAND ----------

# ORM Messages DataFrame
if orm_records:
    orm_schema = StructType([
        StructField("message_control_id", StringType(), True),
        StructField("message_type", StringType(), True),
        StructField("trigger_event", StringType(), True),
        StructField("message_datetime", StringType(), True),
        StructField("sending_facility", StringType(), True),
        StructField("patient_id", StringType(), True),
        StructField("order_control", StringType(), True),
        StructField("order_id", StringType(), True),
        StructField("universal_service_id", StringType(), True),
        StructField("_source_file", StringType(), True),
    ])
    
    orm_df = spark.createDataFrame(orm_records, schema=orm_schema)
    print("📋 ORM Messages (Orders):")
    display(orm_df.select(
        "message_control_id", "patient_id", "order_control", "order_id", "universal_service_id"
    ))

# COMMAND ----------

# ORU Messages - Lab Results with Observations
if oru_records:
    print("📋 ORU Messages (Lab Results):")
    print("=" * 70)
    
    for record in oru_records:
        print(f"\n🔬 Message: {record['message_control_id']}")
        print(f"   Patient: {record['patient_name_given']} {record['patient_name_family']} (MRN: {record['patient_id']})")
        print(f"   Test: {record.get('universal_service_id', 'N/A')}")
        print(f"   Results:")
        
        for obs in record.get("observations", []):
            status = "✅" if obs.get("abnormal_flags", "N") == "N" else "⚠️"
            print(f"      {status} {obs['observation_id']}: {obs['observation_value']} {obs['units']} (Ref: {obs['reference_range']})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Save Parsed Data to Delta Tables (Optional)
# MAGIC 
# MAGIC Uncomment to save the parsed HL7v2 data as Delta tables.

# COMMAND ----------

# # Uncomment to save as Delta tables
# 
# # ADT Messages
# if adt_records:
#     adt_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.hl7v2_adt_messages")
#     print(f"✅ Saved ADT messages to {CATALOG}.{SCHEMA}.hl7v2_adt_messages")
# 
# # ORM Messages  
# if orm_records:
#     orm_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.hl7v2_orm_messages")
#     print(f"✅ Saved ORM messages to {CATALOG}.{SCHEMA}.hl7v2_orm_messages")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Connector Usage Pattern
# MAGIC 
# MAGIC Here's how to use the Healthcare connector with UC Volumes:

# COMMAND ----------

# Example connector configuration for UC Volumes
example_config = {
    "storage_path": f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}/hl7v2",
    "file_pattern": "*.hl7",
}

print("Healthcare Connector Configuration:")
print("-" * 40)
for k, v in example_config.items():
    print(f"  {k}: {v}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Cleanup (Optional)

# COMMAND ----------

# # Uncomment to clean up test files
# import shutil
# shutil.rmtree(HL7_PATH, ignore_errors=True)
# print(f"✅ Cleaned up: {HL7_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC 
# MAGIC | Test | Status |
# MAGIC |------|--------|
# MAGIC | UC Volume creation | ✅ |
# MAGIC | File creation in Volume | ✅ |
# MAGIC | HL7v2 Parser (ADT) | ✅ |
# MAGIC | HL7v2 Parser (ORM) | ✅ |
# MAGIC | HL7v2 Parser (ORU) | ✅ |
# MAGIC | Spark file reading | ✅ |
# MAGIC | DataFrame creation | ✅ |
# MAGIC 
# MAGIC **Path Format**: `/Volumes/<catalog>/<schema>/<volume>/path/to/files`
# MAGIC 
# MAGIC **Next Steps**:
# MAGIC - Use with real HL7v2 files from your healthcare systems
# MAGIC - Save parsed data to Delta tables for analytics
# MAGIC - Integrate with full Lakeflow connector framework
