"""
Local tests for HL7v2 parsing functions.

Run with: python -m pytest tests/test_hl7v2_parser.py -v
Or standalone: python tests/test_hl7v2_parser.py
"""

import json
from typing import List, Optional, Dict


# =============================================================================
# Composite Field Parsers (copied from bronze_hl7v2.py for local testing)
# =============================================================================

def parse_pl(value: str) -> dict:
    """
    Parse PL (Person Location) data type.
    Format: PointOfCare^Room^Bed^Facility^LocationStatus^PersonLocationType^Building^Floor^LocationDescription
    """
    if not value:
        return {"unit": "", "room": "", "bed": "", "facility": "", "building": "", "floor": ""}
    parts = value.split("^")
    return {
        "unit": parts[0] if len(parts) > 0 else "",
        "room": parts[1] if len(parts) > 1 else "",
        "bed": parts[2] if len(parts) > 2 else "",
        "facility": parts[3] if len(parts) > 3 else "",
        "building": parts[6] if len(parts) > 6 else "",
        "floor": parts[7] if len(parts) > 7 else "",
    }


def parse_xcn(value: str) -> dict:
    """
    Parse XCN (Extended Composite ID Number and Name for Persons) data type.
    Format: ID^FamilyName^GivenName^MiddleName^Suffix^Prefix^Degree
    """
    if not value:
        return {"id": "", "family_name": "", "given_name": "", "degree": ""}
    parts = value.split("^")
    return {
        "id": parts[0] if len(parts) > 0 else "",
        "family_name": parts[1] if len(parts) > 1 else "",
        "given_name": parts[2] if len(parts) > 2 else "",
        "degree": parts[6] if len(parts) > 6 else "",
    }


def parse_cx(value: str) -> dict:
    """
    Parse CX (Extended Composite ID with Check Digit) data type.
    Format: ID^CheckDigit^CheckDigitScheme^AssigningAuthority^IDType
    """
    if not value:
        return {"id": "", "assigning_authority": "", "id_type": ""}
    parts = value.split("^")
    return {
        "id": parts[0] if len(parts) > 0 else "",
        "assigning_authority": parts[3] if len(parts) > 3 else "",
        "id_type": parts[4] if len(parts) > 4 else "",
    }


def parse_ce(value: str) -> dict:
    """
    Parse CE/CWE (Coded Element) data type.
    Format: Code^Text^CodingSystem
    """
    if not value:
        return {"code": "", "text": "", "coding_system": ""}
    parts = value.split("^")
    return {
        "code": parts[0] if len(parts) > 0 else "",
        "text": parts[1] if len(parts) > 1 else "",
        "coding_system": parts[2] if len(parts) > 2 else "",
    }


def parse_xpn(value: str) -> dict:
    """
    Parse XPN (Extended Person Name) data type.
    Format: FamilyName^GivenName^MiddleName^Suffix^Prefix
    """
    if not value:
        return {"family": "", "given": "", "middle": "", "suffix": "", "prefix": ""}
    parts = value.split("^")
    return {
        "family": parts[0] if len(parts) > 0 else "",
        "given": parts[1] if len(parts) > 1 else "",
        "middle": parts[2] if len(parts) > 2 else "",
        "suffix": parts[3] if len(parts) > 3 else "",
        "prefix": parts[4] if len(parts) > 4 else "",
    }


def parse_xad(value: str) -> dict:
    """
    Parse XAD (Extended Address) data type.
    Format: StreetAddress^OtherDesignation^City^State^Zip^Country
    """
    if not value:
        return {"street": "", "city": "", "state": "", "zip": "", "country": ""}
    parts = value.split("^")
    return {
        "street": parts[0] if len(parts) > 0 else "",
        "city": parts[2] if len(parts) > 2 else "",
        "state": parts[3] if len(parts) > 3 else "",
        "zip": parts[4] if len(parts) > 4 else "",
        "country": parts[5] if len(parts) > 5 else "",
    }


