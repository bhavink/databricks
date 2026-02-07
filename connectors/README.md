# Healthcare Data Connectors

Production-grade healthcare data ingestion for Databricks using Spark Declarative Pipelines (SDP).

## Quick Start (5 Minutes)

### Prerequisites

1. **Databricks CLI** configured with your workspace
2. **Unity Catalog** enabled with a catalog (default: `main`)
3. **Workspace access** to create pipelines

### Step 1: Create Unity Catalog Resources

```sql
-- Run in Databricks SQL or notebook
CREATE CATALOG IF NOT EXISTS main;

-- For HL7v2
CREATE SCHEMA IF NOT EXISTS main.healthcare;
CREATE VOLUME IF NOT EXISTS main.healthcare.raw_data;

-- For FHIR
CREATE SCHEMA IF NOT EXISTS main.healthcare_fhir;
CREATE VOLUME IF NOT EXISTS main.healthcare_fhir.raw_data;
```

### Step 2: Upload Sample Data

```bash
# Upload HL7v2 files
databricks fs cp ./sample_hl7v2/ /Volumes/main/healthcare/raw_data/hl7v2/ --recursive

# Upload FHIR NDJSON files
databricks fs cp ./sample_fhir/ /Volumes/main/healthcare_fhir/raw_data/fhir/ --recursive
```

### Step 3: Deploy & Run

```bash
# Option A: Deploy both pipelines together
databricks bundle deploy -t dev
databricks bundle run hl7v2_pipeline -t dev   # Run HL7v2
databricks bundle run fhir_pipeline -t dev    # Run FHIR

# Option B: Deploy pipelines independently
cd pipelines/healthcare_ingestion/hl7v2
databricks bundle deploy -t dev
databricks bundle run hl7v2_pipeline -t dev
```

---

## Project Structure

```
connectors/
├── README.md                    # This file - Quick start guide
├── DESIGN.md                    # Architecture & design decisions
├── databricks.yml               # Combined bundle (both pipelines)
├── requirements.txt             # Python dependencies
│
├── data_generation/             # Test data generators
│   ├── hl7v2_faker.py           # Generate HL7v2 messages
│   └── fhir_faker.py            # Generate FHIR resources
│
└── pipelines/healthcare_ingestion/
    ├── hl7v2/                   # HL7v2 pipeline (standalone)
    │   ├── databricks.yml       # Independent bundle
    │   ├── transformations/
    │   │   └── bronze_hl7v2.py
    │   └── tests/
    │
    ├── fhir/                    # FHIR pipeline (standalone)
    │   ├── databricks.yml       # Independent bundle
    │   ├── bronze_fhir.py
    │   ├── silver_fhir.py
    │   ├── ingestion/           # REST API ingestion (optional)
    │   │   ├── databricks.yml   # Separate ingestion bundle
    │   │   ├── fhir_client.py   # REST client with auth
    │   │   ├── fhir_servers.py  # Server presets (hapi, synthea, etc.)
    │   │   └── tests/           # Ingestion tests
    │   └── tests/
    │
    └── notebooks/               # Analytics notebooks
        ├── hl7v2_sankey.py      # HL7v2 flow visualizations
        ├── fhir_sankey.py       # FHIR flow visualizations
        └── fhir_api_ingestion.py # REST API ingestion notebook
```

---

## Deployment Options

| Approach | Command | Use Case |
|----------|---------|----------|
| **Combined** | `databricks bundle deploy` (from root) | Deploy both pipelines together |
| **HL7v2 Only** | `cd hl7v2 && databricks bundle deploy` | HL7v2-only workloads |
| **FHIR Only** | `cd fhir && databricks bundle deploy` | FHIR-only workloads |

### Environment Targets

| Target | Schema Suffix | Mode | Continuous |
|--------|---------------|------|------------|
| `dev` | `_dev` | Development | No |
| `prod` | `_prod` | Production | Yes (always running) |

---

## FHIR REST API Ingestion (Optional)

Fetch FHIR data directly from REST APIs instead of file drops. This is **separate** from the SDP pipeline.

### Server Presets

Easily switch between public FHIR servers:

| Preset | Server | Best For |
|--------|--------|----------|
| `hapi` | HAPI FHIR Public | Fast testing |
| `synthea` | Synthea (MITRE) | Realistic synthetic data |
| `smart_sandbox` | SMART Health IT | OAuth testing |
| `cerner_sandbox` | Cerner Open | EHR vendor testing |

### Quick Start

