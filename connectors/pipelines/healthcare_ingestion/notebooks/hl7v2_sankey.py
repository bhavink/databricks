# Databricks notebook source
# MAGIC %md
# MAGIC # Patient Flow Sankey Diagram
# MAGIC 
# MAGIC **Business Question**: How do patients flow through our hospital?
# MAGIC 
# MAGIC This notebook visualizes patient movement patterns using Sankey diagrams - 
# MAGIC showing the volume of patients moving between different hospital units and stages.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup

# COMMAND ----------

import plotly.graph_objects as go
import pandas as pd
from pyspark.sql import functions as F

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Patient Flow: ADT Event Transitions
# MAGIC 
# MAGIC **What this shows**: How patients move through the admission-transfer-discharge cycle.
# MAGIC - Left side: Entry points (Admissions, Registrations)
# MAGIC - Middle: Hospital units (ER, ICU, MedSurg, etc.)
# MAGIC - Right side: Exit points (Discharges, Transfers out)

# COMMAND ----------

# Query ADT events to build flow data
adt_df = spark.sql("""
    SELECT 
        event_type_code,
        CASE event_type_code 
            WHEN 'A01' THEN 'Admission'
            WHEN 'A02' THEN 'Transfer'
            WHEN 'A03' THEN 'Discharge'
            WHEN 'A04' THEN 'Registration'
            WHEN 'A08' THEN 'Update'
            ELSE event_type_code 
        END as event_name,
        COALESCE(location_unit, 'Unknown') as unit,
        patient_id
    FROM main.healthcare.bronze_hl7v2_adt
    WHERE location_unit IS NOT NULL AND location_unit != ''
""")

# Aggregate for Sankey: Event Type -> Unit
flow_data = adt_df.groupBy("event_name", "unit").count().toPandas()
display(flow_data)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Build Sankey Diagram: Event Type → Hospital Unit

# COMMAND ----------

# Create node labels (unique events + units)
events = flow_data['event_name'].unique().tolist()
units = flow_data['unit'].unique().tolist()
all_nodes = events + units

# Create source/target indices
source_indices = [all_nodes.index(row['event_name']) for _, row in flow_data.iterrows()]
target_indices = [all_nodes.index(row['unit']) for _, row in flow_data.iterrows()]
values = flow_data['count'].tolist()

# Color palette
event_colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6B4C9A']
unit_colors = ['#44AF69', '#FCAB10', '#2EC4B6', '#E71D36', '#FF9F1C', '#011627', '#41B3A3']

node_colors = event_colors[:len(events)] + unit_colors[:len(units)]

# Create Sankey
fig = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_nodes,
        color=node_colors
    ),
    link=dict(
        source=source_indices,
        target=target_indices,
        value=values,
        color='rgba(100, 100, 100, 0.3)'
    )
)])

fig.update_layout(
    title_text="Patient Flow: ADT Event Type → Hospital Unit",
    font_size=12,
    height=500
)

fig.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Lab Results Flow: Test Type → Result Status
# MAGIC 
# MAGIC **What this shows**: How lab tests flow from ordered to resulted, with normal vs abnormal outcomes.

# COMMAND ----------

# Query lab results for flow
labs_df = spark.sql("""
    SELECT 
        COALESCE(observation_text, 'Unknown Test') as test_type,
        CASE 
            WHEN abnormal_flags IN ('H', 'HH') THEN 'High'
            WHEN abnormal_flags IN ('L', 'LL') THEN 'Low'
            WHEN abnormal_flags = 'N' OR abnormal_flags IS NULL THEN 'Normal'
            ELSE 'Other'
        END as result_status,
        COUNT(*) as count
    FROM main.healthcare.bronze_hl7v2_oru_observations
    GROUP BY 1, 2
    ORDER BY count DESC
    LIMIT 50
""").toPandas()

display(labs_df)

# COMMAND ----------

# Build Lab Results Sankey
tests = labs_df['test_type'].unique().tolist()
statuses = ['Normal', 'High', 'Low', 'Other']
all_lab_nodes = tests + statuses

source_lab = [all_lab_nodes.index(row['test_type']) for _, row in labs_df.iterrows()]
target_lab = [all_lab_nodes.index(row['result_status']) for _, row in labs_df.iterrows()]
values_lab = labs_df['count'].tolist()

