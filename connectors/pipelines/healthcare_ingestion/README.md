# Healthcare HL7v2 Ingestion Pipeline

This pipeline ingests HL7v2 messages from UC Volumes using the Healthcare Lakeflow Connector.

## Architecture

```
UC Volumes (HL7v2 files)
        │
        ▼
┌───────────────────────────────────────┐
│  Healthcare Connector (~95% coverage) │
│  - Batch file support (multi-message) │
│  - Error handling (skip/fail/dlq)     │
│  - Checkpointing                      │
└───────────────────────────────────────┘
        │
        ├──► bronze_hl7v2_adt (ADT messages ~40%)
        ├──► bronze_hl7v2_orm (ORM messages ~15%)
        ├──► bronze_hl7v2_oru (ORU messages ~30%)
        ├──► bronze_hl7v2_siu (SIU messages ~8%)
        └──► bronze_hl7v2_vxu (VXU messages ~2%)
```

## Folder Structure

```
healthcare_ingestion/
├── README.md                           # This file
├── explorations/                       # Ad-hoc exploration notebooks
├── transformations/
│   ├── bronze_hl7v2_adt.py            # ADT messages
│   ├── bronze_hl7v2_orm.py            # ORM messages
│   ├── bronze_hl7v2_oru.py            # ORU messages + observations
│   ├── bronze_hl7v2_siu.py            # SIU messages + resources
│   ├── bronze_hl7v2_vxu.py            # VXU messages + vaccinations
│   └── bronze_hl7v2_all.py            # Alternative: All types in one file
└── utilities/
    ├── __init__.py
    └── healthcare_connector.py         # Lakeflow Connect implementation
```

**IMPORTANT:** After uploading, update `PIPELINE_ROOT` in each transformation notebook to match your workspace path:

```python
PIPELINE_ROOT = "/Workspace/Users/<your-email>/hl7-processor-ldp"
```

## Configuration

Set these parameters in your pipeline configuration:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `hl7v2_source_path` | UC Volume path to HL7v2 files | `/Volumes/main/default/healthcare_data/hl7v2` |
| `file_pattern` | Glob pattern for files | `*.hl7` |
| `batch_size` | Files per micro-batch | `1000` |
| `error_handling` | How to handle errors | `skip` / `fail` / `dead_letter` |
| `dead_letter_path` | Path for failed records | `/Volumes/main/default/healthcare_data/dlq` |

## Usage

### Create DLT Pipeline

1. Go to **Workflows** → **Delta Live Tables** → **Create Pipeline**
2. Configure:
   ```
   Name: healthcare_hl7v2_ingestion
   Source: /Workspace/Users/<you>/healthcare_ingestion/transformations/bronze_hl7v2_all.py
   Target: main.default (or your catalog.schema)
   
   Configuration:
     healthcare.storage_path: /Volumes/main/default/healthcare_data/hl7v2
     healthcare.file_pattern: *.hl7
     healthcare.error_handling: skip
     healthcare.batch_size: 1000
   ```
3. Click **Start**

### Tables Created

The pipeline creates 8 bronze tables:
- `bronze_hl7v2_adt` - ADT messages
- `bronze_hl7v2_orm` - ORM messages
- `bronze_hl7v2_oru` - ORU messages + `bronze_hl7v2_oru_observations` (flattened)
- `bronze_hl7v2_siu` - SIU messages + `bronze_hl7v2_siu_resources` (flattened)
- `bronze_hl7v2_vxu` - VXU messages + `bronze_hl7v2_vxu_vaccinations` (flattened)

## Message Types

| Table | HL7v2 Type | Description | Coverage |
|-------|------------|-------------|----------|
| `bronze_hl7v2_adt` | ADT^A01-A08 | Patient admit, discharge, transfer | ~40% |
| `bronze_hl7v2_oru` | ORU^R01 | Lab results and observations | ~30% |
| `bronze_hl7v2_orm` | ORM^O01 | Lab and procedure orders | ~15% |
| `bronze_hl7v2_siu` | SIU^S12-S26 | Appointment scheduling | ~8% |
| `bronze_hl7v2_vxu` | VXU^V04 | Vaccination/immunization records | ~2% |

**Total Coverage: ~95% of typical hospital HL7v2 traffic**

### Flattened Tables

| Table | Source | Description |
|-------|--------|-------------|
| `bronze_hl7v2_oru_observations` | ORU | One row per OBX observation |
| `bronze_hl7v2_siu_resources` | SIU | One row per appointment resource |
| `bronze_hl7v2_vxu_vaccinations` | VXU | One row per vaccination |

## Error Handling

- **skip**: Log errors, continue processing valid records
- **fail**: Stop pipeline on first error
- **dead_letter**: Write failed records to DLQ path for review

## Incremental Processing

The pipeline uses offset-based checkpointing:
- Tracks `last_file` processed
- Tracks list of `processed_files`
- Resumes from last checkpoint on restart

---

## DLT Best Practices Applied

This pipeline follows Spark Declarative Pipeline best practices:

### What Works

