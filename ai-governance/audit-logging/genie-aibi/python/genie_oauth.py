"""
Genie API OAuth: account-level SP, per-workspace token.
Credentials are read only from Databricks secrets via dbutils.secrets.get(scope, key).
"""
# =============================================================================
# Genie API OAuth — Workspace-Scoped Bearer Token
# =============================================================================
# Purpose:
#   1. Load SP credentials from Databricks secrets (scope, sp_client_id, sp_client_secret).
#   2. Obtain workspace-scoped OIDC token (client_credentials, scope=all-apis).
#   3. Return headers dict (Authorization, Content-Type) for Genie REST API calls.
# =============================================================================
import requests


def get_credentials(dbutils, scope, key_client_id="sp_client_id", key_client_secret="sp_client_secret"):
    """
    Load SP credentials from Databricks secrets. Requires dbutils and scope.
    """
    if not dbutils or not scope:
        raise ValueError("dbutils and scope are required; credentials are read only from secrets.")
    client_id = dbutils.secrets.get(scope=scope, key=key_client_id)
    client_secret = dbutils.secrets.get(scope=scope, key=key_client_secret)
    if not client_id or not client_secret:
        raise ValueError(
            f"Secrets not found: scope={scope}, keys={key_client_id!r}, {key_client_secret!r}. "
            "Create the scope and keys (e.g. via scripts/create_genie_obs_secrets.py)."
        )
    return client_id, client_secret


def get_workspace_token(workspace_url: str, dbutils, scope: str, key_client_id="sp_client_id", key_client_secret="sp_client_secret") -> str:
    """
    Get a workspace-scoped Bearer token for Genie API calls.
    workspace_url: e.g. https://adb-984752964297111.11.azuredatabricks.net (no trailing slash)
    """
    client_id, client_secret = get_credentials(dbutils=dbutils, scope=scope, key_client_id=key_client_id, key_client_secret=key_client_secret)
    base = workspace_url.rstrip("/")
    token_url = f"{base}/oidc/v1/token"
    resp = requests.post(
        token_url,
        data={"grant_type": "client_credentials", "scope": "all-apis"},
        auth=(client_id, client_secret),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_headers_for_workspace(workspace_url: str, dbutils, scope: str, key_client_id="sp_client_id", key_client_secret="sp_client_secret") -> dict:
    """Return headers dict with Bearer token for Genie API. Requires dbutils and scope (secrets only)."""
    token = get_workspace_token(workspace_url, dbutils=dbutils, scope=scope, key_client_id=key_client_id, key_client_secret=key_client_secret)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
