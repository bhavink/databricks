# Healthcare HL7v2 Ingestion Pipeline

Production-grade Spark Declarative Pipeline (SDP) for ingesting HL7v2 messages from Unity Catalog Volumes (governed cloud storage: S3, ADLS Gen2, GCS).

## Features

### What SDP Handles Automatically
- **Data Optimization** - Liquid Clustering keeps data organized for fast queries
- **File Management** - Auto-compaction, optimal file sizing, no manual maintenance
- **Streaming Ingestion** - Auto Loader discovers new files, handles schema evolution
- **Error Recovery** - Failed records captured in quarantine table, never lost

### What This Pipeline Provides
- **Modern SDP API** (`pyspark.pipelines as dp`)
- **Comprehensive Configuration** via pipeline settings JSON
- **Composite Field Parsing** (PL, XCN, CX, CE, XPN, XAD data types)
- **Data Quality Expectations** (`@dp.expect`, `@dp.expect_or_drop`)
- **Local Testable** parsing logic (no Spark dependency for tests)

## Architecture

```
Unity Catalog Volumes (S3/ADLS/GCS → governed cloud storage)
        │
        ▼ (HL7v2 files: *.hl7)
        │
        ▼
┌───────────────────────────────────────┐
│     Bronze Layer (~95% coverage)      │
│  - Single transformation file         │
│  - Uses pyspark.pipelines API         │
│  - Config-driven behavior             │
└───────────────────────────────────────┘
        │
        ├──► bronze_hl7v2_raw (all parsed messages)
        ├──► bronze_hl7v2_quarantine (failed records)
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
├── config/
│   └── pipeline_settings.json         # Pipeline configuration (copied to extra_settings)
├── transformations/
│   └── bronze_hl7v2.py                # All HL7v2 table definitions
└── tests/
    ├── __init__.py
    ├── test_hl7v2_parser.py           # Local parser tests
    └── sample_data/
        └── batch_mixed.hl7
```

**Note:** All parsing logic is inlined in `bronze_hl7v2.py` because executors cannot access workspace file imports. Schemas are defined within the main transformation file.

## Key Design Patterns

### 1. Modern SDP API

```python
from pyspark import pipelines as dp

@dp.table(
    name="bronze_hl7v2_adt",
    cluster_by=["patient_id", "message_datetime"],
    table_properties={"quality": "bronze"},
)
@dp.expect_or_drop("valid_message_type", "message_type = 'ADT'")
def bronze_hl7v2_adt():
    return (
        spark.read.table("bronze_hl7v2_raw")
        .filter(col("message_type") == "ADT")
    )
```

### 2. Configuration Helper Class

The pipeline uses a `PipelineConfig` class to centralize all settings:

```python
class PipelineConfig:
    def __init__(self):
        self._cache = {}

    def get(self, key: str, default: str = "") -> str:
        if key not in self._cache:
            self._cache[key] = spark.conf.get(key, default)
        return self._cache[key]

    @property
    def clustering_enabled(self) -> bool:
        return self.get_bool("healthcare.clustering.enabled", True)

    def get_cluster_columns(self, table_name: str) -> list:
        cols = self.get(f"healthcare.clustering.{table_name}.columns", "")
        return [c.strip() for c in cols.split(",") if c.strip()]

config = PipelineConfig()
```

### 3. Dynamic Table Properties

```python
_adt_cluster_cols = config.get_cluster_columns("adt") if config.clustering_enabled else None

@dp.table(
    name="bronze_hl7v2_adt",
    table_properties=config.build_table_properties("adt"),
    cluster_by=_adt_cluster_cols,
)
def bronze_hl7v2_adt():
    ...
```

### 4. Auto Loader for Streaming Ingestion

```python
raw_files = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "text")
    .option("wholetext", "true")
    .option("pathGlobFilter", FILE_PATTERN)
    .option("cloudFiles.maxFilesPerTrigger", config.max_files_per_trigger)
    .option("cloudFiles.maxBytesPerTrigger", config.max_bytes_per_trigger)
    .load(STORAGE_PATH)
)
```

## Configuration Parameters

Configuration is read via `spark.conf.get()` from pipeline settings:

### Source Configuration
| Parameter | Description | Default |
|-----------|-------------|---------|
| `healthcare.storage_path` | UC Volume path to HL7v2 files | `/Volumes/main/healthcare/raw_data/hl7v2` |
| `healthcare.file_pattern` | Glob pattern for files | `*.hl7` |
| `healthcare.max_files_per_trigger` | Files per micro-batch | `1000` |
| `healthcare.max_bytes_per_trigger` | Bytes per micro-batch | `1g` |