# =============================================================================
# Core Parsing Functions (copied from bronze_hl7v2.py for local testing)
# =============================================================================

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
    
    result = {
        "_parse_error": None,
        "_raw_message": msg[:500] if len(msg) > 500 else msg,
    }
    
    try:
        # Parse MSH segment
        msh = lines[0].split("|")
        result["sending_application"] = msh[2] if len(msh) > 2 else ""
        result["sending_facility"] = msh[3] if len(msh) > 3 else ""
        result["receiving_application"] = msh[4] if len(msh) > 4 else ""
        result["receiving_facility"] = msh[5] if len(msh) > 5 else ""
        result["message_datetime"] = msh[6] if len(msh) > 6 else ""
        msg_type_field = msh[8] if len(msh) > 8 else ""
        result["message_type"] = msg_type_field.split("^")[0] if msg_type_field else ""
        result["trigger_event"] = msg_type_field.split("^")[1] if "^" in msg_type_field else ""
        result["message_control_id"] = msh[9] if len(msh) > 9 else ""
        result["processing_id"] = msh[10] if len(msh) > 10 else ""
        result["version_id"] = msh[11] if len(msh) > 11 else ""
        
        # Parse PID segment with composite field parsing
        for line in lines:
            if line.startswith("PID"):
                pf = line.split("|")
                
                # PID-3: Patient ID (CX type)
                pid_field = pf[3] if len(pf) > 3 else ""
                pid_parsed = parse_cx(pid_field)
                result["patient_id"] = pid_parsed["id"]
                result["patient_id_assigning_authority"] = pid_parsed["assigning_authority"]
                result["patient_id_type"] = pid_parsed["id_type"]
                
                # PID-5: Patient Name (XPN type)
                name_field = pf[5] if len(pf) > 5 else ""
                name_parsed = parse_xpn(name_field)
                result["patient_name_family"] = name_parsed["family"]
                result["patient_name_given"] = name_parsed["given"]
                result["patient_name_middle"] = name_parsed["middle"]
                result["patient_name_suffix"] = name_parsed["suffix"]
                result["patient_name_prefix"] = name_parsed["prefix"]
                
                result["date_of_birth"] = pf[7] if len(pf) > 7 else ""
                result["gender"] = pf[8] if len(pf) > 8 else ""
                
                # PID-11: Patient Address (XAD type)
                addr_field = pf[11] if len(pf) > 11 else ""
                addr_parsed = parse_xad(addr_field)
                result["patient_address_street"] = addr_parsed["street"]
                result["patient_address_city"] = addr_parsed["city"]
                result["patient_address_state"] = addr_parsed["state"]
                result["patient_address_zip"] = addr_parsed["zip"]
                result["patient_address_country"] = addr_parsed["country"]
                
                break
        
        mt = result.get("message_type", "")
        
        if mt == "ADT":
            _parse_adt_segments(lines, result)
        elif mt == "ORM":
            _parse_orm_segments(lines, result)
        elif mt == "ORU":
            _parse_oru_segments(lines, result)
        elif mt == "SIU":
            _parse_siu_segments(lines, result)
        elif mt == "VXU":
            _parse_vxu_segments(lines, result)
        
        return result
        
    except Exception as e:
        result["_parse_error"] = str(e)
        return result


def _parse_adt_segments(lines, result):
    """Parse ADT-specific segments."""
    for line in lines:
        if line.startswith("EVN"):
            ef = line.split("|")
            result["event_type_code"] = ef[1] if len(ef) > 1 else ""
            result["event_datetime"] = ef[2] if len(ef) > 2 else ""
            result["event_reason_code"] = ef[4] if len(ef) > 4 else ""
            
        elif line.startswith("PV1"):
            pf = line.split("|")
            result["patient_class"] = pf[2] if len(pf) > 2 else ""
            
            # PV1-3: Assigned Patient Location (PL type)
            loc_field = pf[3] if len(pf) > 3 else ""
            loc_parsed = parse_pl(loc_field)
            result["assigned_location"] = loc_field
            result["location_unit"] = loc_parsed["unit"]
            result["location_room"] = loc_parsed["room"]
            result["location_bed"] = loc_parsed["bed"]
            result["location_facility"] = loc_parsed["facility"]
            result["location_building"] = loc_parsed["building"]
            result["location_floor"] = loc_parsed["floor"]
            
            result["admission_type"] = pf[4] if len(pf) > 4 else ""
            
            # PV1-6: Prior Patient Location (PL type)
            prior_loc = pf[6] if len(pf) > 6 else ""
            prior_parsed = parse_pl(prior_loc)
            result["prior_location_unit"] = prior_parsed["unit"]
            result["prior_location_room"] = prior_parsed["room"]
            result["prior_location_bed"] = prior_parsed["bed"]
            
            # PV1-7: Attending Doctor (XCN type)
            attending = pf[7] if len(pf) > 7 else ""
            attending_parsed = parse_xcn(attending)
            result["attending_doctor_id"] = attending_parsed["id"]
            result["attending_doctor_family"] = attending_parsed["family_name"]
            result["attending_doctor_given"] = attending_parsed["given_name"]
            
            # PV1-8: Referring Doctor (XCN type)
            referring = pf[8] if len(pf) > 8 else ""
            referring_parsed = parse_xcn(referring)
            result["referring_doctor_id"] = referring_parsed["id"]
            result["referring_doctor_family"] = referring_parsed["family_name"]
            result["referring_doctor_given"] = referring_parsed["given_name"]
            
            result["hospital_service"] = pf[10] if len(pf) > 10 else ""
            result["visit_number"] = pf[19] if len(pf) > 19 else ""


