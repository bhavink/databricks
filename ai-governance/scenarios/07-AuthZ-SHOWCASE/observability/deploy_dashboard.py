#!/usr/bin/env python3
"""
Deploy E2E Observability Dashboard + SQL Alerts for AuthZ Showcase.

Creates a production-grade Lakeview dashboard with 4 pages:
  1. Operations Overview — KPIs, request volume, error rates, latency
  2. Quality & Judges — Scorer assessments, guidelines compliance, safety
  3. Cost & Tokens — Token consumption, DBU cost, per-request efficiency
  4. Error Investigation — Error correlation, failure breakdown, recent errors

Also creates 3 SQL Alerts:
  - Error rate spike (>5% in last hour)
  - P95 latency SLA breach (>5s)
  - Safety score drop (<0.8 avg)

Usage:
    python3 deploy_dashboard.py --profile adb-wx1
    python3 deploy_dashboard.py --profile adb-wx1 --alerts-only
    python3 deploy_dashboard.py --profile adb-wx1 --dashboard-only
"""

import argparse
import json
import subprocess
import sys

# ── Config ────────────────────────────────────────────────────────────────────
WAREHOUSE_ID = "093d4ec27ed4bdee"
PARENT_PATH = "/Users/bhavin.kukadia@databricks.com"
DASHBOARD_NAME = "AuthZ Showcase — E2E Observability"
TRACES_TABLE = "authz_showcase.agent_observability.traces"
ENDPOINT_NAME = "mas-155f64f7-endpoint"

# ── Color Palette (Databricks-inspired, high contrast) ────────────────────────
C_GREEN   = "#00A972"
C_RED     = "#FF3621"
C_BLUE    = "#137CBD"
C_AMBER   = "#FFAB00"
C_PURPLE  = "#8F6CC6"
C_TEAL    = "#00B8D9"
C_PINK    = "#AB4057"
C_GRAY    = "#919191"
C_LIME    = "#99DDB4"
C_CORAL   = "#FCA4A1"
PALETTE = [C_BLUE, C_GREEN, C_AMBER, C_RED, C_PURPLE, C_TEAL, C_PINK, C_GRAY, C_LIME, C_CORAL]


# ── Dashboard Builder (inline, no import dependency) ──────────────────────────

def _uid():
    import uuid
    return uuid.uuid4().hex[:8]


