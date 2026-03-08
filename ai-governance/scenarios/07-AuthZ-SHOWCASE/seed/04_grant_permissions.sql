-- Phase 0 / Step 4 — Grant permissions to showcase groups.
--
-- Run after: 03_row_col_security.sql
-- Run before: 05_verify_security.sql
--
-- What this grants:
--   USE CATALOG  — all groups can access the authz_showcase catalog
--   USE SCHEMA   — all groups can use the sales schema (+ future schemas)
--   SELECT       — all groups can query all sales tables
--                  row filters + column masks (applied in step 3) determine
--                  what each group actually sees — not the grants themselves
--
-- Note: EXECUTE on row filter / column mask functions is NOT required.
-- Those functions execute with definer (owner) privileges inside UC;
-- the querying user only needs SELECT on the target table.


-- ══════════════════════════════════════════════════════════════════════════════
-- CATALOG: USE CATALOG
-- ══════════════════════════════════════════════════════════════════════════════

GRANT USE CATALOG ON CATALOG authz_showcase TO `authz_showcase_west`;
GRANT USE CATALOG ON CATALOG authz_showcase TO `authz_showcase_east`;
GRANT USE CATALOG ON CATALOG authz_showcase TO `authz_showcase_managers`;
GRANT USE CATALOG ON CATALOG authz_showcase TO `authz_showcase_finance`;
GRANT USE CATALOG ON CATALOG authz_showcase TO `authz_showcase_executives`;
GRANT USE CATALOG ON CATALOG authz_showcase TO `authz_showcase_admin`;


-- ══════════════════════════════════════════════════════════════════════════════
-- SCHEMA: authz_showcase.sales
-- ══════════════════════════════════════════════════════════════════════════════

GRANT USE SCHEMA ON SCHEMA authz_showcase.sales TO `authz_showcase_west`;
GRANT USE SCHEMA ON SCHEMA authz_showcase.sales TO `authz_showcase_east`;
GRANT USE SCHEMA ON SCHEMA authz_showcase.sales TO `authz_showcase_managers`;
GRANT USE SCHEMA ON SCHEMA authz_showcase.sales TO `authz_showcase_finance`;
GRANT USE SCHEMA ON SCHEMA authz_showcase.sales TO `authz_showcase_executives`;
GRANT USE SCHEMA ON SCHEMA authz_showcase.sales TO `authz_showcase_admin`;


-- ══════════════════════════════════════════════════════════════════════════════
-- TABLE: authz_showcase.sales.sales_reps
-- No row filter or column masks — all groups see all rows.
-- ══════════════════════════════════════════════════════════════════════════════

GRANT SELECT ON TABLE authz_showcase.sales.sales_reps TO `authz_showcase_west`;
GRANT SELECT ON TABLE authz_showcase.sales.sales_reps TO `authz_showcase_east`;
GRANT SELECT ON TABLE authz_showcase.sales.sales_reps TO `authz_showcase_managers`;
GRANT SELECT ON TABLE authz_showcase.sales.sales_reps TO `authz_showcase_finance`;
GRANT SELECT ON TABLE authz_showcase.sales.sales_reps TO `authz_showcase_executives`;
GRANT SELECT ON TABLE authz_showcase.sales.sales_reps TO `authz_showcase_admin`;


-- ══════════════════════════════════════════════════════════════════════════════
-- TABLE: authz_showcase.sales.opportunities
-- Row filter: reps see own rows only; managers/finance/exec/admin see all 15.
-- Column masks:
--   margin_pct  → NULL unless finance or exec
--   is_strategic → NULL unless managers or exec
-- ══════════════════════════════════════════════════════════════════════════════

GRANT SELECT ON TABLE authz_showcase.sales.opportunities TO `authz_showcase_west`;
GRANT SELECT ON TABLE authz_showcase.sales.opportunities TO `authz_showcase_east`;
GRANT SELECT ON TABLE authz_showcase.sales.opportunities TO `authz_showcase_managers`;
GRANT SELECT ON TABLE authz_showcase.sales.opportunities TO `authz_showcase_finance`;
GRANT SELECT ON TABLE authz_showcase.sales.opportunities TO `authz_showcase_executives`;
GRANT SELECT ON TABLE authz_showcase.sales.opportunities TO `authz_showcase_admin`;


-- ══════════════════════════════════════════════════════════════════════════════
-- TABLE: authz_showcase.sales.customers
-- Row filter: reps see own region only; managers/finance/exec/admin see all 10.
-- Column masks:
--   contract_value → NULL unless managers, finance, or exec
-- ══════════════════════════════════════════════════════════════════════════════

GRANT SELECT ON TABLE authz_showcase.sales.customers TO `authz_showcase_west`;
GRANT SELECT ON TABLE authz_showcase.sales.customers TO `authz_showcase_east`;
GRANT SELECT ON TABLE authz_showcase.sales.customers TO `authz_showcase_managers`;
GRANT SELECT ON TABLE authz_showcase.sales.customers TO `authz_showcase_finance`;
GRANT SELECT ON TABLE authz_showcase.sales.customers TO `authz_showcase_executives`;
GRANT SELECT ON TABLE authz_showcase.sales.customers TO `authz_showcase_admin`;


-- ══════════════════════════════════════════════════════════════════════════════
-- TABLE: authz_showcase.sales.products
-- No row filter — all groups see all 5 products.
-- Column masks:
--   cost_price → NULL unless finance or exec
-- ══════════════════════════════════════════════════════════════════════════════

GRANT SELECT ON TABLE authz_showcase.sales.products TO `authz_showcase_west`;
GRANT SELECT ON TABLE authz_showcase.sales.products TO `authz_showcase_east`;
GRANT SELECT ON TABLE authz_showcase.sales.products TO `authz_showcase_managers`;
GRANT SELECT ON TABLE authz_showcase.sales.products TO `authz_showcase_finance`;
GRANT SELECT ON TABLE authz_showcase.sales.products TO `authz_showcase_executives`;
GRANT SELECT ON TABLE authz_showcase.sales.products TO `authz_showcase_admin`;


-- ══════════════════════════════════════════════════════════════════════════════
-- FUTURE SCHEMAS — placeholder grants (populated in later phases)
-- ══════════════════════════════════════════════════════════════════════════════

-- Phase 2: Vector Search uses M2M (app SP) — individual groups do not need direct
-- access to knowledge_base tables. Grant USE SCHEMA here for direct SQL exploration.
GRANT USE SCHEMA ON SCHEMA authz_showcase.knowledge_base TO `authz_showcase_admin`;

-- Phase 3: UC Functions — EXECUTE granted per function in 07_grant_uc_functions.sql.
-- Grant USE SCHEMA now so the schema is discoverable.
GRANT USE SCHEMA ON SCHEMA authz_showcase.functions TO `authz_showcase_admin`;


-- ══════════════════════════════════════════════════════════════════════════════
-- VERIFY
-- ══════════════════════════════════════════════════════════════════════════════
SHOW GRANTS ON TABLE authz_showcase.sales.opportunities;
