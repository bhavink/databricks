# Databricks notebook source
# MAGIC %md
# MAGIC # Healthcare (FHIR R4) Connector - Standalone Test
# MAGIC 
# MAGIC This notebook tests the Healthcare connector directly in Databricks
# MAGIC before full SDP integration.
# MAGIC 
# MAGIC **Test Server**: HAPI FHIR Public R4 (https://hapi.fhir.org/baseR4)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Dependencies
# MAGIC 
# MAGIC **Note**: `requests` is pre-installed on Databricks. No pip install needed.
# MAGIC 
# MAGIC If your cluster has no internet access, that's fine - this notebook uses only built-in libraries.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Connector Implementation
# MAGIC 
# MAGIC Copy of `sources/healthcare/lakeflow_connect.py`

# COMMAND ----------

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


class Healthcare:
    """
    Lakeflow Connect implementation for FHIR R4 APIs.
    """

    SUPPORTED_TABLES = [
        "patients",
        "encounters",
        "observations",
        "conditions",
        "medications",
    ]

    TABLE_TO_RESOURCE = {
        "patients": "Patient",
        "encounters": "Encounter",
        "observations": "Observation",
        "conditions": "Condition",
        "medications": "MedicationRequest",
    }

    def __init__(self, options: dict) -> None:
        if "fhir_base_url" not in options:
            raise ValueError("Missing required option: fhir_base_url")

        self.base_url = options["fhir_base_url"].rstrip("/")
        self.auth_type = options.get("auth_type", "none")

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        })

        if self.auth_type == "api_key":
            api_key = options.get("api_key")
            if not api_key:
                raise ValueError("api_key required when auth_type='api_key'")
            self.session.headers["Authorization"] = f"Bearer {api_key}"

    def list_tables(self) -> list:
        return self.SUPPORTED_TABLES.copy()

    def get_table_schema(self, table_name: str, table_options: dict) -> StructType:
        if table_name not in self.SUPPORTED_TABLES:
            raise ValueError(f"Table '{table_name}' is not supported")
        return SCHEMAS.get(table_name)

    def read_table_metadata(self, table_name: str, table_options: dict) -> dict:
        if table_name not in self.SUPPORTED_TABLES:
            raise ValueError(f"Table '{table_name}' is not supported")
        return METADATA.get(table_name)

    def read_table(
        self,
        table_name: str,
        start_offset: dict,
        table_options: dict,
    ) -> tuple:
        if table_name not in self.SUPPORTED_TABLES:
            raise ValueError(f"Table '{table_name}' is not supported")

        resource_type = self.TABLE_TO_RESOURCE[table_name]
        records = []
        new_offset = {}

        url = f"{self.base_url}/{resource_type}"
        params = {"_count": "100"}

        if start_offset and start_offset.get("last_updated"):
            params["_lastUpdated"] = f"gt{start_offset['last_updated']}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                bundle = response.json()

                if bundle.get("resourceType") == "OperationOutcome":
                    raise requests.RequestException(
                        f"Server error: {bundle.get('issue', [{}])[0].get('diagnostics', 'Unknown')}"
                    )

                entries = bundle.get("entry", [])
                for entry in entries:
                    resource = entry.get("resource", {})
                    if resource:
                        records.append(resource)

                if records:
                    last_record = records[-1]
                    last_updated = last_record.get("meta", {}).get("lastUpdated")
                    if last_updated:
                        new_offset["last_updated"] = last_updated
                break

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                print(f"Error fetching {resource_type}: {e}")

        return iter(records), new_offset if new_offset else None


# Schema definitions
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
    ]),
    "encounters": StructType([
        StructField("resourceType", StringType(), nullable=False),
        StructField("id", StringType(), nullable=False),
        StructField("meta", META_SCHEMA, nullable=True),
        StructField("status", StringType(), nullable=False),
        StructField("subject", REFERENCE_SCHEMA, nullable=True),
        StructField("period", PERIOD_SCHEMA, nullable=True),
    ]),
    "observations": StructType([
        StructField("resourceType", StringType(), nullable=False),
        StructField("id", StringType(), nullable=False),
        StructField("meta", META_SCHEMA, nullable=True),
        StructField("status", StringType(), nullable=False),
        StructField("code", CODEABLE_CONCEPT_SCHEMA, nullable=False),
        StructField("subject", REFERENCE_SCHEMA, nullable=True),
        StructField("effectiveDateTime", StringType(), nullable=True),
    ]),
    "conditions": StructType([
        StructField("resourceType", StringType(), nullable=False),
        StructField("id", StringType(), nullable=False),
        StructField("meta", META_SCHEMA, nullable=True),
        StructField("code", CODEABLE_CONCEPT_SCHEMA, nullable=True),
        StructField("subject", REFERENCE_SCHEMA, nullable=False),
        StructField("onsetDateTime", StringType(), nullable=True),
    ]),
    "medications": StructType([
        StructField("resourceType", StringType(), nullable=False),
        StructField("id", StringType(), nullable=False),
        StructField("meta", META_SCHEMA, nullable=True),
        StructField("status", StringType(), nullable=False),
        StructField("intent", StringType(), nullable=False),
        StructField("subject", REFERENCE_SCHEMA, nullable=False),
        StructField("authoredOn", StringType(), nullable=True),
    ]),
}

