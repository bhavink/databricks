# Databricks notebook source
# MAGIC %md
# MAGIC # FHIR REST API Ingestion
# MAGIC 
# MAGIC This notebook fetches FHIR resources from REST APIs and writes them to Unity Catalog Volumes.
# MAGIC The existing pipeline (`bronze_fhir.py`, `silver_fhir.py`) then processes these files automatically.
# MAGIC 
# MAGIC ## Architecture
# MAGIC ```
# MAGIC ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
# MAGIC │  FHIR Server    │────▶│  This Notebook   │────▶│  UC Volume      │
# MAGIC │  (REST API)     │     │  (Ingestion)     │     │  /fhir/*.ndjson │
# MAGIC └─────────────────┘     └──────────────────┘     └────────┬────────┘
# MAGIC                                                           │
# MAGIC                                                           ▼
# MAGIC                                                  ┌─────────────────┐
# MAGIC                                                  │  SDP Pipeline   │
# MAGIC                                                  │  (Unchanged)    │
# MAGIC                                                  └─────────────────┘
# MAGIC ```
# MAGIC 
# MAGIC ## Public Test Servers (No Auth Required)
# MAGIC - **HAPI FHIR**: `http://hapi.fhir.org/baseR4` (most popular)
# MAGIC - **Synthea**: `https://syntheticmass.mitre.org/fhir` (realistic synthetic data)
# MAGIC 
# MAGIC ## Usage
# MAGIC 1. Configure widgets below
# MAGIC 2. Run all cells
# MAGIC 3. Files appear in volume, pipeline picks them up automatically

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC 
# MAGIC ### Server Presets
# MAGIC | Preset | Description | Best For |
# MAGIC |--------|-------------|----------|
# MAGIC | **hapi** | HAPI FHIR Public Server | General testing, fast |
# MAGIC | **synthea** | Synthea Synthetic Data | Realistic patient data |
# MAGIC | **smart_sandbox** | SMART Health IT | OAuth testing |
# MAGIC | **cerner_sandbox** | Cerner Open Sandbox | EHR vendor testing |
# MAGIC | **custom** | Enter your own URL | Production servers |

# COMMAND ----------

# Widgets for configuration - Easy server selection!
dbutils.widgets.dropdown(
    "server_preset", 
    "hapi", 
    ["hapi", "synthea", "smart_sandbox", "cerner_sandbox", "hl7_test", "custom"],
    "1. Server Preset"
)
dbutils.widgets.text("custom_server_url", "", "   Custom URL (if preset=custom)")
dbutils.widgets.text("output_volume", "/Volumes/main/healthcare_fhir/raw_data/fhir", "2. Output Volume")
dbutils.widgets.text("resource_types", "Patient,Observation,Encounter,Condition", "3. Resource Types")
dbutils.widgets.text("max_per_resource", "100", "4. Max Per Type")
dbutils.widgets.dropdown("auth_type", "none", ["none", "bearer", "smart"], "5. Auth Type")
dbutils.widgets.text("incremental_from", "", "6. Incremental From (ISO date)")

# COMMAND ----------

# Server presets - easy swapping!
SERVER_PRESETS = {
    "hapi": {
        "url": "http://hapi.fhir.org/baseR4",
        "name": "HAPI FHIR Public",
        "rate_limit": 10.0,
        "notes": "Most popular public server. Fast but data is synthetic/unstructured."
    },
    "synthea": {
        "url": "https://syntheticmass.mitre.org/v1/fhir",
        "name": "Synthea (MITRE)",
        "rate_limit": 5.0,
        "notes": "High-quality synthetic patient data. Massachusetts population."
    },
    "smart_sandbox": {
        "url": "https://launch.smarthealthit.org/v/r4/fhir",
        "name": "SMART Health IT Sandbox",
        "rate_limit": 10.0,
        "notes": "SMART on FHIR sandbox. Good for OAuth flow testing."
    },
    "cerner_sandbox": {
        "url": "https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d",
        "name": "Cerner Open Sandbox",
        "rate_limit": 5.0,
        "notes": "Real EHR vendor responses. Good for production-like testing."
    },
    "hl7_test": {
        "url": "http://test.fhir.org/r4",
        "name": "HL7 Official Test Server",
        "rate_limit": 5.0,
        "notes": "Official HL7 server. Good for spec compliance."
    },
}

