# Genie Observability Dashboard

**Version:** 1.0
**Status:** Production
**Last Updated:** February 10, 2026

This document describes the comprehensive Genie Space Analytics dashboard deployed on Databricks AI/BI (Lakeview). The dashboard provides multi-persona observability into Genie usage, performance, quality, and adoption across workspaces.

---

## Overview

The Genie Observability Dashboard is a **tabbed, persona-driven analytics experience** that transforms raw Genie message data into actionable insights for executives, platform engineers, data engineers, and analysts.

**Deployed Dashboard:**
- **URL Pattern:** `https://<workspace-host>/sql/dashboardsv3/<dashboard_id>`
- **Warehouse:** Requires SQL warehouse ID for query execution
- **Data Source:** `main.genie_analytics` schema (message_details, genie_space_details, etc.)

---

## Architecture

### System Overview

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1e1e1'}}}%%
accTitle: Genie Observability Dashboard Architecture
accDescr: High-level architecture showing data flow from Genie API through analytics tables to AI/BI dashboard

flowchart TD
    subgraph External["External Systems"]
        API["Genie REST API"]
        Audit["system.access.audit"]
        QH["system.query.history"]
    end

    subgraph Analytics["main.genie_analytics Schema"]
        MF["genie_messages_to_fetch<br/>(Silver)"]
        MD["message_details<br/>(Gold - Fact Table)"]
        GSD["genie_space_details<br/>(Dimension)"]
        GSM["genie_space_metrics<br/>(Pre-aggregated)"]
        ERR["message_fetch_errors<br/>(Error Tracking)"]
    end

    subgraph Dashboard["AI/BI Dashboard (Lakeview)"]
        Filters["Global Filters<br/>(Workspace)"]
        Exec["Executive Summary"]
        Usage["Usage Analytics"]
        Perf["Performance & Quality"]
        Prompts["Prompts & SQL"]
        Obs["Observability"]
        Adopt["User Adoption"]
        Config["Space Configuration"]
    end

    Audit -->|DLT Pipeline| MF
    API -->|Fetch Messages| MD
    MF -.->|Source| MD
    API -->|Fetch Space Metadata| GSD
    API -.->|Fetch Errors| ERR
    Audit -->|Aggregation| GSM

    MD -->|Star Schema Join| Dashboard
    GSD -->|Human-readable Names| Dashboard
    GSM -->|Metrics| Dashboard
    ERR -->|Error Analysis| Dashboard
    QH -->|User Identity & Performance| Dashboard

    Filters -.->|Applies to All Tabs| Dashboard

    style External fill:#f9f9f9,stroke:#666,stroke-width:2px
    style Analytics fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style Dashboard fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
```

### Data Model

The dashboard uses a **star schema** with `message_details` as the fact table:

| Table | Role | Key Columns |
|-------|------|-------------|
| **message_details** | Fact table - one row per Genie message | `workspace_id`, `space_id`, `conversation_id`, `message_id`, `content`, `query_description`, `query_sql`, `status`, `created_date` |
| **genie_space_details** | Dimension - space metadata | `workspace_id`, `space_id`, `title`, `description`, `serialized_space` |
| **genie_space_metrics** | Pre-aggregated metrics from audit | `workspace_id`, `space_id`, `conversation_count`, `message_count`, `user_count` |
| **message_fetch_errors** | Error tracking | `workspace_id`, `space_id`, `message_id`, `error_type`, `error_message` |
| **genie_messages_to_fetch** | Source messages from audit (with user_email) | `workspace_id`, `message_id`, `user_email` |
| **system.query.history** | SQL execution metrics | `statement_id`, `workspace_id`, `execution_status`, `total_duration_ms` |

**Star Schema Relationships:**

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1e1e1'}}}%%
accTitle: Data Model Star Schema
accDescr: Star schema showing message_details as fact table with dimensional relationships

flowchart LR
    subgraph Dimensions["Dimension Tables"]
        GSD["genie_space_details<br/>────────<br/>workspace_id<br/>space_id<br/>title<br/>serialized_space"]
        QH["system.query.history<br/>────────<br/>statement_id<br/>workspace_id<br/>executed_by<br/>execution_status"]
        MF["genie_messages_to_fetch<br/>────────<br/>workspace_id<br/>message_id<br/>user_email"]
    end

    subgraph Fact["Fact Table (Center)"]
        MD["message_details<br/>════════════<br/>workspace_id<br/>space_id<br/>message_id<br/>statement_id<br/>content<br/>query_description<br/>query_sql<br/>status"]
    end

    subgraph Metrics["Supporting Tables"]
        GSM["genie_space_metrics<br/>────────<br/>workspace_id<br/>space_id<br/>conversation_count"]
        ERR["message_fetch_errors<br/>────────<br/>workspace_id<br/>message_id<br/>error_message"]
    end

    GSD -->|workspace_id<br/>space_id| MD
    QH -->|statement_id<br/>workspace_id| MD
    MF -->|workspace_id<br/>message_id| MD
    GSM -.->|Pre-aggregated<br/>Comparison| MD
    ERR -.->|Error<br/>Analysis| MD

    style MD fill:#ffeb3b,stroke:#f57c00,stroke-width:3px
    style GSD fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style QH fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style MF fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style GSM fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style ERR fill:#ffebee,stroke:#c62828,stroke-width:2px
```

