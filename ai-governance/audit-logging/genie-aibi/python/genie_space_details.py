"""
Genie space details ingestion: fetch full space config (including serialized_space) and persist to Delta.

Current purpose: translate (workspace_id, space_id) → human-readable space title (and description, etc.)
for dashboards and analytics. Later: promotion management (use serialized_space with Create/Update Genie
Space API to promote spaces across environments).

Calls GET /api/2.0/genie/spaces/{space_id}?include_serialized_space=true. The serialized_space field
can be used with the Create Genie Space API and Update Genie Space API to promote spaces across
workspaces or create backups (task for later).

Uses the same Databricks secrets (genie-obs: sp_client_id, sp_client_secret) and config as message
ingestion. Space list is read from main.genie_analytics.genie_messages_to_fetch (distinct workspace_id,
space_id) so only spaces that have message activity are synced.

Run order: SDP pipeline must run first (populates genie_messages_to_fetch). This job can run after
the pipeline only, or after message ingestion, or on its own schedule (e.g. daily). It does not
depend on message_details. Writes to genie_space_details via MERGE on (workspace_id, space_id):
matched rows are updated (overwrite columns for that space); new spaces are inserted. No full-table
overwrite.

Config: config.py — SECRETS_SCOPE, WORKSPACE_IDS, optional SPACE_IDS_BY_WORKSPACE, SPACE_DETAILS_TABLE.
"""
# =============================================================================
# Genie Space Details — Fetch Space Config (Title, serialized_space) & Persist to Delta
# =============================================================================
# Purpose:
#   1. Read distinct (workspace_id, space_id) from genie_messages_to_fetch (spaces with activity).
#   2. Per workspace: GET /api/2.0/genie/spaces/{space_id}?include_serialized_space=true.
#   3. Persist title, description, warehouse_id, serialized_space to genie_space_details.
# =============================================================================
import time
from datetime import datetime, timezone

try:
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
except Exception:
    spark = None

from config import (
    SECRETS_SCOPE,
    TARGET_CATALOG,
    TARGET_SCHEMA,
    MESSAGES_TO_FETCH_TABLE,
    SPACE_DETAILS_TABLE,
    API_RATE_LIMIT_SECONDS,
)
from genie_oauth import get_headers_for_workspace
from genie_message_ingestion import get_dbutils, validate_secrets
import requests


def fetch_space_details(base_url, space_id, headers, include_serialized=True, timeout=15):
    """
    GET /api/2.0/genie/spaces/{space_id}?include_serialized_space=true.
    Returns dict with title, description, warehouse_id, created_timestamp, last_updated_timestamp,
    serialized_space (if include_serialized), or None on failure.
    """
    url = f"{base_url.rstrip('/')}/api/2.0/genie/spaces/{space_id}"
    if include_serialized:
        url += "?include_serialized_space=true"
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return None, r.text[:1000] if r.text else f"HTTP {r.status_code}"
        data = r.json()
        return data, None
    except Exception as e:
        return None, str(e)[:500]


