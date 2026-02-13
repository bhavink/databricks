# Genie Observability – SDP SQL Pipeline

This folder contains the **Spark Declarative Pipeline (SDP)** SQL that builds and populates audit-derived data models for Genie observability. All variable values (workspace IDs, lookback days) are passed via **pipeline configuration**; nothing is hardcoded.

**Data model and architecture:** For a visual overview of how system tables, pipeline MVs, and persisted tables tie together, load modes (initial / incremental / catch-up), and sequence of a Job run, see [docs/genie-aibi-data-model-and-architecture.md](../../docs/genie-aibi-data-model-and-architecture.md).

## SDP best practices (applied)

This pipeline is built and maintained in line with Lakeflow Spark Declarative Pipelines best practices:

| Practice | How it's applied |
|----------|------------------|
| **Parameterization** | All variable values come from pipeline configuration (`genie.workspace_ids`, `genie.days_lookback`, optional `genie.lookback_minutes`). No hardcoded workspace IDs or dates. |
| **Liquid Clustering** | All materialized views use `CLUSTER BY (workspace_id, space_id)` (or equivalent) for layout and query performance. No `PARTITION BY` or Z-ORDER. |
| **Explicit column selection** | Every MV selects explicit columns; no `SELECT *`. Schema is controlled and stable for downstream (e.g. Python ingestion). |
| **Expectations by layer** | **Bronze:** invalid or incomplete rows dropped (`ON VIOLATION DROP ROW`). **Silver:** critical keys enforced with `ON VIOLATION FAIL UPDATE` so the pipeline fails if data is invalid. |
| **Medallion structure** | Bronze → Silver → Gold plus a dedicated **validation** MV (`genie_pipeline_validation`) for tests and monitoring. |
| **SQL syntax** | Constraint list in parentheses immediately after the view name; `COMMENT` and `CLUSTER BY` follow as view clauses (per SDP MATERIALIZED VIEW syntax). |
| **Serverless + Unity Catalog** | Pipeline runs on serverless compute with target catalog/schema (e.g. `main.genie_analytics`). No classic clusters. |
| **Single raw SQL asset** | Pipeline source is a single `.sql` file (not notebooks). |

**Before a full refresh:** run a **dry run** first (`validate_only=True` / "Validate" in the UI) to catch syntax and schema issues without processing data.

## Pipeline configuration

### Compute: Serverless (required)

This pipeline **must** run on **serverless** compute. If you create or update it via API/MCP, the setting can be lost unless you set it explicitly.

- **Via API / MCP:** Always pass **`"serverless": true`** in `extra_settings` when creating or updating the pipeline. Otherwise the pipeline may default to classic (non-serverless) compute. Also always pass **`configuration`** (e.g. `genie.workspace_ids`, `genie.days_lookback`, and optionally `genie.lookback_minutes`) on every update, or the SQL placeholders will be substituted empty and the pipeline may fail.
- **Via UI:** In Pipeline Settings → Compute, ensure the pipeline is set to **"Serverless"**. In Configuration, set `genie.workspace_ids`, `genie.days_lookback`, and optionally `genie.lookback_minutes`.

### Configuration (workspace IDs, lookback)

Set these in the pipeline's **Configuration** (e.g. in the UI under Pipeline Settings → Configuration, or in `extra_settings.configuration` when creating/updating via API).

| Key | Type | Example | Description |
|-----|------|---------|-------------|
| `genie.workspace_ids` | string | `1516413757355523,984752964297111` | Comma-separated workspace IDs to include. |
| `genie.days_lookback` | string | `30` | Days of history (integer as string). Used when **date-based** lookback is active (see `genie.lookback_minutes`). |
| `genie.lookback_minutes` | string | `""` or `"30"` | **Optional.** When empty or `"0"`: filter by **date** (`event_date` and `genie.days_lookback`). When set (e.g. `"30"`): filter by **timestamp** (`event_time >= now - N minutes`) for **continuous capture** (e.g. run every 30 min). |

**Example — date-based (e.g. initial load, 90 days including today):**

```json
{
  "genie.workspace_ids": "1516413757355523,984752964297111",
  "genie.days_lookback": "90",
  "genie.lookback_minutes": ""
}
```

**Example — continuous capture (e.g. every 30 min):**

```json
{
  "genie.workspace_ids": "1516413757355523,984752964297111",
  "genie.days_lookback": "30",
  "genie.lookback_minutes": "30"
}
```

With `genie.lookback_minutes = "30"`, the pipeline only sees audit events from the last 30 minutes. Run the pipeline and the Python ingestion job on the same schedule (e.g. every 30 min). The Python job **skips message_ids already in `message_details`**, so each run only fetches and appends **new** messages (incremental).

**Initial load vs incremental (recommended after first load)**

