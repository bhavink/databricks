# AuthZ Showcase — Zero to Running Setup Guide

This document walks you through deploying the AI AuthZ Showcase from scratch. The audience is a platform engineer or solutions architect with a Databricks workspace who wants a working demo of every AI authorization pattern, with Unity Catalog as the single enforcement point.

Every step is explicit. Nothing is left to assumption.

---

## What You Are Building

A 7-tab Streamlit application running on Databricks Apps that demonstrates:

| Tab | Pattern | What It Shows |
|-----|---------|--------------|
| 1 — Genie | OBO User | Row filters + column masks enforced per human identity |
| 2 — Vector Search | M2M (App SP) | Shared knowledge base, app credentials query VS indexes |
| 3 — UC Functions | M2M (App SP) | SQL + Python UDFs with `is_member()` group-based access |
| 4 — Custom MCP | OBO User + M2M | Two-proxy token passthrough, MCP server with mixed auth |
| 5 — Supervisor Agent | OBO User | Agent Bricks supervisor endpoint, user token forwarded |
| 6 — External MCP | UC Connections | GitHub (Managed OAuth) + Custom MCP (Bearer Token) via USE CONNECTION |
| 7 — Governance | REVOKE/GRANT | Live toggle of connection access, proving UC is the single control plane |

Two Databricks Apps are deployed:

- **authz-showcase** (AppA) — Streamlit frontend, 7 tabs
- **authz-showcase-custom-mcp** (AppB) — FastMCP server, 4 tools: `debug_auth_context`, `get_deal_approval_status`, `submit_deal_for_approval`, `get_crm_sync_status`

---

## Prerequisites

Before you start, confirm every item below. Do not proceed until all are true.

### Infrastructure

- [ ] **Databricks workspace** on Azure (tested). AWS/GCP should work with connection adjustments.
- [ ] **Unity Catalog enabled** on the workspace.
- [ ] **Admin access** — you need to: enable preview features, create UC connections, query system tables, create workspace groups, create Databricks Apps.
- [ ] **A SQL Warehouse** — serverless recommended. Record the warehouse ID (you will need it in multiple places).

### Tools on Your Machine

- [ ] **Databricks CLI** installed and authenticated with a profile pointing to your workspace.
  ```bash
  databricks auth login --host https://<your-workspace>.azuredatabricks.net --profile my-profile
  databricks auth token --profile my-profile  # verify it works
  ```
- [ ] **Python 3.10+** with `databricks-sdk` installed:
  ```bash
  pip install databricks-sdk requests
  ```

### External Dependencies (Tabs That Need Them)

- [ ] **A Genie Space** (Tab 1) — create one in the workspace UI against the sales data tables you will create in Step 1. Record the Genie Space ID.
- [ ] **A Vector Search endpoint** (Tab 2) — or the script in Step 5 will create one for you (`authz-showcase-vs`).
- [ ] **An Agent Bricks supervisor endpoint** (Tab 5) — deploy a Multi-Agent Supervisor via the AI Playground or Mosaic AI. Record the endpoint name.
- [ ] **A GitHub account** (Tab 6) — for the GitHub MCP external connection (Managed OAuth).

---

## Step 1: Create Catalog, Schema, and Tables

**Script:** `seed/00_catalog_schema.sql`

This creates:
- Catalog: `authz_showcase`
- Schema: `authz_showcase.sales` — business data with row/column security
- Schema: `authz_showcase.knowledge_base` — documents for Vector Search RAG
- Schema: `authz_showcase.functions` — UC Functions

**Run:**
```bash
databricks sql exec --profile <your-profile> --file seed/00_catalog_schema.sql
```

Or paste each statement into a SQL editor/notebook and run manually.

**Verify:**
```sql
SHOW SCHEMAS IN authz_showcase;
-- Expected: sales, knowledge_base, functions
```

---

## Step 2: Create Workspace Groups

**Script:** `seed/01_create_groups.py`

Creates two workspace groups used by row-level security policies:
- `authz_showcase_west` — West region sales reps
- `authz_showcase_east` — East region sales reps

**Run:**
```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> python seed/01_create_groups.py
```

