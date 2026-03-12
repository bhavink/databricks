"""
tracing_config.py — Shared tracing configuration for E2E observability.

Single source of truth for experiment targeting. Import in every service
to ensure consistent experiment resolution and trace correlation.

Usage:
    from observability.tracing_config import init_tracing

    # Call once at app startup
    experiment_id = init_tracing()
"""

import os

import mlflow

# ── Experiment Resolution ─────────────────────────────────────────────────────
# Priority: env var > programmatic discovery > error
# The experiment name MUST be set via MLFLOW_EXPERIMENT_NAME env var in app.yaml.
# This avoids hardcoding workspace-specific paths.

EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "")

# ── Performance Settings ──────────────────────────────────────────────────────
# These env vars are read by mlflow-tracing automatically at import time.
# We set them here to guarantee consistency across services.

TRACING_ENV = {
    "MLFLOW_TRACKING_URI": "databricks",
    "MLFLOW_ENABLE_ASYNC_TRACE_LOGGING": os.getenv(
        "MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", "true"
    ),
    "MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS": os.getenv(
        "MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS", "10"
    ),
    "MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE": os.getenv(
        "MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE", "1000"
    ),
    "MLFLOW_TRACE_SAMPLING_RATIO": os.getenv(
        "MLFLOW_TRACE_SAMPLING_RATIO", "1.0"
    ),
}


def init_tracing() -> str:
    """Initialize MLflow tracing. Call once at app startup.

    Returns the resolved experiment_id, or raises if experiment cannot be found.
    """
    if not EXPERIMENT_NAME:
        raise RuntimeError(
            "MLFLOW_EXPERIMENT_NAME env var is not set. "
            "Add it to app.yaml to enable tracing."
        )

    # Apply performance env vars before any mlflow operation
    for key, value in TRACING_ENV.items():
        os.environ.setdefault(key, value)

    # set_experiment creates-or-gets and sets it as active
    mlflow.set_experiment(EXPERIMENT_NAME)

    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise RuntimeError(
            f"Experiment {EXPERIMENT_NAME!r} could not be resolved. "
            f"Check the experiment path and permissions."
        )

    return experiment.experiment_id


def get_service_tags(service_name: str) -> dict:
    """Return standard tags for trace enrichment.

    Call this from mlflow.update_current_trace(tags=...) to ensure
    consistent tagging across services.
    """
    return {
        "service_name": service_name,
        "app_version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "production"),
    }
