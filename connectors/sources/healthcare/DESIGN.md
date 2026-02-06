# Lakeflow Healthcare Connector - Design Document

> **Version**: 2.0  
> **Updated**: 2026-02-03  
> **Status**: Phase 3 Complete  

---

## 1. Overview

Healthcare connector supporting two modes:
- **API Mode**: FHIR R4 REST APIs (Epic, Cerner, HAPI FHIR)
- **File Mode**: HL7v2 files from UC Volumes (S3, GCS, ADLS)

### Target Users
- Healthcare data engineers
- Clinical analytics teams

### Use Cases
1. Build patient 360 views from FHIR data
2. Ingest ADT events for bed management
3. Aggregate lab results (ORU) for analytics

---

## 2. Supported Tables

### FHIR Tables (API Mode)

| Table | Resource | Ingestion | Primary Key |
|-------|----------|-----------|-------------|
| `patients` | Patient | cdc | id |
| `encounters` | Encounter | cdc | id |
| `observations` | Observation | append | id |
| `conditions` | Condition | cdc | id |
| `medications` | MedicationRequest | cdc | id |

### HL7v2 Tables (File Mode)

| Table | Message Types | Ingestion | Primary Key | Coverage |
|-------|---------------|-----------|-------------|----------|
| `adt_messages` | ADT^A01-A08 | append | message_control_id | ~40% |
| `orm_messages` | ORM^O01 | append | message_control_id | ~15% |
| `oru_messages` | ORU^R01 | append | message_control_id | ~30% |
| `siu_messages` | SIU^S12-S26 | append | message_control_id | ~8% |
| `vxu_messages` | VXU^V04 | append | message_control_id | ~2% |

**Total HL7v2 Coverage: ~95% of typical hospital traffic**

---

## 3. Configuration

### API Mode (FHIR)

```python
config = {
    "fhir_base_url": "https://fhir.epic.com/R4",
    "auth_type": "oauth2",  # none | api_key | oauth2
    "token_url": "https://fhir.epic.com/oauth2/token",
    "client_id": "{{secrets/scope/client_id}}",
    "client_secret": "{{secrets/scope/client_secret}}"
}
```

### File Mode (HL7v2 from UC Volumes)

```python
# Batch mode (default)
config = {
    "storage_path": "/Volumes/main/default/healthcare_data/hl7v2",
    "file_pattern": "*.hl7"
}

# With batch size control
table_options = {
    "batch_size": "1000",  # Files per batch
    "mode": "batch"
}

# Streaming mode (micro-batches for SDP)
table_options = {
    "mode": "streaming",
    "max_files_per_trigger": "100"
}
```

**UC Volume Path Format**: `/Volumes/<catalog>/<schema>/<volume>/path`

---

## 4. Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `requests` | >=2.28.0 | HTTP client |
| `pyspark` | >=3.5.0 | Spark integration |
| `fhir.resources` | >=7.0.0 | FHIR models (optional) |
| `hl7apy` | >=1.5.4 | HL7v2 parsing |

---

## 5. Files

```
sources/healthcare/
├── lakeflow_connect.py      # Main connector (API + File modes)
├── hl7v2_parser.py          # HL7v2 message parser
├── DESIGN.md                # This file
├── healthcare_api_doc.md    # FHIR API documentation
└── test/
    ├── test_healthcare_lakeflow_connect.py  # FHIR tests
    └── test_hl7v2_parser.py                 # HL7v2 tests

notebooks/
├── test_healthcare_connector.py  # FHIR test notebook
├── test_hl7v2_file_mode.py       # HL7v2 test notebook
└── hl7v2_faker.py                # Generate test HL7v2 messages
```

---

## 6. Build Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: API Documentation | ✅ | `healthcare_api_doc.md` complete |
| Phase 2: FHIR API Mode | ✅ | 5 resources, OAuth2, tested in Databricks |
| Phase 3: HL7v2 File Mode | ✅ | 3 message types, UC Volumes, tested |
| Phase 4: Streaming | ⏳ | Future |
| Phase 5: Documentation | ⏳ | README needed |

---

## 7. Testing

