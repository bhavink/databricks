# Healthcare Ingestion Pipelines

Spark Declarative Pipelines (SDP) for healthcare data formats.

## Pipelines

| Pipeline | Format | Tables | Standalone Bundle |
|----------|--------|--------|-------------------|
| **HL7v2** | Legacy messaging | 11 bronze | `hl7v2/databricks.yml` |
| **FHIR R4** | Modern REST API | 8 bronze/silver | `fhir/databricks.yml` |

## Quick Deploy

```bash
# HL7v2 only
cd hl7v2
databricks bundle deploy -t dev
databricks bundle run hl7v2_pipeline -t dev

# FHIR only
cd fhir
databricks bundle deploy -t dev
databricks bundle run fhir_pipeline -t dev

# Both (from connectors/ root)
databricks bundle deploy -t dev
```

## Folder Structure

```
healthcare_ingestion/
├── README.md                    # This file
├── .gitignore                   # Git ignore patterns
│
├── hl7v2/                       # HL7v2 Pipeline
│   ├── databricks.yml           # Standalone bundle
│   ├── transformations/
│   │   └── bronze_hl7v2.py      # All table definitions
│   ├── config/
│   │   └── pipeline_settings.json
│   ├── dashboards/
│   │   └── healthcare_hl7v2_operations.lvdash.json
│   └── tests/
│       └── test_hl7v2_parser.py
│
├── fhir/                        # FHIR R4 Pipeline
│   ├── databricks.yml           # Standalone bundle
│   ├── bronze_fhir.py           # Bronze layer
│   ├── silver_fhir.py           # Silver layer
│   ├── transformations/
│   │   ├── fhir_parser.py
│   │   └── fhir_schemas.py
│   ├── ingestion/
│   │   ├── fhir_client.py       # FHIR REST API client
│   │   ├── fhir_ingestion.py    # Ingestion orchestration
│   │   ├── fhir_servers.py      # Server presets (HAPI, Azure FHIR, etc.)
│   │   └── tests/
│   ├── config/
│   │   └── pipeline_settings.json
│   ├── dashboards/
│   │   ├── README.md            # Dashboard documentation
│   │   ├── healthcare_fhir_r4_operations.lvdash.json
│   │   ├── build_fhir_dashboard.py
│   │   └── deploy_fhir_dashboard.py
│   └── tests/
│       ├── conftest.py
│       └── test_fhir_*.py
│
└── notebooks/                   # Analytics
    ├── hl7v2_sankey.py          # HL7v2 flow visualizations
    ├── fhir_sankey.py           # FHIR flow visualizations
    └── fhir_api_ingestion.py    # FHIR API ingestion demo
```

## Data Flow

```
Unity Catalog Volume                   Pipeline Tables
━━━━━━━━━━━━━━━━━━━                   ━━━━━━━━━━━━━━━━
/Volumes/.../hl7v2/*.hl7    ───►      bronze_hl7v2_*
/Volumes/.../fhir/*.ndjson  ───►      bronze_fhir_*, silver_fhir_*
```

## Testing

```bash
# All tests
python -m pytest -v

# With coverage
python -m pytest --cov=fhir --cov=hl7v2 -v

# Specific pipeline
python -m pytest hl7v2/tests/ -v
python -m pytest fhir/tests/ -v
```

## Configuration

Each pipeline uses `spark.conf` for settings. Override in bundle:

```yaml
# In databricks.yml
configuration:
  healthcare.storage_path: "/Volumes/my_catalog/my_schema/my_volume/hl7v2"
  fhir.storage_path: "/Volumes/my_catalog/my_schema/my_volume/fhir"
```

Or via CLI:

```bash
databricks bundle deploy -t dev --var="catalog=my_catalog"
```

## Operational Dashboards

Both pipelines include production-ready AI/BI (Lakeview) dashboards for monitoring data quality and operational metrics.

### HL7v2 Dashboard
- **File:** `hl7v2/dashboards/healthcare_hl7v2_operations.lvdash.json`
- **Focus:** Message types (ADT, ORU, ORM, VXU), patient flow, lab operations
- **Pages:** 7 (Executive Summary, Patient Flow, Lab Operations, Clinical Orders, Immunizations, Data Quality, Advanced Analytics)

### FHIR R4 Dashboard
- **File:** `fhir/dashboards/healthcare_fhir_r4_operations.lvdash.json`
- **Documentation:** `fhir/dashboards/README.md`
- **Focus:** Resource types (Patient, Observation, Encounter, Condition), clinical operations
- **Pages:** 8 (Executive Summary, Patient Demographics, Encounters, Observations, Conditions, Medications & Immunizations, Data Quality, Advanced Analytics)

**Deployment:**
```bash
cd fhir/dashboards
python3 deploy_fhir_dashboard.py
```

See `fhir/dashboards/README.md` for complete dashboard architecture, business value, and deployment instructions.

---

## Key Design Patterns

1. **Inlined UDFs** - All parsing logic inside function (executors can't import)
2. **Liquid Clustering** - Automatic data organization for fast queries
3. **Quarantine Tables** - Failed records captured, never lost
4. **VARIANT Type** - Semi-structured FHIR data with schema evolution

See [DESIGN.md](../../DESIGN.md) for architecture details.
