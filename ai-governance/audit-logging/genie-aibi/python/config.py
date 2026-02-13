# =============================================================================
# Genie Observability — Config (Secrets Scope, Tables, Workspaces, Rate Limits)
# =============================================================================
# Purpose:
#   1. Define Databricks secrets scope and Unity Catalog target (catalog, schema, table names).
#   2. Configure workspace IDs and optional space filter (WORKSPACE_IDS, SPACE_IDS_BY_WORKSPACE).
#   3. Control API rate limiting and batch size for message/space ingestion.
# =============================================================================
# Genie message ingestion config (no secret values - scope name only; values from dbutils.secrets)
SECRETS_SCOPE = "genie-obs"  # Scope in Databricks secrets; keys: sp_client_id, sp_client_secret

TARGET_CATALOG = "main"
TARGET_SCHEMA = "genie_analytics"
MESSAGE_DETAILS_TABLE = "message_details"
MESSAGE_FETCH_ERRORS_TABLE = "message_fetch_errors"
# Space details (title, description, serialized_space) from GET space with include_serialized_space=true.
# Used by genie_space_details.py for backup and promote-across-workspaces.
SPACE_DETAILS_TABLE = "genie_space_details"
# Source of truth for which messages to fetch (populated by SDP pipeline).
# For continuous capture (e.g. every 30 min): set pipeline config genie.lookback_minutes = "30";
# ingestion skips (workspace_id, message_id) already in message_details so only new messages are fetched.
MESSAGES_TO_FETCH_TABLE = "genie_messages_to_fetch"

# Extraction: workspace_ids required; optional space_ids per workspace. All from SOT (genie_messages_to_fetch).
# Ingestion order: for each workspace in WORKSPACE_IDS, process all (configured) spaces in that workspace, then next workspace.
WORKSPACE_IDS = ["1516413757355523", "984752964297111"]  # Required: list of workspace IDs to process

# Optional: restrict to specific spaces per workspace. A workspace can have 100s of spaces.
# - None = extract from ALL spaces in each workspace (SOT can have 10k+ rows).
# - Dict: workspace_id (str) -> list of space_id (str). Use [] for a workspace to mean "all spaces" for that workspace.
# Ingestion iterates through all spaces in workspace 1, then all spaces in workspace 2, etc. Both space IDs below are checked.
# If you see only ~27 rows per run, you are filtering to one space per workspace below; set to None to ingest all.
SPACE_IDS_BY_WORKSPACE = {
    "1516413757355523": ["01f0aaabfed41a778b2e5302795ce495"],   # workspace 1: one space
    "984752964297111": ["01ef7bef0dbf1545bfd9184f19ad97f6"]     # workspace 2: one space (total 2 spaces)
}
# SPACE_IDS_BY_WORKSPACE = None  # Uncomment to ingest from ALL spaces (SOT has 14k+ rows for these workspaces)
EXTRACTION_MESSAGE_LIMIT = None  # None = no limit, or number of messages to extract (e.g. 100)

# Initial/base load: last N days including today. Use for FIRST run only (pipeline + Python).
# Pipeline uses system tables (precise timestamps); set genie.days_lookback to this value for initial load.
# After initial load, run pipeline + Python incrementally (e.g. every 15 min to once per day); use genie.lookback_minutes for timestamp window and Python skips already-ingested message_ids (no duplicates). Errored/dropped rows go to message_fetch_errors.
DEFAULT_DAYS_LOOKBACK = 90
API_BATCH_SIZE = 100
# Delay between API calls (seconds). 0 or None = no manual rate limit (faster for 1000s of messages).
# Use a small value (e.g. 0.05) only if you hit API 429 rate limits.
API_RATE_LIMIT_SECONDS = 0

# Optional: for demo_generate_test_conversations.py (on-demand test data via Genie Conversation API).
# Map workspace_id (str) -> workspace base URL (no trailing slash). If None, script tries to read from
# main.genie_analytics.genie_messages_to_fetch (workspace_id, workspace_url) when run on Databricks.
# Set explicitly to avoid SOT table read (which can fail in serverless job context).
WORKSPACE_URLS = {
    "1516413757355523": "https://adb-1516413757355523.3.azuredatabricks.net",
    "984752964297111": "https://adb-984752964297111.11.azuredatabricks.net",
}
