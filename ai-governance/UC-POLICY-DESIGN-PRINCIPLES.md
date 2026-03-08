# UC Policy Design Principles

> **Read this before writing any row filter, column mask, or UC function.**
>
> These principles apply to every scenario in this repo — regardless of product (Genie, Agent Bricks, Databricks Apps, Vector Search, UC Functions), scale (10 users or 10,000), or cloud (AWS, Azure, GCP). The patterns are derived from building and verifying the [AI Auth Showcase](scenarios/07-AuthZ-SHOWCASE/) end-to-end on Azure Databricks.

---

## The Foundational Question

Before writing any UC policy, answer one question:

> **What identity is executing the SQL when this policy runs?**

The answer determines which policy primitive to use. Everything else follows from this.

---

## The Two Policy Primitives

### `current_user()`

Returns the email of the identity on the **active SQL token** — whoever is driving the query at that moment.

| Context | What `current_user()` returns |
|---|---|
| Human runs SQL directly in a notebook or SQL editor | Their email |
| Genie OBO query on behalf of a user | The user's email ✅ |
| Agent Bricks supervisor routing to a sub-agent OBO | The user's email ✅ |
| App SP calling a UC function via M2M | The SP's OAuth client ID |
| Custom MCP server called via Databricks Apps proxy | The MCP app's SP client ID (the proxy substitutes its token) |

`current_user()` is the most portable anchor — it reflects whoever's identity the SQL runtime has at that moment, regardless of the service layer.

### `is_member('group')`

Evaluates group membership of the **SQL execution context's identity** — not necessarily the calling user.

