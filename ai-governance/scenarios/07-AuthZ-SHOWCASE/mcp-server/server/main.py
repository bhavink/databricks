"""
main.py — Custom MCP server for the AI Auth Showcase.

Auth patterns follow Databricks best practices:
  - OBO User (on behalf of user): ensures users only see data they have
    access to via Unity Catalog row filters and column masks. The user's
    OAuth token (with `sql` scope via User Authorization) is forwarded
    from the Streamlit app and used directly for SQL execution via httpx.
    `current_user()` returns the human email; audit records the human.

  - OBO SP (on behalf of service principal): ensures the app can access
    data/resources regardless of user permissions. Used for system-level
    queries (CRM sync) where individual user identity is not required.
    The SP's credentials are auto-discovered from env vars.

Tools:
  get_deal_approval_status (OBO User):
    SQL executes as the user → UC row filters fire automatically.
    Reps see only their deals; managers/finance/execs see all.
    Audit trail records the human email, not the SP UUID.

  submit_deal_for_approval (OBO User):
    SQL executes as the user → UC row filters enforce who can submit.
    Approval record uses current_user() for the submitted_by field.

  get_crm_sync_status (OBO SP / M2M):
    WorkspaceClient() with no args uses the app SP's credentials.
    CRM sync is a system-level query — user identity is not required.

Environment variables (injected by Databricks Apps automatically):
  DATABRICKS_HOST           workspace URL
  DATABRICKS_CLIENT_ID      app SP application UUID
  DATABRICKS_CLIENT_SECRET  app SP secret
  SQL_WAREHOUSE_ID          SQL warehouse for statement execution
"""

import contextvars
import logging
import os
import sys
from datetime import datetime, timezone

import httpx
_MLFLOW_IMPORT_ERROR = ""
try:
    import mlflow
    _MLFLOW_AVAILABLE = True
except (ImportError, Exception) as _e:
    _MLFLOW_AVAILABLE = False
    _MLFLOW_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"
    # Provide no-op stubs so @mlflow.trace decorators don't crash
    class _mlflow_stub:
        @staticmethod
        def trace(*args, **kwargs):
            def decorator(fn): return fn
            return decorator
        @staticmethod
        def update_current_trace(**kwargs): pass
    mlflow = _mlflow_stub()
import uvicorn
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import Disposition, StatementState
from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp, Receive, Scope, Send

# Service name tag for all traces from this server
_SERVICE_NAME = os.environ.get("SERVICE_NAME", "app-b-mcp-server")

logger = logging.getLogger(__name__)

# ── Tracing Init (Module B) ──────────────────────────────────────────────────
_TRACING_ENABLED = False
_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "")
if _EXPERIMENT_NAME and _MLFLOW_AVAILABLE:
    try:
        # mlflow-tracing requires explicit destination configuration.
        # MLFLOW_EXPERIMENT_NAME alone isn't enough — we must call set_destination().
        os.environ.setdefault("MLFLOW_TRACKING_URI", "databricks")
        os.environ.setdefault("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", "true")
        os.environ.setdefault("MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS", "10")
        os.environ.setdefault("MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE", "1000")
        os.environ.setdefault("MLFLOW_TRACE_SAMPLING_RATIO", "1.0")
        from mlflow.tracing import set_destination
        from mlflow.tracing.destination import Databricks
        set_destination(Databricks(experiment_name=_EXPERIMENT_NAME))
        _TRACING_ENABLED = True
        logger.info("Tracing enabled: experiment=%s (destination set)", _EXPERIMENT_NAME)
    except Exception as e:
        logger.warning("Tracing init failed: %s — continuing without tracing", e)

mcp = FastMCP("authz-showcase-mcp", stateless_http=True)

SQL_WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "")
CATALOG = "authz_showcase"
SCHEMA  = "sales"

# ContextVar holding the caller's verified email (from X-Forwarded-Email).
_request_caller: contextvars.ContextVar[str] = contextvars.ContextVar("request_caller", default="")

# ContextVar holding ALL raw request headers.
_request_headers: contextvars.ContextVar[dict] = contextvars.ContextVar("request_headers", default={})


