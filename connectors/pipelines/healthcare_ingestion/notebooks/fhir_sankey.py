# Databricks notebook source
# MAGIC %md
# MAGIC # FHIR R4 Data Flow Sankey Diagrams
# MAGIC 
# MAGIC **Business Question**: How does clinical data flow through our FHIR-enabled health system?
# MAGIC 
# MAGIC This notebook visualizes FHIR R4 resource flows using Sankey diagrams - 
# MAGIC showing how patients move through encounters, receive diagnoses, and have outcomes.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup

# COMMAND ----------

import plotly.graph_objects as go
import pandas as pd
from pyspark.sql import functions as F

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. FHIR Resource Pipeline Flow
# MAGIC 
# MAGIC **What this shows**: How FHIR resources flow from ingestion through processing.
# MAGIC - Left side: Source files
# MAGIC - Middle: Resource types
# MAGIC - Right side: Processing outcome (Valid/Quarantined)

# COMMAND ----------

# Query resource pipeline flow
pipeline_df = spark.sql("""
    SELECT 
        COALESCE(REGEXP_EXTRACT(_source_file, '.*/([^/]+\\.ndjson)$', 1), 'Unknown Source') as source_file,
        resource_type,
        CASE WHEN is_valid THEN 'Valid' ELSE 'Invalid' END as validation_status,
        COUNT(*) as count
    FROM main.healthcare_fhir.bronze_fhir_raw
    WHERE resource_type IS NOT NULL
    GROUP BY 1, 2, 3
    ORDER BY count DESC
""").toPandas()

display(pipeline_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Build Sankey: Source File → Resource Type → Validation Status

# COMMAND ----------

# Create node labels
sources = pipeline_df['source_file'].unique().tolist()
resources = pipeline_df['resource_type'].unique().tolist()
statuses = ['Valid', 'Invalid']
all_nodes = sources + resources + statuses

# Build links for each stage
links_source = []
links_target = []
links_value = []

# Stage 1: Source → Resource Type
stage1 = pipeline_df.groupby(['source_file', 'resource_type'])['count'].sum().reset_index()
for _, row in stage1.iterrows():
    links_source.append(all_nodes.index(row['source_file']))
    links_target.append(all_nodes.index(row['resource_type']))
    links_value.append(row['count'])

# Stage 2: Resource Type → Validation Status
stage2 = pipeline_df.groupby(['resource_type', 'validation_status'])['count'].sum().reset_index()
for _, row in stage2.iterrows():
    links_source.append(all_nodes.index(row['resource_type']))
    links_target.append(all_nodes.index(row['validation_status']))
    links_value.append(row['count'])

# Color palette
source_colors = ['#3498db', '#9b59b6', '#e74c3c', '#f39c12', '#1abc9c', '#34495e'][:len(sources)]
resource_colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6B4C9A', '#44AF69', '#FCAB10', '#2EC4B6'][:len(resources)]
status_colors = ['#27ae60', '#e74c3c']  # Valid=green, Invalid=red

node_colors = source_colors + resource_colors + status_colors

fig_pipeline = go.Figure(data=[go.Sankey(
    arrangement='snap',
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_nodes,
        color=node_colors
    ),
    link=dict(
        source=links_source,
        target=links_target,
        value=links_value,
        color='rgba(100, 100, 100, 0.3)'
    )
)])

fig_pipeline.update_layout(
    title_text="FHIR Pipeline Flow: Source → Resource Type → Validation",
    font_size=12,
    height=600
)

fig_pipeline.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Patient Encounter Flow: Care Setting → Status
# MAGIC 
# MAGIC **What this shows**: How patient encounters flow through different care settings and statuses.
# MAGIC - Left side: Care settings (Ambulatory, Emergency, Inpatient, etc.)
# MAGIC - Right side: Encounter status (Arrived, Triaged, In Progress, Finished)

# COMMAND ----------