**Join Pattern:**
```sql
FROM main.genie_analytics.message_details md
LEFT JOIN main.genie_analytics.genie_space_details gsd
  ON md.workspace_id = gsd.workspace_id
  AND md.space_id = gsd.space_id
LEFT JOIN system.query.history qh
  ON md.statement_id = qh.statement_id
  AND md.workspace_id = qh.workspace_id
LEFT JOIN main.genie_analytics.genie_messages_to_fetch mf
  ON md.workspace_id = mf.workspace_id
  AND md.message_id = mf.message_id
```

### The Genie Flow: Prompt → Intelligence → SQL → Execution

Understanding what happens between user input and query execution:

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1e1e1'}}}%%
accTitle: Genie Message Processing Flow
accDescr: Sequence diagram showing how user prompts are processed through Genie LLM to SQL execution

sequenceDiagram
    actor User
    participant Genie["Genie Space"]
    participant LLM["Genie LLM"]
    participant Warehouse["SQL Warehouse"]
    participant MD["message_details"]
    participant QH["system.query.history"]

    User->>+Genie: Natural language question
    Note over User,Genie: Stage 1: User Prompt<br/>(content)

    Genie->>+LLM: Question + Space Schema + Context
    LLM->>LLM: Interpret intent
    Note over LLM: Stage 2: Genie Intelligence<br/>(query_description)

    LLM->>LLM: Generate SQL
    Note over LLM: Stage 3: SQL Generation<br/>(query_sql)

    LLM-->>-Genie: SQL Statement + Description
    Genie->>MD: Store message details
    Note over MD: content, query_description,<br/>attachments_json, query_sql

    Genie->>+Warehouse: Execute SQL
    Note over Genie,Warehouse: Stage 4: Execution<br/>(statement_id)

    alt Successful Execution
        Warehouse->>QH: Log execution metrics
        Note over QH: execution_status: SUCCESS<br/>total_duration_ms, read_rows
        Warehouse-->>Genie: Results
        Genie->>MD: Update status = COMPLETED
        Genie-->>-User: Display results
    else Failed Execution
        Warehouse->>QH: Log execution error
        Note over QH: execution_status: FAILED<br/>error_message
        Warehouse-->>Genie: Error
        Genie->>MD: Update status = FAILED
        Genie-->>User: Display error
    end

    Note over MD,QH: Stage 5: Outcome<br/>Join on statement_id + workspace_id