### Local Tests
```bash
cd connectors
source .venv/bin/activate
pytest sources/healthcare/test/ -v
```

### Databricks Tests
1. Upload notebooks to workspace
2. Run `hl7v2_faker.py` to generate test data
3. Run `test_hl7v2_file_mode.py` to parse and validate

---

## 8. Scalability & Error Handling

### HL7v2 File Processing Modes

| Mode | Use Case | Checkpointing |
|------|----------|---------------|
| `batch` | One-time or scheduled loads | Offset-based (last_file) |
| `streaming` | SDP micro-batch | Offset-based + processed_files list |
| `structured_streaming` | Continuous ingestion | Spark-managed (exactly-once) |

### Error Handling Options

| Option | Behavior | Use Case |
|--------|----------|----------|
| `skip` (default) | Log and continue | Development, tolerant pipelines |
| `fail` | Raise exception | Strict data quality |
| `dead_letter` | Write failures to path | Production with review queue |

```python
# Production configuration with dead letter queue
table_options = {
    "mode": "batch",
    "batch_size": "5000",
    "error_handling": "dead_letter",
    "dead_letter_path": "/Volumes/catalog/schema/dlq"
}
```

### Checkpointing

**Batch/Streaming Mode** (offset-based):
```python
offset = {
    "last_file": "/path/to/last/processed.hl7",
    "processed_files": ["file1.hl7", "file2.hl7", ...],  # Last N files
    "_stats": {"records_returned": 500, "batch_size_requested": 1000}
}
```

**Structured Streaming Mode** (Spark-managed):
```python
# Checkpointing handled by Spark
table_options = {
    "mode": "structured_streaming",
    "checkpoint_path": "/Volumes/catalog/schema/checkpoints/hl7v2"
}
```

### Distributed Processing Architecture

```
Files in UC Volume
       │
       ▼
┌─────────────────────────────────────┐
│  Spark Executors                    │
│  - Read binaryFile                  │
│  - Parse HL7v2 (UDF)                │
│  - Return {success, data, error}    │
└─────────────────────────────────────┘
       │
       ├──── Success ────► toLocalIterator() ──► Records
       │
       └──── Failure ────► Dead Letter Queue (optional)
```

---

## 9. Batch File Support

The connector handles **batch files** containing multiple HL7v2 messages:

```
# Single file with multiple messages
batch_file.hl7:
  MSH|...|ADT^A01|MSG001|...   ← Message 1 (ADT)
  PID|...
  PV1|...
  MSH|...|ORM^O01|MSG002|...   ← Message 2 (ORM)
  PID|...
  ORC|...
  MSH|...|ORU^R01|MSG003|...   ← Message 3 (ORU)
  ...
```

**Behavior**:
- Each MSH segment starts a new message
- 1 file can produce N records (one per message)
- Messages are filtered by table (ADT → `adt_messages`, etc.)
- Invalid messages in batch are skipped (logged to DLQ if enabled)

**Functions**:
- `split_hl7_batch(content)` → Split file into individual messages
- `parse_hl7v2_file(content)` → Parse all messages in file

---

## 10. Spark Declarative Pipelines (DLT) Integration

### What Works vs What Doesn't

| Approach | Status | Notes |
|----------|--------|-------|
| `%run ../utilities/...` | ❌ | Magic commands not supported |
| `dbutils.import_notebook()` | ❌ | Not supported in pipelines |
| `list(records)` / `.collect()` | ❌ | Anti-pattern: materializes on driver |
| `createDataFrame(collected_list)` | ❌ | Breaks streaming semantics |
| `input_file_name()` | ❌ | Not Unity Catalog compatible |
| `dlt.read("table")` | ❌ | Deprecated API |
| Notebooks as `__init__.py` | ❌ | Blocks Python imports |
| `from utilities.parser import ...` | ✅ | Import from `.py` files |
| Auto Loader (`cloudFiles`) | ✅ | Recommended for file ingestion |
| `_metadata.file_path` | ✅ | Unity Catalog compatible |
| `spark.read.table("catalog.schema.table")` | ✅ | Fully qualified table names |
| `%pip install package` | ✅ | Only allowed magic command |

