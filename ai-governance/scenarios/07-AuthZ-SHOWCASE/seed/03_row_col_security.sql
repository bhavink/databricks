-- Phase 0 / Step 3 — Row filters and column masks.
--
-- Creates filter/mask functions in authz_showcase.sales, then applies them
-- to the tables. Safe to re-run (CREATE OR REPLACE).
--
-- Run after: 02_seed_data.py
-- Run before: 04_grant_permissions.sql
--
-- Design principle: UC engine enforces all policies at query time, regardless
-- of access path (direct SQL, Genie, Agent Bricks OBO, UC functions, etc.).
-- Prefer table-level column masks over function-body is_member() checks —
-- table policies are central, auditable, and cannot be bypassed by any caller.
--
-- mask_quota uses current_user() lookup (NOT is_member()) because:
--   - is_member() evaluates the SQL execution identity, not the OBO caller's groups.
--   - Genie and Agent Bricks run queries under a service identity; only current_user()
--     is correctly injected with the API caller's email in OBO contexts.
--   - quota_viewers table replaces group-membership check with a UC-governed allowlist
--     that is evaluated via current_user() — works at every access path.
--
-- What this enforces:
--   opportunities : reps see own rows only; managers/finance/exec/admin see all
--   customers     : reps see own region only; managers/finance/exec/admin see all
--   margin_pct    : NULL unless finance or exec
--   is_strategic  : NULL unless managers or exec
--   contract_value: NULL unless managers, finance, or exec
--   cost_price    : NULL unless finance or exec
--   quota         : NULL unless user_email is in quota_viewers table


-- ══════════════════════════════════════════════════════════════════════════════
-- ROW FILTER FUNCTIONS
-- ══════════════════════════════════════════════════════════════════════════════

-- ── opportunities ─────────────────────────────────────────────────────────────
-- A rep sees only rows where rep_email matches their identity.
-- Managers, finance, executives, and admin see all rows.
-- quota_viewers check added so privileged users see all rows via Genie OBO
-- (is_member() does not propagate through Genie/Agent Bricks OBO; current_user()
-- lookup in quota_viewers does).
CREATE OR REPLACE FUNCTION authz_showcase.sales.filter_opportunities(opp_rep_email STRING)
  RETURNS BOOLEAN
  RETURN (
    is_member('authz_showcase_executives') OR
    is_member('authz_showcase_finance')    OR
    is_member('authz_showcase_managers')   OR
    is_member('authz_showcase_admin')      OR
    EXISTS (SELECT 1 FROM authz_showcase.sales.quota_viewers WHERE user_email = current_user()) OR
    opp_rep_email = current_user()
  );

-- ── customers ─────────────────────────────────────────────────────────────────
-- A rep sees only customers in their own region.
-- Managers, finance, executives, and admin see all customers.
-- Uses rep_regions (policy-free) for the region lookup instead of sales_reps,
-- because sales_reps has mask_quota — UC does not allow a policy function to
-- reference a table that itself has any policy (nested policy chain violation).
CREATE OR REPLACE FUNCTION authz_showcase.sales.filter_customers(cust_region STRING)
  RETURNS BOOLEAN
  RETURN (
    is_member('authz_showcase_executives') OR
    is_member('authz_showcase_finance')    OR
    is_member('authz_showcase_managers')   OR
    is_member('authz_showcase_admin')      OR
    EXISTS (SELECT 1 FROM authz_showcase.sales.quota_viewers WHERE user_email = current_user()) OR
    EXISTS (
      SELECT 1
      FROM   authz_showcase.sales.rep_regions
      WHERE  email  = current_user()
      AND    region = cust_region
    )
  );


-- ══════════════════════════════════════════════════════════════════════════════
-- COLUMN MASK FUNCTIONS
-- ══════════════════════════════════════════════════════════════════════════════

-- ── margin_pct (opportunities) ────────────────────────────────────────────────
-- Sensitive profitability data. Visible to finance and exec only.
CREATE OR REPLACE FUNCTION authz_showcase.sales.mask_margin_pct(val DECIMAL(5,2))
  RETURNS DECIMAL(5,2)
  RETURN IF(
    is_member('authz_showcase_finance')    OR
    is_member('authz_showcase_executives') OR
    is_member('authz_showcase_admin'),
    val, NULL
  );

