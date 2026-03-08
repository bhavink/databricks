# Auth Patterns — Databricks Apps + Custom MCP

> Hard-won findings from building the AI Auth Showcase (Phase 5).
> Applies to any Databricks App that hosts a custom MCP server or calls another App.
> Last verified: 2026-03-08 on Azure Databricks.

---

## The Core Problem: Two-Proxy Architecture

When a Streamlit app calls a custom MCP server, both are Databricks Apps. Each has its own Envoy proxy in front of it:

```
User browser
    ↓  HTTPS + session
[main-app proxy]                    ← Proxy 1
    ↓  injects X-Forwarded-Access-Token (A), X-Forwarded-Email
app.py (Streamlit)
    ↓  Authorization: Bearer {token A}   ← forwards token A
[mcp-app proxy]                     ← Proxy 2
    ↓  strips Authorization header
    ↓  injects X-Forwarded-Access-Token (B)  ← NEW token, NOT token A
    ↓  injects X-Forwarded-Email             ← correctly set to user's email
server/main.py (FastMCP)
```

**The two-proxy problem**: Proxy 2 does not forward the user's token from app.py. It substitutes its own token (scoped to the custom MCP app's SP). The user's identity from the first proxy never reaches the second app's code via token.

---

## Token Map

### Token A — X-Forwarded-Access-Token in the main app

| Field | Value |
|---|---|
| Format | JWT (`eyJ...`) |
| Issued by | Proxy 1 (main app) |
| Scopes | `offline_access email iam.current-user:read openid iam.access-control:read profile` |
| Usable for | Genie API, Agent Bricks / Model Serving (server-side scope validation) |
| NOT usable for | Statement Execution API (`sql` scope required, not present) |

### Token B — X-Forwarded-Access-Token in the custom MCP app

| Field | Value |
|---|---|
| Format | JWT (`eyJ...`) |
| Issued by | Proxy 2 (MCP app) |
| Identity | **MCP app SP** — not the user |
| Scopes | Same minimal OIDC scopes as Token A |
| Usable for | Nothing different from Token A |

**Key insight**: Token B's `sub` claim is the MCP SP's UUID, not the user's email. Using `current_user.me()` with Token B returns the SP identity, not the user.

### X-Forwarded-Email — the reliable identity source

| Field | Value |
|---|---|
| Set by | Databricks Apps Envoy proxy (infrastructure layer) |
| Value | Authenticated user's email — always |
| Forgeable by app.py? | **No** — proxy overwrites any client-supplied value |
| Available in | Both the main app AND the custom MCP app |
| Works for app-to-app? | **Yes** — Proxy 2 sets it from the validated Token A |

---

## OAuth Scopes — Complete Reference (Add All Upfront)

> **Add the full scope set on first deploy.** Missing scopes cause cryptic errors discovered per-feature, not per-project. Extra scopes are harmless.

