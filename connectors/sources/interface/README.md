# Lakeflow Connect Interface

This folder contains the base interface that all community connectors must implement.

## Source

Copied from: https://github.com/databrickslabs/lakeflow-community-connectors/blob/master/sources/interface/

## Interface Methods

| Method | Required | Description |
|--------|----------|-------------|
| `__init__(options)` | Yes | Initialize connector with configuration |
| `list_tables()` | Yes | Return list of supported table names |
| `get_table_schema(table_name, table_options)` | Yes | Return Spark StructType for table |
| `read_table_metadata(table_name, table_options)` | Yes | Return metadata dict (primary_keys, cursor_field, ingestion_type) |
| `read_table(table_name, start_offset, table_options)` | Yes | Read records and return (iterator, offset) |
| `read_table_deletes(table_name, start_offset, table_options)` | If cdc_with_deletes | Read deleted records |

## Ingestion Types

| Type | Description |
|------|-------------|
| `snapshot` | Full table reload each time |
| `cdc` | Incremental with upserts only |
| `cdc_with_deletes` | Incremental with upserts AND deletes |
| `append` | Incremental append-only |
