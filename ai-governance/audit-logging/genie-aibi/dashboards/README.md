# Genie Observability Dashboards

This directory contains the **production Genie Observability Dashboard** and deployment utilities.

## Directory Structure

```
dashboards/
├── README.md                                    ← You are here
├── genie_observability_dashboard_v1.0.json     ← Production dashboard JSON (52K)
├── deploy_dashboard.py                         ← Deployment script (MCP-based)
├── backups/                                     ← Timestamped backups
│   ├── genie_dashboard_final_backup.json
│   └── genie_dashboard_final_20260210_143904.json
└── archive_20260210/                           ← Archived old versions
    ├── genie_analytics_dashboard.json
    ├── genie_analytics_dashboard_v2.json
    └── ... (7 old dashboard files)
```

## Purpose of This Directory

### ✅ Production Dashboard Files
**What belongs here:**
- Current production dashboard JSON (`genie_observability_dashboard_v*.json`)
- Deployment script (`deploy_dashboard.py`)
- Timestamped backups (`backups/`)
- Archived old versions (`archive_20260210/`)

### ❌ Not for Development Scripts
**What doesn't belong here:**
- Build scripts (archived in `python/archive_dashboard_scripts_20260210/`)
- Test/development iterations (archived)
- One-off patches and fixes (archived)

## Quick Start

### View Dashboard Info

```python
from deploy_dashboard import get_dashboard_info

info = get_dashboard_info("genie_observability_dashboard_v1.0.json")
print(f"Datasets: {info['datasets']}")
print(f"Pages: {info['pages']}")
print(f"Widgets: {info['total_widgets']}")
```

### Deploy Dashboard (Claude Code with MCP)

```python
# In Claude Code with Databricks MCP server configured
from mcp_databricks import create_or_update_dashboard
from deploy_dashboard import deploy_dashboard

# Load and validate
params = deploy_dashboard(
    dashboard_file="genie_observability_dashboard_v1.0.json",
    warehouse_id="093d4ec27ed4bdee",
    parent_path="/Workspace/Shared/genie-analytics",
    display_name="Genie Observability Dashboard v1.0",
    publish=True
)

# Deploy
result = create_or_update_dashboard(**params)
print(f"Dashboard URL: {result['url']}")
```

### Deploy via Databricks CLI

```bash
# Alternative: Use CLI directly
databricks api post /api/2.0/lakeview/dashboards \
  --json @genie_observability_dashboard_v1.0.json
```

## Files Explained

### `genie_observability_dashboard_v1.0.json`

**Production dashboard** deployed to Databricks AI/BI (Lakeview).

**Contents:**
- 18 datasets (queries against `main.genie_analytics` and `system` tables)
- 8 pages/tabs:
  1. **Filters** (Global) - Workspace multi-select
  2. **Executive Summary** - KPIs and trends
  3. **Usage Analytics** - Space activity
  4. **Performance & Quality** - Error analysis
  5. **Prompts & SQL** - Full prompt→intelligence→SQL flow
  6. **Observability** - Message status with time range filter
  7. **User Adoption** - User metrics and engagement
  8. **Space Configuration** - Space metadata

**Key Features:**
- Global workspace filter (applies to all tabs)
- Page-level time range filter on Observability tab (7, 30, 90 days, All Time)
- "Genie Intelligence" column (query_description field)
- "Context Data" column (attachments_json field)
- Star schema joins: message_details ⟕ genie_space_details ⟕ system.query.history

**Version History:**
- v1.0 (2026-02-10): Initial production release

### `deploy_dashboard.py`

**Deployment utility script** for use with Claude Code + MCP tools.

**Functions:**
- `deploy_dashboard()` - Deploy to Databricks (MCP-based)
- `load_dashboard_json()` - Load and validate JSON
- `validate_dashboard_structure()` - Check JSON integrity
- `list_dashboard_files()` - List available dashboards
- `get_dashboard_info()` - Get metadata (datasets, pages, widgets)

**Design Philosophy:**
- Validation before deployment (catches errors early)
- Works with MCP tools (no manual SDK/API code)
- Clear error messages
- Reusable for future dashboard versions

**Run directly:**
```bash
python deploy_dashboard.py
# Shows available dashboards and usage examples
```

### `backups/`

**Timestamped backups** created before deployments.

**Files:**
- `genie_dashboard_final_backup.json` - Latest backup (generic name)
- `genie_dashboard_final_20260210_143904.json` - Timestamped backup

**When backups are created:**
- Before deploying major changes
- Before column name changes (e.g., "LLM Interpretation" → "Genie Intelligence")
- Before deleting old dashboards
- On request for safety

**Purpose:** Disaster recovery and rollback capability

### `archive_20260210/`

**Archived old dashboard versions** (7 files, ~100K total).

**Contains:**
- Early dashboard iterations (v1, v2, v3, v4)
- Experimental filter implementations
- Obsolete dashboard structures

**Why archived:**
- Superseded by v1.0 production dashboard
- Conflicting approaches and outdated patterns
- Historical record only

**See:** `archive_20260210/README.md` for details

## Deployment Workflow