| Pattern | Usage |
|---------|-------|
| Auto Loader (`cloudFiles`) | Streaming file ingestion with `wholetext=true` |
| `_metadata.file_path` | Unity Catalog compatible source tracking |
| UDFs → `MapType` | Parsing returns key-value pairs |
| `from_json()` | Parse nested structures (observations, vaccinations) |
| `explode()` | Flatten arrays to rows |
| `spark.read.table()` | Read upstream tables (not `dlt.read()`) |

### What Doesn't Work (Avoided)

| Anti-Pattern | Alternative |
|--------------|-------------|
| `%run` magic | Import from `.py` files |
| `.collect()` | Pure DataFrame transformations |
| `input_file_name()` | `_metadata.file_path` |
| `dlt.read()` | `spark.read.table("catalog.schema.table")` |
| Notebooks as modules | Pure `.py` files in utilities |

### File Types

- **transformations/*.py** - Pure Python, no magic commands
- **utilities/*.py** - Python modules (NOT notebooks)

### Nested Structure Pattern

```python
# In UDF: Serialize nested arrays to JSON string
result["observations"] = json.dumps(result["observations"])

# In DataFrame: Parse back to structured array
.withColumn("observations", from_json(col("parsed.observations"), schema))
```

---

## Extending to Other Message Formats

To add support for new message types (e.g., CCDA, X12):

1. Create parser in `utilities/` as `.py` file
2. Define schema for message type
3. Create transformation with Auto Loader + UDF pattern
4. Handle nested structures with JSON serialization
5. Add expectations for data quality

---

## Streaming Sources Support

This pipeline can be adapted for event streaming sources:

### Files vs Streaming Comparison

| Aspect | Current (Files) | Streaming (Kafka/EventHub) |
|--------|-----------------|---------------------------|
| Source | Auto Loader (`cloudFiles`) | `kafka` format |
| Batch Splitting | Required (`split_hl7_batch`) | Not needed |
| Metadata | `_metadata.file_path` | `offset`, `partition`, `timestamp` |
| Latency | Minutes | Seconds |

### Adapting for Kafka/Event Hubs

```python
# Replace Auto Loader with Kafka
raw_stream = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", SERVERS) \
    .option("subscribe", TOPIC) \
    .load()

# No batch splitting needed - direct parsing
return raw_stream \
    .withColumn("parsed", parse_hl7_udf(col("value").cast("string"))) \
    .select(col("parsed.*"), col("offset"), col("partition"))
```

### AWS Kinesis (Recommended Pattern)

Use Kinesis → Firehose → S3, then Auto Loader:

```python
# Firehose writes one message per line - no splitting needed
raw_stream = spark.readStream.format("cloudFiles") \
    .option("cloudFiles.format", "text") \
    .option("cloudFiles.useNotifications", "true") \
    .load(S3_KINESIS_PATH)
```

### When to Use Each

| Source | Use When |
|--------|----------|
| **Auto Loader** | Files in storage, batch OK, simplest |
| **Kafka** | Low-latency, existing Kafka infra |
| **Event Hubs** | Azure cloud, managed service |
| **Kinesis** | AWS cloud - use Firehose → S3 pattern |

---

## Making This a Reusable Asset

### From Project to Product

To share this parser across multiple pipelines/workspaces:

**Current (Project-Specific):**
```
/hl7-processor-ldp/
├── transformations/
│   └── bronze_hl7v2_adt.py  # Imports from local utilities/
└── utilities/
    └── hl7v2_parser.py      # Tightly coupled
```

**Reusable (Product):**
```
Unity Catalog Volume:
/Volumes/shared/libraries/hl7_parser/
└── hl7_parser-1.0.0-py3-none-any.whl

Any Pipeline:
├── transformations/
│   └── bronze_hl7v2_adt.py  # Imports from installed package
```

### Steps to Package

1. **Create package structure:**
```
hl7_parser/
├── setup.py
├── hl7_parser/
│   ├── __init__.py
│   ├── parser.py      # Core parsing (pure Python)
│   ├── schemas.py     # Spark schemas
│   └── spark_utils.py # UDF wrappers
└── tests/
```

2. **Build wheel:**
```bash
python setup.py bdist_wheel
# Output: dist/hl7_parser-1.0.0-py3-none-any.whl
```

3. **Upload to UC Volume:**
```bash
databricks fs cp dist/hl7_parser-1.0.0-py3-none-any.whl \
    dbfs:/Volumes/shared/libraries/hl7_parser/hl7_parser-1.0.0-py3-none-any.whl
```

### Installation in Pipelines

**Option 1: Pipeline libraries (Recommended)**
```json
{
  "libraries": [
    {"whl": "/Volumes/shared/libraries/hl7_parser/hl7_parser-1.0.0-py3-none-any.whl"}
  ]
}
```

**Option 2: %pip**
```python
%pip install /Volumes/shared/libraries/hl7_parser/hl7_parser-1.0.0-py3-none-any.whl
from hl7_parser import split_hl7_batch, parse_hl7v2_message
```

### Version Management

```
/Volumes/shared/libraries/hl7_parser/
├── hl7_parser-1.0.0-py3-none-any.whl
├── hl7_parser-1.1.0-py3-none-any.whl  # New features
└── hl7_parser-2.0.0-py3-none-any.whl  # Breaking changes
```