def _parse_orm_segments(lines, result):
    """Parse ORM-specific segments."""
    for line in lines:
        if line.startswith("ORC"):
            of = line.split("|")
            result["order_control"] = of[1] if len(of) > 1 else ""
            result["order_id"] = of[2] if len(of) > 2 else ""
            result["filler_order_number"] = of[3] if len(of) > 3 else ""
            result["order_status"] = of[5] if len(of) > 5 else ""
            result["order_datetime"] = of[9] if len(of) > 9 else ""
            
            # ORC-12: Ordering Provider (XCN type)
            provider = of[12] if len(of) > 12 else ""
            provider_parsed = parse_xcn(provider)
            result["ordering_provider_id"] = provider_parsed["id"]
            result["ordering_provider_family"] = provider_parsed["family_name"]
            result["ordering_provider_given"] = provider_parsed["given_name"]
            
        elif line.startswith("OBR"):
            bf = line.split("|")
            result["placer_order_number"] = bf[2] if len(bf) > 2 else ""
            
            # OBR-4: Universal Service Identifier (CE type)
            service = bf[4] if len(bf) > 4 else ""
            service_parsed = parse_ce(service)
            result["universal_service_id"] = service
            result["service_code"] = service_parsed["code"]
            result["service_text"] = service_parsed["text"]
            result["service_coding_system"] = service_parsed["coding_system"]


def _parse_oru_segments(lines, result):
    """Parse ORU-specific segments."""
    observations = []
    for line in lines:
        if line.startswith("OBR"):
            bf = line.split("|")
            result["placer_order_number"] = bf[2] if len(bf) > 2 else ""
            result["filler_order_number"] = bf[3] if len(bf) > 3 else ""
            
            service = bf[4] if len(bf) > 4 else ""
            service_parsed = parse_ce(service)
            result["universal_service_id"] = service
            result["service_code"] = service_parsed["code"]
            result["service_text"] = service_parsed["text"]
            result["service_coding_system"] = service_parsed["coding_system"]
            
            result["observation_datetime"] = bf[7] if len(bf) > 7 else ""
            result["result_status"] = bf[25] if len(bf) > 25 else ""
            
        elif line.startswith("OBX"):
            xf = line.split("|")
            
            obs_id = xf[3] if len(xf) > 3 else ""
            obs_id_parsed = parse_ce(obs_id)
            
            units = xf[6] if len(xf) > 6 else ""
            units_parsed = parse_ce(units)
            
            obs = {
                "set_id": xf[1] if len(xf) > 1 else "",
                "value_type": xf[2] if len(xf) > 2 else "",
                "observation_id": obs_id,
                "observation_code": obs_id_parsed["code"],
                "observation_text": obs_id_parsed["text"],
                "observation_coding_system": obs_id_parsed["coding_system"],
                "observation_value": xf[5] if len(xf) > 5 else "",
                "units": units,
                "units_code": units_parsed["code"],
                "units_text": units_parsed["text"],
                "reference_range": xf[7] if len(xf) > 7 else "",
                "abnormal_flags": xf[8] if len(xf) > 8 else "",
                "observation_result_status": xf[11] if len(xf) > 11 else "",
            }
            observations.append(obs)
    result["observations"] = observations


def _parse_siu_segments(lines, result):
    """Parse SIU-specific segments."""
    resources = []
    for line in lines:
        if line.startswith("SCH"):
            sf = line.split("|")
            result["placer_appointment_id"] = sf[1] if len(sf) > 1 else ""
            result["filler_appointment_id"] = sf[2] if len(sf) > 2 else ""
            
            reason = sf[7] if len(sf) > 7 else ""
            reason_parsed = parse_ce(reason)
            result["appointment_reason"] = reason
            result["appointment_reason_code"] = reason_parsed["code"]
            result["appointment_reason_text"] = reason_parsed["text"]
            
            appt_type = sf[8] if len(sf) > 8 else ""
            type_parsed = parse_ce(appt_type)
            result["appointment_type"] = appt_type
            result["appointment_type_code"] = type_parsed["code"]
            result["appointment_type_text"] = type_parsed["text"]
            
            result["appointment_duration"] = sf[9] if len(sf) > 9 else ""
    result["appointment_resources"] = resources


