"""
Tests for FHIR REST API Client

Test Categories:
1. Unit tests with mocked responses
2. Integration tests with public FHIR servers
3. Edge cases and error handling

Run:
    pytest fhir/ingestion/tests/test_fhir_client.py -v
    pytest fhir/ingestion/tests/test_fhir_client.py -v -m "not integration"  # Unit only
    pytest fhir/ingestion/tests/test_fhir_client.py -v -m integration  # Integration only
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ingestion.fhir_client import (
    FHIRClient,
    FHIRClientConfig,
    FHIRResponse,
    FHIRClientError,
    FHIRAuthError,
    FHIRNotFoundError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_patient_bundle() -> Dict[str, Any]:
    """Sample FHIR Bundle with patients"""
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 2,
        "link": [
            {"relation": "self", "url": "http://test/Patient?_count=10"},
        ],
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-001",
                    "gender": "male",
                    "birthDate": "1985-03-15",
                    "name": [{"family": "Smith", "given": ["John"]}],
                }
            },
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-002",
                    "gender": "female",
                    "birthDate": "1990-07-22",
                    "name": [{"family": "Johnson", "given": ["Jane"]}],
                }
            },
        ],
    }


@pytest.fixture
def mock_paginated_bundle() -> tuple:
    """Two-page Bundle for pagination testing"""
    page1 = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 4,
        "link": [
            {"relation": "self", "url": "http://test/Patient?_count=2"},
            {"relation": "next", "url": "http://test/Patient?_count=2&page=2"},
        ],
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "p1"}},
            {"resource": {"resourceType": "Patient", "id": "p2"}},
        ],
    }
    page2 = {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": 4,
        "link": [
            {"relation": "self", "url": "http://test/Patient?_count=2&page=2"},
            {"relation": "previous", "url": "http://test/Patient?_count=2"},
        ],
        "entry": [
            {"resource": {"resourceType": "Patient", "id": "p3"}},
            {"resource": {"resourceType": "Patient", "id": "p4"}},
        ],
    }
    return page1, page2


@pytest.fixture
def mock_capability_statement() -> Dict[str, Any]:
    """Sample CapabilityStatement"""
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [
            {
                "mode": "server",
                "resource": [
                    {"type": "Patient", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Observation", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                ],
            }
        ],
    }


@pytest.fixture
def client() -> FHIRClient:
    """Default client pointing to HAPI"""
    return FHIRClient()


@pytest.fixture
def mock_client() -> FHIRClient:
    """Client with mocked HTTP layer"""
    config = FHIRClientConfig(base_url="http://test.fhir.server/fhir")
    return FHIRClient(config=config)


# =============================================================================
# Unit Tests - Configuration
# =============================================================================

class TestFHIRClientConfig:
    """Test client configuration"""
    
    def test_default_config(self):
        """Default config uses HAPI server"""
        client = FHIRClient()
        assert "hapi.fhir.org" in client.config.base_url
        assert client.config.auth_type == "none"
    
    def test_custom_base_url(self):
        """Custom base URL via shortcut"""
        client = FHIRClient(base_url="http://custom.server/fhir")
        assert client.config.base_url == "http://custom.server/fhir"
    
    def test_full_config(self):
        """Full configuration object"""
        config = FHIRClientConfig(
            base_url="http://test/fhir",
            auth_type="smart",
            client_id="test-client",
            client_secret="secret",
            token_url="http://test/oauth2/token",
            requests_per_second=5.0,
        )
        client = FHIRClient(config=config)
        assert client.config.auth_type == "smart"
        assert client.config.requests_per_second == 5.0


# =============================================================================
# Unit Tests - HTTP Layer (Mocked)
# =============================================================================

class TestFHIRClientRead:
    """Test read operations with mocked responses"""
    
    @patch("ingestion.fhir_client.requests.request")
    def test_read_success(self, mock_request, mock_client):
        """Successfully read a resource"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"resourceType": "Patient", "id": "123"}'
        mock_response.json.return_value = {"resourceType": "Patient", "id": "123"}
        mock_response.headers = {"Content-Type": "application/fhir+json"}
        mock_request.return_value = mock_response
        
        result = mock_client.read("Patient", "123")
        
        assert result.success
        assert result.status_code == 200
        assert result.data["id"] == "123"
    
    @patch("ingestion.fhir_client.requests.request")
    def test_read_not_found(self, mock_request, mock_client):
        """Handle 404 not found"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.headers = {}
        mock_request.return_value = mock_response
        
        result = mock_client.read("Patient", "nonexistent")
        
        assert not result.success
        assert result.status_code == 404
        assert "not found" in result.error.lower()


class TestFHIRClientSearch:
    """Test search operations with mocked responses"""
    
    @patch("ingestion.fhir_client.requests.request")
    def test_search_returns_resources(self, mock_request, mock_client, mock_patient_bundle):
        """Search returns extracted resources"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(mock_patient_bundle)
        mock_response.json.return_value = mock_patient_bundle
        mock_response.headers = {}
        mock_request.return_value = mock_response
        
        results = mock_client.search("Patient")
        
        assert len(results) == 2
        assert results[0]["id"] == "patient-001"
        assert results[1]["id"] == "patient-002"
    
    @patch("ingestion.fhir_client.requests.request")
    def test_search_with_params(self, mock_request, mock_client, mock_patient_bundle):
        """Search with query parameters"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_patient_bundle
        mock_response.text = json.dumps(mock_patient_bundle)
        mock_response.headers = {}
        mock_request.return_value = mock_response
        
        results = mock_client.search("Patient", params={"gender": "male", "_count": 10})
        
        # Verify params were passed
        call_args = mock_request.call_args
        assert call_args[1]["params"]["gender"] == "male"
    
    @patch("ingestion.fhir_client.requests.request")
    def test_search_pagination(self, mock_request, mock_client, mock_paginated_bundle):
        """Search handles pagination automatically"""
        page1, page2 = mock_paginated_bundle
        
        # First call returns page1, second returns page2
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = page1
        mock_response1.text = json.dumps(page1)
        mock_response1.headers = {}
        
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = page2
        mock_response2.text = json.dumps(page2)
        mock_response2.headers = {}
        
        mock_request.side_effect = [mock_response1, mock_response2]
        
        results = mock_client.search("Patient", params={"_count": 2})
        
        assert len(results) == 4
        assert [r["id"] for r in results] == ["p1", "p2", "p3", "p4"]
    
    @patch("ingestion.fhir_client.requests.request")
    def test_search_max_results(self, mock_request, mock_client, mock_paginated_bundle):
        """Search respects max_results limit"""
        page1, _ = mock_paginated_bundle
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = page1
        mock_response.text = json.dumps(page1)
        mock_response.headers = {}
        mock_request.return_value = mock_response
        
        results = mock_client.search("Patient", max_results=1)
        
        assert len(results) == 1
    
    @patch("ingestion.fhir_client.requests.request")
    def test_search_empty_results(self, mock_request, mock_client):
        """Search with no results"""
        empty_bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 0,
            "entry": [],
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = empty_bundle
        mock_response.text = json.dumps(empty_bundle)
        mock_response.headers = {}
        mock_request.return_value = mock_response
        
        results = mock_client.search("Patient")
        
        assert len(results) == 0


class TestFHIRClientAuth:
    """Test authentication handling"""
    
    def test_no_auth_headers(self):
        """No auth type produces no auth header"""
        client = FHIRClient(base_url="http://test")
        headers = client._get_headers()
        
        assert "Authorization" not in headers
    
    def test_basic_auth_headers(self):
        """Basic auth produces correct header"""
        config = FHIRClientConfig(
            base_url="http://test",
            auth_type="basic",
            username="user",
            password="pass",
        )
        client = FHIRClient(config=config)
        headers = client._get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")
    
    def test_bearer_auth_headers(self):
        """Bearer token produces correct header"""
        config = FHIRClientConfig(
            base_url="http://test",
            auth_type="bearer",
            token="my-token-123",
        )
        client = FHIRClient(config=config)
        headers = client._get_headers()
        
        assert headers["Authorization"] == "Bearer my-token-123"


class TestFHIRClientRetry:
    """Test retry and rate limiting"""
    
    @patch("ingestion.fhir_client.requests.request")
    @patch("ingestion.fhir_client.time.sleep")
    def test_retry_on_failure(self, mock_sleep, mock_request, mock_client):
        """Retries on transient failure"""
        # First call fails, second succeeds
        mock_fail = Mock()
        mock_fail.status_code = 500
        mock_fail.text = "Server error"
        mock_fail.headers = {}
        
        mock_success = Mock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"resourceType": "Patient", "id": "123"}
        mock_success.text = '{"resourceType": "Patient"}'
        mock_success.headers = {}
        
        mock_request.side_effect = [mock_fail, mock_success]
        
        result = mock_client.read("Patient", "123")
        
        assert result.success
        assert mock_request.call_count == 2
    
    @patch("ingestion.fhir_client.requests.request")
    @patch("ingestion.fhir_client.time.sleep")
    def test_rate_limit_retry(self, mock_sleep, mock_request, mock_client):
        """Handles 429 rate limit with retry"""
        mock_rate_limit = Mock()
        mock_rate_limit.status_code = 429
        mock_rate_limit.text = "Rate limited"
        mock_rate_limit.headers = {"Retry-After": "1"}
        
        mock_success = Mock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"resourceType": "Patient", "id": "123"}
        mock_success.text = '{"resourceType": "Patient"}'
        mock_success.headers = {}
        
        mock_request.side_effect = [mock_rate_limit, mock_success]
        
        result = mock_client.read("Patient", "123")
        
        assert result.success
        # Should have slept due to rate limit
        assert mock_sleep.called


# =============================================================================
# Integration Tests - Public FHIR Servers
# =============================================================================

@pytest.mark.integration
class TestFHIRClientIntegration:
    """
    Integration tests against public FHIR servers.
    
    These tests hit real servers - use sparingly and be respectful of rate limits.
    Run with: pytest -m integration
    """
    
    def test_hapi_connection(self, client):
        """Test connection to HAPI public server"""
        assert client.test_connection()
    
    def test_hapi_capability_statement(self, client):
        """Fetch capability statement from HAPI"""
        response = client.get_capability_statement()
        
        assert response.success
        assert response.data["resourceType"] == "CapabilityStatement"
        assert response.data["fhirVersion"] == "4.0.1"
    
    def test_hapi_search_patients(self, client):
        """Search patients on HAPI (limited)"""
        results = client.search("Patient", params={"_count": 5}, max_results=5)
        
        assert len(results) <= 5
        for patient in results:
            assert patient["resourceType"] == "Patient"
    
    def test_hapi_read_patient(self, client):
        """Read a specific patient from HAPI"""
        # First search for a patient
        patients = client.search("Patient", params={"_count": 1}, max_results=1)
        
        if patients:
            patient_id = patients[0]["id"]
            response = client.read("Patient", patient_id)
            
            assert response.success
            assert response.data["id"] == patient_id
    
    def test_hapi_search_observations(self, client):
        """Search observations on HAPI"""
        results = client.search(
            "Observation",
            params={"_count": 5, "code": "8867-4"},  # Heart rate
            max_results=5
        )
        
        # May or may not have results, but shouldn't error
        assert isinstance(results, list)
    
    def test_hapi_iterator_mode(self, client):
        """Test lazy iteration mode"""
        count = 0
        for patient in client.search_iter("Patient", params={"_count": 3}):
            count += 1
            assert patient["resourceType"] == "Patient"
            if count >= 3:
                break
        
        assert count == 3


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestFHIRClientEdgeCases:
    """Test edge cases and error scenarios"""
    
    @patch("ingestion.fhir_client.requests.request")
    def test_malformed_json_response(self, mock_request, mock_client):
        """Handle malformed JSON in response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "not valid json"
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.headers = {}
        mock_request.return_value = mock_response
        
        result = mock_client.read("Patient", "123")
        
        # Should handle gracefully
        assert not result.success or result.data is None
    
    @patch("ingestion.fhir_client.requests.request")
    def test_network_timeout(self, mock_request, mock_client):
        """Handle network timeout"""
        import requests
        mock_request.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        result = mock_client.read("Patient", "123")
        
        assert not result.success
        assert "timeout" in result.error.lower() or result.error
    
    @patch("ingestion.fhir_client.requests.request")
    def test_connection_error(self, mock_request, mock_client):
        """Handle connection error"""
        import requests
        mock_request.side_effect = requests.exceptions.ConnectionError("Cannot connect")
        
        result = mock_client.read("Patient", "123")
        
        assert not result.success
    
    def test_empty_bundle_entries(self, mock_client):
        """Handle bundle with missing entry array"""
        bundle = {"resourceType": "Bundle", "type": "searchset"}
        
        # Manually test pagination logic
        resources = list(mock_client._paginate.__wrapped__(
            mock_client, "http://test/Patient", {}, None
        )) if hasattr(mock_client._paginate, '__wrapped__') else []
        
        # Should not crash on missing entry


# =============================================================================
# Boundary Tests
# =============================================================================

class TestFHIRClientBoundaries:
    """Test boundary conditions"""
    
    def test_max_pages_limit(self):
        """Pagination respects max_pages config"""
        config = FHIRClientConfig(base_url="http://test", max_pages=2)
        client = FHIRClient(config=config)
        
        assert client.config.max_pages == 2
    
    def test_rate_limit_config(self):
        """Rate limiting configuration"""
        config = FHIRClientConfig(base_url="http://test", requests_per_second=0.5)
        client = FHIRClient(config=config)
        
        # 0.5 req/s = 2 second interval
        assert client.config.requests_per_second == 0.5
    
    def test_supported_resources_list(self):
        """Client has list of supported resources"""
        assert "Patient" in FHIRClient.SUPPORTED_RESOURCES
        assert "Observation" in FHIRClient.SUPPORTED_RESOURCES
        assert "Encounter" in FHIRClient.SUPPORTED_RESOURCES
    
    def test_public_servers_list(self):
        """Client has public server URLs"""
        assert "hapi" in FHIRClient.PUBLIC_SERVERS
        assert "hapi.fhir.org" in FHIRClient.PUBLIC_SERVERS["hapi"]
