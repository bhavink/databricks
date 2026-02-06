# Healthcare HL7v2 Connector - Design Document

> **Version**: 6.0  
> **Updated**: 2026-02-04  

---

## 1. Overview

This repository provides **production-grade message ingestion connectors** for Databricks using Spark Declarative Pipelines (SDP). Each connector handles a specific message format, parsing complex structures into queryable Delta tables.

### Current Connector

| Format | Domain | Status | Description |
|--------|--------|--------|-------------|
| **HL7v2** | Healthcare | Production | Patient events, lab results, orders, scheduling, vaccinations |

The architecture supports adding new message format connectors following the same patterns.

### Key Features

- **Modern SDP API** (`pyspark.pipelines as dp`) for 2025+ best practices
- **Liquid Clustering** for optimal query performance
- **Configuration-Driven** with `PipelineConfig` helper pattern
- **Composite Field Parsing** for complex nested data types
- **Data Quality Expectations** for validation
- **Quarantine Tables** for failed records
- **Local Testable** parsing logic (no Spark dependency)

---

## 2. Architecture

### Project Structure

```
connectors/
├── DESIGN.md                    # This file
├── databricks.yml               # Asset Bundle config (multi-target)
├── requirements.txt             # Python dependencies
├── .gitignore
│
├── data_generation/             # Test data generators
│   ├── __init__.py
│   └── hl7v2_faker.py           # HL7v2 message generator
│
└── pipelines/                   # SDP Pipelines
    └── healthcare_ingestion/    # HL7v2 connector
        ├── README.md
        ├── config/
        │   └── pipeline_settings.json
        ├── transformations/
        │   └── bronze_hl7v2.py
        └── tests/
            ├── test_hl7v2_parser.py
            └── sample_data/
```

### Pipeline Data Flow Pattern

Each connector follows this medallion architecture pattern:

```
Unity Catalog Volumes (governed cloud storage: S3, ADLS Gen2, GCS)
       │
       ▼
Auto Loader (cloudFiles, wholetext=true)
       │
       ▼
split_batch_udf() → ArrayType[String]
       │
       ▼
explode(messages) → One row per message
       │
       ▼
parse_message_udf() → Structured fields (with composite parsing)
       │
       ├───────────────────────┐
       ▼                       ▼
bronze_<format>_raw       bronze_<format>_quarantine
  (all messages)            (failed records)
       │
       ├──────┬──────┬──────┐
       ▼      ▼      ▼      ▼
  Type-specific tables (filtered by message type)
       │
       ▼
  Flattened tables (one row per nested record)
```

---

## 3. Unity Catalog Volumes

Unity Catalog Volumes provide **governed access to cloud object storage** (S3, ADLS Gen2, GCS). They are NOT a separate storage system - they're a governance layer on top of your existing cloud storage.

### Why Use UC Volumes?

| Feature | Benefit |
|---------|---------|
| **Governed Access** | Fine-grained permissions via Unity Catalog |
| **Cloud Agnostic** | Same `/Volumes/...` path works on AWS, Azure, GCP |
| **Audit Logging** | Track who accessed what data |
| **Lineage** | Automatic data lineage tracking |
| **Credential Passthrough** | No need to manage storage credentials in code |

### Volume Types

| Type | Use Case | Storage |
|------|----------|---------|
| **Managed** | Pipeline outputs, internal data | Databricks-managed location |
| **External** | Landing zones, external data feeds | Your cloud storage bucket |

### Path Format

```
/Volumes/<catalog>/<schema>/<volume>/<path>

# Example:
/Volumes/main/healthcare/raw_data/hl7v2/           # HL7v2 landing zone
```

### Creating a Volume (External)

```sql
-- Create external volume pointing to S3/ADLS/GCS
CREATE EXTERNAL VOLUME main.healthcare.raw_data
LOCATION 's3://my-bucket/healthcare/raw/'
COMMENT 'Landing zone for healthcare messages';

-- Or Azure
LOCATION 'abfss://container@storageaccount.dfs.core.windows.net/healthcare/raw/'

-- Or GCS
LOCATION 'gs://my-bucket/healthcare/raw/'
```