```

**Data Capture by Stage:**

| Stage | What Happens | Captured In | Key Fields |
|-------|--------------|-------------|------------|
| **1. User Prompt** | User asks a question in Genie space | `message_details.content` | User's natural language question |
| **2. Genie Intelligence** | LLM interprets intent and creates description | `message_details.query_description` | What Genie understood about the intent |
| **3. Context** | Attachments and context data | `message_details.attachments_json` | Additional context (charts, tables, etc.) |
| **4. SQL Generation** | LLM generates SQL from question + space schema | `message_details.query_sql` | Generated SQL statement |
| **5. Execution** | SQL runs on warehouse | `message_details.statement_id` → `system.query.history` | Performance metrics, errors |
| **6. Outcome** | Message marked as COMPLETED/FAILED | `message_details.status` | Final status |

**Column Naming Convention:**
- `content` = User Prompt
- `query_description` = **Genie Intelligence** (what the LLM understood)
- `attachments_json` = **Context Data** (avoid ambiguous "attachments" in display names)
- `query_sql` = Generated SQL

---

## Dashboard Structure

### Dashboard Component Overview

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1e1e1'}}}%%
accTitle: Dashboard Tab Structure
accDescr: Component diagram showing 8 dashboard tabs organized by persona and function

flowchart TD
    subgraph Global["Global Controls"]
        F["Filters Page<br/>────────<br/>Workspace Multi-Select"]
    end

    subgraph Executive["Executive View"]
        E["1. Executive Summary<br/>────────<br/>KPIs & Trends<br/>(Leadership)"]
    end

    subgraph Operations["Operational Monitoring"]
        U["2. Usage Analytics<br/>────────<br/>Space Activity<br/>(Platform Engineers)"]
        P["3. Performance & Quality<br/>────────<br/>Error Analysis<br/>(SREs)"]
        O["5. Observability<br/>────────<br/>Message Status<br/>(DevOps)"]
    end

    subgraph Analysis["Deep Analysis"]
        PS["4. Prompts & SQL<br/>────────<br/>Prompt→SQL Flow<br/>(Data Engineers)"]
        A["6. User Adoption<br/>────────<br/>User Metrics<br/>(Product Managers)"]
    end

    subgraph Config["Configuration"]
        C["7. Space Configuration<br/>────────<br/>Space Metadata<br/>(Admins)"]
    end

    F -.->|Applies to All| Executive
    F -.->|Applies to All| Operations
    F -.->|Applies to All| Analysis
    F -.->|Applies to All| Config

    O -->|Page-Level<br/>Time Filter| O

    style F fill:#fff3e0,stroke:#e65100,stroke-width:3px
    style E fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style U fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style P fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style O fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style PS fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style A fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style C fill:#fce4ec,stroke:#c2185b,stroke-width:2px
```

### Global Filter Page

**Purpose:** Apply workspace selection across all tabs

**Widgets:**
- **Workspace Filter** (filter-multi-select) - Select one or more workspaces
  - Data source: `DISTINCT workspace_id` from `message_details`
  - Display format: `<workspace_id> - <workspace_name>`

**Filter Behavior:**
- Global filters affect ALL datasets that contain the `workspace_display` field
- Automatically filters all pages when user selects workspace(s)

### Tab 1: Executive Summary

**Audience:** Leadership, executives, platform owners

**KPIs (3 counters):**
- Total Genie Spaces (90-day window)
- Total Conversations (90-day window)
- Total Messages (90-day window)

**Charts:**
- **Daily Message Volume** (line chart) - 30-day trend
  - X-axis: created_date (temporal)
  - Y-axis: message count (quantitative)
- **Message Status Distribution** (pie chart)
  - Shows COMPLETED vs FAILED vs other statuses
  - Limited to 3-8 categories for readability

**Purpose:** High-level adoption and health at a glance

### Tab 2: Usage Analytics

**Audience:** Platform engineers, workspace admins

**Visualizations:**
- **Space Activity Metrics** (table)
  - Columns: Space Title, Conversations, Messages, Success Rate %
  - Sorted by message volume descending
  - 90-day window

**Purpose:** Identify most active spaces and usage patterns

### Tab 3: Performance & Quality

**Audience:** Platform engineers, SREs

**Visualizations:**
- **Top Errors** (table)
  - Shows error messages and frequency
  - 30-day window
  - Limited to top 20 errors

**Purpose:** Identify systematic issues and error patterns

### Tab 4: Prompts & SQL

**Audience:** Data engineers, analysts, Genie space admins

**Key Feature:** Full context view of the Genie flow

**Columns:**
1. **Space** - Human-readable space title
2. **User Prompt** - What the user asked (`content`)
3. **Genie Intelligence** - What the LLM understood (`query_description`)
4. **Context Data** - Attachments and context (`attachments_json`)
5. **Generated SQL** - SQL produced by LLM (`query_sql`)
6. **Status** - Execution outcome
7. **Created At** - Timestamp

