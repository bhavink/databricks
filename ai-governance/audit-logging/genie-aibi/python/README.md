# Genie Observability – Python (ingestion; uses secrets)

This folder contains **Python only** for **message extraction**. It uses **Databricks secrets** (scope `genie-obs`, keys `sp_client_id`, `sp_client_secret`) for OAuth to the Genie API. No secrets are needed for the SQL dashboard.

**Data model and architecture:** See [docs/genie-aibi-data-model-and-architecture.md](../docs/genie-aibi-data-model-and-architecture.md) for how ingestion fits in (sequence diagram, tables, load modes).

## Files

### Core Pipeline Scripts

| File | Purpose |
|------|--------|
| **config.py** | Scope name (`SECRETS_SCOPE`), table names, **`WORKSPACE_IDS`** (required), optional **`SPACE_IDS_BY_WORKSPACE`** (per-workspace space filter), `EXTRACTION_MESSAGE_LIMIT`. No secret values. |
| **genie_oauth.py** | OAuth helpers; **secrets only** – reads credentials via `dbutils.secrets.get(scope, key)`. Requires `dbutils` and `scope`; no env fallback. |
| **genie_message_ingestion.py** | Reads message list from **SOT table** `main.genie_analytics.genie_messages_to_fetch` (populated by SDP pipeline), calls Genie API per message. **Success** → `message_details` (append); **errored/dropped** → `message_fetch_errors`. Incremental: skips (workspace_id, message_id) already in `message_details` (no duplicates). |
| **genie_space_details.py** | **Space config job (net-new):** calls GET `/api/2.0/genie/spaces/{space_id}?include_serialized_space=true` for each distinct space in `genie_messages_to_fetch`. Merges into `genie_space_details` (title, description, serialized_space). Use `serialized_space` with Create/Update Genie Space API to promote spaces or create backups. Run as a **separate job** (e.g. daily); see `../resources/genie_space_details_job.yml`. |

### Demo/Test Utilities