```bash
# Required patch command (run once after any app delete+recreate):
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

| Scope | Required for | Discovered how |
|---|---|---|
| `dashboards.genie` + `genie` | Genie OBO (Tab 1) — `genie` not shown in UI but required on Azure | Phase 1 |
| `model-serving` | Agent Bricks / Model Serving endpoint OBO (Tab 5) | Phase 4 |
| `sql` | Statement Execution API — but see gotcha below | Phase 4 |
| `unity-catalog` | External MCP proxy `/api/2.0/mcp/external/...` — proxy checks USE CONNECTION; **undocumented requirement** | Phase 6 (hit 403) |
| `all-apis` | Catch-all for other Databricks REST APIs | Phase 1 |

> **`sql` gotcha**: Adding `sql` to `user_authorized_scopes` does NOT embed it in the JWT `scope` claim — the platform issues a minimal OIDC token regardless. Use M2M (app SP) for SQL warehouse queries; OBO for Genie/Agent Bricks only.

> **`unity-catalog` gotcha**: Completely undocumented. The external MCP proxy validates the calling token has this scope before checking USE CONNECTION. Error: `403: "Provided OAuth token does not have required scopes: unity-catalog"`.

---

## Scope Behavior: Why Some APIs Work and Some Don't

The `X-Forwarded-Access-Token` is an **OIDC identity token**, not a full API token. APIs fall into two categories:

| API | Scope check | Works with X-Forwarded-Access-Token? |
|---|---|---|
| `GET /api/2.0/preview/scim/v2/Me` | Server-side, `iam.current-user:read` ✅ in token | ✅ Yes |
| Genie Conversation API | Server-side only | ✅ Yes |
| Agent Bricks / Model Serving | Server-side only | ✅ Yes |
| Statement Execution API | **JWT `scope` claim must contain `sql`** | ❌ No — `sql` not in token |
| External MCP proxy | **JWT `scope` claim must contain `unity-catalog`** | ✅ Yes — IF `unity-catalog` in `user_authorized_scopes` |

Adding `sql` to the OAuth integration's `user_authorized_scopes` does **not** fix Statement Execution — the platform issues a minimal identity token regardless of the integration configuration.

---

## OBO Patterns: What Works Where

### ❌ ModelServingUserCredentials() — Model Serving only, NOT Databricks Apps

```python
# WRONG for Databricks Apps custom MCP servers
from databricks.sdk.credentials_provider import ModelServingUserCredentials
w = WorkspaceClient(credentials_provider=ModelServingUserCredentials())
```

`ModelServingUserCredentials()` reads the token from Model Serving's internal request context. In a Databricks App, this context does not exist — it falls back silently to M2M.

### ❌ WorkspaceClient(host=host, token=user_token) — PAT conflict

```python
# WRONG — SDK treats token= as a PAT, conflicts with DATABRICKS_CLIENT_ID/SECRET env vars
w = WorkspaceClient(host=host, token=user_token)
# Error: "validate: more than one authorization method configured: oauth and pat"
```

### ❌ Reading X-Forwarded-Access-Token for SQL — missing scope

```python
# WRONG — token lacks 'sql' scope, Statement Execution will reject it
token = headers.get(b"x-forwarded-access-token", b"").decode()
w = WorkspaceClient(host=host, credentials_strategy=_BearerToken(token))
rows = w.statement_execution.execute_statement(...)
# Error: "Provided OAuth token does not have required scopes: sql"
```

### ✅ Correct pattern: X-Forwarded-Email + M2M SQL

```python
import contextvars
from starlette.types import ASGIApp, Receive, Scope, Send

_request_caller: contextvars.ContextVar[str] = contextvars.ContextVar("request_caller", default="")
_request_headers: contextvars.ContextVar[dict] = contextvars.ContextVar("request_headers", default={})

class ExtractTokenMiddleware:
    """Pure ASGI middleware — captures proxy-injected identity headers.

    Must be pure ASGI (not BaseHTTPMiddleware) to avoid ContextVar propagation
    breakage: BaseHTTPMiddleware runs call_next in a new asyncio task, which
    breaks ContextVar inheritance.
    """
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            all_headers = {k.decode("utf-8", errors="replace"): v.decode("utf-8", errors="replace")
                           for k, v in headers.items()}
            # X-Forwarded-Email: set by Databricks Apps proxy from validated token.
            # Cannot be forged by the calling application.
            caller_email = headers.get(b"x-forwarded-email", b"").decode("utf-8")
            ctx_h = _request_headers.set(all_headers)
            ctx_c = _request_caller.set(caller_email)
            try:
                await self.app(scope, receive, send)
            finally:
                _request_caller.reset(ctx_c)
                _request_headers.reset(ctx_h)
            return
        await self.app(scope, receive, send)


def _caller_email() -> str:
    """Proxy-verified caller email. Cannot be forged by the calling app."""
    return _request_caller.get("")


@mcp.tool()
def get_deal_approval_status(opp_id: str) -> dict:
    # Step 1: trusted identity from proxy
    caller = _caller_email()
    if not caller:
        return {"error": "No authenticated user — X-Forwarded-Email not set"}

    # Step 2: check elevation via M2M (quota_viewers table)
    w_m2m = WorkspaceClient()  # M2M: app SP credentials from env
    elevated = bool(_run_sql(w_m2m, f"""
        SELECT 1 FROM catalog.schema.quota_viewers
        WHERE user_email = '{_safe(caller)}' LIMIT 1
    """))

    # Step 3: query with explicit per-user filter (mirrors UC row filter logic)
    access_filter = "" if elevated else f"AND rep_email = '{_safe(caller)}'"
    rows = _run_sql(w_m2m, f"""
        SELECT opp_id, customer_id, stage, amount
        FROM   catalog.schema.opportunities
        WHERE  opp_id = '{_safe(opp_id)}' {access_filter}
        LIMIT  1
    """)
    ...


def main() -> None:
    import uvicorn
    starlette_app = mcp.streamable_http_app()
    wrapped = ExtractTokenMiddleware(starlette_app)
    uvicorn.run(wrapped, host="0.0.0.0", port=8000)
