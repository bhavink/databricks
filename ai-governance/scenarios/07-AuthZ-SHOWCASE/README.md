# AI AuthZ Showcase

A 6-tab Streamlit app on Databricks Apps that demonstrates every major AI authorization pattern in one place. The goal: show that Unity Catalog is the single enforcement point whether you're using Genie, Vector Search, UC Functions, a custom MCP server, an Agent Bricks supervisor, or an external API — and that OBO vs M2M is a deliberate design choice, not an accident.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATABRICKS APP (Streamlit)                         │
│                                                                         │
│  Tab 1 💬    Tab 2 🔍    Tab 3 ⚙️    Tab 4 🔧    Tab 5 🤖    Tab 6 🌐   │
│  Genie       VS Search   UC Funcs    Custom MCP  Agent       Ext MCP   │
│    │           │           │           │           │           │        │
│   OBO         M2M         M2M         OBO         OBO         OBO      │
│  user tok    app SP      app SP      user tok    user tok    user tok  │
└────┬──────────┬───────────┬───────────┬───────────┬───────────┬────────┘
     │          │           │           │           │           │
  Genie API  VS Index    UC Funcs    Custom       Agent       UC HTTP
             + FM API    via SQL     MCP App      Bricks      Proxy
                         Warehouse   X-Fwd-       Super-        │
                                     Email        visor       GitHub MCP
                                                    │          Custom MCP
     └──────────┴───────────┴───────────┴───────────┴───────────┘
              Unity Catalog — single enforcement point
         Row filters · Column masks · current_user() · is_member() · USE CONNECTION
```

## Tab Quick Reference

| Tab | Auth | Key Teaching Moment |
|-----|------|---------------------|
| 1 💬 Ask Genie | OBO | UC row filters + column masks enforce data access; Genie sees only what the user can see |
| 2 🔍 Search Knowledge | M2M | App SP has CAN_USE on the VS index; content access is controlled by who owns the SP |
| 3 ⚙️ Business Logic | M2M | `is_member()` inside UC function body — the function itself is the access gate |
| 4 🔧 Custom MCP | OBO | Two-proxy problem: user token is stripped; server reads X-Forwarded-Email (unforgeable) |
| 5 🤖 Ask Agent | OBO | Supervisor auto-propagates token to sub-agents; zero auth code in the supervisor |
| 6 🌐 External Intel | OBO | Per-user GitHub OAuth vs shared bearer via UC connection; USE CONNECTION as the gate |

## `current_user()` vs `is_member()` — Choosing the Right Tool

Both are legitimate UC policy primitives. The choice comes down to **what identity context is executing the SQL** — which varies depending on where in the stack the query runs.

| Function | What it evaluates | OBO contexts (Tab 1, 4, 5) | M2M contexts (Tab 2, 3) |
|---|---|---|---|
| `current_user()` | The identity on the active SQL token | ✅ Returns the OBO caller's email | ✅ Returns the SP's client_id |
| `is_member('group')` | Group membership of the SQL execution context | ⚠️ Evaluates the **execution runtime's** groups — which in Genie/Agent Bricks OBO is the service layer's context, not the calling user's workspace groups | ✅ Ideal — SP group membership is static and controlled by design |

**`current_user()` is the right anchor for user-scoped row filters:**
```sql
-- Resolves from the OBO token regardless of what service is running the SQL
opp_rep_email = current_user()
```
This is why rep-scoped access works correctly in Tab 1 (Genie), Tab 4 (Custom MCP), and Tab 5 (Agent Bricks supervisor) — the calling user's email propagates end-to-end.

**`is_member()` is the right tool for M2M role-based logic:**
```sql
-- Works perfectly in Tab 3 (M2M) because the app SP's group membership is
-- explicitly managed and stable — it is in authz_showcase_executives by design
is_member('authz_showcase_executives')
```
In OBO contexts through Genie or Agent Bricks, `is_member()` evaluates the service's execution context — so the result depends on the service layer's groups, not the user's. For role-based column masks that need to work in OBO, the pattern is a `current_user()` lookup against an allowlist table instead.

**Design rule**: Use `current_user()` to anchor anything that must carry the calling user's identity through an OBO chain. Use `is_member()` in M2M contexts where you control the executing SP's group membership directly.

## Pre-Demo Checklist

- **App running**: `databricks apps get authz-showcase --profile adb-wx1 | grep state`
- **Your persona**: West Rep only — in `authz_showcase_west`, no other authz_showcase groups
- **Refresh custmcp token** (required for Tab 6B, expires ~1h): `cd seed && python refresh_custmcp_token.py`
- **GitHub first-time auth**: visit `https://adb-<YOUR_WORKSPACE_ORG_ID>.3.azuredatabricks.net/explore/connections/authz_showcase_github_conn`

## Files

| Path | Description |
|------|-------------|
| `app/` | Streamlit app (6 tabs) |
| `mcp-server/` | Custom MCP server deployed as a Databricks App (Tab 4) |
| `seed/` | Setup scripts: seeding data, UC grants, OAuth integration, test harness, reset |
| `DEMO-GUIDE.md` | Full demo walkthrough, persona switching, troubleshooting, nuclear rebuild option |
| `AUTHZ-PATTERNS.md` | Technical reference: auth patterns, scope map, gotchas |
| `IMPLEMENTATION-PLAN.md` | Build log for future contributors |
