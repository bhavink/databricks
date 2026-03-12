-- ============================================================================
-- E2E Observability — Cross-Layer Correlation Queries (Modules E/F/H)
-- ============================================================================
-- These queries join MLflow traces with Databricks system tables to provide
-- unified observability across the multi-agent stack.
--
-- Prerequisites:
--   1. Run setup_observability.py notebook (enables trace archival + scorers)
--      This creates authz_showcase.agent_observability.traces via Delta sync
--   2. UC schema: authz_showcase.agent_observability (created by setup)
--   3. System tables accessible (system.serving.*, system.billing.*)
--   4. Experiment: /Users/bhavin.kukadia@databricks.com/mas-155f64f7-dev-experiment
--
-- Concrete values used below (no placeholders):
--   Catalog:    authz_showcase
--   Schema:     agent_observability
--   Supervisor: mas-155f64f7-endpoint
-- ============================================================================


-- ── Widget 1: Request Volume & Error Rate (Module H) ────────────────────────
-- Hourly breakdown of total requests vs errors for the last 7 days.
SELECT
    date_trunc('hour', request_time) AS hour,
    COUNT(*) AS total_requests,
    COUNT(CASE WHEN state = 'ERROR' THEN 1 END) AS errors,
    ROUND(COUNT(CASE WHEN state = 'ERROR' THEN 1 END) * 100.0 / COUNT(*), 2)
        AS error_rate_pct
FROM authz_showcase.agent_observability.traces
WHERE request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1
ORDER BY 1;


-- ── Widget 2: Latency Percentiles (Module H) ────────────────────────────────
-- P50/P95/P99 latency by hour for successful traces.
SELECT
    date_trunc('hour', request_time) AS hour,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY execution_duration_ms) AS p50_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_duration_ms) AS p95_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY execution_duration_ms) AS p99_ms
FROM authz_showcase.agent_observability.traces
WHERE request_time >= CURRENT_DATE - INTERVAL 7 DAYS
    AND state = 'OK'
GROUP BY 1
ORDER BY 1;


-- ── Widget 3: Quality Scores Over Time (Module H) ──────────────────────────
-- Average scorer assessments by day.
SELECT
    date_trunc('day', t.request_time) AS day,
    a.name,
    AVG(CAST(a.feedback.value AS DOUBLE)) AS avg_score,
    COUNT(*) AS sample_count
FROM authz_showcase.agent_observability.traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.request_time >= CURRENT_DATE - INTERVAL 30 DAYS
    AND a.feedback.value IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;


-- ── Widget 4: Token Consumption (Module E — AI Gateway) ────────────────────
-- Daily token usage for the supervisor endpoint.
SELECT
    date_trunc('day', event_time) AS day,
    SUM(input_tokens) AS input_tokens,
    SUM(output_tokens) AS output_tokens,
    SUM(total_tokens) AS total_tokens
FROM system.ai_gateway.usage
WHERE endpoint_name = 'mas-155f64f7-endpoint'
    AND event_time >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY 1
ORDER BY 1;


-- ── Widget 5: Cost Tracking (Module E — Billing) ───────────────────────────
-- Daily DBU cost for model serving.
SELECT
    usage_date,
    SUM(usage_quantity) AS total_dbus
FROM system.billing.usage
WHERE sku_name LIKE '%SERVERLESS_REAL_TIME_INFERENCE%'
    AND usage_metadata.endpoint_name = 'mas-155f64f7-endpoint'
    AND usage_date >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY 1
ORDER BY 1;