### Recommended Pipeline Architecture

```
Files in UC Volume
       │
       ▼
Auto Loader (cloudFiles, wholetext=true)
       │
       ▼
Split UDF (split_hl7_batch → ArrayType[String])
       │
       ▼
explode(messages)
       │
       ▼
Parse UDF (parse_hl7v2_message → MapType[String, String])
       │  ├─ Simple fields: direct to MapType
       │  └─ Nested structures: JSON.dumps() → String
       ▼
from_json(nested_field, schema) → Structured Array
       │
       ▼
Streaming Tables (bronze layer)
       │
       ▼
Materialized Views (flattened data)
```

### Handling Nested Structures (Key Pattern)

UDFs can't return complex nested types directly. Use JSON serialization:

```python
# In UDF: Convert list to JSON string
def parse_with_json(message: str) -> dict:
    result = parse_hl7v2_message(message)
    if "observations" in result:
        result["observations"] = json.dumps(result["observations"])
    return result

# In DataFrame: Parse JSON back to array
.withColumn("observations", from_json(col("parsed.observations"), observation_schema))
```

### File Organization for DLT

```
/pipeline_root/
├── transformations/
│   ├── bronze_hl7v2_adt.py    # DLT tables (pure Python)
│   ├── bronze_hl7v2_orm.py
│   └── bronze_hl7v2_oru.py
└── utilities/
    └── hl7v2_parser.py        # Python module (.py, NOT notebook)
```

**Critical**: `utilities/` must contain `.py` files, NOT notebooks. Notebooks cannot be imported.

### Configuration via spark.conf

```python
# In transformation file
STORAGE_PATH = spark.conf.get("healthcare.storage_path", "/Volumes/main/default/healthcare_data/hl7v2")
FILE_PATTERN = spark.conf.get("healthcare.file_pattern", "*.hl7")

# In pipeline settings JSON
{
  "configuration": {
    "healthcare.storage_path": "/Volumes/prod/healthcare/hl7v2",
    "healthcare.file_pattern": "*.hl7"
  }
}
```

---

## 11. Streaming Sources Architecture

### Files vs Event Streaming Comparison

| Aspect | File-Based (Auto Loader) | Event Streaming (Kafka/EventHub) |
|--------|--------------------------|----------------------------------|
| **Message Format** | Batch files (multiple messages) | Single message per event |
| **Batch Splitting** | Required (`split_hl7_batch` UDF) | Not needed (already individual) |
| **Metadata** | `_metadata.file_path`, modification time | `offset`, `partition`, `timestamp` |
| **Checkpointing** | Managed by Auto Loader | Managed by streaming platform |
| **Ordering** | File-level ordering | Partition-level ordering |
| **Replay** | Reprocess files from storage | Replay from offset/sequence |
| **Latency** | Minutes (file arrival + processing) | Seconds (near real-time) |

### Code Changes: Files → Streaming

**What Changes:**

```python
# FILE-BASED (Auto Loader)
raw_data = spark.readStream.format("cloudFiles") \
    .option("cloudFiles.format", "text") \
    .option("wholetext", "true") \
    .load(STORAGE_PATH)

# KAFKA
raw_data = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", SERVERS) \
    .option("subscribe", TOPIC) \
    .load()

# FILE-BASED (needs batch splitting)
.withColumn("messages", split_hl7_batch_udf(col("value")))
.withColumn("message", explode(col("messages")))

# STREAMING (no batch splitting - direct parsing)
.withColumn("hl7_message", col("value").cast("string"))

# FILE-BASED metadata
.withColumn("_source_file", col("_metadata.file_path"))

# KAFKA metadata
.withColumn("kafka_offset", col("offset"))
.withColumn("kafka_partition", col("partition"))
.withColumn("kafka_timestamp", col("timestamp"))
```

**What Stays the Same:**
- HL7 parsing logic (`parse_hl7v2_message`)
- Data quality expectations
- Downstream transformations
- Schema definitions
- Unity Catalog integration

### Streaming Source Patterns

#### Pattern 1: Kafka