# Query encounters for flow
encounters_df = spark.sql("""
    SELECT 
        CASE class_code 
            WHEN 'AMB' THEN 'Ambulatory'
            WHEN 'EMER' THEN 'Emergency'
            WHEN 'IMP' THEN 'Inpatient'
            WHEN 'OBSENC' THEN 'Observation'
            WHEN 'PRENC' THEN 'Pre-Admission'
            WHEN 'SS' THEN 'Short Stay'
            WHEN 'HH' THEN 'Home Health'
            WHEN 'VR' THEN 'Virtual'
            ELSE COALESCE(class_code, 'Unknown')
        END as care_setting,
        INITCAP(status) as encounter_status,
        COUNT(*) as count
    FROM main.healthcare_fhir.silver_fhir_encounter
    WHERE class_code != 'INVALID' AND class_code IS NOT NULL
    GROUP BY 1, 2
    ORDER BY count DESC
""").toPandas()

display(encounters_df)

# COMMAND ----------

# Build Encounter Flow Sankey
care_settings = encounters_df['care_setting'].unique().tolist()
enc_statuses = encounters_df['encounter_status'].unique().tolist()
all_enc_nodes = care_settings + enc_statuses

source_enc = [all_enc_nodes.index(row['care_setting']) for _, row in encounters_df.iterrows()]
target_enc = [all_enc_nodes.index(row['encounter_status']) for _, row in encounters_df.iterrows()]
values_enc = encounters_df['count'].tolist()

# Status colors
status_colors_map = {
    'Arrived': '#3498db',      # Blue
    'Triaged': '#f39c12',      # Orange
    'In-Progress': '#9b59b6',  # Purple
    'Onleave': '#e67e22',      # Dark Orange
    'Finished': '#27ae60',     # Green
    'Cancelled': '#e74c3c',    # Red
    'Planned': '#1abc9c',      # Teal
    'Unknown': '#95a5a6'       # Gray
}

# Link colors based on status
link_colors_enc = []
for _, row in encounters_df.iterrows():
    status = row['encounter_status']
    color = status_colors_map.get(status, '#888888')
    # Convert hex to rgba
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    link_colors_enc.append(f'rgba({r}, {g}, {b}, 0.4)')

fig_encounters = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_enc_nodes,
        color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6B4C9A', '#44AF69', '#FCAB10', '#2EC4B6'][:len(care_settings)] + 
              [status_colors_map.get(s, '#888') for s in enc_statuses]
    ),
    link=dict(
        source=source_enc,
        target=target_enc,
        value=values_enc,
        color=link_colors_enc
    )
)])

fig_encounters.update_layout(
    title_text="Patient Encounter Flow: Care Setting → Status",
    font_size=12,
    height=500
)

fig_encounters.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Diagnosis Flow: Condition Category → Clinical Status
# MAGIC 
# MAGIC **What this shows**: How diagnoses are distributed across clinical statuses.
# MAGIC - Left side: Top diagnosis categories
# MAGIC - Right side: Clinical status (Active, Resolved, Recurrence, etc.)

# COMMAND ----------

# Query conditions for flow
conditions_df = spark.sql("""
    SELECT 
        CASE 
            WHEN code_display LIKE '%Diabetes%' THEN 'Diabetes'
            WHEN code_display LIKE '%Hypertension%' OR code_display LIKE '%Blood Pressure%' THEN 'Hypertension'
            WHEN code_display LIKE '%Heart%' OR code_display LIKE '%Cardiac%' THEN 'Cardiovascular'
            WHEN code_display LIKE '%COPD%' OR code_display LIKE '%Asthma%' OR code_display LIKE '%Respiratory%' THEN 'Respiratory'
            WHEN code_display LIKE '%Fever%' OR code_display LIKE '%Infection%' THEN 'Infectious'
            WHEN code_display LIKE '%Pain%' OR code_display LIKE '%Arthritis%' THEN 'Musculoskeletal'
            WHEN code_display LIKE '%Depression%' OR code_display LIKE '%Anxiety%' THEN 'Mental Health'
            WHEN code_display LIKE '%Cancer%' OR code_display LIKE '%Tumor%' THEN 'Oncology'
            ELSE 'Other'
        END as condition_category,
        INITCAP(clinical_status_code) as clinical_status,
        COUNT(*) as count
    FROM main.healthcare_fhir.silver_fhir_condition
    WHERE clinical_status_code IS NOT NULL
    GROUP BY 1, 2
    ORDER BY count DESC
""").toPandas()

