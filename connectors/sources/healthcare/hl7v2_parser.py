"""
HL7v2 Message Parser.

Parses HL7v2 messages (ADT, ORM, ORU) into structured dictionaries.
Supports both single-message files and batch files with multiple messages.

Uses hl7apy library for parsing when available, falls back to manual parsing.
"""

from typing import Optional, List
import re


def split_hl7_batch(content: str) -> List[str]:
    """
    Split a batch file containing multiple HL7v2 messages into individual messages.
    
    HL7v2 batch files can contain:
    - Multiple messages, each starting with MSH segment
    - Optional FHS (File Header) and BHS (Batch Header) segments
    - Optional FTS (File Trailer) and BTS (Batch Trailer) segments
    
    Args:
        content: Raw file content (may contain multiple messages)
        
    Returns:
        List of individual message strings
    """
    if not content or not content.strip():
        return []
    
    # Normalize line endings
    content = content.replace("\r\n", "\r").replace("\n", "\r")
    
    # Split by MSH segment (each MSH starts a new message)
    # The pattern captures "MSH|" at the start of a line
    messages = []
    
    # Find all MSH positions
    msh_pattern = re.compile(r'(?:^|\r)(MSH\|)', re.MULTILINE)
    matches = list(msh_pattern.finditer(content))
    
    if not matches:
        # No MSH found, try treating entire content as single message
        if content.strip().startswith("MSH"):
            return [content.strip().replace("\r", "\n")]
        return []
    
    for i, match in enumerate(matches):
        # Start position (after the newline, at MSH)
        start = match.start()
        if content[start] == '\r':
            start += 1
        
        # End position (start of next MSH or end of content)
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(content)
        
        msg = content[start:end].strip()
        if msg:
            # Convert back to newlines for processing
            messages.append(msg.replace("\r", "\n"))
    
    return messages


def parse_hl7v2_file(content: str) -> List[dict]:
    """
    Parse an HL7v2 file that may contain multiple messages.
    
    This is the recommended entry point for file-based parsing.
    
    Args:
        content: Raw file content (single or batch)
        
    Returns:
        List of parsed message dictionaries
    """
    messages = split_hl7_batch(content)
    results = []
    
    for msg in messages:
        parsed = parse_hl7v2_message(msg)
        if parsed:
            results.append(parsed)
    
    return results


def parse_hl7v2_message(message: str) -> Optional[dict]:
    """
    Parse an HL7v2 message into a structured dictionary.
    
    Args:
        message: Raw HL7v2 message string
        
    Returns:
        Dictionary with parsed fields, or None if invalid
    """
    if not message or not message.strip():
        return None
    
    # Normalize line endings
    message = message.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line for line in message.strip().split("\n") if line]
    
    if not lines:
        return None
    
    # Must start with MSH segment
    if not lines[0].startswith("MSH"):
        return None
    
    try:
        result = {}
        
        # Parse MSH segment
        msh = parse_msh_segment(message)
        if not msh:
            return None
        
        result.update(msh)
        
        # Extract message type and trigger
        msg_type_parts = msh.get("message_type", "").split("^")
        result["message_type"] = msg_type_parts[0] if msg_type_parts else ""
        result["trigger_event"] = msg_type_parts[1] if len(msg_type_parts) > 1 else ""
        
        # Parse PID segment if present
        pid = parse_pid_segment(message)
        if pid:
            result.update(pid)
        
        # Parse message-type specific segments
        if result["message_type"] == "ADT":
            result.update(_parse_adt_specific(message))
        elif result["message_type"] == "ORM":
            result.update(_parse_orm_specific(message))
        elif result["message_type"] == "ORU":
            result.update(_parse_oru_specific(message))
        elif result["message_type"] == "SIU":
            result.update(_parse_siu_specific(message))
        elif result["message_type"] == "VXU":
            result.update(_parse_vxu_specific(message))
        
        return result
        
    except Exception:
        return None


