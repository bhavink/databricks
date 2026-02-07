"""
FHIR REST API Client

Handles authentication, pagination, rate limiting, and error handling
for FHIR R4 REST API interactions.

Public Test Servers (no auth required):
- HAPI FHIR: http://hapi.fhir.org/baseR4
- Synthea: https://syntheticmass.mitre.org/fhir

Usage:
    client = FHIRClient(base_url="http://hapi.fhir.org/baseR4")
    patients = client.search("Patient", params={"_count": 10})
    patient = client.read("Patient", "12345")
"""

import time
import logging
from typing import Optional, Dict, List, Any, Iterator
from dataclasses import dataclass, field
from datetime import datetime
import json

# Use httpx for async support, fallback to requests
try:
    import httpx
    HTTP_CLIENT = "httpx"
except ImportError:
    import requests
    HTTP_CLIENT = "requests"


logger = logging.getLogger(__name__)


@dataclass
class FHIRClientConfig:
    """Configuration for FHIR client"""
    base_url: str
    # Authentication
    auth_type: str = "none"  # none, basic, bearer, smart
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    scope: str = "system/*.read"
    # Rate limiting
    requests_per_second: float = 10.0
    retry_count: int = 3
    retry_delay: float = 1.0
    # Timeouts
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    # Pagination
    default_page_size: int = 100
    max_pages: int = 1000  # Safety limit


@dataclass
class FHIRResponse:
    """Standardized response from FHIR operations"""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    request_time_ms: float = 0.0


class FHIRClientError(Exception):
    """Base exception for FHIR client errors"""
    pass


class FHIRAuthError(FHIRClientError):
    """Authentication failed"""
    pass


class FHIRRateLimitError(FHIRClientError):
    """Rate limit exceeded"""
    pass


class FHIRNotFoundError(FHIRClientError):
    """Resource not found"""
    pass