# Status colors
status_colors = {
    'Normal': '#44AF69',   # Green
    'High': '#E71D36',     # Red
    'Low': '#FCAB10',      # Orange
    'Other': '#6B4C9A'     # Purple
}

# Link colors based on target status
link_colors = [
    f"rgba{tuple(list(int(status_colors[labs_df.iloc[i]['result_status']].lstrip('#')[j:j+2], 16) for j in (0, 2, 4)) + [0.4])}"
    for i in range(len(labs_df))
]

fig_labs = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_lab_nodes,
        color=['#2E86AB'] * len(tests) + [status_colors.get(s, '#888') for s in statuses]
    ),
    link=dict(
        source=source_lab,
        target=target_lab,
        value=values_lab,
        color=link_colors
    )
)])

fig_labs.update_layout(
    title_text="Lab Results Flow: Test Type → Result Status",
    font_size=12,
    height=600
)

fig_labs.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Order Lifecycle Flow: Order Type → Status
# MAGIC 
# MAGIC **What this shows**: How clinical orders move through their lifecycle stages.

# COMMAND ----------

# Query orders for flow
orders_df = spark.sql("""
    SELECT 
        COALESCE(service_text, 'Unknown Order') as order_type,
        CASE order_control
            WHEN 'NW' THEN 'New'
            WHEN 'XO' THEN 'Changed'
            WHEN 'CA' THEN 'Cancelled'
            WHEN 'SC' THEN 'Status Changed'
            ELSE COALESCE(order_control, 'Unknown')
        END as order_status,
        COUNT(*) as count
    FROM main.healthcare.bronze_hl7v2_orm
    GROUP BY 1, 2
    ORDER BY count DESC
    LIMIT 30
""").toPandas()

display(orders_df)

# COMMAND ----------

# Build Orders Sankey
order_types = orders_df['order_type'].unique().tolist()
order_statuses = orders_df['order_status'].unique().tolist()
all_order_nodes = order_types + order_statuses

source_ord = [all_order_nodes.index(row['order_type']) for _, row in orders_df.iterrows()]
target_ord = [all_order_nodes.index(row['order_status']) for _, row in orders_df.iterrows()]
values_ord = orders_df['count'].tolist()

# Status colors for orders
order_status_colors = {
    'New': '#44AF69',
    'Changed': '#FCAB10',
    'Cancelled': '#E71D36',
    'Status Changed': '#2E86AB',
    'Unknown': '#888888'
}

fig_orders = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_order_nodes,
        color=['#6B4C9A'] * len(order_types) + [order_status_colors.get(s, '#888') for s in order_statuses]
    ),
    link=dict(
        source=source_ord,
        target=target_ord,
        value=values_ord,
        color='rgba(100, 100, 100, 0.3)'
    )
)])

fig_orders.update_layout(
    title_text="Clinical Orders Flow: Order Type → Status",
    font_size=12,
    height=500
)

fig_orders.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Multi-Stage Sankey: Full Patient Journey
# MAGIC 
# MAGIC **What this shows**: Complete patient journey from admission through labs and discharge.
# MAGIC - Stage 1: Entry (Admission type)
# MAGIC - Stage 2: Unit assignment
# MAGIC - Stage 3: Lab activity
# MAGIC - Stage 4: Outcome (Discharge/Transfer)

# COMMAND ----------

# Build a more complex multi-stage flow
# This simulates a patient journey through stages

journey_data = spark.sql("""
    WITH admissions AS (
        SELECT patient_id, 'Entry' as stage1, 
               CASE WHEN event_type_code = 'A01' THEN 'Emergency' ELSE 'Scheduled' END as entry_type,
               location_unit as unit
        FROM main.healthcare.bronze_hl7v2_adt
        WHERE event_type_code IN ('A01', 'A04')
    ),
    lab_activity AS (
        SELECT patient_id, 
               CASE WHEN COUNT(*) > 5 THEN 'High Lab Activity' 
                    WHEN COUNT(*) > 0 THEN 'Low Lab Activity'
                    ELSE 'No Labs' END as lab_activity
        FROM main.healthcare.bronze_hl7v2_oru_observations
        GROUP BY patient_id
    ),
    discharges AS (
        SELECT patient_id, 'Discharged' as outcome
        FROM main.healthcare.bronze_hl7v2_adt
        WHERE event_type_code = 'A03'
    )
    SELECT 
        a.entry_type,
        COALESCE(a.unit, 'Unknown') as unit,
        COALESCE(l.lab_activity, 'No Labs') as lab_activity,
        COALESCE(d.outcome, 'In Hospital') as outcome,
        COUNT(DISTINCT a.patient_id) as patient_count
    FROM admissions a
    LEFT JOIN lab_activity l ON a.patient_id = l.patient_id
    LEFT JOIN discharges d ON a.patient_id = d.patient_id
    GROUP BY 1, 2, 3, 4
    HAVING patient_count > 0
""").toPandas()

