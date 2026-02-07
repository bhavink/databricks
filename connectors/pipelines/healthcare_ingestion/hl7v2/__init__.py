"""
HL7v2 Ingestion Pipeline

Spark Declarative Pipeline (SDP/DLT) for ingesting HL7v2 messages
into Databricks Lakehouse using Unity Catalog.

Supported Message Types:
- ADT (Admit/Discharge/Transfer)
- ORM (Orders)
- ORU (Lab Results)
- SIU (Scheduling)
- VXU (Immunizations)

Implementation Status: COMPLETE (see transformations/bronze_hl7v2.py)
"""

__version__ = "1.0.0"
