#!/usr/bin/env python3
"""
Local tests for HL7v2 parsing functions.

Run with: python -m pytest tests/test_hl7v2_parser.py -v
Or simply: python tests/test_hl7v2_parser.py
"""

import json
from typing import List, Optional, Dict

# ---------------------------------------------------------------------------
# Copy of parsing functions from bronze_hl7v2.py (for local testing)
# These are pure Python and don't require Spark
# ---------------------------------------------------------------------------

def split_hl7_batch(text: str) -> List[str]:
    """Split batch file into individual HL7v2 messages."""
    if not text:
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    messages, current = [], []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("MSH"):
            if current:
                messages.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        messages.append("\n".join(current))
    return messages


def parse_hl7v2_message(msg: str) -> Optional[Dict]:
    """Parse a single HL7v2 message into a dictionary."""
    if not msg or not msg.strip():
        return None
    msg = msg.replace("\r\n", "\n").replace("\r", "\n")
    lines = [l for l in msg.strip().split("\n") if l]
    if not lines or not lines[0].startswith("MSH"):
        return None
    
    result = {}
    
    # Parse MSH segment (header)
    msh = lines[0].split("|")
    result["sending_application"] = msh[2] if len(msh) > 2 else ""
    result["sending_facility"] = msh[3] if len(msh) > 3 else ""
    result["message_datetime"] = msh[6] if len(msh) > 6 else ""
    msg_type_field = msh[8] if len(msh) > 8 else ""
    result["message_type"] = msg_type_field.split("^")[0] if msg_type_field else ""
    result["trigger_event"] = msg_type_field.split("^")[1] if "^" in msg_type_field else ""
    result["message_control_id"] = msh[9] if len(msh) > 9 else ""
    
    # Parse PID segment (patient identification)
    for line in lines:
        if line.startswith("PID"):
            pf = line.split("|")
            pid_field = pf[3] if len(pf) > 3 else ""
            result["patient_id"] = pid_field.split("^")[0] if pid_field else ""
            name_field = pf[5] if len(pf) > 5 else ""
            np = name_field.split("^")
            result["patient_name_family"] = np[0] if np else ""
            result["patient_name_given"] = np[1] if len(np) > 1 else ""
            result["date_of_birth"] = pf[7] if len(pf) > 7 else ""
            result["gender"] = pf[8] if len(pf) > 8 else ""
            break
    
    mt = result.get("message_type", "")
    
    # Parse message-type specific segments
    if mt == "ADT":
        for line in lines:
            if line.startswith("EVN"):
                ef = line.split("|")
                result["event_type_code"] = ef[1] if len(ef) > 1 else ""
                result["event_datetime"] = ef[2] if len(ef) > 2 else ""
            elif line.startswith("PV1"):
                pf = line.split("|")
                result["patient_class"] = pf[2] if len(pf) > 2 else ""
                result["assigned_location"] = pf[3] if len(pf) > 3 else ""
                result["admission_type"] = pf[4] if len(pf) > 4 else ""
    
    elif mt == "ORM":
        for line in lines:
            if line.startswith("ORC"):
                of = line.split("|")
                result["order_control"] = of[1] if len(of) > 1 else ""
                result["order_id"] = of[2] if len(of) > 2 else ""
                result["filler_order_number"] = of[3] if len(of) > 3 else ""
                result["order_status"] = of[5] if len(of) > 5 else ""
            elif line.startswith("OBR"):
                bf = line.split("|")
                result["placer_order_number"] = bf[2] if len(bf) > 2 else ""
                result["universal_service_id"] = bf[4] if len(bf) > 4 else ""
    
    elif mt == "ORU":
        obs = []
        for line in lines:
            if line.startswith("OBR"):
                bf = line.split("|")
                result["placer_order_number"] = bf[2] if len(bf) > 2 else ""
                result["filler_order_number"] = bf[3] if len(bf) > 3 else ""
                result["universal_service_id"] = bf[4] if len(bf) > 4 else ""
            elif line.startswith("OBX"):
                xf = line.split("|")
                obs.append({
                    "set_id": xf[1] if len(xf) > 1 else "",
                    "value_type": xf[2] if len(xf) > 2 else "",
                    "observation_id": xf[3] if len(xf) > 3 else "",
                    "observation_value": xf[5] if len(xf) > 5 else "",
                    "units": xf[6] if len(xf) > 6 else "",
                    "reference_range": xf[7] if len(xf) > 7 else "",
                    "abnormal_flags": xf[8] if len(xf) > 8 else "",
                    "result_status": xf[11] if len(xf) > 11 else "",
                })
        result["observations"] = obs
    
    # Add other message types as needed...
    
    return result


