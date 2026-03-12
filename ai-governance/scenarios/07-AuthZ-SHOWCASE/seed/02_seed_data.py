"""
Phase 0 / Step 2 — Create tables and seed synthetic data.

Creates all tables in authz_showcase.sales and authz_showcase.knowledge_base,
then inserts realistic synthetic data. Safe to re-run (drops and recreates tables).

Your email (CURRENT_USER_EMAIL) is mapped to a West region rep so row-level
security is immediately testable without adding extra users.

Usage:
    DATABRICKS_CONFIG_PROFILE=<YOUR_CLI_PROFILE> \\
    CURRENT_USER_EMAIL=you@databricks.com \\
    python 02_seed_data.py

Expected output:
    Creating tables...
      ✓ authz_showcase.sales.sales_reps
      ✓ authz_showcase.sales.customers
      ✓ authz_showcase.sales.products
      ✓ authz_showcase.sales.opportunities
      ✓ authz_showcase.knowledge_base.product_docs
      ✓ authz_showcase.knowledge_base.sales_playbooks
    Seeding data...
      ✓ sales_reps      8 rows
      ✓ customers      10 rows
      ✓ products        5 rows
      ✓ opportunities  41 rows
      ✓ product_docs   10 rows
      ✓ sales_playbooks 6 rows
    Done. Next step: run 03_row_col_security.sql
"""

import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

CATALOG = "authz_showcase"
CURRENT_USER = os.environ.get("CURRENT_USER_EMAIL", "")


def sql(w: WorkspaceClient, statement: str) -> list[dict]:
    """Execute a SQL statement on the best available warehouse, polling until done."""
    import time
    warehouses = list(w.warehouses.list())
    if not warehouses:
        raise RuntimeError("No SQL warehouses found in this workspace.")
    # Prefer a running warehouse; otherwise use the first one (it will auto-start)
    running = [wh for wh in warehouses if wh.state and wh.state.value == "RUNNING"]
    warehouse_id = (running[0] if running else warehouses[0]).id

    # Submit with wait_timeout=0 so we always poll (avoids the 50s limit issue)
    resp = w.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
        wait_timeout="0s",
    )
    statement_id = resp.statement_id

    # Poll until terminal state
    terminal = {StatementState.SUCCEEDED, StatementState.FAILED,
                StatementState.CANCELED, StatementState.CLOSED}
    while resp.status.state not in terminal:
        time.sleep(2)
        resp = w.statement_execution.get_statement(statement_id)

    if resp.status.state == StatementState.FAILED:
        raise RuntimeError(f"SQL failed: {resp.status.error.message}\nSQL: {statement[:200]}")
    if resp.result and resp.result.data_array:
        cols = [c.name for c in resp.manifest.schema.columns]
        return [dict(zip(cols, row)) for row in resp.result.data_array]
    return []


# ── DDL ──────────────────────────────────────────────────────────────────────