def parse_msh_segment(message: str) -> Optional[dict]:
    """
    Parse MSH (Message Header) segment.
    
    MSH fields:
    0: Segment ID (MSH)
    1: Field Separator (|)
    2: Encoding Characters (^~\\&)
    3: Sending Application
    4: Sending Facility
    5: Receiving Application
    6: Receiving Facility
    7: Date/Time of Message
    8: Security
    9: Message Type
    10: Message Control ID
    11: Processing ID
    12: Version ID
    """
    lines = message.replace("\r", "\n").split("\n")
    msh_line = None
    for line in lines:
        if line.startswith("MSH"):
            msh_line = line
            break
    
    if not msh_line:
        return None
    
    # MSH uses | as field separator, but first | is field 1
    # So we split and adjust indexing
    fields = msh_line.split("|")
    
    return {
        "sending_application": fields[2] if len(fields) > 2 else "",
        "sending_facility": fields[3] if len(fields) > 3 else "",
        "receiving_application": fields[4] if len(fields) > 4 else "",
        "receiving_facility": fields[5] if len(fields) > 5 else "",
        "message_datetime": fields[6] if len(fields) > 6 else "",
        "message_type": fields[8] if len(fields) > 8 else "",
        "message_control_id": fields[9] if len(fields) > 9 else "",
        "processing_id": fields[10] if len(fields) > 10 else "",
        "version_id": fields[11] if len(fields) > 11 else "",
    }


def parse_pid_segment(message: str) -> Optional[dict]:
    """
    Parse PID (Patient Identification) segment.
    
    PID fields:
    0: Segment ID (PID)
    1: Set ID
    2: Patient ID (External)
    3: Patient ID (Internal) - often MRN
    4: Alternate Patient ID
    5: Patient Name
    6: Mother's Maiden Name
    7: Date of Birth
    8: Sex
    """
    lines = message.replace("\r", "\n").split("\n")
    pid_line = None
    for line in lines:
        if line.startswith("PID"):
            pid_line = line
            break
    
    if not pid_line:
        return None
    
    fields = pid_line.split("|")
    
    # Extract patient ID from field 3 (internal ID)
    # Format: ID^^^NAMESPACE^TYPE
    patient_id_field = fields[3] if len(fields) > 3 else ""
    patient_id = patient_id_field.split("^")[0] if patient_id_field else ""
    
    # Extract patient name from field 5
    # Format: FAMILY^GIVEN^MIDDLE^SUFFIX^PREFIX
    name_field = fields[5] if len(fields) > 5 else ""
    name_parts = name_field.split("^")
    
    return {
        "patient_id": patient_id,
        "patient_name_family": name_parts[0] if name_parts else "",
        "patient_name_given": name_parts[1] if len(name_parts) > 1 else "",
        "date_of_birth": fields[7] if len(fields) > 7 else "",
        "gender": fields[8] if len(fields) > 8 else "",
    }


def _parse_adt_specific(message: str) -> dict:
    """Parse ADT-specific segments (EVN, PV1)."""
    result = {}
    
    lines = message.replace("\r", "\n").split("\n")
    
    for line in lines:
        # EVN - Event Type
        if line.startswith("EVN"):
            fields = line.split("|")
            result["event_type_code"] = fields[1] if len(fields) > 1 else ""
            result["event_datetime"] = fields[2] if len(fields) > 2 else ""
        
        # PV1 - Patient Visit
        elif line.startswith("PV1"):
            fields = line.split("|")
            result["patient_class"] = fields[2] if len(fields) > 2 else ""
            result["assigned_location"] = fields[3] if len(fields) > 3 else ""
            result["admission_type"] = fields[4] if len(fields) > 4 else ""
    
    return result


def _parse_orm_specific(message: str) -> dict:
    """Parse ORM-specific segments (ORC, OBR)."""
    result = {}
    
    lines = message.replace("\r", "\n").split("\n")
    
    for line in lines:
        # ORC - Common Order
        if line.startswith("ORC"):
            fields = line.split("|")
            result["order_control"] = fields[1] if len(fields) > 1 else ""
            result["order_id"] = fields[2] if len(fields) > 2 else ""
            result["filler_order_number"] = fields[3] if len(fields) > 3 else ""
            result["order_status"] = fields[5] if len(fields) > 5 else ""
        
        # OBR - Observation Request
        elif line.startswith("OBR"):
            fields = line.split("|")
            result["placer_order_number"] = fields[2] if len(fields) > 2 else ""
            result["universal_service_id"] = fields[4] if len(fields) > 4 else ""
    
    return result


