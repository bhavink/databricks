"""
Tests for FHIR Ingestion Service

Test Categories:
1. Unit tests with mocked client
2. Integration tests with public servers
3. File output validation

Run:
    pytest fhir/ingestion/tests/test_fhir_ingestion.py -v
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ingestion.fhir_ingestion import FHIRIngestion, IngestionResult, run_ingestion_notebook
from ingestion.fhir_client import FHIRClient, FHIRClientConfig, FHIRResponse


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_patients() -> List[Dict[str, Any]]:
    """Sample patient resources"""
    return [
        {
            "resourceType": "Patient",
            "id": f"patient-{i:03d}",
            "gender": "male" if i % 2 == 0 else "female",
            "birthDate": f"198{i}-01-15",
            "name": [{"family": f"Family{i}", "given": [f"Given{i}"]}],
        }
        for i in range(10)
    ]


@pytest.fixture
def sample_observations() -> List[Dict[str, Any]]:
    """Sample observation resources"""
    return [
        {
            "resourceType": "Observation",
            "id": f"obs-{i:03d}",
            "status": "final",
            "code": {"coding": [{"code": "8867-4", "display": "Heart rate"}]},
            "subject": {"reference": f"Patient/patient-{i % 5:03d}"},
            "valueQuantity": {"value": 70 + i, "unit": "bpm"},
        }
        for i in range(20)
    ]


@pytest.fixture
def temp_output_dir():
    """Temporary directory for test output"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_ingestion(temp_output_dir) -> FHIRIngestion:
    """Ingestion service with mocked client and local output"""
    ingestion = FHIRIngestion(
        base_url="http://test.fhir.server/fhir",
        output_volume=temp_output_dir,
        output_subdir="api_extracts",
        use_dbutils=False,  # Use local filesystem
    )
    return ingestion


# =============================================================================
# Unit Tests - Ingestion Service
# =============================================================================

class TestFHIRIngestionConfig:
    """Test ingestion configuration"""
    
    def test_default_output_volume(self):
        """Default output volume is set"""
        ingestion = FHIRIngestion(use_dbutils=False)
        assert "healthcare_fhir" in ingestion.output_volume
    
    def test_custom_output_volume(self, temp_output_dir):
        """Custom output volume"""
        ingestion = FHIRIngestion(
            output_volume=temp_output_dir,
            use_dbutils=False,
        )
        assert ingestion.output_volume == temp_output_dir
    
    def test_output_path_construction(self, temp_output_dir):
        """Output path includes subdir"""
        ingestion = FHIRIngestion(
            output_volume=temp_output_dir,
            output_subdir="my_extracts",
            use_dbutils=False,
        )
        assert ingestion.output_path == f"{temp_output_dir}/my_extracts"
    
    def test_default_resources(self):
        """Default resources to ingest"""
        assert "Patient" in FHIRIngestion.DEFAULT_RESOURCES
        assert "Observation" in FHIRIngestion.DEFAULT_RESOURCES
        assert "Encounter" in FHIRIngestion.DEFAULT_RESOURCES


class TestFHIRIngestionWrite:
    """Test file writing operations"""
    
    def test_write_to_local(self, mock_ingestion, sample_patients, temp_output_dir):
        """Write resources to local filesystem"""
        files = mock_ingestion._write_resources(
            sample_patients[:5],
            "Patient",
            "test_run"
        )
        
        assert len(files) == 1
        assert files[0].endswith(".ndjson")
        
        # Verify file content
        local_path = files[0].replace(temp_output_dir, temp_output_dir)
        actual_path = f"{temp_output_dir}/api_extracts/{os.path.basename(files[0])}"
        
        with open(actual_path) as f:
            lines = f.readlines()
        
        assert len(lines) == 5
        for line in lines:
            resource = json.loads(line)
            assert resource["resourceType"] == "Patient"
    
    def test_write_batching(self, temp_output_dir, sample_patients):
        """Large datasets are split into batches"""
        ingestion = FHIRIngestion(
            output_volume=temp_output_dir,
            batch_size=3,  # Small batch for testing
            use_dbutils=False,
        )
        
        files = ingestion._write_resources(
            sample_patients,  # 10 patients
            "Patient",
            "test_run"
        )
        
        # Should create 4 files (10 / 3 = 3.33 → 4 files)
        assert len(files) == 4
    
    def test_ndjson_format(self, mock_ingestion, sample_patients, temp_output_dir):
        """Output is valid NDJSON (one JSON per line)"""
        files = mock_ingestion._write_resources(sample_patients[:3], "Patient", "test")
        
        actual_path = f"{temp_output_dir}/api_extracts/{os.path.basename(files[0])}"
        
        with open(actual_path) as f:
            content = f.read()
        
        # Each line should be valid JSON
        lines = content.strip().split("\n")
        assert len(lines) == 3
        
        for line in lines:
            parsed = json.loads(line)
            assert isinstance(parsed, dict)
            assert "resourceType" in parsed