def _parse_vxu_segments(lines, result):
    """Parse VXU-specific segments."""
    vaccinations = []
    observations = []
    current_vax = None
    
    for line in lines:
        if line.startswith("ORC"):
            if current_vax:
                vaccinations.append(current_vax)
            of = line.split("|")
            current_vax = {
                "order_control": of[1] if len(of) > 1 else "",
                "placer_order_number": of[2] if len(of) > 2 else "",
                "filler_order_number": of[3] if len(of) > 3 else "",
            }
            
        elif line.startswith("RXA"):
            rf = line.split("|")
            if current_vax is None:
                current_vax = {}
            
            current_vax["administration_start_datetime"] = rf[3] if len(rf) > 3 else ""
            
            vaccine = rf[5] if len(rf) > 5 else ""
            vaccine_parsed = parse_ce(vaccine)
            current_vax["vaccine_code"] = vaccine_parsed["code"]
            current_vax["vaccine_name"] = vaccine_parsed["text"]
            current_vax["vaccine_coding_system"] = vaccine_parsed["coding_system"]
            
            current_vax["administered_amount"] = rf[6] if len(rf) > 6 else ""
            current_vax["lot_number"] = rf[15] if len(rf) > 15 else ""
            
            mfr = rf[17] if len(rf) > 17 else ""
            mfr_parsed = parse_ce(mfr)
            current_vax["manufacturer_code"] = mfr_parsed["code"]
            current_vax["manufacturer_name"] = mfr_parsed["text"]
    
    if current_vax:
        vaccinations.append(current_vax)
    
    result["vaccinations"] = vaccinations
    result["observations"] = observations


# =============================================================================
# Sample Messages for Testing
# =============================================================================

# ADT A01 (Admit) with full location and provider details
SAMPLE_ADT_A01 = """MSH|^~\\&|HIS|HOSPITAL|LAB|LAB|20240115120000||ADT^A01|MSG00001|P|2.5.1
EVN|A01|20240115120000||ADM
PID|||P001^^^HOSP^MR||DOE^JOHN^WILLIAM^JR^DR||19850315|M|||123 MAIN ST^APT 4B^CHICAGO^IL^60601^USA
PV1||I|ICU^1001^A^HOSPITAL^ACTIVE^ICU^MAINBLDG^3||ER^2002^B|OLD UNIT^OLD ROOM^OLD BED|12345^SMITH^JANE^M^^DR^MD|67890^JONES^ROBERT^^^DR^MD||CARDIO"""

# ADT A03 (Discharge)
SAMPLE_ADT_A03 = """MSH|^~\\&|HIS|HOSPITAL|LAB|LAB|20240116150000||ADT^A03|MSG00002|P|2.5.1
EVN|A03|20240116150000||DIS
PID|||P001^^^HOSP^MR||DOE^JOHN^WILLIAM||19850315|M
PV1||I|MEDSURG^1002^A^HOSPITAL|||||12345^SMITH^JANE^^^DR^MD"""

# ORU R01 (Lab Results) with multiple observations
SAMPLE_ORU_R01 = """MSH|^~\\&|LAB|HOSPITAL|HIS|HOSPITAL|20240115140000||ORU^R01|MSG00003|P|2.5.1
PID|||P001^^^HOSP^MR||DOE^JOHN^WILLIAM||19850315|M
OBR||ORD123|FIL456|1234-5^Basic Metabolic Panel^LN|||20240115133000||||||||||||||||F
OBX|1|NM|2345-7^Glucose^LN||95|mg/dL^milligrams per deciliter^UCUM|70-100||||F
OBX|2|NM|2951-2^Sodium^LN||140|mmol/L^millimoles per liter^UCUM|136-145||||F
OBX|3|NM|2823-3^Potassium^LN||4.2|mmol/L^millimoles per liter^UCUM|3.5-5.0||||F
OBX|4|NM|6299-2^BUN^LN||18|mg/dL^milligrams per deciliter^UCUM|7-20|H|||F"""

# ORM O01 (New Order) with service details
SAMPLE_ORM_O01 = """MSH|^~\\&|HIS|HOSPITAL|LAB|HOSPITAL|20240115100000||ORM^O01|MSG00004|P|2.5.1
PID|||P001^^^HOSP^MR||DOE^JOHN
ORC|NW|ORD789|||SC||||20240115100000|||12345^SMITH^JANE^^^DR^MD
OBR||ORD789||80053^Comprehensive Metabolic Panel^CPT|||20240115100000"""

# SIU S12 (Schedule New Appointment)
SAMPLE_SIU_S12 = """MSH|^~\\&|SCH|HOSPITAL|HIS|HOSPITAL|20240120080000||SIU^S12|MSG00005|P|2.5.1
PID|||P002^^^HOSP^MR||SMITH^MARY^ANN
SCH|APT001|APT001-F|||||ROUTINE^Routine Checkup^HL70276|CHECKUP^Annual Physical^LOCAL|30|MIN|^^^20240125090000^20240125093000"""

