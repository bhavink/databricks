"""
08_create_external_mcp_conn.py — Phase 6: External MCP via UC HTTP Connections

Creates two UC HTTP connections for Tab 6 "External Intelligence":

  1. authz_showcase_github_conn  (Managed OAuth)
     → GitHub MCP installed from Databricks Marketplace
     → Per-user auth: each user completes GitHub OAuth once; Databricks caches tokens
     → Install via UI: Workspace → Marketplace → Agents → MCP Servers → GitHub

  2. authz_showcase_custmcp_conn  (Custom HTTP Bearer)
     → Points to the already-deployed authz-showcase-custom-mcp Databricks App
     → Shared bearer token stored in UC — all callers operate as the SP through this connection
     → Demonstrates the Custom HTTP connection pattern with zero new infrastructure

Teaching moment: USE CONNECTION privilege is the governance layer.
  GRANT  → tools appear in the agent's tool list
  REVOKE → tools vanish immediately, no code change needed

Run:
  DATABRICKS_CONFIG_PROFILE=<YOUR_CLI_PROFILE> \
  CUSTMCP_APP_HOST=<YOUR_CUSTMCP_APP_HOST> \
  SP_BEARER_TOKEN=$(databricks auth token --profile <YOUR_CLI_PROFILE> | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])") \
  python 08_create_external_mcp_conn.py

⚠️  The bearer token is a short-lived Databricks OAuth token (~1 hour). The connection must be
    recreated with a fresh token before each demo session. Add to your demo-prep checklist:

    1. Run this script (or use 10_onboard_app_sp.py --refresh-conn) to refresh the token.
    2. For production, replace with an SP M2M token from a dedicated client credentials flow.

Credentials come exclusively from environment variables — nothing hardcoded.
"""

import os
import sys
import requests

from databricks.sdk import WorkspaceClient

# ── Config from environment ────────────────────────────────────────────────────
CUSTMCP_APP_HOST = os.environ.get("CUSTMCP_APP_HOST", "")
SP_BEARER_TOKEN  = os.environ.get("SP_BEARER_TOKEN", "")   # M2M OAuth token for app SP

APP_SP_NAME = "<YOUR_APP_SP_CLIENT_ID>"       # authz-showcase app SP UUID


def create_github_conn(w: WorkspaceClient) -> None:
    """Install GitHub MCP from Marketplace (UI step), then record the connection name.

    The Managed OAuth connection is created automatically by the Marketplace installer —
    this function just verifies it exists and grants the app SP access.

    Manual install steps (one-time UI):
      1. Workspace → Marketplace → Agents → MCP Servers → GitHub → Install
      2. Connection name: authz_showcase_github_conn
      3. Credential type: Managed OAuth
    """
    conn_name = "authz_showcase_github_conn"
    try:
        conn = w.connections.get(conn_name)
        print(f"✅ GitHub connection exists: {conn.name} (type={conn.connection_type})")
    except Exception as e:
        print(
            f"⚠️  GitHub connection '{conn_name}' not found: {e}\n"
            "   Install via: Workspace → Marketplace → Agents → MCP Servers → GitHub → Install\n"
            "   Use connection name: authz_showcase_github_conn"
        )
        return

    # Grant USE CONNECTION to app SP so it can proxy GitHub requests
    try:
        w.statement_execution.execute_statement(
            warehouse_id=_get_warehouse_id(w),
            statement=f"GRANT USE CONNECTION ON CONNECTION {conn_name} TO `{APP_SP_NAME}`",
            wait_timeout="30s",
        )
        print(f"✅ GRANT USE CONNECTION ON {conn_name} TO app SP")
    except Exception as e:
        print(f"⚠️  Could not grant USE CONNECTION on {conn_name}: {e}")


