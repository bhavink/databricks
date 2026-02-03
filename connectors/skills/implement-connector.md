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