# VXU V04 (Vaccination Record)
# RXA fields: 1=SubID, 2=AdminSubID, 3=StartDT, 4=EndDT, 5=Code, 6=Amount, 7=Units,
#             8-14=various (7 empty), 15=LotNumber, 16=ExpDate, 17=Manufacturer
SAMPLE_VXU_V04 = """MSH|^~\\&|IIS|HOSPITAL|HIS|HOSPITAL|20240118100000||VXU^V04|MSG00006|P|2.5.1
PID|||P003^^^HOSP^MR||JOHNSON^BABY^M||20230815|F
ORC|RE|VAX001|VAX001-F
RXA|0|1|20240118100000||03^MMR^CVX|0.5|ML||||||||LOT123|20251218|MSD^Merck^MVX"""

# Malformed message (no MSH)
SAMPLE_MALFORMED_NO_MSH = """PID|||P001||DOE^JOHN
PV1||I|UNIT^ROOM^BED"""

# Empty message
SAMPLE_EMPTY = ""

# Message with minimal fields
# MSH fields: 2=Enc, 3=SendApp, 4=SendFac, 5=RecvApp, 6=RecvFac, 7=DateTime, 8=Security, 9=MsgType, 10=CtrlID, 11=ProcID, 12=Version
# After split: [0]=MSH, [1]=Enc, [2]=SendApp, [3]=SendFac, [4]=RecvApp, [5]=RecvFac, [6]=DT, [7]=Sec, [8]=MsgType, [9]=CtrlID
SAMPLE_MINIMAL = """MSH|^~\\&|APP|FAC|||||ADT^A01|CTRL001|P|2.5.1"""

# Batch with mixed message types
SAMPLE_BATCH_MIXED = """MSH|^~\\&|HIS|HOSPITAL|LAB|LAB|20240115120000||ADT^A01|MSG00001|P|2.5.1
PID|||P001^^^HOSP^MR||DOE^JOHN^WILLIAM||19850315|M|||123 MAIN ST^APT 4B^CHICAGO^IL^60601^USA
PV1||I|ICU^1001^A^HOSPITAL|||ER^2002^B|12345^SMITH^JANE^^^DR^MD
MSH|^~\\&|LAB|HOSPITAL|HIS|HOSPITAL|20240115140000||ORU^R01|MSG00002|P|2.5.1
PID|||P001^^^HOSP^MR||DOE^JOHN||19850315|M
OBR||ORD123||1234-5^Basic Metabolic Panel^LN|||20240115133000
OBX|1|NM|2345-7^Glucose^LN||95|mg/dL^milligrams per deciliter^UCUM|70-100||||F"""


# =============================================================================
# Composite Field Parser Tests
# =============================================================================

def test_parse_pl_full():
    """Test PL parsing with all components."""
    result = parse_pl("ICU^1001^A^HOSPITAL^ACTIVE^ICU^MAINBLDG^3^Critical Care Unit")
    assert result["unit"] == "ICU"
    assert result["room"] == "1001"
    assert result["bed"] == "A"
    assert result["facility"] == "HOSPITAL"
    assert result["building"] == "MAINBLDG"
    assert result["floor"] == "3"


def test_parse_pl_partial():
    """Test PL parsing with only unit^room^bed."""
    result = parse_pl("1001^2002^01")
    assert result["unit"] == "1001"
    assert result["room"] == "2002"
    assert result["bed"] == "01"
    assert result["facility"] == ""
    assert result["building"] == ""
    assert result["floor"] == ""


def test_parse_pl_empty():
    """Test PL parsing with empty value."""
    result = parse_pl("")
    assert result["unit"] == ""
    assert result["room"] == ""
    assert result["bed"] == ""


def test_parse_pl_none():
    """Test PL parsing with None value."""
    result = parse_pl(None)
    assert result["unit"] == ""


def test_parse_xcn_full():
    """Test XCN parsing with all components."""
    result = parse_xcn("12345^SMITH^JANE^M^JR^DR^MD")
    assert result["id"] == "12345"
    assert result["family_name"] == "SMITH"
    assert result["given_name"] == "JANE"
    assert result["degree"] == "MD"


def test_parse_xcn_partial():
    """Test XCN parsing with only ID and names."""
    result = parse_xcn("12345^SMITH^JANE")
    assert result["id"] == "12345"
    assert result["family_name"] == "SMITH"
    assert result["given_name"] == "JANE"
    assert result["degree"] == ""