These groups determine which rows each user sees when row filters are applied.

---

## Step 3: Seed Demo Data

**Script:** `seed/02_seed_data.py`

Populates all tables with realistic synthetic sales data. Your email is mapped to a West region rep so row-level security is immediately testable.

**Run:**
```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> \
CURRENT_USER_EMAIL=you@example.com \
python seed/02_seed_data.py
```

Replace `you@example.com` with the email of the user who will run the demo.

**Expected output:**
```
Creating tables...
  ✓ authz_showcase.sales.sales_reps          (8 rows)
  ✓ authz_showcase.sales.customers           (10 rows)
  ✓ authz_showcase.sales.products            (5 rows)
  ✓ authz_showcase.sales.opportunities       (41 rows)
  ✓ authz_showcase.knowledge_base.product_docs    (10 rows)
  ✓ authz_showcase.knowledge_base.sales_playbooks (6 rows)
```

**Safe to re-run.** It drops and recreates tables each time.

---

## Step 4: Apply Security Policies

Three scripts, run in order.

### 4a. Row Filters + Column Masks

**Script:** `seed/03_row_col_security.sql`

```bash
databricks sql exec --profile <your-profile> --file seed/03_row_col_security.sql
```

This applies:
- Row filters on `opportunities` and `sales_reps` (users only see their region's data)
- Column masks on sensitive fields (e.g., commission rates visible only to executives)

### 4b. Grants

**Script:** `seed/04_grant_permissions.sql`

```bash
databricks sql exec --profile <your-profile> --file seed/04_grant_permissions.sql
```

Grants SELECT, USE CATALOG, USE SCHEMA to the appropriate groups and users.

### 4c. Verify

**Script:** `seed/05_verify_security.sql`

```bash
databricks sql exec --profile <your-profile> --file seed/05_verify_security.sql
```

Confirms row filters and column masks are applied. Check the output carefully — you should see filtered results that differ by group membership.

---

## Step 5: Create Vector Search Indexes

**Script:** `seed/06_create_vs_index.py`

Creates:
1. A Vector Search endpoint: `authz-showcase-vs` (serverless)
2. Two Delta Sync indexes:
   - `authz_showcase.knowledge_base.product_docs_index`
   - `authz_showcase.knowledge_base.sales_playbooks_index`

Uses the `databricks-bge-large-en` embedding model.

**Run:**
```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> python seed/06_create_vs_index.py
```

**This takes up to 20 minutes.** The script polls until both indexes reach `ONLINE` status. Do not interrupt it.

---

## Step 6: Create UC Functions

Two scripts.

### 6a. Create Functions

**Script:** `seed/07_create_uc_functions.sql`

```bash
databricks sql exec --profile <your-profile> --file seed/07_create_uc_functions.sql
```

Creates SQL and Python UDFs in `authz_showcase.functions`:
- `get_rep_quota` — quota lookup with `is_member()` group check
- `calculate_attainment` — attainment percentage calculation
- `recommend_next_action` — deal recommendation logic

### 6b. Grant Execute

**Script:** `seed/07_grant_uc_functions.sql`

```bash
databricks sql exec --profile <your-profile> --file seed/07_grant_uc_functions.sql
```

---

## Step 7: Deploy the Custom MCP Server (AppB)

Deploy AppB **first** because AppA references its URL, and you need AppB's Service Principal (SP) client ID for connection setup.

### 7a. Upload Source Code to Workspace

```bash
databricks workspace import-dir mcp-server/ /Workspace/Users/<you>/authz-showcase-custom-mcp \
  --profile <your-profile> --overwrite
```

### 7b. Create the App

```bash
databricks apps create authz-showcase-custom-mcp \
  --profile <your-profile> \
  --json '{
    "name": "authz-showcase-custom-mcp",
    "description": "Custom MCP server — deal approval and CRM sync tools"
  }'
```

This auto-creates a Service Principal for the app. **Record the SP's application_id (client_id)** — you need it for connection grants and UC permissions.

To find it:
```bash
databricks apps get authz-showcase-custom-mcp --profile <your-profile>
# Look for the service_principal_client_id in the output
```

### 7c. Deploy

```bash
databricks apps deploy authz-showcase-custom-mcp \
  --profile <your-profile> \
  --source-code-path /Workspace/Users/<you>/authz-showcase-custom-mcp
```

### 7d. Verify

Wait for the app to reach `RUNNING` state:
```bash
databricks apps get authz-showcase-custom-mcp --profile <your-profile>
```

Test the health endpoint:
```bash
curl -s https://authz-showcase-custom-mcp-<workspace-id>.<region>.azure.databricksapps.com/health
```

---

## Step 8: Create Approval Requests Table

**Script:** `seed/09_create_approval_requests.sql`

```bash
databricks sql exec --profile <your-profile> --file seed/09_create_approval_requests.sql
```

Creates `authz_showcase.sales.approval_requests` with three seed rows used by the Custom MCP tools.

---

## Step 9: Create UC HTTP Connections

**Script:** `seed/08_create_external_mcp_conn.py`

Creates two UC connections:

| Connection | Type | Purpose |
|-----------|------|---------|
| `authz_showcase_github_conn` | Managed OAuth (U2M) | GitHub MCP — per-user GitHub auth |
| `authz_showcase_custmcp_conn` | Bearer Token | Custom MCP server — shared SP token |

### 9a. Install GitHub MCP from Marketplace (Manual UI Step)

1. Go to **Workspace > Marketplace > Agents > MCP Servers > GitHub**
2. Click **Install**
3. Set the connection name to: `authz_showcase_github_conn`
4. Credential type: **Managed OAuth**

### 9b. Create the Custom MCP Bearer Token Connection

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> \
CUSTMCP_APP_HOST=authz-showcase-custom-mcp-<workspace-id>.<region>.azure.databricksapps.com \
SP_BEARER_TOKEN=$(databricks auth token --profile <your-profile> | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])") \
python seed/08_create_external_mcp_conn.py
```

### 9c. Connection Ownership (Critical for Tab 7)

Connection ownership determines who has **implicit, irrevocable** USE CONNECTION. For the governance demo to work:

| Connection | Owner Must Be | Tested Identity | Why |
|-----------|--------------|----------------|-----|
| `authz_showcase_custmcp_conn` | Demo user (you) | App SP | You REVOKE from the SP; SP is not the owner, so REVOKE works |
| `authz_showcase_github_conn` | App SP | Demo user (OBO) | You REVOKE from yourself; you are not the owner, so REVOKE works |

If you get this backwards, REVOKE will appear to succeed but the owner will still have access, and Tab 7 will not demonstrate anything.

---

## Step 10: Deploy the Streamlit App (AppA)

### 10a. Update `app/app.yaml` with Your Values

Open `app/app.yaml` and replace every value with your own. The key fields:

```yaml
env:
  - name: GENIE_SPACE_ID
    value: "<your-genie-space-id>"
  - name: VS_INDEX
    value: "authz_showcase.knowledge_base.product_docs_index"
  - name: VS_INDEX_PB
    value: "authz_showcase.knowledge_base.sales_playbooks_index"
  - name: FM_ENDPOINT
    value: "databricks-meta-llama-3-3-70b-instruct"
  - name: SQL_WAREHOUSE
    value: "<your-warehouse-id>"
  - name: UC_FUNCTIONS_CATALOG
    value: "authz_showcase"
  - name: SUPERVISOR_ENDPOINT
    value: "<your-supervisor-endpoint-name>"
  - name: CUSTOM_MCP_URL
    value: "https://authz-showcase-custom-mcp-<workspace-id>.<region>.azure.databricksapps.com/mcp"
  - name: GITHUB_CONN
    value: "authz_showcase_github_conn"
  - name: CUSTMCP_CONN
    value: "authz_showcase_custmcp_conn"
  - name: MLFLOW_EXPERIMENT_NAME
    value: "/Users/<your-email>/mas-<id>-dev-experiment"
