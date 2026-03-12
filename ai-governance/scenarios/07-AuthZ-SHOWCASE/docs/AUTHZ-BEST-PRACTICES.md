# Authorization Best Practices for Databricks AI Applications

> **Audience**: Field Engineers and Solution Architects building production AI apps, custom MCP servers, and agent frameworks on Databricks.
>
> **Companion docs**: `AUTHZ-PATTERNS.md` (implementation patterns), `PROXY-ARCHITECTURE.md` (proxy mechanics), `IDENTITY-AND-AUDIT-ARCHITECTURE.md` (identity map + audit)

---

## Executive Summary

Databricks AI applications combine multiple services — Genie, Vector Search, UC Functions, custom MCP servers, agent frameworks, and external APIs. Each has a different identity model. Getting authorization right means choosing the correct credential for each call, enforcing least privilege, preserving human identity in audit trails, and preventing confused deputy attacks.

This guide distills lessons learned from building production apps across all these patterns.

---

## 1. Choose the Right Identity Model Per Operation

Every API call in your app uses one of three identity models. Pick the right one for each operation:

| Model | When to use | Identity in audit | Example |
|---|---|---|---|
| **On-Behalf-Of (OBO)** | User-specific data, row-filtered queries, consent-gated operations | Human email | Genie queries, OBO SQL, agent endpoints |
| **Machine-to-Machine (M2M)** | Shared resources, system-level queries, background tasks | Service Principal UUID | Vector Search, CRM sync status, knowledge base queries |
| **Proxy Identity + M2M** | User-specific operations where OBO token lacks required scope | SP UUID (with human email in app-level audit) | Custom MCP tools with M2M SQL + `X-Forwarded-Email` identity |

**Rule of thumb**: If the user should only see their own data, use OBO. If everyone sees the same data, use M2M. If you need user identity but can't get OBO scope, use Proxy Identity + M2M as a fallback.

---

## 2. Minimize Service Principal Grants

Every SP grant is attack surface. Apply least privilege rigorously:

### Grant only what the SP's own tools need

```
Good: MCP server SP has SELECT on the two tables its M2M tools query
Bad:  MCP server SP has SELECT on all tables "just in case"
```

### Separate SPs for separate apps

The Streamlit app SP and the MCP server SP are different identities with different grant needs. Never assume grants on one carry over to the other.

### Audit your grants periodically

```sql
-- Check what a specific SP can access
SHOW GRANTS ON CATALOG my_catalog
WHERE grantee = '<sp-uuid>';
```

Remove grants that aren't actively used. If a tool was removed, revoke its grants.

### Use `resources:` in app.yaml for auto-grants

Declared resources auto-grant on every deploy — no manual CLI commands to forget:

```yaml
resources:
  - sql_warehouse:
      id: "<warehouse-id>"
      permission: CAN_USE
  - serving_endpoint:
      name: "<endpoint-name>"
      permission: CAN_QUERY
```

What still requires manual grants: `USE CATALOG`, `USE SCHEMA`, `SELECT` on tables, group membership.

---

## 3. Prevent the Confused Deputy Problem

A **confused deputy** occurs when a service with elevated permissions performs actions on behalf of a user without proper authorization checks. In the Databricks context:

### The risk

Your MCP server SP has `SELECT` on sensitive tables for its M2M tools. An external caller through a UC connection could potentially trigger those tools — using the MCP server's elevated permissions to access data they shouldn't see.

### The defense: UC Connection governance

For external-facing MCP servers, **USE CONNECTION is your primary defense**:

```
Caller → UC External MCP Proxy → USE CONNECTION check → MCP server
```

- If the caller lacks `USE CONNECTION` on the UC HTTP Connection, the request **never reaches** your MCP server
- The MCP server's own SP grants are irrelevant for proxied calls — they only matter for the server's own M2M tools
- `REVOKE USE CONNECTION` instantly cuts off all access through that connection

### Best practices

1. **Keep MCP server SP grants minimal** — only what its M2M tools directly query
2. **Don't give the MCP server SP grants "in case" an external caller needs them** — the caller's access should be governed by USE CONNECTION, not the server's SP
3. **Validate caller identity** — read `X-Forwarded-Email` and enforce per-user access in your tool's WHERE clause
4. **Separate M2M tools from OBO tools** — M2M tools use the server's SP; OBO tools should use the caller's token when available