# Get widget values
SERVER_PRESET = dbutils.widgets.get("server_preset")
CUSTOM_URL = dbutils.widgets.get("custom_server_url")
OUTPUT_VOLUME = dbutils.widgets.get("output_volume")
RESOURCE_TYPES = [r.strip() for r in dbutils.widgets.get("resource_types").split(",")]
MAX_PER_RESOURCE = int(dbutils.widgets.get("max_per_resource"))
AUTH_TYPE = dbutils.widgets.get("auth_type")
INCREMENTAL_FROM = dbutils.widgets.get("incremental_from") or None

# Resolve server URL from preset
if SERVER_PRESET == "custom":
    if not CUSTOM_URL:
        raise ValueError("Custom URL required when preset is 'custom'")
    FHIR_SERVER_URL = CUSTOM_URL
    SERVER_NAME = "Custom Server"
    RATE_LIMIT = 10.0
else:
    preset = SERVER_PRESETS[SERVER_PRESET]
    FHIR_SERVER_URL = preset["url"]
    SERVER_NAME = preset["name"]
    RATE_LIMIT = preset["rate_limit"]

# Display configuration
print("="*60)
print("FHIR API INGESTION CONFIGURATION")
print("="*60)
print(f"\n  Server Preset: {SERVER_PRESET}")
print(f"  Server Name:   {SERVER_NAME}")
print(f"  Server URL:    {FHIR_SERVER_URL}")
print(f"  Rate Limit:    {RATE_LIMIT} req/sec")
print(f"\n  Output Volume: {OUTPUT_VOLUME}")
print(f"  Resources:     {', '.join(RESOURCE_TYPES)}")
print(f"  Max/Resource:  {MAX_PER_RESOURCE}")
print(f"  Auth Type:     {AUTH_TYPE}")
print(f"  Incremental:   {INCREMENTAL_FROM or 'Full ingestion'}")

if SERVER_PRESET in SERVER_PRESETS:
    print(f"\n  Note: {SERVER_PRESETS[SERVER_PRESET]['notes']}")
print("="*60)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install Dependencies

# COMMAND ----------

# Install httpx for better async HTTP handling (optional but recommended)
%pip install httpx --quiet

# COMMAND ----------

# MAGIC %md
# MAGIC ## FHIR Client Implementation

# COMMAND ----------

"""
FHIR REST API Client - Embedded for notebook portability

For production use, import from:
    from fhir.ingestion import FHIRClient, FHIRIngestion
"""

import time
import logging
import json
from typing import Optional, Dict, List, Any, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta

try:
    import httpx
    HTTP_CLIENT = "httpx"
except ImportError:
    import requests
    HTTP_CLIENT = "requests"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fhir_ingestion")


@dataclass
class FHIRClientConfig:
    """FHIR client configuration"""
    base_url: str
    auth_type: str = "none"
    token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    scope: str = "system/*.read"
    requests_per_second: float = 10.0
    retry_count: int = 3
    retry_delay: float = 1.0
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    default_page_size: int = 100
    max_pages: int = 1000