display(conditions_df)

# COMMAND ----------

# Build Condition Flow Sankey
categories = conditions_df['condition_category'].unique().tolist()
clin_statuses = conditions_df['clinical_status'].unique().tolist()
all_cond_nodes = categories + clin_statuses

source_cond = [all_cond_nodes.index(row['condition_category']) for _, row in conditions_df.iterrows()]
target_cond = [all_cond_nodes.index(row['clinical_status']) for _, row in conditions_df.iterrows()]
values_cond = conditions_df['count'].tolist()

# Clinical status colors
clin_status_colors = {
    'Active': '#e74c3c',      # Red - needs attention
    'Resolved': '#27ae60',    # Green - good outcome
    'Recurrence': '#f39c12',  # Orange - watch
    'Remission': '#3498db',   # Blue - improving
    'Inactive': '#95a5a6',    # Gray - dormant
    'Unknown': '#7f8c8d'
}

fig_conditions = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_cond_nodes,
        color=['#6B4C9A', '#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#44AF69', '#FCAB10', '#2EC4B6', '#E71D36'][:len(categories)] + 
              [clin_status_colors.get(s, '#888') for s in clin_statuses]
    ),
    link=dict(
        source=source_cond,
        target=target_cond,
        value=values_cond,
        color='rgba(100, 100, 100, 0.3)'
    )
)])

fig_conditions.update_layout(
    title_text="Diagnosis Flow: Condition Category → Clinical Status",
    font_size=12,
    height=500
)

fig_conditions.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Medication Flow: Drug Class → Prescription Status
# MAGIC 
# MAGIC **What this shows**: How medications flow through the prescription lifecycle.
# MAGIC - Left side: Drug categories
# MAGIC - Right side: Status (Active, Completed, Stopped, Entered-in-Error)

# COMMAND ----------

# Query medications for flow
meds_df = spark.sql("""
    SELECT 
        CASE 
            WHEN medication_display LIKE '%Ibuprofen%' OR medication_display LIKE '%Acetaminophen%' OR medication_display LIKE '%Naproxen%' THEN 'Pain Relief'
            WHEN medication_display LIKE '%Amlodipine%' OR medication_display LIKE '%Lisinopril%' OR medication_display LIKE '%Metoprolol%' THEN 'Cardiovascular'
            WHEN medication_display LIKE '%Metformin%' OR medication_display LIKE '%Insulin%' OR medication_display LIKE '%Glipizide%' THEN 'Diabetes'
            WHEN medication_display LIKE '%Omeprazole%' OR medication_display LIKE '%Pantoprazole%' THEN 'Gastrointestinal'
            WHEN medication_display LIKE '%Amoxicillin%' OR medication_display LIKE '%Azithromycin%' OR medication_display LIKE '%Ciprofloxacin%' THEN 'Antibiotics'
            WHEN medication_display LIKE '%Albuterol%' OR medication_display LIKE '%Fluticasone%' THEN 'Respiratory'
            WHEN medication_display LIKE '%Sertraline%' OR medication_display LIKE '%Escitalopram%' OR medication_display LIKE '%Duloxetine%' THEN 'Mental Health'
            WHEN medication_display LIKE '%Atorvastatin%' OR medication_display LIKE '%Simvastatin%' THEN 'Cholesterol'
            ELSE 'Other'
        END as drug_class,
        INITCAP(status) as rx_status,
        COUNT(*) as count
    FROM main.healthcare_fhir.silver_fhir_medication_request
    WHERE status IS NOT NULL
    GROUP BY 1, 2
    ORDER BY count DESC
""").toPandas()

