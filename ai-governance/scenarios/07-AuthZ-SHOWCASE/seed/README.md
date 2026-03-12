# seed/ — AI AuthZ Showcase Setup & Operations

All scripts use profile `<YOUR_CLI_PROFILE>` by default. Override with `--profile <name>`.

## Quick Reference

```bash
# First-time setup (run scripts in order)
python3 seed/01_create_groups.py
# then run SQL files 00, 03, 04, 05, 07 via SQL editor or dbsql
python3 seed/02_seed_data.py
python3 seed/06_create_vs_index.py
python3 seed/08_create_external_mcp_conn.py

# Before every demo (one command)
python3 seed/demo.py --before --profile <YOUR_CLI_PROFILE>

# After every demo
python3 seed/demo.py --after --profile <YOUR_CLI_PROFILE>

# Quick health check
python3 seed/demo.py --status --profile <YOUR_CLI_PROFILE>

# Full integration test
python3 seed/test_harness.py --profile <YOUR_CLI_PROFILE>
```

## Scripts

### One-Time Setup (run in order)

| # | File | What it creates |
|---|------|----------------|
| 00 | `00_catalog_schema.sql` | Catalog `authz_showcase`, schemas: `sales`, `knowledge_base`, `functions` |
| 01 | `01_create_groups.py` | 7 workspace groups (`authz_showcase_west`, `_east`, `_central`, `_managers`, `_finance`, `_executives`, `_admin`) |
| 02 | `02_seed_data.py` | 6 tables: `sales_reps`, `customers`, `products`, `opportunities`, `product_docs`, `sales_playbooks` (41 opps, 10 customers, 8 reps) |
| 03 | `03_row_col_security.sql` | Row filters (`filter_opportunities`, `filter_customers`) + column masks (`mask_margin_pct`, `mask_is_strategic`, `mask_contract_value`, `mask_cost_price`, `mask_quota`) + helper tables (`quota_viewers`, `rep_regions`) |
| 04 | `04_grant_permissions.sql` | USE CATALOG/SCHEMA + SELECT grants to all 7 groups |
| 05 | `05_verify_security.sql` | 8 validation queries — run as different personas to verify row/column security |
| 06 | `06_create_vs_index.py` | VS endpoint `authz-showcase-vs` + Delta Sync indexes on `product_docs` and `sales_playbooks` |
| 07 | `07_create_uc_functions.sql` | 3 UC functions: `get_rep_quota`, `calculate_attainment`, `recommend_next_action` |
| 07 | `07_grant_uc_functions.sql` | EXECUTE grants on all 3 functions to `account users` |
| 08 | `08_create_external_mcp_conn.py` | UC HTTP connections: `authz_showcase_github_conn` (Managed OAuth) + `authz_showcase_custmcp_conn` (Bearer Token) |
| 09 | `09_create_approval_requests.sql` | `approval_requests` table + 3 seed rows + grants to MCP app SP |

### Operational (recurring)

| File | When to use | What it does |
|------|------------|--------------|
| `demo.py --before` | Before every demo | Verifies apps RUNNING, onboards SPs, refreshes custmcp bearer token (~1h TTL), configures connection ownership + grants for Tab 7, resets `approval_requests` to 3 seed rows, resets persona to West Rep, verifies UC connections |
| `demo.py --after` | After every demo | Resets `approval_requests`, resets persona to West Rep, restores USE CONNECTION grants (undoes Tab 7 revokes), cleans up stale SP secrets |
| `demo.py --status` | Anytime | App status, UC connections (with ownership + grant details), current persona groups, SP info |
| `test_harness.py` | Before demo or after infra changes | Validates all 8 capabilities: SQL warehouse, VS indexes, UC functions, custom MCP, supervisor endpoint, UC proxy connections |
| `cleanup_sp_secrets.py` | When hitting 5-secret limit | Advanced: `--dry-run` to inspect, default keeps platform secret, `--force-all` deletes everything (breaks the app — recovery steps in docstring) |

## Key Details

### Bearer Token Expiry

The UC HTTP connection `authz_showcase_custmcp_conn` stores a Databricks OAuth token that expires in ~1 hour. `demo.py --before` refreshes it automatically. If Tab 7 returns `401 {}` mid-demo, the token expired — re-run `--before`.

The GitHub connection (`authz_showcase_github_conn`) uses Managed OAuth — Databricks handles token refresh automatically after the one-time consent. No maintenance needed.

### Tab 7 Connection Ownership Model

For REVOKE/GRANT to work in the Tab 7 governance demo, the connection **owner** must differ from the **tested identity** (owners have implicit USE CONNECTION that can't be revoked):

| Connection | Auth Type | Tested Identity | Owner | Why |
|-----------|-----------|----------------|-------|-----|
| `authz_showcase_custmcp_conn` | Bearer Token | App SP | Demo user (you) | REVOKE on SP blocks it |
| `authz_showcase_github_conn` | Managed OAuth | Demo user (OBO) | App SP | REVOKE on user blocks it |

`demo.py --before` configures this automatically. Also removes USE CONNECTION from `account users` — that group grant silently overrides individual REVOKEs.

### After App Delete + Recreate

A new app gets a new service principal. Run:
```bash
python3 seed/demo.py --before --profile <YOUR_CLI_PROFILE>
```
This resolves SP UUIDs dynamically from the live app — no hardcoded IDs to update. The UI also picks up the new SP automatically via `DATABRICKS_CLIENT_ID` (injected by the Apps runtime).

### Hardcoded Values

| Value | Used in | Notes |
|-------|---------|-------|
| Warehouse `<YOUR_WAREHOUSE_ID>` | demo.py, test_harness.py, cleanup_sp_secrets.py | `test-serverless` |
| Catalog `authz_showcase` | All setup scripts, demo.py | |
| App names `authz-showcase`, `authz-showcase-custom-mcp` | demo.py, test_harness.py | |
| Supervisor endpoint `<YOUR_SUPERVISOR_ENDPOINT>` | test_harness.py | |
| Connection names `authz_showcase_*_conn` | demo.py, 08_ | |

### Script Dependencies

```
00 catalog/schema
 └─ 01 groups
     └─ 02 seed data (tables)
         ├─ 03 row/col security (filters + masks)
         │   └─ 04 grants (group → table)
         │       └─ 05 verify (validation queries)
         ├─ 06 VS indexes
         ├─ 07 UC functions + grants
         ├─ 08 external MCP connections
         └─ 09 approval_requests
              └─ [deploy apps]
                  └─ demo.py --before (SP onboarding + token refresh)
                      └─ test_harness.py (validation gate)
```