class ExtractTokenMiddleware:
    """Capture the caller's identity and token from proxy-injected headers.

    Uses pure ASGI middleware (not BaseHTTPMiddleware) to avoid the known
    ContextVar propagation issue where BaseHTTPMiddleware runs call_next in a
    new task, breaking ContextVar inheritance.

    The Databricks Apps proxy (when auth is disabled) passes through:
      X-Forwarded-Email        — caller's email (set by upstream proxy)
      X-Forwarded-Access-Token — user's OAuth JWT (with sql scope via User Auth)
      Authorization            — Bearer token forwarded by the Streamlit app
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = {k.lower(): v for k, v in scope.get("headers", [])}

            all_headers = {k.decode("utf-8", errors="replace"): v.decode("utf-8", errors="replace")
                           for k, v in headers.items()}
            ctx_h = _request_headers.set(all_headers)

            caller_email = headers.get(b"x-forwarded-email", b"").decode("utf-8")
            ctx_c = _request_caller.set(caller_email)

            try:
                await self.app(scope, receive, send)
            finally:
                _request_caller.reset(ctx_c)
                _request_headers.reset(ctx_h)
            return
        await self.app(scope, receive, send)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _workspace_host() -> str:
    """Return the workspace URL with https:// prefix."""
    host = os.environ.get("DATABRICKS_HOST", "")
    if host and not host.startswith("http"):
        host = f"https://{host}"
    return host


def _user_token() -> str:
    """Return the user's OBO OAuth token from the forwarded request headers.

    When called directly from the Streamlit app (Tab 4), the user's token
    arrives as x-forwarded-access-token (injected by the Databricks Apps proxy).

    When called via UC External MCP proxy (Tab 6), the Authorization header
    carries the stored bearer token from the UC connection — NOT the calling
    user's identity. We must NOT use that for OBO SQL.

    Only x-forwarded-access-token represents a verified human identity.
    """
    headers = _request_headers.get({})
    return headers.get("x-forwarded-access-token", "")


def _has_user_token() -> bool:
    """Check whether a user OBO token is available in the request."""
    return bool(_user_token())


@mlflow.trace(name="mcp_server.obo_sql", span_type="SQL")
def _obo_sql(statement: str) -> list[list]:
    """Execute SQL as the user via their OAuth token (OBO User pattern).

    Uses httpx directly to call the Statement Execution API, bypassing the
    SDK to avoid the PAT+OAuth env var conflict (DATABRICKS_CLIENT_ID/SECRET
    are in the environment, causing 'more than one authorization method').

    Best practice: Use OBO User to ensure the user only sees data they have
    access to. UC row filters and column masks fire as current_user() = human.

    Returns rows as list of lists. Raises on failure.
    """
    token = _user_token()
    if not token:
        raise RuntimeError("No user token available — cannot execute OBO SQL")

    resp = httpx.post(
        f"{_workspace_host()}/api/2.0/sql/statements",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "warehouse_id": SQL_WAREHOUSE_ID,
            "statement": statement,
            "disposition": "INLINE",
            "wait_timeout": "30s",
        },
        timeout=35,
    )
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(
            f"OBO SQL failed [{resp.status_code}]: empty or non-JSON response "
            f"(token may lack 'sql' scope — via UC proxy, use M2M instead)"
        )
    if resp.status_code == 200 and data.get("status", {}).get("state") == "SUCCEEDED":
        return data.get("result", {}).get("data_array", [])
    error = data.get("status", {}).get("error", {})
    msg = error.get("message", str(data)) if isinstance(error, dict) else str(error)
    state = data.get("status", {}).get("state", "UNKNOWN")
    raise RuntimeError(f"OBO SQL failed [{state}]: {msg}")


@mlflow.trace(name="mcp_server.m2m_sql", span_type="SQL")
def _m2m_sql(statement: str) -> list[list]:
    """Execute SQL as the app SP (OBO SP / M2M pattern).

    Best practice: Use OBO SP for system-level queries where the app needs
    access regardless of individual user permissions.

    Returns rows as list of lists. Raises on failure.
    """
    w = WorkspaceClient()
    result = w.statement_execution.execute_statement(
        warehouse_id=SQL_WAREHOUSE_ID,
        statement=statement,
        wait_timeout="30s",
        disposition=Disposition.INLINE,
    )
    state = result.status.state
    if state != StatementState.SUCCEEDED:
        err = result.status.error
        raise RuntimeError(f"M2M SQL failed [{state}]: {err.message if err else 'unknown error'}")
    if result.result and result.result.data_array:
        return result.result.data_array
    return []


def _caller_email() -> str:
    """Return the proxy-verified caller email from X-Forwarded-Email."""
    return _request_caller.get("")


