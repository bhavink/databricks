"""
FHIR Ingestion Pipeline

Spark Declarative Pipeline (SDP/DLT) for ingesting FHIR R4 resources
into Databricks Lakehouse using Unity Catalog.

Architecture:
- Bronze: Raw FHIR JSON stored as VARIANT (preserves everything)
- Silver: Flattened tables by resource type (Patient, Observation, etc.)
- Quarantine: Invalid/failed records for debugging

Key Design Decisions:
- VARIANT type for semi-structured data (schema evolution, no data loss)
- Typed columns for common fields (query performance, partitioning)
- UDF inlining (all parsing logic self-contained for executor access)
- Liquid Clustering for optimal query performance

Implementation Status: PENDING (tests written first - TDD)
"""

__version__ = "0.1.0"
