# Proxy Architecture — Databricks Apps Request Lifecycle

> **Companion to**: `AUTHZ-PATTERNS.md` (token map, OBO patterns, scope reference).
> This document traces actual HTTP requests through the Databricks Apps proxy layer, header by header, hop by hop. Read this first if you want to understand **why** the auth patterns are what they are.

---

## What is "the proxy"?

There are actually **three distinct proxy types** in play:

### 1. Databricks Apps Proxy (standard)

Every Databricks App gets an **automatic reverse proxy** managed by the platform. You don't deploy it, configure it, or see it in your code. It sits between the internet and your app process (Streamlit, FastMCP, Flask — anything listening on port 8000).

```
Internet → [Databricks Apps Proxy] → your app (port 8000)
```

The proxy does three things:

1. **Authenticates the caller** — validates the OAuth session cookie (browser) or Bearer token (API call)
2. **Injects identity headers** — adds `X-Forwarded-*` headers that your app can read
3. **Strips the original Authorization header** — replaces it with the app's own service principal token

Your app never sees the user's original OAuth token. It sees proxy-injected headers instead.

### 2. UC External MCP Proxy

The endpoint `/api/2.0/mcp/external/{connection_name}` is a **platform service**, not an app proxy. It fronts any HTTP Connection registered in Unity Catalog, enforcing `USE CONNECTION` privilege before forwarding traffic. This proxy injects `x-forwarded-email` from the caller's token into the downstream request.

### 3. The three-proxy combination

When a Streamlit app calls the UC External MCP Proxy, which in turn reaches a Custom MCP server app, the request passes through **three** proxies:

```
App Proxy 1 (Streamlit) → UC External MCP Proxy → App Proxy 2 (MCP server)
```

Each proxy is described in its own section below.

---

## Proxy-injected headers — complete reference

These headers are set by the Databricks Apps proxy on every authenticated request. Your app code reads them from the incoming request — they are not something you send.

| Header | Example value | What it is | Trust level |
|---|---|---|---|
| `X-Forwarded-Email` | `user@example.com` | Caller's email from the validated OAuth token | **High** — set by proxy from authenticated identity. Cannot be forged by the calling app. **Use this for identity.** |
| `X-Forwarded-User` | `{user_id}@{workspace_id}` | `{user_id}@{workspace_id}` | High — same provenance as email |
| `X-Forwarded-Preferred-Username` | `{display_name}` | Display name from the user's profile | High — informational |
| `X-Forwarded-Access-Token` | `eyJraWQi...` (JWT) | Minimal OIDC identity token issued by the proxy | Medium — **not** the user's original token; scopes are limited (see below) |
| `X-Forwarded-Groups` | (comma-separated group list) | Workspace groups the user belongs to | High — from validated token claims |
| `X-Databricks-Org-Id` | `{workspace_id}` | Workspace ID | Informational |

### What X-Forwarded-Access-Token is and isn't