-- ── Master Correlation Query (Module F) ────────────────────────────────────
-- E2E view: Trace quality + serving metrics + token usage
WITH traces AS (
    SELECT
        trace_id,
        client_request_id,
        request_time,
        state,
        execution_duration_ms,
        request,
        response,
        trace_metadata,
        tags,
        assessments
    FROM authz_showcase.agent_observability.traces
    WHERE request_time >= CURRENT_DATE - INTERVAL 1 DAY
),
serving AS (
    SELECT
        databricks_request_id,
        client_request_id AS serving_client_request_id,
        status_code,
        input_token_count,
        output_token_count,
        request_time AS serving_request_time
    FROM system.serving.endpoint_usage eu
    JOIN system.serving.served_entities se
        ON eu.served_entity_id = se.served_entity_id
    WHERE se.endpoint_name = 'mas-155f64f7-endpoint'
        AND eu.request_time >= CURRENT_DATE - INTERVAL 1 DAY
)
SELECT
    t.trace_id,
    t.state AS trace_status,
    t.execution_duration_ms AS e2e_latency_ms,
    s.input_token_count,
    s.output_token_count,
    s.status_code AS serving_status,
    t.tags['service_name'] AS entry_service,
    t.trace_metadata['mlflow.trace.user'] AS user_id,
    t.trace_metadata['mlflow.trace.session'] AS session_id,
    TRANSFORM(t.assessments, a -> a.name) AS scorer_names,
    TRANSFORM(t.assessments, a -> a.feedback.value) AS scorer_values,
    t.request,
    t.response
FROM traces t
LEFT JOIN serving s ON t.trace_id = s.databricks_request_id
ORDER BY t.request_time DESC;


-- ── Error Correlation Query (Module F) ─────────────────────────────────────
-- Find errors and correlate across all layers.
SELECT
    t.trace_id,
    t.state,
    t.execution_duration_ms,
    t.tags['service_name'] AS origin_service,
    t.trace_metadata['mlflow.trace.user'] AS user_id,
    FILTER(
        TRANSFORM(t.spans, sp -> sp.status),
        s -> s.code = 'ERROR'
    ) AS error_spans,
    t.response
FROM authz_showcase.agent_observability.traces t
WHERE t.state = 'ERROR'
    AND t.request_time >= CURRENT_DATE - INTERVAL 7 DAYS
ORDER BY t.request_time DESC;


-- ── Serving Endpoint Usage (Module E) ──────────────────────────────────────
-- Per-request metrics for the supervisor.
SELECT
    date_trunc('hour', eu.request_time) AS hour,
    COUNT(*) AS total_requests,
    SUM(eu.input_token_count) AS total_input_tokens,
    SUM(eu.output_token_count) AS total_output_tokens,
    AVG(eu.input_token_count + eu.output_token_count) AS avg_tokens_per_request,
    COUNT(CASE WHEN eu.status_code != 200 THEN 1 END) AS errors
FROM system.serving.endpoint_usage eu
JOIN system.serving.served_entities se
    ON eu.served_entity_id = se.served_entity_id
WHERE se.endpoint_name = 'mas-155f64f7-endpoint'
    AND eu.request_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY 1
ORDER BY 1 DESC;


-- ── Alert: Error Rate Spike ────────────────────────────────────────────────
-- Trigger when error rate > 5% in the last hour.
SELECT
    COUNT(CASE WHEN state = 'ERROR' THEN 1 END) * 100.0 / COUNT(*) AS error_rate
FROM authz_showcase.agent_observability.traces
WHERE request_time >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
HAVING error_rate > 5.0;


-- ── Alert: P95 Latency SLA Breach ──────────────────────────────────────────
-- Trigger when P95 > 5 seconds.
SELECT
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY execution_duration_ms) AS p95_ms
FROM authz_showcase.agent_observability.traces
WHERE request_time >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
    AND state = 'OK'
HAVING p95_ms > 5000;


-- ── Alert: Quality Score Drop ──────────────────────────────────────────────
-- Trigger when average safety score < 0.8.
SELECT
    AVG(CAST(a.feedback.value AS DOUBLE)) AS avg_safety
FROM authz_showcase.agent_observability.traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE a.name = 'safety_check'
    AND t.request_time >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
HAVING avg_safety < 0.8;