TABLES = {
    f"{CATALOG}.sales.sales_reps": f"""
        CREATE OR REPLACE TABLE {CATALOG}.sales.sales_reps (
            rep_id        STRING        NOT NULL COMMENT 'Primary key',
            email         STRING        NOT NULL COMMENT 'Databricks user email — row filter anchor',
            name          STRING        NOT NULL,
            region        STRING        NOT NULL COMMENT 'WEST | EAST | CENTRAL',
            manager_email STRING,
            team          STRING,
            hire_date     DATE,
            quota         DECIMAL(12,2) COMMENT 'MASKED: users in quota_viewers table only — mask_quota uses current_user() lookup (not is_member()) for Genie/Agent Bricks OBO compatibility'
        )
        COMMENT 'Sales representatives. email maps to Databricks workspace users. quota is column-masked by role.'
    """,

    f"{CATALOG}.sales.customers": f"""
        CREATE OR REPLACE TABLE {CATALOG}.sales.customers (
            customer_id     STRING          NOT NULL COMMENT 'Primary key',
            name            STRING          NOT NULL,
            industry        STRING,
            tier            STRING          COMMENT 'ENTERPRISE | MID-MARKET | SMB',
            region          STRING          NOT NULL COMMENT 'WEST | EAST | CENTRAL — row filter anchor',
            contract_value  DECIMAL(12,2)   COMMENT 'MASKED: managers, finance, exec only',
            annual_revenue  DECIMAL(15,2),
            ticker_symbol   STRING          COMMENT 'Used for external data enrichment (Phase 6)'
        )
        COMMENT 'Customer accounts. contract_value is column-masked by role.'
    """,

    f"{CATALOG}.sales.products": f"""
        CREATE OR REPLACE TABLE {CATALOG}.sales.products (
            product_id  STRING          NOT NULL COMMENT 'Primary key',
            name        STRING          NOT NULL,
            category    STRING,
            list_price  DECIMAL(10,2)   NOT NULL COMMENT 'Visible to all',
            cost_price  DECIMAL(10,2)   COMMENT 'MASKED: finance and exec only',
            description STRING
        )
        COMMENT 'Product catalog. cost_price is column-masked by role.'
    """,

    f"{CATALOG}.sales.opportunities": f"""
        CREATE OR REPLACE TABLE {CATALOG}.sales.opportunities (
            opp_id       STRING          NOT NULL COMMENT 'Primary key',
            rep_email    STRING          NOT NULL COMMENT 'Row filter anchor — must match sales_reps.email',
            customer_id  STRING          NOT NULL,
            product_id   STRING          NOT NULL,
            region       STRING          NOT NULL COMMENT 'Row filter anchor',
            stage        STRING          COMMENT 'PROSPECT | DISCOVERY | PROPOSAL | NEGOTIATION | CLOSED_WON | CLOSED_LOST',
            amount       DECIMAL(12,2),
            margin_pct   DECIMAL(5,2)    COMMENT 'MASKED: finance and exec only',
            close_date   DATE,
            is_strategic BOOLEAN         COMMENT 'MASKED: managers and exec only',
            created_at   TIMESTAMP
        )
        COMMENT 'Sales pipeline. Row-filtered by rep_email; margin_pct and is_strategic are column-masked.'
    """,

    f"{CATALOG}.knowledge_base.product_docs": f"""
        CREATE OR REPLACE TABLE {CATALOG}.knowledge_base.product_docs (
            doc_id       STRING  NOT NULL COMMENT 'Primary key',
            product_id   STRING  NOT NULL,
            title        STRING  NOT NULL,
            content      STRING  NOT NULL COMMENT 'Full text — embedded by Vector Search',
            category     STRING  COMMENT 'feature | faq | competitive',
            last_updated DATE
        )
        COMMENT 'Product documentation for Vector Search RAG. No row/col security — shared knowledge base.'
    """,

    f"{CATALOG}.knowledge_base.sales_playbooks": f"""
        CREATE OR REPLACE TABLE {CATALOG}.knowledge_base.sales_playbooks (
            playbook_id  STRING  NOT NULL COMMENT 'Primary key',
            title        STRING  NOT NULL,
            content      STRING  NOT NULL COMMENT 'Full text — embedded by Vector Search',
            audience     STRING  COMMENT 'rep | manager | all',
            region       STRING  COMMENT 'ALL | WEST | EAST | CENTRAL'
        )
        COMMENT 'Sales methodology playbooks for Vector Search RAG. Shared — no per-user filtering.'
    """,
}


# ── Seed data ─────────────────────────────────────────────────────────────────

