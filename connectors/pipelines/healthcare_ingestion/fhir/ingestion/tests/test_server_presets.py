"""
Tests for FHIR Server Presets

Validates that server presets are correctly configured and usable.

Run:
    pytest test_server_presets.py -v -s
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ingestion.fhir_servers import (
    SERVERS,
    get_server_config,
    list_servers,
    FHIRServerInfo,
)
from ingestion.fhir_client import FHIRClient, FHIRClientConfig
from ingestion.fhir_ingestion import FHIRIngestion


class TestServerPresets:
    """Test server preset configuration"""
    
    def test_all_presets_defined(self):
        """All expected presets are defined"""
        expected = ["hapi", "synthea", "smart_sandbox", "hl7_test", "cerner_sandbox", "hapi_stu3"]
        for preset in expected:
            assert preset in SERVERS, f"Missing preset: {preset}"
        print(f"✓ All {len(expected)} presets defined")
    
    def test_preset_has_required_fields(self):
        """Each preset has required fields"""
        for name, server in SERVERS.items():
            assert server.name, f"{name}: missing name"
            assert server.base_url, f"{name}: missing base_url"
            assert server.base_url.startswith("http"), f"{name}: invalid URL"
            assert server.auth_type in ["none", "basic", "bearer", "smart"], f"{name}: invalid auth_type"
            assert server.requests_per_second > 0, f"{name}: invalid rate limit"
            print(f"✓ {name}: all required fields present")
    
    def test_get_server_config_returns_valid_config(self):
        """get_server_config returns valid FHIRClientConfig"""
        for name in SERVERS:
            config = get_server_config(name)
            assert isinstance(config, FHIRClientConfig)
            assert config.base_url == SERVERS[name].base_url
            assert config.auth_type == SERVERS[name].auth_type
            print(f"✓ {name}: config valid")
    
    def test_get_server_config_invalid_name(self):
        """get_server_config raises error for invalid name"""
        with pytest.raises(ValueError) as exc_info:
            get_server_config("nonexistent_server")
        assert "Unknown server" in str(exc_info.value)
        print("✓ Invalid server name raises ValueError")
    
    def test_list_servers_returns_all(self):
        """list_servers returns all servers"""
        servers = list_servers()
        assert len(servers) == len(SERVERS)
        for s in servers:
            assert "name" in s
            assert "url" in s
            assert "description" in s
        print(f"✓ list_servers returns {len(servers)} servers")


class TestFHIRClientPresets:
    """Test FHIRClient.from_preset"""
    
    def test_client_from_preset_hapi(self):
        """Create client from HAPI preset"""
        client = FHIRClient.from_preset("hapi")
        assert "hapi.fhir.org" in client.config.base_url
        assert client.config.auth_type == "none"
        print("✓ FHIRClient.from_preset('hapi') works")
    
    def test_client_from_preset_synthea(self):
        """Create client from Synthea preset"""
        client = FHIRClient.from_preset("synthea")
        assert "syntheticmass.mitre.org" in client.config.base_url
        # Synthea has lower rate limit
        assert client.config.requests_per_second == 5.0
        print("✓ FHIRClient.from_preset('synthea') works")
    
    def test_client_from_preset_all(self):
        """Create client from all presets"""
        for name in SERVERS:
            client = FHIRClient.from_preset(name)
            assert client.config.base_url == SERVERS[name].base_url
            print(f"✓ FHIRClient.from_preset('{name}') works")


class TestFHIRIngestionPresets:
    """Test FHIRIngestion.from_preset"""
    
    def test_ingestion_from_preset_hapi(self):
        """Create ingestion from HAPI preset"""
        ingestion = FHIRIngestion.from_preset(
            "hapi",
            output_volume="/tmp/test",
            use_dbutils=False,
        )
        assert "hapi.fhir.org" in ingestion.client.config.base_url
        print("✓ FHIRIngestion.from_preset('hapi') works")
    
    def test_ingestion_from_preset_synthea(self):
        """Create ingestion from Synthea preset"""
        ingestion = FHIRIngestion.from_preset(
            "synthea",
            output_volume="/tmp/test",
            use_dbutils=False,
        )
        assert "syntheticmass.mitre.org" in ingestion.client.config.base_url
        print("✓ FHIRIngestion.from_preset('synthea') works")
    
    def test_available_presets_list(self):
        """AVAILABLE_PRESETS class attribute is correct"""
        assert "hapi" in FHIRIngestion.AVAILABLE_PRESETS
        assert "synthea" in FHIRIngestion.AVAILABLE_PRESETS
        print(f"✓ FHIRIngestion.AVAILABLE_PRESETS: {FHIRIngestion.AVAILABLE_PRESETS}")


class TestPresetDisplay:
    """Test display/printing functions"""
    
    def test_list_servers_format(self):
        """list_servers returns properly formatted data"""
        servers = list_servers()
        for s in servers:
            assert isinstance(s["name"], str)
            assert isinstance(s["display_name"], str)
            assert isinstance(s["url"], str)
            assert isinstance(s["description"], str)
            assert isinstance(s["auth"], str)
            assert isinstance(s["fhir_version"], str)
        print("✓ list_servers format is correct")
    
    def test_server_notes_helpful(self):
        """Server notes provide useful guidance"""
        for name, server in SERVERS.items():
            assert server.notes, f"{name}: missing notes"
            assert len(server.notes) > 10, f"{name}: notes too short"
        print("✓ All servers have helpful notes")


# =============================================================================
# Integration Tests (hit real servers)
# =============================================================================

@pytest.mark.integration
class TestPresetIntegration:
    """
    Test that presets actually work against real servers.
    Run with: pytest -m integration
    """
    
    def test_hapi_preset_connection(self):
        """HAPI preset can connect"""
        client = FHIRClient.from_preset("hapi")
        assert client.test_connection(), "HAPI connection failed"
        print("✓ HAPI preset connects successfully")
    
    def test_synthea_preset_connection(self):
        """Synthea preset can connect"""
        client = FHIRClient.from_preset("synthea")
        # Synthea may be slow, just test it doesn't error
        try:
            connected = client.test_connection()
            print(f"✓ Synthea preset {'connected' if connected else 'did not connect (may be down)'}")
        except Exception as e:
            print(f"⚠ Synthea connection error (server may be down): {e}")
    
    def test_smart_sandbox_preset_connection(self):
        """SMART Sandbox preset can connect"""
        client = FHIRClient.from_preset("smart_sandbox")
        assert client.test_connection(), "SMART Sandbox connection failed"
        print("✓ SMART Sandbox preset connects successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "not integration"])
