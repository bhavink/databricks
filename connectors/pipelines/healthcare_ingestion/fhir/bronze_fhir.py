# Healthcare FHIR R4 Bronze Ingestion Pipeline
# =============================================
#
# Production-grade Spark Declarative Pipeline (SDP) for FHIR R4 resource ingestion.
# Uses Auto Loader for streaming file ingestion from UC Volumes.
#
# API: Modern pyspark.pipelines (2026 best practice)
# Features:
# - VARIANT type for raw resource storage (schema evolution)
# - Liquid Clustering for optimal query performance (configurable)
# - Auto-optimization with predictive optimization (configurable)
# - FHIR R4 resource parsing and validation
# - SDP expectations for data quality (configurable)
# - Quarantine table for failed records
# - Bundle extraction (NDJSON and Bundle entries)
#
# Configuration: All settings are externalized to pipeline configuration.
# See config/pipeline_settings.json for available options.
#
# Supported Resources:
# - Patient, Observation, Encounter, MedicationRequest
# - DiagnosticReport, Immunization, Condition, Bundle

# Modern SDP API (pyspark.pipelines)
from pyspark import pipelines as dp
from pyspark.sql.functions import (
    col, udf, explode, when, lit, current_timestamp,
    from_json, to_timestamp
)
from pyspark.sql.types import (
    ArrayType, StructType, StructField, StringType, TimestampType,
    LongType, BooleanType
)
import json


# ---------------------------------------------------------------------------
# Configuration Helper
# ---------------------------------------------------------------------------
class PipelineConfig:
    """
    Centralized configuration management for the FHIR pipeline.
    All settings are read from pipeline configuration (spark.conf).
    """
    
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str, default: str = "") -> str:
        """Get a configuration value with caching."""
        if key not in self._cache:
            self._cache[key] = spark.conf.get(key, default)
        return self._cache[key]
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value."""
        return self.get(key, str(default).lower()) == "true"
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer configuration value."""
        return int(self.get(key, str(default)))
    
    def get_list(self, key: str, default: str = "") -> list:
        """Get a comma-separated list as a Python list."""
        value = self.get(key, default)
        return [v.strip() for v in value.split(",") if v.strip()]
    
    # --- Source Configuration ---
    @property
    def storage_path(self) -> str:
        return self.get("fhir.storage_path", "/Volumes/main/healthcare/raw_data/fhir")
    
    @property
    def checkpoint_path(self) -> str:
        return self.get("fhir.checkpoint_path", "/Volumes/main/healthcare/checkpoints/fhir")
    
    @property
    def file_pattern(self) -> str:
        return self.get("fhir.file_pattern", "*.ndjson")
    
    @property
    def max_files_per_trigger(self) -> str:
        return self.get("fhir.max_files_per_trigger", "1000")
    
    @property
    def max_bytes_per_trigger(self) -> str:
        return self.get("fhir.max_bytes_per_trigger", "10g")
    
    # --- Clustering Configuration ---
    @property
    def clustering_enabled(self) -> bool:
        return self.get_bool("fhir.clustering.enabled", True)
    
    def get_cluster_columns(self, table_name: str) -> list:
        """Get clustering columns for a specific table."""
        key = f"fhir.clustering.{table_name}.columns"
        return self.get_list(key, "")
    
    # --- Optimization Configuration ---
    @property
    def auto_optimize(self) -> bool:
        return self.get_bool("fhir.optimization.auto_optimize", True)
    
    @property
    def optimize_write(self) -> bool:
        return self.get_bool("fhir.optimization.optimize_write", True)
    
    # --- Quality Configuration ---
    @property
    def enable_expectations(self) -> bool:
        return self.get_bool("fhir.quality.enable_expectations", True)
    
    @property
    def quarantine_invalid_records(self) -> bool:
        return self.get_bool("fhir.quality.quarantine_invalid_records", True)
    
    # --- Table Properties Builder ---
    def build_table_properties(self, table_name: str, quality: str = "bronze") -> dict:
        """Build table properties with optimization settings."""
        props = {"quality": quality}
        
        if self.auto_optimize:
            props["pipelines.autoOptimize.managed"] = "true"
        
        if self.optimize_write:
            props["delta.autoOptimize.optimizeWrite"] = "true"
        
        # Note: For Liquid Clustering, we use cluster_by parameter
        # Only set zOrderCols if clustering is disabled
        if not self.clustering_enabled:
            cluster_cols = self.get_cluster_columns(table_name)
            if cluster_cols:
                props["pipelines.autoOptimize.zOrderCols"] = ",".join(cluster_cols)
        
        return props


# Initialize config (module-level for consistency)
config = PipelineConfig()