# ---------------------------------------------------------------------------
# Sample HL7v2 Messages for Testing
# ---------------------------------------------------------------------------

SAMPLE_ADT_A01 = """MSH|^~\\&|HIS|HOSPITAL|LAB|LAB|202401151030||ADT^A01|MSG00001|P|2.5
EVN|A01|202401151030
PID|1||12345^^^MRN||DOE^JOHN^M||19800115|M|||123 MAIN ST^^ANYTOWN^CA^12345
PV1|1|I|ICU^101^A|||||||MED||||||||I123456"""

SAMPLE_ADT_A08 = """MSH|^~\\&|HIS|HOSPITAL|LAB|LAB|202401151130||ADT^A08|MSG00002|P|2.5
EVN|A08|202401151130
PID|1||12345^^^MRN||DOE^JOHN^M||19800115|M|||456 OAK AVE^^ANYTOWN^CA^12345
PV1|1|I|ICU^101^A|||||||MED||||||||I123456"""

SAMPLE_ORU_R01 = """MSH|^~\\&|LAB|HOSPITAL|HIS|HOSPITAL|202401151200||ORU^R01|MSG00003|P|2.5
PID|1||12345^^^MRN||DOE^JOHN^M||19800115|M
OBR|1|ORD001|FIL001|CBC^Complete Blood Count|||202401151100
OBX|1|NM|WBC^White Blood Cell Count||7.5|10*3/uL|4.5-11.0|N|||F
OBX|2|NM|RBC^Red Blood Cell Count||4.8|10*6/uL|4.5-5.5|N|||F
OBX|3|NM|HGB^Hemoglobin||14.2|g/dL|13.5-17.5|N|||F"""

SAMPLE_ORM_O01 = """MSH|^~\\&|HIS|HOSPITAL|LAB|LAB|202401151300||ORM^O01|MSG00004|P|2.5
PID|1||12345^^^MRN||DOE^JOHN^M||19800115|M
ORC|NW|ORD002||||||||||DR^SMITH^JOHN
OBR|1|ORD002||CHEM^Chemistry Panel|||202401151300"""

SAMPLE_BATCH_MIXED = """MSH|^~\\&|HIS|HOSPITAL|LAB|LAB|202401151030||ADT^A01|MSG00001|P|2.5
EVN|A01|202401151030
PID|1||12345^^^MRN||DOE^JOHN^M||19800115|M
PV1|1|I|ICU^101^A
MSH|^~\\&|LAB|HOSPITAL|HIS|HOSPITAL|202401151200||ORU^R01|MSG00003|P|2.5
PID|1||12345^^^MRN||DOE^JOHN^M||19800115|M
OBR|1|ORD001|FIL001|CBC^Complete Blood Count
OBX|1|NM|WBC^White Blood Cell Count||7.5|10*3/uL|4.5-11.0|N|||F
MSH|^~\\&|HIS|HOSPITAL|LAB|LAB|202401151300||ORM^O01|MSG00004|P|2.5
PID|1||67890^^^MRN||SMITH^JANE^A||19901220|F
ORC|NW|ORD002
OBR|1|ORD002||CHEM^Chemistry Panel"""


# ---------------------------------------------------------------------------
# Test Functions
# ---------------------------------------------------------------------------

def test_split_hl7_batch_single():
    """Test splitting a single message."""
    messages = split_hl7_batch(SAMPLE_ADT_A01)
    assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
    assert messages[0].startswith("MSH|")
    print("✓ test_split_hl7_batch_single passed")


def test_split_hl7_batch_multiple():
    """Test splitting a batch with multiple message types."""
    messages = split_hl7_batch(SAMPLE_BATCH_MIXED)
    assert len(messages) == 3, f"Expected 3 messages, got {len(messages)}"
    
    # Each message should start with MSH
    for i, msg in enumerate(messages):
        assert msg.startswith("MSH|"), f"Message {i} doesn't start with MSH"
    
    print("✓ test_split_hl7_batch_multiple passed")