display(meds_df)

# COMMAND ----------

# Build Medication Flow Sankey
drug_classes = meds_df['drug_class'].unique().tolist()
rx_statuses = meds_df['rx_status'].unique().tolist()
all_med_nodes = drug_classes + rx_statuses

source_med = [all_med_nodes.index(row['drug_class']) for _, row in meds_df.iterrows()]
target_med = [all_med_nodes.index(row['rx_status']) for _, row in meds_df.iterrows()]
values_med = meds_df['count'].tolist()

# Rx status colors
rx_status_colors = {
    'Active': '#27ae60',           # Green - current
    'Completed': '#3498db',        # Blue - done
    'Stopped': '#e74c3c',          # Red - discontinued
    'Cancelled': '#f39c12',        # Orange - never started
    'Entered-In-Error': '#9b59b6', # Purple - data error
    'On-Hold': '#95a5a6',          # Gray - paused
    'Draft': '#bdc3c7',            # Light gray - pending
    'Unknown': '#7f8c8d'
}

# Link colors based on status
link_colors_med = []
for _, row in meds_df.iterrows():
    status = row['rx_status']
    color = rx_status_colors.get(status, '#888888')
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    link_colors_med.append(f'rgba({r}, {g}, {b}, 0.4)')

fig_meds = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_med_nodes,
        color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6B4C9A', '#44AF69', '#FCAB10', '#2EC4B6', '#E71D36'][:len(drug_classes)] + 
              [rx_status_colors.get(s, '#888') for s in rx_statuses]
    ),
    link=dict(
        source=source_med,
        target=target_med,
        value=values_med,
        color=link_colors_med
    )
)])

fig_meds.update_layout(
    title_text="Medication Flow: Drug Class → Prescription Status",
    font_size=12,
    height=500
)

fig_meds.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Multi-Stage Patient Journey: Care Setting → Observation Category → Outcome
# MAGIC 
# MAGIC **What this shows**: Complete patient journey through the FHIR data model.
# MAGIC - Stage 1: Care setting (where patient was seen)
# MAGIC - Stage 2: What was measured (Vitals, Labs, etc.)
# MAGIC - Stage 3: Diagnosis outcome (Active condition or Resolved)

# COMMAND ----------

# Build patient journey by linking encounters → observations → conditions
journey_df = spark.sql("""
    WITH encounter_base AS (
        SELECT 
            id as encounter_id,
            subject_id as patient_id,
            CASE class_code 
                WHEN 'AMB' THEN 'Ambulatory'
                WHEN 'EMER' THEN 'Emergency'
                WHEN 'IMP' THEN 'Inpatient'
                WHEN 'OBSENC' THEN 'Observation'
                ELSE 'Other'
            END as care_setting
        FROM main.healthcare_fhir.silver_fhir_encounter
        WHERE class_code IS NOT NULL AND class_code != 'INVALID'
    ),
    patient_obs AS (
        SELECT DISTINCT
            subject_id as patient_id,
            CASE 
                WHEN category_code = 'vital-signs' THEN 'Vitals Taken'
                WHEN category_code = 'laboratory' THEN 'Labs Ordered'
                ELSE 'Other Assessment'
            END as observation_type
        FROM main.healthcare_fhir.silver_fhir_observation
        WHERE category_code IS NOT NULL
    ),
    patient_conditions AS (
        SELECT DISTINCT
            subject_id as patient_id,
            CASE 
                WHEN clinical_status_code = 'active' THEN 'Active Diagnosis'
                WHEN clinical_status_code = 'resolved' THEN 'Resolved'
                ELSE 'Under Monitoring'
            END as diagnosis_outcome
        FROM main.healthcare_fhir.silver_fhir_condition
    )
    SELECT 
        e.care_setting,
        COALESCE(o.observation_type, 'No Observations') as observation_type,
        COALESCE(c.diagnosis_outcome, 'No Diagnosis') as diagnosis_outcome,
        COUNT(DISTINCT e.patient_id) as patient_count
    FROM encounter_base e
    LEFT JOIN patient_obs o ON e.patient_id = o.patient_id
    LEFT JOIN patient_conditions c ON e.patient_id = c.patient_id
    GROUP BY 1, 2, 3
    HAVING patient_count > 0
    ORDER BY patient_count DESC
""").toPandas()