def run_space_details_ingestion(workspace_ids=None, space_ids_by_workspace=None, dbutils=None):
    """
    For each distinct (workspace_id, space_id) in genie_messages_to_fetch (filtered by workspace_ids
    and optional space_ids_by_workspace), call GET space with include_serialized_space=true and merge
    into genie_space_details.
    """
    cfg = __import__("config")
    workspace_ids = workspace_ids if workspace_ids is not None else getattr(cfg, "WORKSPACE_IDS", None)
    if not workspace_ids:
        raise ValueError("WORKSPACE_IDS is required (config.py or pass workspace_ids=...).")
    space_ids_by_workspace = space_ids_by_workspace if space_ids_by_workspace is not None else getattr(cfg, "SPACE_IDS_BY_WORKSPACE", None)
    dbutils = dbutils or get_dbutils()
    scope = SECRETS_SCOPE

    validate_secrets(dbutils=dbutils, scope=scope)

    fetch_table = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{MESSAGES_TO_FETCH_TABLE}"
    from pyspark.sql.functions import col
    df = spark.table(fetch_table)
    workspace_ids_str = [str(w) for w in workspace_ids]
    df = df.filter(col("workspace_id").isin(workspace_ids_str))
    if space_ids_by_workspace and isinstance(space_ids_by_workspace, dict):
        for ws_id, space_list in space_ids_by_workspace.items():
            if not space_list:
                continue
            df = df.filter((col("workspace_id") != str(ws_id)) | col("space_id").isin(space_list))
    df = df.select("workspace_id", "space_id", "workspace_url").distinct()
    spaces_list = df.collect()
    if not spaces_list:
        print(f"No distinct spaces in {fetch_table} for WORKSPACE_IDS. Run the pipeline first.")
        return 0

    workspace_headers = {}
    for row in spaces_list:
        ws_id = row["workspace_id"]
        if ws_id in workspace_headers:
            continue
        base_url = (getattr(row, "workspace_url", None) or "").rstrip("/")
        if not base_url:
            continue
        try:
            workspace_headers[ws_id] = (base_url, get_headers_for_workspace(base_url, dbutils=dbutils, scope=scope))
        except Exception as e:
            print(f"Warning: no token for workspace {ws_id}: {e}")

    batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    now_ts = datetime.now(timezone.utc)
    rows_ok = []
    rows_fail = []
    for i, row in enumerate(spaces_list):
        ws_id = row["workspace_id"]
        space_id = row["space_id"]
        tup = workspace_headers.get(ws_id)
        if not tup:
            rows_fail.append((ws_id, space_id, None, None, None, None, None, None, "NO_TOKEN", None, now_ts, batch_id))
            continue
        base_url, headers = tup
        data, err = fetch_space_details(base_url, space_id, headers, include_serialized=True)
        if err:
            rows_fail.append((ws_id, space_id, None, None, None, None, None, None, "FAILED", err, now_ts, batch_id))
        else:
            serialized = data.get("serialized_space")
            if isinstance(serialized, dict):
                import json
                serialized = json.dumps(serialized)
            rows_ok.append((
                ws_id,
                space_id,
                data.get("title"),
                data.get("description"),
                data.get("warehouse_id"),
                data.get("created_timestamp"),
                data.get("last_updated_timestamp"),
                serialized,
                "SUCCESS",
                None,
                now_ts,
                batch_id,
            ))
        if (i + 1) % 5 == 0:
            print(f"Fetched {i + 1}/{len(spaces_list)} spaces")
        if API_RATE_LIMIT_SECONDS and API_RATE_LIMIT_SECONDS > 0:
            time.sleep(API_RATE_LIMIT_SECONDS)

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_CATALOG}.{TARGET_SCHEMA}")
    target_table = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{SPACE_DETAILS_TABLE}"

    from pyspark.sql.types import StructType, StructField, StringType, LongType, TimestampType
    from pyspark.sql.functions import lit, current_timestamp

    schema = StructType([
        StructField("workspace_id", StringType()),
        StructField("space_id", StringType()),
        StructField("title", StringType()),
        StructField("description", StringType()),
        StructField("warehouse_id", StringType()),
        StructField("created_timestamp", LongType()),
        StructField("last_updated_timestamp", LongType()),
        StructField("serialized_space", StringType()),
        StructField("api_fetch_status", StringType()),
        StructField("api_fetch_error", StringType()),
        StructField("ingestion_timestamp", TimestampType()),
        StructField("ingestion_batch_id", StringType()),
    ])
    all_rows = rows_ok + rows_fail
    if not all_rows:
        return 0
    df_out = spark.createDataFrame(all_rows, schema)
    try:
        spark.table(target_table)
        table_exists = True
    except Exception:
        table_exists = False
    if not table_exists:
        df_out.write.format("delta").mode("overwrite").saveAsTable(target_table)
        print(f"Created {target_table} with {len(all_rows)} space(s) ({len(rows_ok)} OK, {len(rows_fail)} failed)")
        return len(rows_ok)
    df_out.createOrReplaceTempView("space_details_updates")
    spark.sql(f"""
        MERGE INTO {target_table} AS t
        USING space_details_updates AS s
        ON t.workspace_id = s.workspace_id AND t.space_id = s.space_id
        WHEN MATCHED THEN UPDATE SET
            t.title = s.title,
            t.description = s.description,
            t.warehouse_id = s.warehouse_id,
            t.created_timestamp = s.created_timestamp,
            t.last_updated_timestamp = s.last_updated_timestamp,
            t.serialized_space = s.serialized_space,
            t.api_fetch_status = s.api_fetch_status,
            t.api_fetch_error = s.api_fetch_error,
            t.ingestion_timestamp = s.ingestion_timestamp,
            t.ingestion_batch_id = s.ingestion_batch_id
        WHEN NOT MATCHED THEN INSERT *
    """)
    print(f"Merged {len(all_rows)} space(s) into {target_table} ({len(rows_ok)} OK, {len(rows_fail)} failed)")
    return len(rows_ok)


if __name__ == "__main__":
    import config as cfg
    run_space_details_ingestion(
        workspace_ids=getattr(cfg, "WORKSPACE_IDS", None),
        space_ids_by_workspace=getattr(cfg, "SPACE_IDS_BY_WORKSPACE", None),
        dbutils=get_dbutils(),
    )