```

**Why this works:**
- `X-Forwarded-Email` is always the correct user email (set by Proxy 2 from Token A's identity)
- No SQL scope needed — identity comes from the header, not the token
- M2M client has `sql` scope implicitly (client_credentials flow)
- Access control is explicit in the WHERE clause — equivalent to row filter but not dependent on token propagation

---

## Proxy-Injected Headers Reference

All set by Databricks Apps Envoy proxy. Cannot be forged by calling apps when `user_authorization_enabled: true` (default).

| Header | Content | Trust level |
|---|---|---|
| `X-Forwarded-Email` | `alice@example.com` | **High** — use for identity |
| `X-Forwarded-User` | `{user_id}@{workspace_id}` | High |
| `X-Forwarded-Preferred-Username` | `Alice Example` (display name) | High |
| `X-Forwarded-Access-Token` | Minimal OIDC JWT (iam.* scopes only) | Medium — identity only, not for API calls |
| `X-Databricks-Org-Id` | Workspace ID | Informational |
| `X-Databricks-Extauthz-Attrs` | mTLS policy metadata from Envoy | Informational — infrastructure plumbing |

### What is `X-Databricks-Extauthz-Attrs`?

```json
{
  "compare_client_cert": true,
  "id": "<internal-policy-id>",
  "require_client_cert": true,
  "validate_client_cert": {"default": false, "exceptions": []}
}
```

Set by Databricks' internal policy engine (OPA-based) for the Apps networking layer. `validate_client_cert.default: false` means mTLS is enforced at the transport layer but cert content is not cryptographically validated end-to-end. Informational only — your code does not need to read this.

---

## Bearer Token Format: OAuth JWT vs PAT

Both use `Authorization: Bearer <value>` — the format is the same. Distinguish by the value:

| Type | Prefix | Structure |
|---|---|---|
| **OAuth JWT** | `eyJ...` | Three base64url segments: `header.payload.signature` |
| **PAT** | `dapi...` | Opaque string, no dots |

Decode an OAuth token to inspect claims:
```python
import base64, json
token = "eyJraWQi..."
payload = token.split(".")[1] + "=="
claims = json.loads(base64.urlsafe_b64decode(payload))
print(claims.get("scp") or claims.get("scope"))  # → scope claims
print(claims.get("sub"))  # → user email or SP UUID
print(claims.get("aud"))  # → audience (workspace ID)
```

**PATs are not supported** for Databricks Apps custom MCP servers. OAuth only.

---

## App SP Grants Checklist for Custom MCP

The MCP app's SP needs explicit grants — different SP from the main app:

```bash
# Get SP UUID from app
SP=$(databricks apps get <mcp-app-name> --profile <p> | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['service_principal_client_id'])")

# UC grants
databricks sql execute "
  GRANT USE CATALOG ON CATALOG my_catalog     TO \`$SP\`;
  GRANT USE SCHEMA  ON SCHEMA  my_catalog.sales TO \`$SP\`;
  GRANT SELECT      ON TABLE   my_catalog.sales.opportunities  TO \`$SP\`;
  GRANT SELECT      ON TABLE   my_catalog.sales.approval_requests TO \`$SP\`;
  GRANT MODIFY      ON TABLE   my_catalog.sales.approval_requests TO \`$SP\`;
  GRANT SELECT      ON TABLE   my_catalog.sales.quota_viewers    TO \`$SP\`;
  -- If using quota_viewers for elevation check, add SP to it:
  INSERT INTO my_catalog.sales.quota_viewers VALUES ('\$SP', 'service_principal');
" --warehouse <wh-id> --profile <p>

# Warehouse access
databricks permissions update warehouses <wh-id> --profile <p> \
  --json "{\"access_control_list\": [{\"service_principal_name\": \"$SP\", \"permission_level\": \"CAN_USE\"}]}"

# Declare in app.yaml for auto-grant on redeploy
# resources:
#   - sql_warehouse:
#       id: "<wh-id>"
#       permission: CAN_USE
```

**Common miss**: The main app SP and the MCP app SP are different. Grants on the main app SP do not carry over.

---

## Debugging Token Issues

Add a debug tool to the MCP server (remove before production):

```python
@mcp.tool()
def debug_identity() -> dict:
    """Show proxy-injected identity headers for this request."""
    all_headers = _request_headers.get({})
    safe = {k: (v[:40] + "..." if len(v) > 40 and any(
                s in k for s in ("token","authorization","secret","cookie")) else v)
            for k, v in all_headers.items()}
    return {
        "caller_email":    _request_caller.get("(not set)"),
        "x_forwarded_user": all_headers.get("x-forwarded-user", "(not set)"),
        "headers":         safe,
    }
```

