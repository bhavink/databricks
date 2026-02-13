# Genie Observability: Recommendations

Recommendations for the Genie Observability pipeline given **message details are only available via Genie REST API**, and for **splitting SQL (dashboard) vs Python (API extraction)**, using **account-level OAuth SP** with per-workspace permissions.

---

## 1. Recommendation: Messages Only via API

### Problem
- `system.access.audit` has **who, when, what action** (e.g. `genieGetConversationMessage`) but **no message content, SQL, or attachments**.
- Full message details (content, generated SQL, statement_id, attachments) exist only in the **Genie REST API**.

### Recommended flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  EXTRACTION (Python job – scheduled)                                         │
│  system.access.audit → unique (workspace, space, conversation, message)      │
│       → Genie API per message → main.genie_analytics.message_details (Delta)  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  DASHBOARD (SQL / AI/BI)                                                    │
│  Reads only Delta tables (+ system.access.audit, system.query.history)       │
│  No API calls at dashboard runtime.                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Extraction job (Python):**
  - Query audit for message-level actions (e.g. `genieGetConversationMessage`).
  - Deduplicate by `(workspace_id, message_id)`.
  - For each workspace in scope, get workspace token (see Auth below), then call Genie API per message.
  - Enrich with `system.query.history` (join on `statement_id` + `workspace_id`).
  - Write/merge into **`main.genie_analytics.message_details`** (single denormalized table; schema per `genie-messages-persistence-strategy.md`).
  - Run on a schedule (e.g. hourly/daily); use **incremental CDC** (only new messages since last `ingestion_timestamp` / last run).

- **Dashboard (SQL):**
  - Reads **only**:
    - `main.genie_analytics.message_details`
    - `system.access.audit` (for counts, trends, hierarchy metrics)
    - `system.query.history` (if not fully denormalized into `message_details`)
    - `system.access.workspaces_latest` (workspace names).
  - No Genie API calls; no Python at view time.

This keeps **governance and cost** under control: API usage and credentials stay in one scheduled job; dashboards stay fast and simple.

---

## 2. Recommendation: Separate SQL and Python

**Yes — separate SQL and Python.**

| Concern | Recommendation |
|--------|----------------|
| **Dashboard** | Pure SQL (or AI/BI dashboard definitions). No Python at dashboard runtime. |
| **Message extraction** | Python (notebook or job script) that calls Genie API and writes to Delta. |
| **Reuse** | SQL in `.sql` files or in a “dashboard SQL” notebook; Python in a “Genie message ingestion” job. |

### Why separate

1. **Dashboard** = parameterized queries over Delta + system tables; no API, no secrets at query time.
2. **Extraction** = API + OAuth + retries, batching, CDC; easier to test and run as a single-purpose job.
3. **Ownership** = BI/analytics own SQL/dashboard; data eng/platform own the ingestion job.
4. **CI/CD** = SQL can be deployed to AI/BI or a SQL repo; Python can be deployed as a Databricks job (notebook or script).

### Implemented layout (SQL vs Python split)

```
genie-aibi/
├── docs/                          # Design docs
│   ├── genie-observability-recommendations.md
│   ├── genie-messages-persistence-strategy.md
│   └── Genie Observability Demo.ipynb   # Optional all-in-one demo
├── sql/                           # Dashboard only – no secrets, no Python
│   ├── README.md
│   └── genie_observability_queries.sql  # All dashboard queries; params :workspace_id_filter, :days_lookback
├── python/                        # Ingestion only – uses genie-obs secrets
│   ├── README.md
│   ├── config.py                  # SECRETS_SCOPE, WORKSPACE_IDS, SPACE_IDS, table names
│   ├── genie_oauth.py             # OAuth via dbutils.secrets.get(scope, key)
│   └── genie_message_ingestion.py # Audit → Genie API → Delta (main.genie_analytics.message_details)
└── scripts/
    └── create_genie_obs_secrets.py # One-time: create scope genie-obs and store sp_client_id, sp_client_secret
```

- **SQL:** Use in a SQL notebook or AI/BI dashboard. Only parameters are `workspace_id_filter` and `days_lookback`; no credentials.
- **Python:** Run as a job or from a notebook on Databricks. Reads credentials from scope `genie-obs` (keys `sp_client_id`, `sp_client_secret`) and writes to `message_details`.

- **Dashboard:**
  - Either an **AI/BI dashboard** that uses only SQL (and reads `message_details` + system tables), or
  - A **“Genie Observability Dashboard”** notebook that contains **only** `%sql` cells (and no API calls).
  - SQL can be copied from the current notebook into `.sql` files or kept in that notebook.

