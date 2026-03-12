# Observability and Audit Reference

> **Purpose**: Canonical reference for the two-layer observability model in Databricks AI applications -- app-level traces (MLflow) and platform-level audit (`system.access.audit`). Documents the gap between them and how to bridge it.
>
> **Audience**: Field Engineers building production observability for Databricks AI apps. Security reviewers assessing audit posture.
>
> **Last updated**: 2026-03-12

---

## Table of Contents

1. [The Two-Layer Model](#1-the-two-layer-model)
2. [App-Plane Audit (MLflow Traces)](#2-app-plane-audit-mlflow-traces)
3. [Data-Plane Audit (system.access.audit)](#3-data-plane-audit-systemaccessaudit)
4. [Correlation: Bridging the Gap](#4-correlation-bridging-the-gap)
5. [Genie-Specific Observability](#5-genie-specific-observability)
6. [Known Gaps and Limitations](#6-known-gaps-and-limitations)

---

## 1. The Two-Layer Model

Databricks AI applications generate audit data in two separate planes. Neither plane alone provides the full picture.

```
+------------------------------------------------------------------+
|  APPLICATION PLANE (you build this)                               |
|                                                                   |
|  MLflow traces + custom logging                                   |
|  - Human email (from X-Forwarded-Email or user session)           |
|  - Tool calls, inputs, outputs                                    |
|  - Latency, error status                                          |
|  - Quality scores (automated scorers)                             |
|  - Token consumption estimates                                    |
|                                                                   |
|  Storage: MLflow experiment --> Delta table (via trace archival)   |
+------------------------------------------------------------------+
                              |
                   No platform-built join
                              |
+------------------------------------------------------------------+
|  DATA PLANE (platform provides this)                              |
|                                                                   |
|  system.access.audit + system tables                              |
|  - SQL queries executed, tables accessed                          |
|  - Executing identity (human email for OBO, SP UUID for M2M)     |
|  - Model serving requests, token usage                            |
|  - Genie conversations, UC connection access                      |
|                                                                   |
|  Storage: System tables in Unity Catalog                          |
+------------------------------------------------------------------+
```

**The core gap**: When an app uses M2M for SQL queries, the data plane records the SP UUID as the executing identity. The human who triggered the request is only visible in the app plane. There is no platform-built join between these two layers.

---

## 2. App-Plane Audit (MLflow Traces)

### What MLflow Traces Capture

MLflow traces record the application-level execution path. In a Databricks App context:

| Data point | How it is captured | Example |
|---|---|---|
| Human caller | `X-Forwarded-Email` header, logged as trace tag | `alice@company.com` |
| Service name | Custom tag set at trace start | `app-a-frontend`, `app-b-mcp-server` |
| Tool invoked | Span name or custom tag | `get_deal_approval_status` |
| Input/output | Span inputs and outputs | Question text, response text |
| Latency | Span duration | 1200ms |
| Error status | Span status code | `OK` or `ERROR` |
| Auth pattern used | Custom tag | `OBO User`, `M2M` |

### Persisting Traces to Delta

The MLflow experiment UI provides a trace viewer, but it is not queryable with SQL. To make traces queryable:

```python
from mlflow.tracing.archival import enable_databricks_trace_archival

enable_databricks_trace_archival(
    delta_table_fullname="my_catalog.my_schema.traces",
    experiment_id=EXPERIMENT_ID,
)
```

This creates a Delta table that syncs every 15-20 minutes. The table includes trace metadata, span details, and scorer assessments (if configured).

**Important**: The Databricks UI "Enable Monitoring" toggle does NOT create a queryable Delta table. You must call `enable_databricks_trace_archival()` programmatically.

### Automated Quality Scoring

MLflow supports automated scorers that run asynchronously on production traces:

| Scorer type | Cost | Use case |
|---|---|---|
| Built-in Safety | Free | Flags unsafe, harmful, or policy-violating content |
| Built-in RelevanceToQuery | Moderate (LLM judge) | Measures whether response answers the question |
| Custom Guidelines | Higher (LLM judge) | Domain-specific rules (auth pattern correctness, PII absence) |
| Custom Code | Free | Deterministic checks (response length, regex patterns) |

Scorers write assessments back to the trace. These appear in the `assessments` array in the Delta table.

### Key Schema Fields

| Column | Type | Description |
|---|---|---|
| `trace_id` | STRING | Unique trace identifier |
| `request_time` | TIMESTAMP | When the trace started |
| `state` | STRING | `OK` or `ERROR` |
| `execution_duration_ms` | DOUBLE | End-to-end latency |
| `tags` | MAP | Includes `service_name`, `tool`, custom tags |
| `assessments` | ARRAY | Scorer results; access with `a.name` and `a.feedback.value` |

**Gotcha**: The assessment field is `a.name`, NOT `a.assessment_name`. Early documentation referenced `assessment_name` -- that field does not exist.

---

## 3. Data-Plane Audit (system.access.audit)

### What System Tables Capture

Databricks system tables record platform-level operations automatically:

| Table | What it provides |
|---|---|
| `system.access.audit` | All API calls: SQL queries, table access, UC operations, Genie conversations |
| `system.serving.endpoint_usage` | Per-request serving metrics: tokens, status codes, latency |
| `system.serving.served_entities` | Endpoint configuration: entity names, entity IDs |
| `system.ai_gateway.usage` | Token usage and routing through AI Gateway |
| `system.billing.usage` | DBU cost tracking by SKU and endpoint |

### Identity in Audit Records

The critical question: whose identity appears in `system.access.audit`?

| Service | Auth pattern | `user_identity.email` in audit |
|---|---|---|
| Genie Space | OBO | Human email |
| SQL Warehouse | OBO (with `sql` scope via UI) | Human email |
| SQL Warehouse | M2M | SP UUID |
| Agent Bricks | OBO | Human email |
| Agent Bricks | Automatic passthrough | SP UUID |
| UC Connection access | Caller identity | Whoever called the proxy |

### Useful Audit Queries

**Who accessed what table in the last 7 days:**

```sql
SELECT
    user_identity.email,
    request_params.full_name_arg AS table_accessed,
    COUNT(*) as query_count,
    DATE(event_time) as query_date
FROM system.access.audit
WHERE action_name = 'commandSubmit'
  AND request_params.full_name_arg LIKE 'my_catalog%'
  AND datediff(now(), event_time) <= 7
GROUP BY user_identity.email, request_params.full_name_arg, DATE(event_time)
ORDER BY query_count DESC;
```

**Failed access attempts (permission denied):**

```sql
SELECT
    user_identity.email,
    request_params.full_name_arg AS table_name,
    response.status_code,
    event_time
FROM system.access.audit
WHERE response.status_code = 403
  AND datediff(now(), event_time) <= 7
ORDER BY event_time DESC;
```

### System Table Eventual Consistency

System tables have eventual consistency:
- New endpoints can take hours to days to appear
- Recent data may lag by 15-60 minutes
- Queries for newly deployed endpoints may return empty results initially

---

## 4. Correlation: Bridging the Gap

### The Problem

A single user interaction may generate:
- An MLflow trace with the human's email and tool calls (app plane)
- Multiple `system.access.audit` entries with the SP UUID for M2M SQL (data plane)
- A Genie audit entry with the human's email (data plane)

There is no built-in key to join these records.

### Manual Correlation Strategy

1. **Generate a `trace_id`** at the agent or app entry point
2. **Pass it through tool calls** as a parameter or context variable
3. **Log it in MLflow traces** as a trace tag
4. **Include it in SQL comments** so it appears in the audit log query text
5. **Join** app-level and platform-level audit on the shared `trace_id` or on timestamp windows

```python
# Example: Include trace_id in SQL query comment for audit correlation
trace_id = mlflow.get_current_active_span().trace_id
sql = f"""
    /* trace_id={trace_id} caller={caller_email} */
    SELECT * FROM catalog.schema.table
    WHERE user_email = '{caller_email}'
"""
```

### Cross-Layer Correlation Query

```sql
-- Join MLflow traces with serving metrics
SELECT
    t.trace_id,
    t.tags['service_name'] AS service,
    t.execution_duration_ms,
    t.state,
    s.total_tokens,
    s.input_tokens,
    s.output_tokens
FROM my_catalog.my_schema.traces t
LEFT JOIN system.serving.endpoint_usage s
    ON t.trace_id = s.databricks_request_id
WHERE t.request_time >= CURRENT_DATE - INTERVAL 7 DAYS;
```

### Alerting

Three alert types are recommended for production:

| Alert | Condition | Severity |
|---|---|---|
| Error rate spike | Error rate > 5% in the last hour | High |
| Latency SLA breach | P95 latency > 5000ms in the last hour | High |
| Quality score drop | Average safety score < 0.8 in the last hour | Critical |

These can be implemented as SQL alerts in Databricks with configurable notification destinations (Slack, email, PagerDuty).

---

## 5. Genie-Specific Observability

### Platform Audit for Genie

Genie conversations are captured in `system.access.audit` under the `aibiGenie` service name. Key events:

| Event | What it captures |
|---|---|
| Conversation start | User email, Genie space ID |
| Query execution | Generated SQL, table accesses |
| Response delivery | Result metadata |

### Genie Monitoring Suite

The `audit-logging/genie-aibi/` directory contains a complete monitoring solution:

- **Conversation activity tracking**: Daily trends, user engagement metrics
- **User activity monitoring**: Email mapping, per-user query counts
- **Query insights**: Generated SQL parsing, performance metrics
- **Real-time alerting**: Failure detection, inactive space alerts, slow query alerts
- **Delta streaming**: Near-real-time monitoring via streaming architecture

For the full Genie monitoring implementation, see [audit-logging/genie-aibi/](../audit-logging/genie-aibi/).

### Genie vs App-Level Observability

| Aspect | Genie (platform audit) | App-level (MLflow traces) |
|---|---|---|
| Identity | Always human email (OBO) | Human email from X-Forwarded-Email |
| SQL queries | Generated SQL visible in audit | Not captured unless you log it |
| Quality scoring | Not available | Configurable via MLflow scorers |
| Latency tracking | Available via system tables | Available via trace spans |
| Cost tracking | Via system.billing.usage | Via system.ai_gateway.usage |

---

## 6. Known Gaps and Limitations

### No Platform-Built Correlation

The biggest gap: there is no built-in way to join MLflow traces with `system.access.audit` entries for the same user request. You must build this correlation yourself using shared identifiers (trace IDs, timestamps, SQL comments).

### W3C Trace Context Not Propagated

When using `mlflow-tracing` (the lightweight package used in Databricks Apps), W3C trace context headers are not available. This means:

- Multi-service apps (e.g., Streamlit + MCP server) emit independent traces
- Traces are correlated via shared experiment and tags, not parent-child spans
- If full `mlflow` is used, W3C propagation can be added for true distributed tracing

### Trace Archival Lag

The Delta table created by `enable_databricks_trace_archival()` syncs every 15-20 minutes. This means:
- Dashboard data is not real-time
- Alerts evaluate on synced data, not live traces
- For real-time debugging, use the MLflow experiment UI trace viewer

### mlflow-tracing vs mlflow

Production Databricks Apps use `mlflow-tracing` (~5 MB) instead of full `mlflow` (~150 MB). Key differences:

| Available in `mlflow-tracing` | NOT available |
|---|---|
| `mlflow.start_span()` | `mlflow.set_experiment()` |
| `mlflow.update_current_trace()` | Scorer registration APIs |
| `set_destination()` | `get_tracing_context_headers_for_http_request()` |

Scorer registration and trace archival setup require `mlflow[databricks]>=3.1` (full package), run from a notebook.

### Scorer Scope

Scorers are registered against an MLflow experiment, not a serving endpoint. If you create a new experiment, you must re-register scorers.

---

## Related Documents

- [Identity and Auth Reference](identity-and-auth-reference.md) -- Auth patterns, token flows, identity models
- [OBO vs M2M Decision Matrix](obo-vs-m2m-decision-matrix.md) -- Auth pattern selection with audit implications
- [scenarios/07-AuthZ-SHOWCASE/observability/OBSERVABILITY.md](../scenarios/07-AuthZ-SHOWCASE/observability/OBSERVABILITY.md) -- Complete implementation guide for app-level observability (scorers, dashboard, alerts)
- [audit-logging/genie-aibi/](../audit-logging/genie-aibi/) -- Genie-specific monitoring and analytics suite
- [scenarios/07-AuthZ-SHOWCASE/docs/IDENTITY-AND-AUDIT-ARCHITECTURE.md](../scenarios/07-AuthZ-SHOWCASE/docs/IDENTITY-AND-AUDIT-ARCHITECTURE.md) -- Full 16-service identity map and gap analysis