Headless test from CLI:
```bash
TOKEN=$(databricks auth token --profile <p> | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s -X POST https://<mcp-app-url>/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"debug_identity","arguments":{}}}' \
  | grep "^data:" | head -1 | cut -c7- | python3 -m json.tool
```

---

## OAuth Integration Reset — Nuclear Option

> **When**: Tab 6 returns `403: "Provided OAuth token does not have required scopes: unity-catalog"` and opening the app in incognito/private browser still fails.

### Why incognito doesn't help

Adding a scope to `user_authorized_scopes` does NOT affect existing refresh tokens. When the Apps proxy refreshes an access token using an existing refresh token, the new access token inherits the **original scopes from the authorization code grant** — not the current integration configuration. There is no way to force scope propagation without a new authorization code flow.

Incognito only helps if the Databricks workspace SSO session has truly expired. If the workspace session is still valid, the auth code flow completes silently and the new token still has the old scopes.

### The fix: delete + recreate the app

```
App delete
    ↓  OAuth integration deleted → all refresh tokens invalidated
App create (new)
    ↓  New OAuth integration created (new client_id)
    ↓  Patch scopes IMMEDIATELY on new integration
User login
    ↓  New authorization code flow → new refresh token with current scopes
    ↓  X-Forwarded-Access-Token now includes unity-catalog ✅
```

### Step-by-step (2026-03-08 verified)

```bash
# 1. Delete
databricks apps delete authz-showcase --profile adb-wx1

# 2. Wait for DELETING → gone (poll until 404)
# 3. Recreate
databricks apps create authz-showcase \
  --description "AI Auth Showcase — OBO + M2M + UC Functions" --profile adb-wx1
# Record: service_principal_client_id (UUID) and service_principal_id (integer)

# 4. Deploy
databricks apps deploy authz-showcase \
  --source-code-path /Workspace/Users/bhavin.kukadia@databricks.com/authz-showcase \
  --profile adb-wx1

# 5. Get new integration ID
databricks account custom-app-integration list --profile adb-account | \
  python3 -c "import sys,json; [print(i['integration_id'],i['name']) \
    for i in json.load(sys.stdin) \
    if 'authz-showcase' in i.get('name','') and 'mcp' not in i.get('name','')]"

# 6. Patch scopes on NEW integration (old one is now orphaned — delete it too)
databricks account custom-app-integration update '<new-integration-id>' \
  --profile adb-account \
  --json '{"scopes":["offline_access","email","iam.current-user:read","openid",
    "dashboards.genie","genie","iam.access-control:read","profile",
    "model-serving","sql","all-apis","unity-catalog"],
    "user_authorized_scopes":["dashboards.genie","genie","model-serving",
    "sql","all-apis","unity-catalog"]}'

# 7. Re-run UC grants with NEW SP UUID
# 8. Add new SP integer ID to authz_showcase_executives group
# 9. Refresh custmcp token (update APP_SP_NAME in refresh_custmcp_token.py first)
# 10. Delete old orphaned integration
databricks account custom-app-integration delete '<old-integration-id>' --profile adb-account
```

See `DEMO-GUIDE.md → Nuclear Option` for the complete grant commands.

### What carries over after rebuild

| Survives | Doesn't survive |
|---|---|
| UC data, tables, row filters | App SP UUID (new SP created) |
| Group definitions + user memberships | Manual UC grants to old SP |
| VS indexes, Genie space | OAuth integration + all user sessions |
| `account users` USE CONNECTION grants | SP's USE CONNECTION grants |
| mcp-server app + its SP | seed files with hardcoded old SP UUID |

---

## Related

- `mcp-server/server/main.py` — reference implementation of all patterns above
- `IMPLEMENTATION-PLAN.md` — phase-by-phase build log
- `DEMO-GUIDE.md` — full demo walkthrough + troubleshooting + nuclear option procedure
- `seed/test_harness.py` — headless test of all 6 tab capabilities
- `seed/reset_demo.py` — post-demo persona reset
- Fieldkit: `auth/obo-passthrough.md` — OBO patterns across all app types (updated 2026-03-08)
- Fieldkit: `mcp/custom-mcp.md` — custom MCP server setup
- Fieldkit: `mcp/external-mcp.md` — external MCP patterns (updated 2026-03-08)
