# Authorization with Unity Catalog

> **Technical reference for Unity Catalog governance across Databricks AI products**

---

## ⚠️ Important Disclaimers

### Multi-Cloud Documentation

This guide primarily links to **AWS Databricks documentation** for consistency. However, all Unity Catalog concepts apply universally across **AWS, Azure, and GCP**.

**To access cloud-specific documentation:**
- Use the **cloud selector dropdown** at the top of any Databricks doc page
- Navigate: AWS docs → Switch to Azure or GCP
- Cloud-specific differences are noted where applicable

**Quick Links:**
- [AWS Documentation](https://docs.databricks.com/aws/en/)
- [Azure Documentation](https://learn.microsoft.com/en-us/azure/databricks/)
- [GCP Documentation](https://docs.databricks.com/gcp/en/)

### Guidance vs Official Documentation

- This guide represents **practical guidance and best practices**, not official Databricks positions
- Always consult [official Databricks documentation](https://docs.databricks.com) for authoritative information
- Databricks features evolve rapidly - **verify current capabilities** and syntax in official docs
- **Use your best judgment** when applying these patterns to your specific requirements
- Features, APIs, and best practices may have changed since publication
- **Check official documentation** for the latest updates

---

## 🎯 Overview: Unity Catalog's Role in Authorization

**Unity Catalog (UC)** is Databricks' unified governance layer that enforces authorization policies for all data access, regardless of which AI product or compute resource accesses the data.

> 📺 **[View interactive access control flow →](interactive/uc-access-control-layers.html)**

### Key Principles

1. **Separation of Concerns:**
   - **Authentication** (covered in [01-AUTHENTICATION-PATTERNS.md](01-AUTHENTICATION-PATTERNS.md)) → "Who are you?"
   - **Authorization** (this document) → "What can you access?"

2. **Single Source of Truth:**
   - UC policies are defined **once** and enforced **everywhere**
   - Works across Genie Space, Agent Bricks, Databricks Apps, SQL Warehouses, Notebooks

3. **Pattern Integration:**
   - **Pattern 1 (Automatic Auth):** UC evaluates service principal permissions
   - **Pattern 2 (User Auth):** UC evaluates user permissions + row filters + column masks
   - **Pattern 3 (Manual Credentials):** UC not involved (external services)

### Four Layers of Access Control

Access control in Unity Catalog is built on **four complementary layers** that work together to enforce secure, fine-grained access:

| Layer | Question Answered | Mechanisms |
|-------|-------------------|------------|
| **1. Workspace Restrictions** | WHERE can users access data? | Workspace bindings on catalogs, external locations, storage credentials |
| **2. Privileges & Ownership** | WHO can access WHAT? | GRANTs (SELECT, MODIFY, etc.), object ownership, admin roles |
| **3. ABAC Policies** | WHAT data based on tags? | Governed tags + policies with UDFs for dynamic enforcement |
| **4. Table-Level Filtering** | WHAT rows/columns visible? | Row filters, column masks, dynamic views |

### How the Four Layers Work Together

```mermaid
flowchart TB
    subgraph Auth["Authentication (Pattern 1 or 2)"]
        User["User<br/>(Pattern 2)"]
        SP["Service Principal<br/>(Pattern 1)"]
    end
    
    subgraph Products["Databricks AI Products"]
        Genie[Genie Space]
        Agent[Agent Bricks]
        App[Databricks Apps]
    end
    
    subgraph UC["Unity Catalog: Four Authorization Layers"]
        Layer1["Layer 1: Workspace Restrictions<br/>WHERE can they access?"]
        Layer2["Layer 2: Privileges & Ownership<br/>WHO can access WHAT?"]
        Layer3["Layer 3: ABAC Policies<br/>WHAT data based on tags?"]
        Layer4["Layer 4: Table-Level Filtering<br/>WHAT rows/columns?"]
    end
    
    subgraph Data["Data Resources"]
        Tables[(Tables/Views)]
    end
    
    User -->|Authenticated request| Products
    SP -->|Authenticated request| Products
    
    Products -->|Query data| Layer1
    
    Layer1 -->|Workspace OK| Layer2
    Layer2 -->|Has GRANTs| Layer3
    Layer3 -->|Tags match policy| Layer4
    Layer4 -->|Filter & mask| Tables
    
    Tables -->|Return governed data| Products
    
    style UC fill:#e8f8f5,stroke:#1abc9c,stroke-width:3px
    style Layer1 fill:#cffafe,stroke:#06b6d4,stroke-width:2px
    style Layer2 fill:#d5f5e3,stroke:#27ae60,stroke-width:2px
    style Layer3 fill:#f3e8ff,stroke:#a855f7,stroke-width:2px
    style Layer4 fill:#ffedd5,stroke:#f97316,stroke-width:2px
```

**Official Documentation:** 
- [Access Control in Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control)
- [Unity Catalog Overview](https://docs.databricks.com/aws/en/data-governance/unity-catalog/index.html)

---

## 🏛️ Unity Catalog Hierarchy

Unity Catalog enforces authorization at multiple levels in a hierarchical structure:

```mermaid
flowchart TD
    Metastore[Metastore<br/>Account-wide data catalog<br/><br/>Highest level]
    
    Catalog1[Catalog: finance_prod<br/>Domain or tenant<br/><br/>Contains schemas]
    Catalog2[Catalog: marketing_prod<br/>Domain or tenant]
    
    Schema1[Schema: accounting<br/>Functional area<br/><br/>Contains tables]
    Schema2[Schema: campaigns<br/>Functional area]
    
    Table1[Table: transactions<br/>Data object<br/><br/>Contains columns/rows]
    Table2[Table: email_campaigns<br/>Data object]
    
    Column1[Column: amount<br/>Table attribute]
    Row1[Row: Individual record<br/>Data row]
    
    Metastore --> Catalog1
    Metastore --> Catalog2
    
    Catalog1 --> Schema1
    Catalog2 --> Schema2
    
    Schema1 --> Table1
    Schema2 --> Table2
    
    Table1 --> Column1
    Table1 --> Row1
    
    style Metastore fill:#e8f8f5,stroke:#1abc9c,stroke-width:2px
    style Catalog1 fill:#d5f5e3,stroke:#27ae60,stroke-width:2px
    style Catalog2 fill:#d5f5e3,stroke:#27ae60,stroke-width:2px
    style Schema1 fill:#fef5e7,stroke:#f39c12,stroke-width:2px
    style Schema2 fill:#fef5e7,stroke:#f39c12,stroke-width:2px
    style Table1 fill:#fdebd0,stroke:#e67e22,stroke-width:2px
    style Table2 fill:#fdebd0,stroke:#e67e22,stroke-width:2px
    style Column1 fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    style Row1 fill:#ebf5fb,stroke:#3498db,stroke-width:2px
```

### Hierarchy Levels

| Level | Description | Permissions Granted | Example |
|-------|-------------|---------------------|---------|
| **Metastore** | Account-wide catalog | Metastore admin | One per account |
| **Catalog** | Top-level container | USE CATALOG, CREATE SCHEMA | `finance_prod`, `marketing_prod` |
| **Schema** | Logical grouping | USE SCHEMA, CREATE TABLE | `finance_prod.accounting` |
| **Table** | Data object | SELECT, INSERT, UPDATE, DELETE | `finance_prod.accounting.transactions` |
| **Column** | Table attribute | Column masks | `transactions.amount` |
| **Row** | Individual record | Row filters | Individual transaction records |

### Permission Inheritance

```mermaid
flowchart TD
    Top[Permission granted at higher level]
    Cascade[Cascades down to child objects]
    Override[More specific permissions override general ones]
    
    Top --> Cascade
    Cascade --> Override
    
    Example1["Example:<br/>GRANT USE CATALOG ON finance_prod<br/>↓<br/>Can access all schemas within"]
    
    Example2["But if:<br/>DENY SELECT ON specific_table<br/>↓<br/>Cannot read that specific table"]
    
    Override --> Example1
    Override --> Example2
    
    style Top fill:#d5f5e3,stroke:#27ae60,stroke-width:2px
    style Cascade fill:#fef5e7,stroke:#f39c12,stroke-width:2px
    style Override fill:#fce4ec,stroke:#c2185b,stroke-width:2px
```

**Documentation:** [Unity Catalog Object Model](https://docs.databricks.com/aws/en/data-governance/unity-catalog/best-practices.html)

---

## 🔐 Permission Model: GRANTs

Unity Catalog uses SQL GRANT statements to control access to objects.

### Permission Types

| Permission | Level | Description | Required For |
|------------|-------|-------------|--------------|
| `USE CATALOG` | Catalog | Access catalog and list schemas | Prerequisite for schema access |
| `USE SCHEMA` | Schema | Access schema and list tables | Prerequisite for table access |
| `SELECT` | Table | Read data | Queries, Genie Space, read-only agents |
| `INSERT` | Table | Write new data | ETL pipelines, data ingestion |
| `UPDATE` | Table | Modify existing data | Data correction workflows |
| `DELETE` | Table | Remove data | Data retention policies |
| `MODIFY` | Table | Alter table structure | Schema evolution |
| `CREATE TABLE` | Schema | Create new tables | Agent Bricks writing results |
| `CREATE SCHEMA` | Catalog | Create new schemas | Admin operations |
| `ALL PRIVILEGES` | Any | All permissions on object | Full control (use sparingly) |

### GRANT Syntax Pattern

```sql
-- Basic pattern
GRANT <privilege> ON <object_type> <object_name> TO <principal>;

-- Examples
GRANT USE CATALOG ON CATALOG finance_prod TO `analysts`;
GRANT USE SCHEMA ON SCHEMA finance_prod.accounting TO `analysts`;
GRANT SELECT ON TABLE finance_prod.accounting.transactions TO `analysts`;
```

### Permission Cascade Example

```sql
-- Step 1: Grant catalog access
GRANT USE CATALOG ON CATALOG finance_prod TO `analysts`;

-- Step 2: Grant schema access
GRANT USE SCHEMA ON SCHEMA finance_prod.accounting TO `analysts`;

-- Step 3: Grant table access
GRANT SELECT ON TABLE finance_prod.accounting.transactions TO `analysts`;

-- Now analysts group can query: SELECT * FROM finance_prod.accounting.transactions
```

### Who Can Grant Permissions

| Role | Can Grant On | Scope |
|------|--------------|-------|
| **Metastore Admin** | All objects | Account-wide |
| **Catalog Owner** | Catalog and all child objects | Specific catalog |
| **Schema Owner** | Schema and all child objects | Specific schema |
| **Table Owner** | Specific table | Individual table |
| **Users with GRANT permission** | Objects they have GRANT on | Delegated scope |

**Documentation:** 
- [GRANT Statement](https://docs.databricks.com/aws/en/sql/language-manual/security-grant.html)
- [Unity Catalog Privileges](https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/index.html)

---

## 🎭 Row-Level Security: Row Filters

Row filters restrict **which rows** users can see in a table based on their identity or group membership.

> 📺 **[View interactive row filters flow →](interactive/uc-row-filters.html)**

### Concept

When a row filter is applied to a table:
1. User queries the table normally (`SELECT * FROM table`)
2. UC automatically evaluates the filter function for each row
3. UC returns only rows where the filter function returns `TRUE`
4. User is unaware of filtered-out rows (they simply don't appear in results)

### How Row Filters Work

```mermaid
sequenceDiagram
    participant User as User: alice@company.com
    participant Product as AI Product
    participant UC as Unity Catalog
    participant Filter as Row Filter Function
    participant Table as Table Data
    
    User->>Product: Query: SELECT * FROM sales_data
    Product->>UC: Execute query (with user context)
    
    UC->>UC: Identify current_user()<br/>= alice@company.com
    
    UC->>Filter: Evaluate filter for each row<br/>filter_by_owner(owner_email)
    Filter->>Filter: Check: owner_email = current_user()?
    
    alt Row matches filter
        Filter->>UC: Return TRUE
        UC->>Table: Include row in results
    else Row doesn't match
        Filter->>UC: Return FALSE
        UC->>UC: Exclude row from results
    end
    
    Table-->>UC: Filtered dataset
    UC-->>Product: Return only Alice's rows
    Product-->>User: Display results
    
    Note over UC,Filter: Different users see<br/>different rows from<br/>same query
```

### Row Filter Function Pattern

```sql
-- Create filter function
CREATE FUNCTION catalog.schema.filter_function_name(column_name DATA_TYPE)
RETURNS BOOLEAN
RETURN condition_using_current_user_or_is_member;

-- Apply filter to table
ALTER TABLE catalog.schema.table_name
  SET ROW FILTER catalog.schema.filter_function_name ON (column_name);
```

### Example: User-Based Filter

```sql
-- Filter: Users see only their own rows
CREATE FUNCTION sales.filters.user_owns_row(owner STRING)
RETURNS BOOLEAN
RETURN owner = current_user();

ALTER TABLE sales.data.opportunities
  SET ROW FILTER sales.filters.user_owns_row ON (owner_email);
```

### Example: Group-Based Filter

```sql
-- Filter: Users see rows based on group membership
CREATE FUNCTION sales.filters.team_access(team STRING)
RETURNS BOOLEAN
RETURN is_member(team);

ALTER TABLE sales.data.opportunities
  SET ROW FILTER sales.filters.team_access ON (team_name);
```

### Example: Hierarchical Filter

```sql
-- Filter: Managers see team data, employees see own data
CREATE FUNCTION hr.filters.hierarchical(employee STRING, manager STRING)
RETURNS BOOLEAN
RETURN 
    employee = current_user() OR         -- Own records
    manager = current_user() OR          -- Managed records
    is_member('hr-admins');              -- HR sees all

ALTER TABLE hr.data.employee_reviews
  SET ROW FILTER hr.filters.hierarchical ON (employee_email, manager_email);
```

### Common Row Filter Patterns

| Pattern | Use Case | Logic |
|---------|----------|-------|
| **User-based** | Personal data (own records only) | `column = current_user()` |
| **Group-based** | Team data (department access) | `is_member(column)` |
| **Hierarchical** | Manager/employee relationships | `owner = current_user() OR manager = current_user()` |
| **Time-based** | Historical data restrictions | `date_column >= current_date() - 365` |
| **Multi-tenant** | SaaS isolation | `tenant_id = extract_tenant(current_user())` |
| **Compliance bypass** | Audit/compliance sees all | `is_member('compliance') OR condition` |

### Removing Row Filters

```sql
-- Remove row filter from table
ALTER TABLE catalog.schema.table_name DROP ROW FILTER;
```

**Documentation:** [Row Filters and Column Masks](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-row-filter-column-mask.html)

---

## 🔒 Column-Level Security: Column Masks

Column masks control **what values** users see in specific columns based on their identity or group membership.

> 📺 **[View interactive column masks flow →](interactive/uc-column-masks.html)**

### Concept

When a column mask is applied:
1. User queries the table including masked columns
2. UC evaluates the mask function for the user
3. UC returns transformed values based on mask logic
4. User sees masked/redacted values, not original data

### How Column Masks Work

```mermaid
sequenceDiagram
    participant User as User: analyst@company.com<br/>Group: analysts
    participant Product as AI Product
    participant UC as Unity Catalog
    participant Mask as Column Mask Function
    participant Table as Table Data
    
    User->>Product: Query: SELECT ssn FROM customers
    Product->>UC: Execute query (with user context)
    
    UC->>UC: Identify user groups<br/>is_member('analysts') = TRUE
    
    UC->>Table: Retrieve raw column value<br/>SSN: 123-45-6789
    Table->>Mask: Pass value to mask function<br/>mask_ssn()
    
    Mask->>Mask: Evaluate:<br/>CASE WHEN is_member('admins')<br/>THEN VALUE<br/>ELSE '***-**-' || SUBSTR(VALUE, -4)
    
    alt User is admin
        Mask->>UC: Return: 123-45-6789
    else User is not admin
        Mask->>UC: Return: ***-**-6789
    end
    
    UC-->>Product: Return masked value
    Product-->>User: Display: ***-**-6789
    
    Note over Mask: Original value never<br/>leaves UC unmasked
```

### Column Mask Function Pattern

```sql
-- Create mask function
CREATE FUNCTION catalog.schema.mask_function_name()
RETURNS DATA_TYPE
RETURN 
    CASE 
        WHEN condition THEN VALUE              -- Original value
        WHEN other_condition THEN transform    -- Transformed value
        ELSE default_mask                      -- Default mask
    END;

-- Apply mask to column
ALTER TABLE catalog.schema.table_name
  ALTER COLUMN column_name SET MASK catalog.schema.mask_function_name;
```

**Important:** `VALUE` is a special keyword representing the original column value.

### Example: SSN Masking

```sql
-- Mask: Show last 4 digits only to non-admins
CREATE FUNCTION customer.masks.mask_ssn()
RETURNS STRING
RETURN 
    CASE 
        WHEN is_member('admins') THEN VALUE
        ELSE CONCAT('***-**-', SUBSTR(VALUE, -4))
    END;

ALTER TABLE customer.data.customers
  ALTER COLUMN ssn SET MASK customer.masks.mask_ssn;
```

### Example: Email Partial Masking

```sql
-- Mask: Show partial email for verification
CREATE FUNCTION customer.masks.mask_email()
RETURNS STRING
RETURN 
    CASE 
        WHEN is_member('customer-service') THEN VALUE
        WHEN is_member('analysts') THEN 
            CONCAT(SUBSTR(VALUE, 1, 2), '***@', SPLIT_PART(VALUE, '@', 2))
        ELSE '***@***'
    END;

ALTER TABLE customer.data.customers
  ALTER COLUMN email SET MASK customer.masks.mask_email;
```

### Example: Conditional Masking by Data Classification

```sql
-- Mask: Different masking based on data sensitivity
CREATE FUNCTION data.masks.conditional_mask()
RETURNS STRING
RETURN 
    CASE 
        WHEN is_member('data-owners') THEN VALUE
        WHEN sensitivity_level = 'high' AND is_member('managers') THEN VALUE
        WHEN sensitivity_level = 'medium' THEN SUBSTR(VALUE, 1, 10) || '***'
        ELSE '*** REDACTED ***'
    END;
```

### Common Column Mask Patterns

| Pattern | Use Case | Masking Logic |
|---------|----------|---------------|
| **Full redaction** | Hide entire value | `'***'` or `NULL` |
| **Partial redaction** | Show last N characters | `CONCAT('***', SUBSTR(VALUE, -4))` |
| **Email masking** | Hide username, show domain | `CONCAT('***@', SPLIT_PART(VALUE, '@', 2))` |
| **Hash masking** | Pseudonymize for analytics | `SHA2(VALUE, 256)` |
| **Role-based** | Different masks per role | Multiple `WHEN is_member()` conditions |
| **Null masking** | Hide from specific groups | `CASE WHEN is_member() THEN NULL ELSE VALUE` |

### Removing Column Masks

```sql
-- Remove mask from column
ALTER TABLE catalog.schema.table_name
  ALTER COLUMN column_name DROP MASK;
```

**Documentation:** [Column Masks](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-row-filter-column-mask.html)

---

## 🏷️ Attribute-Based Access Control (ABAC)

> **Preview Feature:** ABAC is currently in Public Preview.
>
> 📺 **[View interactive ABAC + Governed Tags flow →](interactive/uc-abac-governed-tags.html)**

ABAC is a **centralized, tag-based policy framework** for enforcing access control in Unity Catalog. It enables admins to define scalable policies that apply dynamically across catalogs, schemas, and tables based on **governed tags**. Databricks recommends using ABAC for centralized and scalable governance, rather than applying filters or masks individually on each table.

### ABAC vs Table-Level Filtering

| Aspect | ABAC (Recommended) | Table-Level Row/Column Filters |
|--------|-------------------|-------------------------------|
| **Scope** | Centralized, tag-driven | Per-table configuration |
| **Scalability** | Define once → apply to 1000s of tables | Must configure each table |
| **Management** | Policies reference governed tags | UDFs directly on tables |
| **Updates** | Change tag → access changes instantly | Must update each table |
| **Use When** | Centralized governance at scale | Per-table logic needed |

### Governed Tags: The Foundation

**[Governed Tags](https://docs.databricks.com/aws/en/admin/governed-tags/)** are account-level tags with enforced rules for consistency. They classify data assets with standardized attributes:

```
sensitivity=high
region=EMEA
domain=finance
classification=pii
```

**Key Characteristics:**
- Defined at **account level** with allowed values
- Applied to **catalogs, schemas, or tables** (inherit downward)
- Control **who can assign tags** and **what values** are allowed
- Tags alone **don't enforce access** — ABAC policies do the enforcement

### How ABAC Works with Governed Tags

```mermaid
flowchart TB
    subgraph Tags["Governed Tags (Classification)"]
        TagDef["Account-level tag definitions<br/>sensitivity: [low, medium, high, critical]<br/>region: [EMEA, AMER, APAC]"]
        TagAssign["Tags applied to tables<br/>customer_data: sensitivity=high, region=EMEA"]
    end
    
    subgraph ABAC["ABAC Policies (Enforcement)"]
        Policy["Policy: If sensitivity=high<br/>THEN require compliance-team"]
        UDF["UDF: filter_by_region()<br/>Row filter logic"]
    end
    
    subgraph Query["Query Execution"]
        User["User: alice@company.com<br/>Groups: compliance-team"]
        Eval["UC evaluates:<br/>1. Table has sensitivity=high<br/>2. Policy requires compliance-team<br/>3. Alice is in compliance-team"]
        Result["✅ Access granted<br/>with policy filters applied"]
    end
    
    TagDef --> TagAssign
    TagAssign --> Policy
    Policy --> UDF
    User --> Eval
    Eval --> Result
    
    style Tags fill:#dbeafe,stroke:#3b82f6,stroke-width:2px
    style ABAC fill:#f3e8ff,stroke:#a855f7,stroke-width:2px
    style Query fill:#d1fae5,stroke:#10b981,stroke-width:2px
```

### ABAC Policy Types

Two types of ABAC policies are supported:

| Policy Type | Purpose | Example Use Case |
|-------------|---------|------------------|
| **Row Filter Policies** | Restrict access to rows based on data content | Only show rows where `region=EMEA` to users with EMEA access |
| **Column Mask Policies** | Control what values users see in columns | Mask phone numbers unless table is tagged `sensitivity=low` |

### ABAC Policy Example

```sql
-- Example: ABAC row filter policy referencing governed tags
-- (Conceptual - actual syntax may vary per feature release)

-- 1. Define governed tag at account level
CREATE TAG POLICY sensitivity
  ALLOWED_VALUES = ['low', 'medium', 'high', 'critical'];

-- 2. Apply tag to tables
ALTER TABLE customer.data.transactions
  SET TAG sensitivity = 'high';

-- 3. Create UDF for filtering logic
CREATE FUNCTION security.filters.require_compliance()
RETURNS BOOLEAN
RETURN is_member('compliance-team') OR is_member('admins');

-- 4. Create ABAC policy referencing tag and UDF
-- Policy: Tables tagged sensitivity=high require compliance-team membership
CREATE POLICY high_sensitivity_access
  ON TAG sensitivity = 'high'
  USING security.filters.require_compliance();
```

### Benefits of ABAC with Governed Tags

| Benefit | Description |
|---------|-------------|
| **Scalability** | Manage access at scale by leveraging tags instead of per-table permissions |
| **Flexibility** | Adjust governance by updating tags or policies without modifying each table |
| **Centralized Governance** | Single policy framework spans catalogs, schemas, and tables |
| **Dynamic Enforcement** | Access decisions evaluated in real-time based on tags and user context |
| **Instant Updates** | Change a tag → access changes immediately across all affected tables |
| **Auditability** | Full visibility into data access through audit logs |

### ABAC Best Practices

1. **Use ABAC for centralized governance:** Apply policies at catalog/schema level for consistency
2. **Define clear tag taxonomies:** Standardize values like `sensitivity: [low, medium, high, critical]`
3. **Fail secure:** Default to deny if policy conditions aren't met
4. **Admin bypass:** Allow compliance/admin roles to override for audits
5. **Start with governed tags:** Classify data before creating policies
6. **Test thoroughly:** Verify with multiple user personas and tag combinations

### ABAC Limitations

- Requires compute on **Databricks Runtime 16.4+** or serverless
- Cannot apply policies directly to **views** (but underlying tables are enforced)
- Only one row filter can resolve per table per user at runtime
- See [official documentation](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac) for complete limitations

**Official Documentation:**
- [Unity Catalog ABAC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac)
- [Governed Tags](https://docs.databricks.com/aws/en/admin/governed-tags/)
- [ABAC Tutorial](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac-tutorial.html)

---

## 🔄 Dynamic Views

Dynamic views use SQL logic to implement complex access control patterns that go beyond simple row filters and column masks.

### When to Use Dynamic Views

| Use Case | Row Filter/Mask | Dynamic View |
|----------|-----------------|--------------|
| **Simple user/group check** | ✅ Preferred | ❌ Overkill |
| **Cross-table logic** | ❌ Not possible | ✅ Use view |
| **Complex aggregations** | ❌ Not possible | ✅ Use view |
| **Conditional column selection** | ⚠️ Mask each column | ✅ SELECT CASE |
| **Legacy migration** | ❌ Requires table changes | ✅ Layer views on top |
| **Performance-sensitive** | ✅ Better | ⚠️ May be slower |

### Dynamic View Pattern

```sql
-- Create view with conditional logic
CREATE VIEW catalog.schema.dynamic_view AS
SELECT 
    column1,
    
    -- Conditional column visibility
    CASE 
        WHEN is_member('group1') THEN column2
        ELSE NULL
    END AS column2,
    
    -- Conditional aggregation
    CASE 
        WHEN is_member('executives') THEN SUM(amount)
        WHEN is_member('managers') THEN SUM(amount) OVER (PARTITION BY team)
        ELSE NULL
    END AS total_amount
    
FROM catalog.schema.base_table
WHERE 
    -- Row-level filtering
    (owner_email = current_user() OR is_member('managers'));
```

### Example: Multi-Tier Visibility View

```sql
-- Different users see different aggregations
CREATE VIEW sales.views.revenue_by_role AS
SELECT 
    date,
    region,
    
    -- Executives see exact amounts
    CASE 
        WHEN is_member('executives') THEN revenue
        WHEN is_member('regional-managers') THEN 
            -- Regional managers see regional totals
            SUM(revenue) OVER (PARTITION BY region, date)
        WHEN is_member('sales-reps') THEN 
            -- Sales reps see only their contribution
            CASE WHEN rep_email = current_user() THEN revenue ELSE NULL END
        ELSE NULL
    END AS revenue_amount
    
FROM sales.data.daily_revenue;
```

### Trade-offs

| Aspect | Row Filters/Masks | Dynamic Views |
|--------|------------------|---------------|
| **Setup** | Simpler (function + ALTER) | More complex (view definition) |
| **Performance** | Better (evaluated in engine) | May be slower (subquery) |
| **Flexibility** | Limited to single table | Complex multi-table logic |
| **Maintenance** | Change function definition | Change view definition |
| **Transparency** | Users query base table | Users query view (abstraction layer) |

**Documentation:** [Dynamic Views for Access Control](https://docs.databricks.com/aws/en/data-governance/unity-catalog/create-views.html)

---

## 📖 Unity Catalog Built-in Functions Reference

UC provides session functions that can be used in row filters, column masks, and dynamic views:

| Function | Returns | Description | Example Use Case |
|----------|---------|-------------|------------------|
| `current_user()` | STRING | Email of authenticated user | Row filter: `owner = current_user()` |
| `is_member('group')` | BOOLEAN | TRUE if user is in specified group | Column mask: `WHEN is_member('admins') THEN VALUE` |
| `current_catalog()` | STRING | Name of current catalog | Context-aware policies |
| `current_schema()` | STRING | Name of current schema | Context-aware policies |
| `current_database()` | STRING | Alias for `current_schema()` | Legacy compatibility |
| `current_timestamp()` | TIMESTAMP | Current timestamp | Time-based access: `date > current_timestamp() - INTERVAL '90' DAY` |
| `current_date()` | DATE | Current date | Date-based filtering |

### Function Examples

```sql
-- Example 1: User-specific row filter
CREATE FUNCTION filters.my_data(owner STRING)
RETURNS BOOLEAN
RETURN owner = current_user();

-- Example 2: Group-based column mask
CREATE FUNCTION masks.redact_pii()
RETURNS STRING
RETURN CASE WHEN is_member('pii-authorized') THEN VALUE ELSE '***' END;

-- Example 3: Time-based row filter
CREATE FUNCTION filters.recent_data(record_date DATE)
RETURNS BOOLEAN
RETURN record_date >= current_date() - INTERVAL '365' DAY;

-- Example 4: Combined logic
CREATE FUNCTION filters.complex_access(owner STRING, dept STRING, created_date DATE)
RETURNS BOOLEAN
RETURN 
    (owner = current_user() OR is_member(dept)) AND
    (created_date >= current_date() - INTERVAL '90' DAY OR is_member('admins'));
```

**Documentation:** [SQL Functions Reference](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-functions-builtin.html)

---

## 🔗 Pattern Integration: How UC Enforces Authentication Patterns

Unity Catalog enforces authorization differently based on which authentication pattern is used:

### Pattern Integration Architecture

```mermaid
flowchart TB
    subgraph Pattern1["Pattern 1: Automatic Auth"]
        SP[Service Principal<br/>sp-agent-prod]
        SP1[Fixed Identity]
    end
    
    subgraph Pattern2["Pattern 2: User Auth"]
        User[End User<br/>alice@company.com]
        User1[Variable Identity]
    end
    
    subgraph Pattern3["Pattern 3: Manual"]
        Ext[External API<br/>Not UC-managed]
    end
    
    subgraph UC["Unity Catalog Enforcement"]
        Grants[Check GRANTs<br/>on objects]
        RowCheck{Row filters<br/>defined?}
        ColCheck{Column masks<br/>defined?}
        Data[(Tables)]
    end
    
    SP --> SP1
    User --> User1
    
    SP1 -->|Query as SP| Grants
    User1 -->|Query as user| Grants
    
    Grants -->|Permission OK| RowCheck
    
    RowCheck -->|Yes| EvalRow[Evaluate:<br/>current_user = user<br/>or SP identity]
    RowCheck -->|No| ColCheck
    
    EvalRow -->|Filter rows| ColCheck
    
    ColCheck -->|Yes| EvalCol[Evaluate:<br/>is_member<br/>for user/SP groups]
    ColCheck -->|No| Data
    
    EvalCol -->|Mask columns| Data
    
    Ext -.->|No UC enforcement| ExtData[(External Data)]
    
    style Pattern1 fill:#fdebd0,stroke:#e67e22,stroke-width:2px
    style Pattern2 fill:#d5f5e3,stroke:#27ae60,stroke-width:2px
    style Pattern3 fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    style UC fill:#e8f8f5,stroke:#1abc9c,stroke-width:3px
```

### How Each Pattern Works with UC

#### Pattern 1: Automatic Authentication Passthrough (Service Principal)

```sql
-- Service principal: sp-agent-prod
-- Groups: [agents, production-services]

-- Query executed as sp-agent-prod
SELECT * FROM catalog.schema.table;

-- UC evaluation:
-- 1. Check GRANTs for sp-agent-prod
-- 2. Evaluate row filters (if any) with current_user() = sp-agent-prod
-- 3. Evaluate column masks (if any) with is_member() for SP's groups
-- 4. Return data based on SP's permissions
```

**Key Characteristics:**
- Same permissions every execution
- Row filters evaluate to same SP identity
- Column masks check SP's group memberships
- Ideal for consistent, automated access

#### Pattern 2: User Authentication Passthrough (OBO)

```sql
-- User: alice@company.com
-- Groups: [analysts, sales-team]

-- Query executed as alice@company.com
SELECT * FROM catalog.schema.table;

-- UC evaluation:
-- 1. Check GRANTs for alice@company.com and her groups
-- 2. Evaluate row filters: current_user() = 'alice@company.com'
-- 3. Evaluate column masks: is_member('analysts'), is_member('sales-team')
-- 4. Return data based on Alice's permissions and group memberships

-- Different user (Bob) gets different results from same query
```

**Key Characteristics:**
- Different permissions per user
- Row filters dynamically filter per user
- Column masks apply differently per user's groups
- Ideal for personalized, user-specific access

#### Pattern 3: Manual Credentials

- UC is **not involved** - external service handles authorization
- Use for APIs outside Databricks (OpenAI, Salesforce, etc.)
- Data from external sources is not governed by UC until written to UC tables

### 📖 Agent Bricks & Agent Framework Authentication Reference

For **[Agent Bricks](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/)** and **AI agents**, the authentication methods integrate with UC as follows:

#### Agent Bricks Use Cases

Agent Bricks supports these production-grade AI agent templates, all of which integrate with UC for authorization:

| Use Case | UC Integration | Auth Pattern |
|----------|----------------|--------------|
| **[Knowledge Assistant](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/knowledge-assistant)** | Vector indexes governed by UC | Pattern 1 or 2 |
| **[Information Extraction](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/key-info-extraction)** (Beta) | Source docs and output tables | Pattern 1 or 2 |
| **[Custom LLM](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/custom-llm)** (Beta) | Model endpoints in UC | Pattern 1 or 2 |
| **[Multi-Agent Supervisor](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor)** (Beta) | Orchestrates Genie + agents | Pattern 2 (OBO) |
| **[Code Your Own](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent)** | Full UC access via SDK | Pattern 1, 2, or 3 |

#### Automatic Authentication Passthrough
- **Agent Framework:** Agent runs with permissions of deployer, Databricks manages short-lived credentials
- **UC Integration:** Service principal permissions evaluated (Pattern 1 above)
- **When to use:** Simple agents, consistent access requirements, least-privilege automation
- **Reference:** [Agent Authentication - Automatic Passthrough](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#automatic-authentication-passthrough)

#### On-Behalf-Of-User (OBO) Authentication
- **Agent Framework:** Agent runs with permissions of end user making request
- **UC Integration:** Per-user row filters, column masks, and ABAC policies apply (Pattern 2 above)
- **When to use:** Per-user data access, fine-grained UC governance, user-attributed auditing
- **Security:** Tokens are downscoped to declared API scopes, reducing risk
- **Reference:** [Agent Authentication - OBO](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#on-behalf-of-user-authentication)

**OBO Security Considerations:**
- Agents can access sensitive resources on behalf of users
- While scopes restrict APIs, endpoints might allow more actions than explicitly requested
- Example: `serving.serving-endpoints` scope grants permission to run a serving endpoint, but that endpoint may access additional API scopes
- **Always review:** [OBO Security Considerations](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#obo-security-considerations)

#### Manual Authentication (OAuth/PAT)
- **Agent Framework:** Explicitly provide credentials via environment variables
- **UC Integration:** Depends on credential type (service principal vs user PAT)
- **When to use:** External resources, prompt registry access, non-passthrough scenarios
- **OAuth (Recommended):** Secure, token-based with automatic refresh
- **Reference:** [Agent Authentication - Manual](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#manual-authentication)

> **Important:** For complete Agent Framework authentication setup (code examples, MLflow integration, resource declarations), see the [official Agent Authentication documentation](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication). This document focuses on **how UC enforces authorization** once authentication is established.

---

## ✅ Testing and Verification

### Check Applied Policies

```sql
-- View table details including row filters
DESCRIBE TABLE EXTENDED catalog.schema.table_name;

-- Check grants on table
SHOW GRANTS ON TABLE catalog.schema.table_name;

-- View column details including masks
DESCRIBE TABLE catalog.schema.table_name column_name;

-- View function definition
SHOW CREATE FUNCTION catalog.schema.filter_function;
```

### Test with Multiple Personas

Create test matrix:

| Test User | Groups | Expected Rows | Expected Column Values |
|-----------|--------|---------------|----------------------|
| alice@company.com | `analysts` | 100 rows (her data) | SSN masked to last 4 |
| bob@company.com | `analysts, managers` | 500 rows (team data) | SSN masked to last 4 |
| carol@company.com | `admins` | 10,000 rows (all data) | SSN unmasked |

```sql
-- Test as each user (run in separate sessions)
SELECT COUNT(*) FROM catalog.schema.table;
SELECT ssn FROM catalog.schema.table LIMIT 1;
```

### Verify Row Filter Logic

```sql
-- As admin, check filter function logic
SHOW CREATE FUNCTION catalog.schema.row_filter_name;

-- Test filter independently (as admin with bypass)
SELECT 
    COUNT(*) as total_rows,
    COUNT(*) FILTER (WHERE owner_email = 'alice@company.com') as alice_rows
FROM catalog.schema.table;
```

### Audit Logs

```sql
-- Query audit logs to see who accessed what
SELECT 
    user_identity.email,
    request_params.full_name_arg AS object_accessed,
    action_name,
    event_time,
    request_params.command_text AS query
FROM system.access.audit
WHERE request_params.full_name_arg = 'catalog.schema.table'
  AND event_date >= current_date() - INTERVAL '7' DAY
ORDER BY event_time DESC
LIMIT 100;
```

**Documentation:** [Unity Catalog Audit Logs](https://docs.databricks.com/aws/en/administration-guide/account-settings/audit-logs.html)

---

## ⚡ Performance Considerations

Row filters and column masks add overhead to query execution. Consider these optimization strategies:

### Performance Impact

| Operation | Overhead | Mitigation Strategy |
|-----------|----------|---------------------|
| **Simple row filter** | Low (5-10%) | Acceptable for most use cases |
| **Complex row filter** | Medium (10-30%) | Simplify logic, use indexes |
| **Multiple row filters** | High (30%+) | Consolidate into single filter |
| **Column mask** | Low-Medium | Minimal impact |
| **Dynamic view with aggregations** | High | Use materialized views |

### Optimization Strategies

#### 1. Use Materialized Views

```sql
-- Create materialized view with pre-filtered data
CREATE MATERIALIZED VIEW catalog.schema.filtered_view AS
SELECT * FROM catalog.schema.base_table
WHERE department = 'sales';

-- Apply row filter to materialized view
ALTER MATERIALIZED VIEW catalog.schema.filtered_view
  SET ROW FILTER catalog.schema.user_filter ON (owner_email);

-- Queries hit pre-filtered, cached data
SELECT * FROM catalog.schema.filtered_view;
```

#### 2. Partition Tables by Filter Column

```sql
-- Partition table by department (commonly filtered column)
CREATE TABLE catalog.schema.partitioned_table (
    id STRING,
    department STRING,
    data STRING
)
PARTITIONED BY (department);

-- Row filter can leverage partition pruning
ALTER TABLE catalog.schema.partitioned_table
  SET ROW FILTER catalog.schema.dept_filter ON (department);
```

#### 3. Simplify Filter Logic

```sql
-- ❌ Complex (slower)
CREATE FUNCTION filters.complex(dept STRING, region STRING, level STRING)
RETURNS BOOLEAN
RETURN 
    (dept = 'sales' AND is_member('sales-' || region || '-' || level)) OR
    (dept = 'marketing' AND is_member('marketing-team')) OR
    is_member('executives');

-- ✅ Simplified (faster)
CREATE FUNCTION filters.simple(dept STRING)
RETURNS BOOLEAN
RETURN 
    is_member(dept) OR is_member('executives');
```

#### 4. Index Commonly Filtered Columns

```sql
-- Create indexes on columns used in row filters
CREATE INDEX idx_owner ON catalog.schema.table (owner_email);
CREATE INDEX idx_dept ON catalog.schema.table (department);
```

### Performance Monitoring

```sql
-- Check query execution time
SELECT 
    query_id,
    execution_duration_ms,
    query_text
FROM system.query.history
WHERE query_text LIKE '%catalog.schema.filtered_table%'
ORDER BY execution_duration_ms DESC
LIMIT 10;
```

**Documentation:** [Performance Tuning](https://docs.databricks.com/aws/en/optimizations/index.html)

---

## 🎯 Best Practices

### 1. Least Privilege Principle

```sql
-- ❌ Don't grant broad access
GRANT ALL PRIVILEGES ON CATALOG production TO `account users`;

-- ✅ Grant minimum required permissions
GRANT USE CATALOG ON CATALOG production TO `analysts`;
GRANT USE SCHEMA ON SCHEMA production.sales TO `analysts`;
GRANT SELECT ON TABLE production.sales.data TO `analysts`;
```

### 2. Use Groups, Not Individual Users

```sql
-- ❌ Don't grant to individual users
GRANT SELECT ON TABLE data TO `alice@company.com`;
GRANT SELECT ON TABLE data TO `bob@company.com`;

-- ✅ Grant to groups
GRANT SELECT ON TABLE data TO `analysts`;
-- Manage group membership in IdP
```

### 3. Document Filter/Mask Logic

```sql
-- ✅ Add clear comments
CREATE FUNCTION filters.sales_access(owner STRING, team STRING)
RETURNS BOOLEAN
COMMENT 'Row filter: Sales reps see own data | Managers see team data | Executives see all'
RETURN 
    CASE
        -- Executives bypass filter
        WHEN is_member('executives') THEN TRUE
        -- Managers see team data
        WHEN is_member('managers') AND is_member(team) THEN TRUE
        -- Sales reps see own data
        WHEN owner = current_user() THEN TRUE
        ELSE FALSE
    END;
```

### 4. Separate Access Control from Business Logic

```sql
-- ❌ Don't mix
CREATE FUNCTION filters.mixed(status STRING, owner STRING)
RETURNS BOOLEAN
RETURN status = 'active' AND owner = current_user();
-- Confusing: is this access control or business logic?

-- ✅ Separate
CREATE FUNCTION filters.access_only(owner STRING)
RETURNS BOOLEAN
RETURN owner = current_user();

-- Business logic in query
SELECT * FROM table WHERE status = 'active';
-- Row filter handles access control automatically
```

### 5. Test with Multiple Personas

Create test users for each role:
- Regular user
- Power user (manager)
- Limited user
- Admin/compliance

Verify each sees correct data and masked columns.

### 6. Regular Audits

```sql
-- Quarterly review: Who has access to what?
SHOW GRANTS ON CATALOG production;
SHOW GRANTS ON SCHEMA production.sales;
SHOW GRANTS ON TABLE production.sales.sensitive_data;

-- Review row filters and masks
SELECT 
    table_catalog,
    table_schema,
    table_name,
    row_filter,
    column_masks
FROM system.information_schema.tables
WHERE table_catalog = 'production';
```

---

## 🚨 Troubleshooting

### Common Issues and Solutions

| Issue | Symptoms | Diagnosis | Solution |
|-------|----------|-----------|----------|
| **User can't see expected data** | Query returns 0 rows | Check GRANTs, row filters, group membership | Verify user has USE CATALOG, USE SCHEMA, SELECT permissions; Check row filter logic |
| **Column appears masked incorrectly** | Wrong mask applied | Check mask function and user groups | Verify `is_member()` conditions and group membership |
| **Performance degradation** | Slow queries after adding filters | Check filter complexity | Simplify filter logic, add materialized views, partition tables |
| **Filter not applying** | All users see all data | Check filter is set on table | Run `DESCRIBE TABLE EXTENDED` to verify filter |
| **Permission denied** | Error accessing table | Missing GRANTs | Grant USE CATALOG, USE SCHEMA, and SELECT in order |

### Diagnostic Queries

```sql
-- 1. Check if user has table permissions
SHOW GRANTS ON TABLE catalog.schema.table;

-- 2. Check if row filter is applied
DESCRIBE TABLE EXTENDED catalog.schema.table;
-- Look for: Row Filter: catalog.schema.filter_name

-- 3. Check user's group membership
SELECT * FROM system.access.users WHERE email = 'user@company.com';

-- 4. Check if any rows match filter
-- (Run as admin to see unfiltered data)
SELECT COUNT(*) FROM catalog.schema.table
WHERE owner_email = 'user@company.com';

-- 5. View filter function logic
SHOW CREATE FUNCTION catalog.schema.filter_name;

-- 6. Test is_member() for user
SELECT is_member('group_name') AS user_in_group;
```

### Debugging Flowchart

```mermaid
flowchart TD
    Start[User reports access issue]
    
    Q1{Can user query<br/>the table at all?}
    Q2{Does query<br/>return 0 rows?}
    Q3{Are columns<br/>masked?}
    
    Q1 -->|No, error| CheckGrants[Check GRANTs:<br/>SHOW GRANTS ON TABLE]
    Q1 -->|Yes, but wrong data| Q2
    
    Q2 -->|Yes, 0 rows| CheckFilter[Check row filter:<br/>DESCRIBE TABLE EXTENDED]
    Q2 -->|No, some rows| Q3
    
    Q3 -->|Yes, incorrectly| CheckMask[Check column mask:<br/>DESCRIBE TABLE<br/>SHOW CREATE FUNCTION]
    Q3 -->|No mask issue| CheckPerf[Check performance:<br/>Query execution time]
    
    CheckGrants --> FixGrants[Grant missing permissions:<br/>USE CATALOG, USE SCHEMA, SELECT]
    CheckFilter --> FixFilter[Fix filter logic or<br/>check group membership]
    CheckMask --> FixMask[Fix mask function or<br/>check is_member conditions]
    CheckPerf --> Optimize[Optimize with<br/>materialized views or partitioning]
    
    style Start fill:#ebf5fb,stroke:#3498db,stroke-width:2px
    style FixGrants fill:#d5f5e3,stroke:#27ae60,stroke-width:2px
    style FixFilter fill:#d5f5e3,stroke:#27ae60,stroke-width:2px
    style FixMask fill:#d5f5e3,stroke:#27ae60,stroke-width:2px
    style Optimize fill:#fef5e7,stroke:#f39c12,stroke-width:2px
```

**Documentation:** [Troubleshooting Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/troubleshooting.html)

---

## 📚 Next Steps

Now that you understand Unity Catalog authorization:

### 1. Review Product Integration
**[03-PRODUCT-INTEGRATION.md →](03-PRODUCT-INTEGRATION.md)**

Learn how specific AI products use UC:
- Genie Space (always enforces UC with user context)
- Agent Bricks (configurable UC enforcement)
- Databricks Apps (UC enforcement based on auth mode)
- Model Serving (UC enforcement for data access)

### 2. Explore Real-World Scenarios
**[scenarios/ →](scenarios/)**

Complete implementation examples:
- Multi-team analytics with row filters
- Large-scale deployments with ABAC
- Embedded applications with dynamic views
- Industry-specific patterns (financial services, healthcare, retail)

### 3. Hands-On Setup
**[examples/ →](examples/)** *(Coming Soon)*

> **Note**: Practical, copy-paste ready examples are currently being developed. These will include step-by-step SQL scripts and UI instructions for:
> - Row-level security setup
> - Column-level security and masking
> - ABAC patterns
> - Genie Space curation with UC governance

For now, refer to the [scenarios/](scenarios/) folder for complete implementation examples.

### 4. Review Best Practices
**[Best Practices →](../guides/)** *(See related guides)*

> **Note**: Dedicated best-practices section is planned for future release. For now, this document includes production-ready patterns in the sections above.

For additional guidance, see:
- [Authentication Guide](../guides/authentication.md) - Secure authentication patterns
- [Networking Guide](../guides/networking.md) - Multi-cloud networking best practices

---

## 🔖 Quick Reference

### UC Authorization Layers

| Layer | Control Type | Configured With | Example |
|-------|-------------|-----------------|---------|
| **Object** | Table access | GRANT statements | `GRANT SELECT ON TABLE` |
| **Row** | Which rows visible | Row filter functions | `current_user() = owner` |
| **Column** | Column value masking | Column mask functions | `WHEN is_member() THEN VALUE` |

### Key SQL Patterns

**Grant Permissions:**
```sql
GRANT USE CATALOG ON CATALOG catalog_name TO `group`;
GRANT SELECT ON TABLE catalog.schema.table TO `group`;
```

**Row Filter:**
```sql
CREATE FUNCTION catalog.schema.filter(col DATA_TYPE) RETURNS BOOLEAN RETURN condition;
ALTER TABLE catalog.schema.table SET ROW FILTER catalog.schema.filter ON (column);
```

**Column Mask:**
```sql
CREATE FUNCTION catalog.schema.mask() RETURNS DATA_TYPE RETURN CASE WHEN condition THEN VALUE ELSE mask END;
ALTER TABLE catalog.schema.table ALTER COLUMN column SET MASK catalog.schema.mask;
```

### UC Functions

| Function | Use For |
|----------|---------|
| `current_user()` | Row filters based on user identity |
| `is_member('group')` | Column masks and row filters based on group |
| `current_catalog()` | Context-aware policies |
| `current_timestamp()` | Time-based access control |

---

**Questions?** See troubleshooting above or continue to [03-PRODUCT-INTEGRATION.md](03-PRODUCT-INTEGRATION.md) to learn how AI products use Unity Catalog.
