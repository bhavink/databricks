"""
Lakeflow Connect Base Interface

This is the base class that all community connectors must implement.
Copied from: https://github.com/databrickslabs/lakeflow-community-connectors/blob/master/sources/interface/lakeflow_connect.py

DO NOT MODIFY THIS FILE - it must match the upstream interface.
"""

from typing import Iterator, Any
from pyspark.sql.types import StructType


class LakeflowConnect:
    """
    Base class for Lakeflow Community Connectors.
    
    Each source connector must implement all methods defined here.
    """
    
    def __init__(self, options: dict[str, str]) -> None:
        """
        Initialize the source connector with parameters needed to connect to the source.
        
        Args:
            options: A dictionary of parameters like authentication tokens, table names,
                     and other configurations.
        """
        raise NotImplementedError("Subclasses must implement __init__")

    def list_tables(self) -> list[str]:
        """
        List names of all the tables supported by the source connector.
        
        The list could either be a static list or retrieved from the source via API.
        
        Returns:
            A list of table names.
        """
        raise NotImplementedError("Subclasses must implement list_tables")

    def get_table_schema(
        self, table_name: str, table_options: dict[str, str]
    ) -> StructType:
        """
        Fetch the schema of a table.
        
        Args:
            table_name: The name of the table to fetch the schema for.
            table_options: A dictionary of options for accessing the table.
            
        Returns:
            A StructType object representing the schema of the table.
        """
        raise NotImplementedError("Subclasses must implement get_table_schema")

    def read_table_metadata(
        self, table_name: str, table_options: dict[str, str]
    ) -> dict:
        """
        Fetch the metadata of a table.
        
        Args:
            table_name: The name of the table to fetch the metadata for.
            table_options: A dictionary of options for accessing the table.
            
        Returns:
            A dictionary containing:
                - primary_keys: List of primary key column names
                - cursor_field: Name of the field to use for incremental loading
                - ingestion_type: One of "snapshot", "cdc", "cdc_with_deletes", "append"
        """
        raise NotImplementedError("Subclasses must implement read_table_metadata")

    def read_table(
        self, table_name: str, start_offset: dict, table_options: dict[str, str]
    ) -> tuple[Iterator[dict], dict]:
        """
        Read the records of a table and return an iterator of records and an offset.
        
        Args:
            table_name: The name of the table to read.
            start_offset: The offset to start reading from.
            table_options: A dictionary of options for accessing the table.
            
        Returns:
            A tuple of (iterator of records as dicts, new offset dict)
            
        Note:
            DO NOT convert the JSON based on the schema in get_table_schema.
            Return raw JSON from the source.
        """
        raise NotImplementedError("Subclasses must implement read_table")

    def read_table_deletes(
        self, table_name: str, start_offset: dict, table_options: dict[str, str]
    ) -> tuple[Iterator[dict], dict]:
        """
        Read deleted records from a table for CDC delete synchronization.
        
        This method is required when ingestion_type is "cdc_with_deletes".
        
        Args:
            table_name: The name of the table to read deleted records from.
            start_offset: The offset to start reading from.
            table_options: A dictionary of options for accessing the table.
            
        Returns:
            A tuple of (iterator of deleted records, new offset dict)
            Records should have at minimum the primary key fields and cursor field.
        """
        raise NotImplementedError("Subclasses must implement read_table_deletes")
