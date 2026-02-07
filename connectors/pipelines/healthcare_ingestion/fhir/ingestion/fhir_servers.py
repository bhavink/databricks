"""
FHIR Server Presets

Pre-configured settings for popular public FHIR servers.
Users can easily swap servers by name instead of configuring URLs/auth.

Usage:
    from fhir_servers import get_server_config, SERVERS
    
    # List available servers
    print(SERVERS.keys())  # ['hapi', 'synthea', 'smart_sandbox', ...]
    
    # Get config by name
    config = get_server_config("synthea")
    client = FHIRClient(config=config)
    
    # Or use shorthand
    client = FHIRClient.from_preset("hapi")
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
from .fhir_client import FHIRClientConfig


@dataclass
class FHIRServerInfo:
    """Information about a FHIR server"""
    name: str
    base_url: str
    description: str
    auth_type: str = "none"
    fhir_version: str = "R4"
    # Server-specific settings
    requests_per_second: float = 10.0
    default_page_size: int = 100
    # Capabilities
    supports_search: bool = True
    supports_history: bool = False
    supports_batch: bool = False
    # Notes
    notes: str = ""
    # Auth details (for servers requiring auth)
    token_url: Optional[str] = None
    scope: str = "system/*.read"


# =============================================================================
# Public FHIR Server Registry
# =============================================================================

SERVERS: Dict[str, FHIRServerInfo] = {
    # -------------------------------------------------------------------------
    # HAPI FHIR - Most Popular Public Server
    # -------------------------------------------------------------------------
    "hapi": FHIRServerInfo(
        name="HAPI FHIR Public",
        base_url="http://hapi.fhir.org/baseR4",
        description="Most popular public FHIR server. No auth required. Good for testing.",
        auth_type="none",
        fhir_version="R4",
        requests_per_second=10.0,
        default_page_size=100,
        supports_search=True,
        supports_history=True,
        supports_batch=True,
        notes="May be slow during peak times. Data is synthetic but unstructured.",
    ),
    
    # -------------------------------------------------------------------------
    # Synthea - Realistic Synthetic Data
    # -------------------------------------------------------------------------
    "synthea": FHIRServerInfo(
        name="Synthea (MITRE)",
        base_url="https://syntheticmass.mitre.org/v1/fhir",
        description="Realistic synthetic patient data from Synthea generator.",
        auth_type="none",
        fhir_version="R4",
        requests_per_second=5.0,  # Be gentle with this server
        default_page_size=50,
        supports_search=True,
        supports_history=False,
        supports_batch=False,
        notes="High-quality synthetic data. Massachusetts population. Rate limited.",
    ),
    
    # -------------------------------------------------------------------------
    # SMART Health IT Sandbox
    # -------------------------------------------------------------------------
    "smart_sandbox": FHIRServerInfo(
        name="SMART Health IT Sandbox",
        base_url="https://launch.smarthealthit.org/v/r4/fhir",
        description="SMART on FHIR sandbox for testing OAuth flows.",
        auth_type="none",  # Open endpoint available
        fhir_version="R4",
        requests_per_second=10.0,
        default_page_size=100,
        supports_search=True,
        supports_history=True,
        supports_batch=True,
        notes="Also supports full SMART OAuth for testing authenticated flows.",
    ),
    
    # -------------------------------------------------------------------------
    # HL7 Official Test Server
    # -------------------------------------------------------------------------
    "hl7_test": FHIRServerInfo(
        name="HL7 FHIR Test Server",
        base_url="http://test.fhir.org/r4",
        description="Official HL7 test server.",
        auth_type="none",
        fhir_version="R4",
        requests_per_second=5.0,
        default_page_size=50,
        supports_search=True,
        supports_history=True,
        supports_batch=True,
        notes="May have limited data. Good for spec compliance testing.",
    ),
    
    # -------------------------------------------------------------------------
    # Cerner Sandbox (requires registration)
    # -------------------------------------------------------------------------
    "cerner_sandbox": FHIRServerInfo(
        name="Cerner Code Sandbox",
        base_url="https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d",
        description="Cerner's open sandbox (no auth for read).",
        auth_type="none",
        fhir_version="R4",
        requests_per_second=5.0,
        default_page_size=50,
        supports_search=True,
        supports_history=False,
        supports_batch=False,
        notes="Real EHR vendor. Good for testing production-like responses.",
    ),
    
    # -------------------------------------------------------------------------
    # HAPI FHIR - STU3 (for legacy testing)
    # -------------------------------------------------------------------------
    "hapi_stu3": FHIRServerInfo(
        name="HAPI FHIR STU3",
        base_url="http://hapi.fhir.org/baseDstu3",
        description="HAPI FHIR STU3 for legacy system testing.",
        auth_type="none",
        fhir_version="STU3",
        requests_per_second=10.0,
        default_page_size=100,
        supports_search=True,
        supports_history=True,
        supports_batch=True,
        notes="Use for testing compatibility with older FHIR versions.",
    ),
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_server_config(server_name: str) -> FHIRClientConfig:
    """
    Get FHIRClientConfig for a named server.
    
    Args:
        server_name: One of: hapi, synthea, smart_sandbox, hl7_test, cerner_sandbox, hapi_stu3
        
    Returns:
        FHIRClientConfig ready to use with FHIRClient
        
    Example:
        config = get_server_config("synthea")
        client = FHIRClient(config=config)
    """
    if server_name not in SERVERS:
        available = ", ".join(SERVERS.keys())
        raise ValueError(f"Unknown server '{server_name}'. Available: {available}")
    
    server = SERVERS[server_name]
    
    return FHIRClientConfig(
        base_url=server.base_url,
        auth_type=server.auth_type,
        token_url=server.token_url,
        scope=server.scope,
        requests_per_second=server.requests_per_second,
        default_page_size=server.default_page_size,
    )


def list_servers() -> List[Dict]:
    """
    List all available server presets.
    
    Returns:
        List of server info dictionaries
    """
    return [
        {
            "name": key,
            "display_name": server.name,
            "url": server.base_url,
            "description": server.description,
            "auth": server.auth_type,
            "fhir_version": server.fhir_version,
        }
        for key, server in SERVERS.items()
    ]


def print_servers():
    """Print formatted list of available servers"""
    print("\n" + "="*70)
    print("Available FHIR Servers")
    print("="*70)
    
    for key, server in SERVERS.items():
        print(f"\n  [{key}]")
        print(f"    Name: {server.name}")
        print(f"    URL:  {server.base_url}")
        print(f"    Auth: {server.auth_type}")
        print(f"    Note: {server.notes}")
    
    print("\n" + "="*70)


# =============================================================================
# Extend FHIRClient with preset support
# =============================================================================

def _add_preset_support():
    """Add from_preset classmethod to FHIRClient"""
    from .fhir_client import FHIRClient
    
    @classmethod
    def from_preset(cls, server_name: str) -> "FHIRClient":
        """
        Create FHIRClient from a server preset.
        
        Args:
            server_name: One of: hapi, synthea, smart_sandbox, etc.
            
        Example:
            client = FHIRClient.from_preset("synthea")
            patients = client.search("Patient", max_results=10)
        """
        config = get_server_config(server_name)
        return cls(config=config)
    
    FHIRClient.from_preset = from_preset

# Apply the extension
try:
    _add_preset_support()
except ImportError:
    pass  # Will be applied when module is properly imported