| Context | What `is_member()` evaluates |
|---|---|
| Human runs SQL directly | Their own workspace group membership ✅ |
| Genie OBO — SQL runs inside Genie's execution layer | The execution context's group membership (may be the service layer, not the OBO caller's groups) ⚠️ |
| Agent Bricks OBO through supervisor | Same as Genie — execution identity depends on the service layer ⚠️ |
| App SP via M2M | The SP's workspace group membership ✅ (if SP is in the right groups) |

`is_member()` is purpose-built and works exactly as designed — the question is simply whether the execution identity matches your intent.

---

## Choosing the Right Primitive

| Design goal | Use | Why |
|---|---|---|
| User sees only their own rows | `column = current_user()` | Email propagates through all OBO chains |
| User sees rows for their team | `current_user()` + allowlist table | Group membership may not propagate through Genie/Agent Bricks service layers |
| Column is visible only to specific roles | `current_user()` + allowlist table (for OBO) or `is_member()` (for M2M) | Depends on execution context |
| SP (M2M) enforces role-based access | `is_member('group')` | SP group membership is stable and controlled by design |
| Time-based or attribute-based filter | Column comparison — no identity function needed | Neither primitive applies |
| Audit/logging with known SP identity | `is_member()` | M2M context — SP is the executor |

**The short version**: `current_user()` travels with the OBO token end-to-end. `is_member()` reflects the SQL executor's groups — ideal when you control who's executing (M2M SP), requires an allowlist table when you need it to reflect an OBO user's role.

---

## The Allowlist Table Pattern

When you need role-based access in an OBO context (Genie, Agent Bricks), replace `is_member()` with a `current_user()` lookup against a UC-governed table:

```sql
-- Instead of: is_member('quota-viewers')
-- Use: a lookup table that UC governs like any other object

CREATE TABLE governance.access.quota_viewers (
  user_email STRING NOT NULL,
  granted_by STRING,
  granted_at TIMESTAMP
);

-- Row filter using the allowlist pattern
CREATE OR REPLACE FUNCTION governance.masks.can_view_quota(val DECIMAL(12,2))
RETURNS DECIMAL(12,2)
RETURN CASE
  WHEN EXISTS (
    SELECT 1 FROM governance.access.quota_viewers
    WHERE user_email = current_user()
  ) THEN val
  ELSE NULL
END;
```

**Why this works across all contexts**: `current_user()` resolves to the OBO caller's email in Genie/Agent Bricks. The allowlist table is just a UC-governed Delta table — you manage access to it like any other object. Adding or removing a user from the table takes effect immediately on the next query, same as revoking group membership.

---

## M2M Contexts: `is_member()` Works as Designed

When an app SP executes SQL via M2M, `is_member()` evaluates the SP's workspace group membership — which you control explicitly:

```sql
-- UC function called by app SP via M2M (Tab 3 pattern)
-- SP is in authz_showcase_executives group by explicit design
CREATE FUNCTION functions.get_rep_quota(rep_email STRING)
RETURNS DECIMAL(12,2)
RETURN CASE
  WHEN is_member('executives') OR is_member('managers') OR is_member('finance')
    THEN (SELECT quota FROM quotas WHERE email = rep_email)
  ELSE NULL
END;
```

This is exactly the right use of `is_member()`. The SP's group membership is:
- Explicitly granted (you added the SP to the group)
- Stable (doesn't change per-request)
- Auditable (group membership is logged in UC system tables)

The function returns the right value because *you designed the SP's identity to have the right access* — not because of user identity.

---

## Combining Both Primitives

Row filters often need both — user-scoped access for individual contributors plus role-based bypass for managers and executives. The pattern that works across all execution contexts:

```sql
CREATE OR REPLACE FUNCTION sales.filter_opportunities(rep_email STRING)
RETURNS BOOLEAN
RETURN (
  -- Role bypass: works in M2M contexts where SP has the right group membership
  -- In OBO contexts through Genie/Agent Bricks, this evaluates the execution context's groups
  is_member('executives') OR
  is_member('managers') OR

  -- Individual access: works everywhere — current_user() always reflects the OBO caller
  rep_email = current_user()
);
```

**In an M2M context (app SP)**: The SP is in `executives` → `is_member('executives')` returns TRUE → all rows visible. The `current_user()` branch returns the SP's client ID and matches nothing (no rep rows belong to the SP) — but the `is_member()` branch already passed.

**In an OBO context (Genie, user is a rep)**: `is_member()` evaluates the execution context. `current_user()` = the user's email → their own rows visible. The rep-scoped access story works correctly even if the `is_member()` bypass doesn't propagate.

**Design implication**: In OBO contexts, the individual-access path (`current_user()`) is the reliable enforcement mechanism. The `is_member()` bypass is a performance optimization and ergonomic convenience when the execution context identity has the right groups — not the primary enforcement mechanism for per-user access.

---

## Execution Context Reference

| Product / pattern | Who executes the SQL | `current_user()` | `is_member()` |
|---|---|---|---|
| Direct SQL (human, notebook, SQL editor) | The human user | User email | User's workspace groups |
| Genie Space (OBO) | Genie service layer with user's token context | User email ✅ | Execution context groups ⚠️ |
| Agent Bricks supervisor → sub-agent (OBO) | Service layer, token forwarded | User email ✅ | Execution context groups ⚠️ |
| Databricks App SP (M2M) | App SP | SP client ID | SP's workspace groups ✅ |
| UC Function called via M2M | App SP (INVOKER security) | SP client ID | SP's workspace groups ✅ |
| Custom MCP app (Databricks Apps proxy) | MCP app SP | MCP SP client ID | MCP SP's workspace groups |
| External MCP via UC HTTP connection | Stored credential in UC connection | Connection credential identity | That credential's groups |

⚠️ = "the execution context identity may not be what you expect — verify your use case against the execution model"

---

## Operational Notes

**Group membership propagation delay**: After adding or removing a user from a workspace group, `is_member()` reflects the change within ~2 minutes. Plan for this in demos and tests — start a new SQL session to get a fresh evaluation.

**SP group membership**: Use the workspace-level group (not account-level). `is_member()` checks workspace groups. Account-level groups are a different concept.

**UC function security model**: Functions can be `DEFINER` (run as owner) or `INVOKER` (run as caller). For M2M scenarios in this repo, functions use INVOKER security — the SP's identity drives `is_member()` and `current_user()` inside the function body.

**Allowlist table access control**: The allowlist table itself needs proper UC grants. Grant `SELECT` to the executing identity (app SP for M2M, or appropriate OBO identity). The table owner manages row-level membership — treating it like any other governed object.

---

## Applied to This Repo's Scenarios

| Scenario | Primary execution context | `is_member()` appropriate? | `current_user()` appropriate? |
|---|---|---|---|
| [01 — Knowledge Assistant](scenarios/01-KNOWLEDGE-ASSISTANT/) | Vector Search OBO | For team-based bypass where SP has group membership; individual access via `current_user()` | ✅ For author/owner scoping |
| [04 — Multi-Agent Supervisor](scenarios/04-MULTI-AGENT-SUPERVISOR/) | Mixed: SP for intent classification, OBO for Genie routing | ✅ For SP-based audit/logging; use allowlist for OBO user-role checks | ✅ For per-user data scoping in Genie sub-agents |
| [05 — Genie Space (multi-team)](scenarios/05-GENIE-SPACE/standalone-multi-team.md) | Genie OBO | For team bypass if execution context carries group membership; individual via `current_user()` | ✅ For owner/creator scoping |
| [05 — Genie Space (scale)](scenarios/05-GENIE-SPACE/standalone-scale.md) | Genie OBO | For complex ABAC; validate empirically that execution context reflects intended groups | ✅ For manager→report, employee→self |
| [07 — AuthZ Showcase](scenarios/07-AuthZ-SHOWCASE/) | Mixed per tab | ✅ Tab 3 M2M; use allowlist pattern for OBO column masks | ✅ All row filters anchored here |

---

## Further Reading

- [Authentication Patterns](01-AUTHENTICATION-PATTERNS.md) — OBO vs M2M decision
- [Authorization with UC](02-AUTHORIZATION-WITH-UC.md) — four-layer access control model
- [AuthZ Showcase — Auth Patterns](scenarios/07-AuthZ-SHOWCASE/AUTHZ-PATTERNS.md) — verified patterns from end-to-end build
- [Fieldkit: OBO Passthrough](../../0-dayjob/databricks-fieldkit/auth/obo-passthrough.md) — two-proxy problem, X-Forwarded-Email, allowlist pattern
- [Fieldkit: M2M Service Principal](../../0-dayjob/databricks-fieldkit/auth/m2m-service-principal.md) — SP group membership, INVOKER vs DEFINER