- **Initial/base load (first run only):** Use **date-based** lookback so the pipeline and Python load the last N days (including today). Set `genie.days_lookback = "90"` (or match `DEFAULT_DAYS_LOOKBACK` in `python/config.py`), `genie.lookback_minutes = ""`. Run the pipeline once, then run the Python ingestion once to fill `message_details` (and any failures go to `message_fetch_errors`).
- **Incremental (use this after the first load):** For scheduled runs, the pipeline **should** run incremental loads only: set **`genie.lookback_minutes`** (e.g. `"30"`) so each run reads only the last N minutes from audit. Run the pipeline and the Python job on the same schedule (e.g. every 30 min). The pipeline then only processes recent audit events; the Python job appends new messages to `message_details` and skips ones already present. No full rescan of history; append-only.
- **Catch-up after a gap:** If the job didn’t run for several days (e.g. 7 days), the next incremental run will only see the last N minutes, so those days are **missing** from `message_details`. To backfill: run **once** with **date-based** lookback (e.g. `genie.days_lookback = "8"`, `genie.lookback_minutes = ""`), run the Job (pipeline + ingestion), then switch back to `genie.lookback_minutes = "30"` for normal incremental runs.

**Example (MCP / create_or_update_pipeline) — always include `serverless: true`:**

```python
extra_settings={
  "serverless": True,
  "configuration": {
    "genie.workspace_ids": "1516413757355523,984752964297111",
    "genie.days_lookback": "30",
    "genie.lookback_minutes": ""   # or "30" for continuous capture every 30 min
  }
}
```

## Datasets (materialized views)

| Dataset | Description |
|---------|-------------|
| **genie_audit_message_events** | Bronze: raw Genie message events from `system.access.audit` (filtered by config). |
| **genie_messages_to_fetch** | Silver: deduplicated list of messages (one per `message_id`). **Source for the Python ingestion job** that calls the Genie API. |
| **genie_space_metrics** | Gold: space-level metrics (conversation count, message count, user count, date range). |
| **genie_pipeline_validation** | Single-row summary: `silver_row_count`, `validation_date`, `configured_days_lookback`, `configured_lookback_minutes`, `effective_start_date`. Use for tests and monitoring. |

Target catalog/schema is set at pipeline level (e.g. `main.genie_analytics`). All names above are unqualified and resolve to that schema.

## Expectations (data quality)

### Bronze: `genie_audit_message_events`

| Name | Rule | Behavior |
|------|------|----------|
| `valid_workspace_id` | `workspace_id IS NOT NULL` | DROP ROW |
| `valid_space_id` | `space_id IS NOT NULL AND length(trim(space_id)) > 0` | DROP ROW |
| `valid_conversation_id` | `conversation_id IS NOT NULL` | DROP ROW |
| `valid_message_id` | `message_id IS NOT NULL` | DROP ROW |
| `success_status` | `status_code = 200` | DROP ROW |
| `valid_event_time` | `event_time IS NOT NULL` | WARN (monitor only) |

### Silver: `genie_messages_to_fetch`

| Name | Rule | Behavior |
|------|------|----------|
| `silver_valid_workspace_id` | `workspace_id IS NOT NULL` | FAIL UPDATE |
| `silver_valid_space_id` | `space_id IS NOT NULL AND length(trim(space_id)) > 0` | FAIL UPDATE |
| `silver_valid_conversation_id` | `conversation_id IS NOT NULL` | FAIL UPDATE |
| `silver_valid_message_id` | `message_id IS NOT NULL` | FAIL UPDATE |
| `silver_valid_event_time` | `event_time IS NOT NULL` | FAIL UPDATE |

Silver uses **FAIL UPDATE** so the pipeline fails if any row violates (ensures downstream Python ingestion only sees valid keys).

## Test cases (backed by expectations and validation view)

1. **Parameter injection**
   - **Test:** Run pipeline with `genie.workspace_ids = "1516413757355523"` and `genie.days_lookback = "30"`.
   - **Assert:** `genie_pipeline_validation` has one row; `configured_days_lookback = 30`; `effective_start_date = current_date - 30`.

2. **Bronze: only success events**
   - **Test:** Query `genie_audit_message_events`; all rows have `status_code = 200` (enforced by `success_status` DROP ROW).

3. **Bronze: required IDs present**
   - **Test:** No row in `genie_audit_message_events` has null `workspace_id`, `space_id`, `conversation_id`, or `message_id` (enforced by expectations).

4. **Silver: deduplication**
   - **Test:** For each `(workspace_id, message_id)` there is exactly one row in `genie_messages_to_fetch` (dedup by `event_time DESC`).

5. **Silver: fail on invalid keys**
   - **Test:** If upstream somehow produced a row with null `message_id`, the pipeline update **fails** (FAIL UPDATE expectations).

