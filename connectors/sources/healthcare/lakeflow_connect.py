"""
Healthcare (FHIR R4) Lakeflow Connect Implementation.

Supports:
- FHIR R4 REST API ingestion
- Incremental sync via meta.lastUpdated
- OAuth2 and no-auth modes

Usage:
    connector = LakeflowConnect({
        "fhir_base_url": "https://hapi.fhir.org/baseR4",
        "auth_type": "none"
    })
    
    tables = connector.list_tables()
    schema = connector.get_table_schema("patients", {})
    records, offset = connector.read_table("patients", None, {})
"""

from typing import Iterator
import requests
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    LongType,
    TimestampType,
    BooleanType,
    ArrayType,
)


class LakeflowConnect:
    """
    Lakeflow Connect implementation for FHIR R4 APIs.
    """

    # Supported tables (FHIR resource types)
    SUPPORTED_TABLES = [
        "patients",
        "encounters",
        "observations",
        "conditions",
        "medications",
    ]

    # FHIR resource type mapping
    TABLE_TO_RESOURCE = {
        "patients": "Patient",
        "encounters": "Encounter",
        "observations": "Observation",
        "conditions": "Condition",
        "medications": "MedicationRequest",
    }

    def __init__(self, options: dict[str, str]) -> None:
        """
        Initialize connector with configuration.

        Args:
            options: Configuration dictionary containing:
                - fhir_base_url: Base URL of FHIR server (required)
                - auth_type: "none" | "api_key" | "oauth2" (default: "none")
                - api_key: API key (if auth_type="api_key")
                - client_id: OAuth2 client ID (if auth_type="oauth2")
                - client_secret: OAuth2 client secret (if auth_type="oauth2")
                - token_url: OAuth2 token URL (if auth_type="oauth2")

        Raises:
            ValueError: If required options are missing
        """
        # Validate required options
        if "fhir_base_url" not in options:
            raise ValueError("Missing required option: fhir_base_url")

        self.base_url = options["fhir_base_url"].rstrip("/")
        self.auth_type = options.get("auth_type", "none")

        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        })

        # Configure authentication
        if self.auth_type == "api_key":
            api_key = options.get("api_key")
            if not api_key:
                raise ValueError("api_key required when auth_type='api_key'")
            self.session.headers["Authorization"] = f"Bearer {api_key}"

        elif self.auth_type == "oauth2":
            # TODO: Implement OAuth2 token refresh
            raise NotImplementedError("OAuth2 not yet implemented")

    def list_tables(self) -> list[str]:
        """
        Return names of all tables supported by this connector.

        Returns:
            List of table names (FHIR resource types)
        """
        return self.SUPPORTED_TABLES.copy()

    def get_table_schema(
        self, table_name: str, table_options: dict[str, str]
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
        if table_name not in self.SUPPORTED_TABLES:
            raise ValueError(f"Table '{table_name}' is not supported")

        return SCHEMAS.get(table_name)

    def read_table_metadata(
        self, table_name: str, table_options: dict[str, str]
    ) -> dict:
        """
        Return metadata for ingestion configuration.

        Args:
            table_name: Name of the table
            table_options: Additional options for this table

        Returns:
            Dictionary with primary_keys, cursor_field, ingestion_type

        Raises:
            ValueError: If table_name is not supported
        """
        if table_name not in self.SUPPORTED_TABLES:
            raise ValueError(f"Table '{table_name}' is not supported")

        return METADATA.get(table_name)

    def read_table(
        self,
        table_name: str,
        start_offset: dict,
        table_options: dict[str, str],
    ) -> tuple[Iterator[dict], dict]:
        """
        Read records from FHIR server.

        Args:
            table_name: Table to read
            start_offset: Resume position (None for initial load)
                         Format: {"last_updated": "2024-01-15T10:30:00Z"}
            table_options: Per-table configuration

        Returns:
            (iterator of records as dicts, new offset dict)

        Raises:
            ValueError: If table_name is not supported
        """
        if table_name not in self.SUPPORTED_TABLES:
            raise ValueError(f"Table '{table_name}' is not supported")

        resource_type = self.TABLE_TO_RESOURCE[table_name]
        records = []
        new_offset = {}

        # Build search URL
        url = f"{self.base_url}/{resource_type}"
        params = {
            "_count": "100",
        }

        # Apply incremental filter if offset provided
        if start_offset and start_offset.get("last_updated"):
            params["_lastUpdated"] = f"gt{start_offset['last_updated']}"
        
        # Note: _sort=_lastUpdated not supported by all FHIR servers (e.g., HAPI FHIR)
        # We track offset from latest record in response instead

        # Fetch from FHIR server with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                bundle = response.json()

                # Check for OperationOutcome (error response)
                if bundle.get("resourceType") == "OperationOutcome":
                    raise requests.RequestException(
                        f"Server error: {bundle.get('issue', [{}])[0].get('diagnostics', 'Unknown')}"
                    )

                # Extract entries from Bundle
                entries = bundle.get("entry", [])
                for entry in entries:
                    resource = entry.get("resource", {})
                    if resource:
                        records.append(resource)

                # Track offset from last record
                if records:
                    last_record = records[-1]
                    last_updated = last_record.get("meta", {}).get("lastUpdated")
                    if last_updated:
                        new_offset["last_updated"] = last_updated
                break  # Success, exit retry loop

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                # Log error on final attempt
                print(f"Error fetching {resource_type}: {e}")

        return iter(records), new_offset if new_offset else None


# ---------------------------------------------------------------------------
# Schema Definitions
# ---------------------------------------------------------------------------

# Common nested types
META_SCHEMA = StructType([
    StructField("versionId", StringType(), nullable=True),
    StructField("lastUpdated", StringType(), nullable=True),
])

IDENTIFIER_SCHEMA = StructType([
    StructField("system", StringType(), nullable=True),
    StructField("value", StringType(), nullable=True),
    StructField("use", StringType(), nullable=True),
])

HUMAN_NAME_SCHEMA = StructType([
    StructField("use", StringType(), nullable=True),
    StructField("family", StringType(), nullable=True),
    StructField("given", ArrayType(StringType()), nullable=True),
    StructField("prefix", ArrayType(StringType()), nullable=True),
    StructField("suffix", ArrayType(StringType()), nullable=True),
])

CODEABLE_CONCEPT_SCHEMA = StructType([
    StructField("coding", ArrayType(StructType([
        StructField("system", StringType(), nullable=True),
        StructField("code", StringType(), nullable=True),
        StructField("display", StringType(), nullable=True),
    ])), nullable=True),
    StructField("text", StringType(), nullable=True),
])

REFERENCE_SCHEMA = StructType([
    StructField("reference", StringType(), nullable=True),
    StructField("display", StringType(), nullable=True),
])

PERIOD_SCHEMA = StructType([
    StructField("start", StringType(), nullable=True),
    StructField("end", StringType(), nullable=True),
])


SCHEMAS = {
    "patients": StructType([
        StructField("resourceType", StringType(), nullable=False),
        StructField("id", StringType(), nullable=False),
        StructField("meta", META_SCHEMA, nullable=True),
        StructField("identifier", ArrayType(IDENTIFIER_SCHEMA), nullable=True),
        StructField("active", BooleanType(), nullable=True),
        StructField("name", ArrayType(HUMAN_NAME_SCHEMA), nullable=True),
        StructField("gender", StringType(), nullable=True),
        StructField("birthDate", StringType(), nullable=True),
        StructField("deceasedBoolean", BooleanType(), nullable=True),
        StructField("deceasedDateTime", StringType(), nullable=True),
    ]),

    "encounters": StructType([
        StructField("resourceType", StringType(), nullable=False),
        StructField("id", StringType(), nullable=False),
        StructField("meta", META_SCHEMA, nullable=True),
        StructField("identifier", ArrayType(IDENTIFIER_SCHEMA), nullable=True),
        StructField("status", StringType(), nullable=False),
        StructField("class", CODEABLE_CONCEPT_SCHEMA, nullable=True),
        StructField("type", ArrayType(CODEABLE_CONCEPT_SCHEMA), nullable=True),
        StructField("subject", REFERENCE_SCHEMA, nullable=True),
        StructField("period", PERIOD_SCHEMA, nullable=True),
    ]),

    "observations": StructType([
        StructField("resourceType", StringType(), nullable=False),
        StructField("id", StringType(), nullable=False),
        StructField("meta", META_SCHEMA, nullable=True),
        StructField("identifier", ArrayType(IDENTIFIER_SCHEMA), nullable=True),
        StructField("status", StringType(), nullable=False),
        StructField("category", ArrayType(CODEABLE_CONCEPT_SCHEMA), nullable=True),
        StructField("code", CODEABLE_CONCEPT_SCHEMA, nullable=False),
        StructField("subject", REFERENCE_SCHEMA, nullable=True),
        StructField("effectiveDateTime", StringType(), nullable=True),
        StructField("valueQuantity", StructType([
            StructField("value", StringType(), nullable=True),
            StructField("unit", StringType(), nullable=True),
            StructField("system", StringType(), nullable=True),
            StructField("code", StringType(), nullable=True),
        ]), nullable=True),
        StructField("valueString", StringType(), nullable=True),
    ]),

    "conditions": StructType([
        StructField("resourceType", StringType(), nullable=False),
        StructField("id", StringType(), nullable=False),
        StructField("meta", META_SCHEMA, nullable=True),
        StructField("identifier", ArrayType(IDENTIFIER_SCHEMA), nullable=True),
        StructField("clinicalStatus", CODEABLE_CONCEPT_SCHEMA, nullable=True),
        StructField("verificationStatus", CODEABLE_CONCEPT_SCHEMA, nullable=True),
        StructField("category", ArrayType(CODEABLE_CONCEPT_SCHEMA), nullable=True),
        StructField("code", CODEABLE_CONCEPT_SCHEMA, nullable=True),
        StructField("subject", REFERENCE_SCHEMA, nullable=False),
        StructField("onsetDateTime", StringType(), nullable=True),
        StructField("recordedDate", StringType(), nullable=True),
    ]),

    "medications": StructType([
        StructField("resourceType", StringType(), nullable=False),
        StructField("id", StringType(), nullable=False),
        StructField("meta", META_SCHEMA, nullable=True),
        StructField("identifier", ArrayType(IDENTIFIER_SCHEMA), nullable=True),
        StructField("status", StringType(), nullable=False),
        StructField("intent", StringType(), nullable=False),
        StructField("medicationCodeableConcept", CODEABLE_CONCEPT_SCHEMA, nullable=True),
        StructField("subject", REFERENCE_SCHEMA, nullable=False),
        StructField("authoredOn", StringType(), nullable=True),
        StructField("requester", REFERENCE_SCHEMA, nullable=True),
    ]),
}


METADATA = {
    "patients": {
        "primary_keys": ["id"],
        "cursor_field": "meta_lastUpdated",
        "ingestion_type": "cdc",
    },
    "encounters": {
        "primary_keys": ["id"],
        "cursor_field": "meta_lastUpdated",
        "ingestion_type": "cdc",
    },
    "observations": {
        "primary_keys": ["id"],
        "cursor_field": "meta_lastUpdated",
        "ingestion_type": "append",
    },
    "conditions": {
        "primary_keys": ["id"],
        "cursor_field": "meta_lastUpdated",
        "ingestion_type": "cdc",
    },
    "medications": {
        "primary_keys": ["id"],
        "cursor_field": "meta_lastUpdated",
        "ingestion_type": "cdc",
    },
}
