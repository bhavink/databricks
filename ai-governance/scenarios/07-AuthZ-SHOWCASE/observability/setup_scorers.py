"""
setup_scorers.py — Register and start automated quality scorers (Module D).

Run this in a Databricks notebook or locally with `databricks-connect`:
    %pip install mlflow[databricks]>=3.1
    dbutils.library.restartPython()
    %run ./setup_scorers

Or from CLI:
    python observability/setup_scorers.py

Scorers run asynchronously on production traces — zero app impact.
They read from the trace store and write assessments back.
"""

import os
import mlflow

EXPERIMENT_NAME = os.getenv(
    "MLFLOW_EXPERIMENT_NAME",
    "/Users/bhavin.kukadia@databricks.com/mas-155f64f7-dev-experiment",
)


def setup_all_scorers():
    """Register and start all scorers. Idempotent — safe to re-run."""
    from mlflow.genai.scorers import (
        Safety,
        RelevanceToQuery,
        Guidelines,
        ScorerSamplingConfig,
        scorer,
    )

    mlflow.set_experiment(EXPERIMENT_NAME)
    print(f"Targeting experiment: {EXPERIMENT_NAME}")

    # ── Built-in: Safety ─────────────────────────────────────────────────
    try:
        safety = Safety().register(name="safety_check")
        safety.start(sampling_config=ScorerSamplingConfig(sample_rate=1.0))
        print("  [OK] safety_check: 100% sampling")
    except Exception as e:
        print(f"  [SKIP] safety_check: {e}")

    # ── Built-in: Relevance ──────────────────────────────────────────────
    try:
        relevance = RelevanceToQuery().register(name="relevance_check")
        relevance.start(sampling_config=ScorerSamplingConfig(sample_rate=0.5))
        print("  [OK] relevance_check: 50% sampling")
    except Exception as e:
        print(f"  [SKIP] relevance_check: {e}")

    # ── Custom: Domain-specific guidelines ────────────────────────────────
    try:
        guidelines = Guidelines(
            name="authz_guidelines",
            guidelines=[
                "The response must correctly identify the auth pattern used (OBO User or M2M).",
                "The response must not contain PII such as SSN or credit card numbers.",
                "If the query involves approval status, the response must include the opp_id.",
                "Error responses must include actionable hints about permissions or access.",
            ],
        ).register(name="authz_guidelines_check")
        guidelines.start(sampling_config=ScorerSamplingConfig(sample_rate=0.3))
        print("  [OK] authz_guidelines_check: 30% sampling")
    except Exception as e:
        print(f"  [SKIP] authz_guidelines_check: {e}")

    # ── Custom code scorer: response length (no LLM cost) ────────────────
    @scorer(aggregations=["mean", "min", "max"])
    def response_length(outputs):
        """Measure response length — catches empty or excessively long responses."""
        return len(str(outputs.get("response", "")))

    try:
        length_scorer = response_length.register(name="response_length")
        length_scorer.start(sampling_config=ScorerSamplingConfig(sample_rate=1.0))
        print("  [OK] response_length: 100% sampling (no LLM cost)")
    except Exception as e:
        print(f"  [SKIP] response_length: {e}")

    # ── Custom code scorer: has auth pattern tag ─────────────────────────
    @scorer
    def has_auth_pattern(outputs):
        """Check if the response identifies the auth pattern used."""
        response = str(outputs.get("response", "")).lower()
        return any(p in response for p in ["obo", "m2m", "auth_pattern", "on behalf of"])

    try:
        auth_scorer = has_auth_pattern.register(name="has_auth_pattern")
        auth_scorer.start(sampling_config=ScorerSamplingConfig(sample_rate=1.0))
        print("  [OK] has_auth_pattern: 100% sampling (no LLM cost)")
    except Exception as e:
        print(f"  [SKIP] has_auth_pattern: {e}")

    print("\nDone. Scorers will process traces asynchronously.")


def list_active_scorers():
    """List all active scorers for the experiment."""
    from mlflow.genai.scorers import list_scorers

    mlflow.set_experiment(EXPERIMENT_NAME)
    scorers = list_scorers()
    if not scorers:
        print("No active scorers found.")
        return
    for s in scorers:
        rate = getattr(s, 'sample_rate', '?')
        print(f"  {s.name}: sampling={rate}")


if __name__ == "__main__":
    setup_all_scorers()
    print("\nActive scorers:")
    list_active_scorers()
