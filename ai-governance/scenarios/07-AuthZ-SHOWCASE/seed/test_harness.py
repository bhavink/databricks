#!/usr/bin/env python3
"""
Headless test harness for the AI AuthZ Showcase demo.

Usage:
    DATABRICKS_CONFIG_PROFILE=<YOUR_CLI_PROFILE> python seed/test_harness.py

Tests 8 capabilities in order. Exits 0 if all pass, 1 if any fail.
"""

import sys
import json
import requests
from databricks.sdk import WorkspaceClient

PROFILE = "<YOUR_CLI_PROFILE>"
WAREHOUSE_ID = "<YOUR_WAREHOUSE_ID>"
APP_URL = "https://authz-showcase-<YOUR_WORKSPACE_ORG_ID>.3.azure.databricksapps.com"
CUSTOM_MCP_URL = "https://authz-showcase-custom-mcp-<YOUR_WORKSPACE_ORG_ID>.3.azure.databricksapps.com"
SUPERVISOR_ENDPOINT = "<YOUR_SUPERVISOR_ENDPOINT>"
VS_INDEX = "authz_showcase.knowledge_base.product_docs_index"
GITHUB_CONN = "authz_showcase_github_conn"
CUSTMCP_CONN = "authz_showcase_custmcp_conn"

results = []


def record(passed: bool, tab: str, description: str, error: str = ""):
    status = "PASS" if passed else "FAIL"
    if passed:
        print(f"[{status}] {tab}: {description}")
    else:
        print(f"[{status}] {tab}: {description} -- {error}")
    results.append(passed)


def get_auth_headers(w: WorkspaceClient) -> dict:
    return w.config.authenticate()