# Read configuration values at module level (for cluster_by)
STORAGE_PATH = config.storage_path
CHECKPOINT_PATH = config.checkpoint_path
FILE_PATTERN = config.file_pattern


# ---------------------------------------------------------------------------
# FHIR Constants (Inlined for executor access)
# ---------------------------------------------------------------------------
SUPPORTED_RESOURCE_TYPES = {
    "Patient", "Observation", "Encounter", "MedicationRequest",
    "DiagnosticReport", "Immunization", "Procedure", "Condition",
    "AllergyIntolerance", "Bundle", "Practitioner", "Organization",
    "Location", "Medication", "ServiceRequest", "CarePlan",
}

REQUIRED_FIELDS = {
    "Observation": ["status", "code"],
    "Encounter": ["status", "class"],
    "MedicationRequest": ["status", "intent", "subject"],
    "Immunization": ["status", "vaccineCode", "patient"],
    "DiagnosticReport": ["status", "code"],
    "Condition": ["subject"],
    "Bundle": ["type"],
}


# ---------------------------------------------------------------------------
# Parsing Functions (Inlined for executor access)
# ---------------------------------------------------------------------------

def validate_and_extract_fhir(raw_json: str) -> dict:
    """
    Validate a FHIR resource and extract key metadata.
    
    ALL LOGIC IS INLINED - executors cannot access workspace imports.
    
    Args:
        raw_json: JSON string of FHIR resource
        
    Returns:
        Dict with validation result and extracted fields
    """
    result = {
        "is_valid": True,
        "resource_type": None,
        "resource_id": None,
        "meta_version_id": None,
        "meta_last_updated": None,
        "validation_errors": []
    }
    
    # Parse JSON
    try:
        resource = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
    except (json.JSONDecodeError, TypeError) as e:
        result["is_valid"] = False
        result["validation_errors"].append(f"JSON parse error: {str(e)}")
        return result
    
    if not resource:
        result["is_valid"] = False
        result["validation_errors"].append("Resource is empty or null")
        return result
    
    # Check resourceType
    resource_type = resource.get("resourceType")
    if not resource_type:
        result["is_valid"] = False
        result["validation_errors"].append("Missing required field: resourceType")
        return result
    
    result["resource_type"] = resource_type
    result["resource_id"] = resource.get("id")
    
    # Extract meta
    meta = resource.get("meta", {})
    result["meta_version_id"] = meta.get("versionId")
    result["meta_last_updated"] = meta.get("lastUpdated")
    
    # Check if supported type
    if resource_type not in SUPPORTED_RESOURCE_TYPES:
        result["validation_errors"].append(f"Unknown resourceType: {resource_type}")
        # Still valid but with warning
    
    # Basic required field validation by type
    for field in REQUIRED_FIELDS.get(resource_type, []):
        if not resource.get(field):
            result["is_valid"] = False
            result["validation_errors"].append(f"Missing required field: {field}")
    
    # Check choice fields
    if resource_type == "MedicationRequest":
        if not resource.get("medicationCodeableConcept") and not resource.get("medicationReference"):
            result["is_valid"] = False
            result["validation_errors"].append("Missing required field: medication[x]")
    
    if resource_type == "Immunization":
        if not resource.get("occurrenceDateTime") and not resource.get("occurrenceString"):
            result["is_valid"] = False
            result["validation_errors"].append("Missing required field: occurrence[x]")
    
    return result


def extract_bundle_entries(raw_json: str) -> list:
    """
    Extract individual resources from a FHIR Bundle.
    
    Args:
        raw_json: JSON string of Bundle or resource
        
    Returns:
        List of resource JSON strings
    """
    try:
        resource = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        
        if not resource or resource.get("resourceType") != "Bundle":
            return [raw_json]  # Not a bundle, return as-is
        
        entries = resource.get("entry", [])
        resources = []
        
        for entry in entries:
            entry_resource = entry.get("resource")
            if entry_resource:
                resources.append(json.dumps(entry_resource))
        
        return resources if resources else [raw_json]
        
    except (json.JSONDecodeError, TypeError):
        return [raw_json]


# ---------------------------------------------------------------------------
# Schema Definitions
# ---------------------------------------------------------------------------

VALIDATION_RESULT_SCHEMA = StructType([
    StructField("is_valid", BooleanType(), False),
    StructField("resource_type", StringType(), True),
    StructField("resource_id", StringType(), True),
    StructField("meta_version_id", StringType(), True),
    StructField("meta_last_updated", StringType(), True),
    StructField("validation_errors", ArrayType(StringType()), True),
])

# Create UDFs
validate_fhir_udf = udf(validate_and_extract_fhir, VALIDATION_RESULT_SCHEMA)
extract_bundle_udf = udf(extract_bundle_entries, ArrayType(StringType()))