def test_split_hl7_batch_empty():
    """Test splitting empty or None input."""
    assert split_hl7_batch("") == []
    assert split_hl7_batch(None) == []
    print("✓ test_split_hl7_batch_empty passed")


def test_parse_adt_message():
    """Test parsing an ADT message."""
    parsed = parse_hl7v2_message(SAMPLE_ADT_A01)
    
    assert parsed is not None
    assert parsed["message_type"] == "ADT"
    assert parsed["trigger_event"] == "A01"
    assert parsed["message_control_id"] == "MSG00001"
    assert parsed["patient_id"] == "12345"
    assert parsed["patient_name_family"] == "DOE"
    assert parsed["patient_name_given"] == "JOHN"
    assert parsed["gender"] == "M"
    assert parsed["event_type_code"] == "A01"
    assert parsed["patient_class"] == "I"
    
    print("✓ test_parse_adt_message passed")
    print(f"  Parsed ADT: {json.dumps(parsed, indent=2)}")


def test_parse_oru_message():
    """Test parsing an ORU message with observations."""
    parsed = parse_hl7v2_message(SAMPLE_ORU_R01)
    
    assert parsed is not None
    assert parsed["message_type"] == "ORU"
    assert parsed["trigger_event"] == "R01"
    assert "observations" in parsed
    assert len(parsed["observations"]) == 3
    
    # Check first observation
    obs1 = parsed["observations"][0]
    assert obs1["observation_id"] == "WBC^White Blood Cell Count"
    assert obs1["observation_value"] == "7.5"
    assert obs1["units"] == "10*3/uL"
    
    print("✓ test_parse_oru_message passed")
    print(f"  Found {len(parsed['observations'])} observations")


def test_parse_orm_message():
    """Test parsing an ORM message."""
    parsed = parse_hl7v2_message(SAMPLE_ORM_O01)
    
    assert parsed is not None
    assert parsed["message_type"] == "ORM"
    assert parsed["trigger_event"] == "O01"
    assert parsed["order_control"] == "NW"
    assert parsed["order_id"] == "ORD002"
    
    print("✓ test_parse_orm_message passed")


def test_parse_batch_mixed_types():
    """Test parsing a batch file with mixed message types."""
    messages = split_hl7_batch(SAMPLE_BATCH_MIXED)
    
    parsed_messages = [parse_hl7v2_message(msg) for msg in messages]
    message_types = [p["message_type"] for p in parsed_messages if p]
    
    assert "ADT" in message_types
    assert "ORU" in message_types
    assert "ORM" in message_types
    
    # Group by type
    by_type = {}
    for p in parsed_messages:
        if p:
            mt = p["message_type"]
            by_type[mt] = by_type.get(mt, 0) + 1
    
    print("✓ test_parse_batch_mixed_types passed")
    print(f"  Message types found: {by_type}")


def test_parse_invalid_message():
    """Test parsing invalid input."""
    assert parse_hl7v2_message("") is None
    assert parse_hl7v2_message(None) is None
    assert parse_hl7v2_message("Not an HL7 message") is None
    assert parse_hl7v2_message("PID|1||12345") is None  # No MSH segment
    
    print("✓ test_parse_invalid_message passed")


def test_carriage_return_handling():
    """Test that different line endings are handled correctly."""
    # Windows style (CRLF)
    msg_crlf = SAMPLE_ADT_A01.replace("\n", "\r\n")
    parsed = parse_hl7v2_message(msg_crlf)
    assert parsed is not None
    assert parsed["message_type"] == "ADT"
    
    # Old Mac style (CR only)
    msg_cr = SAMPLE_ADT_A01.replace("\n", "\r")
    parsed = parse_hl7v2_message(msg_cr)
    assert parsed is not None
    assert parsed["message_type"] == "ADT"
    
    print("✓ test_carriage_return_handling passed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("HL7v2 Parser Local Tests")
    print("=" * 60 + "\n")
    
    tests = [
        test_split_hl7_batch_single,
        test_split_hl7_batch_multiple,
        test_split_hl7_batch_empty,
        test_parse_adt_message,
        test_parse_oru_message,
        test_parse_orm_message,
        test_parse_batch_mixed_types,
        test_parse_invalid_message,
        test_carriage_return_handling,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