def _parse_oru_specific(message: str) -> dict:
    """Parse ORU-specific segments (OBR, OBX)."""
    result = {}
    observations = []
    
    lines = message.replace("\r", "\n").split("\n")
    
    for line in lines:
        # OBR - Observation Request
        if line.startswith("OBR"):
            fields = line.split("|")
            result["placer_order_number"] = fields[2] if len(fields) > 2 else ""
            result["filler_order_number"] = fields[3] if len(fields) > 3 else ""
            result["universal_service_id"] = fields[4] if len(fields) > 4 else ""
        
        # OBX - Observation/Result
        elif line.startswith("OBX"):
            fields = line.split("|")
            obs = {
                "set_id": fields[1] if len(fields) > 1 else "",
                "value_type": fields[2] if len(fields) > 2 else "",
                "observation_id": fields[3] if len(fields) > 3 else "",
                "observation_value": fields[5] if len(fields) > 5 else "",
                "units": fields[6] if len(fields) > 6 else "",
                "reference_range": fields[7] if len(fields) > 7 else "",
                "abnormal_flags": fields[8] if len(fields) > 8 else "",
                "result_status": fields[11] if len(fields) > 11 else "",
            }
            observations.append(obs)
    
    result["observations"] = observations
    return result


def _parse_siu_specific(message: str) -> dict:
    """
    Parse SIU-specific segments (SCH, AIS, AIP, AIL).
    
    SIU = Scheduling Information Unsolicited
    Used for appointment scheduling, rescheduling, cancellation.
    
    Common trigger events:
    - S12: New appointment
    - S13: Rescheduled appointment
    - S14: Modified appointment
    - S15: Cancelled appointment
    - S26: Patient no-show
    """
    result = {}
    resources = []
    
    lines = message.replace("\r", "\n").split("\n")
    
    for line in lines:
        # SCH - Scheduling Activity Information
        if line.startswith("SCH"):
            fields = line.split("|")
            result["placer_appointment_id"] = fields[1] if len(fields) > 1 else ""
            result["filler_appointment_id"] = fields[2] if len(fields) > 2 else ""
            result["occurrence_number"] = fields[3] if len(fields) > 3 else ""
            result["placer_group_number"] = fields[4] if len(fields) > 4 else ""
            result["schedule_id"] = fields[5] if len(fields) > 5 else ""
            result["event_reason"] = fields[6] if len(fields) > 6 else ""
            result["appointment_reason"] = fields[7] if len(fields) > 7 else ""
            result["appointment_type"] = fields[8] if len(fields) > 8 else ""
            result["appointment_duration"] = fields[9] if len(fields) > 9 else ""
            result["appointment_duration_units"] = fields[10] if len(fields) > 10 else ""
            # Timing quantity (field 11) contains start/end times
            timing = fields[11] if len(fields) > 11 else ""
            timing_parts = timing.split("^")
            result["appointment_start_datetime"] = timing_parts[0] if timing_parts else ""
            result["appointment_end_datetime"] = timing_parts[1] if len(timing_parts) > 1 else ""
            result["filler_status_code"] = fields[25] if len(fields) > 25 else ""
        
        # AIS - Appointment Information - Service
        elif line.startswith("AIS"):
            fields = line.split("|")
            resource = {
                "resource_type": "service",
                "set_id": fields[1] if len(fields) > 1 else "",
                "universal_service_id": fields[3] if len(fields) > 3 else "",
                "start_datetime": fields[4] if len(fields) > 4 else "",
                "start_datetime_offset": fields[5] if len(fields) > 5 else "",
                "duration": fields[7] if len(fields) > 7 else "",
                "filler_status_code": fields[10] if len(fields) > 10 else "",
            }
            resources.append(resource)
        
        # AIP - Appointment Information - Personnel
        elif line.startswith("AIP"):
            fields = line.split("|")
            resource = {
                "resource_type": "personnel",
                "set_id": fields[1] if len(fields) > 1 else "",
                "personnel_id": fields[3] if len(fields) > 3 else "",
                "resource_role": fields[4] if len(fields) > 4 else "",
                "start_datetime": fields[6] if len(fields) > 6 else "",
                "duration": fields[8] if len(fields) > 8 else "",
            }
            resources.append(resource)
        
        # AIL - Appointment Information - Location
        elif line.startswith("AIL"):
            fields = line.split("|")
            resource = {
                "resource_type": "location",
                "set_id": fields[1] if len(fields) > 1 else "",
                "location_id": fields[3] if len(fields) > 3 else "",
                "location_type": fields[4] if len(fields) > 4 else "",
                "start_datetime": fields[6] if len(fields) > 6 else "",
                "duration": fields[8] if len(fields) > 8 else "",
            }
            resources.append(resource)
    
    result["appointment_resources"] = resources
    return result


