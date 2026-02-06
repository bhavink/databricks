# Healthcare HL7v2 Ingestion Pipeline

Spark Declarative Pipeline (SDP) for ingesting HL7v2 messages from UC Volumes.

## Architecture

```
UC Volumes (HL7v2 files)
        │
        ▼
┌───────────────────────────────────────┐
│     Bronze Layer (~95% coverage)      │
│  - Single transformation file         │
│  - Uses pyspark.pipelines API         │
│  - Imports from utilities/ folder     │
└───────────────────────────────────────┘
        │
        ├──► bronze_hl7v2_adt (ADT messages ~40%)
        ├──► bronze_hl7v2_orm (ORM messages ~15%)
        ├──► bronze_hl7v2_oru (ORU messages ~30%)
        │      └──► bronze_hl7v2_oru_observations (flattened)
        ├──► bronze_hl7v2_siu (SIU messages ~8%)
        │      └──► bronze_hl7v2_siu_resources (flattened)
        └──► bronze_hl7v2_vxu (VXU messages ~2%)
               └──► bronze_hl7v2_vxu_vaccinations (flattened)
```

## Folder Structure

```
healthcare_ingestion/
├── README.md                          # This file
├── explorations/                      # Ad-hoc exploration notebooks
│   └── explore_hl7v2_data.py
├── transformations/
│   └── bronze_hl7v2.py               # SINGLE file for all HL7v2 types
└── utilities/
    ├── __init__.py                   # Package marker
    └── hl7v2_schemas.py              # PySpark schema definitions
```

**Note:** All files are pure Python (`.py`), no notebooks required. The parsing logic is inlined in the UDF within `bronze_hl7v2.py` because executors cannot access workspace file imports.

## Key Design Patterns

### 1. Workspace Files Import Pattern

Add the pipeline workspace path to `sys.path`, then import from utilities:

```python
import sys
sys.path.append("/Workspace/Users/<email>/healthcare_ingestion")

from utilities.hl7v2_schemas import SCHEMAS, MESSAGE_TYPES
```