```

Also update the `resources:` block with your Genie Space ID, warehouse ID, and serving endpoint names.

### 10b. Configure User Authorization Scopes

In the Databricks UI: **Apps > authz-showcase > Edit > Configure**

Add these user authorization scopes:
- `sql`
- `dashboards.genie`
- `serving.serving-endpoints`
- `unity-catalog`

These produce a real JWT with scopes in the token's `scp` claim. Without them, OBO tabs will fail silently.

### 10c. Upload Source Code

```bash
databricks workspace import-dir app/ /Workspace/Users/<you>/authz-showcase \
  --profile <your-profile> --overwrite
```

### 10d. Create the App

```bash
databricks apps create authz-showcase \
  --profile <your-profile> \
  --json '{
    "name": "authz-showcase",
    "description": "AI AuthZ Showcase — 7-tab Streamlit demo of every authorization pattern"
  }'
```

### 10e. Deploy

```bash
databricks apps deploy authz-showcase \
  --profile <your-profile> \
  --source-code-path /Workspace/Users/<you>/authz-showcase
```

### 10f. Grant the App SP Access to UC Resources

The `resources:` block in `app.yaml` auto-grants some permissions on deploy, but several require manual SQL grants. Run these with the App SP's application_id:

```sql
GRANT USE CATALOG  ON CATALOG  authz_showcase                              TO `<app-sp-id>`;
GRANT USE SCHEMA   ON SCHEMA   authz_showcase.sales                        TO `<app-sp-id>`;
GRANT USE SCHEMA   ON SCHEMA   authz_showcase.knowledge_base               TO `<app-sp-id>`;
GRANT USE SCHEMA   ON SCHEMA   authz_showcase.functions                    TO `<app-sp-id>`;
GRANT SELECT       ON TABLE    authz_showcase.sales.sales_reps             TO `<app-sp-id>`;
GRANT SELECT       ON TABLE    authz_showcase.sales.opportunities          TO `<app-sp-id>`;
GRANT SELECT       ON TABLE    authz_showcase.knowledge_base.product_docs  TO `<app-sp-id>`;
GRANT SELECT       ON TABLE    authz_showcase.knowledge_base.sales_playbooks TO `<app-sp-id>`;
```

---

## Step 11: Configure Connection Governance

**Script:** `seed/demo.py`

This is the single entry point for demo lifecycle management. Run `--before` to set up everything Tab 7 needs:

```bash
python seed/demo.py --before --profile <your-profile>
```

**What `--before` does (all idempotent):**
1. Verifies both apps are RUNNING
2. Onboards app SPs: group membership, warehouse CAN_USE, UC grants
3. Refreshes `authz_showcase_custmcp_conn` bearer token (1-hour TTL)
4. Configures UC connection ownership and grants for Tab 7
5. Resets `approval_requests` to initial seed state (3 rows)
6. Resets your user to `authz_showcase_west` (West Rep persona for demo start)
7. Verifies both connections exist
8. Prints full status summary

**Run this before every demo session.** Bearer tokens expire in ~1 hour.

After the demo, clean up:
```bash
python seed/demo.py --after --profile <your-profile>
```

---

## Step 12: Set Up Observability (Optional but Recommended)

### 12a. Enable Production Monitoring

In the Databricks workspace UI: **Admin Settings > Previews > Production Monitoring** — toggle ON.

### 12b. Run the Observability Setup

Upload `observability/setup_observability.py` as a Databricks notebook and run it, OR run locally:

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> python observability/setup_observability.py
```

