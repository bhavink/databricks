"""
Genie message ingestion: fetch message details from Genie API and persist to Delta.

Uses Databricks secrets (genie-obs scope: sp_client_id, sp_client_secret) for OAuth.
Run on Databricks as a job or from a notebook; requires spark and dbutils.

Config: edit config.py for SECRETS_SCOPE, WORKSPACE_IDS (required), optional SPACE_IDS_BY_WORKSPACE.
Message list is read from SOT table main.genie_analytics.genie_messages_to_fetch (populated by SDP pipeline).

# -----------------------------------------------------------------------------
# If the secret scope does not exist, create it from your LOCAL machine (once):
# -----------------------------------------------------------------------------
#   export DATABRICKS_SP_CLIENT_ID="your-service-principal-client-id"
#   export DATABRICKS_SP_CLIENT_SECRET="your-service-principal-client-secret"
#   cd /path/to/genie-aibi/scripts   # or workspace folder scripts/
#   python create_genie_obs_secrets.py --profile <your-databricks-profile>
#
# Use the same profile as your target workspace (e.g. adb-wx1). List profiles:
#   databricks auth profiles
# -----------------------------------------------------------------------------
"""
# =============================================================================
# Genie Message Ingestion — Fetch Message Details from API & Persist to Delta
# =============================================================================
# Purpose:
#   1. Read message list from SOT (main.genie_analytics.genie_messages_to_fetch).
#   2. Per workspace: get OAuth token, call GET .../messages/{message_id} for each message.
#   3. Merge results into message_details; record failures in message_fetch_errors.
#   4. Skip (workspace_id, message_id) already in message_details (incremental).
# =============================================================================
import json
import time
from datetime import datetime, timezone

# Assumed in Databricks: spark, dbutils in scope when run as job or notebook
try:
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()
except Exception:
    spark = None

# Config and OAuth (secrets used here)
from config import (
    SECRETS_SCOPE,
    TARGET_CATALOG,
    TARGET_SCHEMA,
    MESSAGE_DETAILS_TABLE,
    MESSAGE_FETCH_ERRORS_TABLE,
    MESSAGES_TO_FETCH_TABLE,
    API_RATE_LIMIT_SECONDS,
)
from genie_oauth import get_credentials, get_headers_for_workspace
import requests


def get_dbutils():
    if spark is None:
        raise RuntimeError("Spark not available; run this script on Databricks.")
    try:
        from pyspark.dbutils import DBUtils
        return DBUtils(spark)
    except Exception:
        return None


def fetch_space_name(base_url, space_id, headers, timeout=5):
    """
    Fetch space display name (title) via GET /api/2.0/genie/spaces/{space_id}.
    Response uses 'title' (e.g. "Sales Analytics Space"). No query params needed for title only.
    Returns the space name string or None if the API call fails or the field is missing.
    """
    url = f"{base_url.rstrip('/')}/api/2.0/genie/spaces/{space_id}"
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json()
        return data.get("title") or data.get("name") or data.get("display_name")
    except Exception:
        return None


def validate_secrets(dbutils, scope):
    """
    Ensure the secret scope and keys (sp_client_id, sp_client_secret) exist.
    Raises with a clear message if not. Call this at the start of ingestion.
    """
    try:
        get_credentials(dbutils=dbutils, scope=scope)
        return True
    except Exception as e:
        raise RuntimeError(
            f"Secrets validation failed for scope={scope!r}. "
            f"Create the scope and keys from your local machine (see commented block at top of this file). "
            f"Original error: {e}"
        ) from e


