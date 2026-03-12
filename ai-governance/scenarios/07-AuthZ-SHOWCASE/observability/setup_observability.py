# Databricks notebook source
# MAGIC %pip install "mlflow[databricks]>=3.1"
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

"""
setup_observability.py — One-shot setup for E2E observability.

Enables:
  1. Trace archival → UC Delta table (queryable via SQL)
  2. Production scorers (safety, relevance, guidelines, custom)

Run this once from a Databricks notebook. Safe to re-run (idempotent).

After running:
  - Traces will be archived to: authz_showcase.agent_observability.traces
  - Scorers will assess production traffic automatically
  - correlation_queries.sql will work against the archived traces table
"""

import mlflow

# ── Config ────────────────────────────────────────────────────────────────────
EXPERIMENT_NAME = "/Users/<YOUR_EMAIL>/<YOUR_EXPERIMENT_NAME>"
TRACE_TABLE = "authz_showcase.agent_observability.traces"

mlflow.set_experiment(EXPERIMENT_NAME)
exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
EXPERIMENT_ID = exp.experiment_id
print(f"Experiment: {EXPERIMENT_NAME} (ID: {EXPERIMENT_ID})")

# COMMAND ----------

# ── Step 1: Enable trace archival to UC Delta table ───────────────────────────
# This creates/appends to a Delta table with all trace data + assessments.
# The table is queryable via SQL — this is what correlation_queries.sql needs.

from mlflow.tracing.archival import enable_databricks_trace_archival

enable_databricks_trace_archival(
    delta_table_fullname=TRACE_TABLE,
    experiment_id=EXPERIMENT_ID,
)
print(f"Trace archival enabled → {TRACE_TABLE}")

# COMMAND ----------

# ── Step 2: Register and start production scorers ─────────────────────────────
# Idempotent: if a scorer already exists with the same name, registration will
# either skip or update. Scorers run asynchronously on production traces.

from mlflow.genai.scorers import (
    Safety,
    RelevanceToQuery,
    Guidelines,
    ScorerSamplingConfig,
    scorer,
    list_scorers,
    get_scorer,
)

def safe_register_and_start(scorer_obj, name, sample_rate):
    """Register and start a scorer, skipping if already active."""
    try:
        existing = get_scorer(name=name)
        if existing.sample_rate > 0:
            print(f"  [OK] {name}: already active (rate={existing.sample_rate})")
            return existing
        else:
            started = existing.start(sampling_config=ScorerSamplingConfig(sample_rate=sample_rate))
            print(f"  [OK] {name}: restarted (rate={sample_rate})")
            return started
    except Exception:
        pass  # Scorer doesn't exist yet

    try:
        registered = scorer_obj.register(name=name)
        started = registered.start(sampling_config=ScorerSamplingConfig(sample_rate=sample_rate))
        print(f"  [OK] {name}: registered + started (rate={sample_rate})")
        return started
    except Exception as e:
        print(f"  [SKIP] {name}: {e}")
        return None


# ── Built-in: Safety (100% — critical, low cost) ─────────────────────────────
safe_register_and_start(Safety(), "safety_check", 1.0)

# ── Built-in: Relevance (50% — moderate cost) ────────────────────────────────
safe_register_and_start(RelevanceToQuery(), "relevance_check", 0.5)

# ── Custom: Domain-specific guidelines (30% — LLM cost) ──────────────────────
authz_guidelines = Guidelines(
    name="authz_guidelines",
    guidelines=[
        "The response must correctly identify the auth pattern used (OBO User or M2M).",
        "The response must not contain PII such as SSN or credit card numbers.",
        "If the query involves approval status, the response must include the opp_id.",
        "Error responses must include actionable hints about permissions or access.",
    ],
)
safe_register_and_start(authz_guidelines, "authz_guidelines_check", 0.3)

# ── Custom code scorer: response length (no LLM cost) ────────────────────────
@scorer(aggregations=["mean", "min", "max"])
def response_length(outputs):
    """Measure response length — catches empty or excessively long responses."""
    return len(str(outputs.get("response", "")))

safe_register_and_start(response_length, "response_length", 1.0)

# ── Custom code scorer: has auth pattern tag (no LLM cost) ───────────────────
@scorer
def has_auth_pattern(outputs):
    """Check if the response identifies the auth pattern used."""
    response = str(outputs.get("response", "")).lower()
    return any(p in response for p in ["obo", "m2m", "auth_pattern", "on behalf of"])

safe_register_and_start(has_auth_pattern, "has_auth_pattern", 1.0)

# COMMAND ----------

# ── Step 3: Verify everything ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Active scorers:")
print("=" * 60)
for s in list_scorers():
    rate = getattr(s, 'sample_rate', '?')
    name = getattr(s, 'name', None) or getattr(s, '_name', '?')
    print(f"  {name}: rate={rate}")

print(f"\nTrace archival: {TRACE_TABLE}")
print(f"Experiment: {EXPERIMENT_NAME}")
print(f"\nNext steps:")
print(f"  1. Fire requests through the app to generate traces")
print(f"  2. Wait 15-20 min for initial archival + scorer processing")
print(f"  3. Run correlation_queries.sql against {TRACE_TABLE}")

# COMMAND ----------

# ── Optional: Backfill existing traces ────────────────────────────────────────
# Uncomment to retroactively score historical traces.
# This runs as a Databricks job — monitor in the Jobs UI.

# from databricks.agents.scorers import backfill_scorers
# job_id = backfill_scorers(
#     scorers=["safety_check", "relevance_check", "response_length", "has_auth_pattern"],
# )
# print(f"Backfill job: {job_id}")
