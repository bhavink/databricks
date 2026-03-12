"""
Phase 0 / Step 1 — Create UC workspace groups.

Run this before any other seed script.
Works on any Databricks workspace (AWS, GCP, Azure).

Usage:
    # Uses Databricks CLI OAuth profile — no PAT needed.
    # Ensure CLI is configured: databricks auth login --profile <profile>
    DATABRICKS_CONFIG_PROFILE=<YOUR_CLI_PROFILE> python 01_create_groups.py

Expected output:
    ✓ created  authz_showcase_west
    ✓ created  authz_showcase_east
    ✓ created  authz_showcase_central
    ✓ created  authz_showcase_managers
    ✓ created  authz_showcase_finance
    ✓ created  authz_showcase_executives
    ✓ created  authz_showcase_admin
    Done — 7 groups ready.
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import Group

GROUPS = [
    "authz_showcase_west",        # West region sales reps
    "authz_showcase_east",        # East region sales reps
    "authz_showcase_central",     # Central region sales reps
    "authz_showcase_managers",    # Regional managers (all reps visible)
    "authz_showcase_finance",     # Finance team (margin/cost visible)
    "authz_showcase_executives",  # Executives (all data, no masks)
    "authz_showcase_admin",       # Admin / bypass for testing
]


def get_existing_groups(w: WorkspaceClient) -> dict[str, str]:
    """Return {display_name: group_id} for all existing workspace groups."""
    return {g.display_name: g.id for g in w.groups.list(attributes="id,displayName")}


def main():
    w = WorkspaceClient()
    existing = get_existing_groups(w)
    created = 0
    skipped = 0

    for name in GROUPS:
        if name in existing:
            print(f"  - exists   {name}")
            skipped += 1
        else:
            g = w.groups.create(display_name=name)
            print(f"  ✓ created  {name}  (id={g.id})")
            created += 1

    print(f"\nDone — {created} created, {skipped} already existed.")
    print("Next step: python 02_seed_data.py")


if __name__ == "__main__":
    main()
