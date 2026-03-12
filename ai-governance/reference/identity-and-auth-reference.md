# Identity and Authentication Reference

> **Purpose**: Canonical reference for authentication patterns, token flows, identity models, and OAuth scopes across all Databricks AI products. Consolidates content from multiple docs into a single source of truth.
>
> **Audience**: Field Engineers, Solution Architects, and Security Reviewers building or evaluating AI applications on Databricks.
>
> **Last updated**: 2026-03-12

---

## Table of Contents

1. [Three Authentication Patterns](#1-three-authentication-patterns)
2. [Token Flows and the Two-Proxy Problem](#2-token-flows-and-the-two-proxy-problem)
3. [Identity Models per Service](#3-identity-models-per-service)
4. [OAuth Scope Reference](#4-oauth-scope-reference)
5. [Identity Fragmentation and Known Gaps](#5-identity-fragmentation-and-known-gaps)
6. [Quick Decision Guide](#6-quick-decision-guide)

---

## 1. Three Authentication Patterns

Every Databricks AI application uses one or more of these three patterns. They are universal across Agent Bricks, Databricks Apps, Genie, and custom MCP servers.

### Pattern 1: Automatic Passthrough (M2M)

The platform issues short-lived credentials for a dedicated service principal tied to declared resources. The SP has least-privilege access scoped to what was declared at agent log time.

- **Token type**: Short-lived SP token (OAuth client credentials)
- **Identity in audit**: Service Principal UUID
- **UC enforcement**: SP-level permissions
- **Use cases**: Batch jobs, automation, background tasks, shared-resource queries
- **Docs**: [OAuth M2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m.html), [Automatic Passthrough](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#automatic-authentication-passthrough)

### Pattern 2: On-Behalf-Of User (OBO)

The agent or app runs as the end user. Unity Catalog enforces row filters, column masks, and ABAC policies per user. The user's identity is preserved in audit logs.

- **Token type**: User token (downscoped per request)
- **Identity in audit**: Human email
- **UC enforcement**: Per-user row filters, column masks, ABAC
- **Use cases**: User-facing apps, per-user data access, Genie queries, agent endpoints
- **Key requirement**: Initialize user-authenticated clients inside `predict()` at request time; declare required scopes
- **Docs**: [OBO Auth](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#on-behalf-of-user-authentication), [OAuth U2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-u2m.html)

### Pattern 3: Manual Credentials

External API keys or SP OAuth credentials stored in Databricks Secrets. Used for services outside the Databricks platform.

- **Token type**: External API key or SP OAuth token
- **Identity in audit**: Depends on external service
- **UC enforcement**: None (external to Databricks)
- **Use cases**: External LLM APIs, external MCP servers, third-party SaaS
- **Docs**: [Manual Auth](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#manual-authentication), [Secrets](https://docs.databricks.com/aws/en/security/secrets/)

### When to Use Each

| Question | Answer |
|---|---|
| User should only see their data? | OBO (Pattern 2) |
| Everyone sees the same data? | M2M (Pattern 1) |
| Need user identity in platform audit? | OBO where possible; app-level audit for M2M paths |
| External API or third-party service? | Manual Credentials (Pattern 3) |
| Background/batch processing? | M2M (Pattern 1) |

---

## 2. Token Flows and the Two-Proxy Problem

### Databricks Apps Token Architecture

When a Databricks App serves a browser user, the platform proxy injects identity headers into every request:

```
User browser
    |  HTTPS + session cookie
    v
[App Envoy Proxy]
    |  injects X-Forwarded-Access-Token (OIDC identity JWT)
    |  injects X-Forwarded-Email (authenticated user email)
    v
app.py (your application code)
```

**Proxy-injected headers** (cannot be forged by calling apps when `user_authorization_enabled: true`):

| Header | Content | Trust level |
|---|---|---|
| `X-Forwarded-Email` | `alice@example.com` | High -- use for identity |
| `X-Forwarded-User` | `{user_id}@{workspace_id}` | High |
| `X-Forwarded-Preferred-Username` | `Alice Example` (display name) | High |
| `X-Forwarded-Access-Token` | Minimal OIDC JWT (iam.* scopes only) | Medium -- identity only, not for all API calls |
| `X-Databricks-Org-Id` | Workspace ID | Informational |

### The Two-Proxy Problem

When a Streamlit app (App A) calls a custom MCP server (App B) and both are Databricks Apps, each has its own proxy:

```
User browser
    |  HTTPS + session cookie
    v
[App A Envoy Proxy]              <-- Proxy 1
    |  injects X-Forwarded-Access-Token (Token A = user OBO token)
    |  injects X-Forwarded-Email (user email)
    v
app.py (Streamlit)
    |  Authorization: Bearer {Token A}   <-- app forwards Token A
    v
[App B Envoy Proxy]              <-- Proxy 2
    |  STRIPS the incoming Authorization header
    |  injects X-Forwarded-Access-Token (Token B = App B SP token)
    |  injects X-Forwarded-Email (user email, derived from Token A)
    v
server/main.py (FastMCP)
    |  Token B sub = MCP SP UUID (NOT the user)
    |  X-Forwarded-Email = correct user email
```

**The problem**: Proxy 2 substitutes its own SP token for the user's token. The MCP server code never sees the user's OBO token.

**The solution**: Use `X-Forwarded-Email` (set by the proxy from the validated incoming token, cannot be forged) for user identity. Use `WorkspaceClient()` (M2M, no args) for SQL queries, with explicit `WHERE user_email = '{caller}'` filter in each query.

### Token A vs Token B

| Token | Issued by | Identity | Usable for |
|---|---|---|---|
| Token A (main app) | Proxy 1 | User (OIDC identity JWT) | Genie API, Agent Bricks, Model Serving (server-side scope validation) |
| Token B (MCP app) | Proxy 2 | App B SP UUID | Same minimal OIDC scopes as Token A; `sub` = SP, not user |

**Key insight**: Using `current_user.me()` with Token B returns the SP identity, not the user.

### The Three-Proxy Path (UC External MCP)

When the MCP server is registered as a UC HTTP Connection, there is a third proxy:

```
User browser
    --> [App Proxy]              checks session, injects Token A + email
    --> app.py                   forwards Token A as Bearer
    --> [UC External MCP Proxy]  checks unity-catalog scope + USE CONNECTION
    --> [MCP App Proxy]          strips Bearer, injects Token B + email
    --> server/main.py           receives Token B (SP) + email (user)
```

The UC proxy adds a governance layer: it validates the `unity-catalog` scope on the calling token and checks `USE CONNECTION` privilege on the caller's identity. Revoking `USE CONNECTION` immediately blocks access.

### What NOT to Use in the MCP Server

- `ModelServingUserCredentials()` -- silently falls back to M2M in Databricks Apps context
- `WorkspaceClient(host=host, token=user_token)` -- SDK raises conflict error if `DATABRICKS_CLIENT_ID/SECRET` env vars are also set
- The `X-Forwarded-Access-Token` for SQL -- the token lacks the `sql` scope claim (unless configured via UI "User authorization")

---

## 3. Identity Models per Service

Each Databricks AI service resolves identity differently. This table shows what identity is visible in `system.access.audit` for each service and auth pattern combination.

| Service | Auth Pattern | Identity in `system.access.audit` | Human Visible? |
|---|---|---|---|
| Genie Space | OBO | Human email | Yes |
| Agent Bricks endpoint | Automatic passthrough | SP UUID | No |
| Agent Bricks endpoint | OBO | Human email | Yes |
| SQL Warehouse (via M2M) | M2M | SP UUID | No |
| SQL Warehouse (via OBO + UI scopes) | OBO | Human email | Yes |
| Vector Search | Automatic passthrough | SP UUID | No |
| UC Functions | Caller identity | Depends on calling context | Depends |
| Custom MCP (direct) | Two-proxy M2M | SP UUID (App B SP) | No |
| Custom MCP (UC proxy) | Three-proxy | Calling identity at UC layer | Partially |
| External APIs | Manual credentials | External service logs | N/A |

**The identity fragmentation problem**: In a single user interaction, `system.access.audit` may show the human email for Genie queries but the SP UUID for M2M SQL queries. There is no platform-built join between these records.

---

## 4. OAuth Scope Reference

> **Verified on Azure Databricks, March 2026.** Add ALL scopes upfront -- missing scopes cause cryptic errors discovered per-feature, not per-project. Extra scopes are harmless.

### Scope Map

| Scope | Required for | Notes |
|---|---|---|
| `dashboards.genie` | Genie Conversation API (all clouds) | Must be in `user_authorized_scopes` |
| `genie` | Genie Conversation API on **Azure** | Undocumented Azure-specific requirement -- UI does not show this scope |
| `model-serving` | Agent Bricks / Model Serving OBO | |
| `sql` | Statement Execution API | Adding via CLI does NOT embed it in the JWT -- use UI "User authorization" or M2M for SQL |
| `unity-catalog` | External MCP proxy `/api/2.0/mcp/external/...` | Undocumented -- proxy checks USE CONNECTION privilege; missing = 403 |
| `all-apis` | General Databricks REST APIs | Catch-all |
| `offline_access`, `email`, `openid`, `profile`, `iam.*` | OIDC identity baseline | Always required |

### CLI Patch Command (Run Once After Any App Create or Delete+Recreate)

```bash
databricks account custom-app-integration update '<integration-id>' \
  --profile <account-profile> \
  --json '{
    "scopes": ["offline_access","email","iam.current-user:read",
               "openid","dashboards.genie","genie","iam.access-control:read",
               "profile","model-serving","sql","all-apis","unity-catalog"],
    "user_authorized_scopes": ["dashboards.genie","genie","model-serving",
                                "sql","all-apis","unity-catalog"]
  }'
```

### Two Configuration Paths for Scopes

| Mechanism | How | Result |
|---|---|---|
| **CLI** `custom-app-integration update` | Sets `user_authorized_scopes` on OAuth integration | Sets scopes in config but does NOT populate `effective_user_api_scopes`. Proxy still issues minimal OIDC identity token. |
| **UI** User Authorization (Preview) | Edit App -> Configure -> User Authorization -> Add Scope | Sets both `user_authorized_scopes` AND `effective_user_api_scopes`. Produces real OBO JWT with service scopes embedded. |

**Always use the UI** for adding scopes when you need them in the token's `scope` claim. The CLI approach alone does not result in service scopes appearing in the `X-Forwarded-Access-Token`.

### UI Scope Names

| UI scope name | What it enables |
|---|---|
| `sql` | OBO SQL via Statement Execution API -- `current_user()` = human email |
| `dashboards.genie` | Genie space access |
| `serving.serving-endpoints` | Model Serving / Agent Bricks OBO (maps to CLI scope `model-serving`) |
| `catalog.connections` | UC HTTP Connection access |
| `catalog.catalogs:read` | Read-only UC catalog access |
| `files.files` | File and directory access |

### Scope Behavior: Why Some APIs Work and Some Don't

The `X-Forwarded-Access-Token` is an OIDC identity token, not a full API token:

| API | Scope check | Works with identity token? |
|---|---|---|
| SCIM `Me` endpoint | Server-side, `iam.current-user:read` in token | Yes |
| Genie Conversation API | Server-side only | Yes |
| Agent Bricks / Model Serving | Server-side only | Yes |
| Statement Execution API | JWT `scope` claim must contain `sql` | No (CLI config) / Yes (UI config) |
| External MCP proxy | JWT `scope` claim must contain `unity-catalog` | Yes if in `user_authorized_scopes` |

### OAuth Integration Reset

Adding a scope to `user_authorized_scopes` does NOT affect existing refresh tokens. When the Apps proxy refreshes an access token, the new access token inherits the original scopes from the authorization code grant -- not the current integration configuration. Opening the app in incognito does not help if the workspace SSO session is still valid.

**The only fix**: Delete and recreate the app (creates a new OAuth integration), then immediately patch the new integration with the full scope set. See `scenarios/07-AuthZ-SHOWCASE/DEMO-GUIDE.md` for the complete procedure.

---

## 5. Identity Fragmentation and Known Gaps

### The Problem

Databricks AI applications use multiple services, each with a different identity model. In a single user interaction:

1. **Genie query**: `system.access.audit` records the human email (OBO)
2. **M2M SQL query**: `system.access.audit` records the SP UUID (M2M)
3. **MLflow trace**: Records the human email in trace tags (app-level)
4. **Custom MCP tool**: Logs caller via `X-Forwarded-Email` (app-level)

The human who triggered the M2M SQL query is invisible in the data-plane audit log.

### Known Gaps

| Gap | Description | Impact | Workaround |
|---|---|---|---|
| **M2M audit loses human identity** | When an app uses M2M for SQL, `system.access.audit` records the SP UUID, not the human | Cannot determine which user triggered which query | Use OBO SQL (UI "User authorization" with `sql` scope) where possible; add app-level audit for M2M paths |
| **No MLflow-to-audit join** | MLflow traces and `system.access.audit` are separate systems | Cannot trace from agent invocation to data access | Generate a `trace_id` at the agent entry point, pass through tool calls, log in both systems, join manually |
| **Scope overexposure** | OAuth integrations default to `all-apis` | User token has access to every workspace service | Declare minimum required scopes explicitly |
| **`is_member()` under OBO** | In some OBO contexts (Genie), `is_member()` evaluates the SQL execution identity, not the calling user | Row filters using `is_member()` return the same result for all users | Use `current_user()` + allowlist table lookup instead of `is_member()` |

### Proposed Two-Layer Audit Architecture

```
Application Plane (build it yourself):
  MLflow traces --> Delta table --> has human email, trace_id, tool calls

Data Plane (platform-provided):
  system.access.audit --> has executing identity (human or SP), SQL queries

Correlation:
  JOIN on shared trace_id or timestamp window
  Gap: No platform-built join exists
```

For details on building the app-level audit layer, see [scenarios/07-AuthZ-SHOWCASE/observability/OBSERVABILITY.md](../scenarios/07-AuthZ-SHOWCASE/observability/OBSERVABILITY.md).

---

## 6. Quick Decision Guide

### Choosing an Auth Pattern

```
Is the user accessing their own data?
  |
  +-- YES --> Use OBO (Pattern 2)
  |            - Genie queries: OBO by default
  |            - SQL: Add sql scope via UI
  |            - Agent Bricks: Enable OBO in endpoint config
  |
  +-- NO --> Is this a shared/system resource?
              |
              +-- YES --> Use M2M (Pattern 1)
              |            - Vector Search, knowledge base
              |            - Background jobs, CRM sync
              |
              +-- NO --> Is this an external service?
                          |
                          +-- YES --> Use Manual Credentials (Pattern 3)
                          |
                          +-- NO --> Re-evaluate your architecture
```

### Choosing SQL Authentication

```
Do you need per-user row filter enforcement at the SQL layer?
  |
  +-- YES --> Use OBO SQL
  |            - Configure sql scope via Account Console UI
  |            - Use httpx/requests with X-Forwarded-Access-Token
  |            - current_user() = human email in audit
  |
  +-- NO --> Use M2M SQL
              - WorkspaceClient() with no args
              - Add WHERE clause filtering on X-Forwarded-Email
              - SP UUID in audit (add app-level logging for human identity)
```

---

## Related Documents

- [Authorization Flows](authorization-flows.md) -- UC four-layer access control (workspace bindings, privileges, ABAC, row/column filtering)
- [OBO vs M2M Decision Matrix](obo-vs-m2m-decision-matrix.md) -- Detailed decision framework with audit implications
- [Observability and Audit](observability-and-audit.md) -- Two-layer audit model, app-plane and data-plane correlation
- [UC Policy Design Principles](../UC-POLICY-DESIGN-PRINCIPLES.md) -- `current_user()` vs `is_member()` in all execution contexts
- [scenarios/07-AuthZ-SHOWCASE/docs/AUTHZ-PATTERNS.md](../scenarios/07-AuthZ-SHOWCASE/docs/AUTHZ-PATTERNS.md) -- Implementation patterns, code examples, proxy header reference
- [scenarios/07-AuthZ-SHOWCASE/docs/IDENTITY-AND-AUDIT-ARCHITECTURE.md](../scenarios/07-AuthZ-SHOWCASE/docs/IDENTITY-AND-AUDIT-ARCHITECTURE.md) -- Complete identity map with 16-service analysis