6. **Gold: aggregates**
   - **Test:** For each `(workspace_id, space_id)` in `genie_space_metrics`, `message_count` matches the number of rows in `genie_messages_to_fetch` for that workspace/space.

7. **Configurable lookback**
   - **Test:** Set `genie.days_lookback = "7"` and `genie.lookback_minutes = ""`; re-run; `genie_audit_message_events` and `genie_messages_to_fetch` only contain events where `event_date >= current_date - 7`.
   - **Test (continuous):** Set `genie.lookback_minutes = "30"`; re-run; only events with `event_time >= current_timestamp() - 30 minutes` are included.

## How to run

1. **Create/update pipeline** (catalog `main`, schema `genie_analytics`, **serverless**, **SQL-only**):
   - Add **only** this repo's `pipelines/genie_observability/pipeline.sql` to the pipeline's source files (e.g. upload to workspace and point pipeline at it). Do **not** add the Python flow file; the pipeline is SQL-only. Use the Job (Option B) for pipeline + ingestion.
   - Set **Configuration** as above.
   - Set **Target catalog** = `main`, **Target schema** = `genie_analytics`.
   - **Compute:** In the UI, set compute to **Serverless**. Via API/MCP, always pass **`serverless: true`** in `extra_settings` so the pipeline stays on serverless.

2. **Validate before full run (SDP best practice):**
   - Start a **dry run** (Pipeline UI: "Validate" / API: `start_update(..., validate_only=True)`).
   - Confirm the update completes without syntax or schema errors before running a full refresh.

3. **First run (full refresh, 30-day historical):**
   - Set `genie.days_lookback = "30"` (or desired days).
   - Start pipeline update (full refresh if needed).

4. **Full run (pipeline + ingestion):** Use the **Job** with two tasks (see below). Do not rely on the pipeline alone for ingestion.

## Pipeline + Python ingestion: use a Job

The pipeline is **SQL-only**. SDP does not reliably enforce execution order between SQL and Python in the same pipeline, so run ingestion as a **Job task after the pipeline**. Do **not** add the Python flow file to the pipeline.

### Option B: Job with two tasks (use this)

Use **two tasks in one Job** so ingestion always runs **after** the pipeline. Use **serverless** compute for both tasks.

1. **Task 1 – Pipeline:** Run the `genie_observability` pipeline (pipeline task). Refreshes `genie_messages_to_fetch` from audit. Use serverless pipeline compute.
2. **Task 2 – Python:** Run `genie_message_ingestion.py`; **depends on Task 1**. Use serverless job compute (environment with client version e.g. `4`). Reads `genie_messages_to_fetch` and appends to `message_details` (and `message_fetch_errors` for failures).

**Schedule the job** (e.g. every 15–30 min for incremental capture). See `../resources/genie_observability_job.yml` for an example.

**Pipeline (SQL-only). Example (MCP update_pipeline) — always include `serverless: true` and `configuration`:**

```python
create_or_update_pipeline(
    name="genie_observability",
    root_path="/Workspace/Users/<you>/genie-analytics/genie observability",
    catalog="main",
    schema="genie_analytics",
    workspace_file_paths=[
        "/Workspace/Users/<you>/genie-analytics/genie observability/pipelines/genie_observability/pipeline.sql",
    ],
    extra_settings={
        "serverless": True,
        "configuration": {
            "genie.workspace_ids": "1516413757355523,984752964297111",
            "genie.days_lookback": "30",
            "genie.lookback_minutes": ""
        }
    }
)
```

After a Job run, verify ingestion via `message_details` row counts and `ingestion_batch_id` / `ingestion_timestamp` in that table.

### Generating on-demand test data

To create sample Genie audit events (so the pipeline and ingestion have fresh data to process), use **`python/genie_conversation_test_data.py`**. It starts a conversation and asks 1–2 follow-up questions per configured space via the [Genie Conversation API](https://docs.databricks.com/aws/en/genie/conversation-api#-start-a-conversation), respecting throughput limits (5 queries/min) and polling best practices. Run it on Databricks (notebook or job); set **`WORKSPACE_URLS`** in `config.py` if the SOT table has no rows yet. See **`python/README.md`** (section "On-demand test data") for usage.

## Dependencies

- **System tables:** `system.access.audit`, `system.access.workspaces_latest` (read-only).
- **Downstream:** Python ingestion reads `genie_messages_to_fetch` (or the same logic from audit); it does **not** have to be changed if it currently reads from audit SQL, but you can optionally point it at this table for a single source of truth.

## File

- **pipeline.sql** – Single SQL file with all dataset definitions, expectations, and parameter references (`${genie.workspace_ids}`, `${genie.days_lookback}`, optional `${genie.lookback_minutes}`).
