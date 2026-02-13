-- =============================================================================
-- Genie Observability – Data model (persisted tables)
-- =============================================================================
-- Run this once to create the schema and tables. Aligns with
-- docs/genie-messages-persistence-strategy.md. Python ingestion appends to
-- message_details; dashboard queries read from these tables.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Schema
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS main.genie_analytics;


-- -----------------------------------------------------------------------------
-- message_details: single denormalized table for message + attachments + query perf
-- Partitioned by created_date; clustered by workspace_id, space_id for filter/join perf.
-- Python ingestion (genie_message_ingestion.py) appends; query_* columns can be
-- backfilled from system.query.history via a separate job or view.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS main.genie_analytics.message_details (
  -- Primary Keys
  workspace_id STRING NOT NULL,
  message_id STRING NOT NULL,

  -- Hierarchy
  space_id STRING NOT NULL,
  conversation_id STRING NOT NULL,
  space_name STRING COMMENT 'Space display name (title) from Genie API GET space; improves readability alongside space_id',

  -- Workspace Context
  workspace_name STRING,

  -- Message Content
  content STRING COMMENT 'User question/input',
  status STRING COMMENT 'COMPLETED, FAILED, CANCELED',
  created_timestamp LONG COMMENT 'Unix timestamp in milliseconds',
  updated_timestamp LONG,
  created_date DATE GENERATED ALWAYS AS (DATE(FROM_UNIXTIME(created_timestamp / 1000))),

  -- SQL Generation (from attachments)
  query_sql STRING COMMENT 'SQL extracted from query attachments',
  query_description STRING COMMENT 'What Genie understood from user question',
  statement_id STRING COMMENT 'Links to system.query.history',

  -- Attachments Summary
  attachments_count INT,
  attachments_json STRING COMMENT 'Full attachments array as JSON',

  -- Query Performance (denormalized from system.query.history; backfill optional)
  query_execution_status STRING,
  query_duration_ms LONG,
  query_start_time TIMESTAMP,
  query_end_time TIMESTAMP,
  query_warehouse_id STRING,
  query_read_rows LONG,
  query_read_bytes LONG,
  query_error_message STRING,

  -- API Fetch Metadata
  api_fetch_timestamp TIMESTAMP,
  api_fetch_status STRING,
  api_fetch_error STRING,

  -- Audit Trail
  ingestion_timestamp TIMESTAMP,
  ingestion_batch_id STRING
)
USING DELTA
PARTITIONED BY (created_date)
CLUSTER BY (workspace_id, space_id)
COMMENT 'Genie message details from API; denormalized for analytics. See docs/genie-messages-persistence-strategy.md';


-- -----------------------------------------------------------------------------
-- message_fetch_errors: track failed API calls for retry and monitoring
-- -----------------------------------------------------------------------------
-- Omit DEFAULT on retry_count/resolved for compatibility with Delta without column-defaults feature.
-- Ingestion always supplies 0 and FALSE when inserting.
CREATE TABLE IF NOT EXISTS main.genie_analytics.message_fetch_errors (
  workspace_id STRING,
  message_id STRING,
  space_id STRING,
  conversation_id STRING,
  error_type STRING COMMENT 'AUTH_ERROR, TIMEOUT, RATE_LIMITED, FAILED',
  error_message STRING,
  error_timestamp TIMESTAMP,
  retry_count INT,
  resolved BOOLEAN
)
USING DELTA
COMMENT 'Failed Genie message API fetches; use for retry and monitoring.';


-- -----------------------------------------------------------------------------
-- genie_space_details: full space config from GET /api/2.0/genie/spaces/{space_id}?include_serialized_space=true
-- Filled by Python job genie_space_details.py. Use serialized_space with Create/Update Genie Space API to
-- promote spaces across workspaces or create backups. Merge by (workspace_id, space_id) on each run.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS main.genie_analytics.genie_space_details (
  workspace_id STRING NOT NULL,
  space_id STRING NOT NULL,
  title STRING COMMENT 'Space display name',
  description STRING,
  warehouse_id STRING,
  created_timestamp LONG,
  last_updated_timestamp LONG,
  serialized_space STRING COMMENT 'Serialized space config (instructions, benchmarks, joins, data_sources); use with Create/Update Genie Space API',
  api_fetch_status STRING COMMENT 'SUCCESS or FAILED',
  api_fetch_error STRING,
  ingestion_timestamp TIMESTAMP,
  ingestion_batch_id STRING
)
USING DELTA
CLUSTER BY (workspace_id, space_id)
COMMENT 'Genie space metadata and serialized config; for backup and promote. See python/genie_space_details.py';


-- -----------------------------------------------------------------------------
-- Optional: view that joins message_details with system.query.history for live query perf
-- (Use when query_* columns in message_details are not backfilled.)
-- -----------------------------------------------------------------------------
-- CREATE OR REPLACE VIEW main.genie_analytics.message_details_with_query_perf AS
-- SELECT
--   md.*,
--   qh.execution_status    AS query_execution_status,
--   qh.total_duration_ms   AS query_duration_ms,
--   qh.start_time          AS query_start_time,
--   qh.end_time            AS query_end_time,
--   qh.compute.warehouse_id AS query_warehouse_id,
--   qh.read_rows           AS query_read_rows,
--   qh.read_bytes          AS query_read_bytes,
--   qh.error_message       AS query_error_message
-- FROM main.genie_analytics.message_details md
-- LEFT JOIN system.query.history qh
--   ON md.statement_id = qh.statement_id AND md.workspace_id = qh.workspace_id;