---

## 4. User Authorization (OBO) Configuration

### Two mechanisms — use the right one

| Mechanism | How | Result |
|---|---|---|
| **CLI** `custom-app-integration update` | Sets `user_authorized_scopes` on OAuth integration | Sets scopes in config but does NOT produce OBO JWT with those scopes |
| **UI** User Authorization (Preview) | Edit App → Configure → User Authorization → Add Scope | Sets `effective_user_api_scopes` AND produces real OBO JWT |

**Always use the UI** for adding scopes. The CLI approach alone does not populate `effective_user_api_scopes` and does not result in service scopes appearing in the `x-forwarded-access-token`.

### Available UI scopes

| UI scope name | What it enables |
|---|---|
| `sql` | OBO SQL via Statement Execution API — `current_user()` = human email |
| `dashboards.genie` | Genie space access |
| `serving.serving-endpoints` | Model Serving / Agent Bricks OBO |
| `catalog.connections` | UC HTTP Connection access |
| `catalog.catalogs:read` | Read-only UC catalog access |
| `files.files` | File and directory access |

### OBO SQL unlocks audit trail

With the `sql` scope via UI:
- `current_user()` returns the human email (not SP UUID)
- `session_user()` returns the human email
- UC row filters and column masks fire as the human user
- `system.access.audit` records the human email
- **Gap 1 (M2M audit loses human identity) is solved**

### Implementation note

Use `httpx`/`requests` directly for OBO SQL — not the Databricks SDK. The SDK auto-discovers `DATABRICKS_CLIENT_ID`/`SECRET` from env vars, causing a "more than one authorization method" conflict:

```python
# Correct — direct HTTP with user token
import httpx
host = os.environ["DATABRICKS_HOST"]
if not host.startswith("http"):
    host = f"https://{host}"

resp = httpx.post(
    f"{host}/api/2.0/sql/statements",
    headers={"Authorization": f"Bearer {user_token}"},
    json={"warehouse_id": wh_id, "statement": sql, "wait_timeout": "30s"},
)

# Wrong — SDK conflicts with env vars
# w = WorkspaceClient(token=user_token)  # raises: more than one auth method
```

---

## 5. UC Connection Governance for External MCP

### USE CONNECTION is the on/off switch

Every call through a UC HTTP Connection (including UC External MCP Proxy calls) requires `USE CONNECTION` on the calling identity:

```sql
-- Grant access
GRANT USE CONNECTION ON CONNECTION my_connection TO `<identity>`;

-- Revoke access (instant effect)
REVOKE USE CONNECTION ON CONNECTION my_connection FROM `<identity>`;
```

### Four connection auth methods, same governance

| Auth method | Who authenticates to external service | Best for |
|---|---|---|
| **Bearer Token** | Stored token (shared identity) | APIs with static API keys |
| **OAuth M2M** | Client credentials (shared SP) | Service-to-service APIs |
| **OAuth U2M Shared** | Shared user identity | APIs requiring user context |
| **OAuth U2M Per User** | Each user's own identity | GitHub, Salesforce (per-user audit) |

All four are governed by the same `USE CONNECTION` privilege. The auth method determines *how* the connection authenticates; `USE CONNECTION` determines *whether* the call is allowed.

### Important: Connection owner has implicit USE CONNECTION

The connection owner always has implicit `USE CONNECTION` that cannot be revoked. `GRANT`/`REVOKE` only affects non-owners. When demoing governance, use a non-owner identity (e.g., the app SP).

### Bearer token expiration

UC connections with stored bearer tokens expire (~1hr for Databricks tokens). Refresh before demos:

```bash
# Get fresh token
TOKEN=$(databricks auth token --profile <profile> | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Update connection
databricks connections update <conn-name> --profile <profile> \
  --json "{\"options\":{\"host\":\"<url>\",\"port\":\"443\",
  \"httpPath\":\"/mcp\",\"bearer_token\":\"$TOKEN\"}}"
```

---

## 6. Proxy Architecture Decisions

### authorization: disabled vs enabled