# ---------------------------------------------------------------------------
# Raw Ingestion Table (All FHIR Resources) - Single Parse Pass
# ---------------------------------------------------------------------------

# Build table configuration dynamically
_raw_cluster_cols = config.get_cluster_columns("raw") if config.clustering_enabled else None

@dp.table(
    name="bronze_fhir_raw",
    comment="Raw FHIR R4 resources with validation status. Uses VARIANT-ready storage.",
    table_properties=config.build_table_properties("raw"),
    cluster_by=_raw_cluster_cols,
)
@dp.expect("has_raw_resource", "raw_resource IS NOT NULL")
@dp.expect("has_resource_type", "resource_type IS NOT NULL")
def bronze_fhir_raw():
    """
    Ingest all FHIR files and parse once. Downstream tables filter by resource type.
    
    Features:
    - Auto Loader for incremental NDJSON ingestion
    - Bundle extraction (individual resources from Bundles)
    - Inline validation with error tracking
    
    Clustering: Configurable via fhir.clustering.raw.columns
    """
    # Read NDJSON files from Volume
    raw_files = (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "text")
        .option("pathGlobFilter", FILE_PATTERN)
        .option("cloudFiles.maxFilesPerTrigger", config.max_files_per_trigger)
        .option("cloudFiles.maxBytesPerTrigger", config.max_bytes_per_trigger)
        .option("cloudFiles.schemaLocation", f"{CHECKPOINT_PATH}/bronze_schema")
        .load(STORAGE_PATH)
    )
    
    # Add source metadata - use _metadata.file_path (Unity Catalog compatible)
    # Note: monotonically_increasing_id() not supported in streaming, use row_number at read time
    with_metadata = (
        raw_files
        .withColumn("_source_file", col("_metadata.file_path"))
        .withColumn("_ingestion_timestamp", current_timestamp())
        .withColumnRenamed("value", "raw_json_line")
    )
    
    # Explode bundles into individual resources
    exploded = (
        with_metadata
        .withColumn("resource_list", extract_bundle_udf(col("raw_json_line")))
        .withColumn("raw_resource", explode(col("resource_list")))
        .drop("resource_list", "raw_json_line")
    )
    
    # Validate and extract metadata
    validated = (
        exploded
        .withColumn("validation", validate_fhir_udf(col("raw_resource")))
        .select(
            col("_source_file"),
            col("_ingestion_timestamp"),
            col("raw_resource"),
            col("validation.is_valid").alias("is_valid"),
            col("validation.resource_type").alias("resource_type"),
            col("validation.resource_id").alias("resource_id"),
            col("validation.meta_version_id").alias("meta_version_id"),
            to_timestamp(col("validation.meta_last_updated")).alias("meta_last_updated"),
            col("validation.validation_errors").alias("validation_errors"),
        )
    )
    
    return validated


# ---------------------------------------------------------------------------
# Quarantine Table (Failed Resources)
# ---------------------------------------------------------------------------

_quarantine_cluster_cols = config.get_cluster_columns("quarantine") if config.clustering_enabled else None

@dp.table(
    name="bronze_fhir_quarantine",
    comment="Quarantined FHIR resources that failed parsing or validation",
    table_properties=config.build_table_properties("quarantine"),
    cluster_by=_quarantine_cluster_cols,
)
def bronze_fhir_quarantine():
    """
    Capture resources that failed parsing or validation.
    Per SDP best practice: use quarantine pattern instead of dropping silently.
    
    Clustering: Configurable via fhir.clustering.quarantine.columns
    """
    return (
        spark.read.table("bronze_fhir_raw")
        .filter(col("is_valid") == False)
        .select(
            col("_source_file"),
            col("_ingestion_timestamp"),
            col("raw_resource"),
            col("resource_type"),
            col("resource_id"),
            col("validation_errors"),
        )
    )


# ---------------------------------------------------------------------------
# Data Quality Views
# ---------------------------------------------------------------------------

@dp.view(
    name="bronze_fhir_stats",
    comment="Aggregated statistics for FHIR ingestion monitoring"
)
def bronze_fhir_stats():
    """
    Calculate ingestion statistics for monitoring dashboards.
    """
    from pyspark.sql.functions import window, count, countDistinct, sum as spark_sum
    
    return (
        spark.read.table("bronze_fhir_raw")
        .groupBy(
            window("_ingestion_timestamp", "1 hour").alias("time_window"),
            "resource_type",
            "is_valid"
        )
        .agg(
            count("*").alias("record_count"),
            countDistinct("resource_id").alias("unique_resources"),
            countDistinct("_source_file").alias("source_files"),
        )
    )