| Property | Value |
|---|---|
| **Format** | JWT (`eyJ...`) — three base64url segments |
| **Issuer** | The Databricks Apps proxy (not the user's OAuth provider) |
| **`sub` claim** | The app's **service principal UUID** — not the user |
| **Scopes** | Minimal OIDC: `offline_access email iam.current-user:read openid iam.access-control:read profile` |
| **Usable for** | Genie API, Agent Bricks endpoints (server-side scope validation) |
| **NOT usable for** | Statement Execution API (`sql` scope not present by default), direct UC queries |

The proxy re-issues this token scoped to the app's SP. By default, even if the user's original OAuth token had `sql` or `unity-catalog` scopes, the proxy-injected token does not carry them.

**Exception — UI User Authorization (Public Preview):** When an app is configured with UI User Authorization, the `X-Forwarded-Access-Token` **can** contain service scopes like `sql`. The "no service scopes" behavior described above applies to the default CLI-configured scope model. With UI User Authorization, the platform issues a richer token that may include additional scopes granted through the UI.

---

## Single-proxy path — browser to one app

This is the simple case: a user opens your Streamlit app in a browser.

```
Step 1: User navigates to https://{app_name}-{workspace_id}.{region}.{cloud}.databricksapps.com
        Browser sends: session cookie (from prior OAuth login)

Step 2: Databricks Apps Proxy (automatic)
        ├── Validates session cookie against workspace OIDC
        ├── STRIPS the cookie / Authorization header
        ├── INJECTS:
        │     X-Forwarded-Email: user@example.com
        │     X-Forwarded-User: {user_id}@{workspace_id}
        │     X-Forwarded-Preferred-Username: {display_name}
        │     X-Forwarded-Access-Token: eyJ... (SP-scoped OIDC JWT)
        │     X-Forwarded-Groups: authz_showcase_west,...
        │     X-Databricks-Org-Id: {workspace_id}
        └── Forwards to app process on port 8000

Step 3: app.py (Streamlit) receives the request
        ├── Reads X-Forwarded-Access-Token via st.context.headers
        │   → uses it for Genie API calls, Agent Bricks calls (OBO)
        ├── Reads X-Forwarded-Email (implicitly, via SCIM /Me call with the token)
        │   → builds sidebar identity panel
        └── Uses WorkspaceClient() (no args) for M2M operations
            → SDK auto-discovers DATABRICKS_CLIENT_ID/SECRET from env
```

**Headers at each hop:**

| Hop | Authorization | X-Forwarded-Email | X-Forwarded-Access-Token | Notes |
|---|---|---|---|---|
| Browser → Proxy | Session cookie | (not set) | (not set) | Browser sends cookie, not Bearer |
| Proxy → app.py | (stripped) | `user@...` | `eyJ...` (SP JWT) | Proxy replaces auth, injects identity |

---

## Two-proxy path — Streamlit app calls custom MCP server

This is the core architecture of the AuthZ Showcase. The Streamlit app (Tab 4) calls the custom MCP server, which is a separate Databricks App.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                                 │
│  Cookie: _databricks_session=abc123                                 │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PROXY 1 — for the Streamlit app ({streamlit-app-name})                   │
│                                                                     │
│  Validates: session cookie                                          │
│  Strips:   Cookie / Authorization                                   │
│  Injects:  X-Forwarded-Email: user@example.com        │
│            X-Forwarded-Access-Token: eyJ...TOKEN_A (SP1 JWT)        │
│            X-Forwarded-User: {user_id}@{workspace_id}            │
│                                                                     │
│  app.yaml: authorization NOT disabled (default = enabled)           │
│  → Proxy performs full authentication                                │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  app.py (Streamlit) — Tab 4 code                                    │
│                                                                     │
│  Reads: X-Forwarded-Access-Token → user_token (TOKEN_A)             │
│                                                                     │
│  Calls MCP server:                                                  │
│    POST https://{mcp-app-name}-.../mcp                   │
│    Headers:                                                         │
│      Authorization: Bearer {TOKEN_A}    ← forwards user's token     │
│      Content-Type: application/json                                 │
│      Accept: application/json, text/event-stream                    │
│    Body: {"jsonrpc":"2.0","method":"tools/call",...}                 │
│                                                                     │
│  (see app.py:1454 — _mcp_call function)                             │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PROXY 2 — for the MCP server app ({mcp-app-name})       │
│                                                                     │
│  app.yaml: authorization: disabled                                  │
│                                                                     │
│  With auth DISABLED, Proxy 2:                                       │
│    ✅ Does NOT strip/replace the Authorization header               │
│    ✅ Passes through X-Forwarded-Email from the incoming request    │
│    ✅ Passes through all other X-Forwarded-* headers                │
│    ❌ Does NOT perform authentication itself                        │
│    ❌ Does NOT inject its own X-Forwarded-* headers                 │
│                                                                     │
│  If auth were ENABLED (default), Proxy 2 would:                     │
│    ❌ STRIP the Authorization header from Streamlit                  │
│    ❌ Replace X-Forwarded-Access-Token with TOKEN_B (SP2 JWT)       │
│    ❌ Overwrite X-Forwarded-Email (still correct, but from SP2 auth)│
│    → TOKEN_B.sub = MCP app's SP UUID, NOT the user                  │
│    → The user's original Bearer token would be lost                 │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│  server/main.py (FastMCP on port 8000)                              │
│                                                                     │
│  ExtractTokenMiddleware reads from the incoming request:             │
│    X-Forwarded-Email: user@example.com   → ContextVar  │
│    (all other headers captured for debug_token_scopes)              │
│                                                                     │
│  OBO tools call _caller_email() → "user@example.com"   │
│  M2M tools call WorkspaceClient() → uses app SP credentials         │
│  SQL uses explicit WHERE rep_email = '{caller}' (mirrors row filter) │
└─────────────────────────────────────────────────────────────────────┘
```

**Headers at each hop:**

| Hop | Authorization | X-Forwarded-Email | X-Forwarded-Access-Token | Source of identity |
|---|---|---|---|---|
| Browser → Proxy 1 | Cookie | (not set) | (not set) | Cookie |
| Proxy 1 → app.py | (stripped) | `user@...` | `eyJ...TOKEN_A` | Proxy 1 validates cookie |
| app.py → Proxy 2 | `Bearer TOKEN_A` | (not explicitly sent by app.py — but present if Proxy 1 added it to the upstream response context) | (not sent by app.py) | app.py forwards TOKEN_A |
| Proxy 2 → server/main.py | `Bearer TOKEN_A` (passthrough) | `user@...` (passthrough) | (passthrough if present) | Passthrough — auth disabled |

---

## Three-proxy path — Streamlit → UC External MCP Proxy → Custom MCP

This path uses a Unity Catalog Connection to route MCP traffic through the platform's `/api/2.0/mcp/external/{connection_name}` endpoint instead of calling the MCP server app directly. The UC External MCP Proxy sits in the middle, adding governance (privilege checks, audit logging) that a direct app-to-app call does not have.

```
Browser → Proxy 1 (Streamlit app, auth enabled)
  → app.py reads X-Forwarded-Access-Token as user_token
  → app.py calls /api/2.0/mcp/external/{conn_name} with user_token as Bearer
  → UC External MCP Proxy:
    - Checks USE CONNECTION privilege on calling identity
    - If no USE CONNECTION → 403 "User does not have any privileges on Connection"
    - If granted → forwards to the HTTP Connection's stored URL
    - Injects: x-forwarded-email from caller's token
  → Proxy 2 (MCP server app, auth disabled)
    - Passes through all headers unchanged
  → server/main.py
    - Reads x-forwarded-email for identity
    - OBO token present but typically lacks sql scope → M2M fallback for SQL
```

**Headers at each hop:**

| Hop | Authorization | x-forwarded-email | Notes |
|---|---|---|---|
| Browser → Proxy 1 | Session cookie | (not set) | Browser sends cookie |
| Proxy 1 → app.py | (stripped) | `user@example.com` | Proxy 1 injects identity |
| app.py → UC External MCP Proxy | `Bearer {user_token}` | (not sent by app.py) | app.py forwards the token from Proxy 1 |
| UC External MCP Proxy → Proxy 2 | (rewritten by platform) | `user@example.com` (injected by UC proxy) | USE CONNECTION checked here |
| Proxy 2 → server/main.py | (passthrough) | `user@example.com` (passthrough) | auth disabled — all headers pass through |

The key difference from the two-proxy path: the UC External MCP Proxy enforces **USE CONNECTION** before traffic ever reaches the MCP server. This means you can gate access to the MCP server at the Unity Catalog level — no changes to the MCP server code needed.

---

## USE CONNECTION governance

The UC External MCP Proxy enforces `USE CONNECTION` on every request, regardless of how the caller authenticated:

| Property | Detail |
|---|---|
| **Privilege required** | `USE CONNECTION` on the UC Connection object |
| **Auth method agnostic** | Same check for Bearer token, OAuth M2M, U2M Shared, U2M Per User |
| **Connection owner** | Always has implicit `USE CONNECTION` — cannot be revoked |
| **Non-owners** | Require explicit `GRANT USE CONNECTION ON CONNECTION <name> TO <principal>` |
| **Revocation** | `REVOKE USE CONNECTION ON CONNECTION <name> FROM <principal>` — only affects non-owners |
| **Audit trail** | Every call through a UC Connection is logged in `system.access.audit` |

This gives platform-level governance over which identities can reach backend MCP servers, without requiring any auth logic in the MCP server itself.

---

## Why `authorization: disabled` and where

**Only** the MCP server app (`mcp-server/app.yaml:25`) has `authorization: disabled`. The Streamlit app uses the default (enabled).

```yaml
# mcp-server/app.yaml
authorization: disabled   # ← THIS LINE

# app/app.yaml
# (no authorization line — default = enabled)
```

### What `authorization: disabled` does

| Behavior | auth: enabled (default) | auth: disabled |
|---|---|---|
| Proxy validates incoming token/cookie | Yes | **No** |
| Proxy strips Authorization header | Yes — replaces with SP token | **No** — passes through unchanged |
| Proxy injects X-Forwarded-Email | Yes — from its own validation | **No** — passes through whatever is already in the request |
| Proxy injects X-Forwarded-Access-Token | Yes — SP-scoped OIDC JWT | **No** — passes through |
| Unauthenticated requests reach your app | No — proxy returns 401/302 | **Yes** — proxy is a passthrough |

### Why it's necessary for app-to-app calls

Without `authorization: disabled` on the MCP server:

1. app.py sends `Authorization: Bearer TOKEN_A` (user's token from Proxy 1)
2. Proxy 2 sees this, says "let me authenticate this myself"
3. Proxy 2 **strips** `Bearer TOKEN_A`, replaces with `Bearer TOKEN_B` (MCP app's SP token)
4. Proxy 2 sets `X-Forwarded-Access-Token: TOKEN_B` where `TOKEN_B.sub` = SP UUID
5. server/main.py receives TOKEN_B — the **user's identity is lost**

With `authorization: disabled`:

1. app.py sends `Authorization: Bearer TOKEN_A` + X-Forwarded-Email flows through
2. Proxy 2 passes everything through untouched
3. server/main.py reads `X-Forwarded-Email: user@example.com` — identity preserved

---

## External client path — Claude Code / Cursor / MCP Inspector

When an external client connects directly (not through another Databricks App), there's only one proxy:

```
Claude Code
    │
    │ stdio (subprocess spawn)
    ▼
mcp-remote (npx)
    │
    │ HTTPS POST with Authorization: Bearer {user_oauth_token}
    │ (token obtained via OAuth PKCE flow — mcp-remote handles this)
    ▼
Proxy 2 — for the MCP server app
    │
    │ (see behavior table below)
    ▼
server/main.py (FastMCP)
```

There is no Proxy 1. There is no Streamlit app. The external client talks directly to the MCP server's proxy.

### The problem: `authorization: disabled` breaks external clients

| Header | auth: disabled (current) | auth: enabled |
|---|---|---|
| Authorization | Passes through: `Bearer {user_token}` | Stripped, replaced with SP token |
| X-Forwarded-Email | **Empty** — no upstream proxy set it | **Set by Proxy 2** from validated token: `user@...` |
| X-Forwarded-Access-Token | **Empty** — no upstream proxy set it | Set by Proxy 2: SP-scoped JWT |

With `authorization: disabled`:
- `_caller_email()` returns `""` → OBO tools return `{"error": "No authenticated user identity"}`
- M2M-only tools (`get_crm_sync_status`) still work — they don't check caller identity

With `authorization: enabled`:
- Proxy 2 validates the OAuth token from mcp-remote
- Sets `X-Forwarded-Email` to the user's email
- `_caller_email()` returns `"user@example.com"` → OBO tools work

### The tradeoff

You cannot serve both paths with one deployment and one `authorization` setting:

| Client path | Needs auth: disabled | Needs auth: enabled |
|---|---|---|
| Streamlit app → MCP server (two-proxy) | ✅ | ❌ Proxy 2 strips user token |
| Claude Code → MCP server (single-proxy) | ❌ No X-Forwarded-Email | ✅ |

**Options to support both:**

1. **Two deployments** — one with `authorization: disabled` (for Streamlit), one with default enabled (for external clients). Simplest, no code changes.

2. **Single deployment with fallback logic** — keep `authorization: disabled`, modify `ExtractTokenMiddleware` to parse the Bearer token from the Authorization header when `X-Forwarded-Email` is empty. Decode the JWT, extract the `email` or `sub` claim. This makes the server work in both scenarios but adds token-parsing responsibility to your code.

3. **Single deployment, auth enabled, rework Streamlit** — change the Streamlit app's Tab 4 to not forward the Bearer token. Instead, rely on the user's browser session propagating through to Proxy 2 via a redirect or iframe. More complex, less practical.

---

## Full header trace — Streamlit → MCP server (current production setup)

Step-by-step trace of an actual `get_deal_approval_status` call from Tab 4:

### Hop 1: Browser → Proxy 1

```
GET https://{app_name}-{workspace_id}.{region}.{cloud}.databricksapps.com/
Cookie: _databricks_session=<session_id>
User-Agent: Mozilla/5.0 ...
```

### Hop 2: Proxy 1 → app.py

```
(internal — Proxy 1 forwards to Streamlit on port 8000)

X-Forwarded-Email: user@example.com
X-Forwarded-User: {user_id}@{workspace_id}
X-Forwarded-Preferred-Username: {display_name}
X-Forwarded-Access-Token: eyJraWQi...TOKEN_A
X-Forwarded-Groups: authz_showcase_west,...
X-Databricks-Org-Id: {workspace_id}
X-Real-Ip: <client_ip>
X-Forwarded-For: <client_ip>
X-Forwarded-Proto: https
X-Forwarded-Host: {app_name}-{workspace_id}.{region}.{cloud}.databricksapps.com
```

### Hop 3: app.py → Proxy 2

```
POST https://{mcp_app_name}-{workspace_id}.{region}.{cloud}.databricksapps.com/mcp

Authorization: Bearer eyJraWQi...TOKEN_A       ← app.py forwards the token
Content-Type: application/json
Accept: application/json, text/event-stream
Mcp-Session-Id: <from initialize response>      ← set after first call

Body: {"jsonrpc":"2.0","id":1,"method":"tools/call",
       "params":{"name":"get_deal_approval_status","arguments":{"opp_id":"opp_001"}}}
```

### Hop 4: Proxy 2 → server/main.py (authorization: disabled)

```
(Proxy 2 passes through — does not authenticate, does not rewrite headers)

Authorization: Bearer eyJraWQi...TOKEN_A        ← unchanged
X-Forwarded-Email: user@example.com ← passed through from hop 3
Content-Type: application/json
Accept: application/json, text/event-stream
Mcp-Session-Id: <session_id>
X-Real-Ip: <streamlit_app_ip>
X-Forwarded-For: <streamlit_app_ip>
X-Forwarded-Proto: https
```

### Inside server/main.py

```python
# ExtractTokenMiddleware.__call__:
scope["headers"] → dict of all headers above

_request_caller.set("user@example.com")  # from X-Forwarded-Email
_request_headers.set({...all headers...})               # for debug_token_scopes

# get_deal_approval_status:
caller = _caller_email()  # → "user@example.com"
w_m2m = WorkspaceClient() # → uses DATABRICKS_CLIENT_ID/SECRET from env (app SP)
# SQL: WHERE opp_id = 'opp_001' AND rep_email = 'user@example.com'
```

---

## Design decisions and rationale

### Why X-Forwarded-Email instead of parsing the Bearer token

| Approach | Pros | Cons |
|---|---|---|
| **X-Forwarded-Email** (chosen) | Set by infrastructure; unforgeable; no token parsing; works regardless of token format changes | Requires proxy to set it (fails when auth disabled + no upstream proxy) |
| **Parse Bearer JWT** | Works without proxy injection; self-contained | Token format is platform-internal; `sub` may be SP UUID not email; requires JWT decode + validation; token may be opaque in future |
| **`current_user.me()` API call** | Authoritative; works with any valid token | Extra API call per request; adds latency; requires `iam.current-user:read` scope on the token |

### Why M2M for SQL instead of OBO

The `X-Forwarded-Access-Token` (Token A or Token B) is a minimal OIDC identity token. It does **not** contain the `sql` scope required by the Statement Execution API. Adding `sql` to the OAuth integration's `user_authorized_scopes` does not help — the platform issues a minimal token regardless of the integration configuration.

The pattern: **identity from the proxy header, authorization from the app SP**. The MCP server reads `X-Forwarded-Email` to know *who* is calling, then uses its own SP credentials (`WorkspaceClient()` no-args) to execute SQL with an explicit `WHERE rep_email = '{caller}'` clause. This produces the same access control as a UC row filter, without requiring the `sql` scope on the user's token.

### Why pure ASGI middleware (not BaseHTTPMiddleware)

Starlette's `BaseHTTPMiddleware` runs `call_next()` in a separate `asyncio.Task`. Python `ContextVar` values do not propagate across task boundaries by default. If you use `BaseHTTPMiddleware` and set a `ContextVar` before `call_next()`, the downstream route handler may not see the value.

The `ExtractTokenMiddleware` in `server/main.py` is a pure ASGI middleware that calls `self.app(scope, receive, send)` directly — no task boundary, no ContextVar loss.

---

## Related

- `AUTHZ-PATTERNS.md` — token map, OBO patterns, scope reference, debugging
- `README.md` — tab overview, architecture diagram, pre-demo checklist
- `DEMO-GUIDE.md` — full walkthrough, troubleshooting, rebuild procedure
- `mcp-server/server/main.py` — `ExtractTokenMiddleware` implementation
- `app/app.py:1454` — `_mcp_call()` function that forwards the Bearer token
- `mcp-server/app.yaml:25` — where `authorization: disabled` is set
- Fieldkit: `mcp/custom-mcp.md` — custom MCP server template
- Fieldkit: `mcp/connect-external-clients.md` — mcp-remote + OAuth setup
