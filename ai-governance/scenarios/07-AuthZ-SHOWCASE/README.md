# AI AuthZ Showcase

A 6-tab Streamlit app on Databricks Apps that demonstrates every major AI authorization pattern in one place. The goal: show that Unity Catalog is the single enforcement point whether you're using Genie, Vector Search, UC Functions, a custom MCP server, an Agent Bricks supervisor, or an external API — and that OBO vs M2M is a deliberate design choice, not an accident.

## Architecture

```mermaid
flowchart TB
    subgraph APP["🖥️ Databricks App (Streamlit)"]
        T1["💬 Tab 1\nAsk Genie\n─────\nOBO\nuser token"]
        T2["🔍 Tab 2\nSearch Knowledge\n─────\nM2M\napp SP"]
        T3["⚙️ Tab 3\nBusiness Logic\n─────\nM2M\napp SP"]
        T4["🔧 Tab 4\nCustom MCP\n─────\nOBO\nuser token"]
        T5["🤖 Tab 5\nAsk Agent\n─────\nOBO\nuser token"]
        T6["🌐 Tab 6\nExternal Intel\n─────\nOBO\nuser token"]
    end

    T1 -->|OBO| GENIE["Genie API"]
    T2 -->|M2M| VS["VS Index\n+ FM API"]
    T3 -->|M2M| SQL["UC Functions\nvia SQL Warehouse"]
    T4 -->|OBO + X-Forwarded-Email| MCP["Custom MCP App\n(Databricks App)"]
    T5 -->|OBO| AGENT["Agent Bricks\nSupervisor"]
    T6 -->|OBO| UCHP["UC HTTP Proxy"]

    AGENT -->|OBO sub-agent| GENIE
    AGENT -->|OBO sub-agent| SQL
    UCHP --> GH["GitHub MCP\nCustom MCP"]

    GENIE & VS & SQL & MCP & AGENT & UCHP --> UC

    UC["🛡️ Unity Catalog — single enforcement point\nRow filters · Column masks · current_user() · is_member() · USE CONNECTION"]

    style APP fill:#1e293b,stroke:#475569,color:#f1f5f9
    style UC fill:#1e3a5f,stroke:#3b82f6,color:#93c5fd
    style T1 fill:#0f2d1f,stroke:#22c55e,color:#86efac
    style T4 fill:#0f2d1f,stroke:#22c55e,color:#86efac
    style T5 fill:#0f2d1f,stroke:#22c55e,color:#86efac
    style T6 fill:#0f2d1f,stroke:#22c55e,color:#86efac
    style T2 fill:#2d1f0f,stroke:#f59e0b,color:#fcd34d
    style T3 fill:#2d1f0f,stroke:#f59e0b,color:#fcd34d
```

> Green tabs = OBO (user token propagates end-to-end) · Amber tabs = M2M (app SP identity)

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
