#!/bin/bash
# Fix mlflow namespace conflict: the Databricks Apps runtime or stale uv cache
# can leave a broken mlflow namespace where mlflow/__init__.py is missing.
# Force-reinstall mlflow-tracing to ensure all its files are present.

set -e

# Step 1: Let uv create/sync the .venv with all deps from pyproject.toml
uv sync

# Step 2: Always force-reinstall mlflow-tracing to ensure its files are intact
# (mlflow-skinny from the base image or stale cache can corrupt the namespace)
echo "[startup] Ensuring mlflow-tracing files are intact..."
.venv/bin/pip uninstall -y mlflow-skinny 2>/dev/null || true
.venv/bin/pip install --force-reinstall --no-deps mlflow-tracing 2>/dev/null || true

# Step 3: Run the app
exec .venv/bin/python server/main.py
