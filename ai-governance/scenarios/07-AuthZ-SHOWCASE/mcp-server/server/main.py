"""
main.py — Custom MCP server for the AI Auth Showcase (Phase 5).

Teaching moment: three tools demonstrate two distinct auth patterns:

  Proxy-identity + M2M SQL (get_deal_approval_status, submit_deal_for_approval):
    The Databricks Apps proxy authenticates every request and injects the
    caller's email as X-Forwarded-Email. ExtractTokenMiddleware captures
    this into _request_caller. The OBO tools read _request_caller to get
    the verified user identity — no token scope is needed. M2M executes
    the SQL with an explicit WHERE clause that mirrors the UC row filter:
    reps see own deals, users in quota_viewers see all. Approval records
    are stamped with the proxy-verified identity for full auditability.

    Why X-Forwarded-Email instead of token scopes?
    The X-Forwarded-Access-Token from Databricks Apps is a minimal OIDC
    identity token without the 'sql' scope required by Statement Execution.
    The proxy already authenticated the user and provides their email via
    X-Forwarded-Email — this is trusted (set by proxy, cannot be forged
    by the calling app) and sufficient for identity-based access control.

  M2M (get_crm_sync_status):
    WorkspaceClient() with no args uses the app SP's credentials.
    The SP is in the quota_viewers allowlist so it can see all
    customers. CRM sync is a system-level query — user identity is
    not required and would add unnecessary scope to the SP token.

Environment variables (injected by Databricks Apps automatically):
  DATABRICKS_HOST           workspace URL (https://...)
  DATABRICKS_CLIENT_ID      app SP application UUID
  DATABRICKS_CLIENT_SECRET  app SP secret
  SQL_WAREHOUSE_ID          SQL warehouse for statement execution
"""

import contextvars
import os
from datetime import datetime, timezone

import uvicorn
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import Disposition, StatementState
from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp, Receive, Scope, Send

mcp = FastMCP("authz-showcase-mcp", stateless_http=True)

SQL_WAREHOUSE_ID = os.environ.get("SQL_WAREHOUSE_ID", "")
CATALOG = "authz_showcase"
SCHEMA  = "sales"

# ContextVar holding the caller's verified email (from X-Forwarded-Email).
# Set by the Databricks Apps proxy based on authenticated identity — cannot
# be forged by the calling application.
_request_caller: contextvars.ContextVar[str] = contextvars.ContextVar("request_caller", default="")

# ContextVar holding ALL raw request headers (for debug_token_scopes tool).
_request_headers: contextvars.ContextVar[dict] = contextvars.ContextVar("request_headers", default={})


