"""
06_create_vs_index.py — Phase 2: Vector Search + M2M

Creates:
  1. Enables Change Data Feed on product_docs and sales_playbooks (required for Delta Sync)
  2. VS endpoint: authz-showcase-vs (serverless)
  3. VS index: authz_showcase.knowledge_base.product_docs_index (Delta Sync)
  4. VS index: authz_showcase.knowledge_base.sales_playbooks_index (Delta Sync)
  5. Waits for both indexes to reach ONLINE status

Usage:
  databricks --profile <profile> fs run /path/to/06_create_vs_index.py
  # or locally:
  python 06_create_vs_index.py
"""

import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import (
    EndpointType,
    VectorIndexType,
    DeltaSyncVectorIndexSpecRequest,
    EmbeddingSourceColumn,
    PipelineType,
)
from databricks.sdk.errors.platform import ResourceAlreadyExists, NotFound

# ── Config ─────────────────────────────────────────────────────────────────────

CATALOG = "authz_showcase"
SCHEMA  = "knowledge_base"

VS_ENDPOINT   = "authz-showcase-vs"
EMBEDDING_MODEL = "databricks-bge-large-en"

PRODUCT_DOCS_TABLE = f"{CATALOG}.{SCHEMA}.product_docs"
PLAYBOOKS_TABLE    = f"{CATALOG}.{SCHEMA}.sales_playbooks"

PRODUCT_DOCS_INDEX = f"{CATALOG}.{SCHEMA}.product_docs_index"
PLAYBOOKS_INDEX    = f"{CATALOG}.{SCHEMA}.sales_playbooks_index"

POLL_INTERVAL_SEC = 10
TIMEOUT_SEC       = 20 * 60  # 20 minutes


# ── Helpers ────────────────────────────────────────────────────────────────────

def enable_cdc(w: WorkspaceClient, table: str) -> None:
    """Enable Change Data Feed on a Delta table (required for Delta Sync VS indexes)."""
    print(f"  Enabling CDF on {table} …")
    w.statement_execution.execute_statement(
        warehouse_id=_get_warehouse(w),
        statement=f"ALTER TABLE {table} SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')",
        wait_timeout="30s",
    )
    print(f"  ✓ CDF enabled on {table}")


def _get_warehouse(w: WorkspaceClient) -> str:
    """Return the first available SQL warehouse ID."""
    warehouses = list(w.warehouses.list())
    running = [wh for wh in warehouses if wh.state and wh.state.value == "RUNNING"]
    if running:
        return running[0].id
    if warehouses:
        return warehouses[0].id
    raise RuntimeError("No SQL warehouses available. Create one and retry.")


def ensure_vs_endpoint(w: WorkspaceClient) -> str:
    """Create the VS endpoint if it doesn't exist; wait until it is ONLINE."""
    existing = {ep.name for ep in w.vector_search_endpoints.list_endpoints()}
    if VS_ENDPOINT in existing:
        print(f"  VS endpoint '{VS_ENDPOINT}' already exists — checking status …")
    else:
        print(f"  Creating VS endpoint '{VS_ENDPOINT}' (serverless) …")
        w.vector_search_endpoints.create_endpoint_and_wait(
            name=VS_ENDPOINT,
            endpoint_type=EndpointType.STANDARD,
        )
        print(f"  ✓ VS endpoint '{VS_ENDPOINT}' created")

    # Wait for endpoint to reach ONLINE state before creating indexes
    # (creating indexes before endpoint is ONLINE leaves them stuck in PROVISIONING_ENDPOINT)
    deadline = time.time() + TIMEOUT_SEC
    print(f"  Waiting for endpoint '{VS_ENDPOINT}' to be ONLINE …")
    while time.time() < deadline:
        ep = w.vector_search_endpoints.get_endpoint(VS_ENDPOINT)
        state = ep.endpoint_status.state.value if ep.endpoint_status and ep.endpoint_status.state else "UNKNOWN"
        if state == "ONLINE":
            print(f"  ✓ Endpoint '{VS_ENDPOINT}' is ONLINE")
            return VS_ENDPOINT
        print(f"    endpoint state: {state} — waiting …")
        time.sleep(POLL_INTERVAL_SEC)
    raise TimeoutError(f"VS endpoint '{VS_ENDPOINT}' did not reach ONLINE within {TIMEOUT_SEC // 60} min")



