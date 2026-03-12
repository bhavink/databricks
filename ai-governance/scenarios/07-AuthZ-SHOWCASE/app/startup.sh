#!/bin/bash
# Fix mlflow namespace conflict: the Databricks Apps runtime pre-installs
# mlflow-skinny which conflicts with mlflow-tracing (both provide `mlflow`
# namespace). Force-reinstall mlflow-tracing to ensure its files are intact.

set -e

# Step 1: Remove conflicting mlflow-skinny
echo "[startup] Ensuring mlflow-tracing files are intact..."
pip uninstall -y mlflow-skinny 2>/dev/null || true
pip install --force-reinstall --no-deps mlflow-tracing 2>/dev/null || true

# Step 2: Run the Streamlit app
exec streamlit run app.py --server.port 8000 --server.headless true
