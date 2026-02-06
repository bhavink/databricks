"""
Healthcare Lakeflow Connect Implementation.

Supports two modes:
1. API Mode (FHIR R4): REST API ingestion from FHIR servers
2. File Mode (HL7v2): File-based ingestion from UC-managed cloud storage

Usage:
    # API Mode (FHIR)
    connector = Healthcare({
        "fhir_base_url": "https://hapi.fhir.org/baseR4",
        "auth_type": "none"
    })
    
    # File Mode (HL7v2) - UC-managed storage
    connector = Healthcare({
        "storage_path": "s3://bucket/hl7v2/",
        "file_pattern": "*.hl7"
    })
"""

from typing import Iterator, Optional
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


# Also export as Healthcare for cleaner imports
class Healthcare:
    """
    Lakeflow Connect implementation for Healthcare data.
    
    Supports FHIR R4 APIs and HL7v2 files from cloud storage.
    """

    # FHIR tables (API mode)
    FHIR_TABLES = [
        "patients",
        "encounters",
        "observations",
        "conditions",
        "medications",
    ]

    # HL7v2 tables (File mode)
    HL7V2_TABLES = [
        "adt_messages",
        "orm_messages",
        "oru_messages",
        "siu_messages",
        "vxu_messages",
    ]

    # FHIR resource type mapping
    TABLE_TO_RESOURCE = {
        "patients": "Patient",
        "encounters": "Encounter",
        "observations": "Observation",
        "conditions": "Condition",
        "medications": "MedicationRequest",
    }

    # HL7v2 message type mapping
    TABLE_TO_HL7_TYPE = {
        "adt_messages": "ADT",
        "orm_messages": "ORM",
        "oru_messages": "ORU",
        "siu_messages": "SIU",
        "vxu_messages": "VXU",
    }

    def __init__(self, options: dict) -> None:
        """
        Initialize connector with configuration.

        Args:
            options: Configuration dictionary containing:
            
            For API Mode (FHIR):
                - fhir_base_url: Base URL of FHIR server (required for API mode)
                - auth_type: "none" | "api_key" | "oauth2" (default: "none")
                - api_key: API key (if auth_type="api_key")
                - client_id: OAuth2 client ID (if auth_type="oauth2")
                - client_secret: OAuth2 client secret (if auth_type="oauth2")
                - token_url: OAuth2 token URL (if auth_type="oauth2")
            
            For File Mode (HL7v2):
                - storage_path: UC-managed cloud storage path (required for File mode)
                - file_pattern: Glob pattern for files (default: "*.hl7")
                - recursive: Scan subdirectories (default: "false")

        Raises:
            ValueError: If required options are missing
        """
        # Detect mode based on configuration
        self.mode = self._detect_mode(options)
        self.options = options
        
        if self.mode == "api":
            self._init_api_mode(options)
        elif self.mode == "file":
            self._init_file_mode(options)
        else:
            raise ValueError(
                "Must provide either 'fhir_base_url' (API mode) or 'storage_path' (File mode)"
            )

    def _detect_mode(self, options: dict) -> str:
        """Detect connector mode from options."""
        if "fhir_base_url" in options:
            return "api"
        elif "storage_path" in options:
            return "file"
        return "unknown"

    def _init_api_mode(self, options: dict) -> None:
        """Initialize for FHIR API mode."""
        self.base_url = options["fhir_base_url"].rstrip("/")
        self.auth_type = options.get("auth_type", "none")

        # Initialize HTTP session
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
            self._init_oauth2(options)

    def _init_oauth2(self, options: dict) -> None:
        """Initialize OAuth2 authentication."""
        required = ["token_url", "client_id", "client_secret"]
        for key in required:
            if key not in options:
                raise ValueError(f"Missing required OAuth2 option: {key}")
        
        self.token_url = options["token_url"]
        self.client_id = options["client_id"]
        self.client_secret = options["client_secret"]
        self.scope = options.get("scope", "system/*.read")
        self._access_token = None
        self._token_expires = 0
        
        # Get initial token
        self._refresh_token()

    def _refresh_token(self) -> None:
        """Refresh OAuth2 access token."""
        import time
        
        response = requests.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        token_data = response.json()
        
        self._access_token = token_data["access_token"]
        # Set expiry with 60s buffer
        expires_in = token_data.get("expires_in", 3600)
        self._token_expires = time.time() + expires_in - 60
        
        self.session.headers["Authorization"] = f"Bearer {self._access_token}"

    def _ensure_valid_token(self) -> None:
        """Ensure OAuth2 token is valid, refresh if needed."""
        import time
        if self.auth_type == "oauth2" and time.time() >= self._token_expires:
            self._refresh_token()

    def _init_file_mode(self, options: dict) -> None:
        """Initialize for HL7v2 file mode."""
        self.storage_path = options["storage_path"].rstrip("/")
        self.file_pattern = options.get("file_pattern", "*.hl7")
        self.recursive = options.get("recursive", "false").lower() == "true"
        
        # Spark context will be available at runtime in Databricks
        self._spark = None

    def _get_spark(self):
        """Get or create Spark session."""
        if self._spark is None:
            try:
                from pyspark.sql import SparkSession
                self._spark = SparkSession.builder.getOrCreate()
            except Exception:
                raise RuntimeError(
                    "Spark session not available. File mode requires Databricks runtime."
                )
        return self._spark

    def list_tables(self) -> list:
        """
        Return names of all tables supported by this connector.

        Returns:
            List of table names based on mode
        """
        if self.mode == "api":
            return self.FHIR_TABLES.copy()
        else:  # file mode
            return self.HL7V2_TABLES.copy()

    def get_table_schema(
        self, table_name: str, table_options: dict
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
        supported = self.list_tables()
        if table_name not in supported:
            raise ValueError(f"Table '{table_name}' is not supported")

        return SCHEMAS.get(table_name)

    def read_table_metadata(
        self, table_name: str, table_options: dict
    ) -> dict:
        """
        Return metadata for ingestion configuration.

        Returns:
            Dictionary with primary_keys, cursor_field, ingestion_type
        """
        supported = self.list_tables()
        if table_name not in supported:
            raise ValueError(f"Table '{table_name}' is not supported")

        return METADATA.get(table_name)

    def read_table(
        self,
        table_name: str,
        start_offset: dict,
        table_options: dict,
    ) -> tuple:
        """
        Read records from source.

        Returns:
            (iterator of records as dicts, new offset dict)
        """
        supported = self.list_tables()
        if table_name not in supported:
            raise ValueError(f"Table '{table_name}' is not supported")

        if self.mode == "api":
            return self._read_fhir_table(table_name, start_offset, table_options)
        else:
            return self._read_hl7v2_table(table_name, start_offset, table_options)

    def _read_fhir_table(
        self,
        table_name: str,
        start_offset: Optional[dict],
        table_options: dict,
    ) -> tuple:
        """Read from FHIR API."""
        # Ensure valid OAuth2 token if applicable
        if self.auth_type == "oauth2":
            self._ensure_valid_token()

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

    def _read_hl7v2_table(
        self,
        table_name: str,
        start_offset: Optional[dict],
        table_options: dict,
    ) -> tuple:
        """
        Read HL7v2 files from UC-managed cloud storage.
        
        Supports batch and streaming patterns with robust error handling:
        - Batch: Process files in configurable batch sizes
        - Streaming: Micro-batch for SDP, or true Structured Streaming
        
        Error Handling:
        - Parse errors captured with file path and error message
        - Dead letter queue option for failed files
        - Granular checkpointing (tracks processed files list)
        
        Args:
            table_name: HL7v2 table (adt_messages, orm_messages, oru_messages)
            start_offset: {
                "last_file": "path/to/last/processed.hl7",
                "processed_files": ["file1.hl7", "file2.hl7"]  # Optional granular tracking
            }
            table_options: {
                "batch_size": "1000",           # Files per batch (default: 1000)
                "mode": "batch",                # "batch" | "streaming" | "structured_streaming"
                "error_handling": "skip",       # "skip" | "fail" | "dead_letter"
                "dead_letter_path": "/path",    # Required if error_handling="dead_letter"
                "checkpoint_path": "/path",     # For structured streaming mode
            }
        
        Returns:
            (iterator of records, new_offset)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        target_type = self.TABLE_TO_HL7_TYPE[table_name]
        spark = self._get_spark()
        
        # Configuration
        batch_size = int(table_options.get("batch_size", "1000"))
        mode = table_options.get("mode", "batch")
        error_handling = table_options.get("error_handling", "skip")
        
        # Build path with pattern
        search_path = f"{self.storage_path}/{self.file_pattern}"
        
        # Get offset state
        last_file = start_offset.get("last_file") if start_offset else None
        processed_files = set(start_offset.get("processed_files", [])) if start_offset else set()
        
        try:
            if mode == "structured_streaming":
                return self._read_hl7v2_structured_streaming(
                    spark, search_path, target_type, table_options
                )
            elif mode == "streaming":
                return self._read_hl7v2_batch_internal(
                    spark, search_path, target_type, last_file, processed_files,
                    int(table_options.get("max_files_per_trigger", "100")),
                    error_handling, table_options
                )
            else:
                return self._read_hl7v2_batch_internal(
                    spark, search_path, target_type, last_file, processed_files,
                    batch_size, error_handling, table_options
                )
                
        except Exception as e:
            logger.error(f"Error reading HL7v2 files: {e}", exc_info=True)
            if error_handling == "fail":
                raise
            return iter([]), start_offset

    def _read_hl7v2_batch_internal(
        self,
        spark,
        search_path: str,
        target_type: str,
        last_file: Optional[str],
        processed_files: set,
        batch_size: int,
        error_handling: str,
        table_options: dict,
    ) -> tuple:
        """
        Batch read with distributed processing and robust error handling.
        
        Features:
        - Parsing on executors via UDF (no collect to driver)
        - Error tracking with file path and error message
        - Granular checkpointing (list of processed files)
        - Dead letter queue support
        """
        import logging
        import json
        from pyspark.sql.functions import udf, col, lit, struct
        from pyspark.sql.types import StringType, StructType, StructField, ArrayType
        
        logger = logging.getLogger(__name__)
        
        # Schema for parse result (includes error info)
        PARSE_RESULT_SCHEMA = StructType([
            StructField("success", StringType(), nullable=False),
            StructField("data", StringType(), nullable=True),
            StructField("error", StringType(), nullable=True),
            StructField("msg_type", StringType(), nullable=True),
        ])
        
        # Read files as binary
        try:
            files_df = spark.read.format("binaryFile").load(search_path)
        except Exception as e:
            logger.error(f"Failed to read files from {search_path}: {e}")
            if error_handling == "fail":
                raise
            return iter([]), None
        
        # Sort by path for deterministic ordering
        files_df = files_df.orderBy("path")
        
        # Incremental: filter to files after last processed
        if last_file:
            files_df = files_df.filter(col("path") > last_file)
        
        # Limit batch size
        files_df = files_df.limit(batch_size)
        
        # Schema for array of parse results (supports batch files with multiple messages)
        PARSE_RESULTS_ARRAY_SCHEMA = ArrayType(PARSE_RESULT_SCHEMA)
        
        # UDF that returns array of parse results (handles batch files)
        @udf(returnType=PARSE_RESULTS_ARRAY_SCHEMA)
        def parse_hl7_batch_with_errors(content: bytes, file_path: str):
            """
            Parse HL7v2 file on executor, handles batch files with multiple messages.
            
            Returns array of parse results - one per message in the file.
            """
            import json as json_mod
            
            if content is None:
                return [{"success": "false", "data": None, "error": "Empty content", "msg_type": None}]
            
            results = []
            
            try:
                text = content.decode("utf-8", errors="replace")
                
                # Import parser functions
                from sources.healthcare.hl7v2_parser import parse_hl7v2_file, split_hl7_batch
                
                # Split batch file into individual messages
                messages = split_hl7_batch(text)
                
                if not messages:
                    return [{"success": "false", "data": None, "error": "No valid HL7v2 messages found in file", "msg_type": None}]
                
                # Parse each message
                for i, msg_text in enumerate(messages):
                    try:
                        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
                        
                        parsed = parse_hl7v2_message(msg_text)
                        if parsed:
                            msg_type = parsed.get("message_type", "")
                            results.append({
                                "success": "true",
                                "data": json_mod.dumps(parsed),
                                "error": None,
                                "msg_type": msg_type
                            })
                        else:
                            results.append({
                                "success": "false",
                                "data": None,
                                "error": f"Parser returned None for message {i+1}",
                                "msg_type": None
                            })
                    except Exception as e:
                        results.append({
                            "success": "false",
                            "data": None,
                            "error": f"Parse error in message {i+1}: {str(e)}",
                            "msg_type": None
                        })
                
                return results if results else [{"success": "false", "data": None, "error": "No messages parsed", "msg_type": None}]
                    
            except UnicodeDecodeError as e:
                return [{"success": "false", "data": None, "error": f"Encoding error: {str(e)}", "msg_type": None}]
            except Exception as e:
                return [{"success": "false", "data": None, "error": f"Parse error: {str(e)}", "msg_type": None}]
        
        # Distributed processing with error tracking
        # 1. Parse file (may return multiple messages)
        # 2. Explode to get one row per message
        from pyspark.sql.functions import explode, posexplode
        
        parsed_df = (
            files_df
            .withColumn("parse_results", parse_hl7_batch_with_errors(col("content"), col("path")))
            .select(
                col("path"),
                explode(col("parse_results")).alias("parse_result")
            )
            .select(
                col("path"),
                col("parse_result.success").alias("success"),
                col("parse_result.data").alias("data"),
                col("parse_result.error").alias("error"),
                col("parse_result.msg_type").alias("msg_type"),
            )
        )
        
        # Separate successful parses from failures
        success_df = parsed_df.filter(
            (col("success") == "true") & (col("msg_type") == target_type)
        )
        
        failed_df = parsed_df.filter(col("success") == "false")
        
        # Handle dead letter queue
        dead_letter_path = table_options.get("dead_letter_path")
        if error_handling == "dead_letter" and dead_letter_path:
            try:
                # Write failed records to dead letter location
                failed_count = failed_df.count()
                if failed_count > 0:
                    failed_df.select("path", "error", "msg_type").write.mode("append").json(
                        f"{dead_letter_path}/hl7v2_errors"
                    )
                    logger.warning(f"Wrote {failed_count} failed records to dead letter queue")
            except Exception as e:
                logger.error(f"Failed to write to dead letter queue: {e}")
        
        # Log failures
        if error_handling != "fail":
            try:
                failures = failed_df.select("path", "error").limit(10).collect()
                for row in failures:
                    logger.warning(f"HL7v2 parse failure: {row.path} - {row.error}")
            except Exception:
                pass  # Don't fail on logging
        
        # Stream successful results to driver
        records = []
        new_processed_files = list(processed_files)
        new_offset = {}
        last_successful_file = None
        
        try:
            for row in success_df.select("path", "data").toLocalIterator():
                try:
                    record = json.loads(row.data)
                    record["_source_file"] = row.path
                    records.append(record)
                    new_processed_files.append(row.path)
                    last_successful_file = row.path
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error for {row.path}: {e}")
                    if error_handling == "fail":
                        raise
        except Exception as e:
            logger.error(f"Error iterating results: {e}")
            if error_handling == "fail":
                raise
        
        # Build offset with granular tracking
        if last_successful_file:
            new_offset["last_file"] = last_successful_file
        if new_processed_files:
            # Only keep last N files to avoid unbounded growth
            max_tracked = int(table_options.get("max_tracked_files", "10000"))
            new_offset["processed_files"] = new_processed_files[-max_tracked:]
        
        # Add statistics to offset for observability
        new_offset["_stats"] = {
            "records_returned": len(records),
            "batch_size_requested": batch_size,
        }
        
        return iter(records), new_offset if new_offset else None

    def _read_hl7v2_structured_streaming(
        self,
        spark,
        search_path: str,
        target_type: str,
        table_options: dict,
    ) -> tuple:
        """
        True Structured Streaming with Auto Loader.
        
        This returns a streaming DataFrame, not an iterator.
        Use this for continuous ingestion with exactly-once guarantees.
        
        Checkpointing is handled by Spark Structured Streaming.
        
        Usage:
            records, _ = connector.read_table("adt_messages", None, {
                "mode": "structured_streaming",
                "checkpoint_path": "/Volumes/catalog/schema/checkpoints/hl7v2"
            })
            # records is a streaming DataFrame
            records.writeStream.toTable("target_table")
        """
        from pyspark.sql.functions import udf, col, explode
        from pyspark.sql.types import StringType, StructType, StructField, ArrayType
        
        checkpoint_path = table_options.get("checkpoint_path")
        if not checkpoint_path:
            raise ValueError("checkpoint_path required for structured_streaming mode")
        
        max_files = int(table_options.get("max_files_per_trigger", "100"))
        
        # Use Auto Loader (cloudFiles) for efficient streaming file discovery
        # Falls back to binaryFile if cloudFiles not available
        try:
            streaming_df = (
                spark.readStream
                .format("cloudFiles")
                .option("cloudFiles.format", "binaryFile")
                .option("cloudFiles.maxFilesPerTrigger", max_files)
                .option("cloudFiles.schemaLocation", f"{checkpoint_path}/schema")
                .load(search_path)
            )
        except Exception:
            # Fallback: file-based streaming (less efficient for large dirs)
            streaming_df = (
                spark.readStream
                .format("binaryFile")
                .option("maxFilesPerTrigger", max_files)
                .load(search_path)
            )
        
        # Parse result schema (supports batch files with multiple messages)
        PARSE_RESULT_SCHEMA = StructType([
            StructField("success", StringType(), nullable=False),
            StructField("data", StringType(), nullable=True),
            StructField("error", StringType(), nullable=True),
            StructField("msg_type", StringType(), nullable=True),
        ])
        PARSE_RESULTS_ARRAY_SCHEMA = ArrayType(PARSE_RESULT_SCHEMA)
        
        @udf(returnType=PARSE_RESULTS_ARRAY_SCHEMA)
        def parse_hl7_batch_with_errors(content: bytes, file_path: str):
            """Parse HL7v2 file, handles batch files with multiple messages."""
            import json as json_mod
            
            if content is None:
                return [{"success": "false", "data": None, "error": "Empty content", "msg_type": None}]
            
            results = []
            try:
                text = content.decode("utf-8", errors="replace")
                from sources.healthcare.hl7v2_parser import split_hl7_batch, parse_hl7v2_message
                
                messages = split_hl7_batch(text)
                if not messages:
                    return [{"success": "false", "data": None, "error": "No valid messages", "msg_type": None}]
                
                for i, msg_text in enumerate(messages):
                    try:
                        parsed = parse_hl7v2_message(msg_text)
                        if parsed:
                            results.append({
                                "success": "true",
                                "data": json_mod.dumps(parsed),
                                "error": None,
                                "msg_type": parsed.get("message_type", "")
                            })
                        else:
                            results.append({
                                "success": "false",
                                "data": None,
                                "error": f"Parser returned None for message {i+1}",
                                "msg_type": None
                            })
                    except Exception as e:
                        results.append({
                            "success": "false",
                            "data": None,
                            "error": f"Error in message {i+1}: {str(e)}",
                            "msg_type": None
                        })
                
                return results if results else [{"success": "false", "data": None, "error": "No messages parsed", "msg_type": None}]
                    
            except Exception as e:
                return [{"success": "false", "data": None, "error": str(e), "msg_type": None}]
        
        # Apply parsing UDF and explode for batch files
        parsed_stream = (
            streaming_df
            .withColumn("parse_results", parse_hl7_batch_with_errors(col("content"), col("path")))
            .select(col("path"), explode(col("parse_results")).alias("parse_result"))
            .select(
                col("path").alias("_source_file"),
                col("parse_result.success").alias("_parse_success"),
                col("parse_result.data").alias("_parsed_json"),
                col("parse_result.error").alias("_parse_error"),
                col("parse_result.msg_type").alias("_msg_type"),
            )
            .filter((col("_parse_success") == "true") & (col("_msg_type") == target_type))
        )
        
        # Return streaming DataFrame
        # Caller should use .writeStream to sink the data
        # Checkpoint path should be set in the writeStream, not here
        return parsed_stream, {"mode": "structured_streaming", "checkpoint_path": checkpoint_path}


# Alias for backward compatibility
LakeflowConnect = Healthcare


# ---------------------------------------------------------------------------
# Schema Definitions
# ---------------------------------------------------------------------------

# Common nested types for FHIR
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

# HL7v2 Observation schema (for ORU results)
HL7V2_OBSERVATION_SCHEMA = StructType([
    StructField("set_id", StringType(), nullable=True),
    StructField("value_type", StringType(), nullable=True),
    StructField("observation_id", StringType(), nullable=True),
    StructField("observation_value", StringType(), nullable=True),
    StructField("units", StringType(), nullable=True),
    StructField("reference_range", StringType(), nullable=True),
    StructField("abnormal_flags", StringType(), nullable=True),
    StructField("result_status", StringType(), nullable=True),
])


SCHEMAS = {
    # FHIR Tables
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

    # HL7v2 Tables
    "adt_messages": StructType([
        StructField("message_control_id", StringType(), nullable=False),
        StructField("message_type", StringType(), nullable=False),
        StructField("trigger_event", StringType(), nullable=True),
        StructField("message_datetime", StringType(), nullable=True),
        StructField("sending_application", StringType(), nullable=True),
        StructField("sending_facility", StringType(), nullable=True),
        StructField("patient_id", StringType(), nullable=True),
        StructField("patient_name_family", StringType(), nullable=True),
        StructField("patient_name_given", StringType(), nullable=True),
        StructField("date_of_birth", StringType(), nullable=True),
        StructField("gender", StringType(), nullable=True),
        StructField("event_type_code", StringType(), nullable=True),
        StructField("event_datetime", StringType(), nullable=True),
        StructField("patient_class", StringType(), nullable=True),
        StructField("assigned_location", StringType(), nullable=True),
        StructField("admission_type", StringType(), nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),

    "orm_messages": StructType([
        StructField("message_control_id", StringType(), nullable=False),
        StructField("message_type", StringType(), nullable=False),
        StructField("trigger_event", StringType(), nullable=True),
        StructField("message_datetime", StringType(), nullable=True),
        StructField("sending_application", StringType(), nullable=True),
        StructField("sending_facility", StringType(), nullable=True),
        StructField("patient_id", StringType(), nullable=True),
        StructField("patient_name_family", StringType(), nullable=True),
        StructField("patient_name_given", StringType(), nullable=True),
        StructField("order_control", StringType(), nullable=True),
        StructField("order_id", StringType(), nullable=True),
        StructField("filler_order_number", StringType(), nullable=True),
        StructField("order_status", StringType(), nullable=True),
        StructField("placer_order_number", StringType(), nullable=True),
        StructField("universal_service_id", StringType(), nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),

    "oru_messages": StructType([
        StructField("message_control_id", StringType(), nullable=False),
        StructField("message_type", StringType(), nullable=False),
        StructField("trigger_event", StringType(), nullable=True),
        StructField("message_datetime", StringType(), nullable=True),
        StructField("sending_application", StringType(), nullable=True),
        StructField("sending_facility", StringType(), nullable=True),
        StructField("patient_id", StringType(), nullable=True),
        StructField("patient_name_family", StringType(), nullable=True),
        StructField("patient_name_given", StringType(), nullable=True),
        StructField("placer_order_number", StringType(), nullable=True),
        StructField("filler_order_number", StringType(), nullable=True),
        StructField("universal_service_id", StringType(), nullable=True),
        StructField("observations", ArrayType(HL7V2_OBSERVATION_SCHEMA), nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),

    "siu_messages": StructType([
        StructField("message_control_id", StringType(), nullable=False),
        StructField("message_type", StringType(), nullable=False),
        StructField("trigger_event", StringType(), nullable=True),
        StructField("message_datetime", StringType(), nullable=True),
        StructField("sending_application", StringType(), nullable=True),
        StructField("sending_facility", StringType(), nullable=True),
        StructField("patient_id", StringType(), nullable=True),
        StructField("patient_name_family", StringType(), nullable=True),
        StructField("patient_name_given", StringType(), nullable=True),
        StructField("placer_appointment_id", StringType(), nullable=True),
        StructField("filler_appointment_id", StringType(), nullable=True),
        StructField("schedule_id", StringType(), nullable=True),
        StructField("event_reason", StringType(), nullable=True),
        StructField("appointment_reason", StringType(), nullable=True),
        StructField("appointment_type", StringType(), nullable=True),
        StructField("appointment_duration", StringType(), nullable=True),
        StructField("appointment_start_datetime", StringType(), nullable=True),
        StructField("appointment_end_datetime", StringType(), nullable=True),
        StructField("filler_status_code", StringType(), nullable=True),
        StructField("appointment_resources", ArrayType(StructType([
            StructField("resource_type", StringType(), nullable=True),
            StructField("set_id", StringType(), nullable=True),
            StructField("universal_service_id", StringType(), nullable=True),
            StructField("personnel_id", StringType(), nullable=True),
            StructField("location_id", StringType(), nullable=True),
            StructField("resource_role", StringType(), nullable=True),
            StructField("start_datetime", StringType(), nullable=True),
            StructField("duration", StringType(), nullable=True),
        ])), nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),

    "vxu_messages": StructType([
        StructField("message_control_id", StringType(), nullable=False),
        StructField("message_type", StringType(), nullable=False),
        StructField("trigger_event", StringType(), nullable=True),
        StructField("message_datetime", StringType(), nullable=True),
        StructField("sending_application", StringType(), nullable=True),
        StructField("sending_facility", StringType(), nullable=True),
        StructField("patient_id", StringType(), nullable=True),
        StructField("patient_name_family", StringType(), nullable=True),
        StructField("patient_name_given", StringType(), nullable=True),
        StructField("date_of_birth", StringType(), nullable=True),
        StructField("gender", StringType(), nullable=True),
        StructField("vaccinations", ArrayType(StructType([
            StructField("order_control", StringType(), nullable=True),
            StructField("placer_order_number", StringType(), nullable=True),
            StructField("filler_order_number", StringType(), nullable=True),
            StructField("administration_start_datetime", StringType(), nullable=True),
            StructField("vaccine_code", StringType(), nullable=True),
            StructField("vaccine_name", StringType(), nullable=True),
            StructField("vaccine_coding_system", StringType(), nullable=True),
            StructField("administered_amount", StringType(), nullable=True),
            StructField("administered_units", StringType(), nullable=True),
            StructField("manufacturer_code", StringType(), nullable=True),
            StructField("manufacturer_name", StringType(), nullable=True),
            StructField("lot_number", StringType(), nullable=True),
            StructField("expiration_date", StringType(), nullable=True),
            StructField("completion_status", StringType(), nullable=True),
            StructField("route_code", StringType(), nullable=True),
            StructField("route_name", StringType(), nullable=True),
            StructField("site_code", StringType(), nullable=True),
            StructField("site_name", StringType(), nullable=True),
        ])), nullable=True),
        StructField("observations", ArrayType(HL7V2_OBSERVATION_SCHEMA), nullable=True),
        StructField("_source_file", StringType(), nullable=True),
    ]),
}


METADATA = {
    # FHIR Tables
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
    # HL7v2 Tables
    "adt_messages": {
        "primary_keys": ["message_control_id"],
        "cursor_field": "message_datetime",
        "ingestion_type": "append",
    },
    "orm_messages": {
        "primary_keys": ["message_control_id"],
        "cursor_field": "message_datetime",
        "ingestion_type": "append",
    },
    "oru_messages": {
        "primary_keys": ["message_control_id"],
        "cursor_field": "message_datetime",
        "ingestion_type": "append",
    },
    "siu_messages": {
        "primary_keys": ["message_control_id"],
        "cursor_field": "message_datetime",
        "ingestion_type": "append",
    },
    "vxu_messages": {
        "primary_keys": ["message_control_id"],
        "cursor_field": "message_datetime",
        "ingestion_type": "append",
    },
}
