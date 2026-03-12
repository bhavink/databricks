# Identity, Scope, and Audit Architecture for Databricks AI Applications

> **Status**: Living document. Grounded in AuthZ Showcase (Phases 0–5), Databricks Fieldkit (March 2026), and empirical testing on Azure Databricks.
>
> **Audience**: Field Engineers building production AI apps on Databricks. Solution Architects evaluating auth/audit posture. Security reviewers assessing agent governance.
>
> **Companion docs**: `PROXY-ARCHITECTURE.md` (proxy mechanics), `AUTHZ-PATTERNS.md` (token map, OBO patterns), Fieldkit `governance/ai-governance.md` (governance framework)

---

## 1. Problem Statement

Databricks AI applications use multiple services (Genie, Vector Search, UC Functions, custom MCP, Agent Bricks, external MCP). Each service has a different identity model. Some run as the user (OBO), some run as the app service principal (M2M). The result:

1. **Identity fragmentation**: `system.access.audit` records the SQL session identity — for M2M paths, that's the SP UUID, not the human who triggered it. The human is invisible in the data plane audit log.
2. **Scope overexposure**: OAuth integrations default to `all-apis`, granting the user's token access to every workspace service — not just the one the app needs.
3. **No unified audit trail**: The application plane (MLflow traces) and data plane (`system.access.audit`) are separate systems with no platform-built join. Teams must build the correlation independently.
4. **Extensibility risk**: As new services are added (Lakebase, new MCP servers, new agent frameworks), the identity and audit patterns must scale — not require per-service ad-hoc solutions.

This document defines the complete identity map, minimum viable scopes, audit architecture, product gaps, and a proposed stopgap solution.

---

## 2. Proxy Architecture (Summary)

Every Databricks App has an automatic reverse proxy. See `PROXY-ARCHITECTURE.md` for full mechanics.

```
Internet → [Databricks Apps Proxy] → your app (port 8000)
```

The proxy:
- **Authenticates** the caller (OAuth cookie or Bearer token)
- **Strips** the original Authorization header
- **Injects** `X-Forwarded-Email`, `X-Forwarded-User`, `X-Forwarded-Access-Token`

Key headers:

| Header | Trust | Use for |
|---|---|---|
| `X-Forwarded-Email` | **High** — proxy-injected, unforgeable | User identity in M2M patterns |
| `X-Forwarded-Access-Token` | Medium-High — with UI User Authorization (Public Preview), this CAN be a real OBO JWT carrying service scopes (`sql`, `serving`, etc.), not just a minimal OIDC token. Without UI User Auth, it remains a minimal OIDC JWT. | OBO API calls (Genie, Agent Bricks, OBO SQL when UI User Auth is configured) |
| `X-Forwarded-User` | High — `{user_id}@{workspace_id}` | Unique identifier |

**Two-proxy problem**: When App A calls App B, Proxy B strips App A's token. Solution: `authorization: disabled` on App B + read `X-Forwarded-Email` for identity. Trade-off: external clients (Claude Code) need `authorization: enabled`. See `PROXY-ARCHITECTURE.md § External client path`.

**Third proxy type — UC External MCP Proxy**: For External MCP via UC HTTP connections, a separate proxy sits at `/api/2.0/mcp/external/{connection_name}`. This proxy validates the caller's `unity-catalog` scope, checks `USE CONNECTION` grants, and forwards the call to the external service using the connection's configured credential (shared API key or per-user OAuth). The MCP server itself needs zero data permissions — UC manages the credential lifecycle.

---

## 3. Complete Service Identity Map

### Three identity models

| Model | Who executes | User identity source | `current_user()` returns | UC audit shows |
|---|---|---|---|---|
| **True OBO** | User's token | OAuth token | User email | User email |
| **Proxy identity + M2M** | App SP | `X-Forwarded-Email` (injected by proxy) | SP UUID | SP UUID |
| **Pure M2M** | App SP | Not involved | SP UUID | SP UUID |

### Per-service breakdown

| # | Service | Identity model | Credential executing | User identity source | `current_user()` | `is_member()` | UC row filters fire as | UC audit identity |
|---|---|---|---|---|---|---|---|---|
| 1 | **Genie** (Conversation API) | True OBO | User's OAuth token | Token `sub` claim | User email | **Genie service context** (NOT user groups) | User | User |
| 2 | **AI/BI Dashboard** (run-as-viewer) | True OBO | Viewer's token | Dashboard viewer session | Viewer email | Viewer groups | Viewer | Viewer |
| 3 | **AI/BI Dashboard** (run-as-owner) | Delegated | Owner's token | Dashboard owner | Owner email | Owner groups | Owner | Owner |
| 4 | **Agent Bricks / Model Serving** | True OBO | User's OAuth token (auto-propagated to sub-agents) | Token forwarded end-to-end | User email (at sub-agent) | Sub-agent dependent | User | User |
| 5 | **SQL Warehouse** (direct, user token) | True OBO | User's OAuth token | Token `sub` claim | User email | User groups | User | User |
| 6 | **SQL Warehouse** (direct, SP token) | Pure M2M | App SP | None | SP UUID | SP groups | SP | SP UUID |
| 7 | **Custom MCP** (Databricks Apps) | Proxy identity + M2M **OR True OBO** (with UI User Authorization + `sql` scope) | App SP (M2M) or User token (OBO SQL) | `X-Forwarded-Email` (M2M); Token `sub` claim (OBO) | SP UUID (M2M); **User email** (OBO SQL) | SP groups (M2M); User groups (OBO SQL) | **Manual** `WHERE col = caller` (M2M); **Automatic** row filters fire as user (OBO SQL) | **SP UUID** (M2M); **User email** (OBO SQL) |
| 8 | **UC Functions** (via M2M SQL) | Pure M2M | App SP | None (or passed as function arg) | SP UUID | SP groups | SP | SP UUID |
| 9 | **UC Functions** (via Genie OBO) | True OBO | User's token (Genie forwards) | Token `sub` claim | User email | Genie service context | User | User |
| 10 | **Vector Search** | Pure M2M | App SP | None | N/A (no SQL) | N/A | N/A | SP UUID |
| 11 | **Foundation Model API** | Pure M2M or OBO | SP or user token | Not relevant for inference | N/A | N/A | N/A | Caller identity |
| 12 | **SDP / Lakeflow Pipeline** (serverless) | Delegated | Pipeline owner's identity | Pipeline config | Owner email | Owner groups | Owner | Owner |
| 13 | **External MCP** (shared bearer via UC HTTP) | M2M at proxy | SP or user at Databricks proxy; shared API key at external service | Shared credential at external service | N/A | N/A | N/A | Caller at proxy. **Governance boundary**: `USE CONNECTION` grant controls who can invoke. MCP server needs zero data permissions — UC manages credentials. |
| 14 | **External MCP** (per-user OAuth via UC HTTP) | OBO at proxy | User token at Databricks proxy; user's external OAuth at external service | Individual user at external service | N/A | N/A | N/A | User at proxy. **Governance boundary**: `USE CONNECTION` grant controls who can invoke. MCP server needs zero data permissions. |
| 15 | **Custom MCP → Custom MCP** (chained) | Proxy identity + M2M | Downstream SP | `X-Forwarded-Email` (passthrough, all intermediate proxies auth-disabled) | SP UUID | SP groups | **Manual** | **SP UUID** |
| 16 | **Lakebase** (online tables) | TBD — not yet GA | Expected: SP or user token for serving endpoint queries | Expected: same as Model Serving | TBD | TBD | TBD | TBD |

