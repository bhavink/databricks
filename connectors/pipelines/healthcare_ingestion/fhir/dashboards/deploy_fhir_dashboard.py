#!/usr/bin/env python3
"""
Deploy FIXED Healthcare FHIR R4 Operations Dashboard
Updates the existing dashboard with corrected SQL queries.
"""

import json
import requests
from pathlib import Path

PROFILE = "adb-wx1"
WAREHOUSE_ID = "093d4ec27ed4bdee"
DASHBOARD_NAME = "Healthcare FHIR R4 Operations"
EXISTING_DASHBOARD_ID = "01f106a73e2516a7af4629ad65a59a29"  # The dashboard we already created

DASHBOARD_FILE = "/Users/bhavin.kukadia/Downloads/000-dev/0-repo/databricks/connectors/pipelines/healthcare_ingestion/fhir/dashboards/healthcare_fhir_r4_operations_fixed.lvdash.json"

def get_databricks_config(profile):
    """Read Databricks configuration from ~/.databrickscfg"""
    config_file = Path.home() / ".databrickscfg"
    host = None
    token = None
    in_profile = False
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line == f"[{profile}]":
                in_profile = True
                continue
            if line.startswith('[') and in_profile:
                break
            if in_profile:
                if line.startswith('host'):
                    host = line.split('=')[1].strip()
                elif line.startswith('token'):
                    token = line.split('=')[1].strip()
    return host, token

def get_dashboard(host, token, dashboard_id):
    """Get dashboard details including etag"""
    url = f"{host}/api/2.0/lakeview/dashboards/{dashboard_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def update_dashboard(host, token, dashboard_id, display_name, warehouse_id, serialized_dashboard):
    """Update an existing dashboard"""
    # First get the current dashboard to retrieve etag
    current = get_dashboard(host, token, dashboard_id)
    etag = current.get("etag")

    url = f"{host}/api/2.0/lakeview/dashboards/{dashboard_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "display_name": display_name,
        "warehouse_id": warehouse_id,
        "serialized_dashboard": json.dumps(serialized_dashboard)
    }

    if etag:
        payload["etag"] = etag

    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"   ❌ HTTP Error: {e}")
        if e.response is not None:
            print(f"   Response status: {e.response.status_code}")
            print(f"   Response body: {e.response.text[:500]}")
        raise

def main():
    print("="*80)
    print("Updating Healthcare FHIR R4 Operations Dashboard (FIXED SQL)")
    print("="*80)

    # Get config
    print(f"\n1. Loading configuration (profile: {PROFILE})...")
    host, token = get_databricks_config(PROFILE)
    print(f"   ✅ Connected to: {host}")

    # Load fixed dashboard JSON
    print(f"\n2. Loading FIXED dashboard JSON...")
    print(f"   Source: {DASHBOARD_FILE}")

    if not Path(DASHBOARD_FILE).exists():
        print(f"   ❌ File not found: {DASHBOARD_FILE}")
        print(f"   Run fix_dashboard_queries.py first!")
        return

    try:
        with open(DASHBOARD_FILE, 'r') as f:
            dashboard_json = json.load(f)
        print(f"   ✅ Loaded fixed dashboard JSON")
        print(f"   - {len(dashboard_json['datasets'])} datasets")
        print(f"   - {len(dashboard_json['pages'])} pages")
    except Exception as e:
        print(f"   ❌ Error loading JSON: {e}")
        return

    # Update dashboard
    try:
        print(f"\n3. Updating existing dashboard...")
        print(f"   Dashboard ID: {EXISTING_DASHBOARD_ID}")
        result = update_dashboard(host, token, EXISTING_DASHBOARD_ID, DASHBOARD_NAME, WAREHOUSE_ID, dashboard_json)
        print(f"   ✅ Dashboard updated successfully")

        # Summary
        print("\n" + "="*80)
        print("✅ UPDATE COMPLETE")
        print("="*80)
        print(f"\nDashboard: {DASHBOARD_NAME}")
        print(f"ID: {EXISTING_DASHBOARD_ID}")
        print(f"URL: {host}/sql/dashboardsv3/{EXISTING_DASHBOARD_ID}")
        print(f"\n✅ All SQL queries have been corrected!")
        print(f"   - Column names now match actual FHIR table schema")
        print(f"   - Dashboard should work without errors")

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
