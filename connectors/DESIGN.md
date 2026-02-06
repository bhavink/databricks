# Lakeflow Community Connectors - Design Document

> **Version**: 2.0  
> **Updated**: 2026-02-03  

---

## 1. Overview

This repository contains custom Lakeflow Community Connectors built on the [upstream framework](https://github.com/databrickslabs/lakeflow-community-connectors).

---

## 2. LakeflowConnect Interface

All connectors implement this interface:

```python
class LakeflowConnect:
    def __init__(self, options: dict) -> None
    def list_tables(self) -> list[str]
    def get_table_schema(self, table_name, table_options) -> StructType
    def read_table_metadata(self, table_name, table_options) -> dict
    def read_table(self, table_name, start_offset, table_options) -> (Iterator, dict)
```

### Ingestion Types

| Type | Description |
|------|-------------|
| `snapshot` | Full reload each time |
| `cdc` | Incremental with upserts |
| `append` | Incremental append-only |

---

## 3. Project Structure

```
connectors/
├── DESIGN.md                    # This file
├── WORKFLOW.md                  # Development workflow
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Package config
│
├── notebooks/                   # Databricks test notebooks
│   ├── test_healthcare_connector.py
│   ├── test_hl7v2_file_mode.py
│   └── hl7v2_faker.py
│
├── sources/
│   ├── interface/               # Base interface
│   │   └── lakeflow_connect.py
│   │
│   └── healthcare/              # Healthcare connector
│       ├── lakeflow_connect.py  # Main implementation
│       ├── hl7v2_parser.py      # HL7v2 parser
│       ├── DESIGN.md
│       └── test/
│
├── skills/                      # Development guides
└── libs/                        # Shared utilities
```

---

## 4. Connectors

| Connector | Status | Modes |
|-----------|--------|-------|
| `healthcare` | ✅ Ready | FHIR API, HL7v2 Files |

---

## 5. Development Setup

```bash
# Create venv
cd connectors
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest sources/healthcare/test/ -v
```

---

## 6. Testing in Databricks

1. Upload notebook from `notebooks/`
2. Configure UC Volume path
3. Run cells

**UC Volume Path**: `/Volumes/<catalog>/<schema>/<volume>/`

---

## 7. Key Patterns

| Pattern | Implementation |
|---------|----------------|
| Retry with backoff | 3 attempts, exponential delay |
| Skip unreliable tests | `pytest.skip()` when server unavailable |
| Mode detection | Check config for `fhir_base_url` vs `storage_path` |
| UC Volumes | Direct file I/O with `/Volumes/` paths |

---

## 8. Spark Declarative Pipelines (DLT) Best Practices

These patterns apply when building connectors for DLT/Lakeflow Declarative Pipelines:

### What DOESN'T Work in DLT

| Anti-Pattern | Issue |
|--------------|-------|
| `%run`, `%sql`, `%md` | Magic commands not supported (except `%pip`) |
| `dbutils.import_notebook()` | Not supported in pipelines |
| `.collect()` / `list(iterator)` | Materializes data on driver memory |
| `createDataFrame(collected_list)` | Breaks streaming semantics |
| `input_file_name()` | Not Unity Catalog compatible |
| `dlt.read("table")` | Deprecated API |
| Notebooks as `__init__.py` | Blocks Python imports |

### What WORKS in DLT

| Pattern | Usage |
|---------|-------|
| `from utilities.parser import func` | Import from `.py` files (not notebooks) |
| Auto Loader (`cloudFiles`) | Streaming file ingestion |
| `col("_metadata.file_path")` | Unity Catalog compatible source tracking |
| `spark.read.table("catalog.schema.table")` | Fully qualified table references |
| `%pip install package` | Only allowed magic command |
| UDFs returning `MapType` | For parsing to key-value pairs |
| `from_json(col, schema)` | Parse JSON strings to structured arrays |

### Recommended Architecture for File-Based Connectors

```
Files (UC Volumes)
       │
       ▼
Auto Loader (cloudFiles, wholetext=true)
       │
       ▼
Split UDF → ArrayType[String]
       │
       ▼
explode(messages) → One row per message
       │
       ▼
Parse UDF → MapType[String, String]
       │  └─ Nested structures: json.dumps() → String
       ▼
from_json(nested_field, schema) → Structured Array
       │
       ▼
Streaming Tables (bronze)
       │
       ▼
Materialized Views (flattened)
```

### File Organization

```
/pipeline_root/
├── transformations/           # DLT table definitions
│   ├── bronze_source_type.py  # Pure Python, no magic commands
│   └── bronze_source_type2.py
└── utilities/                 # Shared modules
    └── parser.py              # MUST be .py file, NOT notebook
```

### Configuration Pattern

```python
# In transformation
STORAGE_PATH = spark.conf.get("source.storage_path", "/default/path")

# In pipeline settings
{ "configuration": { "source.storage_path": "/Volumes/prod/data" } }
```

### Handling Nested Structures

UDFs cannot return complex nested types directly. Use JSON serialization:

```python
# In UDF
result["nested_array"] = json.dumps(result["nested_array"])

# In DataFrame
.withColumn("nested_array", from_json(col("parsed.nested_array"), array_schema))
```

### Custom Connector vs Auto Loader Decision

| Use Custom Connector When | Use Auto Loader + UDFs When |
|---------------------------|----------------------------|
| Multiple pipelines need same source | Simple, one-off transforms |
| Need to abstract complex parsing | Want maximum flexibility |
| Consistent schema evolution needed | Prefer explicit over implicit |
| Building reusable data product | Minimize custom code |

---

## 9. Streaming Sources Architecture

### Files vs Event Streaming

| Aspect | File-Based (Auto Loader) | Event Streaming (Kafka/EventHub) |
|--------|--------------------------|----------------------------------|
| **Message Format** | Batch files (multiple messages) | Single message per event |
| **Batch Splitting** | Required (UDF) | Not needed |
| **Metadata** | `_metadata.file_path` | `offset`, `partition`, `timestamp` |
| **Checkpointing** | Auto Loader managed | Platform managed |
| **Latency** | Minutes | Seconds |

### Code Pattern Differences

```python
# FILE-BASED: Needs batch splitting
.withColumn("messages", split_batch_udf(col("value")))
.withColumn("message", explode(col("messages")))
.withColumn("parsed", parse_udf(col("message")))

# STREAMING: Direct parsing (no splitting)
.withColumn("parsed", parse_udf(col("value").cast("string")))
```

### Streaming Source Patterns

**Kafka:**
```python
spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", SERVERS)
    .option("subscribe", TOPIC)
    .load()
```

**Azure Event Hubs (Kafka protocol):**
```python
spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", f"{NAMESPACE}.servicebus.windows.net:9093")
    .option("kafka.sasl.mechanism", "PLAIN")
    .option("kafka.security.protocol", "SASL_SSL")
    .load()
```

**AWS Kinesis (Recommended: Firehose → S3 → Auto Loader):**
```python
spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "text")
    .option("cloudFiles.useNotifications", "true")
    .load(S3_KINESIS_PATH)
```

### When to Use Each Source

| Source | Best For |
|--------|----------|
| **Auto Loader** | Files in cloud storage, batch OK, simplest, historical data |
| **Kafka** | High-throughput, low-latency, exactly-once, existing Kafka |
| **Event Hubs** | Azure cloud, managed Kafka, Azure AD, auto-scaling |
| **Kinesis** | AWS cloud, use Firehose → S3 → Auto Loader pattern |

### Performance Tuning

```python
# Control micro-batch size
.option("maxOffsetsPerTrigger", "10000")
.option("minPartitions", "10")

# Trigger interval
@dlt.table(spark_conf={"spark.databricks.delta.streaming.trigger.interval": "10 seconds"})
```

---

## 10. Making Connectors Reusable Assets

### From Project to Product

Transform connectors into reusable, distributable assets:

1. **Package as Python library** (wheel file)
2. **Decouple parsing from pipeline code**
3. **Store in Unity Catalog Volumes**
4. **Use dynamic configuration**
5. **Version and distribute across workspaces**

### Package Structure

```
connector_lib/
├── setup.py
├── connector_lib/
│   ├── __init__.py      # Public API exports
│   ├── parser.py        # Core parsing (pure Python)
│   ├── schemas.py       # Spark schema definitions
│   ├── spark_utils.py   # UDF wrappers
│   └── validators.py    # Validation logic
└── tests/
```

### Separation of Concerns

| Library | Pipeline |
|---------|----------|
| Parsing logic (pure Python) | Data ingestion |
| Schema definitions | Configuration management |
| Validation | Data quality expectations |
| Error handling | Business transformations |

### Distribution Strategies

| Strategy | Best For |
|----------|----------|
| **UC Volume** | Enterprise sharing, centralized, UC access control |
| **Databricks Repos** | Team development, Git integration, CI/CD |
| **Private PyPI** | Enterprise-wide, standard Python packaging |

### Installation Methods

**Pipeline libraries (Recommended):**
```json
{
  "libraries": [
    {"whl": "/Volumes/shared/libraries/connector-1.0.0-py3-none-any.whl"}
  ]
}
```

**%pip in notebook:**
```python
%pip install /Volumes/shared/libraries/connector-1.0.0-py3-none-any.whl
```

### Version Management

```
/Volumes/shared/libraries/connector/
├── connector-1.0.0-py3-none-any.whl
├── connector-1.1.0-py3-none-any.whl  # New features
├── connector-2.0.0-py3-none-any.whl  # Breaking changes
└── latest -> connector-2.0.0-py3-none-any.whl
```
