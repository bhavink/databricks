# Test Connector Skill

## Description

This skill guides testing of a connector implementation against a real source system. Based on [upstream test_and_fix_connector.md](https://github.com/databrickslabs/lakeflow-community-connectors/blob/master/prompts/test_and_fix_connector.md).

## When to Use

- Phase 3 of connector development
- After implementation is complete
- To validate connector works against real source

---

## Instructions

### Goal

Validate the connector by executing test suite, diagnosing failures, and applying targeted fixes until all tests pass.

### Input

- `sources/{connector}/lakeflow_connect.py` (from implement-connector)

### Output

- `sources/{connector}/test/test_{connector}_lakeflow_connect.py`

---

## Test Setup

### Step 1: Create Test Directory

```
sources/{connector}/
├── test/
│   ├── __init__.py
│   └── test_{connector}_lakeflow_connect.py
└── configs/
    └── dev_config.json  # DO NOT COMMIT
```

### Step 2: Create Config File

Create `sources/{connector}/configs/dev_config.json`:

```json
{
  "base_url": "https://api.example.com",
  "auth_type": "api_key",
  "api_key": "YOUR_API_KEY"
}
```

**IMPORTANT**: Remove this file before committing!

### Step 3: Create Test File

```python
# sources/{connector}/test/test_{connector}_lakeflow_connect.py

import pytest
import json
from pathlib import Path
from pyspark.sql.types import StructType

# Import connector
from sources.{connector}.lakeflow_connect import LakeflowConnect


@pytest.fixture
def config():
    """Load test configuration."""
    config_path = Path(__file__).parent.parent / "configs" / "dev_config.json"
    if not config_path.exists():
        pytest.skip("dev_config.json not found - create it with test credentials")
    with open(config_path) as f:
        return json.load(f)


@pytest.fixture
def connector(config):
    """Initialize connector with test config."""
    return LakeflowConnect(config)


class TestListTables:
    """Tests for list_tables() method."""
    
    def test_returns_list(self, connector):
        tables = connector.list_tables()
        assert isinstance(tables, list)
        
    def test_not_empty(self, connector):
        tables = connector.list_tables()
        assert len(tables) > 0
        
    def test_all_strings(self, connector):
        tables = connector.list_tables()
        assert all(isinstance(t, str) for t in tables)


class TestGetTableSchema:
    """Tests for get_table_schema() method."""
    
    def test_returns_structtype(self, connector):
        for table in connector.list_tables():
            schema = connector.get_table_schema(table, {})
            assert isinstance(schema, StructType)
            
    def test_schema_not_empty(self, connector):
        for table in connector.list_tables():
            schema = connector.get_table_schema(table, {})
            assert len(schema.fields) > 0
            
    def test_invalid_table_raises(self, connector):
        with pytest.raises(ValueError):
            connector.get_table_schema("nonexistent_table", {})


class TestReadTableMetadata:
    """Tests for read_table_metadata() method."""
    
    def test_returns_dict(self, connector):
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            assert isinstance(metadata, dict)
            
    def test_has_required_keys(self, connector):
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            assert "primary_keys" in metadata
            assert "ingestion_type" in metadata
            
    def test_valid_ingestion_type(self, connector):
        valid_types = ["snapshot", "cdc", "cdc_with_deletes", "append"]
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            assert metadata["ingestion_type"] in valid_types
            
    def test_cdc_has_cursor(self, connector):
        """CDC types must have cursor_field."""
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            if metadata["ingestion_type"] in ["cdc", "cdc_with_deletes"]:
                assert "cursor_field" in metadata
                assert metadata["cursor_field"] is not None
                
    def test_invalid_table_raises(self, connector):
        with pytest.raises(ValueError):
            connector.read_table_metadata("nonexistent_table", {})


class TestReadTable:
    """Tests for read_table() method."""
    
    def test_returns_tuple(self, connector):
        table = connector.list_tables()[0]
        result = connector.read_table(table, None, {})
        assert isinstance(result, tuple)
        assert len(result) == 2
        
    def test_first_element_is_iterator(self, connector):
        table = connector.list_tables()[0]
        records_iter, _ = connector.read_table(table, None, {})
        # Should be iterable
        records = list(records_iter)
        assert isinstance(records, list)
        
    def test_second_element_is_dict_or_none(self, connector):
        table = connector.list_tables()[0]
        _, offset = connector.read_table(table, None, {})
        assert offset is None or isinstance(offset, dict)
        
    def test_records_are_dicts(self, connector):
        table = connector.list_tables()[0]
        records_iter, _ = connector.read_table(table, None, {})
        records = list(records_iter)
        if records:
            assert all(isinstance(r, dict) for r in records)
            
    def test_invalid_table_raises(self, connector):
        with pytest.raises(ValueError):
            connector.read_table("nonexistent_table", None, {})


class TestIncrementalRead:
    """Tests for incremental read functionality."""
    
    def test_offset_changes(self, connector):
        """Verify offset updates after read."""
        # Find a CDC table
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            if metadata["ingestion_type"] in ["cdc", "append"]:
                # First read
                records1, offset1 = connector.read_table(table, None, {})
                list(records1)  # Consume
                
                if offset1:
                    # Second read should use offset
                    records2, offset2 = connector.read_table(table, offset1, {})
                    list(records2)
                    # Offset should exist
                    assert offset2 is not None
                break


class TestReadTableDeletes:
    """Tests for read_table_deletes() method (if applicable)."""
    
    def test_cdc_with_deletes_has_method(self, connector):
        """Tables with cdc_with_deletes must support read_table_deletes."""
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            if metadata["ingestion_type"] == "cdc_with_deletes":
                # Method should exist and be callable
                assert hasattr(connector, "read_table_deletes")
                result = connector.read_table_deletes(table, None, {})
                assert isinstance(result, tuple)
```

---

## Running Tests

```bash
# Run all tests
pytest sources/{connector}/test/test_{connector}_lakeflow_connect.py -v

# Run specific test class
pytest sources/{connector}/test/test_{connector}_lakeflow_connect.py::TestReadTable -v

# Run with output
pytest sources/{connector}/test/test_{connector}_lakeflow_connect.py -v -s

# Run with coverage
pytest sources/{connector}/test/ --cov=sources/{connector} --cov-report=term-missing
```

---

## Debugging Failures

### Common Issues

| Error | Likely Cause | Fix |
|-------|--------------|-----|
| `ValueError: Table not supported` | Table name mismatch | Check `list_tables()` |
| `KeyError` in metadata | Missing required key | Add `primary_keys`, `cursor_field` |
| `TypeError: not iterable` | `read_table()` return type | Return `(iter([...]), offset)` |
| `Connection refused` | Wrong URL or auth | Check `dev_config.json` |
| `401 Unauthorized` | Bad credentials | Update credentials |
| `429 Too Many Requests` | Rate limiting | Add backoff/retry |
| `500 Server Error` | External server issue | Add retry with backoff; skip test if persistent |
| Empty response from server | Server temporarily unavailable | Use `pytest.skip()` instead of failing |

### Handling Unreliable External Servers

When testing against public APIs (like HAPI FHIR), servers may be temporarily unavailable. Use this pattern:

```python
def test_read_returns_data(self, connector):
    records, offset = connector.read_table("table", None, {})
    records_list = list(records)
    
    # Skip gracefully if external server is having issues
    if not records_list:
        pytest.skip("Server returned no data - may be unavailable")
    
    # Actual assertions only run if we have data
    assert all(isinstance(r, dict) for r in records_list)
```

**Best Practices**:
- Use `pytest.skip()` not `pytest.fail()` for external service issues
- Add clear skip messages explaining why
- Consider `@pytest.mark.integration` to separate from unit tests
- For reliable local testing, use Docker-based services when possible

### Fix Loop

```
1. Run tests
2. Identify failure
3. Check error message
4. Fix implementation
5. Run tests again
6. Repeat until green
```

---

## Cleanup

**Before committing**:

- [ ] Remove `configs/dev_config.json`
- [ ] Add `configs/` to `.gitignore`
- [ ] Ensure no credentials in code

---

## Acceptance Checklist

- [ ] All test classes pass
- [ ] Tests run against real source (not mocked)
- [ ] Incremental sync tested
- [ ] Invalid table handling tested
- [ ] `dev_config.json` removed