### Clustering Configuration (SDP Auto-Optimizes)
| Parameter | Description | Default |
|-----------|-------------|---------|
| `healthcare.clustering.enabled` | Enable Liquid Clustering (SDP handles optimization) | `true` |
| `healthcare.clustering.<table>.columns` | Columns to optimize queries for | Per-table defaults |

### Optimization Configuration
| Parameter | Description | Default |
|-----------|-------------|---------|
| `healthcare.optimization.auto_optimize` | Enable auto-optimization | `true` |
| `healthcare.optimization.optimize_write` | Enable optimized writes | `true` |
| `healthcare.optimization.auto_compact` | Enable auto-compaction | `true` |

### Quality Configuration
| Parameter | Description | Default |
|-----------|-------------|---------|
| `healthcare.quality.enable_expectations` | Enable data quality checks | `true` |
| `healthcare.quality.quarantine_invalid_records` | Route bad records to quarantine | `true` |

## Tables Created

### Core Tables (11)

| Table | HL7v2 Type | Cluster By | Description |
|-------|------------|-----------|-------------|
| `bronze_hl7v2_raw` | All | `message_type, _ingestion_timestamp` | All parsed messages |
| `bronze_hl7v2_quarantine` | Failed | `_ingestion_timestamp, message_type` | Invalid/failed records |
| `bronze_hl7v2_adt` | ADT | `patient_id, message_datetime` | Patient events |
| `bronze_hl7v2_orm` | ORM | `patient_id, order_datetime` | Orders |
| `bronze_hl7v2_oru` | ORU | `patient_id, message_datetime` | Lab results |
| `bronze_hl7v2_oru_observations` | ORU | `patient_id, observation_datetime` | Flattened observations |
| `bronze_hl7v2_siu` | SIU | `patient_id, appointment_start_datetime` | Scheduling |
| `bronze_hl7v2_siu_resources` | SIU | `patient_id, start_datetime` | Appointment resources |
| `bronze_hl7v2_vxu` | VXU | `patient_id, message_datetime` | Vaccinations |
| `bronze_hl7v2_vxu_vaccinations` | VXU | `patient_id, administration_start_datetime` | Flattened vaccinations |

## Data Quality Expectations

All tables use SDP expectations for data quality:

```python
# Required fields (drop if missing)
@dp.expect_or_drop("valid_message_control_id", "message_control_id IS NOT NULL AND message_control_id != ''")

# Recommended fields (log warning)
@dp.expect("has_patient_id", "patient_id IS NOT NULL AND patient_id != ''")
```

## Testing

### Local Parser Tests

Run tests without Spark dependency:

```bash
cd pipelines/healthcare_ingestion
python -m pytest tests/test_hl7v2_parser.py -v
```

### Test Coverage

1. **Composite Field Parsers** - PL, XCN, CX, CE, XPN, XAD parsing
2. **Batch Splitting** - Multi-message file handling
3. **Message Type Parsers** - ADT, ORU, ORM, SIU, VXU
4. **Edge Cases** - Empty, malformed, minimal messages

## Deployment

### Using Databricks Asset Bundles (Recommended)

```bash
# Validate bundle
databricks bundle validate

# Deploy to dev
databricks bundle deploy -t dev

# Run pipeline
databricks bundle run healthcare_hl7v2_pipeline -t dev
```

### Using MCP Tools (Manual)

```python
# Upload files
upload_folder(
    local_folder="./pipelines/healthcare_ingestion",
    workspace_folder="/Workspace/Users/email@example.com/healthcare_ingestion"
)

# Create/update pipeline
create_or_update_pipeline(
    name="healthcare_hl7v2_bronze",
    root_path="/Workspace/Users/email@example.com/healthcare_ingestion",
    catalog="main",
    schema="healthcare",
    workspace_file_paths=[
        "/Workspace/Users/email@example.com/healthcare_ingestion/transformations/bronze_hl7v2.py"
    ],
    start_run=True,
    wait_for_completion=True
)
```

## References

- [Spark Declarative Pipelines](https://docs.databricks.com/en/ldp/)
- [Python Development](https://docs.databricks.com/en/ldp/developer/python-dev)
- [Liquid Clustering](https://docs.databricks.com/en/delta/clustering)
- [Data Quality Expectations](https://docs.databricks.com/en/ldp/expectations)
