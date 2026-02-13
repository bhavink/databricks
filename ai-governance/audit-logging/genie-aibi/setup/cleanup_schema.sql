-- =============================================================================
-- Clean up schema main.genie_analytics before running ingestion on Databricks
-- =============================================================================
-- Run this once (e.g. in a SQL notebook or SQL Editor) to drop the schema and
-- all tables in it, then recreate an empty schema. Use before first run or to
-- reset state.
-- =============================================================================

DROP SCHEMA IF EXISTS main.genie_analytics CASCADE;
CREATE SCHEMA main.genie_analytics;