def _safe(value: str) -> str:
    """Escape single quotes for SQL string literals."""
    return value.replace("'", "''")


# ── Tool 0: debug_auth_context (educational) ─────────────────────────────────

@mcp.tool()
def debug_auth_context(call_source: str = "auto") -> dict:
    """Trace the full authentication chain — shows exactly how identity and
    credentials flow through each proxy hop to reach this MCP server.

    Use this tool to understand the auth architecture before calling any
    data tools. It reveals which proxies injected which headers, whose
    identity is being used, and which SQL execution path will fire.

    Args:
        call_source: How this server was reached. Pass "direct" when calling
            from Tab 4 (Streamlit → MCP server URL), or "uc_proxy" when
            calling via Tab 6 (Streamlit → UC External MCP Proxy → MCP server).
            Defaults to "auto" which infers from available headers.
    """
    headers = _request_headers.get({})
    has_xfat = bool(headers.get("x-forwarded-access-token", ""))
    has_auth = bool(headers.get("authorization", ""))
    has_xfe = bool(headers.get("x-forwarded-email", ""))
    xf_user = headers.get("x-forwarded-user", "")
    xf_pref = headers.get("x-forwarded-preferred-username", "")
    caller = headers.get("x-forwarded-email", "(unknown)")

    # Detect call path: explicit hint or auto-detect
    if call_source == "uc_proxy":
        via_uc_proxy = True
    elif call_source == "direct":
        via_uc_proxy = False
    else:
        # Auto-detect: if Authorization header is present alongside
        # x-forwarded-access-token, it's likely the stored bearer from UC proxy.
        # If only x-forwarded-access-token, it's a direct call through Apps proxy.
        via_uc_proxy = has_auth and has_xfat
    conn_name = "authz_showcase_custmcp_conn" if via_uc_proxy else ""

    # Build the proxy chain narrative
    if via_uc_proxy:
        call_path = "Tab 6 -> UC External MCP Proxy -> this server"
        proxy_chain = [
            {
                "hop": 1,
                "proxy": "Databricks Apps Proxy (Streamlit app)",
                "what_it_does": (
                    "Authenticates the browser user via OAuth. Injects "
                    "x-forwarded-access-token (user's OBO JWT) and "
                    "x-forwarded-email (verified user identity) into the "
                    "request to the Streamlit app backend."
                ),
            },
            {
                "hop": 2,
                "proxy": "UC External MCP Proxy (/api/2.0/mcp/external/{conn})",
                "what_it_does": (
                    f"Streamlit calls this Databricks API with the user's token. "
                    f"The proxy looks up UC connection '{conn_name}', checks that "
                    f"the caller has USE CONNECTION privilege, retrieves the stored "
                    f"bearer credential, and forwards it as the Authorization header "
                    f"to the target MCP server. Critically, it also re-injects "
                    f"x-forwarded-email and x-forwarded-access-token so the target "
                    f"server knows WHO made the original request."
                ),
            },
            {
                "hop": 3,
                "proxy": "Databricks Apps Proxy (this MCP server)",
                "what_it_does": (
                    "Since this app has authorization: disabled, the Apps Proxy "
                    "passes ALL headers through unchanged — including the identity "
                    "headers from the UC proxy and the stored bearer token."
                ),
            },
        ]
        sql_decision = (
            "The x-forwarded-access-token is present (from the UC proxy) but it "
            "typically lacks the 'sql' scope needed for direct SQL execution — "
            "the token was scoped for the UC proxy call, not for the Statement "
            "Execution API. So we TRY OBO SQL first, and when it fails, we FALL "
            "BACK to M2M SQL using this app's own service principal credentials. "
            "The caller's email is still captured from x-forwarded-email for "
            "audit and display purposes."
        )
    else:
        call_path = "Tab 4 -> direct call -> this server"
        proxy_chain = [
            {
                "hop": 1,
                "proxy": "Databricks Apps Proxy (Streamlit app)",
                "what_it_does": (
                    "Authenticates the browser user via OAuth. Injects "
                    "x-forwarded-access-token (user's OBO JWT with 'sql' scope "
                    "from User Authorization config) and x-forwarded-email "
                    "(verified user identity)."
                ),
            },
            {
                "hop": 2,
                "proxy": "Databricks Apps Proxy (this MCP server)",
                "what_it_does": (
                    "The Streamlit app calls this MCP server's URL directly. "
                    "Since authorization: disabled, the Apps Proxy passes through "
                    "the user's token in x-forwarded-access-token unchanged. "
                    "No credential substitution happens — the user's own JWT "
                    "reaches the server."
                ),
            },
        ]
        sql_decision = (
            "The x-forwarded-access-token carries the user's OBO JWT with 'sql' "
            "scope (configured via User Authorization in the Databricks UI). "
            "OBO SQL executes directly as this user — Unity Catalog row filters "
            "and column masks fire under current_user() = the human's email. "
            "Audit trail records the human, not the service principal."
        )

    # Identity headers summary
    identity_headers = {
        "x-forwarded-email": caller,
        "x-forwarded-user": xf_user or "(not present)",
        "x-forwarded-preferred-username": xf_pref or "(not present)",
        "x-forwarded-access-token": "present (OBO JWT)" if has_xfat else "(not present)",
        "authorization": "present (stored bearer)" if has_auth else "(not present)",
    }

    # UC proxy metadata headers (only present via Tab 6)
    uc_proxy_headers = {}
    for k, v in sorted(headers.items()):
        if k.startswith("x-databricks-"):
            uc_proxy_headers[k] = v

    return {
        "call_path": call_path,
        "caller_identity": caller,
        "sql_execution_path": "OBO User (direct)" if not via_uc_proxy and has_xfat
            else "M2M fallback (OBO token lacks sql scope)" if via_uc_proxy
            else "M2M (no user token present)",
        "proxy_chain": proxy_chain,
        "sql_path_explanation": sql_decision,
        "identity_headers": identity_headers,
        "uc_proxy_metadata": uc_proxy_headers if uc_proxy_headers else "(none — direct call, not via UC proxy)",
    }