def run_ingestion(
    workspace_ids=None,
    space_ids_by_workspace=None,
    message_limit=None,
    dbutils=None,
):
    """
    Ingest Genie message details from the API. Message list is read from the SOT table
    genie_messages_to_fetch (populated by SDP pipeline). Successful fetches are appended to
    message_details; failed or dropped fetches (NO_TOKEN, FAILED) are appended to
    message_fetch_errors. Only new (workspace_id, message_id) pairs are fetched (incremental;
    no duplicates). Run pipeline + this job on a schedule (e.g. 15 min to once per day) after
    initial load.
    """
    cfg = __import__("config")
    workspace_ids = workspace_ids if workspace_ids is not None else getattr(cfg, "WORKSPACE_IDS", None)
    if not workspace_ids:
        raise ValueError(
            "WORKSPACE_IDS is required. Set WORKSPACE_IDS in config.py or pass workspace_ids=[...] to run_ingestion()."
        )
    space_ids_by_workspace = space_ids_by_workspace if space_ids_by_workspace is not None else getattr(cfg, "SPACE_IDS_BY_WORKSPACE", None)
    message_limit = message_limit if message_limit is not None else getattr(cfg, "EXTRACTION_MESSAGE_LIMIT", None)
    dbutils = dbutils or get_dbutils()
    scope = SECRETS_SCOPE

    # Validate secrets exist before reading SOT table and calling API
    validate_secrets(dbutils=dbutils, scope=scope)

    # 1) Read messages to fetch from SOT table (populated by SDP pipeline)
    messages_to_fetch_table = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{MESSAGES_TO_FETCH_TABLE}"
    full_table = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{MESSAGE_DETAILS_TABLE}"
    from pyspark.sql.functions import col
    messages_df = spark.table(messages_to_fetch_table)
    workspace_ids_str = [str(w) for w in workspace_ids]
    # Diagnostic: SOT stats before filters
    sot_total = messages_df.count()
    messages_df_ws = messages_df.filter(col("workspace_id").isin(workspace_ids_str))
    sot_after_workspace = messages_df_ws.count()
    try:
        sot_latest = messages_df_ws.agg({"event_time": "max"}).collect()[0][0]
    except Exception:
        sot_latest = None
    # Incremental: skip (workspace_id, message_id) already in message_details so each run only fetches new messages
    try:
        existing_df = spark.table(full_table).select("workspace_id", "message_id").distinct()
        existing_count = existing_df.count()
        messages_df = messages_df_ws.join(existing_df, ["workspace_id", "message_id"], "left_anti")
    except Exception:
        existing_count = 0
        messages_df = messages_df_ws
        # Table may not exist on first run
        pass
    # Optional: filter by space_ids per workspace (user-supplied; SOT table already has the candidate rows)
    if space_ids_by_workspace and isinstance(space_ids_by_workspace, dict):
        for ws_id, space_list in space_ids_by_workspace.items():
            if not space_list:
                continue
            # For this workspace, keep only rows whose space_id is in the list
            messages_df = messages_df.filter(
                (col("workspace_id") != str(ws_id)) | col("space_id").isin(space_list)
            )
    # Order: newest first globally so any limit picks up latest (e.g. test conversations), then by workspace/space
    messages_df = messages_df.orderBy(
        col("event_time").desc(),
        col("workspace_id"),
        col("space_id"),
    )
    if message_limit:
        messages_df = messages_df.limit(message_limit)
    messages_list = messages_df.collect()
    total_to_fetch = len(messages_list)
    if not messages_list:
        print("=" * 60)
        print("Message ingestion run (no new messages to fetch)")
        print("=" * 60)
        print("Data flow diagnostic:")
        print(f"  {MESSAGES_TO_FETCH_TABLE} total rows (all workspaces):     {sot_total}")
        print(f"  After workspace filter ({workspace_ids_str}):                {sot_after_workspace}")
        print(f"  Latest event_time in SOT (for your workspaces):            {sot_latest}")
        print(f"  Already in {MESSAGE_DETAILS_TABLE} (skipped):              {existing_count}")
        print(f"  New to fetch this run:                                     0")
        print("If you expected new messages: run the SDP pipeline first so audit events appear in genie_messages_to_fetch; then re-run this job.")
        print("=" * 60)
        return 0

    MAX_LOGGED_CALLS = 50  # Log first N API calls, then summary only
    print("=" * 60)
    print("Message ingestion run")
    print("=" * 60)
    print("Data flow (system tables -> SOT -> this job):")
    print(f"  {MESSAGES_TO_FETCH_TABLE} total rows (all workspaces):     {sot_total}")
    print(f"  After workspace filter ({workspace_ids_str}):                {sot_after_workspace}")
    print(f"  Latest event_time in SOT (for your workspaces):            {sot_latest}")
    print(f"  Already in {MESSAGE_DETAILS_TABLE} (skipped):              {existing_count}")
    print(f"  New to fetch this run:                                     {total_to_fetch}")
    print(f"Source: {messages_to_fetch_table}")
    print(f"Target: {full_table}")
    print("-" * 60)

    # 2) Per-workspace OAuth headers (using secrets); workspace_url from table rows
    workspace_headers = {}
    seen_workspaces = set()
    for row in messages_list:
        ws_id = row["workspace_id"]
        if ws_id in seen_workspaces:
            continue
        seen_workspaces.add(ws_id)
        url = (row["workspace_url"] if "workspace_url" in row else "").rstrip("/")
        if not url:
            continue
        try:
            workspace_headers[ws_id] = get_headers_for_workspace(
                url, dbutils=dbutils, scope=scope
            )
        except Exception as e:
            print(f"Warning: could not get token for workspace {ws_id}: {e}")

    # 2b) Space names: one GET /api/2.0/genie/spaces/{space_id} per unique (workspace_id, space_id); cache by (ws_id, space_id)
    space_name_cache = {}
    seen_space_keys = set()
    for msg in messages_list:
        ws_id = msg["workspace_id"]
        space_id = msg["space_id"]
        key = (ws_id, space_id)
        if key in seen_space_keys:
            continue
        seen_space_keys.add(key)
        headers = workspace_headers.get(ws_id)
        base_url = (msg.get("workspace_url") or "").rstrip("/")
        if not headers or not base_url:
            continue
        name = fetch_space_name(base_url, space_id, headers)
        space_name_cache[key] = name
        if API_RATE_LIMIT_SECONDS and API_RATE_LIMIT_SECONDS > 0:
            time.sleep(API_RATE_LIMIT_SECONDS)
    if space_name_cache:
        print(f"Resolved {len(space_name_cache)} unique space(s) to titles")

    # 3) Fetch each message from API
    from pyspark.sql.types import StructType, StructField, StringType, LongType, IntegerType, TimestampType

    schema = StructType([
        StructField("workspace_id", StringType()),
        StructField("workspace_name", StringType()),
        StructField("space_id", StringType()),
        StructField("space_name", StringType()),
        StructField("conversation_id", StringType()),
        StructField("message_id", StringType()),
        StructField("content", StringType()),
        StructField("status", StringType()),
        StructField("created_timestamp", LongType()),
        StructField("updated_timestamp", LongType()),
        StructField("query_sql", StringType()),
        StructField("query_description", StringType()),
        StructField("statement_id", StringType()),
        StructField("attachments_count", IntegerType()),
        StructField("attachments_json", StringType()),
        StructField("api_fetch_status", StringType()),
        StructField("api_fetch_error", StringType()),
    ])
    def make_row(ws_id, workspace_name, space_id, space_name, conv_id, msg_id, content, status, created_ts, updated_ts,
                 query_sql, query_description, statement_id, att_count, att_json, fetch_status, fetch_error):
        return (ws_id, workspace_name, space_id, space_name, conv_id, msg_id, content, status, created_ts, updated_ts,
                query_sql, query_description, statement_id, att_count or 0, att_json, fetch_status, fetch_error)

    rows = []
    for i, msg in enumerate(messages_list):
        ws_id = msg["workspace_id"]
        space_id = msg["space_id"]
        msg_id = msg["message_id"]
        num = i + 1
        space_name = space_name_cache.get((ws_id, space_id))
        headers = workspace_headers.get(ws_id)
        def log_call(outcome):
            if num <= MAX_LOGGED_CALLS:
                print(f"  API call {num}/{total_to_fetch}: workspace={ws_id} space={space_id[:16]}... message_id={msg_id[:16]}... -> {outcome}")

        if not headers:
            rows.append(make_row(ws_id, msg["workspace_name"], space_id, space_name, msg["conversation_id"], msg_id,
                None, None, None, None, None, None, None, 0, None, "NO_TOKEN", None))
            log_call("NO_TOKEN (skipped)")
            continue
        api_url = f"{msg['workspace_url'].rstrip('/')}/api/2.0/genie/spaces/{space_id}/conversations/{msg['conversation_id']}/messages/{msg_id}"
        try:
            r = requests.get(api_url, headers=headers, timeout=10)
            if r.status_code != 200:
                rows.append(make_row(ws_id, msg["workspace_name"], space_id, space_name, msg["conversation_id"], msg_id,
                    None, None, None, None, None, None, None, 0, None, "FAILED", r.text[:500]))
                log_call(f"FAILED ({r.status_code})")
                continue
            data = r.json()
            content = data.get("content") or ""
            status = data.get("status") or ""
            created_ts = data.get("created_timestamp") or 0
            updated_ts = data.get("updated_timestamp") or 0
            attachments = data.get("attachments") or []
            query_sql = None
            query_description = None
            statement_id = None
            for att in attachments:
                if "query" in att:
                    q = att["query"]
                    statement_id = q.get("statement_id")
                    query_sql = q.get("query")
                    query_description = q.get("description")
                    break
            rows.append(make_row(ws_id, msg["workspace_name"], space_id, space_name, msg["conversation_id"], msg_id,
                content, status, created_ts, updated_ts, query_sql, query_description, statement_id,
                len(attachments), json.dumps(attachments)[:65535] if attachments else None,
                "SUCCESS", None))
            log_call("SUCCESS (added to message_details)")
        except Exception as e:
            rows.append(make_row(ws_id, msg["workspace_name"], space_id, space_name, msg["conversation_id"], msg_id,
                None, None, None, None, None, None, None, 0, None, "FAILED", str(e)[:500]))
            log_call(f"FAILED ({e!r})")
        if API_RATE_LIMIT_SECONDS and API_RATE_LIMIT_SECONDS > 0:
            time.sleep(API_RATE_LIMIT_SECONDS)

    if total_to_fetch > MAX_LOGGED_CALLS:
        print(f"  ... ({total_to_fetch - MAX_LOGGED_CALLS} more API calls, see summary below)")

    # 4) Split success vs errored/dropped: success → message_details, errors → message_fetch_errors (no duplicates; append-only)
    from pyspark.sql.functions import current_timestamp, lit

    success_rows = [r for r in rows if r[-2] == "SUCCESS"]  # api_fetch_status is second-to-last
    error_rows = [r for r in rows if r[-2] != "SUCCESS"]
    batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {TARGET_CATALOG}.{TARGET_SCHEMA}")

    if success_rows:
        df_ok = spark.createDataFrame(success_rows, schema)
        df_ok = df_ok.withColumn("ingestion_timestamp", current_timestamp()).withColumn("ingestion_batch_id", lit(batch_id))
        df_ok.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(full_table)
    if error_rows:
        errors_table = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{MESSAGE_FETCH_ERRORS_TABLE}"
        from pyspark.sql.types import StructType as ErrStructType, StructField as ErrStructField, StringType, IntegerType, BooleanType
        err_schema = ErrStructType([
            ErrStructField("workspace_id", StringType()),
            ErrStructField("message_id", StringType()),
            ErrStructField("space_id", StringType()),
            ErrStructField("conversation_id", StringType()),
            ErrStructField("error_type", StringType()),
            ErrStructField("error_message", StringType()),
            ErrStructField("retry_count", IntegerType()),
            ErrStructField("resolved", BooleanType()),
        ])
        err_data = [
            (r[0], r[5], r[2], r[4], r[15], (r[16] or "")[:500], 0, False)
            for r in error_rows
        ]
        df_err = spark.createDataFrame(err_data, err_schema).withColumn("error_timestamp", current_timestamp())
        df_err.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(errors_table)

    print("-" * 60)
    print("Ingestion summary")
    print("-" * 60)
    print(f"  API calls made:           {total_to_fetch}")
    print(f"  Messages ingested (added to {MESSAGE_DETAILS_TABLE}): {len(success_rows)}")
    print(f"  Errors (written to {MESSAGE_FETCH_ERRORS_TABLE}): {len(error_rows)}")
    print("=" * 60)
    return len(success_rows)


if __name__ == "__main__":
    # When run as script, use config: WORKSPACE_IDS (required), optional SPACE_IDS_BY_WORKSPACE.
    import config as cfg
    n = run_ingestion(
        workspace_ids=getattr(cfg, "WORKSPACE_IDS", None),
        space_ids_by_workspace=getattr(cfg, "SPACE_IDS_BY_WORKSPACE", None),
        message_limit=getattr(cfg, "EXTRACTION_MESSAGE_LIMIT", None),
        dbutils=get_dbutils(),
    )
    print(f"Done. Total messages ingested this run: {n}")