- **Python:**
  - **`genie_message_ingestion.py`**: load message IDs from audit (with dedup), loop workspaces, get token per workspace, call Genie API, join with `system.query.history`, merge into `main.genie_analytics.message_details`.
  - **`genie_oauth.py`**: given `workspace_url`, `DATABRICKS_SP_CLIENT_ID`, `DATABRICKS_SP_CLIENT_SECRET`, return Bearer token (and optionally headers).
  - **`config.py`**: table names, catalog/schema, lookback days, batch size; **no** client id/secret.

---

## 3. Auth: Account-Level OAuth SP, Per-Workspace Token

You use a **single account-level OAuth Service Principal** added to each workspace/Genie with the right permissions. That matches the recommended pattern.

### Implementation

- **Do not hardcode** client id/secret in the notebook or repo.
- **Source credentials from environment** (or Databricks secrets) so the same code works in all environments:

```python
# In Python extraction job (e.g. genie_oauth.py or config)
import os

DATABRICKS_SP_CLIENT_ID = os.environ.get("DATABRICKS_SP_CLIENT_ID")
DATABRICKS_SP_CLIENT_SECRET = os.environ.get("DATABRICKS_SP_CLIENT_SECRET")

if not DATABRICKS_SP_CLIENT_ID or not DATABRICKS_SP_CLIENT_SECRET:
    raise ValueError("DATABRICKS_SP_CLIENT_ID and DATABRICKS_SP_CLIENT_SECRET must be set")
```

- **Per-workspace token:**
  Token is **workspace-scoped**. For each workspace you need to:
  1. Resolve `workspace_url` (e.g. from `system.access.workspaces_latest`).
  2. Call `POST {workspace_url}/oidc/v1/token` with `grant_type=client_credentials` and `scope=all-apis`, using the same SP credentials.
  3. Use the returned `access_token` for Genie API calls to that workspace only.

So: **one SP**, **one set of env vars** (`DATABRICKS_SP_CLIENT_ID`, `DATABRICKS_SP_CLIENT_SECRET`), **multiple workspaces** by obtaining a separate token per `workspace_url`. The current notebook’s pattern (token URL = `workspace_url + "/oidc/v1/token"`) is correct; just drive `workspace_url` from the list of workspaces you ingest (e.g. from audit or from a config table).

### Multi-workspace extraction

- **Option A:** Job parameter `workspace_id` → fetch token for that workspace only → process that workspace’s messages (current notebook behavior).
- **Option B:** Job without workspace filter → query audit for distinct `workspace_id` in scope → for each `workspace_id` get `workspace_url` → get token → fetch messages for that workspace → merge all into `message_details` (same table, partitioned/clustered by `workspace_id`).

Dashboard then filters by `workspace_id` (or workspace name via `workspaces_latest`) on the Delta table.

---

## 4. Summary

| Topic | Recommendation |
|-------|----------------|
| **Messages only via API** | Run a **scheduled Python job** that reads audit → dedup message IDs → calls Genie API per workspace (with per-workspace token) → writes/merges into `main.genie_analytics.message_details`. Dashboard **only** reads Delta (+ system tables). |
| **Separate SQL vs Python** | **Yes.** SQL for dashboard (and optional `.sql` files); Python for message extraction job. No API calls in the dashboard path. |
| **Auth** | Use **account-level OAuth SP** via **env vars** `DATABRICKS_SP_CLIENT_ID` and `DATABRICKS_SP_CLIENT_SECRET`; obtain a **per-workspace** token from `{workspace_url}/oidc/v1/token` and use it only for that workspace’s Genie API calls. |

**On Databricks:** Use **`dbutils.secrets.get(scope, key)`** for credentials. The notebook uses a **code-based config** (no widgets for secrets or extraction): set **`SECRETS_SCOPE`** (e.g. `"genie-obs"`), **`WORKSPACE_IDS`** (required list), and optionally **`SPACE_IDS`** in the Config cell. Store keys **`sp_client_id`** and **`sp_client_secret`** in that scope.

---

**Provided in this repo:**
- `python/config.py` – table names and batch/config (no secrets).
- `python/genie_oauth.py` – `get_credentials(dbutils=..., scope=...)` and `get_workspace_token(..., dbutils=..., scope=...)` so ingestion scripts can use `dbutils.secrets.get(scope, key)` when run on Databricks, or env vars when run elsewhere.

**Suggested next steps:** (1) Create a secret scope (e.g. `genie-obs`) and add keys `sp_client_id` and `sp_client_secret`. (2) Add `genie_message_ingestion.py` scaffold that uses `genie_oauth` with `dbutils` and `scope` and writes to `message_details`. (3) Build the dashboard in SQL/AI/BI that reads only Delta + system tables.
