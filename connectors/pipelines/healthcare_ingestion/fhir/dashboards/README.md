# Healthcare FHIR R4 Operations Dashboard

Comprehensive operational dashboard for monitoring FHIR R4 data ingestion, patient demographics, clinical activity, and data quality.

## Dashboard Overview

**Dashboard Name:** Healthcare FHIR R4 Operations
**Dashboard ID:** `01f106a73e2516a7af4629ad65a59a29`
**URL:** https://adb-1516413757355523.3.azuredatabricks.net/sql/dashboardsv3/01f106a73e2516a7af4629ad65a59a29

**Design Pattern:** This dashboard mirrors the Healthcare HL7v2 Operations dashboard design, adapted for FHIR R4 resource types.

## Architecture

### Data Sources

The dashboard queries tables from the `main.healthcare_fhir` schema:

**Bronze Layer:**
- `bronze_fhir_raw` - All FHIR resources (raw ingestion)
- `bronze_fhir_quarantine` - Invalid/failed resources

**Silver Layer:**
- `silver_fhir_patient` - Patient demographics and identifiers
- `silver_fhir_observation` - Lab results, vital signs, clinical measurements
- `silver_fhir_encounter` - Patient visits and care delivery
- `silver_fhir_condition` - Diagnoses and problem lists
- `silver_fhir_medication_request` - Prescription orders
- `silver_fhir_immunization` - Vaccination records

### Dashboard Structure

**8 Pages, 40 Datasets, 60+ Visualizations**

## Page Descriptions

### 1. Executive Summary
**Purpose:** High-level view of healthcare operations at a glance

**KPIs:**
- Total Patients
- Total Encounters
- Total Observations

**Charts:**
- Resource Type Distribution (bar chart)
- Patient Gender Distribution (pie chart)

**Use Cases:**
- Executive reporting
- Quick health check of data volumes
- Population demographics overview

---

### 2. Patient Demographics
**Purpose:** Understanding the patient population

**Visualizations:**
- Patients by Birth Year (bar chart)
- Active vs Inactive Status (pie chart)
- Recent Patient Records (table)

**Use Cases:**
- Population health management
- Demographic analysis
- Patient registry tracking
- Age distribution for targeted programs

**WHY:** Understand patient population age distribution and active status for capacity planning and targeted care programs.

---

### 3. Encounters
**Purpose:** Track patient visits and care delivery patterns

**KPIs:**
- Finished Encounters
- In Progress Encounters

**Charts:**
- Encounter Status Distribution (bar chart)
- Encounter Class Distribution (horizontal bar chart)

**Use Cases:**
- Patient flow monitoring
- Capacity planning
- Operational efficiency tracking
- Care delivery pattern analysis

**WHY:** Monitor patient flow through the healthcare system. Track encounter completion and identify bottlenecks.

---

### 4. Observations
**Purpose:** Monitor clinical measurements, lab results, and vital signs

**KPIs:**
- Final Observations
- Preliminary Observations

**Charts:**
- Top Observation Codes (horizontal bar chart)
- Observation Status Distribution (pie chart)
- Recent Observations (detailed table)

**Use Cases:**
- Lab operations monitoring
- Clinical quality assurance
- Test result tracking
- Critical value identification

**WHY:** Track clinical measurements and lab results. Monitor observation completion rates for quality assurance.

---

### 5. Conditions
**Purpose:** Track diagnoses and chronic condition management

**KPIs:**
- Total Conditions
- Active Conditions

**Charts:**
- Condition Categories (pie chart)
- Top Conditions (horizontal bar chart)

**Use Cases:**
- Disease burden tracking
- Chronic disease management
- Population health interventions
- Quality reporting

**WHY:** Track disease burden and chronic condition prevalence for population health management and care coordination.

---

### 6. Medications & Immunizations
**Purpose:** Monitor medication orders and vaccination coverage

**KPIs:**
- Medication Requests
- Active Medications
- Total Immunizations

**Charts:**
- Top Medications (horizontal bar chart)
- Vaccine Types (bar chart)

**Use Cases:**
- Medication adherence tracking
- Vaccination coverage monitoring
- Pharmacy operations
- Quality reporting

**WHY:** Track medication adherence and vaccination coverage for quality reporting and population health interventions.

---

### 7. Data Quality
**Purpose:** Monitor FHIR ingestion pipeline health

**KPIs:**
- Total Resources
- Valid Resources
- Quarantined Resources