```python
@dlt.table(name="bronze_hl7v2_adt_kafka")
def bronze_hl7v2_adt_kafka():
    kafka_stream = spark.readStream.format("kafka") \
        .option("kafka.bootstrap.servers", spark.conf.get("kafka.servers")) \
        .option("subscribe", spark.conf.get("kafka.topic")) \
        .option("startingOffsets", "earliest") \
        .load()
    
    return kafka_stream \
        .withColumn("hl7_message", col("value").cast("string")) \
        .withColumn("parsed", parse_hl7_udf(col("hl7_message"))) \
        .select(col("parsed.*"), col("offset"), col("partition"), col("timestamp"))
```

#### Pattern 2: Azure Event Hubs

```python
kafka_options = {
    "kafka.bootstrap.servers": f"{EH_NAMESPACE}.servicebus.windows.net:9093",
    "subscribe": EH_NAME,
    "kafka.sasl.mechanism": "PLAIN",
    "kafka.security.protocol": "SASL_SSL",
    "kafka.sasl.jaas.config": f'kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required username="$ConnectionString" password="{EH_CONN_STR}";'
}

@dlt.table(name="bronze_hl7v2_adt_eventhub")
def bronze_hl7v2_adt_eventhub():
    return spark.readStream.format("kafka").options(**kafka_options).load() \
        .withColumn("hl7_message", col("value").cast("string")) \
        .withColumn("parsed", parse_hl7_udf(col("hl7_message"))) \
        .select(col("parsed.*"))
```

#### Pattern 3: AWS Kinesis (Recommended: Firehose → S3 → Auto Loader)

```python
@dlt.table(name="bronze_hl7v2_adt")
def bronze_hl7v2_adt():
    # Kinesis Firehose writes to S3 - one message per line (no splitting needed)
    raw_stream = spark.readStream.format("cloudFiles") \
        .option("cloudFiles.format", "text") \
        .option("cloudFiles.useNotifications", "true") \
        .load(spark.conf.get("s3.kinesis.path"))
    
    return raw_stream \
        .withColumn("parsed", parse_hl7_udf(col("value"))) \
        .select(col("parsed.*"), col("_metadata.file_path"))
```

### Streaming Configuration

**Kafka:**
```json
{
  "configuration": {
    "kafka.servers": "broker1:9092,broker2:9092",
    "kafka.topic": "hl7-messages",
    "kafka.consumer.group": "hl7-processor-prod"
  }
}
```

**Azure Event Hubs:**
```json
{
  "configuration": {
    "eventhub.namespace": "mynamespace",
    "eventhub.name": "hl7-messages",
    "eventhub.secretScope": "eventhub-secrets",
    "eventhub.secretKey": "connection-string"
  }
}
```

**AWS Kinesis (via Firehose → S3):**
```json
{
  "configuration": {
    "s3.kinesis.path": "s3://my-bucket/kinesis-firehose/hl7-messages/"
  }
}
```

### Performance Tuning

```python
# Kafka/Event Hubs - control micro-batch size
.option("maxOffsetsPerTrigger", "10000")
.option("minPartitions", "10")
.option("kafka.max.poll.records", "500")
.option("kafka.fetch.max.bytes", "52428800")  # 50MB

# Set trigger interval
@dlt.table(
    spark_conf={"spark.databricks.delta.streaming.trigger.interval": "10 seconds"}
)
```

### When to Use Each Source

| Source | Use When |
|--------|----------|
| **Kafka** | High-throughput, low-latency, exactly-once semantics, existing infrastructure |
| **Azure Event Hubs** | Azure cloud, managed Kafka-compatible, Azure AD integration, auto-scaling |
| **AWS Kinesis** | AWS cloud, managed streaming. **Recommended**: Kinesis → Firehose → S3 → Auto Loader |
| **Auto Loader (Files)** | Source writes to storage, batch processing OK, simplest implementation, historical files |

---

## 12. Custom Connector vs Auto Loader

| Aspect | Custom Lakeflow Connector | Auto Loader + UDFs |
|--------|---------------------------|-------------------|
| Complexity | Higher (custom code) | Lower (native features) |
| Reusability | Connector pattern | UDFs reusable |
| Abstraction | High-level table API | Low-level transforms |
| Maintenance | More custom code | Less custom code |
| Performance | Implementation-dependent | Optimized by Databricks |
| Schema Evolution | Can automate | Manual updates |