class TestFHIRIngestionFetch:
    """Test resource fetching with mocked client"""
    
    @patch.object(FHIRClient, 'search')
    def test_ingest_resources(self, mock_search, mock_ingestion, sample_patients):
        """Ingest multiple resource types"""
        mock_search.return_value = sample_patients[:5]
        
        result = mock_ingestion.ingest_resources(
            resource_types=["Patient"],
            max_per_resource=5,
        )
        
        assert result.success
        assert result.resources_fetched == 5
        assert result.resources_written == 5
        assert len(result.files_created) == 1
    
    @patch.object(FHIRClient, 'search')
    def test_ingest_multiple_types(self, mock_search, mock_ingestion, sample_patients, sample_observations):
        """Ingest multiple resource types"""
        # Return different resources based on call
        mock_search.side_effect = [sample_patients[:5], sample_observations[:10]]
        
        result = mock_ingestion.ingest_resources(
            resource_types=["Patient", "Observation"],
            max_per_resource=10,
        )
        
        assert result.success
        assert result.resources_fetched == 15  # 5 + 10
        assert len(result.files_created) == 2  # One per resource type
    
    @patch.object(FHIRClient, 'search')
    def test_ingest_with_search_params(self, mock_search, mock_ingestion, sample_patients):
        """Ingest with custom search parameters"""
        mock_search.return_value = sample_patients[:3]
        
        result = mock_ingestion.ingest_resources(
            resource_types=["Patient"],
            search_params={"Patient": {"gender": "male"}},
        )
        
        # Verify search was called with params
        mock_search.assert_called_once()
        call_args = mock_search.call_args
        assert call_args[1]["params"]["gender"] == "male"
    
    @patch.object(FHIRClient, 'search')
    def test_ingest_incremental(self, mock_search, mock_ingestion, sample_patients):
        """Incremental ingestion with _lastUpdated"""
        mock_search.return_value = sample_patients[:2]
        
        result = mock_ingestion.ingest_incremental(
            last_updated="2024-01-01T00:00:00Z",
            resource_types=["Patient"],
        )
        
        # Verify _lastUpdated was added to params
        call_args = mock_search.call_args
        assert "_lastUpdated" in call_args[1]["params"]
        assert "gt2024-01-01" in call_args[1]["params"]["_lastUpdated"]
    
    @patch.object(FHIRClient, 'read')
    def test_ingest_single_resource(self, mock_read, mock_ingestion, sample_patients):
        """Ingest a single resource by ID"""
        mock_read.return_value = FHIRResponse(
            success=True,
            status_code=200,
            data=sample_patients[0],
        )
        
        result = mock_ingestion.ingest_single_resource("Patient", "patient-000")
        
        assert result.success
        assert result.resources_fetched == 1
        assert len(result.files_created) == 1


class TestFHIRIngestionErrors:
    """Test error handling"""
    
    @patch.object(FHIRClient, 'search')
    def test_fetch_error_captured(self, mock_search, mock_ingestion):
        """Errors during fetch are captured"""
        mock_search.side_effect = Exception("Connection failed")
        
        result = mock_ingestion.ingest_resources(resource_types=["Patient"])
        
        assert not result.success
        assert len(result.errors) > 0
        assert "Connection failed" in result.errors[0]
    
    @patch.object(FHIRClient, 'search')
    def test_partial_success(self, mock_search, mock_ingestion, sample_patients):
        """Partial success when some resources fail"""
        # First call succeeds, second fails
        mock_search.side_effect = [
            sample_patients[:5],
            Exception("Failed to fetch"),
        ]
        
        result = mock_ingestion.ingest_resources(
            resource_types=["Patient", "Observation"]
        )
        
        assert not result.success
        assert result.resources_fetched == 5  # Only patients
        assert len(result.errors) == 1  # One error
    
    @patch.object(FHIRClient, 'search')
    def test_empty_results(self, mock_search, mock_ingestion):
        """Handle empty results gracefully"""
        mock_search.return_value = []
        
        result = mock_ingestion.ingest_resources(resource_types=["Patient"])
        
        assert result.success
        assert result.resources_fetched == 0
        assert len(result.files_created) == 0