# ── Tool 1: get_deal_approval_status (OBO User) ──────────────────────────────

@mcp.tool()
def get_deal_approval_status(opp_id: str) -> dict:
    """Return the current approval status for a deal opportunity.

    Auth pattern: OBO User — SQL executes as the calling user's identity.
    UC row filters on `opportunities` fire automatically via current_user(),
    so reps see only their deals and managers see all. No manual WHERE
    clause needed — Unity Catalog enforces access.

    The audit trail in system.access.audit records the human email
    (not the SP UUID) because the user's token executes the query.

    Args:
        opp_id: Opportunity ID (e.g. "OPP001").

    Returns:
        Dict with opp_id, deal_name, stage, amount, approval_status,
        approver, submitted_by, and caller_identity.
    """
    return _get_deal_approval_status_impl(opp_id)


@mlflow.trace(name="mcp_server.get_deal_approval_status")
def _get_deal_approval_status_impl(opp_id: str) -> dict:
    caller = _caller_email()
    opp_id = opp_id.lower()
    if _TRACING_ENABLED:
        mlflow.update_current_trace(
            tags={"service_name": _SERVICE_NAME, "tool": "get_deal_approval_status",
                  "caller": caller, "auth_pattern": "OBO_USER"},
        )

    # Try OBO User first (direct call from Streamlit app), fall back to M2M
    # (UC proxy path where x-forwarded-access-token may lack sql scope).
    opp_query = f"""
        SELECT opp_id, customer_id, stage, amount
        FROM   {CATALOG}.{SCHEMA}.opportunities
        WHERE  opp_id = '{_safe(opp_id)}'
        LIMIT  1
    """
    if _has_user_token():
        try:
            opp_rows = _obo_sql(opp_query)
            auth_pattern = "OBO User \u2014 UC row filters fire as current_user()"
        except RuntimeError:
            # Token present but OBO SQL failed (e.g., missing sql scope via UC proxy)
            opp_rows = _m2m_sql(opp_query)
            auth_pattern = "M2M fallback \u2014 OBO token present but lacks sql scope"
    else:
        opp_rows = _m2m_sql(opp_query)
        auth_pattern = "M2M (via UC proxy) \u2014 stored bearer token, SP identity"
        caller = caller or "stored-credential-identity"

    if not opp_rows:
        return {
            "error":           f"Opportunity {opp_id!r} not found or not accessible.",
            "caller_identity": caller,
            "auth_pattern":    auth_pattern,
            "hint":            "UC row filter may be restricting access — you can only see deals you own.",
        }

    opp = opp_rows[0]

    # Approval status query — use M2M for consistency (already determined path)
    sql_fn = _m2m_sql if "M2M" in auth_pattern else _obo_sql
    try:
        req_rows = sql_fn(f"""
            SELECT status, approver, submitted_by, created_at
            FROM   {CATALOG}.{SCHEMA}.approval_requests
            WHERE  opp_id = '{_safe(opp_id)}'
            ORDER  BY created_at DESC
            LIMIT  1
        """)
    except RuntimeError:
        req_rows = []

    if req_rows:
        req = req_rows[0]
        approval_status = req[0]
        approver        = req[1] or "pending assignment"
        submitted_by    = req[2]
        submitted_at    = str(req[3])
    else:
        approval_status = "NOT_SUBMITTED"
        approver        = "N/A"
        submitted_by    = "N/A"
        submitted_at    = "N/A"

    return {
        "opp_id":          opp[0],
        "customer_id":     opp[1],
        "stage":           opp[2],
        "amount":          float(opp[3]) if opp[3] is not None else None,
        "approval_status": approval_status,
        "approver":        approver,
        "submitted_by":    submitted_by,
        "submitted_at":    submitted_at,
        "caller_identity": caller,
        "auth_pattern":    auth_pattern,
    }


