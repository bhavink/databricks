"""
FHIR Ingestion Service

Fetches FHIR resources from REST APIs and writes them to Unity Catalog Volumes
as NDJSON files for pipeline processing.

The pipeline (bronze_fhir.py, silver_fhir.py) remains unchanged -
it reads NDJSON from volumes regardless of how data arrived there.

Usage:
    # Simple - public HAPI server
    ingestion = FHIRIngestion(
        output_volume="/Volumes/main/healthcare_fhir/raw_data/fhir"
    )
    result = ingestion.ingest_resources(["Patient", "Observation"], max_per_resource=100)
    
    # Custom server with auth
    config = FHIRClientConfig(
        base_url="https://fhir.example.com/api/FHIR/R4",
        auth_type="smart",
        client_id="...",
        client_secret="...",
        token_url="https://fhir.example.com/oauth2/token"
    )
    ingestion = FHIRIngestion(config=config, output_volume="...")
    result = ingestion.ingest_incremental(last_updated="2024-01-01")
"""

import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .fhir_client import FHIRClient, FHIRClientConfig


logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of an ingestion run"""
    success: bool
    resources_fetched: int = 0
    resources_written: int = 0
    files_created: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    run_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "resources_fetched": self.resources_fetched,
            "resources_written": self.resources_written,
            "files_created": self.files_created,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "run_id": self.run_id,
        }


class FHIRIngestion:
    """
    FHIR REST API to Unity Catalog Volume ingestion service.
    
    This is the INGESTION LAYER - completely separate from the pipeline.
    The pipeline reads from volumes; this writes to volumes.
    
    Easy server selection with presets:
        # Use HAPI (default)
        ingestion = FHIRIngestion.from_preset("hapi", output_volume="...")
        
        # Use Synthea for realistic synthetic data
        ingestion = FHIRIngestion.from_preset("synthea", output_volume="...")
        
        # Available presets: hapi, synthea, smart_sandbox, hl7_test, cerner_sandbox
    """
    
    DEFAULT_RESOURCES = [
        "Patient",
        "Observation", 
        "Encounter",
        "Condition",
        "MedicationRequest",
        "Immunization",
    ]
    
    # Available server presets
    AVAILABLE_PRESETS = ["hapi", "synthea", "smart_sandbox", "hl7_test", "cerner_sandbox", "hapi_stu3"]
    
    @classmethod
    def from_preset(
        cls,
        server_name: str,
        output_volume: str = "/Volumes/main/healthcare_fhir/raw_data/fhir",
        output_subdir: str = "api_extracts",
        batch_size: int = 1000,
        use_dbutils: bool = True,
    ) -> "FHIRIngestion":
        """
        Create FHIRIngestion from a server preset.
        
        Args:
            server_name: One of: hapi, synthea, smart_sandbox, hl7_test, cerner_sandbox
            output_volume: UC Volume path for output
            output_subdir: Subdirectory within volume
            batch_size: Resources per file
            use_dbutils: Use dbutils for file operations
            
        Example:
            # Synthea has high-quality synthetic data
            ingestion = FHIRIngestion.from_preset("synthea", output_volume="/Volumes/...")
            
            # HAPI is fast but data is less structured
            ingestion = FHIRIngestion.from_preset("hapi", output_volume="/Volumes/...")
        """
        from .fhir_servers import get_server_config
        config = get_server_config(server_name)
        return cls(
            config=config,
            output_volume=output_volume,
            output_subdir=output_subdir,
            batch_size=batch_size,
            use_dbutils=use_dbutils,
        )
    
    def __init__(
        self,
        config: Optional[FHIRClientConfig] = None,
        base_url: Optional[str] = None,
        output_volume: str = "/Volumes/main/healthcare_fhir/raw_data/fhir",
        output_subdir: str = "api_extracts",
        batch_size: int = 1000,
        use_dbutils: bool = True,
    ):
        """
        Initialize FHIR ingestion service.
        
        Args:
            config: FHIR client configuration
            base_url: Shortcut for simple setup (uses HAPI if not provided)
            output_volume: UC Volume path for output
            output_subdir: Subdirectory within volume for API extracts
            batch_size: Resources per file
            use_dbutils: Use dbutils for file operations (True in Databricks)
        """
        self.client = FHIRClient(config=config, base_url=base_url)
        self.output_volume = output_volume.rstrip("/")
        self.output_subdir = output_subdir
        self.batch_size = batch_size
        self.use_dbutils = use_dbutils
        
        # Will be set at runtime if in Databricks
        self._dbutils = None
    
    @property
    def output_path(self) -> str:
        """Full output path"""
        return f"{self.output_volume}/{self.output_subdir}"
    
    # =========================================================================
    # Main Ingestion Methods
    # =========================================================================
    
    def ingest_resources(
        self,
        resource_types: Optional[List[str]] = None,
        max_per_resource: Optional[int] = None,
        search_params: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> IngestionResult:
        """
        Ingest specified FHIR resources.
        
        Args:
            resource_types: List of resource types to ingest (default: all supported)
            max_per_resource: Max resources per type (None = all)
            search_params: Per-resource search parameters
                           e.g., {"Patient": {"gender": "male"}, "Observation": {"code": "8867-4"}}
        
        Returns:
            IngestionResult with statistics
        """
        import time
        start_time = time.time()
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        resource_types = resource_types or self.DEFAULT_RESOURCES
        search_params = search_params or {}
        
        result = IngestionResult(success=True, run_id=run_id)
        
        logger.info(f"Starting ingestion run {run_id}")
        logger.info(f"Resources: {resource_types}")
        logger.info(f"Output: {self.output_path}")
        
        for resource_type in resource_types:
            try:
                params = search_params.get(resource_type, {})
                resources = self._fetch_resource_type(
                    resource_type, params, max_per_resource
                )
                result.resources_fetched += len(resources)
                
                if resources:
                    files = self._write_resources(resources, resource_type, run_id)
                    result.files_created.extend(files)
                    result.resources_written += len(resources)
                    logger.info(f"  {resource_type}: {len(resources)} resources → {len(files)} files")
                else:
                    logger.info(f"  {resource_type}: 0 resources found")
                    
            except Exception as e:
                error_msg = f"{resource_type}: {str(e)}"
                result.errors.append(error_msg)
                logger.error(f"  {error_msg}")
                result.success = False
        
        result.duration_seconds = time.time() - start_time
        logger.info(f"Ingestion complete: {result.resources_written} resources in {result.duration_seconds:.1f}s")
        
        return result
    
    def ingest_incremental(
        self,
        last_updated: str,
        resource_types: Optional[List[str]] = None,
    ) -> IngestionResult:
        """
        Incremental ingestion - only resources updated since last_updated.
        
        Args:
            last_updated: ISO datetime string (e.g., "2024-01-01T00:00:00Z")
            resource_types: Resource types to ingest
            
        Returns:
            IngestionResult
        """
        search_params = {}
        for rt in (resource_types or self.DEFAULT_RESOURCES):
            search_params[rt] = {"_lastUpdated": f"gt{last_updated}"}
        
        return self.ingest_resources(
            resource_types=resource_types,
            search_params=search_params
        )
    
    def ingest_single_resource(
        self,
        resource_type: str,
        resource_id: str,
    ) -> IngestionResult:
        """
        Ingest a single resource by ID.
        
        Useful for targeted fetches or testing.
        """
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = IngestionResult(success=True, run_id=run_id)
        
        try:
            response = self.client.read(resource_type, resource_id)
            if response.success and response.data:
                files = self._write_resources([response.data], resource_type, run_id)
                result.resources_fetched = 1
                result.resources_written = 1
                result.files_created = files
            else:
                result.success = False
                result.errors.append(response.error or "Resource not found")
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
        
        return result
    
    # =========================================================================
    # Internal Methods
    # =========================================================================
    
    def _fetch_resource_type(
        self,
        resource_type: str,
        params: Dict[str, Any],
        max_results: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Fetch resources of a specific type"""
        logger.debug(f"Fetching {resource_type} with params: {params}")
        return self.client.search(
            resource_type,
            params=params,
            max_results=max_results
        )
    
    def _write_resources(
        self,
        resources: List[Dict[str, Any]],
        resource_type: str,
        run_id: str,
    ) -> List[str]:
        """
        Write resources to volume as NDJSON files.
        
        Files are written in batches to handle large datasets.
        """
        files_created = []
        
        # Split into batches
        for batch_num, i in enumerate(range(0, len(resources), self.batch_size)):
            batch = resources[i:i + self.batch_size]
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{resource_type.lower()}_{run_id}_{batch_num:04d}.ndjson"
            filepath = f"{self.output_path}/{filename}"
            
            # Convert to NDJSON
            ndjson_content = "\n".join(json.dumps(r) for r in batch)
            
            # Write file
            self._write_file(filepath, ndjson_content)
            files_created.append(filepath)
        
        return files_created
    
    def _write_file(self, path: str, content: str):
        """Write content to file (volume or local)"""
        if self.use_dbutils:
            self._write_to_volume(path, content)
        else:
            self._write_to_local(path, content)
    
    def _write_to_volume(self, path: str, content: str):
        """Write to Unity Catalog Volume using dbutils"""
        if self._dbutils is None:
            try:
                # Get dbutils from Databricks runtime
                from pyspark.dbutils import DBUtils
                from pyspark.sql import SparkSession
                spark = SparkSession.builder.getOrCreate()
                self._dbutils = DBUtils(spark)
            except Exception:
                # Fallback for testing outside Databricks
                logger.warning("dbutils not available, using local file system")
                self._write_to_local(path, content)
                return
        
        self._dbutils.fs.put(path, content, overwrite=True)
    
    def _write_to_local(self, path: str, content: str):
        """Write to local file system (for testing)"""
        # Convert volume path to local path
        if path.startswith("/Volumes/"):
            # In testing, write to a local temp directory
            local_path = path.replace("/Volumes/", "/tmp/test_volumes/")
        else:
            local_path = path
        
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "w") as f:
            f.write(content)
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def test_connection(self) -> bool:
        """Test connection to FHIR server"""
        return self.client.test_connection()
    
    def get_server_capabilities(self) -> Dict[str, Any]:
        """Get FHIR server capability statement"""
        response = self.client.get_capability_statement()
        return response.data if response.success else {"error": response.error}


# =============================================================================
# Databricks Notebook Entry Point
# =============================================================================

def run_ingestion_notebook(
    base_url: str = "http://hapi.fhir.org/baseR4",
    output_volume: str = "/Volumes/main/healthcare_fhir/raw_data/fhir",
    resource_types: Optional[List[str]] = None,
    max_per_resource: int = 100,
    incremental_from: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Entry point for Databricks notebook execution.
    
    Example notebook cell:
        result = run_ingestion_notebook(
            base_url="http://hapi.fhir.org/baseR4",
            output_volume="/Volumes/main/healthcare_fhir/raw_data/fhir",
            resource_types=["Patient", "Observation"],
            max_per_resource=100
        )
        print(f"Ingested {result['resources_written']} resources")
    """
    ingestion = FHIRIngestion(
        base_url=base_url,
        output_volume=output_volume,
        use_dbutils=True,
    )
    
    if incremental_from:
        result = ingestion.ingest_incremental(
            last_updated=incremental_from,
            resource_types=resource_types,
        )
    else:
        result = ingestion.ingest_resources(
            resource_types=resource_types,
            max_per_resource=max_per_resource,
        )
    
    return result.to_dict()