METADATA = {
    "patients": {"primary_keys": ["id"], "cursor_field": "meta_lastUpdated", "ingestion_type": "cdc"},
    "encounters": {"primary_keys": ["id"], "cursor_field": "meta_lastUpdated", "ingestion_type": "cdc"},
    "observations": {"primary_keys": ["id"], "cursor_field": "meta_lastUpdated", "ingestion_type": "append"},
    "conditions": {"primary_keys": ["id"], "cursor_field": "meta_lastUpdated", "ingestion_type": "cdc"},
    "medications": {"primary_keys": ["id"], "cursor_field": "meta_lastUpdated", "ingestion_type": "cdc"},
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Initialize Connector

# COMMAND ----------

# Configuration for HAPI FHIR public test server
config = {
    "fhir_base_url": "https://hapi.fhir.org/baseR4",
    "auth_type": "none"
}

connector = Healthcare(config)
print("✅ Connector initialized successfully")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Test: list_tables()

# COMMAND ----------

tables = connector.list_tables()
print(f"Supported tables ({len(tables)}):")
for t in tables:
    print(f"  - {t}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Test: get_table_schema()

# COMMAND ----------

for table in tables:
    schema = connector.get_table_schema(table, {})
    print(f"\n📋 Schema for '{table}' ({len(schema.fields)} fields):")
    for field in schema.fields[:5]:  # Show first 5 fields
        print(f"  - {field.name}: {field.dataType.simpleString()}")
    if len(schema.fields) > 5:
        print(f"  ... and {len(schema.fields) - 5} more fields")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Test: read_table_metadata()

# COMMAND ----------

print("📊 Table Metadata:\n")
print(f"{'Table':<15} {'Ingestion Type':<15} {'Primary Keys':<15} {'Cursor Field'}")
print("-" * 60)
for table in tables:
    meta = connector.read_table_metadata(table, {})
    print(f"{table:<15} {meta['ingestion_type']:<15} {str(meta['primary_keys']):<15} {meta['cursor_field']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Test: read_table() - Fetch Patient Data

# COMMAND ----------

print("🔄 Fetching patients from HAPI FHIR...")
records_iter, offset = connector.read_table("patients", None, {})
records = list(records_iter)

print(f"✅ Fetched {len(records)} patient records")
if offset:
    print(f"📍 Offset for next sync: {offset}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Convert to Spark DataFrame

# COMMAND ----------

if records:
    # Create DataFrame from records using schema
    schema = connector.get_table_schema("patients", {})
    df = spark.createDataFrame(records, schema=schema)
    
    print(f"📊 Created DataFrame with {df.count()} rows")
    display(df.select("id", "gender", "birthDate", "meta.lastUpdated"))
else:
    print("⚠️ No records returned - HAPI FHIR server may be having issues")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Test Incremental Sync

# COMMAND ----------

if offset:
    print(f"🔄 Testing incremental sync with offset: {offset}")
    records_iter2, offset2 = connector.read_table("patients", offset, {})
    records2 = list(records_iter2)
    print(f"✅ Incremental fetch returned {len(records2)} new/updated records")
    if offset2:
        print(f"📍 New offset: {offset2}")
else:
    print("⚠️ No offset from initial read - skipping incremental test")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Fetch All Tables (Optional)

# COMMAND ----------

# Uncomment to test all tables
# for table in tables:
#     print(f"\n{'='*50}")
#     print(f"Fetching: {table}")
#     records_iter, offset = connector.read_table(table, None, {})
#     records = list(records_iter)
#     print(f"  Records: {len(records)}")
#     if records:
#         schema = connector.get_table_schema(table, {})
#         df = spark.createDataFrame(records, schema=schema)
#         display(df.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC 
# MAGIC | Test | Status |
# MAGIC |------|--------|
# MAGIC | Connector initialization | ✅ |
# MAGIC | list_tables() | ✅ |
# MAGIC | get_table_schema() | ✅ |
# MAGIC | read_table_metadata() | ✅ |
# MAGIC | read_table() | Check above |
# MAGIC | Spark DataFrame conversion | Check above |
# MAGIC | Incremental sync | Check above |
# MAGIC 
# MAGIC **Next Steps**: If all tests pass, proceed with full SDP integration.