def test_parse_cx_full():
    """Test CX parsing with all components."""
    result = parse_cx("P001^^^HOSP^MR")
    assert result["id"] == "P001"
    assert result["assigning_authority"] == "HOSP"
    assert result["id_type"] == "MR"


def test_parse_ce_full():
    """Test CE parsing with all components."""
    result = parse_ce("2345-7^Glucose^LN")
    assert result["code"] == "2345-7"
    assert result["text"] == "Glucose"
    assert result["coding_system"] == "LN"


def test_parse_xpn_full():
    """Test XPN parsing with all components."""
    result = parse_xpn("DOE^JOHN^WILLIAM^JR^DR")
    assert result["family"] == "DOE"
    assert result["given"] == "JOHN"
    assert result["middle"] == "WILLIAM"
    assert result["suffix"] == "JR"
    assert result["prefix"] == "DR"


def test_parse_xad_full():
    """Test XAD parsing with all components."""
    result = parse_xad("123 MAIN ST^APT 4B^CHICAGO^IL^60601^USA")
    assert result["street"] == "123 MAIN ST"
    assert result["city"] == "CHICAGO"
    assert result["state"] == "IL"
    assert result["zip"] == "60601"
    assert result["country"] == "USA"


# =============================================================================
# Batch Splitting Tests
# =============================================================================

def test_split_hl7_batch_single():
    """Test splitting a single message."""
    msgs = split_hl7_batch(SAMPLE_ADT_A01)
    assert len(msgs) == 1
    assert msgs[0].startswith("MSH|")


def test_split_hl7_batch_multiple():
    """Test splitting multiple messages."""
    msgs = split_hl7_batch(SAMPLE_BATCH_MIXED)
    assert len(msgs) == 2
    assert all(m.startswith("MSH|") for m in msgs)


def test_split_hl7_batch_empty():
    """Test splitting empty content."""
    msgs = split_hl7_batch("")
    assert len(msgs) == 0


def test_split_hl7_batch_crlf():
    """Test splitting with Windows line endings."""
    windows_msg = SAMPLE_ADT_A01.replace("\n", "\r\n")
    msgs = split_hl7_batch(windows_msg)
    assert len(msgs) == 1


# =============================================================================
# ADT Message Tests
# =============================================================================

def test_parse_adt_a01():
    """Test parsing ADT A01 (Admit) message."""
    result = parse_hl7v2_message(SAMPLE_ADT_A01)
    
    assert result is not None
    assert result["_parse_error"] is None
    
    # MSH fields
    assert result["message_type"] == "ADT"
    assert result["trigger_event"] == "A01"
    assert result["message_control_id"] == "MSG00001"
    assert result["sending_facility"] == "HOSPITAL"
    
    # Patient ID (CX parsed)
    assert result["patient_id"] == "P001"
    assert result["patient_id_assigning_authority"] == "HOSP"
    assert result["patient_id_type"] == "MR"
    
    # Patient Name (XPN parsed)
    assert result["patient_name_family"] == "DOE"
    assert result["patient_name_given"] == "JOHN"
    assert result["patient_name_middle"] == "WILLIAM"
    assert result["patient_name_suffix"] == "JR"
    assert result["patient_name_prefix"] == "DR"
    
    # Patient Address (XAD parsed)
    assert result["patient_address_street"] == "123 MAIN ST"
    assert result["patient_address_city"] == "CHICAGO"
    assert result["patient_address_state"] == "IL"
    assert result["patient_address_zip"] == "60601"
    assert result["patient_address_country"] == "USA"
    
    # Location (PL parsed)
    assert result["location_unit"] == "ICU"
    assert result["location_room"] == "1001"
    assert result["location_bed"] == "A"
    assert result["location_facility"] == "HOSPITAL"
    assert result["location_building"] == "MAINBLDG"
    assert result["location_floor"] == "3"
    
    # Prior Location (PL parsed)
    assert result["prior_location_unit"] == "OLD UNIT"
    assert result["prior_location_room"] == "OLD ROOM"
    assert result["prior_location_bed"] == "OLD BED"
    
    # Attending Doctor (XCN parsed)
    assert result["attending_doctor_id"] == "12345"
    assert result["attending_doctor_family"] == "SMITH"
    assert result["attending_doctor_given"] == "JANE"
    
    # Referring Doctor (XCN parsed)
    assert result["referring_doctor_id"] == "67890"
    assert result["referring_doctor_family"] == "JONES"
    assert result["referring_doctor_given"] == "ROBERT"


def test_parse_adt_a03():
    """Test parsing ADT A03 (Discharge) message."""
    result = parse_hl7v2_message(SAMPLE_ADT_A03)
    
    assert result is not None
    assert result["message_type"] == "ADT"
    assert result["trigger_event"] == "A03"
    assert result["event_type_code"] == "A03"


