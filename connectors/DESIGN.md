# Healthcare Connectors - Design Document

> **Version**: 3.1  
> **Updated**: 2026-02-04  

---

## 1. Overview

This repository contains a healthcare data connector for Databricks using **Spark Declarative Pipelines (SDP/DLT)** for HL7v2 message ingestion.

---

## 2. Project Structure

```
connectors/
├── DESIGN.md                    # This file
├── requirements.txt             # Python dependencies
├── .gitignore
│
├── data_generation/             # Test data generation
│   ├── __init__.py
│   └── hl7v2_faker.py           # Pure Python HL7v2 generator (CLI + importable)
│
└── pipelines/                   # Spark Declarative Pipelines (SDP/DLT)
    └── healthcare_ingestion/    # HL7v2 ingestion pipeline
        ├── README.md
        ├── transformations/     # DLT table definitions
        │   └── bronze_hl7v2.py  # Single file for all message types
        ├── utilities/           # Shared modules (workspace files)
        │   ├── __init__.py
        │   └── hl7v2_schemas.py # Schema definitions
        ├── tests/               # Local parser tests
        │   ├── test_hl7v2_parser.py
        │   └── sample_data/
        └── explorations/        # Ad-hoc exploration scripts
```

---

## 3. Key Patterns

| Pattern | Implementation |
|---------|----------------|
| **Pure Python** | No notebook magic commands |
| **Workspace Files** | `sys.path.append()` + `from utilities import ...` |
| **Auto Loader** | `cloudFiles` format for streaming ingestion |
| **Inlined UDFs** | Parsing logic inside UDF definitions |
| **Configuration** | `spark.conf.get()` at module level |

---

## 4. Architecture

```
UC Volumes (HL7v2 files)
       │
       ▼
Auto Loader (cloudFiles, wholetext=true)
       │
       ▼
split_hl7_batch_udf() → ArrayType[String]
       │
       ▼
explode(messages) → One row per message
       │
       ▼
parse_hl7v2_udf() → Structured fields
       │
       ▼
filter(message_type == "ADT") → Per-type tables
       │
       ▼
bronze_hl7v2_adt, bronze_hl7v2_oru, etc.
```

---

## 5. Supported Message Types

| Type | Description | Table |
|------|-------------|-------|
| **ADT** | Admit/Discharge/Transfer | `bronze_hl7v2_adt` |
| **ORM** | Orders | `bronze_hl7v2_orm` |
| **ORU** | Lab Results | `bronze_hl7v2_oru` |
| **SIU** | Scheduling | `bronze_hl7v2_siu` |
| **VXU** | Vaccinations | `bronze_hl7v2_vxu` |

---

## 6. Testing

### Local Parser Tests

```bash
cd pipelines/healthcare_ingestion
python tests/test_hl7v2_parser.py
```

### Generate Test Data

```bash
cd connectors
python data_generation/hl7v2_faker.py \
  --output /Volumes/catalog/schema/volume/hl7v2 \
  --count 50 \
  --types ADT ORU VXU
```

---

## 7. Development Setup

```bash
cd connectors
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
python pipelines/healthcare_ingestion/tests/test_hl7v2_parser.py
```

---

## 8. Deployment

1. Sync code to Databricks workspace using `databricks sync`
2. Create pipeline pointing to `transformations/bronze_hl7v2.py`
3. Configure:
   - `root_path`: Pipeline folder in workspace
   - `catalog/schema`: Target Unity Catalog location
   - Pipeline configuration for storage path, file pattern, etc.

### Pipeline Configuration

```json
{
  "configuration": {
    "healthcare.storage_path": "/Volumes/catalog/schema/volume/hl7v2",
    "healthcare.file_pattern": "*.hl7"
  }
}
```