def create_custmcp_conn(w: WorkspaceClient) -> None:
    """Create a Custom HTTP Bearer connection pointing to the authz-showcase-custom-mcp app.

    The stored bearer token (SP's M2M OAuth token) is injected by Databricks on every
    proxied request. The custom MCP server sees this token as the Authorization header
    and runs all tools as the SP identity.

    This is the key contrast with Tab 4 (direct OBO):
      Tab 4 direct → user token → tools execute as the user (row filters apply per-user)
      Tab 6 via UC  → SP token  → tools execute as the SP (all data visible, UC governs connection access)
    """
    if not CUSTMCP_APP_HOST or not SP_BEARER_TOKEN:
        print(
            "⚠️  Skipping authz_showcase_custmcp_conn — set CUSTMCP_APP_HOST and SP_BEARER_TOKEN.\n"
            "   Generate SP bearer token:\n"
            "     databricks auth token --profile <YOUR_CLI_PROFILE>\n"
            "   Or via M2M client credentials:\n"
            "     curl -X POST https://<workspace>/oidc/v1/token \\\n"
            "       -d 'grant_type=client_credentials&scope=all-apis' \\\n"
            "       -u '<client_id>:<client_secret>'"
        )
        return

    conn_name = "authz_showcase_custmcp_conn"

    # Delete existing connection if it exists (idempotent re-run)
    try:
        w.connections.delete(conn_name)
        print(f"🔄 Deleted existing connection: {conn_name}")
    except Exception:
        pass

    # Use REST API directly — SDK connections.create does not support HTTP connection type.
    # host MUST include https:// scheme; SDK interprets bare hostname as a cloud storage path.
    host_url = CUSTMCP_APP_HOST if CUSTMCP_APP_HOST.startswith("http") else f"https://{CUSTMCP_APP_HOST}"
    r = requests.post(
        f"{w.config.host}/api/2.1/unity-catalog/connections",
        headers={**w.config.authenticate(), "Content-Type": "application/json"},
        json={
            "name": conn_name,
            "connection_type": "HTTP",
            "comment": (
                "Custom HTTP Bearer connection to authz-showcase-custom-mcp Databricks App. "
                "Stores bearer token — all callers operate as same identity through this connection. "
                "USE CONNECTION privilege is the access control boundary."
            ),
            "options": {
                "host": host_url,
                "base_path": "/mcp",
                "bearer_token": SP_BEARER_TOKEN,   # stored encrypted in UC, never exposed
                "is_mcp_connection": "true",
            },
        },
        timeout=30,
    )
    if not r.ok:
        print(f"❌ Failed to create connection: {r.text}")
        sys.exit(1)
    conn = r.json()
    print(f"✅ Created connection: {conn['name']} → {host_url}/mcp")

    # Grant USE CONNECTION to app SP
    try:
        w.statement_execution.execute_statement(
            warehouse_id=_get_warehouse_id(w),
            statement=f"GRANT USE CONNECTION ON CONNECTION {conn_name} TO `{APP_SP_NAME}`",
            wait_timeout="30s",
        )
        print(f"✅ GRANT USE CONNECTION ON {conn_name} TO app SP")
    except Exception as e:
        print(f"⚠️  Could not grant USE CONNECTION on {conn_name}: {e}")


def verify_connections(w: WorkspaceClient) -> None:
    """Verify both connections exist and are accessible."""
    print("\n── Verification ─────────────────────────────────────────────────────")
    for name in ["authz_showcase_github_conn", "authz_showcase_custmcp_conn"]:
        try:
            conn = w.connections.get(name)
            print(f"✅ {conn.name}: type={conn.connection_type}, comment={conn.comment or '-'}")
        except Exception as e:
            print(f"❌ {name}: {e}")
    print()
    print("Proxy URLs (use these in app.py):")
    host = w.config.host.rstrip("/")
    print(f"  GitHub:     {host}/api/2.0/mcp/external/authz_showcase_github_conn")
    print(f"  Custom MCP: {host}/api/2.0/mcp/external/authz_showcase_custmcp_conn")
    print()
    print("Demo: revoke access and watch tools disappear:")
    print("  REVOKE USE CONNECTION ON CONNECTION authz_showcase_github_conn FROM `<app-sp>`;")
    print("  # → list_tools() returns empty — UC is the control plane, not the agent code")


def _get_warehouse_id(w: WorkspaceClient) -> str:
    """Return the SQL warehouse ID configured in env or fall back to first available."""
    wh_id = os.environ.get("SQL_WAREHOUSE_ID", "<YOUR_WAREHOUSE_ID>")
    if wh_id:
        return wh_id
    warehouses = list(w.warehouses.list())
    if not warehouses:
        raise RuntimeError("No SQL warehouses found")
    return warehouses[0].id


if __name__ == "__main__":
    w = WorkspaceClient()
    print(f"Connected to: {w.config.host}\n")

    print("── Step 1: GitHub MCP (Managed OAuth) ──────────────────────────────")
    create_github_conn(w)

    print("\n── Step 2: Custom MCP bearer connection ─────────────────────────────")
    create_custmcp_conn(w)

    verify_connections(w)
