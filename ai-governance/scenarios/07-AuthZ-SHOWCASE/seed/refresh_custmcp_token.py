"""
refresh_custmcp_token.py — Refresh bearer token in authz_showcase_custmcp_conn.

The UC HTTP connection stores a short-lived OAuth token (~1h TTL). Run this before demos.

Why not a PAT?
  Databricks Apps reject PATs (401) — only OAuth tokens are accepted at the Apps proxy layer.
  M2M client_credentials tokens also expire in ~1h. There is no non-expiring credential
  option for Databricks App targets. Pre-demo refresh is the practical workaround.

Why does an expired stored token also block the calling token?
  The UC proxy does upfront credential validation. If the stored credential fails when
  the proxy tries to forward a request, it returns 401 to the caller even if the caller's
  own auth token is perfectly valid.

Usage:
  DATABRICKS_CONFIG_PROFILE=adb-wx1 python refresh_custmcp_token.py
"""

import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import ConnectionType

CONN_NAME     = "authz_showcase_custmcp_conn"
CUSTMCP_HOST  = "https://authz-showcase-custom-mcp-<YOUR_WORKSPACE_ORG_ID>.3.azure.databricksapps.com"
APP_SP_NAME   = "<YOUR_APP_SP_CLIENT_ID>"
WAREHOUSE_ID  = "<YOUR_WAREHOUSE_ID>"

w = WorkspaceClient()
token = w.config.authenticate()["Authorization"].split("Bearer ")[1]

# Delete + recreate (no update API for connection options)
try:
    w.connections.delete(CONN_NAME)
    print(f"Deleted old {CONN_NAME}")
except Exception:
    pass

import requests as _req
resp = _req.post(
    f"{w.config.host}/api/2.0/unity-catalog/connections",
    headers=w.config.authenticate(),
    json={
        "name": CONN_NAME,
        "connection_type": "HTTP",
        "comment": "Custom HTTP Bearer — all callers operate as same identity. USE CONNECTION is the access boundary.",
        "options": {
            "host": CUSTMCP_HOST,
            "base_path": "/mcp",
            "bearer_token": token,
            "is_mcp_connection": "true",
        },
    },
)
resp.raise_for_status()
print(f"Created {CONN_NAME} with fresh token")

w.statement_execution.execute_statement(
    warehouse_id=WAREHOUSE_ID,
    statement=f"GRANT USE CONNECTION ON CONNECTION {CONN_NAME} TO `{APP_SP_NAME}`",
    wait_timeout="30s",
)
print(f"Granted USE CONNECTION to app SP")
print("Done — token valid for ~1h")