-- ── is_strategic (opportunities) ──────────────────────────────────────────────
-- Deal classification. Visible to managers and exec only.
CREATE OR REPLACE FUNCTION authz_showcase.sales.mask_is_strategic(val BOOLEAN)
  RETURNS BOOLEAN
  RETURN IF(
    is_member('authz_showcase_managers')   OR
    is_member('authz_showcase_executives') OR
    is_member('authz_showcase_admin'),
    val, NULL
  );

-- ── contract_value (customers) ────────────────────────────────────────────────
-- Commercial terms. Visible to managers, finance, and exec only.
CREATE OR REPLACE FUNCTION authz_showcase.sales.mask_contract_value(val DECIMAL(12,2))
  RETURNS DECIMAL(12,2)
  RETURN IF(
    is_member('authz_showcase_managers')   OR
    is_member('authz_showcase_finance')    OR
    is_member('authz_showcase_executives') OR
    is_member('authz_showcase_admin'),
    val, NULL
  );

-- ── cost_price (products) ─────────────────────────────────────────────────────
-- Internal cost data. Visible to finance and exec only.
CREATE OR REPLACE FUNCTION authz_showcase.sales.mask_cost_price(val DECIMAL(10,2))
  RETURNS DECIMAL(10,2)
  RETURN IF(
    is_member('authz_showcase_finance')    OR
    is_member('authz_showcase_executives') OR
    is_member('authz_showcase_admin'),
    val, NULL
  );

-- ── quota_viewers (allowlist table) ──────────────────────────────────────────
-- Manages which users/service principals can see sales_reps.quota AND get
-- elevated row access (all opps/customers) via Genie OBO.
--
-- Why this exists:
--   is_member() in row filters and column masks works for direct SQL and M2M,
--   but does NOT propagate through Genie OBO or Agent Bricks OBO — those systems
--   inject current_user() correctly but evaluate is_member() against their service
--   execution identity, not the calling user's workspace groups.
--   quota_viewers uses current_user() lookup which IS propagated at every access path.
--
-- Rows to seed (minimum):
--   - Real manager/finance/exec user emails
--   - App service principal: '5299e92e-4f66-4be4-a769-ccab1d24d763' (role: service_principal)
--
-- Demo persona switching: INSERT/DELETE real user email to simulate exec vs rep.
-- See app.py 🎭 Demo Controls sidebar for ready-to-use SQL snippets.
CREATE TABLE IF NOT EXISTS authz_showcase.sales.quota_viewers (
  user_email STRING NOT NULL COMMENT 'Databricks user email or SP application UUID',
  role        STRING NOT NULL COMMENT 'Role label: manager | finance | executive | admin | service_principal'
)
COMMENT 'Allowlist for quota visibility and elevated row access. Used by filter_opportunities, filter_customers, and mask_quota for Genie/Agent Bricks OBO compatibility.';

GRANT SELECT ON TABLE authz_showcase.sales.quota_viewers TO `account users`;

-- Seed: synthetic manager/finance personas + app SP
-- (App SP identity in SQL current_user() = its application UUID)
INSERT INTO authz_showcase.sales.quota_viewers (user_email, role)
SELECT t.user_email, t.role FROM (
  VALUES
    ('alice.chen@showcase.demo',               'manager'),
    ('bob.martinez@showcase.demo',             'manager'),
    ('eve.nguyen@showcase.demo',               'finance'),
    ('5299e92e-4f66-4be4-a769-ccab1d24d763',   'service_principal')
) AS t(user_email, role)
WHERE NOT EXISTS (
  SELECT 1 FROM authz_showcase.sales.quota_viewers q WHERE q.user_email = t.user_email
);


-- ── rep_regions (policy-free region lookup) ───────────────────────────────────
-- Denormalized email→region map with NO row filters or column masks.
-- Required because filter_customers needs to look up a rep's region, but
-- sales_reps now has mask_quota (a column mask). Databricks UC does not allow a
-- policy function to reference a table that itself has any policy — so we keep a
-- clean copy of just email+region here.
-- Sync this table whenever sales_reps email/region data changes.
CREATE TABLE IF NOT EXISTS authz_showcase.sales.rep_regions (
  email  STRING NOT NULL COMMENT 'Rep email — matches sales_reps.email',
  region STRING NOT NULL COMMENT 'WEST | EAST | CENTRAL'
)
COMMENT 'Policy-free email→region lookup. Used by filter_customers to avoid nested policy chain caused by sales_reps having mask_quota.';