# ── Tool 2: submit_deal_for_approval (OBO User) ──────────────────────────────

@mcp.tool()
def submit_deal_for_approval(opp_id: str, justification: str) -> dict:
    """Submit a deal opportunity for manager approval.

    Auth pattern: OBO User — SQL executes as the calling user.
    The approval record's submitted_by = current_user() = human email.
    UC row filters restrict which opportunities the user can see/submit.
    The audit trail records the human email for full accountability.

    Args:
        opp_id:        Opportunity ID to submit (e.g. "OPP001").
        justification: Business justification for the approval request.

    Returns:
        Dict with submission result, opp details, and caller identity.
    """
    return _submit_deal_for_approval_impl(opp_id, justification)


@mlflow.trace(name="mcp_server.submit_deal_for_approval")
def _submit_deal_for_approval_impl(opp_id: str, justification: str) -> dict:
    caller = _caller_email()
    opp_id = opp_id.lower()
    if _TRACING_ENABLED:
        mlflow.update_current_trace(
            tags={"service_name": _SERVICE_NAME, "tool": "submit_deal_for_approval",
                  "caller": caller, "auth_pattern": "OBO_USER"},
        )

    # Choose SQL executor: OBO User if token present, M2M fallback if OBO fails
    opp_query = f"""
        SELECT opp_id, customer_id, stage, amount
        FROM   {CATALOG}.{SCHEMA}.opportunities
        WHERE  opp_id = '{_safe(opp_id)}'
        LIMIT  1
    """
    if _has_user_token():
        try:
            opp_rows = _obo_sql(opp_query)
            sql_fn = _obo_sql
            auth_pattern = "OBO User \u2014 UC row filters fire as current_user()"
        except RuntimeError:
            # Token present but OBO SQL failed (e.g., missing sql scope via UC proxy)
            opp_rows = _m2m_sql(opp_query)
            sql_fn = _m2m_sql
            auth_pattern = "M2M fallback \u2014 OBO token present but lacks sql scope"
    else:
        opp_rows = _m2m_sql(opp_query)
        sql_fn = _m2m_sql
        auth_pattern = "M2M (via UC proxy) \u2014 stored bearer token, SP identity"
        caller = caller or "stored-credential-identity"

    if not opp_rows:
        return {
            "submitted": False,
            "error":     f"Opportunity {opp_id!r} not found or not accessible.",
            "hint":      "UC row filter restricts access — you can only submit deals you own.",
            "caller_identity": caller,
            "auth_pattern": auth_pattern,
        }

    opp   = opp_rows[0]
    stage = opp[2]
    approvable_stages = {"PROPOSAL", "NEGOTIATION"}
    if stage not in approvable_stages:
        return {
            "submitted":       False,
            "opp_id":          opp_id,
            "customer_id":     opp[1],
            "stage":           stage,
            "error":           f"Stage '{stage}' is not approvable. Only PROPOSAL and NEGOTIATION deals require approval.",
            "caller_identity": caller,
            "auth_pattern":    auth_pattern,
        }

    try:
        sql_fn(f"""
            INSERT INTO {CATALOG}.{SCHEMA}.approval_requests
              (opp_id, submitted_by, justification, status, created_at, updated_at)
            VALUES
              ('{_safe(opp_id)}', '{_safe(caller)}', '{_safe(justification)}',
               'PENDING', current_timestamp(), current_timestamp())
        """)
    except RuntimeError as e:
        return {"submitted": False, "error": str(e), "caller_identity": caller,
                "auth_pattern": auth_pattern}

    return {
        "submitted":       True,
        "opp_id":          opp[0],
        "customer_id":     opp[1],
        "stage":           stage,
        "amount":          float(opp[3]) if opp[3] is not None else None,
        "submitted_by":    caller,
        "status":          "PENDING",
        "message":         f"Approval request submitted for opp '{opp[0]}' (customer {opp[1]}). Your manager will be notified.",
        "auth_pattern":    auth_pattern,
    }


