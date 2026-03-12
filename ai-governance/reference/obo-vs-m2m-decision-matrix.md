# OBO vs M2M Decision Matrix

> **Purpose**: Quick decision framework for choosing between On-Behalf-Of (OBO) and Machine-to-Machine (M2M) authentication in Databricks AI applications. Extracted from production experience with the AuthZ Showcase and field deployments.
>
> **Audience**: Field Engineers and Solution Architects making auth pattern decisions.
>
> **Last updated**: 2026-03-12

---

## Table of Contents

1. [Quick Decision Tree](#1-quick-decision-tree)
2. [Detailed Decision Matrix](#2-detailed-decision-matrix)
3. [Audit Implications](#3-audit-implications)
4. [Examples by Service](#4-examples-by-service)
5. [The Hybrid Pattern](#5-the-hybrid-pattern)
6. [Anti-Patterns](#6-anti-patterns)

---

## 1. Quick Decision Tree

```
Does the user need to see ONLY their own data?
  |
  +-- YES --> Does the platform support OBO for this service?
  |            |
  |            +-- YES --> Use OBO
  |            |            Row filters, column masks, ABAC fire as the user.
  |            |            Human email appears in system.access.audit.
  |            |
  |            +-- NO  --> Use Proxy Identity + M2M (hybrid)
  |                         Read X-Forwarded-Email for identity.
  |                         Filter in WHERE clause. Log caller in app audit.
  |
  +-- NO  --> Does everyone see the same data?
               |
               +-- YES --> Use M2M
               |            SP credentials. Shared access. Simpler setup.
               |
               +-- NO  --> You have mixed requirements.
                            Use OBO for user-specific, M2M for shared.
                            See "The Hybrid Pattern" below.
```

---

## 2. Detailed Decision Matrix

| Dimension | OBO | M2M | Proxy Identity + M2M (Hybrid) |
|---|---|---|---|
| **Identity in audit** | Human email | SP UUID | SP UUID (platform) + human email (app-level) |
| **UC row filters** | Fire as the user | Fire as the SP (or not at all) | Must replicate in WHERE clause |
| **UC column masks** | Apply per user | Apply per SP | Must replicate in app logic |
| **Setup complexity** | Moderate -- scopes, UI config | Low -- WorkspaceClient() with no args | Moderate -- middleware + explicit filtering |
| **Token requirements** | User token with correct scopes | SP credentials from env vars | SP credentials + X-Forwarded-Email header |
| **Latency** | Slightly higher (token exchange) | Lowest | Same as M2M |
| **Works in Databricks Apps** | Yes (with UI "User authorization") | Yes | Yes |
| **Works in Model Serving** | Yes (ModelServingUserCredentials) | Yes | N/A (no proxy headers in Model Serving) |
| **Works in custom MCP** | No (two-proxy strips user token) | Yes | Yes (this is the recommended pattern for MCP) |
| **Regulatory audit** | Best -- human visible in platform audit | Worst -- human invisible | Middle -- human visible in app-level audit |

---

## 3. Audit Implications

### What appears in `system.access.audit`

| Pattern | `user_identity.email` in audit | Can you trace back to the human? |
|---|---|---|
| OBO | The human's email (e.g., `alice@company.com`) | Yes, directly |
| M2M | The SP UUID (e.g., `sp-uuid-1234`) | No, without app-level logging |
| Hybrid | The SP UUID for SQL; human email for Genie/Agent Bricks | Partially -- need app-level logging for M2M paths |

### Building the audit trail for M2M paths

When you use M2M and need to know which human triggered the query:

1. **Read `X-Forwarded-Email`** from the proxy-injected header
2. **Log it** in your application audit (MLflow traces, structured logging, or a Delta table)
3. **Include a correlation ID** (e.g., `trace_id`) in both the app log and any SQL comments
4. **Join** app-level audit with `system.access.audit` on timestamp or correlation ID

```python
# Example: app-level audit logging in a custom MCP tool
import logging
logger = logging.getLogger("audit")

@mcp.tool()
def get_deal_status(opp_id: str) -> dict:
    caller = _caller_email()  # from X-Forwarded-Email
    logger.info(f"tool=get_deal_status caller={caller} opp_id={opp_id}")
    # M2M SQL query with explicit per-user filter
    rows = _run_sql(w_m2m, f"""
        SELECT * FROM catalog.schema.opportunities
        WHERE opp_id = '{opp_id}' AND rep_email = '{caller}'
    """)
    ...
```

### OBO SQL unlocks full audit trail

With the `sql` scope configured via the Account Console UI:
- `current_user()` returns the human email (not SP UUID)
- `session_user()` returns the human email
- UC row filters and column masks fire as the human user
- `system.access.audit` records the human email
- The M2M audit gap is solved for SQL queries

---

## 4. Examples by Service

### Genie Space

**Always OBO.** Genie runs queries as the calling user. UC row filters and column masks apply per user. No configuration needed beyond granting access to the Genie Space.

### Agent Bricks / Model Serving Endpoint

| Use case | Recommended pattern |
|---|---|
| User asks a question, response includes their data | OBO -- enable in endpoint config |
| Agent queries a shared knowledge base | M2M (automatic passthrough) |
| Agent calls an external API | Manual credentials |

### Databricks Apps (Streamlit, Gradio, etc.)

| Use case | Recommended pattern |
|---|---|
| App queries Genie on behalf of the user | OBO -- forward X-Forwarded-Access-Token |
| App queries SQL warehouse for user-specific data | OBO SQL (UI scopes) or M2M + WHERE filter |
| App calls a shared Vector Search index | M2M -- WorkspaceClient() with no args |
| App calls a custom MCP server (another Databricks App) | Hybrid -- X-Forwarded-Email + M2M SQL in MCP server |

### Custom MCP Server (Databricks App)

**Always hybrid (Proxy Identity + M2M).** The two-proxy architecture strips the user's token. The MCP server must:
1. Read `X-Forwarded-Email` for user identity
2. Use `WorkspaceClient()` (M2M) for SQL queries
3. Add explicit `WHERE user_email = '{caller}'` filters
4. Log the caller in app-level audit

### UC External MCP Proxy

The UC proxy itself is an access control layer, not an auth pattern choice. Behind it, the MCP server still uses the hybrid pattern. The UC proxy governs who can call the MCP server via `USE CONNECTION`.

---

## 5. The Hybrid Pattern

Most production apps use multiple patterns in a single request:

```
User asks: "What's the approval status of deal OPP-001?"

1. Streamlit app receives request
   - Reads X-Forwarded-Email: alice@company.com     (proxy identity)
   - Reads X-Forwarded-Access-Token: Token A         (user OIDC JWT)

2. App calls Genie for context
   - Uses Token A (OBO)                              --> Pattern 2
   - Genie enforces row filters as alice

3. App calls custom MCP server for deal status
   - MCP server reads X-Forwarded-Email: alice       (proxy identity)
   - MCP server uses WorkspaceClient() for SQL        --> Pattern 1 (M2M)
   - SQL query includes WHERE rep_email = 'alice'     (app-level filter)

4. App calls external CRM API
   - Uses stored API key from Secrets                  --> Pattern 3
```

**Rule of thumb**: Use OBO where the platform supports it. Fall back to hybrid (Proxy Identity + M2M) where it doesn't. Use manual credentials for external services.

---

## 6. Anti-Patterns

| Anti-pattern | Why it fails | Better approach |
|---|---|---|
| Using M2M for all queries and ignoring user identity | No per-user governance; audit trail shows only SP | Use OBO for user-specific data; hybrid for MCP |
| Using OBO everywhere including background jobs | OBO requires a user session; background jobs have no user | Use M2M for background/batch processing |
| Granting the SP `SELECT` on all tables "just in case" | Confused deputy -- any tool bug exposes all data | Grant only on tables the SP's tools actually query |
| Using `ModelServingUserCredentials()` in a Databricks App | Silently falls back to M2M -- no error, just wrong identity | Read `X-Forwarded-Email` + use M2M SQL with WHERE filter |
| Hardcoding elevation checks only in application code | Code changes bypass governance | Combine with UC row filters or group-based USE CONNECTION grants |
| Using `WorkspaceClient(token=user_token)` when SP env vars are set | SDK raises "more than one authorization method" error | Use httpx/requests directly for OBO token calls |

---

## Related Documents

- [Identity and Auth Reference](identity-and-auth-reference.md) -- Complete auth patterns, token flows, scope reference
- [Observability and Audit](observability-and-audit.md) -- Building the two-layer audit trail
- [Authorization Flows](authorization-flows.md) -- UC four-layer access control
- [scenarios/07-AuthZ-SHOWCASE/docs/AUTHZ-BEST-PRACTICES.md](../scenarios/07-AuthZ-SHOWCASE/docs/AUTHZ-BEST-PRACTICES.md) -- Detailed best practices with code examples