### In Pipeline Code

```python
# Read from volume (cloud-agnostic path)
STORAGE_PATH = "/Volumes/main/healthcare/raw_data/hl7v2"

raw_files = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "text")
    .load(STORAGE_PATH)  # Auto Loader handles S3/ADLS/GCS
)
```

---

## 4. Connector Design Pattern

### Configuration Helper Class

Each connector uses a `PipelineConfig` class for centralized settings:

```python
class PipelineConfig:
    """Centralized configuration reader with caching."""

    def __init__(self):
        self._cache = {}

    def get(self, key: str, default: str = "") -> str:
        """Get config value with caching."""
        if key not in self._cache:
            self._cache[key] = spark.conf.get(key, default)
        return self._cache[key]

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self.get(key, str(default).lower()) == "true"

    def get_int(self, key: str, default: int = 0) -> int:
        return int(self.get(key, str(default)))

    def get_list(self, key: str, default: str = "") -> list:
        val = self.get(key, default)
        return [x.strip() for x in val.split(",") if x.strip()]

    # Feature flags
    @property
    def clustering_enabled(self) -> bool:
        return self.get_bool("<prefix>.clustering.enabled", True)

    @property
    def auto_optimize(self) -> bool:
        return self.get_bool("<prefix>.optimization.auto_optimize", True)

    # Dynamic table properties
    def build_table_properties(self, table_name: str, quality: str = "bronze") -> dict:
        props = {"quality": quality}
        if self.auto_optimize:
            props["pipelines.autoOptimize.managed"] = "true"
        # Note: Z-order and Liquid Clustering are mutually exclusive
        if not self.clustering_enabled:
            cluster_cols = self.get_cluster_columns(table_name)
            if cluster_cols:
                props["pipelines.autoOptimize.zOrderCols"] = ",".join(cluster_cols)
        return props

    def get_cluster_columns(self, table_name: str) -> list:
        return self.get_list(f"<prefix>.clustering.{table_name}.columns")

config = PipelineConfig()
```

### Dynamic Table Definitions

Tables are defined with configurable clustering:

```python
# Pre-compute clustering columns (must be outside function)
_table_cluster_cols = config.get_cluster_columns("table_name") if config.clustering_enabled else None

@dp.table(
    name="bronze_<format>_<type>",
    comment="Description of table",
    table_properties=config.build_table_properties("table_name"),
    cluster_by=_table_cluster_cols,  # None disables clustering
)
@dp.expect_or_drop("valid_id", "message_id IS NOT NULL")
@dp.expect("has_required_field", "required_field IS NOT NULL")
def bronze_table():
    return (
        spark.read.table("bronze_<format>_raw")
        .filter(col("message_type") == "TYPE")
    )
```

### Inlined UDF Pattern

**Critical**: All parsing logic must be inlined in UDFs because executors cannot access workspace file imports.

```python
def parse_message(raw_message: str) -> dict:
    """
    Parse raw message into structured fields.
    
    ALL PARSING LOGIC MUST BE DEFINED INSIDE THIS FUNCTION.
    Executors cannot access imports from workspace files.
    """
    # Define helper functions inside
    def parse_composite_field(value: str) -> dict:
        # parsing logic here
        pass

    # Main parsing logic
    try:
        # ... parse message ...
        return {"field1": value1, "field2": value2, "_parse_error": None}
    except Exception as e:
        return {"_parse_error": str(e), "_raw_message_full": raw_message}

parse_message_udf = udf(parse_message, result_schema)
```

### UDF Optimization: Regular vs Pandas UDF

When processing messages at scale, you can choose between regular Python UDFs and Arrow-optimized Pandas UDFs.

#### Comparison