def get_seed_data(current_user: str) -> dict[str, list[tuple]]:
    if not current_user:
        raise ValueError(
            "Set CURRENT_USER_EMAIL env var to your Databricks workspace email.\n"
            "This maps you to the West Rep persona for immediate testing."
        )

    return {

        # ── sales_reps ────────────────────────────────────────────────────────
        # current_user is placed as a West rep (rep_001) — the primary test persona.
        # Other reps have placeholder emails that won't match any real workspace user.
        f"{CATALOG}.sales.sales_reps": [
            # (rep_id, email, name, region, manager_email, team, hire_date, quota)
            # quota is column-masked — reps see NULL, managers/finance/exec see the value
            ("rep_001", current_user,                    "You (West Rep)",      "WEST",    "mgr_west@showcase.demo",  "West Enterprise",  "2022-01-15", 150000.00),
            ("rep_002", "alice.chen@showcase.demo",      "Alice Chen",          "WEST",    "mgr_west@showcase.demo",  "West Enterprise",  "2021-06-01", 150000.00),
            ("rep_003", "bob.martinez@showcase.demo",    "Bob Martinez",        "WEST",    "mgr_west@showcase.demo",  "West Mid-Market",  "2023-03-10", 140000.00),
            ("rep_004", "carol.jones@showcase.demo",     "Carol Jones",         "EAST",    "mgr_east@showcase.demo",  "East Enterprise",  "2020-09-15", 130000.00),
            ("rep_005", "dave.patel@showcase.demo",      "Dave Patel",          "EAST",    "mgr_east@showcase.demo",  "East Enterprise",  "2022-11-01", 125000.00),
            ("rep_006", "eve.nguyen@showcase.demo",      "Eve Nguyen",          "EAST",    "mgr_east@showcase.demo",  "East Mid-Market",  "2023-07-20", 135000.00),
            ("rep_007", "frank.wu@showcase.demo",        "Frank Wu",            "CENTRAL", "mgr_west@showcase.demo",  "Central",          "2021-04-05", 120000.00),
            ("rep_008", "grace.kim@showcase.demo",       "Grace Kim",           "CENTRAL", "mgr_west@showcase.demo",  "Central",          "2022-08-12", 115000.00),
        ],

        # ── customers ─────────────────────────────────────────────────────────
        # (customer_id, name, industry, tier, region, contract_value, annual_revenue, ticker_symbol)
        f"{CATALOG}.sales.customers": [
            ("cust_001", "Acme Manufacturing",   "Manufacturing",       "ENTERPRISE",  "WEST",    450000.00, 85000000.00,  "ACME"),
            ("cust_002", "Pacific Retail Co",    "Retail",              "MID-MARKET",  "WEST",    120000.00, 22000000.00,  "PCRT"),
            ("cust_003", "SunState Energy",      "Energy",              "ENTERPRISE",  "WEST",    380000.00, 120000000.00, "SNST"),
            ("cust_004", "Atlantic Finance",     "Financial Services",  "ENTERPRISE",  "EAST",    520000.00, 200000000.00, "ATFN"),
            ("cust_005", "Northeast Health",     "Healthcare",          "ENTERPRISE",  "EAST",    290000.00, 75000000.00,  "NEHL"),
            ("cust_006", "Boston Logistics",     "Logistics",           "MID-MARKET",  "EAST",     95000.00, 18000000.00,  "BSTN"),
            ("cust_007", "Midwest Auto Group",   "Automotive",          "ENTERPRISE",  "CENTRAL", 340000.00, 95000000.00,  "MDAG"),
            ("cust_008", "Prairie Farms",        "Agriculture",         "MID-MARKET",  "CENTRAL",  88000.00, 15000000.00,  "PRFM"),
            ("cust_009", "Global Tech Inc",      "Technology",          "ENTERPRISE",  "WEST",    680000.00, 350000000.00, "GLBT"),
            ("cust_010", "Metro Insurance",      "Insurance",           "MID-MARKET",  "EAST",    175000.00, 42000000.00,  "MTRI"),
        ],

        # ── products ──────────────────────────────────────────────────────────
        # (product_id, name, category, list_price, cost_price, description)
        f"{CATALOG}.sales.products": [
            ("prod_001", "DataPlatform Core",    "Platform",    120000.00, 18000.00, "Core data lakehouse platform with Delta Lake, Unity Catalog, and Databricks SQL. Includes 10 TB storage and 5 clusters."),
            ("prod_002", "AI Analytics Suite",   "AI/ML",        85000.00, 12500.00, "End-to-end ML platform with AutoML, MLflow tracking, and Model Serving. Designed for data science teams scaling from experimentation to production."),
            ("prod_003", "Governance Shield",    "Governance",   45000.00,  6800.00, "Unity Catalog governance add-on: fine-grained access control, column masking, row filters, audit logging, and data lineage."),
            ("prod_004", "StreamFlow Pro",       "Streaming",    60000.00,  9000.00, "Real-time streaming ingestion and processing with Structured Streaming, Delta Live Tables, and Kafka integration."),
            ("prod_005", "CloudConnect Bundle",  "Integration",  35000.00,  5200.00, "Multi-cloud connector bundle: 50+ native connectors, partner integrations, and REST API framework for custom sources."),
        ],

        # ── opportunities ─────────────────────────────────────────────────────
        # 41 rows total: 5-6 per rep across all 6 stages, 3 regions.
        # Current user has 6 WEST opps (76% attainment) — best contrast for row filter demo.
        # Attainment spread: Alice 77%, You 76%, Dave 50%, Frank 41%, Grace/Carol/Bob ~31%, Eve 0%.
        f"{CATALOG}.sales.opportunities": [
            # (opp_id, rep_email, customer_id, product_id, region, stage, amount, margin_pct, close_date, is_strategic, created_at)
            # Current user — WEST (6 opps, 76% attainment)
            ("opp_001", current_user, "cust_001", "prod_001", "WEST", "NEGOTIATION",  95000.00, 32.5, "2026-03-31", True,  "2025-12-01T09:00:00"),
            ("opp_002", current_user, "cust_003", "prod_002", "WEST", "PROPOSAL",     72000.00, 28.1, "2026-04-15", False, "2026-01-10T14:30:00"),
            ("opp_003", current_user, "cust_009", "prod_003", "WEST", "DISCOVERY",    38000.00, 35.0, "2026-05-30", True,  "2026-02-05T11:00:00"),
            ("opp_004", current_user, "cust_002", "prod_005", "WEST", "CLOSED_WON",   29000.00, 30.2, "2026-02-28", False, "2025-11-15T08:00:00"),
            ("opp_016", current_user, "cust_009", "prod_004", "WEST", "CLOSED_WON",   85000.00, 31.5, "2026-01-20", True,  "2025-10-01T09:00:00"),
            ("opp_017", current_user, "cust_001", "prod_003", "WEST", "PROSPECT",     42000.00, 28.0, "2026-07-15", False, "2026-02-10T11:00:00"),
            # Alice Chen — WEST (5 opps, 77% attainment)
            ("opp_005", "alice.chen@showcase.demo", "cust_001", "prod_002", "WEST", "PROPOSAL",     68000.00, 27.8, "2026-04-30", False, "2026-01-20T10:00:00"),
            ("opp_006", "alice.chen@showcase.demo", "cust_009", "prod_001", "WEST", "CLOSED_WON",  115000.00, 31.5, "2026-02-15", True,  "2025-10-01T09:00:00"),
            ("opp_018", "alice.chen@showcase.demo", "cust_003", "prod_004", "WEST", "DISCOVERY",    55000.00, 29.5, "2026-05-20", False, "2026-01-15T10:00:00"),
            ("opp_019", "alice.chen@showcase.demo", "cust_002", "prod_005", "WEST", "NEGOTIATION",  88000.00, 32.0, "2026-04-10", True,  "2025-11-01T09:00:00"),
            ("opp_020", "alice.chen@showcase.demo", "cust_009", "prod_002", "WEST", "CLOSED_LOST",  62000.00, 24.5, "2026-01-15", False, "2025-09-01T08:00:00"),
            # Bob Martinez — WEST (5 opps, 31% attainment)
            ("opp_007", "bob.martinez@showcase.demo", "cust_002", "prod_004", "WEST", "PROSPECT",    52000.00, 29.0, "2026-06-30", False, "2026-02-20T16:00:00"),
            ("opp_021", "bob.martinez@showcase.demo", "cust_001", "prod_002", "WEST", "DISCOVERY",   48000.00, 27.0, "2026-06-01", False, "2026-01-20T10:00:00"),
            ("opp_022", "bob.martinez@showcase.demo", "cust_003", "prod_001", "WEST", "PROPOSAL",   120000.00, 33.5, "2026-04-30", True,  "2025-12-01T09:00:00"),
            ("opp_023", "bob.martinez@showcase.demo", "cust_002", "prod_003", "WEST", "NEGOTIATION", 67000.00, 30.0, "2026-03-28", False, "2025-11-15T11:00:00"),
            ("opp_024", "bob.martinez@showcase.demo", "cust_009", "prod_005", "WEST", "CLOSED_WON",  44000.00, 29.0, "2026-02-10", False, "2025-10-01T09:00:00"),
            # Carol Jones — EAST (5 opps, 32% attainment)
            ("opp_008", "carol.jones@showcase.demo", "cust_004", "prod_001", "EAST", "NEGOTIATION", 108000.00, 33.2, "2026-03-20", True,  "2025-11-10T10:30:00"),
            ("opp_009", "carol.jones@showcase.demo", "cust_005", "prod_003", "EAST", "CLOSED_WON",   41000.00, 34.8, "2026-02-20", False, "2025-12-05T13:00:00"),
            ("opp_025", "carol.jones@showcase.demo", "cust_010", "prod_003", "EAST", "PROSPECT",     35000.00, 26.5, "2026-07-30", False, "2026-02-15T10:00:00"),
            ("opp_026", "carol.jones@showcase.demo", "cust_006", "prod_001", "EAST", "DISCOVERY",    95000.00, 32.0, "2026-05-15", True,  "2026-01-10T09:00:00"),
            ("opp_027", "carol.jones@showcase.demo", "cust_004", "prod_002", "EAST", "PROPOSAL",     74000.00, 28.5, "2026-04-20", False, "2025-12-05T11:00:00"),
            # Dave Patel — EAST (5 opps, 50% attainment)
            ("opp_010", "dave.patel@showcase.demo", "cust_010", "prod_002", "EAST", "PROPOSAL",     79000.00, 26.5, "2026-05-15", False, "2026-01-25T11:00:00"),
            ("opp_011", "dave.patel@showcase.demo", "cust_006", "prod_005", "EAST", "DISCOVERY",    31000.00, 28.9, "2026-06-01", False, "2026-02-15T09:30:00"),
            ("opp_028", "dave.patel@showcase.demo", "cust_005", "prod_001", "EAST", "NEGOTIATION",  88000.00, 31.0, "2026-03-22", True,  "2025-11-20T10:00:00"),
            ("opp_029", "dave.patel@showcase.demo", "cust_010", "prod_004", "EAST", "CLOSED_WON",   63000.00, 30.5, "2026-02-05", False, "2025-09-15T09:00:00"),
            ("opp_030", "dave.patel@showcase.demo", "cust_006", "prod_003", "EAST", "CLOSED_LOST",  45000.00, 23.0, "2026-01-10", False, "2025-08-01T08:00:00"),
            # Eve Nguyen — EAST (5 opps, 0% attainment — new rep)
            ("opp_012", "eve.nguyen@showcase.demo", "cust_004", "prod_004", "EAST", "CLOSED_LOST",  58000.00, 25.1, "2026-01-31", True,  "2025-10-20T14:00:00"),
            ("opp_031", "eve.nguyen@showcase.demo", "cust_004", "prod_005", "EAST", "PROSPECT",     28000.00, 27.5, "2026-08-15", False, "2026-02-20T10:00:00"),
            ("opp_032", "eve.nguyen@showcase.demo", "cust_005", "prod_002", "EAST", "DISCOVERY",    72000.00, 29.0, "2026-06-30", False, "2026-01-25T11:00:00"),
            ("opp_033", "eve.nguyen@showcase.demo", "cust_010", "prod_001", "EAST", "PROPOSAL",    110000.00, 34.0, "2026-05-10", True,  "2025-12-10T09:00:00"),
            ("opp_034", "eve.nguyen@showcase.demo", "cust_006", "prod_004", "EAST", "NEGOTIATION",  58000.00, 31.5, "2026-04-05", False, "2025-11-01T10:00:00"),
            # Frank Wu — CENTRAL (5 opps, 41% attainment)
            ("opp_013", "frank.wu@showcase.demo", "cust_007", "prod_001", "CENTRAL", "NEGOTIATION",  92000.00, 31.0, "2026-03-25", True,  "2025-12-10T10:00:00"),
            ("opp_035", "frank.wu@showcase.demo", "cust_008", "prod_002", "CENTRAL", "DISCOVERY",    55000.00, 28.0, "2026-06-20", False, "2026-01-05T10:00:00"),
            ("opp_036", "frank.wu@showcase.demo", "cust_007", "prod_004", "CENTRAL", "PROPOSAL",     78000.00, 30.5, "2026-05-05", True,  "2025-12-15T09:00:00"),
            ("opp_037", "frank.wu@showcase.demo", "cust_008", "prod_005", "CENTRAL", "CLOSED_WON",   49000.00, 29.5, "2026-02-28", False, "2025-10-15T08:00:00"),
            ("opp_038", "frank.wu@showcase.demo", "cust_007", "prod_003", "CENTRAL", "CLOSED_LOST",  38000.00, 22.0, "2026-01-25", False, "2025-08-10T09:00:00"),
            # Grace Kim — CENTRAL (5 opps, 33% attainment)
            ("opp_014", "grace.kim@showcase.demo", "cust_008", "prod_005", "CENTRAL", "PROPOSAL",    27000.00, 29.5, "2026-05-01", False, "2026-02-01T15:00:00"),
            ("opp_015", "grace.kim@showcase.demo", "cust_007", "prod_003", "CENTRAL", "DISCOVERY",   43000.00, 33.8, "2026-06-15", False, "2026-02-25T10:00:00"),
            ("opp_039", "grace.kim@showcase.demo", "cust_008", "prod_001", "CENTRAL", "PROSPECT",    32000.00, 27.0, "2026-08-30", False, "2026-02-25T11:00:00"),
            ("opp_040", "grace.kim@showcase.demo", "cust_007", "prod_002", "CENTRAL", "NEGOTIATION", 65000.00, 31.0, "2026-03-30", True,  "2025-11-10T10:00:00"),
            ("opp_041", "grace.kim@showcase.demo", "cust_008", "prod_004", "CENTRAL", "CLOSED_WON",  38000.00, 30.0, "2026-02-18", False, "2025-09-20T09:00:00"),
        ],

        # ── product_docs ──────────────────────────────────────────────────────
        # (doc_id, product_id, title, content, category, last_updated)
        f"{CATALOG}.knowledge_base.product_docs": [
            ("doc_001", "prod_001", "DataPlatform Core — Feature Overview",
             "DataPlatform Core delivers a unified lakehouse architecture combining data warehousing and data lake capabilities. Key features include: Delta Lake for ACID transactions and time travel, Unity Catalog for governance across all data assets, Databricks SQL for high-performance analytics, Photon engine for 4x faster query performance, and auto-scaling clusters. Supports AWS S3, Azure ADLS Gen2, and GCP GCS natively.",
             "feature", "2026-01-10"),
            ("doc_002", "prod_001", "DataPlatform Core — Deployment FAQ",
             "Q: How long does initial setup take? A: Typically 2-4 hours for a standard deployment with Unity Catalog. Q: What network requirements are needed? A: Private Link or VPC peering recommended for production. Q: Can we bring our own encryption keys? A: Yes, customer-managed keys (CMK) supported on all clouds. Q: What SLA is offered? A: 99.9% uptime SLA for Premium tier, 99.5% for Standard.",
             "faq", "2026-01-15"),
            ("doc_003", "prod_002", "AI Analytics Suite — MLflow Integration Guide",
             "AI Analytics Suite integrates with MLflow for complete experiment tracking, model registry, and deployment. Workflow: (1) Log experiments with mlflow.autolog() for automatic metric capture. (2) Register best models in Unity Catalog model registry for versioning and governance. (3) Deploy to Model Serving with one click — serverless or dedicated endpoints. (4) Monitor drift with Lakehouse Monitoring. Supports PyTorch, TensorFlow, scikit-learn, XGBoost, and HuggingFace.",
             "feature", "2026-01-20"),
            ("doc_004", "prod_002", "AI Analytics Suite — Competitive Comparison",
             "Compared to Snowflake Cortex: Databricks AI Analytics offers native MLflow integration (no export needed), open-source model support beyond LLMs, and full Spark-based feature engineering. Compared to Azure ML: Databricks provides unified data+ML in one platform eliminating data movement, superior Spark native execution, and multi-cloud flexibility. Compared to SageMaker: Better for teams already on Databricks data platform, simpler governance model, no vendor lock-in.",
             "competitive", "2026-02-01"),
            ("doc_005", "prod_003", "Governance Shield — Row and Column Security Setup",
             "Governance Shield provides Unity Catalog fine-grained access control. Row Filters: CREATE FUNCTION with RETURNS BOOLEAN, then ALTER TABLE SET ROW FILTER. Uses current_user() and is_member() for dynamic enforcement. Column Masks: CREATE FUNCTION returning masked value, then ALTER TABLE ALTER COLUMN SET MASK. Both are enforced at query time across all interfaces: SQL, Python, Genie, dashboards, and API. Audit logs captured automatically in system.access.audit.",
             "feature", "2026-01-25"),
            ("doc_006", "prod_003", "Governance Shield — Common Implementation Patterns",
             "Pattern 1 — Role-based row filter: Filter rows where department = current user department (join to HR table). Pattern 2 — Owner-based filter: Only show records where owner_email = current_user(). Pattern 3 — Column mask by group: Show sensitive column to admins, NULL to others using is_member(). Pattern 4 — ABAC with UC tags: Combine user tags with data tags for attribute-based control. Best practice: test filters with EXPLAIN to check for performance impact before applying to large tables.",
             "feature", "2026-02-05"),
            ("doc_007", "prod_004", "StreamFlow Pro — Architecture Overview",
             "StreamFlow Pro delivers sub-second latency streaming using Spark Structured Streaming with Delta Live Tables (DLT) for declarative pipeline management. Architecture: Source connectors (Kafka, Kinesis, Event Hubs, HTTP) → Bronze DLT table → Silver DLT table with quality rules → Gold aggregated Delta tables. Supports exactly-once semantics, automatic schema evolution, and built-in data quality monitoring. Typical throughput: 500K events/second per cluster.",
             "feature", "2026-01-18"),
            ("doc_008", "prod_004", "StreamFlow Pro — Kafka Integration FAQ",
             "Q: Which Kafka versions are supported? A: Apache Kafka 2.x and 3.x, Confluent Cloud, AWS MSK, Azure Event Hubs. Q: Is exactly-once delivery supported? A: Yes, with Kafka transactions enabled and checkpointing on Delta. Q: How do we handle schema evolution? A: Auto-merging enabled by default; breaking changes trigger alerts. Q: What monitoring is available? A: Databricks Observability dashboard with lag metrics, throughput, and error rates.",
             "faq", "2026-02-10"),
            ("doc_009", "prod_005", "CloudConnect Bundle — Connector Catalog",
             "CloudConnect Bundle includes 50+ certified connectors: Databases (Salesforce, SAP, Oracle, PostgreSQL, MySQL, SQL Server), Files (S3, ADLS, GCS, SFTP), SaaS (Workday, ServiceNow, Marketo, HubSpot), Streaming (Kafka, Kinesis, Pub/Sub), and BI Tools (Tableau, Power BI, Looker via JDBC/ODBC). All connectors support incremental sync, schema inference, and automatic error retry with exponential backoff.",
             "feature", "2026-01-12"),
            ("doc_010", "prod_005", "CloudConnect Bundle — Custom REST API Connector",
             "Build custom connectors using the CloudConnect REST framework: (1) Define endpoint schema in YAML. (2) Configure OAuth 2.0 or API key auth. (3) Map response fields to Delta columns. (4) Schedule incremental sync with cursor-based pagination. Example: Connecting to a custom ERP system requires endpoint URL, auth headers, response schema, and cursor field (e.g., updated_at). Full example in GitHub: databricks/cloudconnect-examples.",
             "faq", "2026-02-08"),
        ],

        # ── sales_playbooks ───────────────────────────────────────────────────
        # (playbook_id, title, content, audience, region)
        f"{CATALOG}.knowledge_base.sales_playbooks": [
            ("pb_001", "Enterprise Discovery Call Framework",
             "Discovery call structure for enterprise accounts: (1) Open with business outcome question: 'What would it mean for your team if you could reduce data pipeline failures by 80%?' (2) Identify the economic buyer and their top 3 priorities this quarter. (3) Map current state: ask about existing tools, team size, data volumes, and key pain points. (4) Quantify pain: time lost, incidents per month, cost of manual work. (5) Close with next step commitment — never leave without a specific follow-up scheduled. Target duration: 45 minutes. Pre-call research: check recent earnings calls and press releases.",
             "rep", "ALL"),
            ("pb_002", "Governance Shield Positioning Guide",
             "When to lead with Governance Shield: (1) Prospect is in Financial Services, Healthcare, or Government (regulatory drivers). (2) Recent data breach or compliance audit mentioned in discovery. (3) Multiple business units sharing data with access concerns. Key value props: (a) UC replaces 3-5 siloed access control tools with one layer. (b) Row/column security enforced at query time — no data copies needed. (c) Audit logs available in system.access.audit — no additional tooling. Objection handling: 'We have existing IAM' → UC sits above IAM and adds data-level control without replacing it.",
             "rep", "ALL"),
            ("pb_003", "Competitive Win Strategy — vs Snowflake",
             "Snowflake displacement plays: (1) ML workloads: Snowflake Cortex is limited to built-in LLMs; Databricks supports any model, framework, and custom training. Frame as: 'Do you want to be locked into Snowflake's AI roadmap?' (2) Open ecosystem: Databricks is built on open standards (Delta, MLflow, Apache Spark) with no format lock-in. (3) Total cost: Databricks separation of compute and storage with serverless auto-scaling often 30-40% lower TCO for mixed workloads. Trap question: 'How are you handling model training and deployment today?' — Snowflake has no answer for custom model training.",
             "manager", "ALL"),
            ("pb_004", "West Region Account Prioritization",
             "West region Q1 2026 priority segments: (1) Tech companies in SF Bay Area and Seattle — AI/ML platform consolidation is top initiative. Lead with AI Analytics Suite. (2) Energy companies (SunState Energy tier) — regulatory compliance and ESG reporting driving governance need. Lead with Governance Shield. (3) Retail (Pacific Retail) — real-time personalization and inventory optimization. Lead with StreamFlow Pro + AI combo. Avoid: SMB accounts under $50K ACV this quarter — focus on Enterprise expansion. Top accounts to penetrate: Global Tech Inc (expansion from DataPlatform Core to AI Suite).",
             "rep", "WEST"),
            ("pb_005", "Manager Deal Review Checklist",
             "Required before any deal above $75K enters Proposal stage: (1) Economic buyer confirmed — VP or above with budget authority. (2) Champion identified with internal selling plan. (3) Compelling event documented — why does the customer need to act by the proposed close date? (4) Competition mapped — is Snowflake, Azure, or AWS native involved? (5) Legal and procurement timeline understood. (6) Success criteria agreed in writing — what does the customer measure success by? Red flags requiring deal coaching: no champion, no compelling event, or procurement cycle longer than 60 days.",
             "manager", "ALL"),
            ("pb_006", "Renewal and Expansion Playbook",
             "60-day renewal process: Day 60 before renewal: EBR (Executive Business Review) — present ROI metrics, usage growth, and expansion roadmap. Day 45: Legal and commercial terms review — avoid last-minute surprises. Day 30: Final pricing and packaging confirmation. Day 14: Signature and processing. Expansion triggers to watch in usage dashboards: (1) Cluster utilization consistently above 80% — signal for compute expansion. (2) New user groups onboarding — signal for seat expansion. (3) New data sources connected — signal for connector add-ons. Target: 120% net revenue retention.",
             "manager", "ALL"),
        ],
    }


