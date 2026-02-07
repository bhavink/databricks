# FHIR REST API Ingestion Module
#
# This module handles fetching FHIR resources from REST APIs
# and writing them to Unity Catalog Volumes for pipeline processing.
#
# The pipeline (bronze_fhir.py, silver_fhir.py) remains unchanged -
# it reads from volumes regardless of how data arrived there.
#
# Quick Start:
#   from fhir.ingestion import FHIRClient, FHIRIngestion, SERVERS
#   
#   # Use a preset server
#   client = FHIRClient.from_preset("synthea")  # or "hapi", "smart_sandbox"
#   
#   # Or create ingestion with preset
#   ingestion = FHIRIngestion.from_preset("hapi", output_volume="/Volumes/...")

from .fhir_client import FHIRClient, FHIRClientConfig
from .fhir_ingestion import FHIRIngestion
from .fhir_servers import SERVERS, get_server_config, list_servers, print_servers

__all__ = [
    "FHIRClient",
    "FHIRClientConfig", 
    "FHIRIngestion",
    "SERVERS",
    "get_server_config",
    "list_servers",
    "print_servers",
]
