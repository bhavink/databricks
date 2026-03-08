-- Phase 0 / Step 5 — Verify row filters and column masks are working.
--
-- Run after: 04_grant_permissions.sql
-- Gate to Phase 1: all checks must show PASS before building the app.
--
-- How to use:
--   1. Run the full file as yourself (you should be in authz_showcase_west
--      from 02_seed_data.py — the seed script maps CURRENT_USER_EMAIL to rep_001).
--   2. All "West Rep" checks should show PASS.
--   3. Switch groups and re-run to verify other personas:
--
--      Add to managers:    databricks groups add-member --group-name authz_showcase_managers --member-email you@databricks.com
--      Add to finance:     databricks groups add-member --group-name authz_showcase_finance  --member-email you@databricks.com
--      Add to executives:  databricks groups add-member --group-name authz_showcase_executives --member-email you@databricks.com
--
--   4. Remove from previous group before adding to next, or results will reflect
--      the highest-privilege group (is_member is OR'd in the filter functions).
--
-- Row counts in the seed data (02_seed_data.py):
--   sales_reps    : 8 total (WEST: 3, EAST: 3, CENTRAL: 2)  — no row filter
--   opportunities : 15 total (WEST: 7, EAST: 5, CENTRAL: 3) — row-filtered
--   customers     : 10 total (WEST: 4, EAST: 4, CENTRAL: 2) — row-filtered
--   products      : 5 total                                  — no row filter
--
-- West Rep (seed user, rep_001):  4 own opportunities, 4 WEST customers
-- East Rep (e.g. carol.jones):    2 own opportunities, 4 EAST customers
-- Managers / Finance / Exec:     15 opportunities,   10 customers


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 0 — Who am I?
-- Run this first to confirm your identity and detected persona.
-- ══════════════════════════════════════════════════════════════════════════════

SELECT current_user() AS current_user;

SELECT
  CASE
    WHEN is_member('authz_showcase_admin')      THEN 'admin'
    WHEN is_member('authz_showcase_executives') THEN 'executive'
    WHEN is_member('authz_showcase_finance')    THEN 'finance'
    WHEN is_member('authz_showcase_managers')   THEN 'manager'
    WHEN is_member('authz_showcase_east')       THEN 'east_rep'
    WHEN is_member('authz_showcase_west')       THEN 'west_rep'
    ELSE '⚠ not in any authz_showcase group — add yourself first'
  END AS detected_persona,
  is_member('authz_showcase_west')       AS in_west,
  is_member('authz_showcase_east')       AS in_east,
  is_member('authz_showcase_managers')   AS in_managers,
  is_member('authz_showcase_finance')    AS in_finance,
  is_member('authz_showcase_executives') AS in_executives,
  is_member('authz_showcase_admin')      AS in_admin;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 1 — Row filter: opportunities
-- ══════════════════════════════════════════════════════════════════════════════

-- CHECK 1a: Row count matches persona
--   west_rep (seed user) → 4    (own opportunities only)
--   east_rep             → varies by rep (Carol: 2, Dave: 2, Eve: 1)
--   manager / finance / exec / admin → 15 (all rows)
SELECT
  'check_1a_opportunities_row_count' AS check_name,
  COUNT(*)                           AS actual_count,
  CASE
    WHEN is_member('authz_showcase_admin')
      OR is_member('authz_showcase_executives')
      OR is_member('authz_showcase_finance')
      OR is_member('authz_showcase_managers')
    THEN CASE WHEN COUNT(*) = 15
              THEN 'PASS — all 15 rows visible (elevated persona)'
              ELSE CONCAT('FAIL — expected 15, got ', COUNT(*))
         END
    WHEN is_member('authz_showcase_west')
    THEN CASE WHEN COUNT(*) = 4
              THEN 'PASS — 4 own opportunities (west_rep seed user)'
              ELSE CONCAT('FAIL — expected 4 for seed west rep, got ', COUNT(*))
         END
    WHEN is_member('authz_showcase_east')
    THEN CASE WHEN COUNT(*) BETWEEN 1 AND 3
              THEN CONCAT('PASS — ', COUNT(*), ' own opportunities (east_rep)')
              ELSE CONCAT('FAIL — expected 1-3 for an east rep, got ', COUNT(*))
         END
    ELSE '⚠ not in any group — cannot validate'
  END AS result
FROM authz_showcase.sales.opportunities;

-- CHECK 1b: Rep cannot see another rep's rows
--   A west_rep should see ONLY rows where rep_email = current_user().
--   This count should equal CHECK 1a when in a rep group.
SELECT
  'check_1b_own_rows_only' AS check_name,
  COUNT(*)                 AS rows_not_owned_by_me,
  CASE
    WHEN is_member('authz_showcase_admin')
      OR is_member('authz_showcase_executives')
      OR is_member('authz_showcase_finance')
      OR is_member('authz_showcase_managers')
    THEN 'SKIP — elevated persona sees all rows by design'
    WHEN COUNT(*) = 0
    THEN 'PASS — rep sees only own rows'
    ELSE CONCAT('FAIL — rep can see ', COUNT(*), ' rows belonging to other reps')
  END AS result
FROM authz_showcase.sales.opportunities
WHERE rep_email <> current_user();


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 2 — Row filter: customers
-- ══════════════════════════════════════════════════════════════════════════════

-- CHECK 2a: Row count matches persona
--   west_rep  → 4 (WEST customers: Acme, Pacific Retail, SunState, Global Tech)
--   east_rep  → 4 (EAST customers: Atlantic, Northeast Health, Boston, Metro Ins)
--   manager / finance / exec / admin → 10 (all)
SELECT
  'check_2a_customers_row_count' AS check_name,
  COUNT(*)                       AS actual_count,
  CASE
    WHEN is_member('authz_showcase_admin')
      OR is_member('authz_showcase_executives')
      OR is_member('authz_showcase_finance')
      OR is_member('authz_showcase_managers')
    THEN CASE WHEN COUNT(*) = 10
              THEN 'PASS — all 10 customers visible (elevated persona)'
              ELSE CONCAT('FAIL — expected 10, got ', COUNT(*))
         END
    WHEN is_member('authz_showcase_west')
    THEN CASE WHEN COUNT(*) = 4
              THEN 'PASS — 4 WEST customers visible'
              ELSE CONCAT('FAIL — expected 4 WEST customers, got ', COUNT(*))
         END
    WHEN is_member('authz_showcase_east')
    THEN CASE WHEN COUNT(*) = 4
              THEN 'PASS — 4 EAST customers visible'
              ELSE CONCAT('FAIL — expected 4 EAST customers, got ', COUNT(*))
         END
    ELSE '⚠ not in any group — cannot validate'
  END AS result
FROM authz_showcase.sales.customers;

-- CHECK 2b: Reps only see their own region's customers
SELECT
  'check_2b_own_region_only' AS check_name,
  COLLECT_LIST(DISTINCT region) AS regions_visible,
  CASE
    WHEN is_member('authz_showcase_admin')
      OR is_member('authz_showcase_executives')
      OR is_member('authz_showcase_finance')
      OR is_member('authz_showcase_managers')
    THEN 'SKIP — elevated persona sees all regions by design'
    WHEN is_member('authz_showcase_west') AND SIZE(COLLECT_SET(region)) = 1
      AND ARRAY_CONTAINS(COLLECT_SET(region), 'WEST')
    THEN 'PASS — west_rep sees only WEST region customers'
    WHEN is_member('authz_showcase_east') AND SIZE(COLLECT_SET(region)) = 1
      AND ARRAY_CONTAINS(COLLECT_SET(region), 'EAST')
    THEN 'PASS — east_rep sees only EAST region customers'
    ELSE CONCAT('FAIL — unexpected regions visible: ', TO_JSON(COLLECT_SET(region)))
  END AS result
FROM authz_showcase.sales.customers;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 3 — No row filter: sales_reps and products
-- These tables have no row filter — all authenticated users see all rows.
-- ══════════════════════════════════════════════════════════════════════════════

SELECT
  'check_3a_sales_reps_all_visible' AS check_name,
  COUNT(*)                          AS actual_count,
  CASE WHEN COUNT(*) = 8
       THEN 'PASS — all 8 reps visible (no row filter)'
       ELSE CONCAT('FAIL — expected 8, got ', COUNT(*))
  END AS result
FROM authz_showcase.sales.sales_reps;

SELECT
  'check_3b_products_all_visible' AS check_name,
  COUNT(*)                        AS actual_count,
  CASE WHEN COUNT(*) = 5
       THEN 'PASS — all 5 products visible (no row filter)'
       ELSE CONCAT('FAIL — expected 5, got ', COUNT(*))
  END AS result
FROM authz_showcase.sales.products;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 4 — Column mask: margin_pct (opportunities)
-- Visible only to: authz_showcase_finance, authz_showcase_executives, authz_showcase_admin
-- NULL for: west_rep, east_rep, managers
-- ══════════════════════════════════════════════════════════════════════════════

SELECT
  'check_4_margin_pct_mask' AS check_name,
  COUNT(*)                  AS total_rows_seen,
  COUNT(margin_pct)         AS non_null_margin_count,
  CASE
    WHEN is_member('authz_showcase_finance')
      OR is_member('authz_showcase_executives')
      OR is_member('authz_showcase_admin')
    THEN CASE WHEN COUNT(margin_pct) = COUNT(*)
              THEN 'PASS — margin_pct visible (finance/exec/admin persona)'
              ELSE CONCAT('FAIL — expected all non-null, got ', COUNT(margin_pct), ' of ', COUNT(*))
         END
    ELSE  -- reps and managers should see NULL
      CASE WHEN COUNT(margin_pct) = 0
           THEN 'PASS — margin_pct masked as NULL'
           ELSE CONCAT('FAIL — expected all NULL, got ', COUNT(margin_pct), ' non-null values (mask not applied)')
      END
  END AS result
FROM authz_showcase.sales.opportunities;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 5 — Column mask: is_strategic (opportunities)
-- Visible only to: authz_showcase_managers, authz_showcase_executives, authz_showcase_admin
-- NULL for: west_rep, east_rep, finance
-- ══════════════════════════════════════════════════════════════════════════════

SELECT
  'check_5_is_strategic_mask' AS check_name,
  COUNT(*)                    AS total_rows_seen,
  COUNT(is_strategic)         AS non_null_strategic_count,
  CASE
    WHEN is_member('authz_showcase_managers')
      OR is_member('authz_showcase_executives')
      OR is_member('authz_showcase_admin')
    THEN CASE WHEN COUNT(is_strategic) = COUNT(*)
              THEN 'PASS — is_strategic visible (manager/exec/admin persona)'
              ELSE CONCAT('FAIL — expected all non-null, got ', COUNT(is_strategic), ' of ', COUNT(*))
         END
    ELSE  -- reps and finance should see NULL
      CASE WHEN COUNT(is_strategic) = 0
           THEN 'PASS — is_strategic masked as NULL'
           ELSE CONCAT('FAIL — expected all NULL, got ', COUNT(is_strategic), ' non-null values (mask not applied)')
      END
  END AS result
FROM authz_showcase.sales.opportunities;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 6 — Column mask: contract_value (customers)
-- Visible only to: authz_showcase_managers, authz_showcase_finance, authz_showcase_executives, authz_showcase_admin
-- NULL for: west_rep, east_rep
-- ══════════════════════════════════════════════════════════════════════════════

SELECT
  'check_6_contract_value_mask' AS check_name,
  COUNT(*)                      AS total_rows_seen,
  COUNT(contract_value)         AS non_null_contract_count,
  CASE
    WHEN is_member('authz_showcase_managers')
      OR is_member('authz_showcase_finance')
      OR is_member('authz_showcase_executives')
      OR is_member('authz_showcase_admin')
    THEN CASE WHEN COUNT(contract_value) = COUNT(*)
              THEN 'PASS — contract_value visible (manager/finance/exec/admin persona)'
              ELSE CONCAT('FAIL — expected all non-null, got ', COUNT(contract_value), ' of ', COUNT(*))
         END
    ELSE  -- reps should see NULL
      CASE WHEN COUNT(contract_value) = 0
           THEN 'PASS — contract_value masked as NULL'
           ELSE CONCAT('FAIL — expected all NULL, got ', COUNT(contract_value), ' non-null values (mask not applied)')
      END
  END AS result
FROM authz_showcase.sales.customers;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 7 — Column mask: cost_price (products)
-- Visible only to: authz_showcase_finance, authz_showcase_executives, authz_showcase_admin
-- NULL for: west_rep, east_rep, managers
-- ══════════════════════════════════════════════════════════════════════════════

SELECT
  'check_7_cost_price_mask' AS check_name,
  COUNT(*)                  AS total_rows_seen,
  COUNT(cost_price)         AS non_null_cost_count,
  CASE
    WHEN is_member('authz_showcase_finance')
      OR is_member('authz_showcase_executives')
      OR is_member('authz_showcase_admin')
    THEN CASE WHEN COUNT(cost_price) = COUNT(*)
              THEN 'PASS — cost_price visible (finance/exec/admin persona)'
              ELSE CONCAT('FAIL — expected all non-null, got ', COUNT(cost_price), ' of ', COUNT(*))
         END
    ELSE  -- reps and managers should see NULL
      CASE WHEN COUNT(cost_price) = 0
           THEN 'PASS — cost_price masked as NULL'
           ELSE CONCAT('FAIL — expected all NULL, got ', COUNT(cost_price), ' non-null values (mask not applied)')
      END
  END AS result
FROM authz_showcase.sales.products;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 8 — Summary: raw view of masked columns (spot-check)
-- Useful for eyeballing after switching personas.
-- ══════════════════════════════════════════════════════════════════════════════

-- Opportunities: show first 5 rows with all potentially-masked columns
SELECT
  opp_id, rep_email, region, stage, amount,
  margin_pct,   -- NULL unless finance/exec/admin
  is_strategic  -- NULL unless managers/exec/admin
FROM authz_showcase.sales.opportunities
ORDER BY opp_id
LIMIT 5;

-- Customers: show first 5 rows with masked column
SELECT
  customer_id, name, industry, tier, region,
  contract_value  -- NULL unless managers/finance/exec/admin
FROM authz_showcase.sales.customers
ORDER BY customer_id
LIMIT 5;

-- Products: show all with masked column
SELECT
  product_id, name, category, list_price,
  cost_price  -- NULL unless finance/exec/admin
FROM authz_showcase.sales.products
ORDER BY product_id;


-- ══════════════════════════════════════════════════════════════════════════════
-- EXPECTED RESULTS PER PERSONA (reference)
-- ══════════════════════════════════════════════════════════════════════════════
--
-- Persona           | opps | customers | margin_pct | is_strategic | contract_value | cost_price
-- ------------------|------|-----------|------------|--------------|----------------|------------
-- west_rep (seed)   |    4 |         4 | NULL       | NULL         | NULL           | NULL
-- east_rep (carol)  |    2 |         4 | NULL       | NULL         | NULL           | NULL
-- manager           |   15 |        10 | NULL       | visible      | visible        | NULL
-- finance           |   15 |        10 | visible    | NULL         | visible        | visible
-- executive         |   15 |        10 | visible    | visible      | visible        | visible
-- admin             |   15 |        10 | visible    | visible      | visible        | visible
--
-- All personas see: 8 sales_reps, 5 products (no row filter on these tables)