**Purpose:** Understand how prompts are interpreted and translated to SQL

**Use Cases:**
- Debug why a question didn't work as expected
- Learn what prompts generate good SQL
- Identify patterns in successful vs failed queries
- Train users on effective prompting

### Tab 5: Observability

**Audience:** Platform engineers, DevOps

**Key Feature:** Configurable time range filter (page-level, not global)

**Time Range Filter Options:**
- 7 Days
- 30 Days (default)
- 90 Days
- All Time

**Visualizations:**
- **Recent Message Status** (table)
  - Shows last 50 messages with status tracking
  - Columns: Message ID, Space, Status, Prompt Preview, Date
  - Filtered by selected time range

**Purpose:** Real-time monitoring of message processing health

**Filter Implementation:**
- Page-level filter (affects only this tab)
- Single-select dropdown
- Default: 30 days

### Tab 6: User Adoption

**Audience:** Product managers, platform owners

**Visualizations:**
- **Daily Active Users Trend** (line chart)
  - 30-day trend of unique users per day
  - Requires join to `system.query.history` for `executed_by`
- **User Adoption by Space** (table)
  - Unique users, total prompts, prompts per user
  - Identifies power users and engagement patterns
- **Top Users by Activity** (table)
  - Top 20 users by prompt volume
  - Shows spaces used, conversations, prompts, success rate

**Purpose:** Track platform adoption and identify champions

### Tab 7: Space Configuration

**Audience:** Genie space admins, data governance

**Sections:**

1. **Sample Questions**
   - Shows configured sample questions per space
   - Parsed from `serialized_space` JSON

2. **Data Sources (Tables)**
   - Lists tables configured in each space
   - Column count per table

3. **Text Instructions**
   - Custom instructions configured for spaces
   - Guides LLM behavior

4. **Join Specifications**
   - Configured table joins
   - Shows left table, right table, join condition

5. **Benchmarks**
   - Reference questions with expected SQL answers
   - Used for quality validation

**Purpose:** Document and audit space configurations

---

## Implementation Details

### Dataset Architecture

**Principles:**
1. **One dataset per domain** - Don't mix unrelated entities
2. **Pre-aggregated where possible** - Reduce computation in widgets
3. **Fully-qualified table names** - Always use `catalog.schema.table`
4. **Human-readable fields** - Never show raw IDs to users
5. **Consistent naming** - `workspace_display`, `space_title` (not `space_name`)

**Key Datasets:**

```sql
-- ds_workspaces: For global workspace filter
SELECT DISTINCT
  workspace_id,
  CONCAT(workspace_id, ' - ', COALESCE(workspace_name, 'Workspace ' || workspace_id)) AS workspace_display
FROM main.genie_analytics.message_details
WHERE workspace_id IS NOT NULL
ORDER BY workspace_id

-- ds_prompts_enhanced: Full context for Prompts & SQL tab
SELECT
  md.workspace_id,
  CONCAT(md.workspace_id, ' - ', COALESCE(md.workspace_name, 'Workspace ' || md.workspace_id)) AS workspace_display,
  COALESCE(gsd.title, md.space_name, 'Space ' || md.space_id) AS space_title,
  md.conversation_id,
  md.message_id,
  md.content AS user_prompt,
  md.query_description AS genie_intelligence,
  md.attachments_json AS context_data,
  md.query_sql AS generated_sql,
  md.status,
  FROM_UNIXTIME(md.created_timestamp / 1000) AS created_at
FROM main.genie_analytics.message_details md
LEFT JOIN main.genie_analytics.genie_space_details gsd
  ON md.space_id = gsd.space_id
WHERE md.content IS NOT NULL
  AND md.query_sql IS NOT NULL
ORDER BY md.created_timestamp DESC

-- ds_days_filter: Time range options for Observability tab
SELECT * FROM (VALUES
  (7, '7 Days'),
  (30, '30 Days'),
  (90, '90 Days'),
  (999999, 'All Time')
) AS t(days_value, days_label)
```

### Widget Specifications

**Version Requirements (CRITICAL):**
- Counter widgets: `version: 2`
- Table widgets: `version: 2`
- Filter widgets: `version: 2`
- Chart widgets (line, bar, pie): `version: 3`
- Text widgets: NO `spec` block - use `multilineTextboxSpec` directly