This calls `enable_databricks_trace_archival()` programmatically — the UI toggle alone does NOT create a queryable Delta table.

### 12c. Deploy the Lakeview Dashboard

```bash
python observability/deploy_dashboard.py --profile <your-profile>
```

Creates a Lakeview dashboard with SQL alerts for monitoring trace data, latency, and error rates.

---

## Step 13: Verify Everything

### 13a. Run the Test Harness

**Script:** `seed/test_harness.py`

Before running, update the constants at the top of the file with your values (warehouse ID, app URLs, endpoint names, connection names).

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> python seed/test_harness.py
```

Validates 8 checks:
1. App status (both apps RUNNING)
2. Groups exist
3. Data seeded correctly
4. Row filters enforced
5. UC Functions executable
6. Vector Search indexes ONLINE
7. Connections valid
8. Custom MCP server responding

All 8 must PASS. Exit code 0 = all pass, 1 = any fail.

### 13b. Manual Smoke Test

Open the Streamlit app URL in your browser:
```
https://authz-showcase-<workspace-id>.<region>.azure.databricksapps.com
```

Walk through each tab:
- **Tab 1 (Genie):** Ask a question. Verify you only see West region data.
- **Tab 2 (Vector Search):** Search product docs. Should return results.
- **Tab 3 (UC Functions):** Call `get_rep_quota`. Verify group-based access.
- **Tab 4 (Custom MCP):** Call `get_deal_approval_status`. Verify OBO context shows your email.
- **Tab 5 (Supervisor):** Ask the agent a question. Verify it routes to sub-agents.
- **Tab 6 (External MCP):** Use GitHub connection. Complete OAuth consent if first time.
- **Tab 7 (Governance):** REVOKE a connection, verify tools disappear. GRANT it back.

---

## Critical Gotchas

These are hard-won lessons from development. Each one will block you if you hit it.

### 1. `account users` Has Implicit USE CONNECTION

If your workspace has `account users` granted USE CONNECTION on a connection, individual REVOKEs on specific users or SPs are silently overridden. You must `REVOKE USE CONNECTION ON CONNECTION <conn> FROM account users` first. The `demo.py --before` script handles this, but if you are setting up manually, do it yourself.

### 2. Connection Ownership = Implicit, Irrevocable Access

The owner of a UC connection always has USE CONNECTION. This cannot be revoked. For Tab 7 governance demos: the identity you are testing REVOKE against must NOT be the connection owner. See the ownership table in Step 9c.

### 3. App SP Only Changes on Delete + Create

`databricks apps deploy` does NOT change the Service Principal. If you need a new SP (e.g., to match connection grants after a permissions reset), you must:
```bash
databricks apps delete authz-showcase --profile <your-profile>
databricks apps create authz-showcase --profile <your-profile> --json '...'
databricks apps deploy authz-showcase --profile <your-profile> --source-code-path ...
```

After delete + create, you must re-run all SP grants and `demo.py --before`.

### 4. `mlflow-tracing` vs `mlflow`

The apps use `mlflow-tracing` (lightweight). It does NOT have `set_experiment()`, `get_experiment_by_name()`, or `get_tracing_context_headers_for_http_request()`. Use `set_destination()` instead. The `startup.sh` scripts handle the `mlflow-skinny` conflict in the Apps runtime by force-reinstalling `mlflow-tracing`.

### 5. `enable_databricks_trace_archival()` Is Required

The UI "Enable Monitoring" toggle alone does NOT create a queryable Delta table. You must call the API programmatically via `setup_observability.py`. Without this, your Lakeview dashboard will have no data.

### 6. Assessments Struct Field Is `name` Not `assessment_name`

The trace Delta table schema uses `a.name` for scorer names, not `a.assessment_name` as some documentation suggests. If your dashboard queries return empty, check this.

### 7. OBO Token May Lack `sql` Scope

When AppA forwards a user's OBO token to the MCP server (AppB), the token may not have `sql` scope depending on the UC proxy path. The MCP server handles this with M2M fallback — but if you see "insufficient permissions" in Tab 4, verify the user authorization scopes are configured (Step 10b).

### 8. Bearer Token Connections Expire (~1 Hour)

UC Bearer Token connections store a static credential. It expires. Run `demo.py --before` to refresh before every demo session. For a production deployment, replace with an SP M2M token from a dedicated client credentials flow.

### 9. System Tables Have Eventual Consistency

New serving endpoints may take hours or days to appear in `system.serving.*` and `system.ai_gateway.*`. Do not expect real-time data in observability dashboards for newly created resources.

### 10. Managed OAuth Requires Per-User Consent

GitHub OAuth (U2M) connections require each user to complete OAuth consent by visiting the connection URL in their browser. The app cannot do this on behalf of the user. First-time users of Tab 6 must complete this flow.

---

## Values to Customize

Every value below must be replaced with your own. Grep for the example values to find all occurrences.

| Value | Where Used | Example |
|-------|-----------|---------|
| Catalog name | seed scripts, app.py, mcp-server | `authz_showcase` |
| Schema name (sales) | seed scripts, app.py, mcp-server | `sales` |
| Schema name (knowledge_base) | seed scripts, app.py | `knowledge_base` |
| Genie Space ID | `app/app.yaml` env + resources | `01f117ff5bdd167daf9aed6baa32c4c8` |
| Supervisor Endpoint | `app/app.yaml` env + resources | `mas-155f64f7-endpoint` |
| FM Endpoint | `app/app.yaml` env + resources | `databricks-meta-llama-3-3-70b-instruct` |
| VS Index (product docs) | `app/app.yaml` env + resources | `authz_showcase.knowledge_base.product_docs_index` |
| VS Index (playbooks) | `app/app.yaml` env + resources | `authz_showcase.knowledge_base.sales_playbooks_index` |
| VS Endpoint Name | `seed/06_create_vs_index.py` | `authz-showcase-vs` |
| SQL Warehouse ID | `app/app.yaml`, `mcp-server/app.yaml`, seed scripts | `093d4ec27ed4bdee` |
| Custom MCP URL | `app/app.yaml` | `https://authz-showcase-custom-mcp-<wid>.<region>.azure.databricksapps.com/mcp` |
| GitHub MCP Connection | `app/app.yaml`, seed scripts | `authz_showcase_github_conn` |
| Custom MCP Connection | `app/app.yaml`, seed scripts | `authz_showcase_custmcp_conn` |
| MLflow Experiment Name | `app/app.yaml`, `mcp-server/app.yaml` | `/Users/<email>/mas-<id>-dev-experiment` |
| Databricks CLI Profile | all CLI commands | `adb-wx1` |
| Workspace URL | all CLI commands, app URLs | `adb-1516413757355523.3.azuredatabricks.net` |
| Demo User Email | `seed/02_seed_data.py` | `you@databricks.com` |
| App SP Application ID | UC grants, connection ownership | (from `databricks apps get`) |

