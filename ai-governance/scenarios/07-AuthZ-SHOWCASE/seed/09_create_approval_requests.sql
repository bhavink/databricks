-- Phase 5 / Step 1 — Create approval_requests table for the custom MCP server demo.
--
-- Used by:
--   get_deal_approval_status  — reads latest approval status for an opportunity
--   submit_deal_for_approval  — inserts a new approval request stamped with caller identity
--
-- Auth teaching moment:
--   INSERT is done via the CALLING USER's OBO token (ModelServingUserCredentials).
--   The submitted_by column is populated programmatically from w.current_user.me()
--   — the app cannot spoof a different user's identity.
--   SELECT is open to all (no row filter) because:
--     a) get_deal_approval_status first verifies opp access via opportunities row filter
--     b) submit_deal_for_approval only inserts for opps the user can already see
--
-- Grants:
--   account users → SELECT (read approval status)
--   app MCP SP    → SELECT + MODIFY (read + insert)
--
-- Run after: 04_grant_permissions.sql
-- Run before: deploying the custom MCP server

CREATE TABLE IF NOT EXISTS authz_showcase.sales.approval_requests (
  request_id   STRING  GENERATED ALWAYS AS (uuid())  COMMENT 'Auto-generated UUID',
  opp_id       STRING  NOT NULL                       COMMENT 'FK → opportunities.opp_id',
  submitted_by STRING  NOT NULL                       COMMENT 'Email of the submitting user — set programmatically from OBO token',
  justification STRING                                COMMENT 'Business justification provided at submission time',
  status       STRING  NOT NULL DEFAULT 'PENDING'     COMMENT 'PENDING | APPROVED | REJECTED',
  approver     STRING                                 COMMENT 'Email of the manager who approved/rejected; NULL until actioned',
  created_at   TIMESTAMP NOT NULL                     COMMENT 'Submission timestamp (UTC)',
  updated_at   TIMESTAMP NOT NULL                     COMMENT 'Last status-change timestamp (UTC)'
)
COMMENT 'Deal approval requests submitted via the custom MCP server (Phase 5). Demonstrates OBO auditability — submitted_by always reflects the actual calling user identity.'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- Read access for all workspace users (query approval status)
GRANT SELECT ON TABLE authz_showcase.sales.approval_requests TO `account users`;

-- Full access for the custom MCP app SP
-- Replace with the actual SP application UUID shown in `databricks apps get authz-showcase-custom-mcp`
-- b05684ad-974c-4252-a9be-ec4982e000df  ← authz-showcase-custom-mcp SP (created 2026-03-06)
GRANT SELECT, MODIFY ON TABLE authz_showcase.sales.approval_requests TO `b05684ad-974c-4252-a9be-ec4982e000df`;

-- Seed a few example rows to make get_deal_approval_status immediately useful in demo
INSERT INTO authz_showcase.sales.approval_requests
  (opp_id, submitted_by, justification, status, approver, created_at, updated_at)
SELECT t.opp_id, t.submitted_by, t.justification, t.status, t.approver,
       current_timestamp(), current_timestamp()
FROM (
  VALUES
    ('OPP001', 'carol.white@showcase.demo',  'Strategic account — needs exec alignment before final close', 'APPROVED', 'alice.chen@showcase.demo'),
    ('OPP004', 'david.park@showcase.demo',   'Non-standard payment terms requested by customer',           'PENDING',  NULL),
    ('OPP007', 'emma.johnson@showcase.demo', 'Discount > 20% — requires finance sign-off',                'REJECTED', 'bob.martinez@showcase.demo')
) AS t(opp_id, submitted_by, justification, status, approver)
WHERE NOT EXISTS (
  SELECT 1 FROM authz_showcase.sales.approval_requests r WHERE r.opp_id = t.opp_id
);

-- Verify
SELECT * FROM authz_showcase.sales.approval_requests ORDER BY created_at;