def create_delta_sync_index(
    w: WorkspaceClient,
    index_name: str,
    source_table: str,
    primary_key: str,
    embedding_col: str,
) -> None:
    """Create a Delta Sync Vector Search index (skip if already exists)."""
    # Check if index already exists
    try:
        existing = w.vector_search_indexes.get_index(index_name)
        print(f"  Index '{index_name}' already exists (ready={existing.status.ready if existing.status else '?'}) — skipping create")
        return
    except NotFound:
        pass  # index doesn't exist — create it
    except Exception as e:
        # Unexpected error during get — log and attempt create anyway
        print(f"  Warning: get_index raised {type(e).__name__}: {e} — attempting create")

    print(f"  Creating Delta Sync index '{index_name}' …")
    try:
        w.vector_search_indexes.create_index(
            name=index_name,
            endpoint_name=VS_ENDPOINT,
            primary_key=primary_key,
            index_type=VectorIndexType.DELTA_SYNC,
            delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
                source_table=source_table,
                pipeline_type=PipelineType.TRIGGERED,
                embedding_source_columns=[
                    EmbeddingSourceColumn(
                        name=embedding_col,
                        embedding_model_endpoint_name=EMBEDDING_MODEL,
                    )
                ],
            ),
        )
        print(f"  ✓ Index '{index_name}' creation initiated")
    except ResourceAlreadyExists:
        print(f"  Index '{index_name}' already exists (UC) — skipping create")


def wait_for_indexes_online(w: WorkspaceClient, index_names: list[str]) -> None:
    """Poll until all indexes are ONLINE (ready_for_query=True) or timeout."""
    deadline = time.time() + TIMEOUT_SEC
    pending = set(index_names)

    print(f"\n  Waiting for indexes to come ONLINE (timeout: {TIMEOUT_SEC // 60} min) …")

    while pending and time.time() < deadline:
        for name in list(pending):
            try:
                idx = w.vector_search_indexes.get_index(name)
                ready = idx.status.ready if idx.status else False
                msg = (idx.status.message or "")[:100] if idx.status else "UNKNOWN"
                label = "ONLINE" if ready else msg
                print(f"    [{name.split('.')[-1]}] {label}")
                if ready:
                    pending.remove(name)
                    print(f"    ✓ {name} is ONLINE")
            except Exception as e:
                print(f"    [{name}] error polling: {e}")

        if pending:
            time.sleep(POLL_INTERVAL_SEC)

    if pending:
        raise TimeoutError(
            f"Timed out waiting for indexes to come ONLINE: {pending}\n"
            "Check Databricks VS endpoint logs and retry."
        )


def test_query(w: WorkspaceClient, index_name: str, query: str) -> None:
    """Run a test query and assert ≥1 result is returned."""
    import requests, json

    host = w.config.host.rstrip("/")
    auth = w.config.authenticate()
    headers = {**auth, "Content-Type": "application/json"}

    print(f"\n  Test query on '{index_name}': \"{query}\" …")
    r = requests.post(
        f"{host}/api/2.0/vector-search/indexes/{index_name}/query",
        headers=headers,
        json={
            "query_text": query,
            "num_results": 3,
            "columns": ["doc_id", "title", "content", "category"],
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("result", {}).get("data_array", [])
    print(f"  Results returned: {len(results)}")
    if results:
        print(f"  First result: {json.dumps(results[0], indent=2)[:300]}")
    assert len(results) >= 1, f"Test gate FAILED: expected ≥1 result, got 0 for query: '{query}'"
    print(f"  ✓ Test gate PASSED: {len(results)} result(s)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("Phase 2: Vector Search Index Setup")
    print("=" * 60)

    w = WorkspaceClient()
    print(f"\nConnected to: {w.config.host}")

    # Step 1 — Enable CDF on both source tables
    print("\n[1/4] Enabling Change Data Feed …")
    enable_cdc(w, PRODUCT_DOCS_TABLE)
    enable_cdc(w, PLAYBOOKS_TABLE)

    # Step 2 — Ensure VS endpoint exists
    print("\n[2/4] Ensuring VS endpoint …")
    ensure_vs_endpoint(w)

    # Step 3 — Create Delta Sync indexes
    print("\n[3/4] Creating Delta Sync indexes …")
    create_delta_sync_index(
        w,
        index_name=PRODUCT_DOCS_INDEX,
        source_table=PRODUCT_DOCS_TABLE,
        primary_key="doc_id",
        embedding_col="content",
    )
    create_delta_sync_index(
        w,
        index_name=PLAYBOOKS_INDEX,
        source_table=PLAYBOOKS_TABLE,
        primary_key="playbook_id",
        embedding_col="content",
    )

    # Step 4 — Wait for ONLINE
    print("\n[4/4] Waiting for ONLINE status …")
    wait_for_indexes_online(w, [PRODUCT_DOCS_INDEX, PLAYBOOKS_INDEX])

    # Step 5 — Test gate
    print("\n[5/5] Running test queries …")
    test_query(w, PRODUCT_DOCS_INDEX, "DataPlatform Core features")

    # Summary
    print("\n" + "=" * 60)
    print("✅ Phase 2 seed complete!")
    print(f"\nWire these into app.yaml env / resources:")
    print(f"  VS_INDEX    = {PRODUCT_DOCS_INDEX}")
    print(f"  VS_INDEX_PB = {PLAYBOOKS_INDEX}")
    print("=" * 60)


if __name__ == "__main__":
    main()