### Standard Deployment

1. **Edit Dashboard JSON**
   - Modify `genie_observability_dashboard_v1.0.json`
   - Or create new version: `genie_observability_dashboard_v1.1.json`

2. **Test SQL Queries** (CRITICAL)
   ```python
   from mcp_databricks import execute_sql

   # Test each dataset query
   execute_sql("SELECT ... FROM main.genie_analytics.message_details ...")
   ```

3. **Validate Structure**
   ```python
   from deploy_dashboard import validate_dashboard_structure

   with open('genie_observability_dashboard_v1.0.json') as f:
       validate_dashboard_structure(f.read())
   ```

4. **Create Backup**
   ```bash
   cp genie_observability_dashboard_v1.0.json \
      backups/genie_dashboard_$(date +%Y%m%d_%H%M%S).json
   ```

5. **Deploy**
   ```python
   # Use deploy_dashboard.py + MCP as shown above
   ```

6. **Verify in UI**
   - Open dashboard URL
   - Test filters
   - Check all widgets render
   - Verify data accuracy

### Rollback Procedure

If deployment fails or dashboard is broken:

1. **Find backup:**
   ```bash
   ls -lt backups/
   ```

2. **Restore from backup:**
   ```bash
   cp backups/genie_dashboard_20260210_143904.json \
      genie_observability_dashboard_v1.0.json
   ```

3. **Redeploy:**
   ```python
   # Deploy the restored version
   ```

## Integration with Other Directories

```
genie-aibi/
├── dashboards/              ← YOU ARE HERE
│   └── deploy_dashboard.py  (Uses MCP tools)
├── docs/
│   └── genie-observability-dashboard.md  (Full documentation)
├── python/
│   ├── genie_message_ingestion.py  (Populates data)
│   └── archive_dashboard_scripts_20260210/  (Old build scripts)
└── notebooks/
    └── genie_observability_demo.ipynb  (SQL examples)
```

**Data Flow:**
```
SDP Pipeline (audit → genie_messages_to_fetch)
    ↓
Python Scripts (API fetch → message_details)
    ↓
Dashboard JSON (queries → visualizations)
    ↓
Databricks AI/BI (rendered dashboard)
```

## Best Practices

### ✅ DO

- **Version dashboard files:** `v1.0`, `v1.1`, `v2.0`
- **Test SQL first:** Use `execute_sql()` before deployment
- **Backup before changes:** Create timestamped backup
- **Validate structure:** Use `validate_dashboard_structure()`
- **Document changes:** Update version history in JSON comments or docs
- **Use MCP tools:** Simpler than manual SDK/API calls

### ❌ DON'T

- **Don't skip SQL testing:** Broken queries = broken widgets
- **Don't deploy without backup:** Always have rollback option
- **Don't store dev scripts here:** Keep development iterations in archive
- **Don't hardcode credentials:** Use MCP authentication
- **Don't bypass validation:** Catch errors before deployment

## Common Issues

### Widget shows "no selected fields to visualize"

**Cause:** Field name mismatch between `query.fields[].name` and `encodings.*.fieldName`

**Fix:** Ensure exact match:
```json
// CORRECT
"fields": [{"name": "sum(spaces)", "expression": "SUM(`total_spaces`)"}]
"encodings": {"value": {"fieldName": "sum(spaces)", ...}}
```

### Widget shows "Invalid widget definition"

**Cause:** Wrong version number for widget type

**Fix:** Check version requirements:
- Counter: `version: 2`
- Table: `version: 2`
- Filters: `version: 2`
- Charts (line/bar/pie): `version: 3`

### Filter not working

**Cause:** Dataset doesn't include filter field

**Fix:** Add filter dimension to dataset query:
```sql
SELECT
  workspace_id,
  CONCAT(workspace_id, ' - ', workspace_name) AS workspace_display,  -- For filter
  ...
```

### Dashboard shows empty

**Cause:** No data in source tables or time window too narrow

**Fix:**
1. Check data exists: `SELECT COUNT(*) FROM main.genie_analytics.message_details`
2. Widen time window: Change `date_sub(CURRENT_DATE(), 7)` to `date_sub(CURRENT_DATE(), 90)`

## Documentation

**Full Documentation:** `../docs/genie-observability-dashboard.md`

**Includes:**
- Architecture diagrams (Mermaid)
- Data model (star schema)
- All tabs explained
- SQL patterns
- Troubleshooting guide
- Maintenance procedures

**Quick Links:**
- Data Model: `../docs/genie-aibi-data-model-and-architecture.md`
- Pipeline Code: `../python/genie_message_ingestion.py`
- SQL Examples: `../notebooks/genie_observability_demo.ipynb`

## Support

**For dashboard issues:**
1. Check this README
2. Review `docs/genie-observability-dashboard.md`
3. Test SQL queries independently
4. Verify data in source tables
5. Check Databricks SQL warehouse logs

**For data pipeline issues:**
See `../python/README.md`

---

**Last Updated:** February 10, 2026
**Dashboard Version:** 1.0
**Deployment Method:** Databricks MCP Tools in Claude Code
