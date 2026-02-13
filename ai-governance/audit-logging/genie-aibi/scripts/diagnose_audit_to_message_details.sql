-- =============================================================================
-- Genie observability: diagnose audit -> SOT -> message_details
-- Run in Databricks SQL or a notebook to verify system tables are feeding the pipeline.
-- =============================================================================

-- 1) Recent Genie message actions in system.access.audit (pipeline reads these two)
--    Pipeline filters: service_name = 'aibiGenie', action_name IN ('genieGetConversationMessage', 'getConversationMessage')
SELECT
  event_time,
  workspace_id,
  action_name,
  request_params['space_id']     AS space_id,
  request_params['message_id']   AS message_id,
  request_params['conversation_id'] AS conversation_id
FROM system.access.audit
WHERE service_name = 'aibiGenie'
  AND action_name IN ('genieGetConversationMessage', 'getConversationMessage')
  AND request_params['space_id'] IS NOT NULL
  AND request_params['message_id'] IS NOT NULL
ORDER BY event_time DESC
LIMIT 20;

-- 2) Counts by action (confirm pipeline's actions have recent data)
SELECT
  action_name,
  COUNT(*) AS cnt,
  MAX(event_time) AS latest
FROM system.access.audit
WHERE service_name = 'aibiGenie'
  AND action_name IN ('genieGetConversationMessage', 'getConversationMessage')
GROUP BY action_name
ORDER BY cnt DESC;

-- 3) SOT table: genie_messages_to_fetch (populated by SDP pipeline from audit)
SELECT
  workspace_id,
  COUNT(*) AS to_fetch_cnt,
  MAX(event_time) AS latest_event
FROM main.genie_analytics.genie_messages_to_fetch
GROUP BY workspace_id
ORDER BY workspace_id;

-- 4) Message details (output of ingestion job)
SELECT
  workspace_id,
  COUNT(*) AS in_details_cnt,
  MAX(created_timestamp) AS latest_ts
FROM main.genie_analytics.message_details
GROUP BY workspace_id
ORDER BY workspace_id;

-- 5) Gap: in SOT but not yet in message_details (should be fetched on next ingestion run)
SELECT
  f.workspace_id,
  f.space_id,
  COUNT(*) AS not_yet_ingested,
  MAX(f.event_time) AS latest_in_sot
FROM main.genie_analytics.genie_messages_to_fetch f
LEFT JOIN main.genie_analytics.message_details d
  ON d.workspace_id = f.workspace_id AND d.message_id = f.message_id
WHERE d.workspace_id IS NULL
GROUP BY f.workspace_id, f.space_id
ORDER BY latest_in_sot DESC
LIMIT 20;
