"""
One-off: GET a single Genie message by workspace, space, conversation, message IDs.

Uses Databricks secrets (same as ingestion):
  Scope: genie-obs
  Keys:  sp_client_id, sp_client_secret (service principal for OAuth)
No env vars or config files for credentials; dbutils.secrets.get(scope, key) only.

Run on Databricks (notebook or job) so dbutils is available.

Usage (from notebook):
  %run /Workspace/Users/<you>/genie-analytics/genie observability/python/get_message_by_id
  get_message()   # uses defaults from audit query
  # or:
  get_message(workspace_id="...", space_id="...", conversation_id="...", message_id="...")
"""
from __future__ import annotations

import json
import os
import sys

# Same-folder imports
_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)

import requests
from genie_oauth import get_headers_for_workspace
from genie_message_ingestion import get_dbutils

# Default from user's audit query (2026-02-10)
DEFAULT_WORKSPACE_ID = "1516413757355523"
DEFAULT_SPACE_ID = "01f0aaabfed41a778b2e5302795ce495"
DEFAULT_CONVERSATION_ID = "01f105f722d910f6ba801eb18e78872f"
DEFAULT_MESSAGE_ID = "01f105f722e81150a6dea8e982a4ed20"


def get_message(
    workspace_id: str = DEFAULT_WORKSPACE_ID,
    space_id: str = DEFAULT_SPACE_ID,
    conversation_id: str = DEFAULT_CONVERSATION_ID,
    message_id: str = DEFAULT_MESSAGE_ID,
    workspace_url: str | None = None,
    scope: str = "genie-obs",
) -> dict:
    """
    GET /api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}
    Returns the API response as a dict. Raises on auth or request failure.
    """
    if workspace_url is None:
        import config as cfg
        urls = getattr(cfg, "WORKSPACE_URLS", None) or {}
        workspace_url = urls.get(workspace_id) or ""
    workspace_url = (workspace_url or "").rstrip("/")
    if not workspace_url:
        raise ValueError(f"No workspace_url for workspace_id={workspace_id}. Set WORKSPACE_URLS in config or pass workspace_url=.")

    dbutils = get_dbutils()
    if not dbutils:
        raise RuntimeError("dbutils not available; run on Databricks.")

    headers = get_headers_for_workspace(workspace_url, dbutils=dbutils, scope=scope)
    url = f"{workspace_url}/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}"

    print(f"GET {url}")
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, indent=2))
    return data


if __name__ == "__main__":
    try:
        get_message()
    except Exception as e:
        print(f"Error: {e}")
        raise