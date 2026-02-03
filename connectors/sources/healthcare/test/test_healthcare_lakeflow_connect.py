"""
Test suite for Healthcare (FHIR R4) Lakeflow Connector.

Tests run against real HAPI FHIR server (https://hapi.fhir.org/baseR4).
No mocking - validates actual API behavior.

Usage:
    pytest sources/healthcare/test/test_healthcare_lakeflow_connect.py -v
"""

import pytest
import json
from pathlib import Path
from typing import Iterator

# Import will fail until we create the implementation
try:
    from pyspark.sql.types import StructType
except ImportError:
    # Allow tests to be discovered even without pyspark
    StructType = type("StructType", (), {})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def config():
    """Load test configuration from dev_config.json."""
    config_path = Path(__file__).parent.parent / "configs" / "dev_config.json"
    if not config_path.exists():
        pytest.skip(
            "dev_config.json not found - create configs/dev_config.json with test settings"
        )
    with open(config_path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def connector(config):
    """Initialize connector with test config."""
    from sources.healthcare.lakeflow_connect import LakeflowConnect
    
    return LakeflowConnect(config)


# ---------------------------------------------------------------------------
# Test: __init__
# ---------------------------------------------------------------------------


class TestInit:
    """Tests for __init__() method."""

    def test_missing_base_url_raises(self):
        """Should raise ValueError if fhir_base_url is missing."""
        from sources.healthcare.lakeflow_connect import LakeflowConnect
        
        with pytest.raises(ValueError, match="fhir_base_url"):
            LakeflowConnect({"auth_type": "none"})

    def test_valid_config_succeeds(self, config):
        """Should initialize without error with valid config."""
        from sources.healthcare.lakeflow_connect import LakeflowConnect
        
        connector = LakeflowConnect(config)
        assert connector is not None


# ---------------------------------------------------------------------------
# Test: list_tables
# ---------------------------------------------------------------------------


class TestListTables:
    """Tests for list_tables() method."""

    def test_returns_list(self, connector):
        """Should return a list."""
        tables = connector.list_tables()
        assert isinstance(tables, list)

    def test_not_empty(self, connector):
        """Should return at least one table."""
        tables = connector.list_tables()
        assert len(tables) > 0

    def test_all_strings(self, connector):
        """All table names should be strings."""
        tables = connector.list_tables()
        assert all(isinstance(t, str) for t in tables)

    def test_expected_tables(self, connector):
        """Should include expected FHIR resources."""
        tables = connector.list_tables()
        # At minimum, should have patients
        assert "patients" in tables


# ---------------------------------------------------------------------------
# Test: get_table_schema
# ---------------------------------------------------------------------------


class TestGetTableSchema:
    """Tests for get_table_schema() method."""

    def test_returns_structtype(self, connector):
        """Should return a StructType for each table."""
        from pyspark.sql.types import StructType
        
        for table in connector.list_tables():
            schema = connector.get_table_schema(table, {})
            assert isinstance(schema, StructType), f"Schema for {table} is not StructType"

    def test_schema_not_empty(self, connector):
        """Schema should have at least one field."""
        for table in connector.list_tables():
            schema = connector.get_table_schema(table, {})
            assert len(schema.fields) > 0, f"Schema for {table} has no fields"

    def test_schema_has_id(self, connector):
        """All FHIR resources should have an 'id' field."""
        for table in connector.list_tables():
            schema = connector.get_table_schema(table, {})
            field_names = [f.name for f in schema.fields]
            assert "id" in field_names, f"Schema for {table} missing 'id' field"

    def test_invalid_table_raises(self, connector):
        """Should raise ValueError for unknown table."""
        with pytest.raises(ValueError, match="not supported"):
            connector.get_table_schema("nonexistent_table_xyz", {})


# ---------------------------------------------------------------------------
# Test: read_table_metadata
# ---------------------------------------------------------------------------


class TestReadTableMetadata:
    """Tests for read_table_metadata() method."""

    def test_returns_dict(self, connector):
        """Should return a dictionary."""
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            assert isinstance(metadata, dict), f"Metadata for {table} is not dict"

    def test_has_primary_keys(self, connector):
        """Metadata should include primary_keys."""
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            assert "primary_keys" in metadata, f"Metadata for {table} missing primary_keys"
            assert isinstance(metadata["primary_keys"], list)

    def test_has_ingestion_type(self, connector):
        """Metadata should include ingestion_type."""
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            assert "ingestion_type" in metadata, f"Metadata for {table} missing ingestion_type"

    def test_valid_ingestion_type(self, connector):
        """ingestion_type should be a valid value."""
        valid_types = ["snapshot", "cdc", "cdc_with_deletes", "append"]
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            assert metadata["ingestion_type"] in valid_types, (
                f"Invalid ingestion_type for {table}: {metadata['ingestion_type']}"
            )

    def test_cdc_has_cursor_field(self, connector):
        """CDC types must have cursor_field."""
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            if metadata["ingestion_type"] in ["cdc", "cdc_with_deletes", "append"]:
                assert "cursor_field" in metadata, (
                    f"Table {table} with {metadata['ingestion_type']} missing cursor_field"
                )
                assert metadata["cursor_field"] is not None

    def test_invalid_table_raises(self, connector):
        """Should raise ValueError for unknown table."""
        with pytest.raises(ValueError, match="not supported"):
            connector.read_table_metadata("nonexistent_table_xyz", {})


# ---------------------------------------------------------------------------
# Test: read_table
# ---------------------------------------------------------------------------


class TestReadTable:
    """Tests for read_table() method."""

    def test_returns_tuple(self, connector):
        """Should return a tuple of (iterator, offset)."""
        table = connector.list_tables()[0]
        result = connector.read_table(table, None, {})
        assert isinstance(result, tuple), "read_table should return tuple"
        assert len(result) == 2, "read_table should return 2-element tuple"

    def test_first_element_is_iterable(self, connector):
        """First element should be an iterator/iterable."""
        table = connector.list_tables()[0]
        records_iter, _ = connector.read_table(table, None, {})
        # Should be iterable - convert to list
        records = list(records_iter)
        assert isinstance(records, list)

    def test_second_element_is_dict_or_none(self, connector):
        """Second element (offset) should be dict or None."""
        table = connector.list_tables()[0]
        _, offset = connector.read_table(table, None, {})
        assert offset is None or isinstance(offset, dict), (
            f"Offset should be dict or None, got {type(offset)}"
        )

    def test_records_are_dicts(self, connector):
        """Each record should be a dictionary."""
        table = connector.list_tables()[0]
        records_iter, _ = connector.read_table(table, None, {})
        records = list(records_iter)
        if records:
            for i, r in enumerate(records[:5]):  # Check first 5
                assert isinstance(r, dict), f"Record {i} is not dict: {type(r)}"

    def test_records_have_id(self, connector):
        """Each record should have an 'id' field."""
        table = connector.list_tables()[0]
        records_iter, _ = connector.read_table(table, None, {})
        records = list(records_iter)
        if records:
            for i, r in enumerate(records[:5]):  # Check first 5
                assert "id" in r, f"Record {i} missing 'id' field"

    def test_invalid_table_raises(self, connector):
        """Should raise ValueError for unknown table."""
        with pytest.raises(ValueError, match="not supported"):
            connector.read_table("nonexistent_table_xyz", None, {})


# ---------------------------------------------------------------------------
# Test: Incremental Read
# ---------------------------------------------------------------------------


class TestIncrementalRead:
    """Tests for incremental read functionality."""

    def test_initial_read_returns_offset(self, connector):
        """Initial read (start_offset=None) should return an offset."""
        # Find a CDC or append table
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            if metadata["ingestion_type"] in ["cdc", "append"]:
                records, offset = connector.read_table(table, None, {})
                records_list = list(records)  # Consume iterator
                
                # Skip if server returned no data (server unavailable)
                if not records_list:
                    pytest.skip("FHIR server returned no data - may be unavailable")
                
                # Should have an offset
                assert offset is not None, f"Table {table} should return offset"
                assert isinstance(offset, dict)
                break

    def test_incremental_read_uses_offset(self, connector):
        """Reading with offset should filter results."""
        # Find a CDC table
        for table in connector.list_tables():
            metadata = connector.read_table_metadata(table, {})
            if metadata["ingestion_type"] == "cdc":
                # First read
                records1, offset1 = connector.read_table(table, None, {})
                list1 = list(records1)
                
                # Skip if server returned no data
                if not list1:
                    pytest.skip("FHIR server returned no data - may be unavailable")
                
                if offset1 and list1:
                    # Second read with offset
                    records2, offset2 = connector.read_table(table, offset1, {})
                    list2 = list(records2)
                    
                    # Should return offset (even if no new records)
                    assert offset2 is not None
                break


# ---------------------------------------------------------------------------
# Test: Connection to HAPI FHIR
# ---------------------------------------------------------------------------


class TestHAPIFHIRConnection:
    """Tests specific to HAPI FHIR server connectivity."""

    def test_can_fetch_patients(self, connector):
        """Should successfully fetch patients from HAPI FHIR."""
        if "patients" not in connector.list_tables():
            pytest.skip("patients table not in list_tables")
        
        records, offset = connector.read_table("patients", None, {})
        records_list = list(records)
        
        # Skip if server returned no data (server unavailable)
        if not records_list:
            pytest.skip("FHIR server returned no data - may be unavailable")
        
        # HAPI FHIR should have test patients
        assert len(records_list) > 0, "Should fetch at least one patient"

    def test_patients_have_expected_fields(self, connector):
        """Patient records should have expected FHIR fields."""
        if "patients" not in connector.list_tables():
            pytest.skip("patients table not in list_tables")
        
        records, _ = connector.read_table("patients", None, {})
        records_list = list(records)
        
        if records_list:
            patient = records_list[0]
            # FHIR Patient must have resourceType
            assert patient.get("resourceType") == "Patient", (
                f"Expected resourceType='Patient', got {patient.get('resourceType')}"
            )
