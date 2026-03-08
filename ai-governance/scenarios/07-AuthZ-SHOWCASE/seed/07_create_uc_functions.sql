-- Phase 3 / Step 1 — Create UC Functions in authz_showcase.functions schema.
--
-- Three business-logic functions for Tab 3 of the AI Auth Showcase app:
--   get_rep_quota        — quota by rep email (managers/finance/exec only)
--   calculate_attainment — closed-won vs quota (all groups; row filter scopes to rep)
--   recommend_next_action — rule-based next action by opp_id (all groups)
--
-- Auth teaching moment:
--   EXECUTE privilege is the access gate — not table-level SELECT.
--   get_rep_quota is restricted to managers/finance/exec because reps
--   should not be able to look up each other's quotas.
--   calculate_attainment is open to all — each caller can only compute
--   attainment for reps visible to them (row filter applied at query time).
--
-- Run after:  04_grant_permissions.sql  (catalog + schemas already exist)
-- Run before: 07_grant_uc_functions.sql
--
-- Test gate:
--   SELECT authz_showcase.functions.get_rep_quota('your-email@databricks.com');
--   → should return a quota value (e.g. 150000.00)


-- Safety net: ensure the functions schema exists
CREATE SCHEMA IF NOT EXISTS authz_showcase.functions;


-- ── 1. get_rep_quota ──────────────────────────────────────────────────────────
-- Returns the current-quarter quota for a rep.
--
-- Access control is enforced by the column mask on sales_reps.quota (mask_quota),
-- not inside this function. The UC engine applies the mask at query time regardless
-- of who calls it — Genie, direct SQL, Agent Bricks OBO, or M2M. This means:
--   - Reps get NULL automatically (mask returns NULL for non-managers/finance/exec)
--   - No is_member() check needed here — keeping the function body clean
--   - The same protection applies everywhere, not just when this function is called
--
-- This is the preferred pattern: push access control to the data layer (column mask),
-- not the function layer. See 03_row_col_security.sql → mask_quota.
CREATE OR REPLACE FUNCTION authz_showcase.functions.get_rep_quota(p_rep_email STRING)
  RETURNS DECIMAL(12, 2)
  LANGUAGE SQL
  COMMENT 'Returns current-quarter sales quota for a rep. Access control enforced by mask_quota column mask on sales_reps.quota — UC engine applies it at every access path, not just when this function is called.'
  RETURN (
    SELECT quota
    FROM authz_showcase.sales.sales_reps
    WHERE email = p_rep_email
    LIMIT 1
  );


-- ── 2. calculate_attainment ───────────────────────────────────────────────────
-- Returns attainment % = (sum of CLOSED_WON amounts / quota) * 100.
-- Queries opportunities — the row filter (filter_opportunities) is enforced
-- at query time using current_user() identity.
--
-- When called OBO (user token): row filter limits to that user's own rows
--   → reps can only compute their own attainment.
-- When called M2M (app SP): SP must be in authz_showcase_executives so the
--   row filter passes for all rows, enabling Tab 3 to serve any user's data.
--   See 07_grant_uc_functions.sql for SP group membership.

CREATE OR REPLACE FUNCTION authz_showcase.functions.calculate_attainment(p_rep_email STRING)
  RETURNS DECIMAL(5, 2)
  LANGUAGE SQL
  COMMENT 'Returns attainment % (closed-won amount / quota * 100) for a rep. Row filter on opportunities is enforced at query time.'
  -- Uses CTE to compute quota inline (can't call get_rep_quota which has access gate).
  -- Quota is used only as a divisor — not returned directly to the caller.
  RETURN (
    WITH quota AS (
      SELECT CASE r.region
               WHEN 'WEST'    THEN CAST(150000.00 AS DECIMAL(12, 2))
               WHEN 'EAST'    THEN CAST(130000.00 AS DECIMAL(12, 2))
               WHEN 'CENTRAL' THEN CAST(120000.00 AS DECIMAL(12, 2))
               ELSE                CAST(100000.00 AS DECIMAL(12, 2))
             END AS q
      FROM authz_showcase.sales.sales_reps r
      WHERE r.email = p_rep_email LIMIT 1
    ),
    won AS (
      SELECT COALESCE(
        SUM(CASE WHEN o.stage = 'CLOSED_WON' THEN o.amount ELSE CAST(0 AS DECIMAL(12, 2)) END),
        CAST(0 AS DECIMAL(12, 2))
      ) AS w
      FROM authz_showcase.sales.opportunities o
      WHERE o.rep_email = p_rep_email
    )
    SELECT CAST(won.w / quota.q * CAST(100 AS DECIMAL(12, 2)) AS DECIMAL(5, 2))
    FROM won, quota
  );
  -- Notes:
  -- ROUND(expr, scale) is not allowed in UC SQL UDFs — use CAST(... AS DECIMAL).
  -- Subqueries inside aggregate functions require CTE restructuring.


-- ── 3. recommend_next_action ──────────────────────────────────────────────────
-- Returns a rule-based recommended next action for an opportunity.
-- Based on current stage — demonstrates UC function as a business logic layer
-- without requiring external LLM calls inside the function itself.
-- The app calls this via SQL and then optionally augments with FM in the UI.

CREATE OR REPLACE FUNCTION authz_showcase.functions.recommend_next_action(p_opp_id STRING)
  RETURNS STRING
  LANGUAGE SQL
  COMMENT 'Returns a recommended next action for an opportunity based on its current stage. Available to all groups via EXECUTE privilege.'
  RETURN (
    SELECT
      CASE o.stage
        WHEN 'PROSPECT'    THEN 'Send personalized intro email and connect on LinkedIn. Goal: secure a 30-min discovery call within 2 weeks.'
        WHEN 'DISCOVERY'   THEN 'Complete MEDDIC qualification. Identify economic buyer and schedule a technical deep dive with your champion.'
        WHEN 'PROPOSAL'    THEN 'Prepare executive ROI analysis and business case. Loop in Solutions Architect for technical validation.'
        WHEN 'NEGOTIATION' THEN 'Address top 3 objections with data. Involve exec sponsor and confirm a mutual close plan with defined success criteria.'
        WHEN 'CLOSED_WON'  THEN 'Transition to Customer Success within 48h. Schedule kickoff call within 2 weeks. Document key success drivers.'
        WHEN 'CLOSED_LOST' THEN 'Conduct loss review: document key decision criteria missed. Flag for re-engagement in 6 months if budget-driven.'
        ELSE 'Review opportunity details and align on next steps with your manager.'
      END
    FROM authz_showcase.sales.opportunities o
    WHERE o.opp_id = p_opp_id
    LIMIT 1
  );


-- ── Verification ──────────────────────────────────────────────────────────────
-- Run as a user with EXECUTE privilege to confirm functions exist and return values.
-- Replace the email/opp_id with real values from your seeded data.
--
-- SELECT authz_showcase.functions.get_rep_quota('your-email@databricks.com');
-- SELECT authz_showcase.functions.calculate_attainment('your-email@databricks.com');
-- SELECT authz_showcase.functions.recommend_next_action('OPP001');
--
-- Expected: quota value, attainment %, and a recommendation string.
-- If PERMISSION_DENIED on get_rep_quota → you are a rep (correct behavior).
