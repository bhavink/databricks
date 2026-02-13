#!/usr/bin/env python3
"""
Create the genie-obs secret scope and store SP credentials using the Databricks SDK.

Uses the same auth as the Databricks CLI (~/.databrickscfg). Specify profile if not DEFAULT.

Usage:
  export DATABRICKS_SP_CLIENT_ID="your-sp-client-id"
  export DATABRICKS_SP_CLIENT_SECRET="your-sp-client-secret"
  python create_genie_obs_secrets.py
  # or with a specific CLI profile:
  python create_genie_obs_secrets.py --profile DEFAULT
"""
import argparse
import os
import sys

try:
    from databricks.sdk import WorkspaceClient
except ImportError:
    print("Install the Databricks SDK: pip install databricks-sdk", file=sys.stderr)
    sys.exit(1)

SCOPE = "genie-obs"
KEY_CLIENT_ID = "sp_client_id"
KEY_CLIENT_SECRET = "sp_client_secret"


def main():
    parser = argparse.ArgumentParser(description="Create genie-obs scope and store SP secrets")
    parser.add_argument(
        "--profile",
        default=os.environ.get("DATABRICKS_CONFIG_PROFILE", "DEFAULT"),
        help="Databricks CLI profile from ~/.databrickscfg (default: DEFAULT or DATABRICKS_CONFIG_PROFILE)",
    )
    args = parser.parse_args()

    client_id = os.environ.get("DATABRICKS_SP_CLIENT_ID") or os.environ.get("GENIE_OBS_SP_CLIENT_ID")
    client_secret = os.environ.get("DATABRICKS_SP_CLIENT_SECRET") or os.environ.get("GENIE_OBS_SP_CLIENT_SECRET")

    if not client_id or not client_secret:
        print(
            "Set DATABRICKS_SP_CLIENT_ID and DATABRICKS_SP_CLIENT_SECRET (or GENIE_OBS_*)\n"
            "in the environment before running this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    w = WorkspaceClient(profile=args.profile)
    print(f"Using Databricks profile: {args.profile}")

    # Create scope if it does not exist
    existing = [s.name for s in w.secrets.list_scopes()]
    if SCOPE not in existing:
        w.secrets.create_scope(scope=SCOPE)
        print(f"Created secret scope: {SCOPE}")
    else:
        print(f"Secret scope already exists: {SCOPE}")

    # Put secrets (overwrites if key already exists)
    w.secrets.put_secret(scope=SCOPE, key=KEY_CLIENT_ID, string_value=client_id)
    w.secrets.put_secret(scope=SCOPE, key=KEY_CLIENT_SECRET, string_value=client_secret)
    print(f"Stored secrets: {KEY_CLIENT_ID}, {KEY_CLIENT_SECRET}")

    # List keys (not values) to confirm
    keys = [s.key for s in w.secrets.list_secrets(scope=SCOPE)]
    print(f"Keys in scope '{SCOPE}': {keys}")


if __name__ == "__main__":
    main()