class FHIRClient:
    """
    FHIR R4 REST API Client
    
    Supports:
    - Multiple auth types (none, basic, bearer, SMART on FHIR)
    - Automatic pagination
    - Rate limiting
    - Retry with exponential backoff
    - Bundle extraction
    """
    
    # Public test servers (no auth required)
    PUBLIC_SERVERS = {
        "hapi": "http://hapi.fhir.org/baseR4",
        "synthea": "https://syntheticmass.mitre.org/fhir",
    }
    
    SUPPORTED_RESOURCES = [
        "Patient", "Observation", "Encounter", "Condition",
        "MedicationRequest", "Immunization", "DiagnosticReport",
        "Procedure", "AllergyIntolerance", "CarePlan"
    ]
    
    def __init__(self, config: Optional[FHIRClientConfig] = None, base_url: Optional[str] = None):
        """
        Initialize FHIR client.
        
        Args:
            config: Full configuration object
            base_url: Shortcut for simple setup (uses defaults)
        """
        if config:
            self.config = config
        elif base_url:
            self.config = FHIRClientConfig(base_url=base_url)
        else:
            # Default to HAPI public server
            self.config = FHIRClientConfig(base_url=self.PUBLIC_SERVERS["hapi"])
        
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None
        self._last_request_time: float = 0.0
        self._request_count: int = 0
    
    # =========================================================================
    # Core FHIR Operations
    # =========================================================================
    
    def read(self, resource_type: str, resource_id: str) -> FHIRResponse:
        """
        Read a single resource by ID.
        
        GET [base]/[resource_type]/[id]
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient")
            resource_id: Resource ID
            
        Returns:
            FHIRResponse with the resource
        """
        url = f"{self.config.base_url}/{resource_type}/{resource_id}"
        return self._request("GET", url)
    
    def search(
        self,
        resource_type: str,
        params: Optional[Dict[str, Any]] = None,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for resources with automatic pagination.
        
        GET [base]/[resource_type]?[params]
        
        Args:
            resource_type: FHIR resource type
            params: Search parameters (e.g., {"_count": 100, "gender": "male"})
            max_results: Maximum total results to return (None = all)
            
        Returns:
            List of FHIR resources
        """
        params = params or {}
        if "_count" not in params:
            params["_count"] = self.config.default_page_size
        
        url = f"{self.config.base_url}/{resource_type}"
        return list(self._paginate(url, params, max_results))
    
    def search_iter(
        self,
        resource_type: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Search with lazy iteration (memory efficient for large datasets).
        
        Yields resources one at a time without loading all into memory.
        """
        params = params or {}
        if "_count" not in params:
            params["_count"] = self.config.default_page_size
        
        url = f"{self.config.base_url}/{resource_type}"
        yield from self._paginate(url, params)
    
    def get_capability_statement(self) -> FHIRResponse:
        """
        Get server capability statement (metadata).
        
        GET [base]/metadata
        """
        url = f"{self.config.base_url}/metadata"
        return self._request("GET", url)
    
    # =========================================================================
    # Pagination
    # =========================================================================
    
    def _paginate(
        self,
        url: str,
        params: Dict[str, Any],
        max_results: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Handle FHIR Bundle pagination.
        
        Yields individual resources from paginated Bundle responses.
        """
        total_yielded = 0
        page = 0
        
        while url and page < self.config.max_pages:
            # First request includes params, subsequent use next link
            if page == 0:
                response = self._request("GET", url, params=params)
            else:
                response = self._request("GET", url)
            
            if not response.success or not response.data:
                logger.error(f"Pagination failed at page {page}: {response.error}")
                break
            
            bundle = response.data
            
            # Extract resources from Bundle entries
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
            logger.debug(f"Fetched page {page}, total resources: {total_yielded}")
        
        if page >= self.config.max_pages:
            logger.warning(f"Reached max pages limit ({self.config.max_pages})")
    
    # =========================================================================
    # HTTP Layer
    # =========================================================================
    
    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> FHIRResponse:
        """
        Make HTTP request with rate limiting, retries, and error handling.
        """
        # Rate limiting
        self._rate_limit()
        
        # Get auth headers
        headers = self._get_headers()
        
        # Retry loop
        last_error = None
        for attempt in range(self.config.retry_count):
            try:
                start_time = time.time()
                
                if HTTP_CLIENT == "httpx":
                    response = self._httpx_request(method, url, headers, params, data)
                else:
                    response = self._requests_request(method, url, headers, params, data)
                
                request_time = (time.time() - start_time) * 1000
                self._request_count += 1
                
                # Handle response
                if response.status_code == 200:
                    return FHIRResponse(
                        success=True,
                        status_code=response.status_code,
                        data=response.json() if response.text else None,
                        headers=dict(response.headers),
                        request_time_ms=request_time
                    )
                elif response.status_code == 404:
                    return FHIRResponse(
                        success=False,
                        status_code=404,
                        error="Resource not found",
                        request_time_ms=request_time
                    )
                elif response.status_code == 401:
                    raise FHIRAuthError("Authentication failed")
                elif response.status_code == 429:
                    # Rate limited - exponential backoff
                    retry_after = int(response.headers.get("Retry-After", self.config.retry_delay * (2 ** attempt)))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
            
            # Wait before retry
            if attempt < self.config.retry_count - 1:
                time.sleep(self.config.retry_delay * (2 ** attempt))
        
        return FHIRResponse(
            success=False,
            status_code=0,
            error=last_error or "Unknown error"
        )
    
    def _httpx_request(self, method, url, headers, params, data):
        """Make request using httpx"""
        with httpx.Client(
            timeout=httpx.Timeout(self.config.connect_timeout, read=self.config.read_timeout)
        ) as client:
            return client.request(method, url, headers=headers, params=params, json=data)
    
    def _requests_request(self, method, url, headers, params, data):
        """Make request using requests library"""
        return requests.request(
            method, url,
            headers=headers,
            params=params,
            json=data,
            timeout=(self.config.connect_timeout, self.config.read_timeout)
        )
    
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
        """Get request headers including auth"""
        headers = {
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json",
        }
        
        if self.config.auth_type == "none":
            pass
        elif self.config.auth_type == "basic":
            import base64
            creds = base64.b64encode(
                f"{self.config.username}:{self.config.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"
        elif self.config.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self.config.token}"
        elif self.config.auth_type == "smart":
            token = self._get_smart_token()
            headers["Authorization"] = f"Bearer {token}"
        
        return headers
    
    def _get_smart_token(self) -> str:
        """Get SMART on FHIR OAuth2 token"""
        # Check if cached token is still valid
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token
        
        if not self.config.token_url:
            raise FHIRAuthError("token_url required for SMART auth")
        
        # Request new token
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
            raise FHIRAuthError(f"Token request failed: {response.text}")
        
        token_data = response.json()
        self._token = token_data["access_token"]
        
        # Set expiry (default 1 hour if not provided)
        expires_in = token_data.get("expires_in", 3600)
        from datetime import timedelta
        self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
        
        return self._token
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    def test_connection(self) -> bool:
        """Test if server is reachable and responding"""
        try:
            response = self.get_capability_statement()
            return response.success
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "base_url": self.config.base_url,
            "auth_type": self.config.auth_type,
            "request_count": self._request_count,
        }