Reference: [Import Python modules from workspace files](https://learn.microsoft.com/en-us/azure/databricks/ldp/import-workspace-files)

### 2. Pipeline Configuration

Use `spark.conf.get()` at module level to read pipeline settings:

```python
STORAGE_PATH = spark.conf.get("healthcare.storage_path", "/Volumes/main/default/healthcare_data/hl7v2")
FILE_PATTERN = spark.conf.get("healthcare.file_pattern", "*.hl7")
```

### 3. Auto Loader for Streaming Ingestion

Use `cloudFiles` format for incremental file processing:

```python
raw_files = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "text")
    .option("wholetext", "true")
    .option("pathGlobFilter", FILE_PATTERN)
    .load(STORAGE_PATH)
)
```

### 4. UDF Registration Pattern

Define functions, then register as UDFs with explicit schemas:

```python
def parse_hl7v2_message(msg: str):
    # parsing logic
    return result

parse_hl7v2_udf = udf(parse_hl7v2_message, StructType([
    StructField("message_control_id", StringType()),
    StructField("message_type", StringType()),
    # ...
]))
```

### 5. DLT Table Decorators

```python
@dlt.table(
    name="bronze_hl7v2_adt",
    comment="Bronze layer for HL7v2 ADT messages",
    table_properties={"quality": "bronze"},
)
@dlt.expect_or_drop("valid_message_type", "message_type = 'ADT'")
@dlt.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
def bronze_hl7v2_adt():
    # ...
```

### 6. Reading Other Pipeline Tables

Use `dlt.read()` to read tables within the same pipeline:

```python
@dlt.table(name="bronze_hl7v2_oru_observations")
def bronze_hl7v2_oru_observations():
    return (
        dlt.read("bronze_hl7v2_oru")
        .filter(col("observations").isNotNull())
        .select(explode(col("observations")).alias("obs"))
        # ...
    )
```

### 7. Pipeline Mode (Triggered vs Continuous)

| Mode | Use Case | Configuration |
|------|----------|---------------|
| **Triggered** | Development, batch processing | `"continuous": false` |
| **Continuous** | Production, near-real-time | `"continuous": true` |

Reference: [Triggered vs. continuous pipeline mode](https://learn.microsoft.com/en-us/azure/databricks/ldp/pipeline-mode)

## Development Workflow

### 1. Local Development (Cursor IDE)

Edit files locally in your IDE:
```
healthcare_ingestion/
├── transformations/bronze_hl7v2.py
└── utilities/
    ├── hl7v2_schemas.py
    └── hl7v2_parser.py
```

### 2. Sync to Workspace

Use Databricks CLI to sync files to your workspace:

```bash
# One-time sync
databricks sync ./healthcare_ingestion /Workspace/Users/<email>/healthcare_ingestion

# Continuous sync during development
databricks sync --watch ./healthcare_ingestion /Workspace/Users/<email>/healthcare_ingestion
```

### 3. Create Pipeline

In Databricks UI, create a new pipeline:

**Pipeline Settings:**
```json
{
  "name": "healthcare_hl7v2_bronze",
  "target": "main.healthcare",
  "development": true,
  "continuous": false,
  "channel": "CURRENT",
  "libraries": [
    {
      "file": {
        "path": "/Workspace/Users/<email>/healthcare_ingestion/transformations/bronze_hl7v2.py"
      }
    }
  ],
  "configuration": {
    "healthcare.storage_path": "/Volumes/main/default/healthcare_data/hl7v2",
    "healthcare.file_pattern": "*.hl7",
    "healthcare.error_handling": "skip",
    "healthcare.batch_size": "1000"
  }
}
```

### 4. Production Pipeline

For production, update the pipeline configuration:

```json
{
  "name": "healthcare_hl7v2_bronze_prod",
  "development": false,
  "continuous": true,
  ...
}
```

## Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `healthcare.storage_path` | UC Volume path to HL7v2 files | `/Volumes/main/default/healthcare_data/hl7v2` |
| `healthcare.file_pattern` | Glob pattern for files | `*.hl7` |
| `healthcare.batch_size` | Files per micro-batch | `1000` |
| `healthcare.error_handling` | Error handling mode | `skip` |

## Tables Created

### Primary Tables (5)

| Table | HL7v2 Type | Description | Coverage |
|-------|------------|-------------|----------|
| `bronze_hl7v2_adt` | ADT^A01-A08 | Patient admit, discharge, transfer | ~40% |
| `bronze_hl7v2_oru` | ORU^R01 | Lab results and observations | ~30% |
| `bronze_hl7v2_orm` | ORM^O01 | Lab and procedure orders | ~15% |
| `bronze_hl7v2_siu` | SIU^S12-S26 | Appointment scheduling | ~8% |
| `bronze_hl7v2_vxu` | VXU^V04 | Vaccination/immunization records | ~2% |

**Total Coverage: ~95% of typical hospital HL7v2 traffic**

### Flattened Tables (3)

| Table | Source | Description |
|-------|--------|-------------|
| `bronze_hl7v2_oru_observations` | ORU | One row per OBX observation |
| `bronze_hl7v2_siu_resources` | SIU | One row per appointment resource |
| `bronze_hl7v2_vxu_vaccinations` | VXU | One row per vaccination |

## Data Quality Expectations

All primary tables include these expectations:

```python
@dp.expect_or_drop("valid_message_type", f"message_type = '{msg_type}'")
@dp.expect_or_drop("has_control_id", "message_control_id IS NOT NULL")
```

## Pure Python Files

DLT/SDP uses pure Python files (`.py`), not notebooks. Key considerations:

1. **`spark` is available at module level**: DLT runtime injects `spark` before executing
2. **`dlt` module available**: Import with `import dlt`
3. **UDF logic must be inlined**: Executors cannot access workspace file imports
4. **No magic commands**: No `%run`, `%pip`, `display()`, etc.
5. **Driver-side imports work**: Schema imports from `utilities/` work on the driver

## Extending the Pipeline

### Adding New Message Types

1. Add schema to `utilities/hl7v2_schemas.py`:
```python
SCHEMAS["MDM"] = StructType([
    StructField("message_control_id", StringType(), nullable=False),
    # ... add fields
])
```

2. Add `"MDM"` to `MESSAGE_TYPES` list in `hl7v2_schemas.py`

3. Add parsing logic to the inlined UDF in `bronze_hl7v2.py`:
```python
elif mt == "MDM":
    # Parse MDM-specific segments (TXA, OBX, etc.)
    for line in lines:
        if line.startswith("TXA"):
            # ...
```

4. The for loop will automatically create `bronze_hl7v2_mdm` table.

### Adding Silver/Gold Layers

Create additional transformation files in `transformations/`:
```
transformations/
├── bronze_hl7v2.py          # Bronze layer
├── silver_hl7v2.py          # Silver layer (cleaned, deduplicated)
└── gold_hl7v2.py            # Gold layer (aggregated, business logic)
```

## References

- [Spark Declarative Pipelines Overview](https://learn.microsoft.com/en-us/azure/databricks/ldp/)
- [Develop pipeline code with Python](https://learn.microsoft.com/en-us/azure/databricks/ldp/developer/python-dev)
- [Import Python modules from workspace files](https://learn.microsoft.com/en-us/azure/databricks/ldp/import-workspace-files)
- [Manage Python dependencies](https://learn.microsoft.com/en-us/azure/databricks/ldp/developer/external-dependencies)
- [Triggered vs. continuous pipeline mode](https://learn.microsoft.com/en-us/azure/databricks/ldp/pipeline-mode)
