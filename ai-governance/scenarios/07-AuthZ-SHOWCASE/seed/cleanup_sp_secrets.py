#!/usr/bin/env python3
"""
cleanup_sp_secrets.py — Delete DEMO secrets for the authz-showcase app SP.

⚠️  CRITICAL: DO NOT delete ALL secrets.
    The Databricks Apps platform stores one SP secret internally and uses it
    to deploy and run the app.  Deleting that secret breaks the app and
    requires admin-level account work to recover.

    This script preserves the OLDEST secret (the platform-managed one) and
    deletes all newer ones (created by terminal demo runs).

Run after each demo session to reclaim slots under the 5-secret limit:
    python3 seed/cleanup_sp_secrets.py --profile <YOUR_CLI_PROFILE>

⚠️  SP_ID and SP_DISPLAY_NAME must be updated whenever the app is recreated
    (databricks apps delete + create creates a NEW service principal).

    To find the current SP_ID after recreating the app:
        databricks apps get authz-showcase --profile <YOUR_CLI_PROFILE> \\
            | python3 -c "import sys,json; d=json.load(sys.stdin); \\
                          print(d['service_principal_id'], d['service_principal_client_id'])"

Recovery if you accidentally deleted ALL secrets (app enters UNAVAILABLE state):
    1. databricks apps delete authz-showcase --profile <YOUR_CLI_PROFILE>
    2. databricks apps create authz-showcase --description '...' --profile <YOUR_CLI_PROFILE>
       (may fail with QUOTA_EXCEEDED if account has 1000 OAuth integrations —
        ask a workspace admin to clean up old app integrations)
    3. Re-run grants: warehouse CAN_USE, USE SCHEMA, SELECT on sales tables,
       add new SP to authz_showcase_executives group.
"""

import argparse
import requests
import sys
from databricks.sdk import WorkspaceClient

# ── Update these after any app delete+create ───────────────────────────────
SP_ID = "<YOUR_SP_NUMERIC_ID>"           # service_principal_id from `databricks apps get`
SP_DISPLAY_NAME = "app-670ges authz-showcase"
KEEP_OLDEST = 1                     # always preserve the platform-managed secret
# ──────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Delete DEMO OAuth secrets for the authz-showcase SP (keeps oldest)")
    parser.add_argument("--profile", default="<YOUR_CLI_PROFILE>",
                        help="Databricks CLI profile (default: <YOUR_CLI_PROFILE>)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List secrets without deleting")
    parser.add_argument("--force-all", action="store_true",
                        help="⚠️  Delete ALL secrets including platform ones (BREAKS THE APP)")
    args = parser.parse_args()

    if args.force_all:
        print("⚠️  --force-all: deleting ALL secrets.  This WILL break the app.")
        print("   Run `databricks apps delete authz-showcase` and recreate it afterwards.")
        print()

    w = WorkspaceClient(profile=args.profile)
    host = w.config.host
    auth = w.config.authenticate()
    headers = {**auth, "Content-Type": "application/json"}

    # List secrets
    r = requests.get(
        f"{host}/api/2.0/accounts/servicePrincipals/{SP_ID}/credentials/secrets",
        headers=headers,
    )
    if r.status_code == 404:
        print(f"SP '{SP_DISPLAY_NAME}' ({SP_ID}) not found — was the app recreated?")
        print("Update SP_ID at the top of this script after recreating the app.")
        sys.exit(1)
    r.raise_for_status()
    secrets = r.json().get("secrets", [])

    if not secrets:
        print(f"No secrets found for SP '{SP_DISPLAY_NAME}' ({SP_ID}). Nothing to clean up.")
        return

    # Sort by creation time so oldest first
    secrets_sorted = sorted(secrets, key=lambda s: s.get("create_time", ""))

    print(f"Found {len(secrets_sorted)} secret(s) for SP '{SP_DISPLAY_NAME}' ({SP_ID}):")
    for i, s in enumerate(secrets_sorted):
        created = s.get("create_time", "unknown")
        expires = s.get("expire_time", "unknown")
        tag = "  ← KEEP (platform)" if (not args.force_all and i < KEEP_OLDEST) else ""
        print(f"  {s['id'][:20]}...  created={created}  expires={expires}{tag}")

    to_delete = secrets_sorted if args.force_all else secrets_sorted[KEEP_OLDEST:]

    if not to_delete:
        print(f"\nOnly {len(secrets_sorted)} secret(s) present — nothing to delete (platform secret preserved).")
        return

    if args.dry_run:
        print(f"\n--dry-run: would delete {len(to_delete)} secret(s), keep {len(secrets_sorted) - len(to_delete)}.")
        return

    # Delete
    print(f"\nDeleting {len(to_delete)} demo secret(s)...")
    deleted = 0
    for s in to_delete:
        d = requests.delete(
            f"{host}/api/2.0/accounts/servicePrincipals/{SP_ID}/credentials/secrets/{s['id']}",
            headers=headers,
        )
        if d.status_code == 200:
            print(f"  ✓ deleted {s['id'][:20]}...")
            deleted += 1
        else:
            print(f"  ✗ failed  {s['id'][:20]}... ({d.status_code}: {d.text})")

    kept = len(secrets_sorted) - deleted
    print(f"\nDone — {deleted}/{len(to_delete)} demo secret(s) deleted.  {kept} secret(s) retained.")
    if not args.force_all:
        print(f"Platform secret preserved — app deploy will continue to work.")


if __name__ == "__main__":
    main()
