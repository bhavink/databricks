# Implement Connector Skill

## Description

This skill guides implementation of the LakeflowConnect interface for a data source. Based on [upstream implement_connector.md](https://github.com/databrickslabs/lakeflow-community-connectors/blob/master/prompts/implement_connector.md).

## When to Use

- Phase 2 of connector development
- After API documentation is complete
- When ready to write implementation code

---

## Instructions

### Goal

Implement Python connector that conforms exactly to the interface defined in `sources/interface/lakeflow_connect.py`.

### Input

- `sources/{connector}/{connector}_api_doc.md` (from understand-source)

### Output

- `sources/{connector}/lakeflow_connect.py`

---

## Implementation Requirements

### Method: `__init__(self, options: dict[str, str])`

```python
def __init__(self, options: dict[str, str]) -> None:
    """
    Initialize connector with configuration.
    
    Args:
        options: Connection parameters from Unity Catalog connection
    
    Raises:
        ValueError: If required options are missing
    """
    # Validate required options
    required = ["base_url", "auth_type"]
    for key in required:
        if key not in options:
            raise ValueError(f"Missing required option: {key}")
    
    # Initialize client
    self.base_url = options["base_url"]
    self.auth_type = options.get("auth_type", "none")
    # ... initialize HTTP client, auth, etc.
```

### Method: `list_tables(self)`

```python
def list_tables(self) -> list[str]:
    """
    Return names of all tables supported by this connector.
    
    Returns:
        List of table names (static or from API)
    """
    return ["table1", "table2", "table3"]
```

### Method: `get_table_schema(self, table_name, table_options)`

```python
def get_table_schema(
    self, 
    table_name: str, 
    table_options: dict[str, str]
) -> StructType:
    """
    Return Spark schema for a table.
    
    Args:
        table_name: Name of the table
        table_options: Additional options for this table
        
    Returns:
        Spark StructType schema
        
    Raises:
        ValueError: If table_name is not supported
    """
    # REQUIRED: Check table exists
    if table_name not in self.list_tables():
        raise ValueError(f"Table '{table_name}' is not supported")
    
    # Return schema (prefer StructType over MapType)
    return SCHEMAS.get(table_name)
```

### Method: `read_table_metadata(self, table_name, table_options)`

```python
def read_table_metadata(
    self, 
    table_name: str, 
    table_options: dict[str, str]
) -> dict:
    """
    Return metadata for ingestion configuration.
    
    Returns:
        {
            "primary_keys": ["id"],
            "cursor_field": "updated_at",  # Required for cdc/cdc_with_deletes
            "ingestion_type": "cdc"  # snapshot|cdc|cdc_with_deletes|append
        }
    """
    # REQUIRED: Check table exists
    if table_name not in self.list_tables():
        raise ValueError(f"Table '{table_name}' is not supported")
    
    return METADATA.get(table_name)
```

### Method: `read_table(self, table_name, start_offset, table_options)`

```python
def read_table(
    self, 
    table_name: str, 
    start_offset: dict, 
    table_options: dict[str, str]
) -> tuple[Iterator[dict], dict]:
    """
    Read records from source.
    
    Args:
        table_name: Table to read
        start_offset: Resume position (None for initial load)
        table_options: Per-table configuration
        
    Returns:
        (iterator of records as dicts, new offset dict)
        
    Important:
        - Do NOT convert JSON based on schema
        - Return raw JSON from API
    """
    # REQUIRED: Check table exists
    if table_name not in self.list_tables():
        raise ValueError(f"Table '{table_name}' is not supported")
    
    records = []
    new_offset = start_offset or {}
    
    # Fetch from API with pagination
    # Handle incremental (use cursor from start_offset)
    # ...
    
    return iter(records), new_offset
```

### Method: `read_table_deletes(self, table_name, start_offset, table_options)`

```python
def read_table_deletes(
    self, 
    table_name: str, 
    start_offset: dict, 
    table_options: dict[str, str]
) -> tuple[Iterator[dict], dict]:
    """
    Read deleted records for CDC delete synchronization.
    
    Required if ingestion_type is 'cdc_with_deletes'.
    
    Returns:
        Records with at minimum primary key fields and cursor field populated.
    """
    # REQUIRED: Check table exists
    if table_name not in self.list_tables():
        raise ValueError(f"Table '{table_name}' is not supported")
    
    # Fetch deleted records from API
    # ...
    
    return iter(deleted_records), new_offset
```

---

## Required Patterns

| Pattern | Example |
|---------|---------|
| Check table exists | `if table_name not in self.list_tables(): raise ValueError(...)` |
| Prefer StructType | `StructType([StructField("id", StringType())])` not `MapType()` |
| Use LongType | `LongType()` not `IntegerType()` |
| None for missing | `{"nested": None}` not `{"nested": {}}` |

---

## Prohibited Patterns

| Pattern | Why |
|---------|-----|
| Mock objects | Tests must use real data |
| `main()` function | Only class methods |
| Schema conversion in `read_table()` | Return raw JSON |
| Hardcoded credentials | Use options from connection |
| Flattening nested fields | Preserve structure |

---

## Schema Definition Example

```python
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, 
    TimestampType, BooleanType, ArrayType
)

SCHEMAS = {
    "users": StructType([
        StructField("id", StringType(), nullable=False),
        StructField("email", StringType(), nullable=True),
        StructField("created_at", TimestampType(), nullable=False),
        StructField("metadata", StructType([
            StructField("source", StringType(), nullable=True),
            StructField("version", LongType(), nullable=True),
        ]), nullable=True),  # Use None, not {} if missing
    ]),
}

METADATA = {
    "users": {
        "primary_keys": ["id"],
        "cursor_field": "updated_at",
        "ingestion_type": "cdc",
    },
}
```

---

## Retry and Backoff Pattern

Implement retry logic for transient network/server errors:

```python
import time
import requests

def read_table(self, table_name, start_offset, table_options):
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API-level errors (e.g., FHIR OperationOutcome)
            if self._is_error_response(data):
                raise requests.RequestException(f"API error: {data}")
            
            # Process and return data
            return iter(records), new_offset
            
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s
                time.sleep(2 ** attempt)
                continue
            # Log and return empty on final failure
            print(f"Error after {max_retries} retries: {e}")
            return iter([]), None
```

**Key Points**:
- Use exponential backoff (2^attempt seconds)
- Set reasonable timeout (30s default)
- Check for API-specific error responses (not just HTTP status)
- Return empty iterator on persistent failure (don't crash pipeline)

---

---

## Spark Declarative Pipelines (DLT) Integration

When building connectors for use with DLT/Lakeflow Declarative Pipelines:

### What DOESN'T Work in DLT

| Anti-Pattern | Issue |
|--------------|-------|
| `%run ../utilities/...` | Magic commands not supported |
| `dbutils.import_notebook()` | Not supported in pipelines |
| `.collect()` / `list(iterator)` | Materializes data on driver (anti-pattern) |
| `createDataFrame(collected_list)` | Breaks streaming semantics |
| `input_file_name()` | Not Unity Catalog compatible |
| `dlt.read("table")` | Deprecated API |
| Notebooks as `__init__.py` | Blocks Python imports |

### What WORKS in DLT

| Pattern | Usage |
|---------|-------|
| `from utilities.parser import func` | Import from `.py` files (NOT notebooks) |
| Auto Loader (`cloudFiles`) | Streaming file ingestion |
| `col("_metadata.file_path")` | Unity Catalog compatible source tracking |
| `spark.read.table("catalog.schema.table")` | Fully qualified table names |
| `%pip install package` | Only allowed magic command |
| UDFs returning `MapType` | For parsing key-value pairs |
| `from_json(col, schema)` | Parse JSON strings to structured arrays |

### Recommended DLT Architecture for File Sources

```
Files (UC Volumes)
       │
       ▼
Auto Loader (cloudFiles, wholetext=true)
       │
       ▼
Split UDF → ArrayType[String]  (batch file support)
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
Streaming Tables (bronze layer)
```

### File Organization for DLT

```
/pipeline_root/
├── transformations/           # DLT table definitions
│   └── bronze_source_type.py  # Pure Python, NO magic commands
└── utilities/                 # Shared modules
    └── parser.py              # MUST be .py file, NOT notebook
```

### Handling Nested Structures (Critical Pattern)

UDFs cannot return complex nested types directly. Use JSON serialization:

```python
# In UDF: Convert nested list to JSON string
def parse_with_json(message: str) -> dict:
    result = parse_message(message)
    if "observations" in result:
        result["observations"] = json.dumps(result["observations"])  # List → String
    return result

# In DataFrame: Parse JSON back to structured array
.withColumn("observations", from_json(col("parsed.observations"), obs_schema))
```

### Configuration via spark.conf

```python
# In transformation file
STORAGE_PATH = spark.conf.get("source.storage_path", "/Volumes/main/default/data")

# In pipeline settings
{ "configuration": { "source.storage_path": "/Volumes/prod/data" } }
```

### Custom Connector vs Auto Loader Decision

| Use Custom Connector When | Use Auto Loader + UDFs When |
|---------------------------|----------------------------|
| Multiple pipelines need same source | Simple, one-off transforms |
| Need to abstract complex parsing | Want maximum flexibility |
| Consistent schema evolution needed | Prefer explicit over implicit |
| Building reusable data product | Minimize custom code |

---

## Streaming Sources Architecture

When building connectors that support event streaming (Kafka, Event Hubs, Kinesis):

### Files vs Event Streaming

| Aspect | File-Based (Auto Loader) | Event Streaming |
|--------|--------------------------|-----------------|
| **Message Format** | Batch files (multiple messages) | Single message per event |
| **Batch Splitting** | Required (`split_batch` UDF + `explode`) | Not needed |
| **Metadata** | `_metadata.file_path` | `offset`, `partition`, `timestamp` |
| **Checkpointing** | Auto Loader managed | Platform managed |
| **Latency** | Minutes | Seconds |

### Code Pattern Differences

**File-Based (needs batch splitting):**
```python
spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "text")
    .option("wholetext", "true")
    .load(STORAGE_PATH)
    .withColumn("messages", split_batch_udf(col("value")))
    .withColumn("message", explode(col("messages")))
    .withColumn("parsed", parse_udf(col("message")))
```

**Event Streaming (direct parsing):**
```python
spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", SERVERS)
    .option("subscribe", TOPIC)
    .load()
    .withColumn("parsed", parse_udf(col("value").cast("string")))
    # No explode needed - messages already individual!
```

### Streaming Metadata

```python
# File-based
.withColumn("_source_file", col("_metadata.file_path"))

# Kafka/Event Hubs
.withColumn("kafka_offset", col("offset"))
.withColumn("kafka_partition", col("partition"))
.withColumn("kafka_timestamp", col("timestamp"))
```

### Streaming Source Patterns

**Kafka:**
```python
spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", spark.conf.get("kafka.servers"))
    .option("subscribe", spark.conf.get("kafka.topic"))
    .option("startingOffsets", "earliest")
    .load()
```

**Azure Event Hubs (Kafka protocol):**
```python
kafka_options = {
    "kafka.bootstrap.servers": f"{NAMESPACE}.servicebus.windows.net:9093",
    "subscribe": TOPIC,
    "kafka.sasl.mechanism": "PLAIN",
    "kafka.security.protocol": "SASL_SSL",
    "kafka.sasl.jaas.config": f'...password="{CONN_STR}";'
}
spark.readStream.format("kafka").options(**kafka_options).load()
```

**AWS Kinesis (Recommended: Firehose → S3 → Auto Loader):**
```python
# Kinesis → Firehose writes one message per line to S3
spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "text")
    .option("cloudFiles.useNotifications", "true")
    .load(S3_KINESIS_PATH)
    # No batch splitting - Firehose already separates messages
```

### When to Use Each Source

| Source | Best For |
|--------|----------|
| **Auto Loader (Files)** | Files in cloud storage, batch OK, simplest implementation, historical data |
| **Kafka** | High-throughput, low-latency, exactly-once semantics, existing Kafka |
| **Azure Event Hubs** | Azure cloud, managed Kafka-compatible, Azure AD integration |
| **AWS Kinesis** | AWS cloud - **Recommended**: Kinesis → Firehose → S3 → Auto Loader |

### Performance Tuning

```python
# Kafka/Event Hubs - control micro-batch size
.option("maxOffsetsPerTrigger", "10000")
.option("minPartitions", "10")
.option("kafka.max.poll.records", "500")

# Set trigger interval
@dlt.table(spark_conf={"spark.databricks.delta.streaming.trigger.interval": "10 seconds"})
```

### Streaming Configuration Examples

**Kafka:**
```json
{ "kafka.servers": "broker1:9092", "kafka.topic": "hl7-messages" }
```

**Event Hubs:**
```json
{ "eventhub.namespace": "ns", "eventhub.name": "hl7", "eventhub.secretScope": "secrets" }
```

**Kinesis (via S3):**
```json
{ "s3.kinesis.path": "s3://bucket/kinesis-firehose/messages/" }
```

---

## Making Connectors Reusable Assets

### From Project to Product

Transform connectors into distributable, production-ready assets:

1. **Package as Python library** (wheel file)
2. **Decouple parsing from pipeline code**
3. **Store in Unity Catalog Volumes**
4. **Use dynamic configuration**
5. **Version and distribute across workspaces**

### Package Structure

```
connector_lib/
├── setup.py
├── README.md
├── connector_lib/
│   ├── __init__.py      # Public API exports
│   ├── parser.py        # Core parsing (pure Python, no Spark)
│   ├── schemas.py       # Spark schema definitions
│   ├── spark_utils.py   # UDF wrappers
│   └── validators.py    # Validation logic
└── tests/
    └── test_parser.py
```

### setup.py Template

```python
from setuptools import setup, find_packages

setup(
    name="connector_lib",
    version="1.0.0",
    description="Connector library for Databricks pipelines",
    packages=find_packages(),
    install_requires=["pyspark>=3.5.0"],
    python_requires=">=3.10",
)
```

### Separation of Concerns

**Library Responsibilities:**
- Parsing logic (pure Python, no Spark dependencies in core)
- Schema definitions
- Validation logic
- Error handling

**Pipeline Responsibilities:**
- Data ingestion (Auto Loader/Kafka)
- Configuration management
- Data quality expectations
- Business transformations

### Build and Deploy

```bash
# Build wheel
cd connector_lib/
python setup.py bdist_wheel
# Output: dist/connector_lib-1.0.0-py3-none-any.whl

# Upload to UC Volume
databricks fs cp \
    dist/connector_lib-1.0.0-py3-none-any.whl \
    dbfs:/Volumes/shared/libraries/connector_lib/connector_lib-1.0.0-py3-none-any.whl
```

### Distribution Strategies

| Strategy | Pros | Best For |
|----------|------|----------|
| **UC Volume** | Centralized, UC access control, cross-workspace | Enterprise sharing |
| **Databricks Repos** | Git integration, CI/CD, code review | Team development |
| **Private PyPI** | Standard Python packaging, dependency mgmt | Enterprise-wide |

### Installation in Pipelines

**Option 1: Pipeline libraries (Recommended)**
```json
{
  "libraries": [
    {"whl": "/Volumes/shared/libraries/connector_lib/connector_lib-1.0.0-py3-none-any.whl"}
  ]
}
```

**Option 2: %pip in notebook**
```python
%pip install /Volumes/shared/libraries/connector_lib/connector_lib-1.0.0-py3-none-any.whl
from connector_lib import parse_message, get_schema
```

### Version Management

```
/Volumes/shared/libraries/connector_lib/
├── connector_lib-1.0.0-py3-none-any.whl
├── connector_lib-1.1.0-py3-none-any.whl  # New features (backward compatible)
├── connector_lib-2.0.0-py3-none-any.whl  # Breaking changes
└── latest -> connector_lib-2.0.0-py3-none-any.whl
```

### Simplified Pipeline After Packaging

```python
import dlt
from pyspark.sql.functions import col, explode
from connector_lib import parse_message
from connector_lib.spark_utils import get_parse_udf

parse_udf = get_parse_udf()

@dlt.table(name="bronze_data")
def bronze_data():
    return (
        spark.readStream.format("cloudFiles")
        .load(spark.conf.get("connector.storage_path"))
        .withColumn("parsed", parse_udf(col("value")))
        .select(col("parsed.*"))
    )
```

### UC Volume Setup (SQL)

```sql
-- Create shared catalog and schema
CREATE CATALOG IF NOT EXISTS shared;
CREATE SCHEMA IF NOT EXISTS shared.libraries;

-- Create volume for libraries
CREATE VOLUME IF NOT EXISTS shared.libraries.python_packages;

-- Grant access
GRANT READ VOLUME ON VOLUME shared.libraries.python_packages TO `data-engineers`;
```

---

## Acceptance Checklist

- [ ] All 5 interface methods implemented
- [ ] Table name validation in each method
- [ ] StructType preferred over MapType
- [ ] LongType preferred over IntegerType
- [ ] No mock objects
- [ ] No main() function
- [ ] No schema conversion in read_table()
- [ ] Proper error handling
- [ ] Retry/backoff for transient errors (max 3 attempts, exponential backoff)

### If Using with DLT (Additional Checks)

- [ ] Utilities are `.py` files (NOT notebooks)
- [ ] No magic commands in transformation files
- [ ] Nested structures use JSON serialization pattern
- [ ] Uses `_metadata.file_path` (not `input_file_name()`)
- [ ] Uses `spark.read.table()` (not `dlt.read()`)
