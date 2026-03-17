# Custom MCP Architecture — Governance, Security, Observability

## Principles

1. **MCP is the single gateway** — apps never call Databricks APIs directly. All data/compute access routes through MCP tools.
2. **Scopes over grants** — OAuth scopes restrict what a token can do. Direct table/service grants are minimized; UC governance (row filters, column masks, `USE CONNECTION`, `EXECUTE`) enforces fine-grained access.
3. **UC governance end-to-end** — every tool invocation runs under the caller's identity. Row filters, column masks, and connection access checks fire at the engine level.
4. **100% trace coverage** — every tool call creates an MLflow trace with: service, tool, caller, request_id, latency, status.
5. **100% audit coverage** — every tool call writes to the audit table (async, fire-and-forget). Denials, errors, and successes all recorded.
6. **Defense in depth** — tool-level RBAC (federation) + UC governance + scope restrictions. Multiple layers, any one sufficient.
7. **No secrets in code** — UC connections hold external credentials. GitHub token comes from `USE CONNECTION`, not env vars.

## Two Identity Patterns

### mcp-databricks-federation (External IDP → Role SPs)

```
External User → IDP (Auth0/Okta/Entra) → App Server (JWT verify)
  → Token Exchange (RFC 8693) → Databricks SP token (scoped)
  → MCP Server → Tools → UC Governance (fires per SP group)
```

**Scopes on exchanged token**: `sql genie serving`
- `sql` → SQL warehouse access (row filters, column masks fire)
- `genie` → Genie Conversation API
- `serving` → Model Serving endpoints (supervisor agent)

**UC governance layers**:
- Row filters: `is_member('authz_showcase_west')` etc.
- Column masks: `margin_pct` masked for non-finance/exec/admin
- `USE CONNECTION`: controls GitHub/external API access per SP
- `EXECUTE`: controls UC function access per SP
- `CAN QUERY`: controls serving endpoint access per SP

### mcp-databricks-obo (Databricks Native Identity)

```
Databricks User → OAuth (browser) → Apps Proxy
  → x-forwarded-access-token (OBO token, scoped)
  → MCP Server → Tools → UC Governance (fires per user identity)
```

**Scopes on OBO token** (configured in App UI → User Authorization):
- `sql` → SQL warehouse
- `dashboards.genie` + `genie` → Genie (Azure needs both)
- `serving` → Model Serving endpoints
- `apps` → calling other Databricks Apps

**UC governance**: fires as `current_user()` = human email. No SP intermediary.

## Scope-Based Access Model

| Resource | Scope Required | UC Grant Required | Who Checks |
|----------|---------------|-------------------|------------|
| SQL Warehouse | `sql` | `CAN USE` on warehouse | Token + UC |
| Genie Space | `genie` + `dashboards.genie` | Access to space + underlying tables | Token + UC |
| Model Serving | `serving` | `CAN QUERY` on endpoint | Token + UC |
| Vector Search | `sql` (SDK uses SQL internally) | `SELECT` on VS index | Token + UC |
| UC Connection | `sql` (for DESCRIBE CONNECTION) | `USE CONNECTION` | Token + UC |
| UC Function | `sql` (for SELECT fn()) | `EXECUTE` on function | Token + UC |
| Audit Table | `sql` | `SELECT` on table | Token + UC |

**Key insight**: Scopes restrict what the token CAN do. UC grants restrict what the identity CAN access. Both layers enforce independently. Revoking either blocks access.

## External Credentials via UC Connections

**Never store external secrets in env vars or code.** Use UC connections:

```sql
-- Create connection (one-time setup)
CREATE CONNECTION github_bearer_token
  TYPE HTTP
  OPTIONS (host 'https://api.github.com', bearer_token SECRET '<pat>');

-- Control access (per-identity)
GRANT USE CONNECTION ON CONNECTION github_bearer_token TO `<sp-or-group>`;
REVOKE USE CONNECTION ON CONNECTION github_bearer_token FROM `<sp-or-group>`;
```

At runtime, the MCP server:
1. Calls `DESCRIBE CONNECTION` with caller's token → UC checks `USE CONNECTION`
2. If allowed → retrieves connection options (includes credential)
3. Uses credential for the external API call
4. Audit records the UC connection access

## Observability Stack

```
Tool Call → MLflow Trace (spans: auth, sql, external_api, audit)
         → Audit Table (async, never blocks response)
         → Structured JSON Logs (request_id correlation)
         → Lakeview Dashboard (queries audit table)
```

### Audit Table Schema

| Column | Type | Description |
|--------|------|-------------|
| request_id | STRING | Correlation ID (from header or generated) |
| request_time | TIMESTAMP | When the tool call started |
| external_user_email | STRING | Who made the call (from IDP or OBO) |
| role_mapped | STRING | Role (federation) or "obo_user" (OBO) |
| tool_name | STRING | Which tool was called |
| status | STRING | success / error / access_denied |
| error_code | STRING | Error classification |
| latency_ms | INT | End-to-end tool latency |

### MLflow Trace Tags

Every trace includes: `service_name`, `tool`, `caller.email`, `caller.role`, `request_id`, `status`, `latency_ms`

## Rate Limiting

| API | Limit | Strategy |
|-----|-------|----------|
| Genie | 5 QPM per workspace | In-memory sliding window, return 429 with retry_after_ms |
| SQL | No hard limit | Connection pool limits (20 concurrent) |
| Serving | Depends on endpoint | Retry with backoff on 429 |
| GitHub | 5000/hr per token | Retry with backoff on 429 |

## Supervisor Agent Integration

Both MCP servers can be registered as sub-agents of a Databricks Supervisor Agent:

```
Supervisor Agent (Model Serving endpoint)
  → UC Connection (bearer token auth) → Custom MCP Server
  → Genie Space (direct)
  → Knowledge Assistant endpoint (direct)
  → UC Functions (direct)
```

**Registration path**: Create a UC connection pointing to the MCP server URL, then add it as an "External MCP Server" sub-agent in the Supervisor UI.

**Access control lever**: `USE CONNECTION` on the UC connection. Revoking it removes the MCP from the user's supervisor experience at runtime. Max 20 sub-agents per supervisor.

**OBO requirement**: Supervisor uses on-behalf-of authorization — the calling user's identity propagates to sub-agents. This is how per-user permission checks work at runtime.

**Stateful Agents (Lakebase)**:
- Short-term memory: `thread_id` + LangGraph checkpointing in Lakebase
- Long-term memory: cross-session key insights in Lakebase
- Genie conversation threading: `conversation_id` persistence in app state
- Both MCP servers support `conversation_id` on genie_query for multi-turn conversations

## Security Checklist

- [ ] No secrets in env vars (use UC connections)
- [ ] All SQL uses parameterized queries or safe escaping
- [ ] Input validation on all tool parameters
- [ ] Rate limiting on Genie (5 QPM)
- [ ] Connection pool limits prevent resource exhaustion
- [ ] Async audit never blocks tool response
- [ ] Structured logging with request_id for tracing
- [ ] Health check validates all dependencies
- [ ] Retry with jitter prevents thundering herd
- [ ] Token never logged (even in error messages)
