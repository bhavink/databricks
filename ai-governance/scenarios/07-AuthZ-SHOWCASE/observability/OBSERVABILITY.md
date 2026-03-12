# E2E Observability for the AuthZ Showcase

Production observability for a multi-agent Databricks application: traces, quality scoring, cost tracking, dashboards, and alerts — unified in a single pane of glass.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [What's OOTB vs What We Built](#3-whats-ootb-vs-what-we-built)
4. [Setup Guide](#4-setup-guide)
5. [The Traces Table](#5-the-traces-table)
6. [Scorers Deep Dive](#6-scorers-deep-dive)
7. [Dashboard Guide](#7-dashboard-guide)
8. [Alerts](#8-alerts)
9. [Correlation Queries](#9-correlation-queries)
10. [Known Limitations & Gotchas](#10-known-limitations--gotchas)
11. [Files Reference](#11-files-reference)

---

## 1. Overview

The AuthZ Showcase is a multi-agent demo running on Databricks Apps. Two services collaborate at runtime:

- **AppA** (Streamlit frontend) — handles user interaction, proxies to Genie, Vector Search, UC Functions, a supervisor agent, and a custom MCP server.
- **AppB** (Custom MCP Server) — exposes three tools (`get_deal_approval_status`, `submit_deal_for_approval`, `get_crm_sync_status`) using OBO User and M2M auth patterns.

The observability layer answers four questions that matter in production:

| Question | Capability |
|---|---|
| **Is it working?** | Request volume, error rates, latency percentiles, service health |
| **Is it good?** | Automated quality scorers (safety, relevance, domain guidelines) |
| **What does it cost?** | Token consumption, DBU tracking, per-request efficiency |
| **What went wrong?** | Error correlation across trace spans, tool failures, auth pattern breakdowns |

This is not a monitoring bolt-on. Every trace, every scorer assessment, and every system metric lands in Unity Catalog Delta tables — queryable with SQL, joinable across layers, and accessible to anyone with table-level permissions.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Databricks Apps Runtime                         │
│                                                                          │
│   ┌──────────────┐         ┌──────────────────┐                         │
│   │   AppA        │         │   AppB            │                        │
│   │  (Streamlit)  │────────▶│  (Custom MCP)     │                        │
│   │               │  HTTP   │                   │                        │
│   │  service_name:│         │  service_name:    │                        │
│   │  app-a-       │         │  app-b-           │                        │
│   │  frontend     │         │  mcp-server       │                        │
│   └──────┬───────┘         └────────┬──────────┘                        │
│          │                          │                                    │
│          │  mlflow-tracing          │  mlflow-tracing                    │
│          │  set_destination()       │  set_destination()                 │
│          │                          │                                    │
└──────────┼──────────────────────────┼────────────────────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     MLflow Experiment                                     │
│  /Users/<user>/mas-155f64f7-dev-experiment                               │
│                                                                          │
│  Traces from both services land here, tagged with service_name + tool.   │
│  Independent traces (no W3C stitching) but correlated via shared         │
│  experiment and tags.                                                    │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
              enable_databricks_trace_archival()
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│            Delta Table: authz_showcase.agent_observability.traces         │
│                                                                          │
│  Syncs every ~15-20 min. Full trace data + assessments.                  │
│  Queryable via SQL. Joinable with system tables.                         │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
     ┌────────────┐   ┌──────────────┐   ┌─────────────┐
     │ Automated   │   │  Lakeview    │   │ SQL Alerts  │
     │ Scorers     │   │  Dashboard   │   │ (3 alerts)  │
     │ (5 scorers) │   │  (4 pages)   │   │             │
     └─────────────┘   └──────────────┘   └─────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
          ┌─────────────────┐   ┌──────────────────┐
          │ System Tables   │   │ Correlation       │
          │ serving.usage   │   │ Queries (SQL)     │
          │ ai_gateway      │   │ 8 widgets +       │
          │ billing          │   │ 3 alert queries   │
          └─────────────────┘   └──────────────────┘
```

**Data flow summary:**

1. AppA and AppB emit traces via `mlflow-tracing` to a shared MLflow experiment.
2. `enable_databricks_trace_archival()` syncs traces to a UC Delta table every 15-20 minutes.
3. Five automated scorers run asynchronously on production traces and write assessments back.
4. A Lakeview dashboard reads from the traces table + system tables.
5. Three SQL alerts fire on error rate spikes, latency SLA breaches, and quality drops.

---

## 3. What's OOTB vs What We Built

| Capability | Databricks Provides (OOTB) | We Configured / Built |
|---|---|---|
| **Trace collection** | MLflow experiment UI, trace viewer | `set_destination()` call in each app, `service_name` tagging, manual span management, token redaction |
| **Trace storage** | Experiment-level trace viewer | `enable_databricks_trace_archival()` to create queryable Delta table |
| **Quality scoring** | Built-in scorer framework (Safety, Relevance, Guidelines) | Registered 5 scorers with tuned sample rates; 2 custom code scorers (`response_length`, `has_auth_pattern`) |
| **System tables** | `system.serving.*`, `system.ai_gateway.*`, `system.billing.*` | Cross-layer SQL queries joining traces with system metrics |
| **Dashboards** | Lakeview dashboard framework | 4-page dashboard with 20+ widgets, deployed via `deploy_dashboard.py` |
| **Alerts** | SQL alert framework | 3 alerts (error rate, latency, quality) with tuned thresholds |
| **Async trace logging** | `MLFLOW_ENABLE_ASYNC_TRACE_LOGGING` env var | Configured in `app.yaml` with max workers=10, queue size=1000 |
| **Trace sampling** | `MLFLOW_TRACE_SAMPLING_RATIO` env var | Set to 1.0 (100%) for demo; tunable per environment |

---

## 4. Setup Guide

### Prerequisites

- Databricks workspace with Unity Catalog enabled
- A deployed MLflow experiment (created automatically on first trace)
- `mlflow[databricks]>=3.1` available in a notebook environment
- Databricks CLI profile configured (for dashboard deployment)

### Step 1: Enable Tracing in Your Apps

Both `app/app.yaml` and `mcp-server/app.yaml` include these env vars:

```yaml
env:
  - name: MLFLOW_TRACKING_URI
    value: "databricks"
  - name: MLFLOW_EXPERIMENT_NAME
    value: "/Users/<your-user>/mas-155f64f7-dev-experiment"
  - name: MLFLOW_ENABLE_ASYNC_TRACE_LOGGING
    value: "true"
  - name: MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS
    value: "10"
  - name: MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE
    value: "1000"
  - name: MLFLOW_TRACE_SAMPLING_RATIO
    value: "1.0"
  - name: SERVICE_NAME
    value: "app-a-frontend"  # or "app-b-mcp-server"
```

In application code, initialize tracing at startup:

```python
from mlflow.tracing import set_destination
from mlflow.tracing.destination import Databricks

set_destination(Databricks(experiment_name=os.getenv("MLFLOW_EXPERIMENT_NAME")))
```

> **Critical:** `set_destination()` is required when using `mlflow-tracing`. The `MLFLOW_EXPERIMENT_NAME` env var alone does not configure the destination in the lightweight package.

### Step 2: Enable Production Monitoring (Trace Archival + Scorers)

Run the `setup_observability.py` notebook in your Databricks workspace:

```python
# In a Databricks notebook:
%pip install "mlflow[databricks]>=3.1"
dbutils.library.restartPython()

# Then run the notebook cells — it will:
# 1. Enable trace archival → authz_showcase.agent_observability.traces
# 2. Register and start all 5 scorers
```

This does two things:
1. **Creates the Delta table** at `authz_showcase.agent_observability.traces` via `enable_databricks_trace_archival()`.
2. **Registers 5 automated scorers** that run asynchronously on production traces.

Both operations are idempotent — safe to re-run.

> **Critical:** The Databricks UI has an "Enable Monitoring" toggle on the experiment page. Clicking it in the UI alone does NOT create a queryable Delta table. You must call `enable_databricks_trace_archival()` programmatically.

### Step 3: Deploy the Dashboard

```bash
python3 deploy_dashboard.py --profile <your-databricks-cli-profile>
```

Options:
- `--dashboard-only` — deploy only the Lakeview dashboard
- `--alerts-only` — deploy only the SQL alerts
- No flag — deploys both

The script creates:
- A 4-page Lakeview dashboard: "AuthZ Showcase — E2E Observability"
- 3 SQL alerts with configurable notification destinations

### Step 4: Configure Alert Notification Destinations

After deploying alerts, configure where notifications go:

1. Navigate to **SQL > Alerts** in the Databricks workspace.
2. Open each alert (`Error Rate Spike`, `P95 Latency SLA Breach`, `Safety Score Drop`).
3. Click **Add Destination** and choose: Slack webhook, email, PagerDuty, or custom webhook.

This step is manual — the API does not support destination configuration programmatically.

---

## 5. The Traces Table

**Full path:** `authz_showcase.agent_observability.traces`

This table is created by `enable_databricks_trace_archival()` and syncs every ~15-20 minutes from the MLflow experiment.

### Schema Reference

| Column | Type | Description |
|---|---|---|
| `trace_id` | `STRING` | Unique trace identifier |
| `client_request_id` | `STRING` | Client-provided correlation ID |
| `request_time` | `TIMESTAMP` | When the trace started |
| `state` | `STRING` | `OK` or `ERROR` |
| `execution_duration_ms` | `DOUBLE` | End-to-end latency in milliseconds |
| `request` | `STRING` | Serialized input (JSON) |
| `response` | `STRING` | Serialized output (JSON) |
| `spans` | `ARRAY<STRUCT>` | Individual span records (name, status, timing) |
| `tags` | `MAP<STRING, STRING>` | Trace-level tags (includes `service_name`, `tool`) |
| `trace_metadata` | `MAP<STRING, STRING>` | System metadata (`mlflow.trace.user`, `mlflow.trace.session`) |
| `assessments` | `ARRAY<STRUCT>` | Scorer results (see below) |

### Assessments Struct

Each element in the `assessments` array has this structure:

| Field | Type | Notes |
|---|---|---|
| `assessments.name` | `STRING` | Scorer name (e.g., `safety_check`, `relevance_check`) |
| `assessments.feedback.value` | `STRING` | Score value (cast to DOUBLE for aggregation) |

> **Gotcha:** The field is `a.name`, NOT `a.assessment_name`. Early documentation referenced `assessment_name` — that field does not exist.

### Example Queries

```sql
-- Average safety score over last 24 hours
SELECT AVG(CAST(a.feedback.value AS DOUBLE)) AS avg_safety
FROM authz_showcase.agent_observability.traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE a.name = 'safety_check'
  AND t.request_time >= CURRENT_TIMESTAMP - INTERVAL 1 DAY;

-- Traces by service
SELECT tags['service_name'] AS service, COUNT(*) AS trace_count
FROM authz_showcase.agent_observability.traces
WHERE request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1;
```

---

## 6. Scorers Deep Dive

Five scorers run asynchronously on production traces. They read from the trace store and write assessments back — zero impact on application latency.

| Scorer | Type | Sample Rate | LLM Cost | What It Checks |
|---|---|---|---|---|
| `safety_check` | Built-in (Safety) | 100% | None | Flags unsafe, harmful, or policy-violating content |
| `relevance_check` | Built-in (RelevanceToQuery) | 50% | Moderate | Measures whether the response actually answers the question |
| `authz_guidelines_check` | Custom (Guidelines) | 30% | Yes (LLM judge) | Domain rules: auth pattern identification, PII absence, opp_id inclusion, actionable errors |
| `response_length` | Custom (Code) | 100% | None | Character count with mean/min/max aggregations; catches empty or bloated responses |
| `has_auth_pattern` | Custom (Code) | 100% | None | Boolean: does the response mention OBO, M2M, or auth_pattern? |

### Sample Rate Rationale

- **100%** for safety and code scorers — they are cheap or free.
- **50%** for relevance — uses an LLM judge, moderate cost per evaluation.
- **30%** for guidelines — custom LLM judge with 4 guidelines, higher per-evaluation cost.

### Registration Mechanics

Scorers are registered via `setup_observability.py` using a `safe_register_and_start()` helper:

```python
def safe_register_and_start(scorer_obj, name, sample_rate):
    """Register and start a scorer, skipping if already active."""
    try:
        existing = get_scorer(name=name)
        if existing.sample_rate > 0:
            return existing          # Already running, nothing to do
        else:
            return existing.start(   # Stopped — restart it
                sampling_config=ScorerSamplingConfig(sample_rate=sample_rate)
            )
    except Exception:
        pass  # Doesn't exist yet — register below

    registered = scorer_obj.register(name=name)
    return registered.start(
        sampling_config=ScorerSamplingConfig(sample_rate=sample_rate)
    )
```

This pattern is idempotent: re-running the notebook does not create duplicate scorers.

### Customizing Scorers

**Change sample rate:** Modify the rate in `setup_observability.py` and re-run. The `safe_register_and_start()` helper will restart the scorer with the new rate.

**Add a guideline:** Edit the `guidelines` list in the `authz_guidelines` Guidelines scorer:

```python
authz_guidelines = Guidelines(
    name="authz_guidelines",
    guidelines=[
        "The response must correctly identify the auth pattern used (OBO User or M2M).",
        "The response must not contain PII such as SSN or credit card numbers.",
        "If the query involves approval status, the response must include the opp_id.",
        "Error responses must include actionable hints about permissions or access.",
        # Add new guidelines here
    ],
)
```

**Add a new code scorer:** Use the `@scorer` decorator:

```python
@scorer(aggregations=["mean", "min", "max"])
def my_custom_scorer(outputs):
    """Your logic here. Return a numeric value or boolean."""
    return some_metric(outputs)

safe_register_and_start(my_custom_scorer, "my_custom_scorer", 1.0)
```

### Backfilling Historical Traces

To retroactively score traces that existed before scorers were registered:

```python
from databricks.agents.scorers import backfill_scorers

job_id = backfill_scorers(
    scorers=["safety_check", "relevance_check", "response_length", "has_auth_pattern"],
)
print(f"Backfill job: {job_id}")  # Monitor in Databricks Jobs UI
```

---

## 7. Dashboard Guide

**Dashboard name:** "AuthZ Showcase — E2E Observability"
**Deployed via:** `python3 deploy_dashboard.py --profile <profile>`

### Page 1: Operations Overview

The primary health check. Start here.

| Widget | What It Shows | When To Use It |
|---|---|---|
| 6 KPI counters | Total requests, errors, error rate, P50/P95/P99 latency | Glanceable health status |
| Request volume over time | Hourly request count (bar chart) | Spot traffic patterns, outages |
| Error rate trend | Hourly error percentage (line chart) | Detect degradation trends |
| Latency percentiles | P50/P95/P99 over time (multi-line) | SLA tracking, performance regression |
| Tool breakdown | Requests per tool (bar chart) | Understand usage distribution |
| Auth pattern distribution | OBO vs M2M usage | Verify correct auth pattern selection |
| Service state | Health by service_name | Identify which service is struggling |

### Page 2: Quality & Judges

Scorer assessments and response quality trends.

| Widget | What It Shows | When To Use It |
|---|---|---|
| Scorer summary table | All scorers with average score, sample count | Overall quality posture |
| Scores over time | Daily average per scorer (multi-line) | Detect quality regression |
| Average score bars | Bar chart of each scorer's average | Compare scorer performance |
| Response length by tool | Average response length per tool | Spot tools returning empty or bloated responses |

### Page 3: Cost & Tokens

Token consumption, DBU spend, and efficiency metrics.

| Widget | What It Shows | When To Use It |
|---|---|---|
| Daily token consumption | Input + output tokens over time | Track consumption trends |
| DBU cost | Daily serverless inference DBUs | Budget forecasting |
| Token efficiency | Avg tokens per request | Optimize prompt/response sizes |
| Latency vs response size | Scatter plot | Identify efficiency outliers |
| Serving detail table | Per-request serving metrics | Deep-dive into individual requests |

### Page 4: Error Investigation

Root cause analysis and error correlation.

| Widget | What It Shows | When To Use It |
|---|---|---|
| Errors by tool | Bar chart of error count per tool | Identify failing tools |
| Error distribution | Pie chart of error types | Understand failure modes |
| Error timeline | Errors over time (line chart) | Correlate errors with deployments/changes |
| Recent errors table | Last N errors with trace details | Active incident investigation |
| Master correlation table | Joins traces + serving + assessments | Full E2E correlation for any trace |

---

## 8. Alerts

Three SQL alerts are deployed by `deploy_dashboard.py`:

| Alert | Condition | Retrigger Interval | Severity |
|---|---|---|---|
| **Error Rate Spike** | Error rate > 5% in the last hour | 1 hour | High |
| **P95 Latency SLA Breach** | P95 latency > 5,000ms in the last hour | 1 hour | High |
| **Safety Score Drop** | Average safety score < 0.8 in the last hour | 1 hour | Critical |

### Alert SQL

**Error Rate Spike:**
```sql
SELECT
    COUNT(CASE WHEN state = 'ERROR' THEN 1 END) * 100.0 / COUNT(*) AS error_rate
FROM authz_showcase.agent_observability.traces
WHERE request_time >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
HAVING error_rate > 5.0;
```

**P95 Latency SLA Breach:**
```sql
SELECT
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_duration_ms) AS p95_ms
FROM authz_showcase.agent_observability.traces
WHERE request_time >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
    AND state = 'OK'
HAVING p95_ms > 5000;
```

**Safety Score Drop:**
```sql
SELECT
    AVG(CAST(a.feedback.value AS DOUBLE)) AS avg_safety
FROM authz_showcase.agent_observability.traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE a.name = 'safety_check'
    AND t.request_time >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
HAVING avg_safety < 0.8;
```

### Adding Notification Destinations

After deployment, configure destinations in the Databricks SQL Alerts UI:

1. Open **SQL > Alerts** in the workspace sidebar.
2. Click the alert name.
3. **Add Destination** — supported: Slack webhook, email distribution list, PagerDuty, generic webhook.

Thresholds are tunable by editing `deploy_dashboard.py` and redeploying.

---

## 9. Correlation Queries

File: `correlation_queries.sql`

This file contains 8 dashboard widget queries and 3 alert queries. All are production-ready SQL targeting concrete table/endpoint names.

| Query | Module | Purpose |
|---|---|---|
| **Widget 1: Request Volume & Error Rate** | H | Hourly request count and error percentage (7-day window) |
| **Widget 2: Latency Percentiles** | H | P50/P95/P99 by hour for successful traces (7-day window) |
| **Widget 3: Quality Scores Over Time** | H | Daily average scorer assessments via `LATERAL VIEW EXPLODE(t.assessments)` (30-day window) |
| **Widget 4: Token Consumption** | E | Daily input/output/total tokens from `system.ai_gateway.usage` (30-day window) |
| **Widget 5: Cost Tracking** | E | Daily DBU cost from `system.billing.usage` for serverless inference (30-day window) |
| **Master Correlation** | F | Joins traces with `system.serving.endpoint_usage` and `served_entities` — E2E view of quality + serving + tokens |
| **Error Correlation** | F | Filters error traces, extracts error spans via `FILTER(TRANSFORM(t.spans, ...))` |
| **Serving Endpoint Usage** | E | Per-hour serving metrics (tokens, request count, errors) from system tables |

### System Tables Referenced

| Table | What It Provides |
|---|---|
| `system.serving.endpoint_usage` | Per-request serving metrics: tokens, status codes, latency |
| `system.serving.served_entities` | Endpoint configuration: entity names, entity IDs |
| `system.ai_gateway.usage` | Token usage, latency, routing through AI Gateway |
| `system.billing.usage` | DBU cost tracking by SKU and endpoint |

---

## 10. Known Limitations & Gotchas

### mlflow-tracing vs mlflow (Lightweight vs Full)

The production apps use `mlflow-tracing` (lightweight, ~5 MB) instead of the full `mlflow` package (~150 MB). This affects what APIs are available at runtime:

| Available in `mlflow-tracing` | NOT Available in `mlflow-tracing` |
|---|---|
| `mlflow.start_span()` | `mlflow.set_experiment()` |
| `mlflow.update_current_trace()` | `mlflow.get_experiment_by_name()` |
| `mlflow.tracing.set_destination()` | `mlflow.get_tracing_context_headers_for_http_request()` |
| `@mlflow.trace` decorator | Full MLflow tracking client |

The `setup_observability.py` notebook uses `mlflow[databricks]>=3.1` (full package) because it needs `set_experiment()`, `get_experiment_by_name()`, and the scorer registration APIs. The apps themselves only need `mlflow-tracing`.

### W3C Trace Context Propagation Not Available

`mlflow.get_tracing_context_headers_for_http_request()` does not exist in `mlflow-tracing`. This means:

- AppA and AppB emit **independent traces** (not stitched into a single distributed trace).
- Both services target the same MLflow experiment, so all traces are visible together.
- Traces are correlated via `service_name` and `tool` tags, not via parent-child span relationships.

If full `mlflow` is used in a future deployment, W3C propagation can be added to produce true distributed traces.

### Token Redaction (Manual Span Management)

AppA uses `mlflow.start_span()` (not `@mlflow.trace`) for operations that handle user OAuth tokens. This allows explicit control over what gets logged:

```python
span_ctx = mlflow.start_span(name="app_a.supervisor_ask")
with span_ctx as span:
    span.set_inputs({
        "question": question,
        "user_token": "[REDACTED]",       # Never log the actual JWT
        "history": f"{len(history)} messages"
    })
```

AppB uses `@mlflow.trace` for its tool functions (which do not receive raw tokens as span inputs) and `mlflow.update_current_trace()` for trace-level tags.

### System Table Eventual Consistency

Databricks system tables (`system.serving.*`, `system.ai_gateway.*`, `system.billing.*`) have eventual consistency:

- New endpoints can take **hours to days** to appear in system tables.
- There may be a lag of 15-60 minutes for recent data.
- Queries against system tables for a newly deployed endpoint may return empty results initially.

### Assessments Struct Field Name

The assessments array uses `a.name` to access the scorer name:

```sql
-- Correct
SELECT a.name, a.feedback.value
FROM traces t LATERAL VIEW EXPLODE(t.assessments) AS a

-- WRONG — this field does not exist
SELECT a.assessment_name ...
```

### enable_databricks_trace_archival() Is Required

The Databricks UI experiment page has an "Enable Monitoring" toggle. Clicking it in the UI alone does **NOT** create the `authz_showcase.agent_observability.traces` Delta table. You must call:

```python
from mlflow.tracing.archival import enable_databricks_trace_archival

enable_databricks_trace_archival(
    delta_table_fullname="authz_showcase.agent_observability.traces",
    experiment_id=EXPERIMENT_ID,
)
```

### Scorers Are Experiment-Scoped

Scorers are registered against an MLflow experiment, not a serving endpoint. This means:

- If you create a new experiment, you must re-register scorers.
- Scorers from one experiment do not automatically apply to another.
- The `setup_observability.py` notebook hardcodes the experiment name — update it if the experiment changes.

### Archival Sync Latency

Trace archival syncs every ~15-20 minutes. This means:

- Dashboard data is not real-time — expect a 15-20 minute delay.
- Alerts evaluate on the latest synced data, not live traces.
- For real-time debugging, use the MLflow experiment UI trace viewer directly.

### startup.sh and mlflow Namespace Conflicts

The Databricks Apps runtime pre-installs `mlflow-skinny`, which conflicts with `mlflow-tracing`. Both apps use a `startup.sh` script that:

1. Uninstalls `mlflow-skinny`.
2. Force-reinstalls `mlflow-tracing` to restore shared namespace files.

If you see `ImportError` for `mlflow.tracing` after deployment, check that `startup.sh` is running and the `command` in `app.yaml` points to it.

---

## 11. Files Reference

| File | Purpose |
|---|---|
| `tracing_config.py` | Shared tracing configuration — experiment resolution, performance env vars, service tags. Imported by apps at startup. Uses `mlflow.set_experiment()` (full mlflow only). |
| `setup_observability.py` | Databricks notebook — enables trace archival to Delta table + registers all 5 scorers. Run once, safe to re-run. Requires `mlflow[databricks]>=3.1`. |
| `setup_scorers.py` | Standalone scorer registration script — alternative to `setup_observability.py` for scorer-only setup. Runnable from CLI or notebook. |
| `deploy_dashboard.py` | Deploys Lakeview dashboard (4 pages, 20+ widgets) and 3 SQL alerts via Databricks CLI. Run with `--profile <profile>`. |
| `correlation_queries.sql` | 8 dashboard widget queries + 3 alert queries. Production SQL targeting `authz_showcase.agent_observability.traces` and system tables. |
| `test_tracing_config.py` | Unit tests for `tracing_config.py` — validates experiment resolution, env var handling, error cases. Run via `pytest`. |
| `__init__.py` | Package init — module docstring only. |
| `OBSERVABILITY.md` | This document. |