def main():
    print("=" * 60)
    print("AI AuthZ Showcase — Test Harness")
    print("=" * 60)
    print()

    try:
        w = WorkspaceClient(profile=PROFILE)
        host = w.config.host.rstrip("/")
        auth_headers = get_auth_headers(w)
    except Exception as e:
        print(f"[FATAL] Could not initialize WorkspaceClient: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Test 1: App status
    # ------------------------------------------------------------------
    try:
        app = w.apps.get("authz-showcase")
        state = app.compute_status.state.value if app.compute_status else "UNKNOWN"
        if state == "ACTIVE":
            record(True, "App", "authz-showcase is RUNNING")
        else:
            record(False, "App", "authz-showcase is RUNNING", f"state={state}")
    except Exception as e:
        record(False, "App", "authz-showcase is RUNNING", str(e))

    # ------------------------------------------------------------------
    # Test 2: Tab 1/3 — UC catalog access via SQL warehouse
    # ------------------------------------------------------------------
    try:
        resp = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement="SELECT current_user()",
            wait_timeout="15s",
        )
        state = resp.status.state.value
        if state == "SUCCEEDED":
            user = resp.result.data_array[0][0] if resp.result and resp.result.data_array else "?"
            record(True, "Tab 1/3", f"SQL warehouse accessible (current_user={user})")
        else:
            record(False, "Tab 1/3", "SQL warehouse accessible", f"state={state}")
    except Exception as e:
        record(False, "Tab 1/3", "SQL warehouse accessible", str(e))

    # ------------------------------------------------------------------
    # Test 3: Tab 2 — Vector Search index queryable
    # ------------------------------------------------------------------
    try:
        from databricks.sdk.service.vectorsearch import QueryVectorIndexRequest

        result = w.vector_search_indexes.query_index(
            index_name=VS_INDEX,
            query_text="test",
            num_results=1,
            columns=["content"],
        )
        count = len(result.result.data_array) if result.result and result.result.data_array else 0
        record(True, "Tab 2", f"VS index queryable (got {count} result(s))")
    except Exception as e:
        # VS SDK interface varies — try alternate method name
        try:
            from databricks.sdk.service import vectorsearch as vs_service
            client = w.vector_search_indexes
            result = client.query_index(
                index_name=VS_INDEX,
                query_text="test",
                num_results=1,
            )
            record(True, "Tab 2", "VS index queryable")
        except Exception as e2:
            record(False, "Tab 2", "VS index queryable", str(e2))

    # ------------------------------------------------------------------
    # Test 4: Tab 3 — UC function callable
    # ------------------------------------------------------------------
    try:
        resp = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement="SELECT authz_showcase.functions.recommend_next_action('OPP001')",
            wait_timeout="15s",
        )
        state = resp.status.state.value
        if state == "SUCCEEDED":
            val = resp.result.data_array[0][0] if resp.result and resp.result.data_array else None
            record(True, "Tab 3", f"UC function recommend_next_action callable (result={str(val)[:50]})")
        else:
            err = resp.status.error.message if resp.status.error else state
            record(False, "Tab 3", "UC function recommend_next_action callable", err)
    except Exception as e:
        record(False, "Tab 3", "UC function recommend_next_action callable", str(e))

    # ------------------------------------------------------------------
    # Test 5: Tab 4 — Custom MCP server reachable
    # ------------------------------------------------------------------
    try:
        resp = requests.get(
            CUSTOM_MCP_URL,
            headers=auth_headers,
            timeout=10,
            allow_redirects=True,
        )
        if resp.status_code in (200, 401, 403):
            record(True, "Tab 4", f"Custom MCP server reachable (HTTP {resp.status_code})")
        else:
            record(False, "Tab 4", "Custom MCP server reachable", f"HTTP {resp.status_code}")
    except Exception as e:
        record(False, "Tab 4", "Custom MCP server reachable", str(e))

    # ------------------------------------------------------------------
    # Test 6: Tab 5 — Supervisor endpoint reachable
    # ------------------------------------------------------------------
    try:
        endpoint_url = f"{host}/serving-endpoints/{SUPERVISOR_ENDPOINT}/invocations"
        payload = {
            "messages": [{"role": "user", "content": "hello"}],
            "max_tokens": 10,
        }
        resp = requests.post(
            endpoint_url,
            headers={**auth_headers, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            record(True, "Tab 5", f"Supervisor endpoint {SUPERVISOR_ENDPOINT} reachable and responding")
        elif resp.status_code in (400, 422):
            # Endpoint exists but rejected our minimal payload — that's fine
            record(True, "Tab 5", f"Supervisor endpoint {SUPERVISOR_ENDPOINT} reachable (HTTP {resp.status_code} — endpoint exists)")
        else:
            record(False, "Tab 5", f"Supervisor endpoint {SUPERVISOR_ENDPOINT} reachable",
                   f"HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        record(False, "Tab 5", f"Supervisor endpoint {SUPERVISOR_ENDPOINT} reachable", str(e))

    # ------------------------------------------------------------------
    # Test 7: Tab 6B — custmcp UC proxy token freshness
    # ------------------------------------------------------------------
    try:
        proxy_url = f"{host}/api/2.0/mcp/external/{CUSTMCP_CONN}"
        payload = {"jsonrpc": "2.0", "method": "initialize", "id": 1,
                   "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                              "clientInfo": {"name": "test-harness", "version": "1.0"}}}
        resp = requests.post(
            proxy_url,
            headers={**auth_headers, "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        if resp.status_code == 200:
            record(True, "Tab 6B", "custmcp UC proxy token fresh (initialize succeeded)")
        elif resp.status_code == 401:
            record(False, "Tab 6B", "custmcp UC proxy token fresh",
                   "401 Unauthorized — run: python seed/refresh_custmcp_token.py")
        else:
            record(False, "Tab 6B", "custmcp UC proxy token fresh",
                   f"HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        record(False, "Tab 6B", "custmcp UC proxy token fresh", str(e))

    # ------------------------------------------------------------------
    # Test 8: Tab 6A — GitHub UC proxy reachable
    # ------------------------------------------------------------------
    try:
        proxy_url = f"{host}/api/2.0/mcp/external/{GITHUB_CONN}"
        payload = {"jsonrpc": "2.0", "method": "initialize", "id": 1,
                   "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                              "clientInfo": {"name": "test-harness", "version": "1.0"}}}
        resp = requests.post(
            proxy_url,
            headers={**auth_headers, "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        body = resp.text[:200]
        if resp.status_code == 200:
            record(True, "Tab 6A", "GitHub UC proxy reachable (initialize succeeded)")
        elif resp.status_code == 400 and "Credential not found" in body:
            record(True, "Tab 6A",
                   "GitHub UC proxy reachable (credential not found — user needs to authorize at /explore/connections/authz_showcase_github_conn)")
        elif resp.status_code == 403 and "unity-catalog" in body:
            record(False, "Tab 6A", "GitHub UC proxy reachable",
                   "403 missing unity-catalog scope — nuclear rebuild required (see DEMO-GUIDE.md)")
        else:
            record(False, "Tab 6A", "GitHub UC proxy reachable",
                   f"HTTP {resp.status_code}: {body}")
    except Exception as e:
        record(False, "Tab 6A", "GitHub UC proxy reachable", str(e))

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Result: {passed}/{total} checks passed")
    if passed < total:
        print()
        print("Failed checks require attention before the demo.")
        print("See DEMO-GUIDE.md Section 5: Troubleshooting")
    print("=" * 60)

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