**Charts:**
- Resource Type Counts (horizontal bar chart)
- Validation Quality by Resource Type (table with success rates)

**Use Cases:**
- Pipeline health monitoring
- Data quality assurance
- Integration issue detection
- Source system monitoring

**WHY:** 0 quarantined = healthy pipeline. Monitor resource volumes to detect FHIR source issues early.

---

### 8. Advanced Analytics
**Purpose:** Identify patterns and correlations across FHIR resources

**Visualizations:**
- Encounter Class × Gender (heatmap)
- Resource Type × Status (heatmap)
- Medication Status Distribution (pie chart with color coding)
- Immunization Status Distribution (pie chart with color coding)

**Use Cases:**
- Pattern discovery
- Correlation analysis
- Operational insights
- Quality improvement

**WHY HEATMAPS:** Instantly spot patterns in FHIR data. Dark cells = high volume. White cells = gaps. Use to identify integration issues.

**WHY PIE CHARTS:** See completion at a glance. High red (stopped/not-done) may indicate compliance issues. Monitor for quality improvement.

---

## Comparison to HL7v2 Dashboard

### Design Similarities

| Aspect | HL7v2 Dashboard | FHIR Dashboard |
|--------|----------------|----------------|
| **Structure** | 7 pages | 8 pages |
| **Layout** | Title, subtitle, KPIs, charts, "WHY" sections, tables | Identical |
| **Widget Types** | Counter, bar, pie, heatmap, table | Identical |
| **Color Schemes** | Blue/gold heatmaps, green/red/yellow status colors | Identical |
| **"WHY" Sections** | Explains business value of each page | Identical |

### Content Differences (FHIR vs HL7v2)

| HL7v2 Page | FHIR Equivalent | Key Differences |
|-----------|----------------|-----------------|
| 1. Executive Summary | 1. Executive Summary | FHIR: Resources instead of message types |
| 2. Patient Flow (ADT) | 2. Patient Demographics | FHIR: Demographics focus vs flow focus |
| 3. Lab Operations (ORU) | 4. Observations | FHIR: All observation types, not just labs |
| 4. Clinical Orders (ORM) | 6. Medications | FHIR: Medications instead of generic orders |
| 5. Immunizations (VXU) | 6. Medications & Immunizations | FHIR: Combined with medications |
| 6. Data Quality | 7. Data Quality | FHIR: Resource validation vs message validation |
| 7. Advanced Analytics | 8. Advanced Analytics | FHIR: Resource correlations vs message correlations |
| (none) | 3. Encounters | FHIR-specific: Patient visits |
| (none) | 5. Conditions | FHIR-specific: Diagnoses tracking |

### FHIR-Specific Enhancements

1. **Resource-Centric:** FHIR dashboard focuses on resource types (Patient, Observation, Encounter) rather than message types (ADT, ORU, ORM)

2. **Standardized Terminology:** Uses FHIR standard status codes (final, preliminary, active, completed)

3. **Structured Data:** Leverages FHIR's structured fields (code_display, category_text) instead of parsing message segments

4. **Modern Healthcare:** Reflects contemporary healthcare workflows (encounters, conditions) vs legacy messaging patterns

5. **Data Quality Focus:** Validation success rates by resource type (not just quarantine counts)

---

## Technical Details

### Query Performance

All queries are optimized for Liquid Clustering patterns used in the FHIR pipeline:

```sql
-- Patient table clustered by (id, gender)
-- Observation table clustered by (subject_id, code_code, effective_datetime)
-- Encounter table clustered by (subject_reference, status)
```

### VARIANT Type Usage

Many queries use VARIANT field access for semi-structured FHIR data:

```sql
-- Access nested FHIR resource fields
raw_resource:active::boolean
raw_resource:meta:lastUpdated::timestamp
```

### Dashboard Configuration

- **Warehouse:** `093d4ec27ed4bdee` (test-serverless)
- **Parent Path:** `/Workspace/Shared/`
- **Published:** Yes (embed_credentials: true)

---

## Deployment

### Files

```
fhir/dashboards/
├── build_fhir_dashboard.py              # Generates dashboard JSON
├── healthcare_fhir_r4_operations.lvdash.json  # Dashboard definition
├── deploy_fhir_dashboard.py             # Deploys to Databricks
└── README.md                            # This file
```

### How to Deploy

```bash
cd /Users/bhavin.kukadia/Downloads/000-dev/0-repo/databricks/connectors/pipelines/healthcare_ingestion/fhir/dashboards

# Generate dashboard JSON
python3 build_fhir_dashboard.py

# Deploy to Databricks
python3 deploy_fhir_dashboard.py
```