GRANT SELECT ON TABLE authz_showcase.sales.rep_regions TO `account users`;

INSERT INTO authz_showcase.sales.rep_regions (email, region)
SELECT email, region FROM authz_showcase.sales.sales_reps
WHERE NOT EXISTS (
  SELECT 1 FROM authz_showcase.sales.rep_regions r WHERE r.email = authz_showcase.sales.sales_reps.email
);


-- ── quota (sales_reps) ────────────────────────────────────────────────────────
-- Per-rep sales quota. Privileged — visible to managers, finance, and exec only.
--
-- Uses is_member() — works for direct SQL and M2M (app SP in exec group).
-- NOTE: Via Genie OBO, is_member() evaluates the Genie service identity, not the
-- caller's groups → quota column returns NULL for all users via Genie. This is a
-- documented limitation. Row-level access (who sees which rows) is correctly
-- enforced via quota_viewers in filter_opportunities/filter_customers.
-- Cannot use quota_viewers here: a column mask with a table subquery causes a
-- nested policy chain violation when sales_reps is referenced in filter_customers.
CREATE OR REPLACE FUNCTION authz_showcase.sales.mask_quota(val DECIMAL(12,2))
  RETURNS DECIMAL(12,2)
  COMMENT 'Column mask for sales_reps.quota. Uses is_member() — works for direct SQL and M2M. Via Genie OBO the quota column returns NULL (is_member() evaluates Genie service identity); row-level access is correctly enforced via quota_viewers in row filters.'
  RETURN IF(
    is_member('authz_showcase_managers')   OR
    is_member('authz_showcase_finance')    OR
    is_member('authz_showcase_executives') OR
    is_member('authz_showcase_admin'),
    val, NULL
  );


-- ══════════════════════════════════════════════════════════════════════════════
-- APPLY TO TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- Row filter: opportunities
ALTER TABLE authz_showcase.sales.opportunities
  SET ROW FILTER authz_showcase.sales.filter_opportunities ON (rep_email);

-- Row filter: customers
ALTER TABLE authz_showcase.sales.customers
  SET ROW FILTER authz_showcase.sales.filter_customers ON (region);

-- Column mask: margin_pct
ALTER TABLE authz_showcase.sales.opportunities
  ALTER COLUMN margin_pct
  SET MASK authz_showcase.sales.mask_margin_pct;

-- Column mask: is_strategic
ALTER TABLE authz_showcase.sales.opportunities
  ALTER COLUMN is_strategic
  SET MASK authz_showcase.sales.mask_is_strategic;

-- Column mask: contract_value
ALTER TABLE authz_showcase.sales.customers
  ALTER COLUMN contract_value
  SET MASK authz_showcase.sales.mask_contract_value;

-- Column mask: cost_price
ALTER TABLE authz_showcase.sales.products
  ALTER COLUMN cost_price
  SET MASK authz_showcase.sales.mask_cost_price;

-- Column mask: quota (sales_reps)
ALTER TABLE authz_showcase.sales.sales_reps
  ALTER COLUMN quota
  SET MASK authz_showcase.sales.mask_quota;


-- ══════════════════════════════════════════════════════════════════════════════
-- VERIFY FUNCTIONS AND MASKS APPLIED
-- ══════════════════════════════════════════════════════════════════════════════
DESCRIBE EXTENDED authz_showcase.sales.opportunities;
DESCRIBE EXTENDED authz_showcase.sales.sales_reps;

-- Verify quota_viewers contents
SELECT * FROM authz_showcase.sales.quota_viewers ORDER BY role;

-- Test mask enforcement:
-- As West Rep (not in quota_viewers): SELECT email, quota FROM sales_reps → quota = NULL
-- As Executive (in quota_viewers):    SELECT email, quota FROM sales_reps → quota = value
-- To add yourself as exec for demo:
--   INSERT INTO authz_showcase.sales.quota_viewers VALUES ('you@databricks.com', 'executive');
-- To reset back to rep:
--   DELETE FROM authz_showcase.sales.quota_viewers WHERE user_email = 'you@databricks.com';
