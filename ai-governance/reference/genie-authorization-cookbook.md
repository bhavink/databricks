# Genie Authorization Cookbook

> **Purpose**: Consolidated guide for securing Genie Space deployments with Unity Catalog -- from simple multi-team setups through enterprise-scale ABAC to multi-agent supervisor coordination. Replaces four separate scenario documents.
>
> **Audience**: Field Engineers deploying Genie Spaces with UC governance at any scale.
>
> **Last updated**: 2026-03-12
>
> **UC policy primer**: Before writing any row filter or column mask, read [UC Policy Design Principles](../UC-POLICY-DESIGN-PRINCIPLES.md) -- how `current_user()` and `is_member()` behave in Genie OBO contexts.

---

## Table of Contents

1. [Security Fundamentals](#1-security-fundamentals)
2. [Tier 1: Simple Multi-Team (3-5 teams, 50-150 users)](#2-tier-1-simple-multi-team)
3. [Tier 2: Enterprise Scale (1000+ users, ABAC)](#3-tier-2-enterprise-scale)
4. [Tier 3: Multi-Agent Supervisor](#4-tier-3-multi-agent-supervisor)
5. [Performance at Scale](#5-performance-at-scale)
6. [Monitoring and Audit](#6-monitoring-and-audit)
7. [Common Issues and Solutions](#7-common-issues-and-solutions)

---

## 1. Security Fundamentals

These principles apply to every tier.

### Genie Runs as the User (OBO)

When a user queries a Genie Space, the generated SQL executes as that user's identity. Unity Catalog enforces:

- **Row filters**: Functions that return TRUE/FALSE per row, evaluated per user
- **Column masks**: Functions that transform column values based on user identity
- **ABAC (governed tags)**: Attribute-based access control for tag-driven policies
- **Privilege grants**: USE CATALOG, USE SCHEMA, SELECT on tables

### `current_user()` vs `is_member()` in Genie

This is the most common source of confusion in Genie deployments:

| Function | Returns | Behavior in Genie OBO |
|---|---|---|
| `current_user()` | The human email of the Genie user | Correct -- use this for per-user filtering |
| `is_member('group')` | Whether the SQL execution identity is in the group | May not work as expected -- evaluates the execution context, not always the calling user |

**Best practice**: Use `current_user()` + an allowlist table for group-based access. This works reliably across all OBO contexts.

```sql
-- Reliable pattern: allowlist table instead of is_member()
CREATE TABLE my_catalog.security.role_assignments (
    user_email STRING,
    role STRING  -- 'sales', 'marketing', 'finance', 'executive'
);

-- Row filter using allowlist
CREATE FUNCTION my_catalog.schema.team_filter(owner_email STRING, team STRING)
RETURNS BOOLEAN
RETURN
    CASE
        -- User sees their own records
        WHEN owner_email = current_user() THEN TRUE
        -- Executives see all
        WHEN EXISTS (
            SELECT 1 FROM my_catalog.security.role_assignments
            WHERE user_email = current_user() AND role = 'executive'
        ) THEN TRUE
        -- Team members see team records
        WHEN EXISTS (
            SELECT 1 FROM my_catalog.security.role_assignments
            WHERE user_email = current_user() AND role = team
        ) THEN TRUE
        ELSE FALSE
    END;
```

### Genie Space Access Control Layers

```
Layer 1: Genie Space membership
  - Who can access the Genie Space at all (configured in UI)

Layer 2: UC catalog/schema/table grants
  - USE CATALOG, USE SCHEMA, SELECT on tables
  - Without SELECT, Genie cannot query the table

Layer 3: Row filters
  - Per-row access based on user identity
  - Applied transparently to all queries

Layer 4: Column masks
  - Per-column value transformation based on user identity
  - Applied transparently to all SELECT results
```

---

## 2. Tier 1: Simple Multi-Team

**Scenario**: 3-5 teams (Sales, Marketing, Finance) share a single Genie Space. Each team sees only their authorized data. Executives see everything. 50-150 users.

### Data Model

```sql
-- Single catalog with team-specific schemas
revenue_analytics
  +-- sales/
  |     +-- opportunities         (team-based row filter)
  |     +-- customer_interactions
  +-- marketing/
  |     +-- campaigns             (creator-based row filter)
  |     +-- lead_attribution
  +-- finance/
  |     +-- revenue               (column masks on amounts)
  |     +-- invoices
  +-- shared/
        +-- customers             (all teams)
        +-- products              (all teams)
```

### UC Configuration

**Step 1: Groups and grants**

Create groups: `sales-team`, `marketing-team`, `finance-team`, `executives`.

```sql
-- Catalog access
GRANT USE CATALOG ON CATALOG revenue_analytics TO `sales-team`;
GRANT USE CATALOG ON CATALOG revenue_analytics TO `marketing-team`;
GRANT USE CATALOG ON CATALOG revenue_analytics TO `finance-team`;
GRANT USE CATALOG ON CATALOG revenue_analytics TO `executives`;

-- Schema access (team-specific)
GRANT USE SCHEMA ON SCHEMA revenue_analytics.sales TO `sales-team`;
GRANT USE SCHEMA ON SCHEMA revenue_analytics.sales TO `executives`;
GRANT USE SCHEMA ON SCHEMA revenue_analytics.marketing TO `marketing-team`;
GRANT USE SCHEMA ON SCHEMA revenue_analytics.marketing TO `executives`;
GRANT USE SCHEMA ON SCHEMA revenue_analytics.finance TO `finance-team`;
GRANT USE SCHEMA ON SCHEMA revenue_analytics.finance TO `executives`;
GRANT USE SCHEMA ON SCHEMA revenue_analytics.shared TO `sales-team`;
GRANT USE SCHEMA ON SCHEMA revenue_analytics.shared TO `marketing-team`;
GRANT USE SCHEMA ON SCHEMA revenue_analytics.shared TO `finance-team`;
GRANT USE SCHEMA ON SCHEMA revenue_analytics.shared TO `executives`;

-- Table SELECT grants
GRANT SELECT ON TABLE revenue_analytics.sales.opportunities
  TO `sales-team`, `executives`, `marketing-team`, `finance-team`;
GRANT SELECT ON TABLE revenue_analytics.marketing.campaigns
  TO `marketing-team`, `executives`;
GRANT SELECT ON TABLE revenue_analytics.finance.revenue
  TO `finance-team`, `executives`;
```

**Step 2: Row filters**

```sql
-- Opportunities: team-based access
CREATE FUNCTION revenue_analytics.sales.filter_opportunities(
    owner STRING, team STRING
)
RETURNS BOOLEAN
RETURN
    CASE
        WHEN is_member('sales-team') AND (owner = current_user() OR team = 'sales') THEN TRUE
        WHEN is_member('marketing-team') AND team = 'marketing' THEN TRUE
        WHEN is_member('finance-team') AND team = 'finance' THEN TRUE
        WHEN is_member('executives') THEN TRUE
        ELSE FALSE
    END;

ALTER TABLE revenue_analytics.sales.opportunities
  SET ROW FILTER revenue_analytics.sales.filter_opportunities
  ON (owner_email, team);

-- Campaigns: creator-based access
CREATE FUNCTION revenue_analytics.marketing.filter_campaigns(creator STRING)
RETURNS BOOLEAN
RETURN
    CASE
        WHEN is_member('marketing-team') AND creator = current_user() THEN TRUE
        WHEN is_member('executives') THEN TRUE
        ELSE FALSE
    END;

ALTER TABLE revenue_analytics.marketing.campaigns
  SET ROW FILTER revenue_analytics.marketing.filter_campaigns
  ON (created_by);
```

**Step 3: Column masks**

```sql
-- Revenue amounts: precision masking by role
CREATE FUNCTION revenue_analytics.finance.mask_revenue_amount()
RETURNS DECIMAL(15,2)
RETURN
    CASE
        WHEN is_member('finance-team') OR is_member('executives') THEN VALUE
        WHEN is_member('sales-team') OR is_member('marketing-team') THEN ROUND(VALUE, -3)
        ELSE NULL
    END;

ALTER TABLE revenue_analytics.finance.revenue
  ALTER COLUMN amount SET MASK revenue_analytics.finance.mask_revenue_amount;
ALTER TABLE revenue_analytics.finance.revenue
  ALTER COLUMN recognized_amount SET MASK revenue_analytics.finance.mask_revenue_amount;
```

### Genie Space Configuration

```
Name: "Revenue Analytics"
Description: "Natural language queries for sales, marketing, and finance data"
Catalog: revenue_analytics
SQL Warehouse: <serverless-warehouse>

Instructions:
  You are a revenue analytics assistant for a B2B company.
  Sales team: sees all sales opportunities
  Marketing team: sees campaigns and attributed opportunities
  Finance team: sees revenue and closed deals
  Executives: see all data

  Common terms:
  - "Pipeline" = sum of opportunity amounts in stages before 'closed_won'
  - "Closed deals" = opportunities with stage = 'closed_won'
  - "Conversion rate" = (closed_won / total) * 100
```

### Test Matrix

| User | Query | Expected result |
|---|---|---|
| alice@co.com (sales) | "My opportunities" | Only Alice's opportunities |
| bob@co.com (marketing) | "Campaign performance" | Only Bob's campaigns |
| carol@co.com (finance) | "Revenue for Q4" | Full revenue (exact amounts) |
| alice@co.com (sales) | "Total revenue Q4" | Rounded amounts (column mask) |
| david@co.com (executive) | "All opportunities" | All opportunities, all teams |

---

## 3. Tier 2: Enterprise Scale

**Scenario**: 5000+ employees across 50 countries and 20 departments query HR data. Hierarchical access: Employee -> Manager -> Director -> Executive -> HR Admin. Multi-dimensional security (department, region, role, sensitivity).

### Data Model

```sql
hr_analytics
  +-- employees/
  |     +-- core_data         (ABAC: role + dept + region + sensitivity)
  |     +-- compensation      (PII masked, HR-only raw access)
  |     +-- performance       (hierarchical: manager sees reports)
  |     +-- attendance        (personal data)
  +-- organization/
  |     +-- departments
  |     +-- locations
  |     +-- cost_centers
  +-- analytics/
  |     +-- headcount_mv      (materialized view, fast queries)
  |     +-- attrition_mv      (pre-aggregated metrics)
  |     +-- diversity_mv      (aggregated only)
  +-- audit/
        +-- access_log
        +-- query_log
```

**Key table design**: Partition by `country` and `department` for performance. Include `data_sensitivity` column (`public`, `internal`, `confidential`) for ABAC filtering.

### ABAC Row Filter

```sql
CREATE FUNCTION hr_analytics.employees.can_access_employee(
    record_email STRING,
    record_manager STRING,
    record_department STRING,
    record_region STRING,
    record_sensitivity STRING,
    record_level INT
)
RETURNS BOOLEAN
RETURN
    CASE
        -- HR Admins see everything
        WHEN is_member('hr-admins') THEN TRUE
        -- Executives see all except individual PII
        WHEN is_member('executives') AND record_sensitivity != 'confidential' THEN TRUE
        -- Directors see department aggregates
        WHEN is_member('directors')
             AND is_member(CONCAT(record_department, '-directors'))
             AND record_sensitivity IN ('public', 'internal') THEN TRUE
        -- Managers see direct reports
        WHEN is_member('managers') AND record_manager = current_user() THEN TRUE
        -- Managers see team aggregates in their department
        WHEN is_member('managers')
             AND is_member(CONCAT(record_department, '-managers'))
             AND record_sensitivity = 'public' THEN TRUE
        -- Employees see only their own record
        WHEN record_email = current_user() THEN TRUE
        -- EMEA data residency
        WHEN record_region = 'EMEA' AND NOT is_member('emea-authorized') THEN FALSE
        -- C-level data protection
        WHEN record_level >= 9 AND NOT is_member('executives') THEN FALSE
        ELSE FALSE
    END;

ALTER TABLE hr_analytics.employees.core_data
  SET ROW FILTER hr_analytics.employees.can_access_employee
  ON (email, manager_email, department, region, data_sensitivity, job_level);
```

### PII Column Masks

```sql
-- Progressive salary disclosure
CREATE FUNCTION hr_analytics.employees.mask_salary()
RETURNS DECIMAL(15,2)
RETURN
    CASE
        WHEN is_member('hr-admins') THEN VALUE
        WHEN is_member('executives') THEN ROUND(VALUE, -4)
        WHEN is_member('directors') THEN NULL  -- force to aggregate views
        WHEN is_member('employees') THEN VALUE  -- own salary (row filter limits to own record)
        ELSE NULL
    END;

ALTER TABLE hr_analytics.employees.compensation
  ALTER COLUMN base_salary SET MASK hr_analytics.employees.mask_salary;
ALTER TABLE hr_analytics.employees.compensation
  ALTER COLUMN total_compensation SET MASK hr_analytics.employees.mask_salary;
```

### Materialized Views for Performance

At 1000+ users, direct queries against base tables with complex row filters become slow. Pre-aggregate common queries:

```sql
-- Headcount by department/region (safe for directors/executives)
CREATE MATERIALIZED VIEW hr_analytics.analytics.headcount_mv AS
SELECT
    department, region, country, job_level, employment_status,
    COUNT(DISTINCT employee_id) as employee_count,
    COUNT(DISTINCT CASE WHEN employment_status = 'active' THEN employee_id END) as active_count,
    current_date() as snapshot_date
FROM hr_analytics.employees.core_data
WHERE employment_status = 'active'
GROUP BY department, region, country, job_level, employment_status;

-- Attrition rates
CREATE MATERIALIZED VIEW hr_analytics.analytics.attrition_mv AS
-- (monthly hires vs terminations by department and region)
...
```

Grant these materialized views to all roles. They contain only aggregated data -- no individual PII.

### Genie Instructions for Scale

```
You are the Global HR Analytics assistant serving 5000+ employees worldwide.

Data access rules:
- Employees: see only their own records
- Managers: see their direct reports' data
- Directors: see aggregated department metrics (no individual PII)
- Executives: see org-wide metrics and trends
- HR Admins: full access to all data

Query optimization:
- For headcount/attrition queries, use hr_analytics.analytics.* materialized views
- Always filter by department or region when possible
- Aggregate to at least 5 employees for directors/executives (k-anonymity)

Privacy:
- Never expose individual salaries except to HR admins and the employee themselves
- Never show performance comments to executives or directors
```

### Performance Targets

| User role | Query type | Target latency |
|---|---|---|
| Employee | Self-query ("My salary") | < 500ms |
| Manager | Team query ("Team performance") | < 2s |
| Director | Department aggregate | < 3s (via materialized view) |
| Executive | Org-wide metric | < 5s (via materialized view) |

---

## 4. Tier 3: Multi-Agent Supervisor

**Scenario**: A supervisor agent routes queries to specialized Genie Spaces based on intent. Example: Financial advisory platform with Portfolio Genie, Market Data Genie, and Compliance Genie.

### Architecture

```
Users (Clients, Advisors, Compliance Officers)
    |
    v
[Supervisor Agent]        <-- Intent classification (M2M, no user data)
    |
    +-- Portfolio Genie   <-- OBO: client sees own portfolio, advisor sees assigned clients
    |
    +-- Market Data Genie <-- OBO: public data for all, premium for advisors
    |
    +-- Compliance Genie  <-- OBO: compliance officers only
```

### Auth Strategy

The supervisor uses hybrid auth:
- **Intent classification**: M2M (no user data needed, uses app SP)
- **Genie routing**: Forwards user token (OBO) so UC enforces per-user access
- **Compliance logging**: M2M (SP writes to audit table)

### Catalog Separation

Use separate catalogs per domain for clear governance boundaries:

```sql
portfolio_catalog    -- Client portfolios, transactions, performance
market_catalog       -- Real-time quotes, news, benchmarks
compliance_catalog   -- Audit logs, trading alerts, compliance flags
```

### Per-Domain Row Filters

```sql
-- Portfolio: hierarchical client -> advisor -> compliance
CREATE FUNCTION portfolio_catalog.holdings.can_access_portfolio(
    record_client_email STRING, record_advisor_email STRING
)
RETURNS BOOLEAN
RETURN
    CASE
        WHEN is_member('compliance-officers') THEN TRUE
        WHEN is_member('advisors') AND record_advisor_email = current_user() THEN TRUE
        WHEN is_member('clients') AND record_client_email = current_user() THEN TRUE
        ELSE FALSE
    END;

-- Market data: tiered access
CREATE FUNCTION market_catalog.realtime.can_access_market_data(data_tier STRING)
RETURNS BOOLEAN
RETURN
    CASE
        WHEN data_tier = 'premium' AND
             (is_member('advisors') OR is_member('compliance-officers')) THEN TRUE
        WHEN data_tier = 'public' THEN TRUE
        ELSE FALSE
    END;

-- Compliance: restricted
CREATE FUNCTION compliance_catalog.audit.compliance_only()
RETURNS BOOLEAN
RETURN is_member('compliance-officers');
```

### Supervisor Routing Logic

```python
class FinancialAdvisorSupervisor:
    def predict(self, inputs, context):
        query = inputs.get("query")
        user_token = context.user_token

        # Step 1: Classify intent (M2M -- no user data)
        intent = self._classify_intent(query)

        # Step 2: Route to Genie with user token (OBO)
        w = WorkspaceClient(token=user_token)
        response = w.genie.query(
            space_id=self.genies[intent]["space_id"],
            query=query
        )

        # Step 3: Log for compliance (M2M -- SP writes to audit)
        self._log_interaction(context.user_email, query, intent)

        return response
```

### Test Matrix

| User | Query | Routing | Expected access |
|---|---|---|---|
| Client | "My portfolio balance" | Portfolio Genie | Own portfolio only |
| Advisor | "Show John's allocation" | Portfolio Genie | Assigned client data |
| Advisor | "Latest Fed rate?" | Market Data Genie | Premium market data |
| Client | "Apple stock price?" | Market Data Genie | Public data only |
| Compliance | "Audit client X trades" | Compliance Genie | All trade history |
| Client | "Show all client trades" | Compliance Genie | Access denied |

---

## 5. Performance at Scale

### Table Partitioning

Partition by the most common filter dimensions:

```sql
-- Partition by the dimensions your row filters check most often
CREATE TABLE ... PARTITIONED BY (country, department);

-- Z-ORDER by the columns used in filter function parameters
OPTIMIZE my_table ZORDER BY (email, manager_email);
```

### Materialized Views

Pre-aggregate for any query pattern that directors, executives, or large user groups commonly run:

- Headcount by department/region
- Attrition rates by period
- Revenue aggregates by quarter
- Performance rating distributions

### Result Caching

Enable result caching at the warehouse level. Monitor cache hit rates:

```sql
SELECT cache_hit, COUNT(*) as query_count
FROM system.query.history
WHERE warehouse_id = '<id>' AND query_start_time >= current_date() - 7
GROUP BY cache_hit;
```

### Row Filter Performance

Keep row filter functions simple:
- Avoid subqueries in row filter functions (use allowlist tables with EXISTS instead of IN)
- Avoid complex string operations
- Avoid calling other UDFs from within a row filter

---

## 6. Monitoring and Audit

### Usage Monitoring

```sql
-- Daily active users by team
SELECT
    DATE(event_time) as date,
    user_identity.email,
    COUNT(*) as query_count
FROM system.access.audit
WHERE action_name = 'commandSubmit'
  AND request_params.full_name_arg LIKE 'my_catalog%'
  AND datediff(now(), event_time) <= 30
GROUP BY DATE(event_time), user_identity.email
ORDER BY date DESC, query_count DESC;
```

### Security Monitoring

```sql
-- Permission denied spike detection
SELECT
    user_identity.email,
    request_params.full_name_arg as table_name,
    COUNT(*) as failure_count
FROM system.access.audit
WHERE response.status_code = 403
  AND datediff(now(), event_time) <= 1
GROUP BY user_identity.email, table_name
HAVING failure_count > 10
ORDER BY failure_count DESC;
```

### Cost Tracking

```sql
-- Compute hours by department (proxy via email domain)
SELECT
    DATE(event_time) as date,
    COUNT(*) as query_count,
    SUM(response.result.duration_ms) / 1000.0 / 3600.0 as compute_hours
FROM system.access.audit
WHERE action_name = 'commandSubmit'
  AND datediff(now(), event_time) <= 30
GROUP BY DATE(event_time)
ORDER BY date DESC;
```

For comprehensive Genie monitoring, see [audit-logging/genie-aibi/](../audit-logging/genie-aibi/).

---

## 7. Common Issues and Solutions

### User Can't See Expected Data

**Diagnosis**:
1. Check group membership: Is the user in the correct group?
2. Check row filter: `SHOW CREATE FUNCTION schema.filter_name;`
3. Check grants: Does the user have SELECT on the table?
4. Check `current_user()` vs `is_member()` behavior in the filter

### User Sees Data They Shouldn't

**Diagnosis**:
1. Verify row filter is applied: `DESCRIBE TABLE EXTENDED schema.table;`
2. Test filter function with specific user: `SELECT schema.filter_fn('user@co.com', 'team');`
3. Check for gaps in CASE logic (missing ELSE FALSE)

### Performance Degradation

**Diagnosis**:
1. Check partitioning: `DESCRIBE DETAIL schema.table;`
2. Check Z-ORDER: Run `OPTIMIZE` if stale
3. Check if materialized views exist for common query patterns
4. Simplify row filter functions (avoid subqueries, complex logic)

### `is_member()` Returns Wrong Result

This is the most common issue in Genie deployments. `is_member()` may evaluate the SQL execution identity rather than the calling user in some OBO contexts.

**Fix**: Replace `is_member('group')` with an allowlist table lookup using `current_user()`.

### Genie Generates Wrong Queries

**Fix**: Improve Genie instructions with:
- Explicit column names and table references
- Common business term definitions
- Query pattern examples for each role
- Instructions to prefer materialized views for aggregate queries

---

## Related Documents

- [UC Policy Design Principles](../UC-POLICY-DESIGN-PRINCIPLES.md) -- `current_user()` vs `is_member()` across all execution contexts
- [Identity and Auth Reference](identity-and-auth-reference.md) -- Auth patterns, token flows, scope reference
- [Authorization Flows](authorization-flows.md) -- UC four-layer access control diagrams
- [audit-logging/genie-aibi/](../audit-logging/genie-aibi/) -- Genie monitoring and analytics suite
- Databricks docs: [Genie Space](https://docs.databricks.com/aws/en/genie/), [Row Filters](https://docs.databricks.com/en/data-governance/unity-catalog/row-and-column-filters.html), [ABAC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac)