def build_dashboard() -> dict:
    """Build the full 4-page observability dashboard."""

    datasets = []
    pages = []

    def ds(name, display, sql):
        datasets.append({"name": name, "displayName": display, "queryLines": [sql]})
        return name

    # ── Datasets ──────────────────────────────────────────────────────────────

    ds("kpi_totals", "KPI Totals", f"""
SELECT
    COUNT(*) AS total_traces,
    COUNT(CASE WHEN state = 'OK' THEN 1 END) AS success_count,
    COUNT(CASE WHEN state = 'ERROR' THEN 1 END) AS error_count,
    ROUND(COUNT(CASE WHEN state = 'ERROR' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS error_rate_pct,
    ROUND(AVG(execution_duration_ms), 0) AS avg_latency_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_duration_ms), 0) AS p95_latency_ms,
    COUNT(DISTINCT tags['tool']) AS unique_tools,
    COUNT(DISTINCT trace_metadata['mlflow.trace.user']) AS unique_users
FROM {TRACES_TABLE}
WHERE request_time >= CURRENT_DATE - INTERVAL 7 DAYS
""")

    ds("hourly_volume", "Hourly Request Volume", f"""
SELECT
    date_trunc('hour', request_time) AS hour,
    COUNT(*) AS total_requests,
    COUNT(CASE WHEN state = 'ERROR' THEN 1 END) AS errors,
    COUNT(CASE WHEN state = 'OK' THEN 1 END) AS successes
FROM {TRACES_TABLE}
WHERE request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1
ORDER BY 1
""")

    ds("hourly_error_rate", "Hourly Error Rate", f"""
SELECT
    date_trunc('hour', request_time) AS hour,
    ROUND(COUNT(CASE WHEN state = 'ERROR' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS error_rate_pct
FROM {TRACES_TABLE}
WHERE request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1
ORDER BY 1
""")

    ds("latency_percentiles", "Latency Percentiles", f"""
SELECT
    date_trunc('hour', request_time) AS hour,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY execution_duration_ms), 0) AS p50_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_duration_ms), 0) AS p95_ms,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY execution_duration_ms), 0) AS p99_ms
FROM {TRACES_TABLE}
WHERE request_time >= CURRENT_DATE - INTERVAL 7 DAYS AND state = 'OK'
GROUP BY 1
ORDER BY 1
""")

    ds("by_tool", "Requests by Tool", f"""
SELECT
    COALESCE(tags['tool'], '(supervisor)') AS tool_name,
    COUNT(*) AS request_count,
    ROUND(AVG(execution_duration_ms), 0) AS avg_latency_ms,
    COUNT(CASE WHEN state = 'ERROR' THEN 1 END) AS errors
FROM {TRACES_TABLE}
WHERE request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1
ORDER BY 2 DESC
""")

    ds("by_service", "Requests by Service", f"""
SELECT
    COALESCE(tags['service_name'], 'unknown') AS service,
    state,
    COUNT(*) AS request_count
FROM {TRACES_TABLE}
WHERE request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1, 2
ORDER BY 3 DESC
""")

    ds("by_auth_pattern", "Auth Pattern Distribution", f"""
SELECT
    CASE
        WHEN response LIKE '%OBO User%' THEN 'OBO User'
        WHEN response LIKE '%M2M fallback%' THEN 'M2M Fallback'
        WHEN response LIKE '%M2M (via UC proxy)%' THEN 'M2M (UC Proxy)'
        WHEN response LIKE '%stored bearer%' OR response LIKE '%SP identity%' THEN 'SP (Bearer Token)'
        ELSE 'Other/Unknown'
    END AS auth_pattern,
    COUNT(*) AS request_count
FROM {TRACES_TABLE}
WHERE request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1
ORDER BY 2 DESC
""")

    # Quality / Scorers
    ds("scorer_daily", "Daily Scorer Averages", f"""
SELECT
    date_trunc('day', t.request_time) AS day,
    a.name AS scorer_name,
    ROUND(AVG(CAST(a.feedback.value AS DOUBLE)), 3) AS avg_score,
    COUNT(*) AS sample_count
FROM {TRACES_TABLE} t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.request_time >= CURRENT_DATE - INTERVAL 30 DAYS
    AND a.feedback.value IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2
""")

    ds("scorer_summary", "Scorer Summary", f"""
SELECT
    a.name AS scorer,
    COUNT(*) AS samples,
    ROUND(AVG(CAST(a.feedback.value AS DOUBLE)), 3) AS avg_score,
    ROUND(MIN(CAST(a.feedback.value AS DOUBLE)), 3) AS min_score,
    ROUND(MAX(CAST(a.feedback.value AS DOUBLE)), 3) AS max_score
FROM {TRACES_TABLE} t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.request_time >= CURRENT_DATE - INTERVAL 30 DAYS
    AND a.feedback.value IS NOT NULL
GROUP BY 1
ORDER BY 3
""")

    ds("guideline_compliance", "AuthZ Guidelines Compliance", f"""
SELECT
    a.name AS guideline,
    ROUND(AVG(CASE WHEN CAST(a.feedback.value AS DOUBLE) >= 0.5 THEN 1.0 ELSE 0.0 END) * 100, 1) AS pass_rate_pct,
    COUNT(*) AS samples
FROM {TRACES_TABLE} t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE a.name = 'authz_guidelines_check'
    AND t.request_time >= CURRENT_DATE - INTERVAL 30 DAYS
    AND a.feedback.value IS NOT NULL
GROUP BY 1
""")

    ds("response_length_stats", "Response Length Stats", f"""
SELECT
    COALESCE(tags['tool'], '(supervisor)') AS tool_name,
    ROUND(AVG(LENGTH(response)), 0) AS avg_response_len,
    MIN(LENGTH(response)) AS min_response_len,
    MAX(LENGTH(response)) AS max_response_len,
    COUNT(*) AS samples
FROM {TRACES_TABLE}
WHERE request_time >= CURRENT_DATE - INTERVAL 30 DAYS AND state = 'OK'
GROUP BY 1
ORDER BY 2 DESC
""")

    # Cost & Tokens
    ds("daily_tokens", "Daily Token Usage", f"""
SELECT
    date_trunc('day', event_time) AS day,
    SUM(input_tokens) AS input_tokens,
    SUM(output_tokens) AS output_tokens,
    SUM(total_tokens) AS total_tokens
FROM system.ai_gateway.usage
WHERE endpoint_name = '{ENDPOINT_NAME}'
    AND event_time >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY 1
ORDER BY 1
""")

    ds("daily_cost", "Daily DBU Cost", f"""
SELECT
    usage_date,
    ROUND(SUM(usage_quantity), 2) AS total_dbus
FROM system.billing.usage
WHERE sku_name LIKE '%SERVERLESS_REAL_TIME_INFERENCE%'
    AND usage_metadata.endpoint_name = '{ENDPOINT_NAME}'
    AND usage_date >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY 1
ORDER BY 1
""")

    ds("serving_hourly", "Serving Endpoint Hourly", f"""
SELECT
    date_trunc('hour', eu.request_time) AS hour,
    COUNT(*) AS total_requests,
    SUM(eu.input_token_count) AS input_tokens,
    SUM(eu.output_token_count) AS output_tokens,
    ROUND(AVG(eu.input_token_count + eu.output_token_count), 0) AS avg_tokens_per_req,
    COUNT(CASE WHEN eu.status_code != 200 THEN 1 END) AS errors
FROM system.serving.endpoint_usage eu
JOIN system.serving.served_entities se ON eu.served_entity_id = se.served_entity_id
WHERE se.endpoint_name = '{ENDPOINT_NAME}'
    AND eu.request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1
ORDER BY 1
""")

    ds("token_efficiency", "Token Efficiency by Tool", f"""
SELECT
    COALESCE(t.tags['tool'], '(supervisor)') AS tool_name,
    ROUND(AVG(t.execution_duration_ms), 0) AS avg_latency_ms,
    COUNT(*) AS request_count,
    ROUND(AVG(LENGTH(t.response)), 0) AS avg_response_size
FROM {TRACES_TABLE} t
WHERE t.request_time >= CURRENT_DATE - INTERVAL 7 DAYS AND t.state = 'OK'
GROUP BY 1
ORDER BY 2 DESC
""")

    # Errors
    ds("error_by_tool", "Errors by Tool", f"""
SELECT
    COALESCE(tags['tool'], '(unknown)') AS tool_name,
    COUNT(*) AS error_count
FROM {TRACES_TABLE}
WHERE state = 'ERROR' AND request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1
ORDER BY 2 DESC
""")

    ds("error_by_service", "Errors by Service", f"""
SELECT
    COALESCE(tags['service_name'], 'unknown') AS service,
    COUNT(*) AS error_count
FROM {TRACES_TABLE}
WHERE state = 'ERROR' AND request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1
ORDER BY 2 DESC
""")

    ds("recent_errors", "Recent Errors", f"""
SELECT
    request_time,
    trace_id,
    COALESCE(tags['service_name'], 'unknown') AS service,
    COALESCE(tags['tool'], '(unknown)') AS tool,
    trace_metadata['mlflow.trace.user'] AS user_id,
    execution_duration_ms AS latency_ms,
    SUBSTRING(response, 1, 200) AS response_preview
FROM {TRACES_TABLE}
WHERE state = 'ERROR' AND request_time >= CURRENT_DATE - INTERVAL 7 DAYS
ORDER BY request_time DESC
LIMIT 50
""")

    ds("error_timeline", "Error Timeline", f"""
SELECT
    date_trunc('hour', request_time) AS hour,
    COALESCE(tags['tool'], '(unknown)') AS tool_name,
    COUNT(*) AS error_count
FROM {TRACES_TABLE}
WHERE state = 'ERROR' AND request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1, 2
ORDER BY 1
""")

    ds("master_correlation", "Master Correlation", f"""
WITH traces AS (
    SELECT trace_id, client_request_id, request_time, state,
           execution_duration_ms, tags, trace_metadata, assessments,
           SUBSTRING(request, 1, 150) AS request_preview,
           SUBSTRING(response, 1, 150) AS response_preview
    FROM {TRACES_TABLE}
    WHERE request_time >= CURRENT_DATE - INTERVAL 1 DAY
)
SELECT
    t.trace_id,
    t.state AS status,
    t.execution_duration_ms AS latency_ms,
    t.tags['service_name'] AS service,
    t.tags['tool'] AS tool,
    t.trace_metadata['mlflow.trace.user'] AS user_id,
    SIZE(t.assessments) AS num_assessments,
    t.request_preview,
    t.response_preview,
    t.request_time
FROM traces t
ORDER BY t.request_time DESC
LIMIT 100
""")

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1: Operations Overview
    # ══════════════════════════════════════════════════════════════════════════
    p1_layout = []

    def w(spec, pos):
        p1_layout.append({"widget": {"name": _uid(), **spec}, "position": pos})

    # ── KPI Row (y=0, height=2) ───────────────────────────────────────────
    for i, (field, label, agg) in enumerate([
        ("total_traces", "Total Requests (7d)", "SUM"),
        ("error_rate_pct", "Error Rate %", "SUM"),
        ("avg_latency_ms", "Avg Latency (ms)", "SUM"),
        ("p95_latency_ms", "P95 Latency (ms)", "SUM"),
        ("unique_tools", "Active Tools", "SUM"),
        ("unique_users", "Unique Users", "SUM"),
    ]):
        vn = f"sum({field})" if agg == "SUM" else f"count(*)"
        ve = f"SUM(`{field}`)" if agg == "SUM" else "COUNT(`*`)"
        w({
            "queries": [{"name": "main_query", "query": {
                "datasetName": "kpi_totals",
                "fields": [{"name": vn, "expression": ve}],
                "disaggregated": True
            }}],
            "spec": {
                "version": 2, "widgetType": "counter",
                "encodings": {"value": {"fieldName": vn, "displayName": label}},
                "frame": {"showTitle": True, "title": label}
            }
        }, {"x": i, "y": 0, "width": 1, "height": 2})

    # ── Request Volume + Error Rate (y=2) ─────────────────────────────────
    w({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "hourly_volume",
            "fields": [
                {"name": "hour", "expression": "`hour`"},
                {"name": "successes", "expression": "`successes`"},
                {"name": "errors", "expression": "`errors`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "bar",
            "encodings": {
                "x": {"fieldName": "hour", "scale": {"type": "temporal"}, "displayName": "Hour"},
                "y": {"fieldName": "successes", "scale": {"type": "quantitative"}, "displayName": "Successes"},
            },
            "frame": {"showTitle": True, "title": "Request Volume (Hourly)"},
            "mark": {"colors": [C_BLUE, C_RED]}
        }
    }, {"x": 0, "y": 2, "width": 4, "height": 4})

    # Error Rate Line
    w({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "hourly_error_rate",
            "fields": [
                {"name": "hour", "expression": "`hour`"},
                {"name": "error_rate_pct", "expression": "`error_rate_pct`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "line",
            "encodings": {
                "x": {"fieldName": "hour", "scale": {"type": "temporal"}, "displayName": "Hour"},
                "y": {"fieldName": "error_rate_pct", "scale": {"type": "quantitative"}, "displayName": "Error Rate %"},
            },
            "frame": {"showTitle": True, "title": "Error Rate % (Hourly)"},
            "mark": {"colors": [C_RED]}
        }
    }, {"x": 4, "y": 2, "width": 2, "height": 4})

    # ── Latency Percentiles (y=6) ─────────────────────────────────────────
    w({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "latency_percentiles",
            "fields": [
                {"name": "hour", "expression": "`hour`"},
                {"name": "p50_ms", "expression": "`p50_ms`"},
                {"name": "p95_ms", "expression": "`p95_ms`"},
                {"name": "p99_ms", "expression": "`p99_ms`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "line",
            "encodings": {
                "x": {"fieldName": "hour", "scale": {"type": "temporal"}, "displayName": "Hour"},
                "y": {"fieldName": "p50_ms", "scale": {"type": "quantitative"}, "displayName": "Latency (ms)"},
            },
            "frame": {"showTitle": True, "title": "Latency Percentiles (P50 / P95 / P99)"},
            "mark": {"colors": [C_GREEN, C_AMBER, C_RED]}
        }
    }, {"x": 0, "y": 6, "width": 3, "height": 4})

    # ── By Tool Bar Chart (y=6) ───────────────────────────────────────────
    w({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "by_tool",
            "fields": [
                {"name": "tool_name", "expression": "`tool_name`"},
                {"name": "request_count", "expression": "`request_count`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "bar",
            "encodings": {
                "x": {"fieldName": "tool_name", "scale": {"type": "categorical", "sort": {"by": "y-reversed"}}, "displayName": "Tool"},
                "y": {"fieldName": "request_count", "scale": {"type": "quantitative"}, "displayName": "Requests"},
                "label": {"show": True}
            },
            "frame": {"showTitle": True, "title": "Requests by Tool"},
            "mark": {"colors": PALETTE}
        }
    }, {"x": 3, "y": 6, "width": 3, "height": 4})

    # ── Auth Pattern + Service Breakdown (y=10) ───────────────────────────
    w({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "by_auth_pattern",
            "fields": [
                {"name": "count(*)", "expression": "SUM(`request_count`)"},
                {"name": "auth_pattern", "expression": "`auth_pattern`"},
            ],
            "disaggregated": False
        }}],
        "spec": {
            "version": 3, "widgetType": "pie",
            "encodings": {
                "angle": {"fieldName": "count(*)", "scale": {"type": "quantitative"}, "displayName": "Requests"},
                "color": {"fieldName": "auth_pattern", "scale": {"type": "categorical"}, "displayName": "Auth Pattern"},
            },
            "frame": {"showTitle": True, "title": "Auth Pattern Distribution"},
        }
    }, {"x": 0, "y": 10, "width": 3, "height": 4})

    w({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "by_service",
            "fields": [
                {"name": "count(*)", "expression": "SUM(`request_count`)"},
                {"name": "service", "expression": "`service`"},
                {"name": "state", "expression": "`state`"},
            ],
            "disaggregated": False
        }}],
        "spec": {
            "version": 3, "widgetType": "bar",
            "encodings": {
                "x": {"fieldName": "service", "scale": {"type": "categorical"}, "displayName": "Service"},
                "y": {"fieldName": "count(*)", "scale": {"type": "quantitative"}, "displayName": "Requests"},
                "color": {"fieldName": "state", "scale": {"type": "categorical"}, "displayName": "State"},
                "label": {"show": True}
            },
            "frame": {"showTitle": True, "title": "Requests by Service & State"},
            "mark": {"colors": [C_GREEN, C_RED]}
        }
    }, {"x": 3, "y": 10, "width": 3, "height": 4})

    pages.append({
        "name": _uid(), "displayName": "Operations Overview",
        "pageType": "PAGE_TYPE_CANVAS", "layout": p1_layout
    })

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2: Quality & Judges
    # ══════════════════════════════════════════════════════════════════════════
    p2_layout = []

    def w2(spec, pos):
        p2_layout.append({"widget": {"name": _uid(), **spec}, "position": pos})

    # Scorer Summary Table (y=0)
    w2({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "scorer_summary",
            "fields": [
                {"name": "scorer", "expression": "`scorer`"},
                {"name": "samples", "expression": "`samples`"},
                {"name": "avg_score", "expression": "`avg_score`"},
                {"name": "min_score", "expression": "`min_score`"},
                {"name": "max_score", "expression": "`max_score`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 1, "widgetType": "table",
            "encodings": {"columns": [
                {"fieldName": "scorer", "type": "string", "displayAs": "string", "title": "Scorer", "displayName": "Scorer", "order": 100000, "alignContent": "left"},
                {"fieldName": "samples", "type": "integer", "displayAs": "number", "title": "Samples", "displayName": "Samples", "order": 100001, "alignContent": "right"},
                {"fieldName": "avg_score", "type": "float", "displayAs": "number", "title": "Avg Score", "displayName": "Avg Score", "order": 100002, "alignContent": "right"},
                {"fieldName": "min_score", "type": "float", "displayAs": "number", "title": "Min", "displayName": "Min", "order": 100003, "alignContent": "right"},
                {"fieldName": "max_score", "type": "float", "displayAs": "number", "title": "Max", "displayName": "Max", "order": 100004, "alignContent": "right"},
            ]},
            "frame": {"showTitle": True, "title": "Scorer Summary (30d)"}
        }
    }, {"x": 0, "y": 0, "width": 6, "height": 4})

    # Quality Scores Over Time (y=4)
    w2({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "scorer_daily",
            "fields": [
                {"name": "day", "expression": "`day`"},
                {"name": "avg_score", "expression": "`avg_score`"},
                {"name": "scorer_name", "expression": "`scorer_name`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "line",
            "encodings": {
                "x": {"fieldName": "day", "scale": {"type": "temporal"}, "displayName": "Day"},
                "y": {"fieldName": "avg_score", "scale": {"type": "quantitative"}, "displayName": "Avg Score"},
                "color": {"fieldName": "scorer_name", "scale": {"type": "categorical"}, "displayName": "Scorer"},
            },
            "frame": {"showTitle": True, "title": "Quality Scores Over Time"},
            "mark": {"colors": PALETTE}
        }
    }, {"x": 0, "y": 4, "width": 4, "height": 4})

    # Scorer Bar Chart (y=4)
    w2({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "scorer_summary",
            "fields": [
                {"name": "scorer", "expression": "`scorer`"},
                {"name": "avg_score", "expression": "`avg_score`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "bar",
            "encodings": {
                "x": {"fieldName": "scorer", "scale": {"type": "categorical"}, "displayName": "Scorer"},
                "y": {"fieldName": "avg_score", "scale": {"type": "quantitative"}, "displayName": "Avg Score"},
                "label": {"show": True}
            },
            "frame": {"showTitle": True, "title": "Average Score by Scorer"},
            "mark": {"colors": [C_GREEN, C_BLUE, C_AMBER, C_PURPLE, C_TEAL]}
        }
    }, {"x": 4, "y": 4, "width": 2, "height": 4})

    # Response Length by Tool (y=8)
    w2({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "response_length_stats",
            "fields": [
                {"name": "tool_name", "expression": "`tool_name`"},
                {"name": "avg_response_len", "expression": "`avg_response_len`"},
                {"name": "samples", "expression": "`samples`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "bar",
            "encodings": {
                "x": {"fieldName": "tool_name", "scale": {"type": "categorical", "sort": {"by": "y-reversed"}}, "displayName": "Tool"},
                "y": {"fieldName": "avg_response_len", "scale": {"type": "quantitative"}, "displayName": "Avg Response Length (chars)"},
                "label": {"show": True}
            },
            "frame": {"showTitle": True, "title": "Avg Response Length by Tool"},
            "mark": {"colors": [C_TEAL]}
        }
    }, {"x": 0, "y": 8, "width": 6, "height": 4})

    pages.append({
        "name": _uid(), "displayName": "Quality & Judges",
        "pageType": "PAGE_TYPE_CANVAS", "layout": p2_layout
    })

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3: Cost & Tokens
    # ══════════════════════════════════════════════════════════════════════════
    p3_layout = []

    def w3(spec, pos):
        p3_layout.append({"widget": {"name": _uid(), **spec}, "position": pos})

    # Daily Token Usage (y=0)
    w3({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "daily_tokens",
            "fields": [
                {"name": "day", "expression": "`day`"},
                {"name": "input_tokens", "expression": "`input_tokens`"},
                {"name": "output_tokens", "expression": "`output_tokens`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "bar",
            "encodings": {
                "x": {"fieldName": "day", "scale": {"type": "temporal"}, "displayName": "Day"},
                "y": {"fieldName": "input_tokens", "scale": {"type": "quantitative"}, "displayName": "Tokens"},
                "label": {"show": False}
            },
            "frame": {"showTitle": True, "title": "Daily Token Consumption"},
            "mark": {"colors": [C_BLUE, C_AMBER]}
        }
    }, {"x": 0, "y": 0, "width": 4, "height": 4})

    # Daily DBU Cost (y=0)
    w3({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "daily_cost",
            "fields": [
                {"name": "usage_date", "expression": "`usage_date`"},
                {"name": "total_dbus", "expression": "`total_dbus`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "line",
            "encodings": {
                "x": {"fieldName": "usage_date", "scale": {"type": "temporal"}, "displayName": "Date"},
                "y": {"fieldName": "total_dbus", "scale": {"type": "quantitative"}, "displayName": "DBUs"},
            },
            "frame": {"showTitle": True, "title": "Daily DBU Cost (Model Serving)"},
            "mark": {"colors": [C_GREEN]}
        }
    }, {"x": 4, "y": 0, "width": 2, "height": 4})

    # Serving Endpoint Hourly (y=4)
    w3({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "serving_hourly",
            "fields": [
                {"name": "hour", "expression": "`hour`"},
                {"name": "total_requests", "expression": "`total_requests`"},
                {"name": "avg_tokens_per_req", "expression": "`avg_tokens_per_req`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "line",
            "encodings": {
                "x": {"fieldName": "hour", "scale": {"type": "temporal"}, "displayName": "Hour"},
                "y": {"fieldName": "avg_tokens_per_req", "scale": {"type": "quantitative"}, "displayName": "Avg Tokens/Request"},
            },
            "frame": {"showTitle": True, "title": "Token Efficiency (Avg Tokens per Request)"},
            "mark": {"colors": [C_PURPLE]}
        }
    }, {"x": 0, "y": 4, "width": 3, "height": 4})

    # Latency vs Response Size by Tool (y=4)
    w3({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "token_efficiency",
            "fields": [
                {"name": "tool_name", "expression": "`tool_name`"},
                {"name": "avg_latency_ms", "expression": "`avg_latency_ms`"},
                {"name": "avg_response_size", "expression": "`avg_response_size`"},
                {"name": "request_count", "expression": "`request_count`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "scatter",
            "encodings": {
                "x": {"fieldName": "avg_latency_ms", "scale": {"type": "quantitative"}, "displayName": "Avg Latency (ms)"},
                "y": {"fieldName": "avg_response_size", "scale": {"type": "quantitative"}, "displayName": "Avg Response Size"},
                "color": {"fieldName": "tool_name", "scale": {"type": "categorical"}, "displayName": "Tool"},
            },
            "frame": {"showTitle": True, "title": "Latency vs Response Size by Tool"},
            "mark": {"colors": PALETTE}
        }
    }, {"x": 3, "y": 4, "width": 3, "height": 4})

    # Serving Detail Table (y=8)
    w3({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "serving_hourly",
            "fields": [
                {"name": "hour", "expression": "`hour`"},
                {"name": "total_requests", "expression": "`total_requests`"},
                {"name": "input_tokens", "expression": "`input_tokens`"},
                {"name": "output_tokens", "expression": "`output_tokens`"},
                {"name": "avg_tokens_per_req", "expression": "`avg_tokens_per_req`"},
                {"name": "errors", "expression": "`errors`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 1, "widgetType": "table",
            "encodings": {"columns": [
                {"fieldName": "hour", "type": "datetime", "displayAs": "datetime", "title": "Hour", "displayName": "Hour", "order": 100000, "alignContent": "right"},
                {"fieldName": "total_requests", "type": "integer", "displayAs": "number", "title": "Requests", "displayName": "Requests", "order": 100001, "alignContent": "right"},
                {"fieldName": "input_tokens", "type": "integer", "displayAs": "number", "title": "Input Tokens", "displayName": "Input Tokens", "order": 100002, "alignContent": "right"},
                {"fieldName": "output_tokens", "type": "integer", "displayAs": "number", "title": "Output Tokens", "displayName": "Output Tokens", "order": 100003, "alignContent": "right"},
                {"fieldName": "avg_tokens_per_req", "type": "integer", "displayAs": "number", "title": "Avg Tokens/Req", "displayName": "Avg Tokens/Req", "order": 100004, "alignContent": "right"},
                {"fieldName": "errors", "type": "integer", "displayAs": "number", "title": "Errors", "displayName": "Errors", "order": 100005, "alignContent": "right"},
            ]},
            "frame": {"showTitle": True, "title": "Serving Endpoint Detail (Hourly)"}
        }
    }, {"x": 0, "y": 8, "width": 6, "height": 5})

    pages.append({
        "name": _uid(), "displayName": "Cost & Tokens",
        "pageType": "PAGE_TYPE_CANVAS", "layout": p3_layout
    })

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4: Error Investigation
    # ══════════════════════════════════════════════════════════════════════════
    p4_layout = []

    def w4(spec, pos):
        p4_layout.append({"widget": {"name": _uid(), **spec}, "position": pos})

    # Error by Tool + Service (y=0)
    w4({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "error_by_tool",
            "fields": [
                {"name": "tool_name", "expression": "`tool_name`"},
                {"name": "error_count", "expression": "`error_count`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "bar",
            "encodings": {
                "x": {"fieldName": "tool_name", "scale": {"type": "categorical", "sort": {"by": "y-reversed"}}, "displayName": "Tool"},
                "y": {"fieldName": "error_count", "scale": {"type": "quantitative"}, "displayName": "Errors"},
                "label": {"show": True}
            },
            "frame": {"showTitle": True, "title": "Errors by Tool (7d)"},
            "mark": {"colors": [C_RED]}
        }
    }, {"x": 0, "y": 0, "width": 3, "height": 4})

    w4({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "error_by_service",
            "fields": [
                {"name": "count(*)", "expression": "SUM(`error_count`)"},
                {"name": "service", "expression": "`service`"},
            ],
            "disaggregated": False
        }}],
        "spec": {
            "version": 3, "widgetType": "pie",
            "encodings": {
                "angle": {"fieldName": "count(*)", "scale": {"type": "quantitative"}, "displayName": "Errors"},
                "color": {"fieldName": "service", "scale": {"type": "categorical"}, "displayName": "Service"},
            },
            "frame": {"showTitle": True, "title": "Error Distribution by Service"},
        }
    }, {"x": 3, "y": 0, "width": 3, "height": 4})

    # Error Timeline (y=4)
    w4({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "error_timeline",
            "fields": [
                {"name": "hour", "expression": "`hour`"},
                {"name": "error_count", "expression": "`error_count`"},
                {"name": "tool_name", "expression": "`tool_name`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 3, "widgetType": "bar",
            "encodings": {
                "x": {"fieldName": "hour", "scale": {"type": "temporal"}, "displayName": "Hour"},
                "y": {"fieldName": "error_count", "scale": {"type": "quantitative"}, "displayName": "Errors"},
                "color": {"fieldName": "tool_name", "scale": {"type": "categorical"}, "displayName": "Tool"},
            },
            "frame": {"showTitle": True, "title": "Error Timeline by Tool"},
            "mark": {"colors": PALETTE}
        }
    }, {"x": 0, "y": 4, "width": 6, "height": 4})

    # Recent Errors Table (y=8)
    w4({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "recent_errors",
            "fields": [
                {"name": "request_time", "expression": "`request_time`"},
                {"name": "trace_id", "expression": "`trace_id`"},
                {"name": "service", "expression": "`service`"},
                {"name": "tool", "expression": "`tool`"},
                {"name": "user_id", "expression": "`user_id`"},
                {"name": "latency_ms", "expression": "`latency_ms`"},
                {"name": "response_preview", "expression": "`response_preview`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 1, "widgetType": "table",
            "encodings": {"columns": [
                {"fieldName": "request_time", "type": "datetime", "displayAs": "datetime", "title": "Time", "displayName": "Time", "order": 100000, "alignContent": "right"},
                {"fieldName": "trace_id", "type": "string", "displayAs": "string", "title": "Trace ID", "displayName": "Trace ID", "order": 100001, "alignContent": "left"},
                {"fieldName": "service", "type": "string", "displayAs": "string", "title": "Service", "displayName": "Service", "order": 100002, "alignContent": "left"},
                {"fieldName": "tool", "type": "string", "displayAs": "string", "title": "Tool", "displayName": "Tool", "order": 100003, "alignContent": "left"},
                {"fieldName": "user_id", "type": "string", "displayAs": "string", "title": "User", "displayName": "User", "order": 100004, "alignContent": "left"},
                {"fieldName": "latency_ms", "type": "integer", "displayAs": "number", "title": "Latency (ms)", "displayName": "Latency (ms)", "order": 100005, "alignContent": "right"},
                {"fieldName": "response_preview", "type": "string", "displayAs": "string", "title": "Response", "displayName": "Response", "order": 100006, "alignContent": "left"},
            ]},
            "frame": {"showTitle": True, "title": "Recent Errors (Last 7 Days)"}
        }
    }, {"x": 0, "y": 8, "width": 6, "height": 6})

    # Master Correlation Table (y=14)
    w4({
        "queries": [{"name": "main_query", "query": {
            "datasetName": "master_correlation",
            "fields": [
                {"name": "request_time", "expression": "`request_time`"},
                {"name": "trace_id", "expression": "`trace_id`"},
                {"name": "status", "expression": "`status`"},
                {"name": "latency_ms", "expression": "`latency_ms`"},
                {"name": "service", "expression": "`service`"},
                {"name": "tool", "expression": "`tool`"},
                {"name": "user_id", "expression": "`user_id`"},
                {"name": "num_assessments", "expression": "`num_assessments`"},
                {"name": "request_preview", "expression": "`request_preview`"},
                {"name": "response_preview", "expression": "`response_preview`"},
            ],
            "disaggregated": True
        }}],
        "spec": {
            "version": 1, "widgetType": "table",
            "encodings": {"columns": [
                {"fieldName": "request_time", "type": "datetime", "displayAs": "datetime", "title": "Time", "displayName": "Time", "order": 100000, "alignContent": "right"},
                {"fieldName": "trace_id", "type": "string", "displayAs": "string", "title": "Trace", "displayName": "Trace", "order": 100001, "alignContent": "left"},
                {"fieldName": "status", "type": "string", "displayAs": "string", "title": "Status", "displayName": "Status", "order": 100002, "alignContent": "left"},
                {"fieldName": "latency_ms", "type": "integer", "displayAs": "number", "title": "Latency", "displayName": "Latency", "order": 100003, "alignContent": "right"},
                {"fieldName": "service", "type": "string", "displayAs": "string", "title": "Service", "displayName": "Service", "order": 100004, "alignContent": "left"},
                {"fieldName": "tool", "type": "string", "displayAs": "string", "title": "Tool", "displayName": "Tool", "order": 100005, "alignContent": "left"},
                {"fieldName": "user_id", "type": "string", "displayAs": "string", "title": "User", "displayName": "User", "order": 100006, "alignContent": "left"},
                {"fieldName": "num_assessments", "type": "integer", "displayAs": "number", "title": "Assessments", "displayName": "Assessments", "order": 100007, "alignContent": "right"},
                {"fieldName": "request_preview", "type": "string", "displayAs": "string", "title": "Request", "displayName": "Request", "order": 100008, "alignContent": "left"},
                {"fieldName": "response_preview", "type": "string", "displayAs": "string", "title": "Response", "displayName": "Response", "order": 100009, "alignContent": "left"},
            ]},
            "frame": {"showTitle": True, "title": "Master Correlation (Last 24h)"}
        }
    }, {"x": 0, "y": 14, "width": 6, "height": 6})

    pages.append({
        "name": _uid(), "displayName": "Error Investigation",
        "pageType": "PAGE_TYPE_CANVAS", "layout": p4_layout
    })

    return {
        "display_name": DASHBOARD_NAME,
        "warehouse_id": WAREHOUSE_ID,
        "parent_path": PARENT_PATH,
        "serialized_dashboard": json.dumps({
            "datasets": datasets,
            "pages": pages,
            "uiSettings": {
                "theme": {"widgetHeaderAlignment": "ALIGNMENT_UNSPECIFIED"},
                "applyModeEnabled": False
            }
        })
    }


# ── Alert Definitions ─────────────────────────────────────────────────────────

ALERTS = [
    {
        "display_name": "AuthZ: Error Rate Spike (>5%)",
        "query_text": f"""
SELECT ROUND(COUNT(CASE WHEN state = 'ERROR' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS error_rate
FROM {TRACES_TABLE}
WHERE request_time >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
""",
        "op": "GREATER_THAN",
        "threshold": "5.0",
        "custom_subject": "[AuthZ Showcase] Error rate spike — {{error_rate}}% in the last hour",
        "custom_body": "Error rate exceeded 5% threshold. Check the Error Investigation tab in the observability dashboard.",
    },
    {
        "display_name": "AuthZ: P95 Latency SLA Breach (>5s)",
        "query_text": f"""
SELECT ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_duration_ms), 0) AS p95_ms
FROM {TRACES_TABLE}
WHERE request_time >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR AND state = 'OK'
""",
        "op": "GREATER_THAN",
        "threshold": "5000",
        "custom_subject": "[AuthZ Showcase] P95 latency SLA breach — {{p95_ms}}ms",
        "custom_body": "P95 latency exceeded 5000ms threshold. Check latency percentiles in the Operations Overview dashboard.",
    },
    {
        "display_name": "AuthZ: Safety Score Drop (<0.8)",
        "query_text": f"""
SELECT ROUND(AVG(CAST(a.feedback.value AS DOUBLE)), 3) AS avg_safety
FROM {TRACES_TABLE} t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE a.name = 'safety_check'
    AND t.request_time >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
""",
        "op": "LESS_THAN",
        "threshold": "0.8",
        "custom_subject": "[AuthZ Showcase] Safety score drop — {{avg_safety}} avg",
        "custom_body": "Average safety score dropped below 0.8 threshold. Check Quality & Judges dashboard for details.",
    },
]


def run_cli(args, profile):
    """Run databricks CLI command and return output."""
    cmd = ["databricks"] + args + ["--profile", profile]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}", file=sys.stderr)
        return None
    return result.stdout.strip()


def deploy_dashboard(profile):
    """Create the Lakeview dashboard via REST API."""
    print("Building dashboard payload...")
    payload = build_dashboard()

    print(f"Creating dashboard: {DASHBOARD_NAME}")
    payload_json = json.dumps(payload)

    result = run_cli([
        "api", "post",
        "/api/2.0/lakeview/dashboards",
        "--json", payload_json,
    ], profile)

    if result:
        data = json.loads(result)
        dashboard_id = data.get("dashboard_id", "unknown")
        path = data.get("path", "unknown")
        print(f"  Dashboard created: {dashboard_id}")
        print(f"  Path: {path}")

        # Publish it
        print("Publishing dashboard...")
        pub_result = run_cli([
            "api", "post",
            f"/api/2.0/lakeview/dashboards/{dashboard_id}/published",
            "--json", json.dumps({
                "warehouse_id": WAREHOUSE_ID,
                "embed_credentials": True,
            }),
        ], profile)
        if pub_result:
            print("  Published successfully!")

        return dashboard_id
    return None


def deploy_alerts(profile):
    """Create SQL queries and alerts."""
    for alert_def in ALERTS:
        name = alert_def["display_name"]
        print(f"\nCreating alert: {name}")

        # Step 1: Create a SQL query
        query_payload = json.dumps({
            "display_name": f"[Alert] {name}",
            "warehouse_id": WAREHOUSE_ID,
            "parent_path": PARENT_PATH,
            "query_text": alert_def["query_text"].strip(),
            "run_as_mode": "OWNER",
        })

        result = run_cli([
            "api", "post",
            "/api/2.0/sql/queries",
            "--json", query_payload,
        ], profile)

        if not result:
            print(f"  Failed to create query for {name}")
            continue

        query_data = json.loads(result)
        query_id = query_data.get("id")
        print(f"  Query created: {query_id}")

        # Step 2: Create the alert
        alert_payload = json.dumps({
            "alert": {
                "display_name": name,
                "query_id": query_id,
                "condition": {
                    "op": alert_def["op"],
                    "operand": {"column": {"name": list(json.loads("{}").keys())[0] if False else alert_def["query_text"].split(" AS ")[-1].split("\n")[0].strip()}},
                    "threshold": {"value": {"double_value": float(alert_def["threshold"])}},
                },
                "custom_subject": alert_def["custom_subject"],
                "custom_body": alert_def["custom_body"],
                "notify_on_ok": False,
                "seconds_to_retrigger": 3600,
            }
        })

        result = run_cli([
            "api", "post",
            "/api/2.0/sql/alerts",
            "--json", alert_payload,
        ], profile)

        if result:
            alert_data = json.loads(result)
            alert_id = alert_data.get("id", "unknown")
            print(f"  Alert created: {alert_id}")
        else:
            print(f"  Failed to create alert (query {query_id} still exists)")


def main():
    parser = argparse.ArgumentParser(description="Deploy AuthZ Showcase Observability Dashboard + Alerts")
    parser.add_argument("--profile", required=True, help="Databricks CLI profile")
    parser.add_argument("--dashboard-only", action="store_true", help="Only deploy the dashboard")
    parser.add_argument("--alerts-only", action="store_true", help="Only deploy alerts")
    args = parser.parse_args()

    neither = not args.dashboard_only and not args.alerts_only

    if neither or args.dashboard_only:
        print("=" * 60)
        print("Deploying Lakeview Dashboard")
        print("=" * 60)
        deploy_dashboard(args.profile)

    if neither or args.alerts_only:
        print("\n" + "=" * 60)
        print("Deploying SQL Alerts")
        print("=" * 60)
        deploy_alerts(args.profile)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
