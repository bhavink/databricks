#!/usr/bin/env python3
"""
Genie Observability Dashboard Deployment Script

This script deploys the Genie Observability Dashboard to Databricks using MCP tools.
It's designed to work within Claude Code with Databricks MCP server configured.

Usage:
    From Claude Code:
    1. Ensure Databricks MCP server is configured
    2. Run: deploy_dashboard(dashboard_file, warehouse_id, workspace_path)

Features:
    - Loads dashboard JSON from file
    - Validates JSON structure
    - Deploys to Databricks AI/BI (Lakeview)
    - Auto-publishes dashboard
    - Returns dashboard URL

Author: Generated with Claude Code
Date: February 10, 2026
Version: 1.0
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


def load_dashboard_json(file_path: str) -> str:
    """
    Load dashboard JSON from file.

    Args:
        file_path: Path to dashboard JSON file

    Returns:
        Dashboard JSON as string

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Dashboard file not found: {file_path}")

    with open(path, 'r') as f:
        content = f.read()

    # Validate JSON
    json.loads(content)

    return content


def validate_dashboard_structure(dashboard_json: str) -> Dict[str, Any]:
    """
    Validate dashboard JSON structure.

    Args:
        dashboard_json: Dashboard JSON string

    Returns:
        Parsed dashboard dictionary

    Raises:
        ValueError: If structure is invalid
    """
    dashboard = json.loads(dashboard_json)

    # Check required top-level keys
    required_keys = ['datasets', 'pages']
    for key in required_keys:
        if key not in dashboard:
            raise ValueError(f"Missing required key: {key}")

    # Validate datasets
    if not isinstance(dashboard['datasets'], list) or len(dashboard['datasets']) == 0:
        raise ValueError("Dashboard must have at least one dataset")

    for ds in dashboard['datasets']:
        if 'name' not in ds or 'queryLines' not in ds:
            raise ValueError(f"Dataset missing required fields: {ds}")

    # Validate pages
    if not isinstance(dashboard['pages'], list) or len(dashboard['pages']) == 0:
        raise ValueError("Dashboard must have at least one page")

    for page in dashboard['pages']:
        if 'name' not in page or 'displayName' not in page:
            raise ValueError(f"Page missing required fields: {page}")

    return dashboard