---

## File Reference

```
07-AuthZ-SHOWCASE/
├── app/                          # AppA — Streamlit frontend
│   ├── app.py                    #   Main application (7 tabs)
│   ├── app.yaml                  #   App config (env vars, resources)
│   ├── auth_utils.py             #   OBO token extraction helpers
│   ├── requirements.txt          #   Python deps (databricks-sdk, streamlit, mlflow-tracing)
│   └── startup.sh                #   Fixes mlflow-skinny conflict, launches streamlit
├── mcp-server/                   # AppB — Custom MCP server
│   ├── server/                   #   FastMCP server source
│   │   └── main.py               #     4 MCP tools (debug_auth_context, deal approval, CRM sync)
│   ├── app.yaml                  #   App config (authorization: disabled for token passthrough)
│   ├── pyproject.toml            #   Python deps (mcp, databricks-sdk, uvicorn, mlflow-tracing)
│   ├── startup.sh                #   uv sync + mlflow fix + launches server
│   └── requirements.txt          #   Just `uv` (uv manages the real deps via pyproject.toml)
├── seed/                         # Setup + demo lifecycle scripts
│   ├── 00_catalog_schema.sql     #   Step 1: Create catalog + schemas
│   ├── 01_create_groups.py       #   Step 2: Create workspace groups
│   ├── 02_seed_data.py           #   Step 3: Seed demo data
│   ├── 03_row_col_security.sql   #   Step 4a: Row filters + column masks
│   ├── 04_grant_permissions.sql  #   Step 4b: Group/user grants
│   ├── 05_verify_security.sql    #   Step 4c: Validate security policies
│   ├── 06_create_vs_index.py     #   Step 5: Vector Search indexes
│   ├── 07_create_uc_functions.sql #  Step 6a: Create UC Functions
│   ├── 07_grant_uc_functions.sql #   Step 6b: Grant execute on functions
│   ├── 08_create_external_mcp_conn.py # Step 9: UC HTTP connections
│   ├── 09_create_approval_requests.sql # Step 8: Approval requests table
│   ├── demo.py                   #   Step 11: Demo lifecycle (--before / --after / --status)
│   └── test_harness.py           #   Step 13: Validation (8 checks)
├── observability/                # Step 12: Tracing + monitoring
│   ├── setup_observability.py    #   Enable trace archival + experiment config
│   ├── deploy_dashboard.py       #   Create Lakeview dashboard + SQL alerts
│   ├── setup_scorers.py          #   Configure assessment scorers
│   └── tracing_config.py         #   Tracing configuration helpers
└── SETUP.md                      # This file
```