| Setting | Use when | Trade-off |
|---|---|---|
| **enabled** (default) | App serves browser users, external clients (Claude Code) | Proxy strips forwarded tokens from upstream apps |
| **disabled** | App receives calls from another Databricks App | Proxy passes through all headers; no auth validation |

### Can't serve both? Two options

1. **Two deployments** — one with auth disabled (for app-to-app), one with default enabled (for external clients). Simplest, no code changes.
2. **Fallback logic** — keep auth disabled, parse Bearer token from Authorization header when `X-Forwarded-Email` is empty. Decode JWT to extract email claim.

### User Authorization works with either setting

User Authorization (UI scopes) works independently of the `authorization` setting. Even with `authorization: disabled`, the proxy triggers the OAuth consent flow and injects the OBO token. The two-proxy pattern and user authorization can coexist.

---

## 7. Audit Trail Architecture

### Platform audit (automatic)

| Service | Audit source | Identity captured |
|---|---|---|
| SQL Warehouse | `system.access.audit` → `databricksSql` | Executing identity (human for OBO, SP for M2M) |
| Genie | `system.access.audit` → `aibiGenie` | Human email |
| UC connections | `system.access.audit` | Calling identity |
| Model Serving | `system.access.audit` | Calling identity |

### Application-level audit (build it yourself)

For M2M paths where the human email isn't in the platform audit, add application-level logging:

```python
import logging
logger = logging.getLogger("audit")

@mcp.tool()
def my_tool(args: str) -> dict:
    caller = _caller_email()  # from X-Forwarded-Email
    logger.info(f"tool=my_tool caller={caller} args={args}")
    # ... execute with M2M credentials
```

### MLflow trace correlation (gap)

There is no platform-built join between MLflow traces and UC audit events. If you need end-to-end tracing from agent invocation to data access:
- Generate a `trace_id` at the agent entry point
- Pass it through tool calls
- Log it in both MLflow traces and application audit
- Join manually via the shared `trace_id`

---

## 8. Decision Matrix — Quick Reference

| Question | Answer |
|---|---|
| User should only see their data? | Use OBO (user token + UC row filters) |
| Everyone sees the same data? | Use M2M (app SP credentials) |
| Need SQL as the user? | Add `sql` scope via UI User Authorization, use OBO token with httpx |
| External API via UC connection? | Use UC External MCP Proxy + USE CONNECTION governance |
| MCP server called by another app? | Set `authorization: disabled` on MCP server |
| MCP server called by external clients too? | Deploy two instances, or add token-parsing fallback |
| Need human identity in audit? | Use OBO where possible; add app-level audit for M2M paths |
| Preventing confused deputy? | Minimal SP grants + USE CONNECTION as the governance layer |

---

## 9. Common Pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| SDK PAT+OAuth conflict | "more than one authorization method configured" | Use httpx directly for OBO token calls |
| CLI scopes don't produce OBO JWT | Token has only OIDC scopes, no `sql` | Use UI User Authorization, not CLI `custom-app-integration update` |
| Bearer token expired in UC connection | 401 on UC proxy calls | Refresh stored bearer token before demos |
| Connection owner can't be revoked | REVOKE succeeds but owner still has access | Use non-owner identity for governance demos |
| `is_member()` checks session_user groups | Group-based access fails under Genie OBO | Use `current_user()` checks or explicit WHERE clauses instead |
| `X-Forwarded-Email` empty in MCP server | Using auth:disabled with no upstream proxy | Parse Bearer token JWT directly, or switch to auth:enabled |
| Gave MCP server SP too many grants | Confused deputy risk | Audit grants, revoke unused ones, enforce least privilege |

---

## Related

- `AUTHZ-PATTERNS.md` — Implementation details, token maps, code patterns
- `PROXY-ARCHITECTURE.md` — Proxy mechanics, header traces, design rationale
- `IDENTITY-AND-AUDIT-ARCHITECTURE.md` — Complete identity map, audit architecture, product gaps
- Fieldkit: `auth/obo-passthrough.md` — OBO patterns across all app types
- Fieldkit: `mcp/custom-mcp.md` — Custom MCP server setup
- Fieldkit: `mcp/external-connection-tools.md` — UC HTTP Connections + External MCP
