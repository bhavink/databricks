-- =============================================================================
-- Genie Observability – SDP SQL Pipeline
-- =============================================================================
-- Builds and populates audit-derived data models from system.access.audit.
-- Follows SDP best practices: parameterization, CLUSTER BY, expectations by
-- layer (bronze DROP ROW, silver FAIL UPDATE), explicit columns, medallion + validation.
--
-- Pipeline configuration (pass in pipeline settings):
--   genie.workspace_ids    = comma-separated workspace IDs (e.g. "1516413757355523,984752964297111")
--   genie.days_lookback   = days of history (e.g. "30"); used when genie.lookback_minutes is not set
--   genie.lookback_minutes = optional; when set (e.g. "30"), filter by event_time >= now - N minutes (incremental runs). When "" or "0", use date-based lookback (for initial load only). After first load, use lookback_minutes for incremental.
--
-- Target catalog/schema: set in pipeline (e.g. catalog=main, schema=genie_analytics).
-- Compute: use Serverless. In UI set to Serverless; via API/MCP always pass extra_settings.serverless = true.
-- Before full refresh: run a dry run (validate_only=True) to catch schema/syntax issues.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Bronze: Raw Genie message events from audit (parameterized filter)
-- Expectations: drop rows missing required IDs; warn on non-200 status.
-- -----------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW genie_audit_message_events
(
  CONSTRAINT valid_workspace_id    EXPECT (workspace_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_space_id         EXPECT (space_id IS NOT NULL AND length(trim(space_id)) > 0) ON VIOLATION DROP ROW,
  CONSTRAINT valid_conversation_id  EXPECT (conversation_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_message_id      EXPECT (message_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT success_status        EXPECT (status_code = 200) ON VIOLATION DROP ROW,
  CONSTRAINT valid_event_time      EXPECT (event_time IS NOT NULL)
)
COMMENT 'Raw aibiGenie message events from audit; filtered by genie.workspace_ids; lookback by genie.days_lookback (date) or genie.lookback_minutes (timestamp)'
CLUSTER BY (workspace_id, space_id)
AS
SELECT
  ae.workspace_id,
  w.workspace_name,
  w.workspace_url,
  CAST(ae.request_params['space_id'] AS STRING) AS space_id,
  CAST(ae.request_params['conversation_id'] AS STRING) AS conversation_id,
  CAST(ae.request_params['message_id'] AS STRING) AS message_id,
  ae.action_name,
  ae.event_time,
  ae.event_date,
  ae.user_identity.email AS user_email,
  ae.response.status_code AS status_code,
  ae.response.error_message AS error_message
FROM system.access.audit ae
INNER JOIN system.access.workspaces_latest w ON ae.workspace_id = w.workspace_id
WHERE ae.service_name = 'aibiGenie'
  AND ae.action_name IN ('genieGetConversationMessage', 'getConversationMessage')
  AND ae.request_params['space_id'] IS NOT NULL
  AND ae.request_params['conversation_id'] IS NOT NULL
  AND ae.request_params['message_id'] IS NOT NULL
  AND array_contains(split('${genie.workspace_ids}', ','), cast(ae.workspace_id AS STRING))
  -- Lookback: date-based (genie.lookback_minutes empty/0) or timestamp-based (e.g. last 30 min for continuous capture)
  AND (
    ( coalesce(trim('${genie.lookback_minutes}'), '') = '' OR try_cast(trim(coalesce('${genie.lookback_minutes}', '0')) AS INT) IS NULL OR try_cast(trim(coalesce('${genie.lookback_minutes}', '0')) AS INT) <= 0 )
    AND ae.event_date >= date_sub(current_date(), cast(${genie.days_lookback} AS INT))
    AND ae.event_date <= current_date()
  )
  OR (
    try_cast(trim('${genie.lookback_minutes}') AS INT) > 0
    AND ae.event_time >= current_timestamp() - make_interval(0, 0, 0, 0, 0, try_cast(trim('${genie.lookback_minutes}') AS INT), 0)
  );


-- -----------------------------------------------------------------------------
-- Silver: Deduplicated messages to fetch (one row per message_id)
-- Source for Python ingestion job. Expectations enforce required keys.
-- -----------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW genie_messages_to_fetch
(
  CONSTRAINT silver_valid_workspace_id   EXPECT (workspace_id IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT silver_valid_space_id       EXPECT (space_id IS NOT NULL AND length(trim(space_id)) > 0) ON VIOLATION FAIL UPDATE,
  CONSTRAINT silver_valid_conversation_id EXPECT (conversation_id IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT silver_valid_message_id     EXPECT (message_id IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT silver_valid_event_time     EXPECT (event_time IS NOT NULL)
)
COMMENT 'Deduplicated list of messages to fetch from Genie API; used by Python ingestion'
CLUSTER BY (workspace_id, space_id)
AS
SELECT
  workspace_id,
  workspace_name,
  workspace_url,
  space_id,
  conversation_id,
  message_id,
  event_time,
  event_date,
  user_email,
  action_name,
  status_code
FROM (
  SELECT
    workspace_id,
    workspace_name,
    workspace_url,
    space_id,
    conversation_id,
    message_id,
    event_time,
    event_date,
    user_email,
    action_name,
    status_code,
    row_number() OVER (PARTITION BY workspace_id, message_id ORDER BY event_time DESC) AS rn
  FROM genie_audit_message_events
)
WHERE rn = 1;


-- -----------------------------------------------------------------------------
-- Gold: Space-level metrics (aggregated by workspace and space)
-- -----------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW genie_space_metrics
COMMENT 'Space-level action counts and user counts for Genie spaces in scope'
CLUSTER BY (workspace_id, space_id)
AS
SELECT
  workspace_id,
  space_id,
  count(DISTINCT conversation_id) AS conversation_count,
  count(DISTINCT message_id)      AS message_count,
  count(DISTINCT user_email)      AS user_count,
  min(event_time)                 AS first_event_time,
  max(event_time)                 AS last_event_time,
  min(event_date)                 AS first_event_date,
  max(event_date)                 AS last_event_date
FROM genie_messages_to_fetch
GROUP BY workspace_id, space_id;


-- -----------------------------------------------------------------------------
-- Test / validation: single-row summary for pipeline health and tests
-- When genie.lookback_minutes is set, effective_start_date is approximate (start of date window for display only).
-- -----------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW genie_pipeline_validation
COMMENT 'Pipeline validation: row count and config for assertions and monitoring'
AS
SELECT
  count(*)                                       AS silver_row_count,
  current_date()                                 AS validation_date,
  cast('${genie.days_lookback}' AS INT)          AS configured_days_lookback,
  try_cast(trim(coalesce('${genie.lookback_minutes}', '')) AS INT) AS configured_lookback_minutes,
  date_sub(current_date(), cast('${genie.days_lookback}' AS INT)) AS effective_start_date
FROM genie_messages_to_fetch;