### Prerequisites

1. Databricks workspace configured in `~/.databrickscfg` with profile `adb-wx1`
2. FHIR pipeline deployed and tables populated in `main.healthcare_fhir` schema
3. Warehouse ID `093d4ec27ed4bdee` accessible
4. Python 3 with `requests` library

---

## Business Value

### Operational Insights

1. **Real-Time Monitoring:** Track patient activity, clinical measurements, and care delivery as data flows in
2. **Quality Assurance:** Identify data quality issues early with validation metrics
3. **Capacity Planning:** Understand encounter patterns and patient volumes
4. **Population Health:** Track conditions, medications, and immunizations for targeted interventions

### Healthcare Use Cases

| Persona | Use Case | Dashboard Pages |
|---------|----------|----------------|
| **CMO** | Executive overview, population health | Executive Summary, Patient Demographics |
| **CNO** | Patient flow, capacity management | Encounters, Advanced Analytics |
| **Lab Manager** | Lab operations, result tracking | Observations, Data Quality |
| **Quality Manager** | Medication safety, immunization coverage | Medications & Immunizations, Conditions |
| **IT/Integration** | Pipeline health, source system monitoring | Data Quality, Advanced Analytics |

### Compliance & Reporting

- **HEDIS/MIPS Quality Measures:** Immunization rates, chronic condition management
- **Meaningful Use:** Medication reconciliation, clinical data exchange
- **Population Health:** Disease burden tracking, preventive care gaps

---

## Maintenance

### Updating Queries

To modify dashboard queries, edit `build_fhir_dashboard.py`:

1. Update dataset `queryLines`
2. Regenerate JSON: `python3 build_fhir_dashboard.py`
3. Redeploy: `python3 deploy_fhir_dashboard.py`

### Adding Pages

Add new page dictionaries to the `pages` array in `build_fhir_dashboard.py`:

```python
{
    "name": "new_page",
    "displayName": "9. New Page Title",
    "layout": [
        # Add widgets here
    ],
    "pageType": "PAGE_TYPE_CANVAS"
}
```

### Modifying Visuals

Widget specifications follow Databricks Lakeview API format:

- **Counter:** KPI metrics
- **Bar/Horizontal Bar:** Categorical comparisons
- **Pie:** Composition/proportions
- **Heatmap:** Two-dimensional patterns
- **Table:** Detailed records

---

## Troubleshooting

### Empty Widgets

**Symptom:** Widget shows "No data"

**Solutions:**
1. Verify tables exist: `SHOW TABLES IN main.healthcare_fhir`
2. Check data: `SELECT * FROM main.healthcare_fhir.silver_fhir_patient LIMIT 10`
3. Run FHIR pipeline to populate tables
4. Verify warehouse has access to schema

### Query Errors

**Symptom:** Widget shows "Error executing query"

**Solutions:**
1. Copy query from dataset `queryLines` in JSON
2. Test query in SQL Editor with warehouse
3. Check field names match table schema: `DESCRIBE TABLE main.healthcare_fhir.silver_fhir_patient`
4. Verify VARIANT field access syntax: `raw_resource:field::type`

### Permission Issues

**Symptom:** "Access denied" or "Table not found"

**Solutions:**
1. Grant warehouse access to `main.healthcare_fhir` schema
2. Check Unity Catalog permissions
3. Verify profile in deployment script matches workspace

---

## Next Steps

### Enhancements to Consider

1. **Filters:** Add global filters for date range, provider, facility
2. **Drill-Through:** Link patient ID to detailed patient view
3. **Alerts:** Set up alerts for data quality thresholds
4. **Scheduling:** Schedule automated dashboard refreshes
5. **Export:** Add export buttons for regulatory reporting

### Additional Dashboards

Consider creating specialized dashboards:

- **Clinical Quality Dashboard:** HEDIS/MIPS measures
- **Referral Tracking Dashboard:** Encounter linkages
- **Medication Safety Dashboard:** Drug interactions, contraindications
- **Cost Analytics Dashboard:** Resource utilization, procedure volumes

---

## References

- FHIR Pipeline Design: `../../DESIGN.md`
- HL7v2 Dashboard: `../../hl7v2/dashboards/healthcare_hl7v2_operations.lvdash.json`
- Databricks Lakeview API: https://docs.databricks.com/api/workspace/lakeview
- FHIR R4 Specification: https://hl7.org/fhir/R4/