---

## Execution Order Summary

For copy-paste convenience, here is the full sequence assuming profile `my-profile` and email `you@example.com`:

```bash
export PROFILE=my-profile
export EMAIL=you@example.com

# Step 1: Catalog + schemas
databricks sql exec --profile $PROFILE --file seed/00_catalog_schema.sql

# Step 2: Groups
DATABRICKS_CONFIG_PROFILE=$PROFILE python seed/01_create_groups.py

# Step 3: Seed data
DATABRICKS_CONFIG_PROFILE=$PROFILE CURRENT_USER_EMAIL=$EMAIL python seed/02_seed_data.py

# Step 4: Security policies
databricks sql exec --profile $PROFILE --file seed/03_row_col_security.sql
databricks sql exec --profile $PROFILE --file seed/04_grant_permissions.sql
databricks sql exec --profile $PROFILE --file seed/05_verify_security.sql

# Step 5: Vector Search (takes ~20 min)
DATABRICKS_CONFIG_PROFILE=$PROFILE python seed/06_create_vs_index.py

# Step 6: UC Functions
databricks sql exec --profile $PROFILE --file seed/07_create_uc_functions.sql
databricks sql exec --profile $PROFILE --file seed/07_grant_uc_functions.sql

# Step 7: Deploy AppB (Custom MCP server)
databricks workspace import-dir mcp-server/ /Workspace/Users/$EMAIL/authz-showcase-custom-mcp --profile $PROFILE --overwrite
databricks apps create authz-showcase-custom-mcp --profile $PROFILE --json '{"name":"authz-showcase-custom-mcp","description":"Custom MCP server"}'
databricks apps deploy authz-showcase-custom-mcp --profile $PROFILE --source-code-path /Workspace/Users/$EMAIL/authz-showcase-custom-mcp

# Step 8: Approval requests table
databricks sql exec --profile $PROFILE --file seed/09_create_approval_requests.sql

# Step 9: UC connections (GitHub via UI first, then run script)
DATABRICKS_CONFIG_PROFILE=$PROFILE \
CUSTMCP_APP_HOST=$(databricks apps get authz-showcase-custom-mcp --profile $PROFILE --output json | python3 -c "import sys,json; print(json.load(sys.stdin).get('url','').replace('https://',''))") \
SP_BEARER_TOKEN=$(databricks auth token --profile $PROFILE | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])") \
python seed/08_create_external_mcp_conn.py

# Step 10: Deploy AppA (update app/app.yaml with your values first!)
databricks workspace import-dir app/ /Workspace/Users/$EMAIL/authz-showcase --profile $PROFILE --overwrite
databricks apps create authz-showcase --profile $PROFILE --json '{"name":"authz-showcase","description":"AI AuthZ Showcase"}'
databricks apps deploy authz-showcase --profile $PROFILE --source-code-path /Workspace/Users/$EMAIL/authz-showcase

# Step 11: Configure governance
python seed/demo.py --before --profile $PROFILE

# Step 12: Observability (optional)
DATABRICKS_CONFIG_PROFILE=$PROFILE python observability/setup_observability.py
python observability/deploy_dashboard.py --profile $PROFILE

# Step 13: Verify
DATABRICKS_CONFIG_PROFILE=$PROFILE python seed/test_harness.py
```

---

## Before Every Demo Session

```bash
python seed/demo.py --before --profile <your-profile>
```

This refreshes the bearer token, resets demo data, and verifies everything is running. Takes ~30 seconds. Do this every time, no exceptions.