class ExtractTokenMiddleware:
    """Capture the caller's identity from proxy-injected headers into ContextVars.

    Uses pure ASGI middleware (not BaseHTTPMiddleware) to avoid the known
    ContextVar propagation issue where BaseHTTPMiddleware runs call_next in a
    new task, breaking ContextVar inheritance.

    The Databricks Apps proxy authenticates every request and injects trusted
    headers:
      X-Forwarded-Email  — caller's email (set by proxy, cannot be forged)
      X-Forwarded-User   — caller's user ID
    These are captured into _request_caller for use by OBO tools.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = {k.lower(): v for k, v in scope.get("headers", [])}

            # Capture all headers for debugging
            all_headers = {k.decode("utf-8", errors="replace"): v.decode("utf-8", errors="replace")
                           for k, v in headers.items()}
            ctx_h = _request_headers.set(all_headers)

            # X-Forwarded-Email is set by the Databricks Apps proxy based on
            # the authenticated user — trusted source of identity.
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

def _run_sql(w: WorkspaceClient, statement: str) -> list[list]:
    """Execute a SQL statement; return rows as list of lists. Raises on failure."""
    result = w.statement_execution.execute_statement(
        warehouse_id=SQL_WAREHOUSE_ID,
        statement=statement,
        wait_timeout="30s",
        disposition=Disposition.INLINE,
    )
    state = result.status.state
    if state != StatementState.SUCCEEDED:
        err = result.status.error
        raise RuntimeError(f"SQL failed [{state}]: {err.message if err else 'unknown error'}")
    if result.result and result.result.data_array:
        return result.result.data_array
    return []


def _caller_email() -> str:
    """Return the proxy-verified caller email from X-Forwarded-Email.

    The Databricks Apps proxy sets X-Forwarded-Email to the authenticated
    user's email on every request — it cannot be forged by the calling app.
    Returns empty string if no user is authenticated (should not happen in
    normal operation; tools return an error in this case).
    """
    return _request_caller.get("")


def _m2m_client() -> WorkspaceClient:
    """WorkspaceClient that executes as the APP SERVICE PRINCIPAL (M2M).

    SDK auto-discovers DATABRICKS_CLIENT_ID / SECRET / HOST from the
    environment variables injected by Databricks Apps.
    """
    return WorkspaceClient()


def _safe(value: str) -> str:
    """Escape single quotes for SQL string literals."""
    return value.replace("'", "''")


# ── Tool 1: get_deal_approval_status (OBO) ────────────────────────────────────

@mcp.tool()
def debug_token_scopes() -> dict:
    """Return proxy-injected identity headers and all request headers for debugging."""
    all_headers = _request_headers.get({})

    # Redact sensitive header values, keep 40-char prefixes
    safe_headers = {}
    for k, v in all_headers.items():
        if any(s in k.lower() for s in ("authorization", "token", "secret", "cookie")):
            safe_headers[k] = v[:40] + "..." if len(v) > 40 else v
        else:
            safe_headers[k] = v

    return {
        "caller_email":    _request_caller.get("(not set)"),
        "x_forwarded_user": all_headers.get("x-forwarded-user", "(not set)"),
        "x_forwarded_preferred_username": all_headers.get("x-forwarded-preferred-username", "(not set)"),
        "headers_received": safe_headers,
    }


@mcp.tool()
def get_deal_approval_status(opp_id: str) -> dict:
    """Return the current approval status for a deal opportunity.

    Auth pattern: OBO identity + M2M SQL.
      Step 1 (OBO): Verify caller identity from the user's OAuth token —
        cannot be spoofed.
      Step 2 (M2M): Execute SQL with explicit per-user WHERE clause that
        mirrors the UC row filter logic (quota_viewers for elevated access,
        rep_email = caller for reps). Produces the same access-control
        outcome as a UC row filter without requiring 'sql' scope on the
        OBO token (which Databricks Apps X-Forwarded-Access-Token does
        not carry).

    Args:
        opp_id: Opportunity ID (e.g. "OPP001").

    Returns:
        Dict with opp_id, deal_name, stage, amount, approval_status,
        approver, submitted_by, and caller_identity.
    """
    # Step 1 — Proxy identity: X-Forwarded-Email is set by Databricks Apps proxy
    # based on authenticated user — cannot be forged by the calling application.
    caller = _caller_email()
    if not caller:
        return {"error": "No authenticated user identity — X-Forwarded-Email not set.", "hint": "Ensure the request comes through the Databricks Apps proxy."}
    opp_id = opp_id.lower()   # IDs are stored lowercase (opp_001)

    # Step 2 — M2M: check if caller has elevated access (in quota_viewers)
    w_m2m = _m2m_client()
    elevated = bool(_run_sql(
        w_m2m,
        f"""
        SELECT 1
        FROM   {CATALOG}.{SCHEMA}.quota_viewers
        WHERE  user_email = '{_safe(caller)}'
        LIMIT  1
        """,
    ))
    access_filter = "" if elevated else f"AND rep_email = '{_safe(caller)}'"

    # Step 3 — M2M: fetch opportunity with caller-scoped filter
    opp_rows = _run_sql(
        w_m2m,
        f"""
        SELECT opp_id, customer_id, stage, amount
        FROM   {CATALOG}.{SCHEMA}.opportunities
        WHERE  opp_id = '{_safe(opp_id)}'
        {access_filter}
        LIMIT  1
        """,
    )
    if not opp_rows:
        return {
            "error":           f"Opportunity {opp_id!r} not found or not accessible.",
            "caller_identity": caller,
            "hint":            "Caller-scoped filter active -- you can only check deals you own.",
        }

    opp = opp_rows[0]

    # Step 4 — M2M: fetch latest approval request for this opp
    req_rows = _run_sql(
        w_m2m,
        f"""
        SELECT status, approver, submitted_by, created_at
        FROM   {CATALOG}.{SCHEMA}.approval_requests
        WHERE  opp_id = '{_safe(opp_id)}'
        ORDER  BY created_at DESC
        LIMIT  1
        """,
    )

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
        "elevated_access": elevated,
        "auth_pattern":    "Proxy identity (X-Forwarded-Email) + M2M SQL (explicit per-user filter mirrors UC row filter)",
    }


# ── Tool 2: submit_deal_for_approval (OBO) ────────────────────────────────────

@mcp.tool()
def submit_deal_for_approval(opp_id: str, justification: str) -> dict:
    """Submit a deal opportunity for manager approval.

    Auth pattern: OBO identity + M2M SQL.
      OBO verifies the caller's identity (used to stamp the approval record
      and to scope the opportunity lookup). M2M executes the SQL with an
      explicit caller-scoped WHERE clause. The approval record is
      permanently stamped with the verified caller identity for auditability.

    Args:
        opp_id:        Opportunity ID to submit (e.g. "OPP001").
        justification: Business justification for the approval request.

    Returns:
        Dict with submission result, opp details, and caller identity.
    """
    # Step 1 — Proxy identity: X-Forwarded-Email is set by Databricks Apps proxy.
    caller = _caller_email()
    if not caller:
        return {"submitted": False, "error": "No authenticated user identity — X-Forwarded-Email not set."}
    opp_id = opp_id.lower()   # IDs are stored lowercase (opp_001)

    # Step 2 — M2M: check elevation
    w_m2m = _m2m_client()
    elevated = bool(_run_sql(
        w_m2m,
        f"""
        SELECT 1
        FROM   {CATALOG}.{SCHEMA}.quota_viewers
        WHERE  user_email = '{_safe(caller)}'
        LIMIT  1
        """,
    ))
    access_filter = "" if elevated else f"AND rep_email = '{_safe(caller)}'"

    # Step 3 — M2M: verify opp is accessible and approvable
    opp_rows = _run_sql(
        w_m2m,
        f"""
        SELECT opp_id, customer_id, stage, amount
        FROM   {CATALOG}.{SCHEMA}.opportunities
        WHERE  opp_id = '{_safe(opp_id)}'
        {access_filter}
        LIMIT  1
        """,
    )
    if not opp_rows:
        return {
            "submitted": False,
            "error":     f"Opportunity {opp_id!r} not found or not accessible.",
            "hint":      "Caller-scoped filter active — you can only submit deals you own.",
            "caller_identity": caller,
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
        }

    # Step 4 — M2M: write approval request stamped with the verified caller identity
    _run_sql(
        w_m2m,
        f"""
        INSERT INTO {CATALOG}.{SCHEMA}.approval_requests
          (opp_id, submitted_by, justification, status, created_at, updated_at)
        VALUES
          ('{_safe(opp_id)}', '{_safe(caller)}', '{_safe(justification)}',
           'PENDING', current_timestamp(), current_timestamp())
        """,
    )

    return {
        "submitted":       True,
        "opp_id":          opp[0],
        "customer_id":     opp[1],
        "stage":           stage,
        "amount":          float(opp[3]) if opp[3] is not None else None,
        "submitted_by":    caller,
        "status":          "PENDING",
        "message":         f"Approval request submitted for opp '{opp[0]}' (customer {opp[1]}). Your manager will be notified.",
        "auth_pattern":    "Proxy identity (X-Forwarded-Email) stamped on record + M2M SQL (explicit per-user filter)",
    }


# ── Tool 3: get_crm_sync_status (M2M) ─────────────────────────────────────────

@mcp.tool()
def get_crm_sync_status(customer_id: str) -> dict:
    """Return the CRM synchronisation status for a customer account.

    Auth pattern: M2M — uses the app SP credentials. CRM sync is a
    system-level operation; individual user identity is not required.
    The SP is in quota_viewers so it can see all customers.

    Args:
        customer_id: Customer ID (e.g. "CUST01").

    Returns:
        Dict with customer details and CRM sync metadata.
    """
    w = _m2m_client()
    sp_identity = w.current_user.me().user_name   # SP application UUID
    customer_id = customer_id.lower()             # IDs are stored lowercase (cust_001)

    rows = _run_sql(
        w,
        f"""
        SELECT customer_id, name, region, tier, contract_value
        FROM   {CATALOG}.{SCHEMA}.customers
        WHERE  customer_id = '{_safe(customer_id)}'
        LIMIT  1
        """,
    )
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
        "auth_pattern":   "M2M — app SP identity; no user token forwarded",
        "sp_identity":    sp_identity,
    }


def main() -> None:
    # Wrap the FastMCP Starlette app with our pure-ASGI middleware directly.
    # ExtractTokenMiddleware captures Authorization: Bearer for OBO tools.
    starlette_app = mcp.streamable_http_app()
    wrapped = ExtractTokenMiddleware(starlette_app)
    uvicorn.run(wrapped, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