| Aspect | Regular UDF | Pandas UDF (Arrow) |
|--------|-------------|-------------------|
| **Serialization** | Pickle (slower) | Apache Arrow (faster) |
| **Processing** | Row-by-row | Batch/vectorized |
| **Best for** | Complex parsing, nested schemas | Numeric operations, ML |
| **Complexity** | Simpler return types | Must return `pd.DataFrame` for StructType |

#### Recommendation

| Scenario | Use | Reason |
|----------|-----|--------|
| **< 1M messages/day** | Regular UDF | Simpler, debugging easier |
| **> 1M messages/day** | Consider Pandas UDF | ~20-30% throughput gain from reduced serialization |
| **Numeric/ML workloads** | Always Pandas UDF | 10x+ performance gains |
| **Complex nested output** | Regular UDF | Pandas DataFrame construction is tricky |

For message parsing (HL7v2, SWIFT, etc.), the **core logic is string manipulation** which isn't vectorizable. The gain from Pandas UDF comes purely from **reduced serialization overhead**, not from vectorized computation.

#### How to Convert to Pandas UDF

If your volume justifies it, here's the pattern:

```python
from pyspark.sql.functions import pandas_udf
import pandas as pd

# Define schema (same as regular UDF)
PARSE_SCHEMA = StructType([
    StructField("message_id", StringType()),
    StructField("message_type", StringType()),
    # ... other fields
])

# Pandas UDF - processes batches
@pandas_udf(PARSE_SCHEMA)
def parse_message_pandas(messages: pd.Series) -> pd.DataFrame:
    """
    Arrow-optimized message parser.
    
    ALL PARSING LOGIC MUST STILL BE INLINED.
    The batch is processed as a loop - same parsing, less serialization overhead.
    """
    def parse_single(raw_message: str) -> dict:
        # Same parsing logic as regular UDF
        try:
            # ... parse message ...
            return {"message_id": id, "message_type": type, ...}
        except Exception as e:
            return {"_parse_error": str(e)}
    
    # Process batch - not truly vectorized, but Arrow serialization is faster
    results = [parse_single(msg) for msg in messages]
    return pd.DataFrame(results)

# Usage is identical
df.withColumn("parsed", parse_message_pandas(col("raw_message")))
```

#### Key Points

1. **Inlining still required** - Pandas UDFs have the same executor import limitations
2. **Schema matching** - Return `pd.DataFrame` columns must exactly match `StructType` fields
3. **Memory** - Entire batch loads into memory; tune `spark.sql.execution.arrow.maxRecordsPerBatch`
4. **Testing** - Pandas UDFs are harder to test locally than regular UDFs

#### When NOT to Use Pandas UDF