### Audit gap summary

| Identity model | UC audit captures human? | Application-plane audit required? |
|---|---|---|
| True OBO (#1, 2, 3, 4, 5, 9) | **Yes** — automatic | Optional (enrichment) |
| Proxy identity + M2M (#7, 15) | **No** — shows SP UUID. **SOLVABLE**: With UI User Authorization + `sql` scope, OBO SQL causes `current_user()` to return the human email and UC audit records the human identity directly. | **Required** for M2M path — only way to tie SP action to human. **Not required** when using OBO SQL via UI User Auth. |
| Pure M2M (#6, 8, 10, 11) | **No** — shows SP UUID | **Required** if per-user attribution matters |
| Delegated (#3, 12) | **Yes** — but shows owner, not end user | Depends on use case |
| External MCP (#13, 14) | N/A — external service | **Required** — Databricks audit shows proxy call, not external action |

---

## 4. OAuth Scopes — Complete Reference

### All known scopes

| Scope | What it grants | Required by | In `user_authorized_scopes`? | Gotcha |
|---|---|---|---|---|
| `openid` | OIDC identity token issuance | All OAuth flows | No (platform-managed) | Required for any OAuth flow to work |
| `email` | Email claim in identity token | Proxy `X-Forwarded-Email` injection | No | Without this, proxy may not set email header |
| `profile` | Display name, preferred username claims | Proxy `X-Forwarded-Preferred-Username` | No | Informational |
| `offline_access` | Refresh token issuance | Long-lived sessions | No (platform-managed) | Without this, user must re-authenticate when access token expires |
| `iam.current-user:read` | `GET /api/2.0/preview/scim/v2/Me` | Identity verification | No | Identity only — cannot modify anything |
| `iam.access-control:read` | Read access control lists | ACL inspection | No | Rarely needed by apps |
| `dashboards.genie` | Genie space access (UI + API) | Genie Conversation API | **Yes** | Must pair with `genie` scope on Azure |
| `genie` | Genie Conversation API | Genie Conversation API (Azure) | **Yes** | **Not shown in account UI** but required on Azure. Discovered empirically. Without it: silent 403. |
| `model-serving` | Model Serving / Agent Bricks endpoint invocation | Agent Bricks supervisor, FM API OBO calls | **Yes** | — |
| `sql` | Statement Execution API | Direct SQL execution with user token | **Yes** | **Two configuration mechanisms**: (1) **CLI `user_authorized_scopes`** — adds to OAuth integration but historically did NOT embed in JWT. (2) **UI User Authorization (Public Preview)** — configure via Apps UI "User authorization" panel; this DOES produce a real OBO JWT with `sql` in the scope claim. **Working via UI path.** Track configured scopes via `effective_user_api_scopes` on the app object. |
| `unity-catalog` | UC REST API operations + UC External MCP proxy | External MCP via UC HTTP connections (`/api/2.0/mcp/external/...`). Also required for UC External MCP Proxy — the third proxy type that manages credential lifecycle for external services. | **Yes** | **Undocumented requirement.** Proxy checks this scope before validating `USE CONNECTION`. Without it: `403 "does not have required scopes: unity-catalog"`. |
| `all-apis` | Catch-all for Databricks REST APIs not covered by specific scopes | General API access | **Yes** | Broadest scope — grants access to any workspace API |

### Per-service minimum scopes

| Service | Minimum scopes on user token | Notes |
|---|---|---|
| **Custom MCP** (identity only, M2M for data) | `openid`, `email`, `profile`, `offline_access` | User token only proves identity. SP does all data access. **Least privilege.** |
| **Genie** | + `dashboards.genie`, `genie` | Both required on Azure |
| **Agent Bricks / Model Serving** | + `model-serving` | Token forwarded to supervisor |
| **External MCP** (UC HTTP connections) | + `unity-catalog` | Proxy validates this scope before checking `USE CONNECTION` |
| **Direct SQL** (user token) | + `sql` | **Working via UI User Authorization** — configure `sql` scope through the Apps UI "User authorization" panel. CLI-only `user_authorized_scopes` path remains unreliable. |
| **Full-featured app** (all services) | All scopes above + `all-apis` | AuthZ Showcase uses this |

### Bare minimum for a Claude Code MCP integration

```json
{
  "scopes": ["openid", "email", "profile", "offline_access"],
  "user_authorized_scopes": []
}
```

This token can:
- Authenticate the user at the proxy → `X-Forwarded-Email` is set
- Refresh without re-login

This token **cannot**:
- Call Genie, Agent Bricks, Statement Execution, or any other Databricks API
- Access UC objects directly
- Be used as a credential for anything beyond proving identity

All data access is M2M via the app SP.

---

## 5. User/OAuth Journey — Sequence Diagram

### First-time authentication (Claude Code → Custom MCP)

```
┌─────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌─────────┐
│  Claude  │  │mcp-remote│  │  Databricks  │  │  Browser  │  │Custom   │
│  Code    │  │  (npx)   │  │  OIDC/OAuth  │  │  (user)   │  │MCP App  │
└────┬─────┘  └────┬─────┘  └──────┬───────┘  └─────┬─────┘  └────┬────┘
     │             │               │                 │              │
     │  spawn      │               │                 │              │
     ├────────────>│               │                 │              │
     │             │               │                 │              │
     │             │  PKCE auth    │                 │              │
     │             │  request      │                 │              │
     │             ├──────────────>│                 │              │
     │             │               │                 │              │
     │             │  Open browser │ redirect to     │              │
     │             │  localhost:   │ workspace login  │              │
     │             │  3000/callback│                 │              │
     │             ├──────────────>├────────────────>│              │
     │             │               │                 │              │
     │             │               │  User logs in   │              │
     │             │               │  (SSO/password) │              │
     │             │               │<────────────────┤              │
     │             │               │                 │              │
     │             │               │  Authorization  │              │
     │             │               │  code → token   │              │
     │             │               │  Scopes: openid │              │
     │             │               │  email profile  │              │
     │             │               │  offline_access │              │
     │             │<──────────────┤                 │              │
     │             │               │                 │              │
     │             │  Token cached locally           │              │
     │             │  (~/.mcp-auth or similar)       │              │
     │             │               │                 │              │
     │  MCP tool   │               │                 │              │
     │  call       │               │                 │              │
     ├────────────>│               │                 │              │
     │             │                                 │              │
     │             │  POST /mcp                      │              │
     │             │  Authorization: Bearer {token}  │              │
     │             ├────────────────────────────────────────────────>│
     │             │                                                │
     │             │         ┌──────────────────────────┐           │
     │             │         │ Databricks Apps Proxy    │           │
     │             │         │ (authorization: enabled) │           │
     │             │         │                          │           │
     │             │         │ Validates Bearer token   │           │
     │             │         │ Strips Authorization hdr │           │
     │             │         │ Injects:                 │           │
     │             │         │  X-Forwarded-Email:      │           │
     │             │         │   alice@acme.com         │           │
     │             │         │  X-Forwarded-User:       │           │
     │             │         │   12345@workspace_id     │           │
     │             │         └──────────────────────────┘           │
     │             │                                                │
     │             │                              ExtractTokenMiddleware
     │             │                              reads X-Forwarded-Email
     │             │                              → _caller_email()
     │             │                              → "alice@acme.com"
     │             │                                                │
     │             │                              M2M: WorkspaceClient()
     │             │                              SQL: WHERE rep_email
     │             │                                = 'alice@acme.com'
     │             │                                                │
     │             │                              @audited decorator
     │             │                              writes to audit table:
     │             │                              caller=alice, tool=X,
     │             │                              sp=<SP_UUID>
     │             │                                                │
     │             │  JSON-RPC response                             │
     │             │<───────────────────────────────────────────────┤
     │  result     │                                                │
     │<────────────┤                                                │
```

### Subsequent calls (token cached)

```
Claude Code → mcp-remote (reads cached token) → POST /mcp with Bearer
→ Proxy validates → injects X-Forwarded-Email → app processes
→ Token refresh happens automatically (offline_access scope)
```

### Token refresh (invisible to user)

```
mcp-remote detects expired access token
→ sends refresh_token to token endpoint
→ gets new access_token (same scopes as original grant)
→ continues with new token
```

**Critical**: Changing scopes on the OAuth integration does NOT affect existing refresh tokens. New scopes require a full app delete+recreate to force new authorization code flows. This is a platform behavior, not a bug. See `AUTHZ-PATTERNS.md § OAuth Integration Reset`.

---

## 6. Product Gaps — With Evidence

### GAP 1: M2M audit trail loses human identity — SOLVABLE via OBO SQL

**Status**: **SOLVABLE.** With UI User Authorization (Public Preview) + `sql` scope configured, Custom MCP apps can execute OBO SQL where `current_user()` returns the human email. UC audit then records the human identity directly, closing this gap for services that use the OBO SQL path.

**Evidence**: `system.access.audit` records `user_identity.email` as the SQL session identity. For M2M queries, this is the SP UUID.

```sql
-- What UC audit actually shows for an M2M query:
SELECT event_time, user_identity.email, action_name, service_name
FROM system.access.audit
WHERE service_name = 'unityCatalog'
  AND event_time > current_timestamp() - INTERVAL 1 HOUR;

-- Result (M2M path):
-- event_time              | user_identity.email           | action_name    | service_name
-- 2026-03-10 14:32:01     | <sp-uuid>                     | commandSubmit  | unityCatalog
--                         ↑ SP UUID, not human email

-- Result (OBO SQL via UI User Auth):
-- event_time              | user_identity.email           | action_name    | service_name
-- 2026-03-10 14:32:01     | user@example.com              | commandSubmit  | unityCatalog
--                         ↑ Human email — gap closed
```

**Affected services (M2M path only)**: Custom MCP (#7 when not using OBO SQL), UC Functions via M2M (#8), Vector Search (#10), any M2M SQL path (#6).

**Databricks docs confirm**: System tables record the executing identity. There is no built-in mechanism to attach a "requested by" field to `system.access.audit` entries. See: [Databricks audit log schema](https://docs.databricks.com/en/administration-guide/account-settings/audit-log-delivery.html).

### GAP 2: No platform-built join between MLflow traces and UC audit

**Evidence**: `mlflow.traces` and `system.access.audit` are separate system tables with no foreign key relationship. The join requires matching on SP UUID + time window — an approximation, not a precise correlation.

**Fieldkit documents this**: `governance/ai-governance.md § GAP 2`: "No platform-built join between MLflow traces and system.access.audit. Every team must build the join query independently."

### GAP 3: `sql` scope in JWT — RESOLVED (configuration issue, not platform bug)

**Status**: **RESOLVED.** The `sql` scope works when configured through the UI User Authorization panel (Public Preview) rather than solely through the CLI `user_authorized_scopes` field.

**Original evidence** (CLI path): Adding `sql` to `user_authorized_scopes` in the OAuth integration did not result in the `sql` claim appearing in the JWT `scope` field. The platform issued a minimal OIDC identity token regardless.

```python
# CLI-configured token — minimal OIDC, no sql scope:
{
  "scope": "offline_access email iam.current-user:read openid iam.access-control:read profile",
  # NO "sql" — even though sql is in user_authorized_scopes
}
```

**Resolution**: Configure `sql` scope via the Databricks Apps UI "User authorization" panel. The resulting `X-Forwarded-Access-Token` is a real OBO JWT with the `sql` scope claim. Track configured scopes via `effective_user_api_scopes` on the app object. This enables true OBO SQL: `current_user()` returns the human email, row filters fire as the user, and UC audit records the human identity.

**Impact**: True OBO SQL (user token → Statement Execution API) IS available for Databricks Apps when UI User Authorization is configured. The M2M workaround (manual WHERE clause) is no longer the only option.

**Fieldkit documents this**: `auth/obo-passthrough.md § sql scope gotcha`.

### GAP 4: `is_member()` broken in OBO contexts through Genie/Agent Bricks — needs re-test

**Status**: Confirmed broken under Genie/Agent Bricks OBO contexts. **Needs re-test under UI User Authorization** — when OBO SQL is executed with a real user JWT (via UI User Auth + `sql` scope), `is_member()` may correctly evaluate the user's workspace groups since the SQL session identity is the actual user, not a service identity.

**Evidence**: `is_member()` in a row filter or column mask evaluates the SQL **execution identity** (Genie service, Agent Bricks runtime), not the OBO caller's workspace groups.

```sql
-- This row filter does NOT work correctly under Genie OBO:
CREATE FUNCTION mask_quota(val DECIMAL)
  RETURNS DECIMAL
  RETURN IF(is_member('executives'), val, NULL);
-- is_member() evaluates Genie service groups, not the user's groups
```

**Workaround**: Use `current_user()` + allowlist table lookup instead of `is_member()`.

**Fieldkit documents this**: `auth/overview.md § is_member() vs current_user()`, `governance/ai-governance.md § Governing Principle P8`.

### GAP 5: `unity-catalog` scope requirement for External MCP — undocumented

**Evidence**: Calling `/api/2.0/mcp/external/{connection_name}` without the `unity-catalog` scope returns `403: "Provided OAuth token does not have required scopes: unity-catalog"`. This scope is not mentioned in the External MCP documentation.

**Fieldkit documents this**: `mcp/external-mcp.md § Gotchas`, `auth/obo-passthrough.md § unity-catalog scope gotcha`.

### GAP 6: Token scope refresh requires full app rebuild

**Evidence**: Adding scopes to an existing OAuth integration does not propagate to existing refresh tokens. Users must re-authorize via a new authorization code flow. The only reliable way to force this: delete and recreate the entire Databricks App (which creates a new OAuth integration, new SP, new client_id).

**Impact**: Every scope change is a destructive operation that requires re-granting the new SP's UC access.

**Fieldkit documents this**: `AUTHZ-PATTERNS.md § OAuth Integration Reset`.

### GAP 7: `authorization: disabled` cannot serve both app-to-app and external clients

**Evidence**: See `PROXY-ARCHITECTURE.md § The tradeoff`. App-to-app calls need auth disabled (to preserve upstream token). External clients need auth enabled (to trigger proxy identity injection). No single setting works for both.

### GAP 8½: Connection owner has implicit `USE CONNECTION` — no explicit grant required

**Evidence**: The owner of a UC HTTP connection (the principal that created it) has implicit `USE CONNECTION` permission. This means the connection owner can invoke External MCP tools without an explicit `GRANT USE CONNECTION`. This is consistent with UC ownership semantics but is worth noting because it means the governance boundary (`USE CONNECTION`) does not appear in `SHOW GRANTS` for the owner — making access audits incomplete if you only check explicit grants.

**Impact**: When auditing who can access an External MCP server, you must check both explicit `USE CONNECTION` grants AND connection ownership.

### GAP 9: Lakebase data-plane query audit undocumented

**What's documented**: Lakebase has a comprehensive identity and access control story:

- **Authentication**: Two methods — (1) **OAuth tokens** (workspace-scoped, 1-hour expiry, U2M + M2M, via `generate-database-credential`); (2) **Native Postgres passwords** (no auto-expiry, manual rotation). Identity mapped to Postgres role via `databricks_auth` extension.
- **Identity**: `current_user` returns the Databricks email (e.g., `user@databricks.com`) — confirmed in docs.
- **Row-Level Security**: Postgres-native RLS via `CREATE POLICY ... USING (...)`. Patterns include user ownership (`assigned_to = current_user`), tenant isolation, team membership, and role-based access via `pg_has_role()`. When RLS is enabled, all rows are hidden by default — policies grant access. This is the Postgres equivalent of UC row filters.
- **Data API**: PostgREST-compatible REST interface. `authenticator` role assumes the user's Postgres role per request. RLS automatically enforced on all API requests.
- **Management audit**: Captured in `system.access.audit` under service `databaseInstances` (15 actions: instance CRUD, catalog registration, table CRUD, synced tables, ACL changes).

**What remains undocumented**: Data-plane Postgres SQL query audit only — do SELECT/INSERT/UPDATE/DELETE on Lakebase tables appear in `system.access.audit`? If so, what identity is recorded?

**References**: [Lakebase Authentication](https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/authentication) | [Lakebase Data API & RLS](https://learn.microsoft.com/en-us/azure/databricks/oltp/projects/data-api) | [Lakebase Audit Events](https://learn.microsoft.com/en-us/azure/databricks/admin/account-settings/audit-logs#-lakebase-events)

---

## 7. Confused Deputy Prevention — SP Isolation Strategy

### The problem

A **confused deputy** attack occurs when a trusted entity (the app SP) is tricked into using its authority on behalf of an unauthorized caller. In Databricks Apps context:

- A single SP with `SELECT` on sensitive tables + `MODIFY` on approval tables is a confused deputy waiting to happen
- If that SP is shared across a read-only dashboard AND a write-capable MCP server, the dashboard's SP credentials can be exploited to write data
- If the same SP serves both the Streamlit app and the custom MCP server, a vulnerability in either app exposes the other's capabilities
- An attacker who compromises one tool's input can leverage the SP's full privilege set across all tools

### The principle: One SP per capability boundary

**From Fieldkit `governance/ai-governance.md`**: "Every deployed agent is a Service Principal. One SP per capability boundary — not one SP per application. An agent that does read-only deal analysis and an agent that submits deal approvals must have different SPs."

This means: **do NOT use the same SP** for the Streamlit app and the custom MCP server. They are separate Databricks Apps with separate SPs by default — this is correct. The risk is when you manually grant the same privileges to both, or share credentials.

### SP isolation matrix for the AuthZ Showcase

| App / Component | SP | Read capabilities | Write capabilities | Why separate |
|---|---|---|---|---|
| **Streamlit app** (`authz-showcase`) | SP-A | Genie (OBO), VS indexes, UC Functions, FM API | None (all writes go through MCP or Agent Bricks) | Frontend — should never have direct write access to data |
| **Custom MCP server** (`authz-showcase-custom-mcp`) | SP-B | `opportunities`, `quota_viewers`, `customers` | `approval_requests` (INSERT only) | MCP tools need MODIFY on approval_requests; Streamlit app does not |
| **Claude Code MCP** (`authz-mcp-external`) | SP-C | Same read tables as SP-B | Same write tables as SP-B | Separate from SP-B because: different `authorization` setting, different OAuth integration, different scope, independent lifecycle |
| **Agent Bricks supervisor** | SP-D (auto-managed by Model Serving) | Sub-agents inherit user token (OBO) | Through sub-agent tools only | Supervisor SP is platform-managed; sub-agent access = user's access |

### Correct grant scoping

```sql
-- SP-A (Streamlit app): READ-ONLY on shared data, EXECUTE on functions
GRANT USE CATALOG ON CATALOG authz_showcase TO `<SP-A>`;
GRANT USE SCHEMA  ON SCHEMA  authz_showcase.sales TO `<SP-A>`;
GRANT USE SCHEMA  ON SCHEMA  authz_showcase.functions TO `<SP-A>`;
GRANT SELECT      ON TABLE   authz_showcase.sales.sales_reps TO `<SP-A>`;
GRANT EXECUTE     ON FUNCTION authz_showcase.functions.get_rep_quota TO `<SP-A>`;
GRANT EXECUTE     ON FUNCTION authz_showcase.functions.calculate_attainment TO `<SP-A>`;
GRANT EXECUTE     ON FUNCTION authz_showcase.functions.recommend_next_action TO `<SP-A>`;
-- NO MODIFY grants. NO SELECT on approval_requests.
-- SP-A can query via Genie (OBO) or UC Functions, but cannot write data.

-- SP-B (Custom MCP for Streamlit): READ + targeted WRITE
GRANT USE CATALOG ON CATALOG authz_showcase TO `<SP-B>`;
GRANT USE SCHEMA  ON SCHEMA  authz_showcase.sales TO `<SP-B>`;
GRANT SELECT      ON TABLE   authz_showcase.sales.opportunities TO `<SP-B>`;
GRANT SELECT      ON TABLE   authz_showcase.sales.quota_viewers TO `<SP-B>`;
GRANT SELECT      ON TABLE   authz_showcase.sales.customers TO `<SP-B>`;
GRANT SELECT      ON TABLE   authz_showcase.sales.approval_requests TO `<SP-B>`;
GRANT MODIFY      ON TABLE   authz_showcase.sales.approval_requests TO `<SP-B>`;
-- MODIFY only on approval_requests. Cannot touch opportunities, customers, etc.

-- SP-C (Claude Code MCP): SAME read/write as SP-B but independent SP
-- (identical grants — separate SP for lifecycle isolation)
GRANT USE CATALOG ON CATALOG authz_showcase TO `<SP-C>`;
GRANT USE SCHEMA  ON SCHEMA  authz_showcase.sales TO `<SP-C>`;
GRANT SELECT      ON TABLE   authz_showcase.sales.opportunities TO `<SP-C>`;
GRANT SELECT      ON TABLE   authz_showcase.sales.quota_viewers TO `<SP-C>`;
GRANT SELECT      ON TABLE   authz_showcase.sales.customers TO `<SP-C>`;
GRANT SELECT      ON TABLE   authz_showcase.sales.approval_requests TO `<SP-C>`;
GRANT MODIFY      ON TABLE   authz_showcase.sales.approval_requests TO `<SP-C>`;

-- Audit table: ALL MCP SPs need write access
GRANT USE SCHEMA  ON SCHEMA  authz_showcase.audit TO `<SP-B>`;
GRANT MODIFY      ON TABLE   authz_showcase.audit.tool_invocations TO `<SP-B>`;
GRANT USE SCHEMA  ON SCHEMA  authz_showcase.audit TO `<SP-C>`;
GRANT MODIFY      ON TABLE   authz_showcase.audit.tool_invocations TO `<SP-C>`;
-- SP-A does NOT get audit write — it doesn't invoke MCP tools directly
```

### What confused deputy prevention buys you

| Scenario | Single shared SP | Isolated SPs |
|---|---|---|
| Streamlit app compromised | Attacker has MODIFY on approval_requests | SP-A has no MODIFY — attack surface limited to read-only |
| MCP tool injection (e.g., malicious `opp_id` input) | Same SP has access to all tables across all apps | SP-B only has grants on specific tables; blast radius contained |
| Claude Code session hijacked | Shares credentials with production Streamlit app | SP-C is independent; revoking it doesn't affect the demo app |
| Need to rotate credentials | Must rotate for all apps simultaneously | Rotate per-app; others unaffected |
| Audit investigation | All M2M queries show same SP UUID — can't tell which app | Different SP UUIDs in `system.access.audit` — immediate attribution to app |

### Anti-patterns to avoid

| Anti-pattern | Why it's dangerous | Correct approach |
|---|---|---|
| Sharing `DATABRICKS_CLIENT_ID/SECRET` across apps via env vars | One credential compromise = all apps compromised | Each `databricks apps create` auto-generates a unique SP. Never copy credentials. |
| Granting `ALL PRIVILEGES` on a catalog to an SP | SP can do anything — read, write, drop, grant | Grant only specific object-level permissions |
| Using the same SP for read and write tools | A read-only tool vulnerability becomes a write exploit | Separate SPs per capability boundary, or use UC Functions as write gates |
| Re-using the main app's OAuth integration for external clients | Scope changes affect production users | Separate OAuth integration per deployment target |
| Adding the MCP SP to admin groups | SP bypasses all row filters and column masks | SP should only be in groups that match its declared capabilities |

### Verifying SP isolation

```bash
# List all grants for each SP — should show minimal, non-overlapping sets
for SP in "<SP-A>" "<SP-B>" "<SP-C>"; do
  echo "=== Grants for $SP ==="
  databricks sql execute "SHOW GRANTS ON CATALOG authz_showcase TO \`$SP\`" \
    --warehouse <warehouse-id> --profile <db-profile>
  databricks sql execute "SHOW GRANTS TO \`$SP\`" \
    --warehouse <warehouse-id> --profile <db-profile>
done
```

---

## 8. What the Platform Provides Today

### System tables — complete inventory

#### Access and audit

| Table | What it records | Identity field | Useful for |
|---|---|---|---|
| `system.access.audit` | All UC operations, SQL executions, API calls, app lifecycle | `user_identity.email` (executing identity) | Primary audit trail. Services: `genieService`, `vectorSearchService`, `sqlStatements`, `apps`, `unityCatalog`, `mlflowModelRegistry` |
| `system.access.table_lineage` | Table-level data flow (source → target) | Source/target table metadata | Understanding data flow through pipelines and agents |
| `system.access.column_lineage` | Column-level data flow | `source_column_name`, `target_column_name` | PII propagation tracking (e.g., did SSN flow to a public table?) |

#### Governance metadata (information_schema)

| Table | What it records | Useful for |
|---|---|---|
| `system.information_schema.column_tags` | Column-level tags (including auto-classified PII) | ABAC policies, data classification audit |
| `system.information_schema.table_tags` | Table-level tags | Tag-based access control |
| `system.information_schema.schema_tags` | Schema-level tags | Governance taxonomy |
| `system.information_schema.catalog_tags` | Catalog-level tags | Same |
| `system.information_schema.column_masks` | Applied column mask functions | Verify masks are applied to sensitive columns |
| `system.information_schema.metastore_summary` | Metastore ID, storage root, region | Environment inventory |
| `system.information_schema.metastore_privileges` | Metastore admin grants | Privilege escalation detection |
| `system.information_schema.external_location_privileges` | Grants on external storage | Storage access audit |
| `system.information_schema.catalogs` | All catalogs with owner and creation info | Ownership tracking |

#### Compute and billing

| Table | What it records | Identity field | Useful for |
|---|---|---|---|
| `system.billing.usage` | DBU consumption and cost | `identity_metadata` | Cost attribution per user/SP/workspace |
| `system.compute.clusters` | Cluster creation and lifecycle events | `creator_user_name` | Cluster ownership, resource tracking |
| `system.lakeflow.job_run_timeline` | Job/pipeline execution history | `run_as` identity | Pipeline owner attribution |

#### MLflow (application plane)

| Table | What it records | Useful for |
|---|---|---|
| `mlflow.traces` | Agent conversation traces with spans | Application-plane audit — what the agent decided, what tools it called |

**Key limitation of `system.access.audit`**: Records the **executing identity** only. For M2M, this is the SP UUID — not the human who triggered it. There is no `requested_by` or `on_behalf_of` field. This is the fundamental gap that necessitates the application-plane audit table.

### MLflow tracing

| Capability | What it provides | How to use for audit |
|---|---|---|
| `mlflow.start_span()` | Create a trace span with name, type, attributes | Set `user_email`, `agent_sp_id` as span tags |
| `mlflow.traces` system table | Query all traces via SQL | Join with `system.access.audit` on SP UUID + time window |
| Span types | `LLM`, `CHAT_MODEL`, `RETRIEVAL`, `TOOL`, `CHAIN`, `AGENT`, `EMBEDDING`, `RERANKER`, `PARSER` | Use `TOOL` for MCP tool calls |
| Autolog | `mlflow.langchain.autolog()`, `mlflow.openai.autolog()`, `mlflow.databricks.autolog()` | Automatic tracing for supported frameworks |
| Trace attributes | Arbitrary key-value tags on spans | Store `caller_email`, `tool_args`, `result_status` |
| `mlflow.search_traces()` | Programmatic trace search | Incident investigation |

**Key limitation**: MLflow trace tags are **convention, not enforced**. There is no platform mechanism to require specific tags on all traces. Teams must self-enforce via code review and the `@audited` decorator pattern.

---

## 8. Proposed Stopgap Solution

### Design goals

1. **Every MCP tool invocation records who (human) asked for what (tool + args) via which agent (SP)**
2. **Records are immutable** (Delta table with append-only semantics + change data feed)
3. **Joinable** with `system.access.audit` via SP UUID + time window
4. **Joinable** with `mlflow.traces` via trace_id (when available)
5. **Extensible** — new services (Lakebase, new MCP tools) add rows, not schema changes
6. **Zero code changes to tool logic** — decorator pattern wraps existing tools

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  APPLICATION PLANE (you build)                               │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  authz_showcase.audit.tool_invocations              │    │
│  │  (Delta table, append-only, CDC enabled)            │    │
│  │                                                     │    │
│  │  caller_email      ← X-Forwarded-Email              │    │
│  │  caller_user_id    ← X-Forwarded-User               │    │
│  │  caller_display    ← X-Forwarded-Preferred-Username  │    │
│  │  app_sp_id         ← DATABRICKS_CLIENT_ID           │    │
│  │  app_name          ← APP_NAME env var               │    │
│  │  service_type      ← "custom_mcp" | "uc_function"   │    │
│  │  tool_name         ← function name                  │    │
│  │  tool_args_hash    ← SHA-256 of sanitized args      │    │
│  │  tool_args_safe    ← sanitized JSON (no secrets)    │    │
│  │  result_status     ← "success" | "error" | "denied" │    │
│  │  error_message     ← error detail (if any)          │    │
│  │  trace_id          ← MLflow trace ID (if available) │    │
│  │  request_id        ← UUID per invocation            │    │
│  │  event_time        ← server timestamp               │    │
│  │  duration_ms       ← wall-clock execution time      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  MLflow Traces (platform-managed)                    │    │
│  │  Tags: user_email, agent_sp_id, session_id           │    │
│  │  Spans: TOOL type per tool call                      │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
              JOIN ON: app_sp_id + time window
              JOIN ON: trace_id (precise, when available)
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  DATA PLANE (platform-managed)                               │
│                                                             │
│  system.access.audit                                         │
│  user_identity.email = SP UUID for M2M queries              │
│  action_name, request_params, service_name, event_time      │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

#### Step 1: Create the audit table

```sql
CREATE SCHEMA IF NOT EXISTS authz_showcase.audit;

CREATE TABLE IF NOT EXISTS authz_showcase.audit.tool_invocations (
  -- WHO triggered it (human identity from proxy)
  caller_email       STRING     NOT NULL   COMMENT 'X-Forwarded-Email — proxy-verified user identity',
  caller_user_id     STRING                COMMENT 'X-Forwarded-User — {user_id}@{workspace_id}',
  caller_display     STRING                COMMENT 'X-Forwarded-Preferred-Username — display name',

  -- WHICH agent executed it (SP identity)
  app_sp_id          STRING     NOT NULL   COMMENT 'DATABRICKS_CLIENT_ID — the SP that ran SQL',
  app_name           STRING     NOT NULL   COMMENT 'Application name for multi-app correlation',

  -- WHAT was done
  service_type       STRING     NOT NULL   COMMENT 'custom_mcp | uc_function | external_mcp | agent_bricks | genie',
  tool_name          STRING     NOT NULL   COMMENT 'Tool/function name invoked',
  tool_args_hash     STRING                COMMENT 'SHA-256 of canonical args JSON — for dedup and correlation',
  tool_args_safe     STRING                COMMENT 'Sanitized JSON args (secrets/PII redacted)',
  result_status      STRING     NOT NULL   COMMENT 'success | error | denied | timeout',
  error_message      STRING                COMMENT 'Error detail if status != success',

  -- CORRELATION keys
  trace_id           STRING                COMMENT 'MLflow trace ID — precise join to mlflow.traces',
  request_id         STRING     NOT NULL   COMMENT 'UUID per invocation — unique across all apps',

  -- TIMING
  event_time         TIMESTAMP  NOT NULL   COMMENT 'Server-side UTC timestamp',
  duration_ms        LONG                  COMMENT 'Wall-clock execution time in milliseconds'
)
USING DELTA
COMMENT 'Application-plane audit log for MCP tool invocations. Joins with system.access.audit on app_sp_id + event_time window.'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.logRetentionDuration' = 'interval 365 days',
  'delta.deletedFileRetentionDuration' = 'interval 365 days'
);

-- Grant the MCP app SP write access
GRANT MODIFY ON TABLE authz_showcase.audit.tool_invocations TO `<mcp-app-sp-uuid>`;
GRANT USE CATALOG ON CATALOG authz_showcase TO `<mcp-app-sp-uuid>`;
GRANT USE SCHEMA ON SCHEMA authz_showcase.audit TO `<mcp-app-sp-uuid>`;
```

#### Step 2: Audit decorator (zero changes to tool logic)

```python
"""audit.py — Drop-in audit decorator for MCP tools."""
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from functools import wraps

APP_SP_ID = os.environ.get("DATABRICKS_CLIENT_ID", "unknown")
APP_NAME = os.environ.get("APP_NAME", "authz-mcp-external")
AUDIT_CATALOG = "authz_showcase"
AUDIT_SCHEMA = "audit"

# Keys to redact from tool_args before logging
_SENSITIVE_KEYS = frozenset({"password", "secret", "token", "api_key", "credential"})


def _sanitize_args(args: dict) -> str:
    """Redact sensitive values from tool arguments."""
    safe = {}
    for k, v in args.items():
        if k.lower() in _SENSITIVE_KEYS:
            safe[k] = "***REDACTED***"
        elif isinstance(v, str) and len(v) > 500:
            safe[k] = v[:500] + "...[truncated]"
        else:
            safe[k] = v
    return json.dumps(safe, default=str, sort_keys=True)


def _args_hash(args: dict) -> str:
    """Deterministic hash of canonical args for dedup/correlation."""
    canonical = json.dumps(args, default=str, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _write_audit_record(
    caller_email: str, caller_user_id: str, caller_display: str,
    service_type: str, tool_name: str, tool_args: dict,
    result_status: str, error_message: str | None,
    trace_id: str | None, request_id: str, duration_ms: int,
):
    """Write one audit record. Fails silently — audit must not break tools."""
    try:
        from server.main import _m2m_client, _run_sql, _safe
        w = _m2m_client()
        safe_args = _sanitize_args(tool_args)
        _run_sql(w, f"""
            INSERT INTO {AUDIT_CATALOG}.{AUDIT_SCHEMA}.tool_invocations
              (caller_email, caller_user_id, caller_display,
               app_sp_id, app_name, service_type, tool_name,
               tool_args_hash, tool_args_safe, result_status, error_message,
               trace_id, request_id, event_time, duration_ms)
            VALUES
              ('{_safe(caller_email)}', '{_safe(caller_user_id)}',
               '{_safe(caller_display)}', '{_safe(APP_SP_ID)}',
               '{_safe(APP_NAME)}', '{_safe(service_type)}',
               '{_safe(tool_name)}', '{_safe(_args_hash(tool_args))}',
               '{_safe(safe_args)}', '{_safe(result_status)}',
               {f"'{_safe(error_message)}'" if error_message else "NULL"},
               {f"'{_safe(trace_id)}'" if trace_id else "NULL"},
               '{_safe(request_id)}', current_timestamp(), {duration_ms})
        """)
    except Exception:
        pass  # Audit failure must never break the tool


def audited(service_type: str = "custom_mcp"):
    """Decorator that wraps any MCP tool with audit logging.

    Usage:
        @mcp.tool()
        @audited()
        def my_tool(arg1: str) -> dict:
            ...

    For UC Functions or other services:
        @audited(service_type="uc_function")
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import uuid as _uuid
            from server.main import _caller_email, _request_headers

            caller = _caller_email()
            headers = _request_headers.get({})
            caller_user_id = headers.get("x-forwarded-user", "")
            caller_display = headers.get("x-forwarded-preferred-username", "")
            request_id = str(_uuid.uuid4())

            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.monotonic() - start) * 1000)

                status = "error" if isinstance(result, dict) and "error" in result else "success"
                error_msg = result.get("error") if status == "error" else None

                _write_audit_record(
                    caller, caller_user_id, caller_display,
                    service_type, func.__name__, kwargs,
                    status, error_msg, None, request_id, duration_ms,
                )
                return result
            except Exception as e:
                duration_ms = int((time.monotonic() - start) * 1000)
                _write_audit_record(
                    caller, caller_user_id, caller_display,
                    service_type, func.__name__, kwargs,
                    "error", str(e), None, request_id, duration_ms,
                )
                raise
        return wrapper
    return decorator
```

#### Step 3: Apply to tools (one-line change per tool)

```python
@mcp.tool()
@audited()
def get_deal_approval_status(opp_id: str) -> dict:
    # ... existing logic unchanged ...

@mcp.tool()
@audited()
def submit_deal_for_approval(opp_id: str, justification: str) -> dict:
    # ... existing logic unchanged ...

@mcp.tool()
@audited(service_type="custom_mcp")  # explicit for clarity
def get_crm_sync_status(customer_id: str) -> dict:
    # ... existing logic unchanged ...
```

#### Step 4: Chain of custody query

```sql
-- Full audit trail: human → tool → SQL → data
-- Joins application plane (your table) with data plane (system.access.audit)

WITH app_events AS (
  SELECT
    request_id,
    caller_email,
    caller_display,
    app_sp_id,
    app_name,
    service_type,
    tool_name,
    tool_args_safe,
    result_status,
    error_message,
    trace_id,
    event_time,
    duration_ms,
    -- Window for joining to UC audit (tool execution ± buffer)
    event_time - INTERVAL 2 SECONDS  AS window_start,
    event_time + INTERVAL 30 SECONDS AS window_end
  FROM authz_showcase.audit.tool_invocations
  WHERE event_time > current_timestamp() - INTERVAL 24 HOURS
),
uc_events AS (
  SELECT
    event_time      AS uc_event_time,
    user_identity.email AS uc_executor,    -- SP UUID for M2M queries
    action_name     AS uc_action,
    request_params  AS uc_params,
    service_name    AS uc_service,
    response.status_code AS uc_status
  FROM system.access.audit
  WHERE event_time > current_timestamp() - INTERVAL 24 HOURS
    AND service_name IN ('unityCatalog', 'sqlStatements', 'databricksSql')
)
SELECT
  a.caller_email                     AS human,
  a.caller_display                   AS human_name,
  a.tool_name                        AS tool,
  a.tool_args_safe                   AS args,
  a.result_status                    AS tool_result,
  a.duration_ms                      AS tool_duration_ms,
  u.uc_action                        AS uc_operation,
  u.uc_executor                      AS uc_identity,
  u.uc_status                        AS uc_status,
  a.event_time                       AS tool_time,
  u.uc_event_time                    AS uc_time,
  a.app_sp_id                        AS agent_sp,
  a.trace_id
FROM app_events a
LEFT JOIN uc_events u
  ON u.uc_executor = a.app_sp_id
  AND u.uc_event_time BETWEEN a.window_start AND a.window_end
ORDER BY a.event_time DESC;
```

**Result example:**

```
human              | tool                       | uc_operation   | uc_identity    | tool_time           | uc_time
alice@acme.com     | get_deal_approval_status   | commandSubmit  | abc-123-sp     | 2026-03-10 14:32:01 | 2026-03-10 14:32:02
alice@acme.com     | submit_deal_for_approval   | commandSubmit  | abc-123-sp     | 2026-03-10 14:33:15 | 2026-03-10 14:33:16
bob@acme.com       | get_crm_sync_status        | commandSubmit  | abc-123-sp     | 2026-03-10 14:35:22 | 2026-03-10 14:35:23
```

UC only knows `abc-123-sp` ran queries. Your audit table proves Alice and Bob triggered them.

---

## 9. Extensibility

### Adding a new MCP tool

One-line decorator. No schema changes:

```python
@mcp.tool()
@audited()
def new_tool(param: str) -> dict:
    ...
```

### Adding a new service type (e.g., Lakebase online table query)

```python
@audited(service_type="lakebase")
def query_online_table(table_name: str, key: str) -> dict:
    ...
```

The `service_type` column differentiates services in the audit table. No schema migration needed.

### Adding Agent Bricks / UC Function audit

Same decorator pattern in any Python-based agent:

```python
# In an Agent Bricks tool function:
@audited(service_type="agent_bricks")
def agent_tool(query: str) -> dict:
    ...

# In a UC Function wrapper:
@audited(service_type="uc_function")
def call_uc_function(func_name: str, args: dict) -> dict:
    ...
```

### Adding external MCP audit

For External MCP via UC HTTP connections (where your app calls `/api/2.0/mcp/external/{conn}`):

```python
@audited(service_type="external_mcp")
def call_external_mcp(connection_name: str, tool: str, args: dict) -> dict:
    ...
```

### Future: Lakebase online tables

When Lakebase is GA, the expected pattern:
- Online table queries via serving endpoints → Model Serving identity model
- If OBO: user token forwarded, `system.access.audit` captures user identity
- If M2M: SP executes, same audit gap as today → use `@audited(service_type="lakebase")`

The audit table schema is service-agnostic. New services add rows with a new `service_type` value, not new columns.

---

## 10. Alert views

```sql
-- Alert: tool invocation by unknown caller (empty email = broken auth)
CREATE OR REPLACE VIEW authz_showcase.audit.alert_missing_identity AS
SELECT * FROM authz_showcase.audit.tool_invocations
WHERE caller_email = '' OR caller_email IS NULL;

-- Alert: high-frequency tool calls from single user (potential abuse)
CREATE OR REPLACE VIEW authz_showcase.audit.alert_high_frequency AS
SELECT caller_email, tool_name, COUNT(*) AS call_count,
       MIN(event_time) AS first_call, MAX(event_time) AS last_call
FROM authz_showcase.audit.tool_invocations
WHERE event_time > current_timestamp() - INTERVAL 1 HOUR
GROUP BY caller_email, tool_name
HAVING COUNT(*) > 50;

-- Alert: write operations (submit_deal_for_approval and future write tools)
CREATE OR REPLACE VIEW authz_showcase.audit.alert_write_ops AS
SELECT * FROM authz_showcase.audit.tool_invocations
WHERE tool_name IN ('submit_deal_for_approval')
  AND result_status = 'success'
ORDER BY event_time DESC;

-- Alert: error rate spike (tool failures)
CREATE OR REPLACE VIEW authz_showcase.audit.alert_error_rate AS
SELECT tool_name,
       COUNT(*) AS total,
       SUM(CASE WHEN result_status = 'error' THEN 1 ELSE 0 END) AS errors,
       ROUND(SUM(CASE WHEN result_status = 'error' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS error_pct
FROM authz_showcase.audit.tool_invocations
WHERE event_time > current_timestamp() - INTERVAL 1 HOUR
GROUP BY tool_name
HAVING error_pct > 10;
```

---

## 11. Why this approach

| Design decision | Rationale |
|---|---|
| **Delta table, not logs** | Queryable, joinable, governed by UC. Logs are unstructured and harder to correlate. |
| **Append-only with CDC** | Immutable audit trail. Change data feed enables downstream consumers (alerting, dashboards). |
| **`@audited` decorator** | Zero changes to tool logic. Separation of concerns. Add/remove audit without touching business code. |
| **`service_type` column** | Extensible to any service without schema migration. Filter by service in queries. |
| **`tool_args_hash`** | Enables dedup and correlation without logging full args (which may be large or sensitive). |
| **`trace_id` column** | Precise join to MLflow traces when available. Falls back to SP UUID + time window otherwise. |
| **Silent failure on audit write** | Audit must never break the tool. A failed audit INSERT must not return an error to the user. Log the failure separately. |
| **365-day retention** | Compliance-grade retention. Adjust per policy. |

---

## 12. What's NOT solved (honest limitations)

| Limitation | Impact | Mitigation |
|---|---|---|
| **Time-window join is approximate** (M2M path only) | If two users call the same tool within 30 seconds via the same SP, the UC audit events may be attributed to the wrong user | Use `trace_id` for precise join when MLflow tracing is available. **Better**: use OBO SQL via UI User Authorization — UC audit records the human email directly, eliminating the need for time-window joins. |
| **Audit table requires SP write access** | The SP must have MODIFY on the audit table — an additional privilege | This is a dedicated audit table, not production data. The SP already has MODIFY on `approval_requests`. |
| **No platform enforcement of required tags** | MLflow trace tags are convention-based. A developer can ship without `user_email` tag. | The `@audited` decorator makes it automatic. Code review catches tools without the decorator. |
| **External MCP audit is one-sided** | Your audit table records that Alice called the GitHub MCP tool. It does NOT record what GitHub returned or what actions were taken at GitHub. | For per-user OAuth connections, GitHub has its own audit log tied to the user. For shared bearer, the external audit is limited to the shared identity. |
| **Lakebase audit is speculative** | Lakebase is not GA. The audit pattern may differ from what's described here. | The `service_type` column makes it trivial to add once the identity model is confirmed. |

---

## Related documents

| Document | What it covers |
|---|---|
| `PROXY-ARCHITECTURE.md` | How the proxy works, header injection, `authorization: disabled`, external client tradeoffs |
| `AUTHZ-PATTERNS.md` | Token map, OBO patterns, scope reference, OAuth integration lifecycle |
| `README.md` | AuthZ Showcase tab overview, architecture diagram |
| `DEMO-GUIDE.md` | Full demo walkthrough, audit query examples |
| Fieldkit `governance/ai-governance.md` | Six enforcement layers, governing principles, 8 product gaps, build list |
| Fieldkit `ai/mlflow-tracing.md` | MLflow tracing: autolog, manual spans, span types, system table queries |
| Fieldkit `auth/overview.md` | OBO vs M2M vs PAT decision tree |
| Fieldkit `auth/obo-passthrough.md` | OBO implementation patterns, scope gotchas |
| Fieldkit `governance/unity-catalog.md` | System tables reference (audit, lineage, billing) |
| Fieldkit `governance/data-classification.md` | Auto PII classification + tag-based governance |
| Fieldkit `governance/governed-tags.md` | Tag taxonomy, information_schema tag tables |
| Fieldkit `apps/proxy-architecture.md` | Generalized proxy architecture reference |
