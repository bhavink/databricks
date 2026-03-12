-- Phase 0 / Step 0 — Create catalog and schemas.
--
-- Run order: this script first, then 01_create_groups.py, then 02_seed_data.py.
-- Works on any Databricks workspace (AWS, GCP, Azure) with Unity Catalog enabled.
--
-- Usage (Databricks CLI):
--   databricks sql exec --profile <YOUR_CLI_PROFILE> --file 00_catalog_schema.sql
--
-- Or run each statement manually in a notebook / SQL editor.

-- ── Catalog ──────────────────────────────────────────────────────────────────
CREATE CATALOG IF NOT EXISTS authz_showcase
  COMMENT 'AI Auth Showcase — demonstrates Databricks auth/authz patterns from first principles.';

-- ── Schemas ───────────────────────────────────────────────────────────────────

-- Core business data: opportunities, customers, products, sales reps.
-- Row filters and column masks applied here (Step 3).
CREATE SCHEMA IF NOT EXISTS authz_showcase.sales
  COMMENT 'Retail sales data with row-level and column-level security applied.';

-- Documents for Vector Search RAG (Phase 2).
-- No row/col security — shared knowledge base, accessed via M2M app SP.
CREATE SCHEMA IF NOT EXISTS authz_showcase.knowledge_base
  COMMENT 'Product docs and sales playbooks for Vector Search RAG. Shared — no per-user filtering.';

-- UC Functions for business logic (Phase 3).
CREATE SCHEMA IF NOT EXISTS authz_showcase.functions
  COMMENT 'UC Functions: quota lookup, attainment calculation, deal recommendations.';

-- ── Verify ────────────────────────────────────────────────────────────────────
SHOW SCHEMAS IN authz_showcase;