# =============================================================================
# ORU Message Tests
# =============================================================================

def test_parse_oru_r01():
    """Test parsing ORU R01 (Lab Results) message."""
    result = parse_hl7v2_message(SAMPLE_ORU_R01)
    
    assert result is not None
    assert result["_parse_error"] is None
    assert result["message_type"] == "ORU"
    assert result["trigger_event"] == "R01"
    
    # Service (CE parsed)
    assert result["service_code"] == "1234-5"
    assert result["service_text"] == "Basic Metabolic Panel"
    assert result["service_coding_system"] == "LN"
    
    # Observations
    obs = result.get("observations", [])
    assert len(obs) == 4
    
    # First observation (Glucose)
    assert obs[0]["observation_code"] == "2345-7"
    assert obs[0]["observation_text"] == "Glucose"
    assert obs[0]["observation_coding_system"] == "LN"
    assert obs[0]["observation_value"] == "95"
    assert obs[0]["units_code"] == "mg/dL"
    assert obs[0]["units_text"] == "milligrams per deciliter"
    assert obs[0]["reference_range"] == "70-100"


# =============================================================================
# ORM Message Tests
# =============================================================================

def test_parse_orm_o01():
    """Test parsing ORM O01 (New Order) message."""
    result = parse_hl7v2_message(SAMPLE_ORM_O01)
    
    assert result is not None
    assert result["_parse_error"] is None
    assert result["message_type"] == "ORM"
    assert result["trigger_event"] == "O01"
    
    # Order fields
    assert result["order_control"] == "NW"
    assert result["order_id"] == "ORD789"
    
    # Ordering Provider (XCN parsed)
    assert result["ordering_provider_id"] == "12345"
    assert result["ordering_provider_family"] == "SMITH"
    assert result["ordering_provider_given"] == "JANE"
    
    # Service (CE parsed)
    assert result["service_code"] == "80053"
    assert result["service_text"] == "Comprehensive Metabolic Panel"
    assert result["service_coding_system"] == "CPT"


# =============================================================================
# SIU Message Tests
# =============================================================================

def test_parse_siu_s12():
    """Test parsing SIU S12 (Schedule) message."""
    result = parse_hl7v2_message(SAMPLE_SIU_S12)
    
    assert result is not None
    assert result["_parse_error"] is None
    assert result["message_type"] == "SIU"
    assert result["trigger_event"] == "S12"
    
    # Appointment fields
    assert result["placer_appointment_id"] == "APT001"
    
    # Reason (CE parsed)
    assert result["appointment_reason_code"] == "ROUTINE"
    assert result["appointment_reason_text"] == "Routine Checkup"
    
    # Type (CE parsed)
    assert result["appointment_type_code"] == "CHECKUP"
    assert result["appointment_type_text"] == "Annual Physical"


# =============================================================================
# VXU Message Tests
# =============================================================================

def test_parse_vxu_v04():
    """Test parsing VXU V04 (Vaccination) message."""
    result = parse_hl7v2_message(SAMPLE_VXU_V04)
    
    assert result is not None
    assert result["_parse_error"] is None
    assert result["message_type"] == "VXU"
    assert result["trigger_event"] == "V04"
    
    # Vaccinations array
    vax = result.get("vaccinations", [])
    assert len(vax) == 1
    
    # Vaccine (CE parsed)
    assert vax[0]["vaccine_code"] == "03"
    assert vax[0]["vaccine_name"] == "MMR"
    assert vax[0]["vaccine_coding_system"] == "CVX"
    
    # Manufacturer (CE parsed)
    assert vax[0]["manufacturer_code"] == "MSD"
    assert vax[0]["manufacturer_name"] == "Merck"
    
    assert vax[0]["lot_number"] == "LOT123"


# =============================================================================
# Edge Case Tests
# =============================================================================

def test_parse_malformed_no_msh():
    """Test parsing message without MSH segment."""
    result = parse_hl7v2_message(SAMPLE_MALFORMED_NO_MSH)
    assert result is None


def test_parse_empty():
    """Test parsing empty message."""
    result = parse_hl7v2_message(SAMPLE_EMPTY)
    assert result is None


def test_parse_minimal():
    """Test parsing minimal valid message."""
    result = parse_hl7v2_message(SAMPLE_MINIMAL)
    assert result is not None
    assert result["message_type"] == "ADT"
    assert result["message_control_id"] == "CTRL001"


def test_parse_null_input():
    """Test parsing None input."""
    result = parse_hl7v2_message(None)
    assert result is None


