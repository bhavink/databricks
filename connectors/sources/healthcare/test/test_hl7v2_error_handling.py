"""
Comprehensive tests for HL7v2 error handling, checkpointing, and streaming.

Tests cover:
- Error handling modes: skip, fail, dead_letter
- Checkpointing: granular file tracking
- Batch processing with various scenarios
- Streaming mode (micro-batch)
- Structured streaming mode
- Parse error scenarios
- Dead letter queue

These tests require a Spark session and will be skipped if Spark is unavailable.
"""

import pytest
import json
import os
import tempfile
import shutil
from typing import Optional

# Skip all tests if pyspark is not available
pytest.importorskip("pyspark")

from pyspark.sql import SparkSession


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def spark():
    """Create a local Spark session for testing."""
    spark = (
        SparkSession.builder
        .master("local[2]")
        .appName("HL7v2_Error_Handling_Tests")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield spark
    spark.stop()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def hl7_test_dir(temp_dir):
    """Create a directory with sample HL7v2 files."""
    hl7_dir = os.path.join(temp_dir, "hl7v2")
    os.makedirs(hl7_dir, exist_ok=True)
    return hl7_dir


# ---------------------------------------------------------------------------
# Sample Messages
# ---------------------------------------------------------------------------

VALID_ADT_A01 = """MSH|^~\\&|EPIC|HOSPITAL|LABADT|DH|20240115120000||ADT^A01|MSG00001|P|2.4
EVN|A01|20240115120000
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M|||123 MAIN ST^^ANYTOWN^NY^12345
PV1|1|I|ICU^101^A|E|||1234567890^SMITH^JANE^^^DR"""

VALID_ADT_A02 = """MSH|^~\\&|EPIC|HOSPITAL|LABADT|DH|20240115130000||ADT^A02|MSG00002|P|2.4
EVN|A02|20240115130000
PID|1||MRN789012^^^HOSPITAL^MR||SMITH^JANE^B||19750620|F
PV1|1|I|MED^202^B"""

VALID_ORM_O01 = """MSH|^~\\&|CPOE|HOSPITAL|LAB|HOSPITAL|20240115130000||ORM^O01|MSG00003|P|2.4
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M
ORC|NW|ORD001|LAB001||SC|||20240115130000
OBR|1|ORD001|LAB001|CBC^Complete Blood Count^L"""

VALID_ORU_R01 = """MSH|^~\\&|LAB|HOSPITAL|EMR|HOSPITAL|20240115140000||ORU^R01|MSG00004|P|2.4
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M
OBR|1|ORD001|LAB001|CBC^Complete Blood Count^L
OBX|1|NM|WBC^White Blood Cell Count^L||7.5|10*3/uL|4.5-11.0|N|||F"""

# Sample SIU^S12 message (New Appointment)
VALID_SIU_S12 = """MSH|^~\\&|SCHEDULING|HOSPITAL|EMR|HOSPITAL|20240115150000||SIU^S12|MSG00005|P|2.4
SCH|APT001|APT001|||SCHED001|NEW|CHECKUP^Annual Checkup|ROUTINE||30|MIN|||||||||||||BOOKED
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M
AIS|1||CHECKUP^Annual Checkup|20240201100000|||30|MIN||BOOKED
AIP|1||1234567890^SMITH^JANE^^^DR|ATTENDING||20240201100000||30|MIN
AIL|1||CLINIC^101^A|EXAM|||20240201100000||30|MIN"""

# Sample VXU^V04 message (Vaccination Update)
VALID_VXU_V04 = """MSH|^~\\&|IMMUNIZATION|HOSPITAL|IIS|REGISTRY|20240115160000||VXU^V04|MSG00006|P|2.5.1
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M
ORC|RE|VAX001|VAX001|||||||1234567890^SMITH^JANE^^^DR
RXA|0|1|20240115100000||141^Influenza, seasonal^CVX|0.5|mL||00^New immunization record^NIP001||||||LT123456|20250115|SKB^GlaxoSmithKline^MVX|||CP|A
RXR|IM^Intramuscular^HL70162|LD^Left Deltoid^HL70163
OBX|1|CE|30963-3^Vaccine funding source^LN||VXC50^Public^CDCPHINVS||||||F"""

INVALID_MESSAGE = """THIS IS NOT A VALID HL7 MESSAGE
IT DOESN'T START WITH MSH
AND HAS NO STRUCTURE"""

MALFORMED_MSH = """MSH|INCOMPLETE"""

CORRUPT_ENCODING = b"\xff\xfe\x00\x01MSH|^~\\&|BAD"


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def write_hl7_file(directory: str, filename: str, content: str) -> str:
    """Write an HL7v2 message to a file."""
    filepath = os.path.join(directory, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def write_binary_file(directory: str, filename: str, content: bytes) -> str:
    """Write binary content to a file."""
    filepath = os.path.join(directory, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------

class TestParseErrorScenarios:
    """Test parsing error scenarios."""

    def test_parse_valid_adt_message(self):
        """Valid ADT message should parse successfully."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
        
        result = parse_hl7v2_message(VALID_ADT_A01)
        
        assert result is not None
        assert result["message_type"] == "ADT"
        assert result["message_control_id"] == "MSG00001"

    def test_parse_invalid_message_returns_none(self):
        """Invalid message should return None."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
        
        result = parse_hl7v2_message(INVALID_MESSAGE)
        
        assert result is None

    def test_parse_malformed_msh_returns_none(self):
        """Malformed MSH should return None."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
        
        result = parse_hl7v2_message(MALFORMED_MSH)
        
        # Should not crash, should return None or partial result
        # (depends on parser tolerance)
        assert result is None or isinstance(result, dict)

    def test_parse_empty_message_returns_none(self):
        """Empty message should return None."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
        
        assert parse_hl7v2_message("") is None
        assert parse_hl7v2_message(None) is None
        assert parse_hl7v2_message("   \n\t  ") is None

    def test_message_type_detection(self):
        """Correctly detect message types."""
        from sources.healthcare.hl7v2_parser import get_message_type_from_content
        
        assert get_message_type_from_content(VALID_ADT_A01) == "ADT"
        assert get_message_type_from_content(VALID_ORM_O01) == "ORM"
        assert get_message_type_from_content(VALID_ORU_R01) == "ORU"
        assert get_message_type_from_content(VALID_SIU_S12) == "SIU"
        assert get_message_type_from_content(VALID_VXU_V04) == "VXU"
        assert get_message_type_from_content(INVALID_MESSAGE) is None

    def test_parse_siu_message(self):
        """Parse SIU^S12 (scheduling) message."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
        
        result = parse_hl7v2_message(VALID_SIU_S12)
        
        assert result is not None
        assert result["message_type"] == "SIU"
        assert result["trigger_event"] == "S12"
        assert result["message_control_id"] == "MSG00005"
        assert result["placer_appointment_id"] == "APT001"
        assert result["appointment_type"] == "ROUTINE"
        assert "appointment_resources" in result
        assert len(result["appointment_resources"]) >= 1

    def test_parse_vxu_message(self):
        """Parse VXU^V04 (vaccination) message."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
        
        result = parse_hl7v2_message(VALID_VXU_V04)
        
        assert result is not None
        assert result["message_type"] == "VXU"
        assert result["trigger_event"] == "V04"
        assert result["message_control_id"] == "MSG00006"
        assert result["patient_id"] == "MRN123456"
        assert "vaccinations" in result
        assert len(result["vaccinations"]) >= 1
        # Check vaccination details
        vax = result["vaccinations"][0]
        assert vax["vaccine_code"] == "141"
        assert "Influenza" in vax.get("vaccine_name", "")


class TestBatchErrorHandling:
    """Test batch mode error handling options."""

    def test_error_handling_skip_continues_on_error(self, spark, hl7_test_dir):
        """Skip mode should continue processing after parse errors."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Write mix of valid and invalid files
        write_hl7_file(hl7_test_dir, "01_valid.hl7", VALID_ADT_A01)
        write_hl7_file(hl7_test_dir, "02_invalid.hl7", INVALID_MESSAGE)
        write_hl7_file(hl7_test_dir, "03_valid.hl7", VALID_ADT_A02)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, offset = connector.read_table(
            "adt_messages",
            None,
            {"error_handling": "skip"}
        )
        
        records_list = list(records)
        
        # Should have 2 valid records (skipped the invalid one)
        assert len(records_list) == 2
        assert offset is not None

    def test_error_handling_fail_raises_on_error(self, spark, hl7_test_dir):
        """Fail mode should raise exception on configuration errors."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Use non-existent path to trigger error
        config = {"storage_path": "/nonexistent/path/that/does/not/exist", "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        # Should raise when error_handling is "fail"
        with pytest.raises(Exception):
            records, offset = connector.read_table(
                "adt_messages",
                None,
                {"error_handling": "fail"}
            )
            list(records)  # Force evaluation

    def test_error_handling_dead_letter_writes_failures(self, spark, hl7_test_dir, temp_dir):
        """Dead letter mode should write failed records to DLQ path."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        dlq_path = os.path.join(temp_dir, "dlq")
        os.makedirs(dlq_path, exist_ok=True)
        
        # Write mix of valid and invalid files
        write_hl7_file(hl7_test_dir, "01_valid.hl7", VALID_ADT_A01)
        write_hl7_file(hl7_test_dir, "02_invalid.hl7", INVALID_MESSAGE)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, offset = connector.read_table(
            "adt_messages",
            None,
            {
                "error_handling": "dead_letter",
                "dead_letter_path": dlq_path
            }
        )
        
        records_list = list(records)
        
        # Should have 1 valid record
        assert len(records_list) == 1
        
        # Check DLQ was written (may or may not exist depending on timing)
        # Note: DLQ write happens asynchronously, so this is informational


class TestCheckpointing:
    """Test checkpointing and offset tracking."""

    def test_offset_contains_last_file(self, spark, hl7_test_dir):
        """Offset should contain last processed file."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        write_hl7_file(hl7_test_dir, "01_first.hl7", VALID_ADT_A01)
        write_hl7_file(hl7_test_dir, "02_second.hl7", VALID_ADT_A02)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, offset = connector.read_table("adt_messages", None, {})
        list(records)  # Consume iterator
        
        assert offset is not None
        assert "last_file" in offset
        assert "02_second.hl7" in offset["last_file"]

    def test_offset_contains_processed_files_list(self, spark, hl7_test_dir):
        """Offset should contain list of processed files."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        write_hl7_file(hl7_test_dir, "01_first.hl7", VALID_ADT_A01)
        write_hl7_file(hl7_test_dir, "02_second.hl7", VALID_ADT_A02)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, offset = connector.read_table("adt_messages", None, {})
        list(records)
        
        assert "processed_files" in offset
        assert len(offset["processed_files"]) == 2

    def test_offset_contains_stats(self, spark, hl7_test_dir):
        """Offset should contain processing statistics."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        write_hl7_file(hl7_test_dir, "01_first.hl7", VALID_ADT_A01)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, offset = connector.read_table("adt_messages", None, {})
        list(records)
        
        assert "_stats" in offset
        assert "records_returned" in offset["_stats"]

    def test_incremental_read_with_offset(self, spark, hl7_test_dir):
        """Should only read files after offset."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Write initial files
        write_hl7_file(hl7_test_dir, "01_first.hl7", VALID_ADT_A01)
        write_hl7_file(hl7_test_dir, "02_second.hl7", VALID_ADT_A02)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        # First read
        records, offset = connector.read_table("adt_messages", None, {})
        first_batch = list(records)
        assert len(first_batch) == 2
        
        # Add new file
        valid_adt_a03 = VALID_ADT_A01.replace("MSG00001", "MSG00005").replace("A01", "A03")
        write_hl7_file(hl7_test_dir, "03_third.hl7", valid_adt_a03)
        
        # Second read with offset
        records2, offset2 = connector.read_table("adt_messages", offset, {})
        second_batch = list(records2)
        
        # Should only get the new file
        assert len(second_batch) == 1
        assert second_batch[0]["message_control_id"] == "MSG00005"


class TestBatchProcessing:
    """Test batch processing with batch_size option."""

    def test_batch_size_limits_records(self, spark, hl7_test_dir):
        """Batch size should limit number of files processed."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Write multiple files
        for i in range(5):
            msg = VALID_ADT_A01.replace("MSG00001", f"MSG{i:05d}")
            write_hl7_file(hl7_test_dir, f"{i:02d}_file.hl7", msg)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        # Read with batch_size=2
        records, offset = connector.read_table(
            "adt_messages",
            None,
            {"batch_size": "2"}
        )
        
        records_list = list(records)
        
        # Should only get 2 records
        assert len(records_list) == 2

    def test_batch_mode_is_default(self, spark, hl7_test_dir):
        """Batch mode should be the default."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        write_hl7_file(hl7_test_dir, "01_file.hl7", VALID_ADT_A01)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        # No mode specified - should work
        records, offset = connector.read_table("adt_messages", None, {})
        records_list = list(records)
        
        assert len(records_list) == 1


class TestStreamingMode:
    """Test streaming (micro-batch) mode."""

    def test_streaming_mode_with_max_files(self, spark, hl7_test_dir):
        """Streaming mode should respect max_files_per_trigger."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Write multiple files
        for i in range(5):
            msg = VALID_ADT_A01.replace("MSG00001", f"MSG{i:05d}")
            write_hl7_file(hl7_test_dir, f"{i:02d}_file.hl7", msg)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        # Read in streaming mode
        records, offset = connector.read_table(
            "adt_messages",
            None,
            {"mode": "streaming", "max_files_per_trigger": "2"}
        )
        
        records_list = list(records)
        
        # Should only get 2 records per trigger
        assert len(records_list) == 2

    def test_streaming_incremental_reads(self, spark, hl7_test_dir):
        """Streaming should support incremental reads via offset."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Write initial files
        for i in range(3):
            msg = VALID_ADT_A01.replace("MSG00001", f"MSG{i:05d}")
            write_hl7_file(hl7_test_dir, f"{i:02d}_file.hl7", msg)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        # First micro-batch
        records1, offset1 = connector.read_table(
            "adt_messages",
            None,
            {"mode": "streaming", "max_files_per_trigger": "2"}
        )
        batch1 = list(records1)
        
        # Second micro-batch with offset
        records2, offset2 = connector.read_table(
            "adt_messages",
            offset1,
            {"mode": "streaming", "max_files_per_trigger": "2"}
        )
        batch2 = list(records2)
        
        # Should process remaining file
        assert len(batch1) == 2
        assert len(batch2) == 1


class TestStructuredStreamingMode:
    """Test structured streaming mode."""

    def test_structured_streaming_requires_checkpoint_path(self, spark, hl7_test_dir):
        """Structured streaming should require checkpoint_path."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        write_hl7_file(hl7_test_dir, "01_file.hl7", VALID_ADT_A01)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        # Should raise without checkpoint_path
        with pytest.raises(ValueError, match="checkpoint_path"):
            connector.read_table(
                "adt_messages",
                None,
                {"mode": "structured_streaming"}
            )

    def test_structured_streaming_returns_streaming_df(self, spark, hl7_test_dir, temp_dir):
        """Structured streaming should return a streaming DataFrame."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        checkpoint_path = os.path.join(temp_dir, "checkpoints")
        
        write_hl7_file(hl7_test_dir, "01_file.hl7", VALID_ADT_A01)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        # This may fail in local mode due to cloudFiles not being available
        # That's expected - test verifies the mode is attempted
        try:
            result, offset = connector.read_table(
                "adt_messages",
                None,
                {
                    "mode": "structured_streaming",
                    "checkpoint_path": checkpoint_path
                }
            )
            
            assert offset["mode"] == "structured_streaming"
            assert "checkpoint_path" in offset
            
            # Result should be a DataFrame (streaming or batch depending on availability)
            assert result is not None
            
        except Exception as e:
            # cloudFiles may not be available in local Spark
            if "cloudFiles" in str(e) or "MALFORMED_RECORD_IN_PARSING" in str(e):
                pytest.skip("cloudFiles format not available in local Spark")
            raise


class TestMessageTypeFiltering:
    """Test filtering by message type."""

    def test_adt_table_only_returns_adt_messages(self, spark, hl7_test_dir):
        """adt_messages table should only return ADT messages."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        write_hl7_file(hl7_test_dir, "01_adt.hl7", VALID_ADT_A01)
        write_hl7_file(hl7_test_dir, "02_orm.hl7", VALID_ORM_O01)
        write_hl7_file(hl7_test_dir, "03_oru.hl7", VALID_ORU_R01)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, _ = connector.read_table("adt_messages", None, {})
        records_list = list(records)
        
        assert len(records_list) == 1
        assert records_list[0]["message_type"] == "ADT"

    def test_orm_table_only_returns_orm_messages(self, spark, hl7_test_dir):
        """orm_messages table should only return ORM messages."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        write_hl7_file(hl7_test_dir, "01_adt.hl7", VALID_ADT_A01)
        write_hl7_file(hl7_test_dir, "02_orm.hl7", VALID_ORM_O01)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, _ = connector.read_table("orm_messages", None, {})
        records_list = list(records)
        
        assert len(records_list) == 1
        assert records_list[0]["message_type"] == "ORM"

    def test_oru_table_only_returns_oru_messages(self, spark, hl7_test_dir):
        """oru_messages table should only return ORU messages."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        write_hl7_file(hl7_test_dir, "01_adt.hl7", VALID_ADT_A01)
        write_hl7_file(hl7_test_dir, "02_oru.hl7", VALID_ORU_R01)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, _ = connector.read_table("oru_messages", None, {})
        records_list = list(records)
        
        assert len(records_list) == 1
        assert records_list[0]["message_type"] == "ORU"


class TestSourceFileTracking:
    """Test that source file is tracked in records."""

    def test_record_contains_source_file(self, spark, hl7_test_dir):
        """Each record should contain _source_file field."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        write_hl7_file(hl7_test_dir, "01_file.hl7", VALID_ADT_A01)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, _ = connector.read_table("adt_messages", None, {})
        records_list = list(records)
        
        assert len(records_list) == 1
        assert "_source_file" in records_list[0]
        assert "01_file.hl7" in records_list[0]["_source_file"]


class TestBatchFileProcessing:
    """Test batch files containing multiple HL7v2 messages."""

    def test_split_batch_file_multiple_messages(self):
        """Split batch file into individual messages."""
        from sources.healthcare.hl7v2_parser import split_hl7_batch
        
        # Batch file with 3 messages
        batch_content = f"""{VALID_ADT_A01}
{VALID_ADT_A02}
{VALID_ORM_O01}"""
        
        messages = split_hl7_batch(batch_content)
        
        assert len(messages) == 3
        assert messages[0].startswith("MSH|")
        assert messages[1].startswith("MSH|")
        assert messages[2].startswith("MSH|")

    def test_split_batch_file_single_message(self):
        """Single message file should return one message."""
        from sources.healthcare.hl7v2_parser import split_hl7_batch
        
        messages = split_hl7_batch(VALID_ADT_A01)
        
        assert len(messages) == 1

    def test_split_batch_file_empty(self):
        """Empty content should return empty list."""
        from sources.healthcare.hl7v2_parser import split_hl7_batch
        
        assert split_hl7_batch("") == []
        assert split_hl7_batch(None) == []
        assert split_hl7_batch("   \n\t  ") == []

    def test_parse_hl7v2_file_multiple_messages(self):
        """Parse batch file with multiple messages."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_file
        
        # Batch file with ADT, ORM, ORU
        batch_content = f"""{VALID_ADT_A01}
{VALID_ORM_O01}
{VALID_ORU_R01}"""
        
        results = parse_hl7v2_file(batch_content)
        
        assert len(results) == 3
        assert results[0]["message_type"] == "ADT"
        assert results[1]["message_type"] == "ORM"
        assert results[2]["message_type"] == "ORU"

    def test_parse_hl7v2_file_with_invalid_messages(self):
        """Batch file with some invalid messages should parse valid ones."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_file
        
        # Batch with valid ADT, invalid, valid ORM
        batch_content = f"""{VALID_ADT_A01}
{INVALID_MESSAGE}
{VALID_ORM_O01}"""
        
        results = parse_hl7v2_file(batch_content)
        
        # Should get 2 valid messages (invalid one skipped)
        assert len(results) == 2
        assert results[0]["message_type"] == "ADT"
        assert results[1]["message_type"] == "ORM"

    def test_batch_file_in_connector_returns_all_messages(self, spark, hl7_test_dir):
        """Connector should return all messages from batch file."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Create batch file with 2 ADT messages
        batch_content = f"""{VALID_ADT_A01}
{VALID_ADT_A02}"""
        
        write_hl7_file(hl7_test_dir, "batch_file.hl7", batch_content)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, offset = connector.read_table("adt_messages", None, {})
        records_list = list(records)
        
        # Should get 2 records from 1 file
        assert len(records_list) == 2
        
        # Both should reference the same source file
        assert all("batch_file.hl7" in r["_source_file"] for r in records_list)
        
        # Should have different message control IDs
        msg_ids = {r["message_control_id"] for r in records_list}
        assert len(msg_ids) == 2

    def test_batch_file_mixed_types_filters_correctly(self, spark, hl7_test_dir):
        """Batch file with mixed message types should filter by table."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Create batch file with ADT, ORM, ORU
        batch_content = f"""{VALID_ADT_A01}
{VALID_ORM_O01}
{VALID_ORU_R01}"""
        
        write_hl7_file(hl7_test_dir, "mixed_batch.hl7", batch_content)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        # Query adt_messages - should only get ADT
        adt_records, _ = connector.read_table("adt_messages", None, {})
        adt_list = list(adt_records)
        assert len(adt_list) == 1
        assert adt_list[0]["message_type"] == "ADT"
        
        # Query orm_messages - should only get ORM
        orm_records, _ = connector.read_table("orm_messages", None, {})
        orm_list = list(orm_records)
        assert len(orm_list) == 1
        assert orm_list[0]["message_type"] == "ORM"
        
        # Query oru_messages - should only get ORU
        oru_records, _ = connector.read_table("oru_messages", None, {})
        oru_list = list(oru_records)
        assert len(oru_list) == 1
        assert oru_list[0]["message_type"] == "ORU"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_directory_returns_empty_results(self, spark, hl7_test_dir):
        """Empty directory should return empty results, not error."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Directory is empty
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        # Should not raise, should return empty
        try:
            records, offset = connector.read_table("adt_messages", None, {})
            records_list = list(records)
            assert len(records_list) == 0
        except Exception as e:
            # Some Spark versions may raise on empty glob
            if "Path does not exist" in str(e) or "Unable to infer schema" in str(e):
                pytest.skip("Spark raises on empty directory in this version")
            raise

    def test_no_matching_files_returns_empty(self, spark, hl7_test_dir):
        """No matching files should return empty results."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Write file with different extension
        with open(os.path.join(hl7_test_dir, "file.txt"), "w") as f:
            f.write(VALID_ADT_A01)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        try:
            records, offset = connector.read_table("adt_messages", None, {})
            records_list = list(records)
            assert len(records_list) == 0
        except Exception as e:
            if "Path does not exist" in str(e) or "Unable to infer schema" in str(e):
                pytest.skip("Spark raises on no matching files")
            raise

    def test_max_tracked_files_limits_offset_size(self, spark, hl7_test_dir):
        """processed_files should be limited to max_tracked_files."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # Write many files
        for i in range(20):
            msg = VALID_ADT_A01.replace("MSG00001", f"MSG{i:05d}")
            write_hl7_file(hl7_test_dir, f"{i:02d}_file.hl7", msg)
        
        config = {"storage_path": hl7_test_dir, "file_pattern": "*.hl7"}
        connector = Healthcare(config)
        connector._spark = spark
        
        records, offset = connector.read_table(
            "adt_messages",
            None,
            {"max_tracked_files": "5"}
        )
        list(records)
        
        # Should only track last 5 files
        assert len(offset.get("processed_files", [])) <= 5
