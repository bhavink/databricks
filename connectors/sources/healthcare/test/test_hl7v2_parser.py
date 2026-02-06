"""
Tests for HL7v2 message parsing.

Test-first approach: Write tests before implementation.
"""

import pytest


# Sample HL7v2 ADT^A01 message (Admit/Visit Notification)
SAMPLE_ADT_A01 = """MSH|^~\\&|EPIC|HOSPITAL|LABADT|DH|20240115120000||ADT^A01|MSG00001|P|2.4
EVN|A01|20240115120000
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M|||123 MAIN ST^^ANYTOWN^NY^12345||(555)123-4567
PV1|1|I|ICU^101^A|E|||1234567890^SMITH^JANE^^^DR|||MED||||1|||1234567890^SMITH^JANE^^^DR|IN||||||||||||||||||HOSP|||20240115120000"""

# Sample HL7v2 ORM^O01 message (Order)
SAMPLE_ORM_O01 = """MSH|^~\\&|CPOE|HOSPITAL|LAB|HOSPITAL|20240115130000||ORM^O01|MSG00002|P|2.4
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M
ORC|NW|ORD001|LAB001||SC|||20240115130000|||1234567890^SMITH^JANE^^^DR
OBR|1|ORD001|LAB001|CBC^Complete Blood Count^L|||20240115130000||||||||1234567890^SMITH^JANE^^^DR"""

# Sample HL7v2 ORU^R01 message (Lab Result)
SAMPLE_ORU_R01 = """MSH|^~\\&|LAB|HOSPITAL|EMR|HOSPITAL|20240115140000||ORU^R01|MSG00003|P|2.4
PID|1||MRN123456^^^HOSPITAL^MR||DOE^JOHN^A||19800315|M
OBR|1|ORD001|LAB001|CBC^Complete Blood Count^L|||20240115130000
OBX|1|NM|WBC^White Blood Cell Count^L||7.5|10*3/uL|4.5-11.0|N|||F
OBX|2|NM|RBC^Red Blood Cell Count^L||4.8|10*6/uL|4.5-5.5|N|||F
OBX|3|NM|HGB^Hemoglobin^L||14.2|g/dL|13.5-17.5|N|||F"""


class TestHL7v2Parser:
    """Tests for HL7v2 message parsing."""

    def test_parse_adt_message(self):
        """Parse ADT^A01 message and extract key fields."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
        
        result = parse_hl7v2_message(SAMPLE_ADT_A01)
        
        assert result is not None
        assert result["message_type"] == "ADT"
        assert result["trigger_event"] == "A01"
        assert result["message_control_id"] == "MSG00001"
        assert result["patient_id"] == "MRN123456"
        assert result["patient_name_family"] == "DOE"
        assert result["patient_name_given"] == "JOHN"

    def test_parse_orm_message(self):
        """Parse ORM^O01 message and extract order details."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
        
        result = parse_hl7v2_message(SAMPLE_ORM_O01)
        
        assert result is not None
        assert result["message_type"] == "ORM"
        assert result["trigger_event"] == "O01"
        assert result["order_control"] == "NW"  # New Order
        assert result["order_id"] == "ORD001"

    def test_parse_oru_message(self):
        """Parse ORU^R01 message and extract results."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
        
        result = parse_hl7v2_message(SAMPLE_ORU_R01)
        
        assert result is not None
        assert result["message_type"] == "ORU"
        assert result["trigger_event"] == "R01"
        # Should have observations
        assert "observations" in result
        assert len(result["observations"]) == 3

    def test_parse_invalid_message_returns_none(self):
        """Invalid HL7v2 message should return None or raise."""
        from sources.healthcare.hl7v2_parser import parse_hl7v2_message
        
        result = parse_hl7v2_message("NOT A VALID HL7 MESSAGE")
        assert result is None

    def test_extract_msh_segment(self):
        """Extract MSH segment fields correctly."""
        from sources.healthcare.hl7v2_parser import parse_msh_segment
        
        msh = parse_msh_segment(SAMPLE_ADT_A01)
        
        assert msh["sending_application"] == "EPIC"
        assert msh["sending_facility"] == "HOSPITAL"
        assert msh["message_datetime"] == "20240115120000"
        assert msh["message_type"] == "ADT^A01"

    def test_extract_pid_segment(self):
        """Extract PID (Patient ID) segment correctly."""
        from sources.healthcare.hl7v2_parser import parse_pid_segment
        
        pid = parse_pid_segment(SAMPLE_ADT_A01)
        
        assert pid["patient_id"] == "MRN123456"
        assert pid["patient_name_family"] == "DOE"
        assert pid["patient_name_given"] == "JOHN"
        assert pid["date_of_birth"] == "19800315"
        assert pid["gender"] == "M"


class TestHL7v2FileReader:
    """Tests for reading HL7v2 files from storage."""

    def test_list_hl7_tables(self):
        """Connector should list HL7v2 tables when in file mode."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        # File mode config
        config = {
            "storage_path": "/tmp/test/hl7v2/",
            "file_pattern": "*.hl7"
        }
        connector = Healthcare(config)
        tables = connector.list_tables()
        
        # Should include HL7v2 tables
        assert "adt_messages" in tables
        assert "orm_messages" in tables
        assert "oru_messages" in tables

    def test_mode_detection_api(self):
        """Detect API mode when fhir_base_url is provided."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        config = {"fhir_base_url": "https://hapi.fhir.org/baseR4"}
        connector = Healthcare(config)
        
        assert connector.mode == "api"

    def test_mode_detection_file(self):
        """Detect file mode when storage_path is provided."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        config = {"storage_path": "s3://bucket/hl7v2/"}
        connector = Healthcare(config)
        
        assert connector.mode == "file"

    def test_hl7_table_schema(self):
        """HL7v2 tables should have proper schema."""
        from sources.healthcare.lakeflow_connect import Healthcare
        from pyspark.sql.types import StructType
        
        config = {"storage_path": "/tmp/test/hl7v2/"}
        connector = Healthcare(config)
        
        schema = connector.get_table_schema("adt_messages", {})
        
        assert isinstance(schema, StructType)
        field_names = [f.name for f in schema.fields]
        assert "message_control_id" in field_names
        assert "message_type" in field_names
        assert "patient_id" in field_names

    def test_hl7_table_metadata(self):
        """HL7v2 tables should return correct metadata."""
        from sources.healthcare.lakeflow_connect import Healthcare
        
        config = {"storage_path": "/tmp/test/hl7v2/"}
        connector = Healthcare(config)
        
        metadata = connector.read_table_metadata("adt_messages", {})
        
        assert metadata["primary_keys"] == ["message_control_id"]
        assert metadata["ingestion_type"] == "append"
        assert "cursor_field" in metadata