class FHIRClient:
    """FHIR R4 REST API Client"""
    
    def __init__(self, config: FHIRClientConfig):
        self.config = config
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._last_request_time: float = 0.0
        self._request_count: int = 0
    
    def search(self, resource_type: str, params: Optional[Dict] = None, max_results: Optional[int] = None) -> List[Dict]:
        """Search for resources with automatic pagination"""
        params = params or {}
        if "_count" not in params:
            params["_count"] = self.config.default_page_size
        
        url = f"{self.config.base_url}/{resource_type}"
        return list(self._paginate(url, params, max_results))
    
    def read(self, resource_type: str, resource_id: str) -> Optional[Dict]:
        """Read single resource by ID"""
        url = f"{self.config.base_url}/{resource_type}/{resource_id}"
        response = self._request("GET", url)
        return response.get("data") if response.get("success") else None
    
    def test_connection(self) -> bool:
        """Test server connectivity"""
        try:
            response = self._request("GET", f"{self.config.base_url}/metadata")
            return response.get("success", False)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def _paginate(self, url: str, params: Dict, max_results: Optional[int]) -> Iterator[Dict]:
        """Handle Bundle pagination"""
        total_yielded = 0
        page = 0
        
        while url and page < self.config.max_pages:
            if page == 0:
                response = self._request("GET", url, params=params)
            else:
                response = self._request("GET", url)
            
            if not response.get("success") or not response.get("data"):
                break
            
            bundle = response["data"]
            
            for entry in bundle.get("entry", []):
                resource = entry.get("resource")
                if resource:
                    yield resource
                    total_yielded += 1
                    if max_results and total_yielded >= max_results:
                        return
            
            # Get next page URL
            url = None
            for link in bundle.get("link", []):
                if link.get("relation") == "next":
                    url = link.get("url")
                    break
            
            page += 1
    
    def _request(self, method: str, url: str, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request with rate limiting and retries"""
        self._rate_limit()
        headers = self._get_headers()
        
        for attempt in range(self.config.retry_count):
            try:
                start = time.time()
                
                if HTTP_CLIENT == "httpx":
                    with httpx.Client(timeout=httpx.Timeout(self.config.connect_timeout, read=self.config.read_timeout)) as client:
                        response = client.request(method, url, headers=headers, params=params)
                else:
                    response = requests.request(method, url, headers=headers, params=params, 
                                               timeout=(self.config.connect_timeout, self.config.read_timeout))
                
                self._request_count += 1
                elapsed = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    return {"success": True, "data": response.json(), "elapsed_ms": elapsed}
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", self.config.retry_delay * (2 ** attempt)))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.retry_count - 1:
                    time.sleep(self.config.retry_delay * (2 ** attempt))
        
        return {"success": False, "error": "Max retries exceeded"}
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        if self.config.requests_per_second <= 0:
            return
        min_interval = 1.0 / self.config.requests_per_second
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth"""
        headers = {"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"}
        
        if self.config.auth_type == "bearer" and self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        elif self.config.auth_type == "smart":
            token = self._get_smart_token()
            headers["Authorization"] = f"Bearer {token}"
        
        return headers
    
    def _get_smart_token(self) -> str:
        """Get SMART on FHIR OAuth2 token"""
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token
        
        if not self.config.token_url:
            raise ValueError("token_url required for SMART auth")
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": self.config.scope,
        }
        
        if HTTP_CLIENT == "httpx":
            with httpx.Client() as client:
                response = client.post(self.config.token_url, data=data)
        else:
            response = requests.post(self.config.token_url, data=data)
        
        if response.status_code != 200:
            raise ValueError(f"Token request failed: {response.text}")
        
        token_data = response.json()
        self._token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
        
        return self._token

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingestion Functions

# COMMAND ----------