| File | Purpose |
|------|--------|
| **demo_generate_test_conversations.py** | **On-demand test data:** starts a Genie conversation and asks 1–2 follow-ups per configured space via the [Genie Conversation API](https://docs.databricks.com/aws/en/genie/conversation-api#-start-a-conversation). Respects throughput (5 queries/min) and polling best practices. Run on Databricks to generate audit events that flow into the pipeline and `message_details`. See [setup guide](../docs/setup-test-data-generation.md) for usage. |

## Prerequisites

- **Secrets:** Create scope `genie-obs` and keys `sp_client_id`, `sp_client_secret` (see `../setup/create_secrets.py`).
- **SOT table:** Run the **SDP pipeline** (see `../pipelines/genie_observability/`) so `main.genie_analytics.genie_messages_to_fetch` is populated.
- **Config:** Set **`WORKSPACE_IDS`** (required). Optionally set **`SPACE_IDS_BY_WORKSPACE`** (dict: `workspace_id` → list of `space_id`). If not set (`None`), messages from **all spaces** in each workspace are extracted; a workspace can have 100s of spaces, so you can restrict to one or more space_ids per workspace. Use `[]` for a workspace in the dict to mean “all spaces” for that workspace. Get space_ids from the SOT table (`genie_messages_to_fetch`) or from the Genie UI.
- **Run on Databricks:** Script expects `spark` and `dbutils` (notebook or job).

## Running ingestion

**From a Databricks notebook:**

```python
# Add python/ to path if needed
import sys
sys.path.insert(0, "/Workspace/path/to/genie-aibi/python")
from genie_message_ingestion import run_ingestion, get_dbutils

# Required: workspace_ids. Optional: space_ids_by_workspace (dict: workspace_id -> [space_id, ...])
# None = all spaces per workspace; or e.g. one space per workspace:
run_ingestion(
    workspace_ids=["1516413757355523", "984752964297111"],
    space_ids_by_workspace=None,  # or {"1516413757355523": ["space_id_1"], "984752964297111": ["space_id_2"]}
    dbutils=get_dbutils(),
)
```

**As a Databricks job:** Point the job at `genie_message_ingestion.py`; set working directory so `config` and `genie_oauth` are importable. Set **`WORKSPACE_IDS`** in `config.py` (required). Optionally pass `workspace_ids` and/or `space_ids_by_workspace` as job parameters if you inject them in code.

## Run order (pipeline and Python)

1. **SDP pipeline** runs first → populates `genie_messages_to_fetch` (and other MVs). Required before any Python ingestion.
2. **genie_message_ingestion.py** → reads from `genie_messages_to_fetch`, fetches each message via API, appends to `message_details` and `message_fetch_errors`. Skips messages already in `message_details`.
3. **genie_space_details.py** → reads **distinct (workspace_id, space_id)** from `genie_messages_to_fetch` (same SOT), fetches GET space per space, **merges** into `genie_space_details`. Current purpose: **space_id → title** for dashboards; later: promotion management.

Space details does **not** depend on message ingestion—only on the pipeline. You can run: **SDP → message_ingestion → space_details**, or **SDP → space_details** on its own schedule (e.g. daily). For matching (workspace_id, space_id) the merge **updates** that row; new spaces are **inserted**. No full-table overwrite.

## Space details job (genie_space_details.py)

A **separate job** fetches full space configuration (including **serialized_space**) for dashboards (title) and, later, promote-across-workspaces. It reads distinct (workspace_id, space_id) from `genie_messages_to_fetch` (same WORKSPACE_IDS / SPACE_IDS_BY_WORKSPACE), calls GET `/api/2.0/genie/spaces/{space_id}?include_serialized_space=true`, and **merges** into `main.genie_analytics.genie_space_details`. Use the stored `serialized_space` with the [Create Genie Space](https://docs.databricks.com/api/workspace/genie/createspace) and [Update Genie Space](https://docs.databricks.com/api/workspace/genie/updatespace) APIs for promotion (later). Run on a schedule (e.g. daily) or after the pipeline. Job definition: **`../resources/genie_space_details_job.yml`**.

```python
from genie_message_ingestion import get_dbutils
from genie_space_details import run_space_details_ingestion
run_space_details_ingestion(dbutils=get_dbutils())
```

## Schema and table

- **Schema:** `main.genie_analytics` (see `TARGET_SCHEMA` in config). To reset before running ingestion, run **`scripts/cleanup_genie_analytics_schema.sql`** in Databricks (drops and recreates the schema).
- **Output tables:** Message ingestion: successful fetches → `main.genie_analytics.message_details` (append); failed → `message_fetch_errors` (append). Space details job: → `main.genie_analytics.genie_space_details` (merge by workspace_id, space_id). For full DDL see `sql/genie_observability_schema.sql` and `docs/genie-messages-persistence-strategy.md`.
- **Initial vs incremental:** For **initial load**, run the SDP pipeline with `genie.days_lookback = "90"` (or `DEFAULT_DAYS_LOOKBACK` in config), `genie.lookback_minutes = ""`, then run ingestion once. For **incremental**, run pipeline + ingestion on a schedule (e.g. every 15 min to once per day) with `genie.lookback_minutes` set (e.g. `"30"`); only new messages are fetched (no duplicates).

## On-demand test data (Genie Conversation API)

To generate sample audit messages for the configured spaces (e.g. for testing the pipeline and ingestion), run **`genie_conversation_test_data.py`** on Databricks. It will:

1. **Start a conversation** per space (`POST .../start-conversation`) with a sample question.
2. **Poll** the message until `COMPLETED` / `FAILED` / `CANCELLED` (exponential backoff, 10 min timeout).
3. **Send 1–2 follow-up questions** (`POST .../conversations/{id}/messages`) and poll each.
4. **Respect** the Genie API throughput limit (5 queries per minute per workspace) by waiting 15 s between POSTs.

**Config:** Same as ingestion (`WORKSPACE_IDS`, `SPACE_IDS_BY_WORKSPACE`, `SECRETS_SCOPE`). In addition, set **`WORKSPACE_URLS`** in `config.py` (dict: `workspace_id` → base URL, no trailing slash). If `WORKSPACE_URLS` is `None`, the script tries to read workspace URLs from `main.genie_analytics.genie_messages_to_fetch` (so run the pipeline at least once, or set `WORKSPACE_URLS` manually).

**Run from a notebook:**

```python
import sys
sys.path.insert(0, "/Workspace/path/to/genie-aibi/python")
from genie_conversation_test_data import main
main()
```

**Run as a job:** Attach the job to `genie_conversation_test_data.py` with the same working directory as ingestion so `config` and `genie_oauth` are on the path. After the run, trigger the SDP pipeline (or wait for the next run) so new audit events are picked up and written to `message_details`.

## SQL vs Python

- **SQL** (`../sql/`): Dashboard queries only. No secrets, no API calls. Reads from `system.access.audit`, `system.query.history`, and `main.genie_analytics.message_details`.
- **Python** (this folder): Message ingestion (`message_details`, `message_fetch_errors`) and space details (`genie_space_details`). Uses secrets for OAuth.