```bash
# Deploy ingestion job (separate from pipeline)
cd pipelines/healthcare_ingestion/fhir/ingestion
databricks bundle deploy -t dev

# Run with different servers
databricks bundle run fhir_api_ingestion -t dev --var="server_preset=hapi"
databricks bundle run fhir_api_ingestion -t dev --var="server_preset=synthea"
```

### In Python

```python
from fhir.ingestion import FHIRClient, FHIRIngestion

# One-liner server switch
client = FHIRClient.from_preset("synthea")

# Full ingestion
ingestion = FHIRIngestion.from_preset("hapi", output_volume="/Volumes/...")
result = ingestion.ingest_resources(["Patient", "Observation"])
```

### Interactive Notebook

Open `notebooks/fhir_api_ingestion.py` and use the **dropdown widget** to select server.

> **Note:** The REST API writes NDJSON to UC Volumes. The SDP pipeline then picks up these files automatically via Auto Loader.

---

## Configuration

All configuration is done via `spark.conf` in the bundle YAML. Override defaults:

```bash
# Override catalog
databricks bundle deploy -t dev --var="catalog=my_catalog"

# Override schema
databricks bundle deploy -t dev --var="hl7v2_schema=my_schema"
```

### Key Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `healthcare.storage_path` | UC Volume path for HL7v2 | `/Volumes/main/healthcare/raw_data/hl7v2` |
| `fhir.storage_path` | UC Volume path for FHIR | `/Volumes/main/healthcare_fhir/raw_data/fhir` |
| `*.max_files_per_trigger` | Files per micro-batch | `1000` |
| `*.clustering.enabled` | Enable Liquid Clustering | `true` |

---

## Validation (Dry Run)

**Always dry-run before deploying to production:**

```bash
# Validate bundle configuration
databricks bundle validate

# Validate in specific target
databricks bundle validate -t prod
```

---

## Testing

```bash
# Run all tests
cd pipelines/healthcare_ingestion
python -m pytest -v

# Run HL7v2 tests only
python -m pytest hl7v2/tests/ -v

# Run FHIR tests only
python -m pytest fhir/tests/ -v
```

---

## Tables Created

### HL7v2 Pipeline (11 tables)

| Table | Description |
|-------|-------------|
| `bronze_hl7v2_raw` | All parsed messages |
| `bronze_hl7v2_quarantine` | Failed records |
| `bronze_hl7v2_adt` | Admit/Discharge/Transfer |
| `bronze_hl7v2_orm` | Orders |
| `bronze_hl7v2_oru` | Lab results |
| `bronze_hl7v2_oru_observations` | Flattened lab observations |
| `bronze_hl7v2_siu` | Scheduling |
| `bronze_hl7v2_siu_resources` | Appointment resources |
| `bronze_hl7v2_vxu` | Vaccinations |
| `bronze_hl7v2_vxu_vaccinations` | Flattened vaccinations |

### FHIR Pipeline (8 tables)

| Table | Description |
|-------|-------------|
| `bronze_fhir_raw` | All FHIR resources |
| `bronze_fhir_quarantine` | Failed/invalid resources |
| `silver_fhir_patient` | Patient demographics |
| `silver_fhir_observation` | Vitals and lab results |
| `silver_fhir_encounter` | Clinical encounters |
| `silver_fhir_condition` | Diagnoses |
| `silver_fhir_medication_request` | Prescriptions |
| `silver_fhir_immunization` | Vaccinations |

---

## Troubleshooting

### "Cannot find volume"

```sql
-- Verify volume exists
SHOW VOLUMES IN main.healthcare;

-- Create if missing
CREATE VOLUME IF NOT EXISTS main.healthcare.raw_data;
```

### "Pipeline validation failed"

```bash
# Check bundle syntax
databricks bundle validate

# Check detailed logs
databricks bundle deploy -t dev --debug
```

### "No data in tables"

1. Verify files exist in volume:
   ```sql
   LIST '/Volumes/main/healthcare/raw_data/hl7v2/';
   ```

2. Check quarantine table for parsing errors:
   ```sql
   SELECT * FROM main.healthcare.bronze_hl7v2_quarantine LIMIT 10;
   ```

---

## Next Steps

- **[DESIGN.md](./DESIGN.md)** - Architecture details, UDF patterns, vectorized UDFs
- **[Dashboard Setup](./pipelines/healthcare_ingestion/notebooks/)** - Sankey visualizations
- **[Test Data Generation](./data_generation/)** - Generate sample messages