- Deeply nested output schemas (like HL7v2's 150+ line schema) - DataFrame construction is error-prone
- Development/debugging phase - Regular UDFs have better error messages
- Low volume pipelines - Complexity isn't worth the marginal gain

---

## 5. HL7v2 Connector (Production)

### Supported Message Types

| Type | Coverage | Description | Output Tables |
|------|----------|-------------|---------------|
| ADT | ~40% | Admit/Discharge/Transfer | `bronze_hl7v2_adt` |
| ORM | ~15% | Orders | `bronze_hl7v2_orm` |
| ORU | ~30% | Lab Results | `bronze_hl7v2_oru`, `bronze_hl7v2_oru_observations` |
| SIU | ~8% | Scheduling | `bronze_hl7v2_siu`, `bronze_hl7v2_siu_resources` |
| VXU | ~2% | Vaccinations | `bronze_hl7v2_vxu`, `bronze_hl7v2_vxu_vaccinations` |

**Total Coverage: ~95% of typical hospital HL7v2 traffic**

### Composite Field Parsing

HL7v2 uses composite data types:

| HL7v2 Type | Description | Parsed Columns |
|------------|-------------|----------------|
| **PL** | Person Location | `location_unit`, `location_room`, `location_bed`, `location_facility` |
| **XCN** | Extended Composite Name | `*_id`, `*_family`, `*_given`, `*_degree` |
| **CX** | Extended Composite ID | `*_id`, `*_assigning_authority`, `*_id_type` |
| **CE/CWE** | Coded Element | `*_code`, `*_text`, `*_coding_system` |
| **XPN** | Extended Person Name | `*_family`, `*_given`, `*_middle`, `*_suffix`, `*_prefix` |
| **XAD** | Extended Address | `*_street`, `*_city`, `*_state`, `*_zip`, `*_country` |

### Clustering Strategy

| Table | Cluster By | Rationale |
|-------|-----------|-----------|
| `bronze_hl7v2_raw` | `message_type, _ingestion_timestamp` | Filter by type, time-based |
| `bronze_hl7v2_adt` | `patient_id, message_datetime` | Patient lookups |
| `bronze_hl7v2_oru_observations` | `patient_id, observation_datetime` | Time series queries |

---

## 6. Data Quality Patterns

### Expectation Levels

| Decorator | Behavior | Use Case |
|-----------|----------|----------|
| `@dp.expect(name, constraint)` | Log metric, continue | Soft warnings |
| `@dp.expect_or_drop(name, constraint)` | Drop row silently | Invalid data |
| `@dp.expect_or_fail(name, constraint)` | Fail pipeline | Critical errors |

### Common Expectations

```python
# Required identifier (drop if missing)
@dp.expect_or_drop("valid_id", "message_id IS NOT NULL AND message_id != ''")

# Type validation (drop if wrong type)
@dp.expect_or_drop("valid_type", "message_type = 'EXPECTED'")

# Recommended fields (log only)
@dp.expect("has_patient_id", "patient_id IS NOT NULL")
@dp.expect("has_timestamp", "message_datetime IS NOT NULL")
```

### Quarantine Pattern

Per SDP best practices, failed records go to a quarantine table:

```python
@dp.table(
    name="bronze_<format>_quarantine",
    cluster_by=["_ingestion_timestamp", "message_type"],
)
def quarantine():
    return (
        spark.read.table("bronze_<format>_raw")
        .filter(
            (col("message_id").isNull()) |
            (col("message_id") == "") |
            (col("_parse_error").isNotNull())
        )
    )
```

---

## 7. Configuration Guide

### Pipeline Settings JSON

Each connector has a `config/pipeline_settings.json`:

```json
{
  "<prefix>.storage_path": "/Volumes/catalog/schema/volume/data",
  "<prefix>.file_pattern": "*.msg",

  "<prefix>.max_files_per_trigger": "1000",
  "<prefix>.max_bytes_per_trigger": "1g",

  "<prefix>.clustering.enabled": "true",
  "<prefix>.clustering.raw.columns": "message_type,_ingestion_timestamp",
  "<prefix>.clustering.<table>.columns": "key_field1,key_field2",

  "<prefix>.optimization.auto_optimize": "true",
  "<prefix>.optimization.optimize_write": "true",
  "<prefix>.optimization.auto_compact": "true",

  "<prefix>.quality.enable_expectations": "true",
  "<prefix>.quality.quarantine_invalid_records": "true",

  "<prefix>.tables.<table>.enabled": "true"
}
```

### How SDP Handles Optimization

| What You Do | What SDP Does Automatically |
|-------------|----------------------------|
| **Specify `cluster_by` columns** | Liquid Clustering optimizes data layout, file sizes, and compaction |
| **Define clustering in config** | Pipeline reads config at startup, applies to all tables |
| **Inline UDF logic** | SDP distributes parsing code to executors for parallel processing |
| **Set config at module level** | `spark.conf.get()` values are resolved once at pipeline start |

---

## 8. Testing Strategy

### Local Parser Tests

Each connector has local tests that run without Spark:

```bash
cd pipelines/<connector>_ingestion
python -m pytest tests/test_<format>_parser.py -v
```

### Test Categories

1. **Composite Field Parsers** - Test each data type parser
2. **Batch Splitting** - Test multi-message file handling
3. **Message Type Parsers** - Test each message type
4. **Edge Cases** - Empty, malformed, minimal messages
5. **Error Handling** - Verify quarantine behavior

### Test Data Generation

```bash
# Generate test data
python data_generation/<format>_faker.py \
  --output /Volumes/catalog/schema/volume/<format> \
  --count 100 \
  --types TYPE1 TYPE2 TYPE3
```

---

## 9. Deployment

### Asset Bundles (Recommended)

```bash
# Validate configuration
databricks bundle validate

# Deploy to development
databricks bundle deploy -t dev

# Run pipeline
databricks bundle run <connector>_pipeline -t dev

# Deploy to production
databricks bundle deploy -t prod
```

### Manual Deployment

```bash
# Sync files to workspace
databricks sync \
  --source ./pipelines/<connector>_ingestion \
  --dest /Workspace/Users/email@example.com/<connector>_ingestion

# Create/update pipeline via API
```

---

## 10. Adding New Connectors

### Step 1: Create Folder Structure

```bash
mkdir -p pipelines/<format>_ingestion/{config,transformations,tests/sample_data}
```

### Step 2: Create Pipeline Settings

Copy and adapt `config/pipeline_settings.json` from existing connector.

### Step 3: Create Transformation File

1. Define `PipelineConfig` class with format-specific prefix
2. Implement parsing UDFs with inlined logic
3. Define raw, quarantine, and type-specific tables
4. Add flattened tables for nested arrays

### Step 4: Create Tests

1. Copy parsing functions to test file (for local testing)
2. Add test cases for each parser
3. Add sample data files

### Step 5: Create Data Generator

Add `data_generation/<format>_faker.py` for test data creation.

### Step 6: Update Asset Bundle

Add pipeline to `databricks.yml` resources.

---

## 11. Best Practices Summary

| Area | What SDP Handles For You |
|------|--------------------------|
| **Data Optimization** | Liquid Clustering automatically organizes data for fast queries - just specify `cluster_by` columns |
| **File Management** | Auto-compaction, optimal file sizing, no manual `OPTIMIZE` needed |
| **Streaming Ingestion** | Auto Loader handles incremental file discovery, schema evolution, exactly-once processing |
| **Data Quality** | Built-in expectations (`@dp.expect`) with metrics, alerting, and quarantine patterns |
| **Error Handling** | Quarantine tables capture failed records automatically - no data loss |
| **Configuration** | `spark.conf.get()` enables environment-specific settings without code changes |

### Your Responsibilities

| Area | Best Practice |
|------|---------------|
| **API** | Use modern `pyspark.pipelines as dp` API |
| **Tables** | Use `spark.read.table()` for reading pipeline tables |
| **Parsing** | Single parse pass in raw table, filter downstream by type |
| **UDFs** | Inline all parsing logic (SDP distributes to executors automatically) |
| **Config** | Use `PipelineConfig` class for centralized settings |
| **Testing** | Local tests for parsing logic (no Spark dependency) |
| **Arrays** | Flatten nested arrays to separate tables for easier querying |

---

## 12. References

- [Unity Catalog Volumes](https://docs.databricks.com/en/volumes/) - Governed cloud storage (S3, ADLS, GCS)
- [Spark Declarative Pipelines](https://docs.databricks.com/en/ldp/)
- [Python Development](https://docs.databricks.com/en/ldp/developer/python-dev)
- [Liquid Clustering](https://docs.databricks.com/en/delta/clustering)
- [Data Quality Expectations](https://docs.databricks.com/en/ldp/expectations)
- [Auto Loader](https://docs.databricks.com/en/ingestion/auto-loader/)
- [Asset Bundles](https://docs.databricks.com/en/dev-tools/bundles/)
- [Pandas UDFs (Arrow-optimized)](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.functions.pandas_udf.html)