# ── Insert helpers ────────────────────────────────────────────────────────────

def escape(v) -> str:
    """Format a Python value as a SQL literal."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    # String — escape single quotes
    return "'" + str(v).replace("'", "''") + "'"


def insert_rows(w: WorkspaceClient, table: str, rows: list[tuple]):
    """Insert rows into a table using a single multi-row INSERT statement."""
    if not rows:
        return
    values = ",\n    ".join(
        "(" + ", ".join(escape(v) for v in row) + ")"
        for row in rows
    )
    sql(w, f"INSERT INTO {table} VALUES\n    {values}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    w = WorkspaceClient()

    print(f"Current user: {CURRENT_USER or '(not set)'}")
    print()

    # 1. Create tables
    print("Creating tables...")
    for table_name, ddl in TABLES.items():
        sql(w, ddl.strip())
        short = table_name.split(".")[-1]
        print(f"  ✓ {table_name}")
    print()

    # 2. Seed data
    print("Seeding data...")
    seed = get_seed_data(CURRENT_USER)
    for table_name, rows in seed.items():
        insert_rows(w, table_name, rows)
        short = table_name.split(".")[-1]
        print(f"  ✓ {short:<25} {len(rows):>2} rows")

    print()
    print("Done.")
    print("Next step: run 03_row_col_security.sql")


if __name__ == "__main__":
    main()