display(journey_df)

# COMMAND ----------

# Build multi-stage journey Sankey
care_settings_j = journey_df['care_setting'].unique().tolist()
obs_types = journey_df['observation_type'].unique().tolist()
outcomes = journey_df['diagnosis_outcome'].unique().tolist()

all_journey_nodes = care_settings_j + obs_types + outcomes

# Build links for each stage
j_links_source = []
j_links_target = []
j_links_value = []

# Stage 1 → Stage 2: Care Setting → Observation Type
j_stage1 = journey_df.groupby(['care_setting', 'observation_type'])['patient_count'].sum().reset_index()
for _, row in j_stage1.iterrows():
    j_links_source.append(all_journey_nodes.index(row['care_setting']))
    j_links_target.append(all_journey_nodes.index(row['observation_type']))
    j_links_value.append(row['patient_count'])

# Stage 2 → Stage 3: Observation Type → Diagnosis Outcome
j_stage2 = journey_df.groupby(['observation_type', 'diagnosis_outcome'])['patient_count'].sum().reset_index()
for _, row in j_stage2.iterrows():
    j_links_source.append(all_journey_nodes.index(row['observation_type']))
    j_links_target.append(all_journey_nodes.index(row['diagnosis_outcome']))
    j_links_value.append(row['patient_count'])

# Node colors by stage
journey_node_colors = (
    ['#E71D36', '#2E86AB', '#44AF69', '#F18F01', '#6B4C9A'][:len(care_settings_j)] +  # Care settings
    ['#A23B72', '#FCAB10', '#2EC4B6', '#C73E1D'][:len(obs_types)] +  # Observation types
    ['#e74c3c', '#27ae60', '#f39c12', '#3498db'][:len(outcomes)]  # Outcomes
)

fig_journey = go.Figure(data=[go.Sankey(
    arrangement='snap',
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_journey_nodes,
        color=journey_node_colors
    ),
    link=dict(
        source=j_links_source,
        target=j_links_target,
        value=j_links_value,
        color='rgba(100, 100, 100, 0.2)'
    )
)])

fig_journey.update_layout(
    title_text="Complete Patient Journey: Care Setting → Observations → Diagnosis Outcome",
    font_size=12,
    height=600
)

fig_journey.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Observation Flow: Test Type → Category → Status
# MAGIC 
# MAGIC **What this shows**: How clinical observations (vitals and labs) flow through types and statuses.

# COMMAND ----------

# Query observations for multi-stage flow
obs_flow_df = spark.sql("""
    SELECT 
        CASE 
            WHEN code_display LIKE '%Heart%' OR code_display LIKE '%Pulse%' THEN 'Heart Rate'
            WHEN code_display LIKE '%Blood Pressure%' OR code_display LIKE '%Systolic%' OR code_display LIKE '%Diastolic%' THEN 'Blood Pressure'
            WHEN code_display LIKE '%Temperature%' THEN 'Temperature'
            WHEN code_display LIKE '%Respiratory%' OR code_display LIKE '%Breathing%' THEN 'Respiratory Rate'
            WHEN code_display LIKE '%Glucose%' THEN 'Glucose'
            WHEN code_display LIKE '%Cholesterol%' OR code_display LIKE '%LDL%' OR code_display LIKE '%HDL%' THEN 'Cholesterol'
            WHEN code_display LIKE '%Hemoglobin%' OR code_display LIKE '%A1c%' THEN 'Hemoglobin'
            WHEN code_display LIKE '%Creatinine%' THEN 'Kidney Function'
            WHEN code_display LIKE '%BMI%' OR code_display LIKE '%Weight%' OR code_display LIKE '%Height%' THEN 'Body Metrics'
            ELSE 'Other Tests'
        END as test_type,
        CASE category_code
            WHEN 'vital-signs' THEN 'Vital Signs'
            WHEN 'laboratory' THEN 'Laboratory'
            ELSE 'Other'
        END as category,
        INITCAP(status) as obs_status,
        COUNT(*) as count
    FROM main.healthcare_fhir.silver_fhir_observation
    WHERE status IS NOT NULL
    GROUP BY 1, 2, 3
    ORDER BY count DESC
""").toPandas()