display(journey_data)

# COMMAND ----------

# Build multi-stage Sankey
# Nodes: Entry types, Units, Lab activity, Outcomes
entry_types = journey_data['entry_type'].unique().tolist()
units = journey_data['unit'].unique().tolist()
lab_activities = journey_data['lab_activity'].unique().tolist()
outcomes = journey_data['outcome'].unique().tolist()

all_journey_nodes = entry_types + units + lab_activities + outcomes
node_count = len(all_journey_nodes)

# Build links for each stage transition
links_source = []
links_target = []
links_value = []

# Stage 1 → Stage 2: Entry → Unit
stage1_2 = journey_data.groupby(['entry_type', 'unit'])['patient_count'].sum().reset_index()
for _, row in stage1_2.iterrows():
    links_source.append(all_journey_nodes.index(row['entry_type']))
    links_target.append(all_journey_nodes.index(row['unit']))
    links_value.append(row['patient_count'])

# Stage 2 → Stage 3: Unit → Lab Activity
stage2_3 = journey_data.groupby(['unit', 'lab_activity'])['patient_count'].sum().reset_index()
for _, row in stage2_3.iterrows():
    links_source.append(all_journey_nodes.index(row['unit']))
    links_target.append(all_journey_nodes.index(row['lab_activity']))
    links_value.append(row['patient_count'])

# Stage 3 → Stage 4: Lab Activity → Outcome
stage3_4 = journey_data.groupby(['lab_activity', 'outcome'])['patient_count'].sum().reset_index()
for _, row in stage3_4.iterrows():
    links_source.append(all_journey_nodes.index(row['lab_activity']))
    links_target.append(all_journey_nodes.index(row['outcome']))
    links_value.append(row['patient_count'])

# Node colors by stage
node_colors = (
    ['#E71D36', '#2E86AB'][:len(entry_types)] +  # Entry: red/blue
    ['#44AF69', '#FCAB10', '#6B4C9A', '#2EC4B6', '#FF9F1C', '#011627'][:len(units)] +  # Units: greens/oranges
    ['#A23B72', '#F18F01', '#C73E1D'][:len(lab_activities)] +  # Lab activity: purples
    ['#44AF69', '#888888'][:len(outcomes)]  # Outcomes: green/gray
)

fig_journey = go.Figure(data=[go.Sankey(
    arrangement='snap',
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=all_journey_nodes,
        color=node_colors
    ),
    link=dict(
        source=links_source,
        target=links_target,
        value=links_value,
        color='rgba(100, 100, 100, 0.2)'
    )
)])

fig_journey.update_layout(
    title_text="Complete Patient Journey: Entry → Unit → Labs → Outcome",
    font_size=12,
    height=600
)

fig_journey.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC 
# MAGIC These Sankey diagrams reveal:
# MAGIC 
# MAGIC 1. **Patient Flow**: Which units receive the most admissions? Where do transfers go?
# MAGIC 2. **Lab Patterns**: Which tests have the highest abnormal rates?
# MAGIC 3. **Order Lifecycle**: What percentage of orders get cancelled vs completed?
# MAGIC 4. **Full Journey**: How do patients move through the entire care continuum?
# MAGIC 
# MAGIC ---
# MAGIC 
# MAGIC **Use Cases:**
# MAGIC - **Capacity Planning**: Identify bottleneck units
# MAGIC - **Quality Improvement**: Track abnormal lab patterns
# MAGIC - **Operational Efficiency**: Monitor order cancellation rates
# MAGIC - **Patient Experience**: Understand the typical care journey