def ingest_resources(
    client: FHIRClient,
    resource_types: List[str],
    output_volume: str,
    max_per_resource: int = 100,
    incremental_from: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest FHIR resources to Unity Catalog Volume.
    
    Returns:
        Dictionary with ingestion statistics
    """
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{output_volume}/api_extracts"
    
    result = {
        "run_id": run_id,
        "success": True,
        "resources_fetched": 0,
        "files_created": [],
        "errors": [],
        "start_time": datetime.now().isoformat(),
    }
    
    logger.info(f"Starting ingestion run {run_id}")
    logger.info(f"Output path: {output_path}")
    
    for resource_type in resource_types:
        try:
            logger.info(f"Fetching {resource_type}...")
            
            # Build search params
            params = {}
            if incremental_from:
                params["_lastUpdated"] = f"gt{incremental_from}"
            
            # Fetch resources
            resources = client.search(resource_type, params=params, max_results=max_per_resource)
            result["resources_fetched"] += len(resources)
            
            if resources:
                # Write to volume as NDJSON
                filename = f"{resource_type.lower()}_{run_id}.ndjson"
                filepath = f"{output_path}/{filename}"
                
                ndjson_content = "\n".join(json.dumps(r) for r in resources)
                dbutils.fs.put(filepath, ndjson_content, overwrite=True)
                
                result["files_created"].append(filepath)
                logger.info(f"  {resource_type}: {len(resources)} resources → {filepath}")
            else:
                logger.info(f"  {resource_type}: 0 resources found")
                
        except Exception as e:
            error_msg = f"{resource_type}: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(f"  Error: {error_msg}")
            result["success"] = False
    
    result["end_time"] = datetime.now().isoformat()
    return result

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Ingestion

# COMMAND ----------

# Build client configuration with preset rate limiting
config = FHIRClientConfig(
    base_url=FHIR_SERVER_URL,
    auth_type=AUTH_TYPE,
    requests_per_second=RATE_LIMIT,  # Use preset's rate limit
)

# Add token if bearer auth
if AUTH_TYPE == "bearer":
    # For bearer auth, get token from secrets
    # config.token = dbutils.secrets.get(scope="fhir", key="access_token")
    print("⚠️  Bearer auth selected - configure token in secrets")
    pass

# Add SMART credentials if SMART auth
if AUTH_TYPE == "smart":
    # config.client_id = dbutils.secrets.get(scope="fhir", key="client_id")
    # config.client_secret = dbutils.secrets.get(scope="fhir", key="client_secret")
    # config.token_url = dbutils.secrets.get(scope="fhir", key="token_url")
    print("⚠️  SMART auth selected - configure credentials in secrets")
    pass

# Create client
client = FHIRClient(config)
print(f"\n✓ Client configured for: {SERVER_NAME}")

# Test connection
print("Testing connection...")
if client.test_connection():
    print("✓ Connected successfully")
else:
    print("✗ Connection failed")
    dbutils.notebook.exit("Connection failed")

# COMMAND ----------

# Run ingestion
result = ingest_resources(
    client=client,
    resource_types=RESOURCE_TYPES,
    output_volume=OUTPUT_VOLUME,
    max_per_resource=MAX_PER_RESOURCE,
    incremental_from=INCREMENTAL_FROM,
)

# Display results
print("\n" + "="*60)
print("INGESTION COMPLETE")
print("="*60)
print(f"Run ID: {result['run_id']}")
print(f"Success: {result['success']}")
print(f"Resources fetched: {result['resources_fetched']}")
print(f"Files created: {len(result['files_created'])}")

if result['errors']:
    print(f"\nErrors:")
    for e in result['errors']:
        print(f"  - {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Output

# COMMAND ----------

# List files in output directory
output_path = f"{OUTPUT_VOLUME}/api_extracts"
print(f"Files in {output_path}:")
try:
    files = dbutils.fs.ls(output_path)
    for f in files[-10:]:  # Last 10 files
        print(f"  {f.name} ({f.size} bytes)")
except Exception as e:
    print(f"  Error listing files: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Schedule with Databricks Workflows
# MAGIC 
# MAGIC To schedule this notebook:
# MAGIC 
# MAGIC 1. **Workflows UI**: Create new job → Add task → Select this notebook
# MAGIC 2. **Configure parameters** via task parameters (same as widget names)
# MAGIC 3. **Set schedule**: Cron expression (e.g., `0 0 * * *` for daily)
# MAGIC 
# MAGIC Example workflow YAML:
# MAGIC ```yaml
# MAGIC tasks:
# MAGIC   - task_key: fhir_ingestion
# MAGIC     notebook_task:
# MAGIC       notebook_path: /Workspace/.../fhir_api_ingestion
# MAGIC       base_parameters:
# MAGIC         fhir_server_url: "http://hapi.fhir.org/baseR4"
# MAGIC         resource_types: "Patient,Observation"
# MAGIC         max_per_resource: "1000"
# MAGIC schedule:
# MAGIC   quartz_cron_expression: "0 0 6 * * ?"
# MAGIC   timezone_id: "UTC"
# MAGIC ```

# COMMAND ----------

# Return result for workflow orchestration
dbutils.notebook.exit(json.dumps(result))