def test_parse_whitespace_only():
    """Test parsing whitespace-only input."""
    result = parse_hl7v2_message("   \n\t  ")
    assert result is None


# =============================================================================
# Expectation Validation Tests (simulating DLT expectations)
# =============================================================================

def validate_adt_expectations(result):
    """Validate ADT-specific expectations."""
    errors = []
    if not result:
        return ["Message parsed to None"]
    if not result.get("message_control_id"):
        errors.append("Missing message_control_id")
    if result.get("message_type") != "ADT":
        errors.append(f"Invalid message_type: {result.get('message_type')}")
    if not result.get("patient_id"):
        errors.append("Missing patient_id (warning)")
    if not result.get("trigger_event"):
        errors.append("Missing trigger_event (warning)")
    return errors


def validate_oru_expectations(result):
    """Validate ORU-specific expectations."""
    errors = []
    if not result:
        return ["Message parsed to None"]
    if not result.get("message_control_id"):
        errors.append("Missing message_control_id")
    if result.get("message_type") != "ORU":
        errors.append(f"Invalid message_type: {result.get('message_type')}")
    if not result.get("patient_id"):
        errors.append("Missing patient_id (warning)")
    obs = result.get("observations", [])
    if not obs:
        errors.append("Missing observations (warning)")
    return errors


def test_adt_expectations_pass():
    """Test ADT expectations on valid message."""
    result = parse_hl7v2_message(SAMPLE_ADT_A01)
    errors = validate_adt_expectations(result)
    assert len(errors) == 0, f"Unexpected errors: {errors}"


def test_oru_expectations_pass():
    """Test ORU expectations on valid message."""
    result = parse_hl7v2_message(SAMPLE_ORU_R01)
    errors = validate_oru_expectations(result)
    assert len(errors) == 0, f"Unexpected errors: {errors}"


def test_expectations_on_minimal():
    """Test expectations on minimal message (should have warnings)."""
    result = parse_hl7v2_message(SAMPLE_MINIMAL)
    errors = validate_adt_expectations(result)
    # Should have warnings for missing patient_id, trigger_event
    assert "Missing patient_id (warning)" in errors or "Missing trigger_event (warning)" in errors


# =============================================================================
# Test Runner
# =============================================================================

def run_all_tests():
    """Run all tests and report results."""
    import sys
    
    tests = [
        # Composite field parser tests
        ("test_parse_pl_full", test_parse_pl_full),
        ("test_parse_pl_partial", test_parse_pl_partial),
        ("test_parse_pl_empty", test_parse_pl_empty),
        ("test_parse_pl_none", test_parse_pl_none),
        ("test_parse_xcn_full", test_parse_xcn_full),
        ("test_parse_xcn_partial", test_parse_xcn_partial),
        ("test_parse_cx_full", test_parse_cx_full),
        ("test_parse_ce_full", test_parse_ce_full),
        ("test_parse_xpn_full", test_parse_xpn_full),
        ("test_parse_xad_full", test_parse_xad_full),
        # Batch splitting tests
        ("test_split_hl7_batch_single", test_split_hl7_batch_single),
        ("test_split_hl7_batch_multiple", test_split_hl7_batch_multiple),
        ("test_split_hl7_batch_empty", test_split_hl7_batch_empty),
        ("test_split_hl7_batch_crlf", test_split_hl7_batch_crlf),
        # ADT tests
        ("test_parse_adt_a01", test_parse_adt_a01),
        ("test_parse_adt_a03", test_parse_adt_a03),
        # ORU tests
        ("test_parse_oru_r01", test_parse_oru_r01),
        # ORM tests
        ("test_parse_orm_o01", test_parse_orm_o01),
        # SIU tests
        ("test_parse_siu_s12", test_parse_siu_s12),
        # VXU tests
        ("test_parse_vxu_v04", test_parse_vxu_v04),
        # Edge case tests
        ("test_parse_malformed_no_msh", test_parse_malformed_no_msh),
        ("test_parse_empty", test_parse_empty),
        ("test_parse_minimal", test_parse_minimal),
        ("test_parse_null_input", test_parse_null_input),
        ("test_parse_whitespace_only", test_parse_whitespace_only),
        # Expectation tests
        ("test_adt_expectations_pass", test_adt_expectations_pass),
        ("test_oru_expectations_pass", test_oru_expectations_pass),
        ("test_expectations_on_minimal", test_expectations_on_minimal),
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 70)
    print("HL7v2 Parser Tests - Production Grade Validation")
    print("=" * 70)
    
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  PASS: {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {name}")
            print(f"        {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {name}")
            print(f"         {type(e).__name__}: {e}")
            failed += 1
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
