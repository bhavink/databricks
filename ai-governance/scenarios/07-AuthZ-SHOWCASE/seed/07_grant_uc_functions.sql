-- Phase 3 / Step 2 — Grant EXECUTE on UC functions per group.
--
-- IMPORTANT: Workspace-local groups (created via w.groups.create()) are NOT
-- valid UC GRANT principals — SQL GRANT TO `authz_showcase_west` fails with
-- PRINCIPAL_DOES_NOT_EXIST. UC GRANT works with account-level groups only.
--
-- Workaround used in this demo:
--   1. GRANT EXECUTE to `account users` (built-in principal = all workspace users)
--   2. Access control enforced INSIDE get_rep_quota via is_member() which works
--      with workspace groups (checked against the caller's JWT token claims).
--   3. calculate_attainment and recommend_next_action are open to all callers;
--      the row filter on opportunities limits what each caller actually sees.
--
-- Run after: 07_create_uc_functions.sql
--
-- IMPORTANT: Re-run these GRANTs after any CREATE OR REPLACE FUNCTION.
-- CREATE OR REPLACE drops all existing GRANT/REVOKE on the replaced function.

GRANT USE SCHEMA ON SCHEMA authz_showcase.functions TO `account users`;
GRANT EXECUTE ON FUNCTION authz_showcase.functions.get_rep_quota        TO `account users`;
GRANT EXECUTE ON FUNCTION authz_showcase.functions.calculate_attainment TO `account users`;
GRANT EXECUTE ON FUNCTION authz_showcase.functions.recommend_next_action TO `account users`;


-- ── Verification ──────────────────────────────────────────────────────────────
-- As a West Rep (should fail for get_rep_quota, succeed for others):
--   SELECT authz_showcase.functions.get_rep_quota('west-rep@databricks.com');
--   → PERMISSION_DENIED (correct — reps cannot see quotas)
--
--   SELECT authz_showcase.functions.calculate_attainment('west-rep@databricks.com');
--   → returns attainment % for that rep only
--
-- As a Manager (should succeed for all):
--   SELECT authz_showcase.functions.get_rep_quota('any-rep@databricks.com');
--   → returns quota value