**Field Name Matching Rule:**
The `name` in `query.fields` MUST exactly match `fieldName` in `encodings`:

```json
// CORRECT
"fields": [{"name": "sum(spaces)", "expression": "SUM(`total_spaces`)"}]
"encodings": {"value": {"fieldName": "sum(spaces)", ...}}

// WRONG - names don't match
"fields": [{"name": "total_spaces", "expression": "SUM(`total_spaces`)"}]
"encodings": {"value": {"fieldName": "sum(spaces)", ...}}
```

**Layout Grid:**
- 6-column grid system
- Each row must sum to width=6 (no gaps)
- Counter/KPI: width=2, height=3-4
- Charts: width=3, height=5-6
- Tables: width=6, height=5-8
- Text headers: width=6, height=1

**Widget Naming:**
- `widget.name`: alphanumeric + hyphens + underscores ONLY (no spaces)
- `frame.title`: human-readable (any characters)
- `widget.queries[0].name`: always `"main_query"`

### Filter Implementation

**Global Filter (Workspace):**
```json
{
  "name": "filters",
  "pageType": "PAGE_TYPE_GLOBAL_FILTERS",
  "layout": [{
    "widget": {
      "name": "filter-workspace",
      "spec": {
        "version": 2,
        "widgetType": "filter-multi-select",
        "encodings": {
          "fields": [{
            "fieldName": "workspace_display",
            "displayName": "Workspace",
            "queryName": "q_workspaces"
          }]
        },
        "frame": {"showTitle": true, "title": "Workspace"}
      }
    }
  }]
}
```

**Page-Level Filter (Time Range on Observability tab):**
```json
{
  "widget": {
    "name": "filter_days_range",
    "spec": {
      "version": 2,
      "widgetType": "filter-single-select",
      "encodings": {
        "fields": [{
          "fieldName": "days_value",
          "displayName": "Time Range",
          "queryName": "ds_days_filter_query"
        }]
      },
      "frame": {"showTitle": true, "title": "Time Range"}
    }
  },
  "position": {"x": 4, "y": 0, "width": 2, "height": 2}
}
```

---

## Deployment

### Using Databricks MCP Tools

**Prerequisites:**
1. Databricks MCP server configured in Claude Code
2. SQL warehouse ID
3. Dashboard JSON file

**Deployment Command:**
```python
from mcp_databricks import create_or_update_dashboard
import json

# Load dashboard JSON
with open('genie_observability_dashboard_v1.0.json', 'r') as f:
    dashboard_json = f.read()

# Deploy
result = create_or_update_dashboard(
    display_name="Genie Observability Dashboard v1.0",
    parent_path="/Workspace/Shared/genie-analytics",
    serialized_dashboard=dashboard_json,
    warehouse_id="093d4ec27ed4bdee",
    publish=True
)

print(f"Dashboard URL: {result['url']}")
```

**Result:**
```json
{
  "success": true,
  "status": "created",
  "dashboard_id": "01f106b8ab5a103182643cee149a7759",
  "url": "https://<workspace>/sql/dashboardsv3/<id>",
  "published": true
}
```

### Using Databricks CLI

**Alternative deployment method:**
```bash
# Export workspace token
export DATABRICKS_HOST="https://adb-<id>.azuredatabricks.net"
export DATABRICKS_TOKEN="<your-token>"

# Deploy using REST API
curl -X POST "${DATABRICKS_HOST}/api/2.0/lakeview/dashboards" \
  -H "Authorization: Bearer ${DATABRICKS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @dashboard_payload.json
```

### Publishing

**Auto-publish:** Set `publish: true` in deployment call

**Manual publish:**
```python
from mcp_databricks import publish_dashboard

publish_dashboard(dashboard_id="<dashboard_id>")
```

---

## Validation Checklist

Before deploying any dashboard updates:

- [ ] All SQL queries tested via `execute_sql()` MCP tool
- [ ] Widget field names match dataset column names exactly
- [ ] Version numbers correct (counters=2, tables=2, filters=2, charts=3)
- [ ] Layout rows sum to width=6 with no gaps
- [ ] No raw IDs displayed - all human-readable names
- [ ] Filter widgets include `frame: {showTitle: true}`
- [ ] Text widgets use `multilineTextboxSpec` (no `spec` block)
- [ ] Counter widgets use correct aggregation pattern
- [ ] Chart dimensions limited to 3-8 distinct values