def _parse_vxu_specific(message: str) -> dict:
    """
    Parse VXU-specific segments (RXA, RXR, OBX).
    
    VXU = Vaccination Record Update
    Used for immunization records.
    
    Common trigger event:
    - V04: Unsolicited vaccination record update
    """
    result = {}
    vaccinations = []
    observations = []
    
    lines = message.replace("\r", "\n").split("\n")
    current_vaccination = None
    
    for line in lines:
        # ORC - Order segment (marks start of a vaccination order group)
        if line.startswith("ORC"):
            # Save previous vaccination if exists
            if current_vaccination:
                vaccinations.append(current_vaccination)
            fields = line.split("|")
            current_vaccination = {
                "order_control": fields[1] if len(fields) > 1 else "",
                "placer_order_number": fields[2] if len(fields) > 2 else "",
                "filler_order_number": fields[3] if len(fields) > 3 else "",
                "order_status": fields[5] if len(fields) > 5 else "",
            }
        
        # RXA - Pharmacy/Treatment Administration
        elif line.startswith("RXA"):
            fields = line.split("|")
            if current_vaccination is None:
                current_vaccination = {}
            
            current_vaccination["give_sub_id"] = fields[1] if len(fields) > 1 else ""
            current_vaccination["administration_sub_id"] = fields[2] if len(fields) > 2 else ""
            current_vaccination["administration_start_datetime"] = fields[3] if len(fields) > 3 else ""
            current_vaccination["administration_end_datetime"] = fields[4] if len(fields) > 4 else ""
            
            # Vaccine code (field 5) - CVX code
            vaccine_code = fields[5] if len(fields) > 5 else ""
            code_parts = vaccine_code.split("^")
            current_vaccination["vaccine_code"] = code_parts[0] if code_parts else ""
            current_vaccination["vaccine_name"] = code_parts[1] if len(code_parts) > 1 else ""
            current_vaccination["vaccine_coding_system"] = code_parts[2] if len(code_parts) > 2 else ""
            
            current_vaccination["administered_amount"] = fields[6] if len(fields) > 6 else ""
            current_vaccination["administered_units"] = fields[7] if len(fields) > 7 else ""
            
            # Manufacturer (field 17)
            manufacturer = fields[17] if len(fields) > 17 else ""
            mfr_parts = manufacturer.split("^")
            current_vaccination["manufacturer_code"] = mfr_parts[0] if mfr_parts else ""
            current_vaccination["manufacturer_name"] = mfr_parts[1] if len(mfr_parts) > 1 else ""
            
            current_vaccination["lot_number"] = fields[15] if len(fields) > 15 else ""
            current_vaccination["expiration_date"] = fields[16] if len(fields) > 16 else ""
            current_vaccination["completion_status"] = fields[20] if len(fields) > 20 else ""
            current_vaccination["action_code"] = fields[21] if len(fields) > 21 else ""
        
        # RXR - Route
        elif line.startswith("RXR"):
            fields = line.split("|")
            if current_vaccination:
                route = fields[1] if len(fields) > 1 else ""
                route_parts = route.split("^")
                current_vaccination["route_code"] = route_parts[0] if route_parts else ""
                current_vaccination["route_name"] = route_parts[1] if len(route_parts) > 1 else ""
                
                site = fields[2] if len(fields) > 2 else ""
                site_parts = site.split("^")
                current_vaccination["site_code"] = site_parts[0] if site_parts else ""
                current_vaccination["site_name"] = site_parts[1] if len(site_parts) > 1 else ""
        
        # OBX - Observation (e.g., VIS date, contraindication, reaction)
        elif line.startswith("OBX"):
            fields = line.split("|")
            obs = {
                "set_id": fields[1] if len(fields) > 1 else "",
                "value_type": fields[2] if len(fields) > 2 else "",
                "observation_id": fields[3] if len(fields) > 3 else "",
                "observation_value": fields[5] if len(fields) > 5 else "",
                "units": fields[6] if len(fields) > 6 else "",
                "observation_result_status": fields[11] if len(fields) > 11 else "",
            }
            observations.append(obs)
    
    # Don't forget the last vaccination
    if current_vaccination:
        vaccinations.append(current_vaccination)
    
    result["vaccinations"] = vaccinations
    result["observations"] = observations
    return result


def get_message_type_from_content(message: str) -> Optional[str]:
    """
    Determine the HL7v2 message type from content.
    
    Returns: "ADT", "ORM", "ORU", "SIU", "VXU", or None
    """
    msh = parse_msh_segment(message)
    if not msh:
        return None
    
    msg_type = msh.get("message_type", "")
    return msg_type.split("^")[0] if msg_type else None