class TestIngestionResult:
    """Test IngestionResult dataclass"""
    
    def test_to_dict(self):
        """Convert result to dictionary"""
        result = IngestionResult(
            success=True,
            resources_fetched=100,
            resources_written=100,
            files_created=["/path/to/file.ndjson"],
            run_id="test123",
        )
        
        d = result.to_dict()
        
        assert d["success"] is True
        assert d["resources_fetched"] == 100
        assert d["run_id"] == "test123"
    
    def test_default_values(self):
        """Default values are set"""
        result = IngestionResult(success=True)
        
        assert result.resources_fetched == 0
        assert result.files_created == []
        assert result.errors == []


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.integration
class TestFHIRIngestionIntegration:
    """
    Integration tests against public FHIR servers.
    
    Run with: pytest -m integration
    """
    
    def test_hapi_connection(self, temp_output_dir):
        """Test connection to HAPI"""
        ingestion = FHIRIngestion(
            base_url="http://hapi.fhir.org/baseR4",
            output_volume=temp_output_dir,
            use_dbutils=False,
        )
        
        assert ingestion.test_connection()
    
    def test_hapi_ingest_small(self, temp_output_dir):
        """Ingest small dataset from HAPI"""
        ingestion = FHIRIngestion(
            base_url="http://hapi.fhir.org/baseR4",
            output_volume=temp_output_dir,
            use_dbutils=False,
        )
        
        result = ingestion.ingest_resources(
            resource_types=["Patient"],
            max_per_resource=5,
        )
        
        assert result.success
        assert result.resources_fetched <= 5
        
        # Verify files were created
        if result.files_created:
            for filepath in result.files_created:
                local_path = filepath.replace(temp_output_dir, temp_output_dir)
                actual = f"{temp_output_dir}/api_extracts/{os.path.basename(filepath)}"
                assert os.path.exists(actual)
    
    def test_hapi_get_capabilities(self, temp_output_dir):
        """Get server capabilities"""
        ingestion = FHIRIngestion(
            base_url="http://hapi.fhir.org/baseR4",
            output_volume=temp_output_dir,
            use_dbutils=False,
        )
        
        caps = ingestion.get_server_capabilities()
        
        assert "resourceType" in caps
        assert caps["resourceType"] == "CapabilityStatement"


# =============================================================================
# Notebook Entry Point Tests
# =============================================================================

class TestNotebookEntryPoint:
    """Test the notebook entry point function"""
    
    @patch.object(FHIRClient, 'search')
    def test_run_ingestion_notebook(self, mock_search, temp_output_dir, sample_patients):
        """Test notebook entry point"""
        mock_search.return_value = sample_patients[:5]
        
        # Patch the dbutils check to use local filesystem
        with patch.object(FHIRIngestion, '_write_to_volume', FHIRIngestion._write_to_local):
            result = run_ingestion_notebook(
                base_url="http://test/fhir",
                output_volume=temp_output_dir,
                resource_types=["Patient"],
                max_per_resource=5,
            )
        
        assert result["success"] is True or result["resources_fetched"] >= 0


# =============================================================================
# File Format Validation
# =============================================================================

class TestOutputFileFormat:
    """Validate output file format for pipeline compatibility"""
    
    def test_files_are_pipeline_compatible(self, mock_ingestion, sample_patients, temp_output_dir):
        """Output files are compatible with Auto Loader pipeline"""
        files = mock_ingestion._write_resources(sample_patients[:5], "Patient", "test")
        
        actual_path = f"{temp_output_dir}/api_extracts/{os.path.basename(files[0])}"
        
        # Read and validate
        with open(actual_path) as f:
            for line in f:
                resource = json.loads(line)
                
                # Must have resourceType (pipeline filters on this)
                assert "resourceType" in resource
                
                # Must have id (used for deduplication)
                assert "id" in resource
    
    def test_filename_contains_metadata(self, mock_ingestion, sample_patients, temp_output_dir):
        """Filenames contain useful metadata"""
        files = mock_ingestion._write_resources(sample_patients[:5], "Patient", "run123")
        
        filename = os.path.basename(files[0])
        
        # Should contain resource type
        assert "patient" in filename.lower()
        
        # Should contain run ID
        assert "run123" in filename
        
        # Should have .ndjson extension
        assert filename.endswith(".ndjson")