---

## Maintenance

### Adding a New Tab

1. **Define persona and questions** - What does this user need to know?
2. **Design datasets** - What tables and joins are needed?
3. **Test SQL queries** - Verify via `execute_sql()` first
4. **Build widgets** - Follow version requirements and naming conventions
5. **Add to pages array** - Set `pageType: "PAGE_TYPE_CANVAS"`
6. **Deploy and test** - Verify filters work correctly

### Modifying Existing Widgets

1. **Read current dashboard JSON** - Use `get_dashboard()` MCP tool
2. **Update relevant sections** - Modify datasets or widget specs
3. **Test queries if changed** - Always validate SQL first
4. **Deploy as update** - Same display_name triggers update vs create
5. **Verify in UI** - Check that changes render correctly

### Troubleshooting

**Widget shows "no selected fields to visualize":**
- Field name mismatch between `query.fields[].name` and `encodings.*.fieldName`
- Fix: Ensure names match exactly (including aggregation syntax like `sum(field)`)

**Widget shows "Invalid widget definition":**
- Wrong version number for widget type
- Missing required properties (e.g., `queryName` in filter encodings)
- Text widget has a `spec` block (should only have `multilineTextboxSpec`)

**Filter not affecting widgets:**
- Global filter: Dataset must include the filter field
- Page-level filter: Widget must be on the same page as filter
- Check field name consistency across datasets

**Dashboard shows empty widgets:**
- SQL query returned no results
- Check time window filters (e.g., `created_date >= date_sub(CURRENT_DATE(), 90)`)
- Verify data exists in source tables

---

## Data Governance

### Data Lineage

```
system.access.audit (Genie actions)
  ↓
main.genie_analytics.genie_messages_to_fetch (silver)
  ↓
Genie API (message fetch)
  ↓
main.genie_analytics.message_details (gold)
  ↓
AI/BI Dashboard (visualization)
```

### Access Control

**Dashboard Access:**
- View: Workspace users with dashboard permissions
- Edit: Dashboard owners and admins
- Manage: Workspace admins

**Data Access:**
- Requires SELECT on `main.genie_analytics.*`
- Requires SELECT on `system.query.history` (for user adoption metrics)
- Queries run as dashboard viewer (not owner)

### Privacy Considerations

**User Identification:**
- User email only in `genie_messages_to_fetch` (from audit)
- `message_details` does NOT store user identity
- Join required for user-level analytics
- Consider anonymization for sensitive workspaces

**Content Sensitivity:**
- `message_details.content` contains user questions (may be sensitive)
- `message_details.query_sql` may reveal data structures
- Apply appropriate catalog/schema permissions
- Consider row-level security if needed

---

## References

### Databricks Documentation

- [AI/BI Dashboards Overview](https://docs.databricks.com/dashboards/)
- [Dashboard API Tutorial](https://learn.microsoft.com/en-us/azure/databricks/dashboards/tutorials/dashboard-crud-api)
- [Visualization Types](https://docs.databricks.com/dashboards/visualizations/types)
- [Genie API Reference](https://docs.databricks.com/genie/api-reference.html)

### Related Documentation

- `genie-aibi-data-model-and-architecture.md` - Data model details
- `genie-messages-persistence-strategy.md` - How messages are captured
- `genie-observability-recommendations.md` - Platform recommendations

### Dashboard Files

- **Production:** `/Workspace/Shared/genie-analytics/Genie Observability Dashboard v1.0.lvdash.json`
- **Repo:** `databricks/ai-governance/audit-logging/genie-aibi/dashboards/genie_observability_dashboard_v1.0.json`
- **Backups:** `databricks/ai-governance/audit-logging/genie-aibi/dashboards/backups/`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-10 | Initial production release with 8 tabs, global workspace filter, configurable time range on Observability tab, and full prompt→SQL flow visibility |

---

## Support

For issues or questions about the dashboard:
1. Check troubleshooting section above
2. Review related data model documentation
3. Test SQL queries independently using `execute_sql()`
4. Verify data freshness in source tables
5. Contact platform team for data pipeline issues