display(obs_flow_df)

# COMMAND ----------

# Build Observation multi-stage Sankey
test_types = obs_flow_df['test_type'].unique().tolist()
obs_categories = obs_flow_df['category'].unique().tolist()
obs_statuses_list = obs_flow_df['obs_status'].unique().tolist()

all_obs_nodes = test_types + obs_categories + obs_statuses_list

# Build links
obs_links_source = []
obs_links_target = []
obs_links_value = []

# Stage 1: Test Type → Category
obs_stage1 = obs_flow_df.groupby(['test_type', 'category'])['count'].sum().reset_index()
for _, row in obs_stage1.iterrows():
    obs_links_source.append(all_obs_nodes.index(row['test_type']))
    obs_links_target.append(all_obs_nodes.index(row['category']))
    obs_links_value.append(row['count'])

# Stage 2: Category → Status
obs_stage2 = obs_flow_df.groupby(['category', 'obs_status'])['count'].sum().reset_index()
for _, row in obs_stage2.iterrows():
    obs_links_source.append(all_obs_nodes.index(row['category']))
    obs_links_target.append(all_obs_nodes.index(row['obs_status']))
    obs_links_value.append(row['count'])

# Colors
obs_node_colors = (
    ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6B4C9A', '#44AF69', '#FCAB10', '#2EC4B6', '#E71D36', '#1abc9c'][:len(test_types)] +
    ['#9b59b6', '#3498db', '#95a5a6'][:len(obs_categories)] +
    ['#27ae60', '#e74c3c', '#f39c12', '#7f8c8d'][:len(obs_statuses_list)]
)

fig_obs = go.Figure(data=[go.Sankey(
    arrangement='snap',
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_obs_nodes,
        color=obs_node_colors
    ),
    link=dict(
        source=obs_links_source,
        target=obs_links_target,
        value=obs_links_value,
        color='rgba(100, 100, 100, 0.2)'
    )
)])

fig_obs.update_layout(
    title_text="Observation Flow: Test Type → Category → Status",
    font_size=12,
    height=600
)

fig_obs.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC 
# MAGIC These Sankey diagrams reveal:
# MAGIC 
# MAGIC 1. **Pipeline Flow**: How FHIR resources move from ingestion to validation
# MAGIC 2. **Encounter Patterns**: Where patients receive care and their encounter status
# MAGIC 3. **Diagnosis Distribution**: Which condition categories are active vs resolved
# MAGIC 4. **Medication Lifecycle**: Prescription patterns by drug class and status
# MAGIC 5. **Patient Journey**: Complete flow from care setting through observations to outcomes
# MAGIC 6. **Observation Flow**: How clinical tests distribute across categories
# MAGIC 
# MAGIC ---
# MAGIC 
# MAGIC **Use Cases:**
# MAGIC - **Data Quality**: Monitor pipeline health and validation rates
# MAGIC - **Capacity Planning**: Understand care setting utilization
# MAGIC - **Population Health**: Track disease prevalence and outcomes
# MAGIC - **Pharmacy Management**: Analyze prescription patterns and completion rates
# MAGIC - **Clinical Operations**: Identify bottlenecks in patient flow
# MAGIC - **Quality Metrics**: Compare active vs resolved conditions for quality reporting