**When to use Custom Connector:**
- Multiple pipelines with same source
- Abstract complex parsing logic
- Consistent schema evolution across teams
- Building reusable data products

**When to use Auto Loader + UDFs:**
- Simple, one-off transformations
- Maximum flexibility needed
- Prefer explicit over implicit
- Minimize custom code

---

## 13. Making it a Reusable Asset

### From Project to Product

To transform this connector into a reusable, production-ready asset:

1. **Package the parser as a Python library** (wheel file)
2. **Decouple parsing logic from pipeline code**
3. **Store library in Unity Catalog Volumes**
4. **Use dynamic configuration** (not hardcoded values)
5. **Version and distribute across workspaces**

### Architecture Evolution

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
└── config/
    └── pipeline_config.yaml  # Dynamic configuration
```

### Package Structure

```
hl7_parser/
├── setup.py
├── README.md
├── hl7_parser/
│   ├── __init__.py      # Exports public API
│   ├── parser.py        # Core parsing (pure Python)
│   ├── schemas.py       # Spark schema definitions
│   ├── spark_utils.py   # UDF wrappers
│   └── validators.py    # Validation logic
└── tests/
    └── test_parser.py
```

### Separation of Concerns

**Library Responsibilities:**
- HL7 message parsing (pure Python)
- Schema definitions
- Validation logic
- Error handling

**Pipeline Responsibilities:**
- Data ingestion (Auto Loader/Kafka)
- Configuration management
- Data quality expectations
- Business transformations

### Version Management

```
/Volumes/shared/libraries/hl7_parser/
├── hl7_parser-1.0.0-py3-none-any.whl
├── hl7_parser-1.1.0-py3-none-any.whl  # New features
├── hl7_parser-2.0.0-py3-none-any.whl  # Breaking changes
└── latest -> hl7_parser-2.0.0-py3-none-any.whl
```

### Distribution Strategies

| Strategy | Pros | Best For |
|----------|------|----------|
| **UC Volume** | Centralized, UC access control, cross-workspace | Enterprise sharing |
| **Databricks Repos** | Git integration, CI/CD, code review | Team development |
| **Private PyPI** | Standard Python packaging, dependency mgmt | Enterprise-wide |

### Installation in Pipelines

**Option 1: %pip in notebook**
```python
%pip install /Volumes/shared/libraries/hl7_parser/hl7_parser-1.0.0-py3-none-any.whl
from hl7_parser import split_hl7_batch, parse_hl7v2_message
```

**Option 2: Pipeline libraries (Recommended)**
```json
{
  "libraries": [
    {"whl": "/Volumes/shared/libraries/hl7_parser/hl7_parser-1.0.0-py3-none-any.whl"}
  ]
}
```

### Simplified Pipeline Code (After Packaging)

```python
import dlt
from pyspark.sql.functions import col, explode
from hl7_parser import split_hl7_batch, parse_hl7v2_message
from hl7_parser.spark_utils import get_split_udf, get_parse_udf

split_udf = get_split_udf()
parse_udf = get_parse_udf()

@dlt.table(name="bronze_hl7v2_adt")
def bronze_hl7v2_adt():
    return (
        spark.readStream.format("cloudFiles")
        .load(spark.conf.get("healthcare.storage_path"))
        .withColumn("messages", split_udf(col("value")))
        .withColumn("message", explode(col("messages")))
        .withColumn("parsed", parse_udf(col("message")))
        .select(col("parsed.*"))
    )
```

---

## 14. Known Issues

| Issue | Mitigation |
|-------|------------|
| HAPI FHIR 500 errors | Retry with backoff, skip test if persistent |
| `_sort` not supported | Track offset from last record instead |
| HL7v2 segment variations | Parser handles common segments only |

---

## 13. References

- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [HL7v2 Message Structure](https://hl7-definition.caristix.com/v2/)
- [UC Volumes Documentation](https://docs.databricks.com/en/connect/unity-catalog/volumes.html)