# ── Tool 3: get_crm_sync_status (OBO SP / M2M) ──────────────────────────────

@mcp.tool()
def get_crm_sync_status(customer_id: str) -> dict:
    """Return the CRM synchronisation status for a customer account.

    Auth pattern: OBO SP (M2M) — uses the app SP credentials.
    Best practice: use OBO SP to ensure the app can access data regardless
    of user permissions. CRM sync is a system-level operation; individual
    user identity is not required and would add unnecessary scope.

    Args:
        customer_id: Customer ID (e.g. "CUST01").

    Returns:
        Dict with customer details and CRM sync metadata.
    """
    return _get_crm_sync_status_impl(customer_id)


@mlflow.trace(name="mcp_server.get_crm_sync_status")
def _get_crm_sync_status_impl(customer_id: str) -> dict:
    caller = _caller_email()
    customer_id = customer_id.lower()
    if _TRACING_ENABLED:
        mlflow.update_current_trace(
            tags={"service_name": _SERVICE_NAME, "tool": "get_crm_sync_status",
                  "caller": caller or "system", "auth_pattern": "OBO_SP_M2M"},
        )

    w = WorkspaceClient()
    sp_identity = w.current_user.me().user_name

    rows = _m2m_sql(f"""
        SELECT customer_id, name, region, tier, contract_value
        FROM   {CATALOG}.{SCHEMA}.customers
        WHERE  customer_id = '{_safe(customer_id)}'
        LIMIT  1
    """)
    if not rows:
        return {
            "error":        f"Customer {customer_id!r} not found.",
            "sp_identity":  sp_identity,
        }

    row = rows[0]
    return {
        "customer_id":    row[0],
        "name":           row[1],
        "region":         row[2],
        "tier":           row[3],
        "contract_value": float(row[4]) if row[4] is not None else None,
        "crm_sync": {
            "status":          "SYNCED",
            "last_sync_utc":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "records_synced":  1,
            "source_system":   "Salesforce",
            "next_sync_in":    "4h",
        },
        "auth_pattern":   "OBO SP (M2M) — app SP identity; system-level query",
        "sp_identity":    sp_identity,
    }


# ── Debug tool (for development — remove before production) ──────────────────

@mcp.tool()
def debug_token_scopes() -> dict:
    """Return proxy-injected identity headers and token info for debugging."""
    all_headers = _request_headers.get({})

    safe_headers = {}
    for k, v in all_headers.items():
        if any(s in k.lower() for s in ("authorization", "token", "secret", "cookie")):
            safe_headers[k] = v[:40] + "..." if len(v) > 40 else v
        else:
            safe_headers[k] = v

    # Decode token scopes if JWT
    token = _user_token()
    token_info = {"available": bool(token), "length": len(token)}
    if token and token.count(".") == 2:
        try:
            import base64, json as _json
            payload_b64 = token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            claims = _json.loads(base64.urlsafe_b64decode(payload_b64))
            token_info["type"] = "JWT"
            token_info["scopes"] = claims.get("scp", claims.get("scope", "(no scope claim)"))
            token_info["sub"] = claims.get("sub", "(no sub)")
        except Exception as e:
            token_info["decode_error"] = str(e)

    return {
        "caller_email":    _request_caller.get("(not set)"),
        "x_forwarded_user": all_headers.get("x-forwarded-user", "(not set)"),
        "user_token":      token_info,
        "headers_received": safe_headers,
    }



def main() -> None:
    starlette_app = mcp.streamable_http_app()
    wrapped = ExtractTokenMiddleware(starlette_app)
    uvicorn.run(wrapped, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