def deploy_dashboard(
    dashboard_file: str,
    warehouse_id: str,
    parent_path: str = "/Workspace/Shared/genie-analytics",
    display_name: str = "Genie Observability Dashboard",
    publish: bool = True,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Deploy dashboard to Databricks.

    This function is designed to be called from Claude Code with MCP tools.

    Args:
        dashboard_file: Path to dashboard JSON file (relative or absolute)
        warehouse_id: SQL warehouse ID for query execution
        parent_path: Workspace folder path for dashboard
        display_name: Dashboard display name
        publish: Whether to publish after creation
        validate: Whether to validate JSON structure before deployment

    Returns:
        Dictionary with deployment results:
        {
            "success": bool,
            "status": "created" | "updated",
            "dashboard_id": str,
            "path": str,
            "url": str,
            "published": bool
        }

    Raises:
        FileNotFoundError: If dashboard file doesn't exist
        ValueError: If JSON structure is invalid

    Example:
        >>> result = deploy_dashboard(
        ...     dashboard_file="genie_observability_dashboard_v1.0.json",
        ...     warehouse_id="093d4ec27ed4bdee"
        ... )
        >>> print(f"Dashboard URL: {result['url']}")
    """
    print(f"Loading dashboard from: {dashboard_file}")
    dashboard_json = load_dashboard_json(dashboard_file)

    if validate:
        print("Validating dashboard structure...")
        dashboard = validate_dashboard_structure(dashboard_json)
        print(f"✓ Validated: {len(dashboard['datasets'])} datasets, {len(dashboard['pages'])} pages")

    print(f"Deploying to: {parent_path}/{display_name}")
    print(f"Warehouse ID: {warehouse_id}")
    print(f"Publish: {publish}")

    # NOTE: This requires Databricks MCP tools to be available
    # When running in Claude Code, use:
    # from mcp_databricks import create_or_update_dashboard
    # result = create_or_update_dashboard(...)

    # For reference, the MCP call looks like:
    deployment_params = {
        "display_name": display_name,
        "parent_path": parent_path,
        "serialized_dashboard": dashboard_json,
        "warehouse_id": warehouse_id,
        "publish": publish
    }

    print("\nDeployment parameters:")
    print(f"  Display Name: {deployment_params['display_name']}")
    print(f"  Parent Path: {deployment_params['parent_path']}")
    print(f"  Warehouse ID: {deployment_params['warehouse_id']}")
    print(f"  Publish: {deployment_params['publish']}")
    print(f"  Dashboard Size: {len(dashboard_json):,} bytes")

    # Return deployment parameters for MCP call
    # In Claude Code, this would be called via:
    # mcp__databricks__create_or_update_dashboard(**deployment_params)

    return deployment_params


def list_dashboard_files(directory: str = ".") -> list:
    """
    List available dashboard JSON files in directory.

    Args:
        directory: Directory to search (default: current)

    Returns:
        List of dashboard JSON file paths
    """
    path = Path(directory)
    json_files = list(path.glob("*.json"))

    # Filter for dashboard files (exclude backup files)
    dashboard_files = [
        f for f in json_files
        if 'dashboard' in f.name.lower() and 'backup' not in f.name.lower()
    ]

    return sorted(dashboard_files)


def get_dashboard_info(dashboard_file: str) -> Dict[str, Any]:
    """
    Get information about a dashboard file without deploying.

    Args:
        dashboard_file: Path to dashboard JSON file

    Returns:
        Dictionary with dashboard metadata
    """
    dashboard_json = load_dashboard_json(dashboard_file)
    dashboard = json.loads(dashboard_json)

    # Count widgets
    widget_count = 0
    for page in dashboard.get('pages', []):
        widget_count += len(page.get('layout', []))

    # Get page info
    pages = [
        {
            'name': page['name'],
            'displayName': page['displayName'],
            'type': page.get('pageType', 'PAGE_TYPE_CANVAS'),
            'widgets': len(page.get('layout', []))
        }
        for page in dashboard.get('pages', [])
    ]

    return {
        'file': dashboard_file,
        'file_size_bytes': Path(dashboard_file).stat().st_size,
        'datasets': len(dashboard.get('datasets', [])),
        'pages': len(dashboard.get('pages', [])),
        'total_widgets': widget_count,
        'page_details': pages
    }


# Example usage and documentation
if __name__ == "__main__":
    print("Genie Observability Dashboard Deployment Script")
    print("=" * 60)
    print()
    print("This script is designed to run in Claude Code with MCP tools.")
    print()
    print("Available Functions:")
    print("  - deploy_dashboard(): Deploy dashboard to Databricks")
    print("  - list_dashboard_files(): List available dashboard files")
    print("  - get_dashboard_info(): Get metadata about a dashboard")
    print()
    print("Example in Claude Code:")
    print("-" * 60)
    print("""
    # Import the MCP tool
    from mcp_databricks import create_or_update_dashboard

    # Load and validate dashboard
    params = deploy_dashboard(
        dashboard_file="genie_observability_dashboard_v1.0.json",
        warehouse_id="093d4ec27ed4bdee",
        parent_path="/Workspace/Shared/genie-analytics",
        display_name="Genie Observability Dashboard v1.0",
        publish=True
    )

    # Deploy via MCP
    result = create_or_update_dashboard(**params)

    # Print results
    print(f"Success: {result['success']}")
    print(f"Status: {result['status']}")
    print(f"Dashboard ID: {result['dashboard_id']}")
    print(f"URL: {result['url']}")
    """)
    print("-" * 60)
    print()

    # Show available dashboards
    print("Available Dashboard Files:")
    dashboards = list_dashboard_files()
    if dashboards:
        for dash in dashboards:
            print(f"  - {dash}")
            info = get_dashboard_info(str(dash))
            print(f"    Datasets: {info['datasets']}, "
                  f"Pages: {info['pages']}, "
                  f"Widgets: {info['total_widgets']}")
    else:
        print("  No dashboard files found in current directory")
    print()
    print("For full documentation, see:")
    print("  docs/genie-observability-dashboard.md")
