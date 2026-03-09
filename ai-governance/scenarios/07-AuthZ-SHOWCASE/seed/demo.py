#!/usr/bin/env python3
"""
demo.py — Single entry point for AI AuthZ Showcase demo lifecycle.

BEFORE demo:
  python3 seed/demo.py --before --profile adb-wx1

AFTER demo:
  python3 seed/demo.py --after --profile adb-wx1

STATUS check only:
  python3 seed/demo.py --status --profile adb-wx1

What --before does (all idempotent):
  1. Verify both apps are RUNNING
  2. Onboard app SPs: group membership, warehouse CAN_USE, UC grants, quota_viewers
  3. Refresh authz_showcase_custmcp_conn bearer token (~1h TTL)
  4. Reset approval_requests to initial seed state (3 seeded rows)
  5. Reset your user to authz_showcase_west (West Rep persona for demo start)
  6. Verify connections (github + custmcp exist)
  7. Print full status summary

What --after does:
  1. Reset approval_requests to initial seed state (removes demo-added rows)
  2. Reset your user to authz_showcase_west
  3. Cleanup SP secrets — delete all but the oldest (platform-managed) one
  4. Print summary

Nothing is hardcoded. SPs are resolved live from `databricks apps get`.
"""

import argparse
import json
import re
import requests
import subprocess
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import iam
from databricks.sdk.service.sql import StatementState

# ── Static config (infra-level, doesn't change with app recreate) ─────────────
WAREHOUSE_ID  = "<YOUR_WAREHOUSE_ID>"
CATALOG       = "authz_showcase"
MAIN_APP      = "authz-showcase"
MCP_APP       = "authz-showcase-custom-mcp"
EXEC_GROUP    = "authz_showcase_executives"
DEMO_PERSONA  = "authz_showcase_west"   # starting persona
CONN_CUSTMCP  = "authz_showcase_custmcp_conn"
CONN_GITHUB   = "authz_showcase_github_conn"

UC_GRANTS = [
    "GRANT USE CATALOG  ON CATALOG  {cat}                         TO `{sp}`",
    "GRANT USE SCHEMA   ON SCHEMA   {cat}.sales                   TO `{sp}`",
    "GRANT USE SCHEMA   ON SCHEMA   {cat}.knowledge_base          TO `{sp}`",
    "GRANT USE SCHEMA   ON SCHEMA   {cat}.functions               TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.sales.opportunities      TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.sales.sales_reps         TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.sales.quota_viewers      TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.sales.approval_requests  TO `{sp}`",
    "GRANT MODIFY       ON TABLE    {cat}.sales.approval_requests  TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.knowledge_base.product_docs          TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.knowledge_base.product_docs_index    TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.knowledge_base.sales_playbooks       TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.knowledge_base.sales_playbooks_index TO `{sp}`",
    "GRANT EXECUTE      ON FUNCTION {cat}.functions.get_rep_quota              TO `{sp}`",
    "GRANT EXECUTE      ON FUNCTION {cat}.functions.calculate_attainment       TO `{sp}`",
    "GRANT EXECUTE      ON FUNCTION {cat}.functions.recommend_next_action      TO `{sp}`",
]

# Seed rows to restore in approval_requests after each demo
APPROVAL_SEED_ROWS = [
    ("opp001", "carol.white@showcase.demo",  "Strategic account - needs exec alignment before final close", "APPROVED", "alice.chen@showcase.demo"),
    ("opp004", "david.park@showcase.demo",   "Non-standard payment terms requested by customer",           "PENDING",  None),
    ("opp007", "emma.johnson@showcase.demo", "Discount > 20% - requires finance sign-off",                "REJECTED", "bob.martinez@showcase.demo"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def sql(w: WorkspaceClient, statement: str, label: str = "") -> bool:
    resp = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID, statement=statement, wait_timeout="30s"
    )
    ok = resp.status.state == StatementState.SUCCEEDED
    if not ok:
        err = resp.status.error
        print(f"  ✗ {label or statement[:60]}: {err.message if err else 'unknown'}")
    return ok


def get_app_sp(w: WorkspaceClient, app_name: str) -> dict | None:
    try:
        app = w.apps.get(app_name)
        return {
            "client_id":  app.service_principal_client_id,
            "numeric_id": str(app.service_principal_id),
            "name":       app.service_principal_name,
            "url":        app.url or "",
            "state":      app.compute_status.state.value if app.compute_status else "UNKNOWN",
        }
    except Exception as e:
        print(f"  ✗ Could not get app '{app_name}': {e}")
        return None


def ensure_group_member(w: WorkspaceClient, sp_numeric_id: str, group_name: str) -> None:
    groups = list(w.groups.list(filter=f'displayName eq "{group_name}"'))
    if not groups:
        print(f"  ✗ Group {group_name} not found")
        return
    group = w.groups.get(groups[0].id)
    existing = {m.value for m in (group.members or [])}
    if sp_numeric_id in existing:
        print(f"  ✓ SP in {group_name}")
        return
    w.groups.patch(
        groups[0].id,
        schemas=[iam.PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
        operations=[iam.Patch(op=iam.PatchOp.ADD, path="members", value=[{"value": sp_numeric_id}])],
    )
    print(f"  ✓ Added SP to {group_name}")


def grant_warehouse(w: WorkspaceClient, sp_client_id: str) -> None:
    r = requests.patch(
        f"{w.config.host}/api/2.0/permissions/warehouses/{WAREHOUSE_ID}",
        headers={**w.config.authenticate(), "Content-Type": "application/json"},
        json={"access_control_list": [{"service_principal_name": sp_client_id, "permission_level": "CAN_USE"}]},
    )
    if r.ok:
        print(f"  ✓ Warehouse CAN_USE for {sp_client_id[:8]}...")
    else:
        print(f"  ✗ Warehouse grant failed: {r.text[:100]}")


def run_uc_grants(w: WorkspaceClient, sp_client_id: str) -> None:
    for tmpl in UC_GRANTS:
        stmt = tmpl.format(cat=CATALOG, sp=sp_client_id)
        sql(w, stmt, stmt.split("ON")[0].strip())


def upsert_quota_viewers(w: WorkspaceClient, sp_client_id: str) -> None:
    ok = sql(w, f"""
        MERGE INTO {CATALOG}.sales.quota_viewers AS t
        USING (SELECT '{sp_client_id}' AS user_email, 'service_principal' AS role) AS s
        ON t.user_email = s.user_email
        WHEN NOT MATCHED THEN INSERT (user_email, role) VALUES (s.user_email, s.role)
    """, "quota_viewers upsert")
    if ok:
        print(f"  ✓ quota_viewers upsert for {sp_client_id[:8]}...")


def refresh_custmcp_conn(w: WorkspaceClient, main_sp_client_id: str, custmcp_app_url: str) -> None:
    """Recreate UC HTTP connection with fresh bearer token (~1h TTL)."""
    token = w.config.authenticate().get("Authorization", "").replace("Bearer ", "")
    if not token:
        print(f"  ✗ Could not get auth token for connection refresh")
        return

    # Delete existing (ignore if not found)
    try:
        w.connections.delete(CONN_CUSTMCP)
        print(f"  🔄 Deleted stale {CONN_CUSTMCP}")
    except Exception:
        pass

    host_url = custmcp_app_url.rstrip("/")
    r = requests.post(
        f"{w.config.host}/api/2.1/unity-catalog/connections",
        headers={**w.config.authenticate(), "Content-Type": "application/json"},
        json={
            "name": CONN_CUSTMCP,
            "connection_type": "HTTP",
            "comment": "Custom HTTP Bearer - authz-showcase-custom-mcp. Token refreshed by demo.py.",
            "options": {
                "host": host_url,
                "base_path": "/mcp",
                "bearer_token": token,
                "is_mcp_connection": "true",
            },
        },
        timeout=30,
    )
    if not r.ok:
        print(f"  ✗ Failed to create {CONN_CUSTMCP}: {r.text[:150]}")
        return
    print(f"  ✓ {CONN_CUSTMCP} created → {host_url}/mcp (~1h TTL)")

    # Grant USE CONNECTION to app SP
    ok = sql(w, f"GRANT USE CONNECTION ON CONNECTION {CONN_CUSTMCP} TO `{main_sp_client_id}`",
             "USE CONNECTION grant")
    if ok:
        print(f"  ✓ USE CONNECTION granted to main app SP")


def reset_approval_requests(w: WorkspaceClient) -> None:
    """Delete all rows and restore 3 seed rows."""
    if not sql(w, f"DELETE FROM {CATALOG}.sales.approval_requests", "DELETE approval_requests"):
        return
    print(f"  ✓ approval_requests cleared")

    for opp_id, submitted_by, justification, status, approver in APPROVAL_SEED_ROWS:
        approver_val = f"'{approver}'" if approver else "NULL"
        ok = sql(w, f"""
            INSERT INTO {CATALOG}.sales.approval_requests
              (opp_id, submitted_by, justification, status, approver, created_at, updated_at)
            VALUES
              ('{opp_id}', '{submitted_by}', '{justification}', '{status}',
               {approver_val}, current_timestamp(), current_timestamp())
        """, f"seed {opp_id}")
        if ok:
            print(f"  ✓ Seeded {opp_id} ({status})")


def reset_user_group(w: WorkspaceClient) -> None:
    """Reset current user to authz_showcase_west (demo starting persona)."""
    me = w.current_user.me()
    user_id = me.id
    user_email = me.user_name
    GROUP_PREFIX = "authz_showcase_"

    my_groups = [g for g in (me.groups or []) if g.display and g.display.startswith(GROUP_PREFIX)]
    to_remove = [g for g in my_groups if g.display != DEMO_PERSONA]

    for g in to_remove:
        groups_found = list(w.groups.list(filter=f'displayName eq "{g.display}"'))
        if not groups_found:
            continue
        try:
            w.groups.patch(
                id=groups_found[0].id,
                operations=[iam.Patch(op=iam.PatchOp.REMOVE, path=f'members[value eq "{user_id}"]')],
                schemas=[iam.PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
            )
            print(f"  ✓ Removed {user_email} from {g.display}")
        except Exception as e:
            print(f"  ⚠  Could not remove from {g.display}: {e}")

    # Ensure in west group
    west_groups = list(w.groups.list(filter=f'displayName eq "{DEMO_PERSONA}"'))
    if not west_groups:
        print(f"  ✗ Group {DEMO_PERSONA} not found")
        return
    west_group = w.groups.get(id=west_groups[0].id)
    if user_id not in {m.value for m in (west_group.members or [])}:
        w.groups.patch(
            id=west_groups[0].id,
            operations=[iam.Patch(op=iam.PatchOp.ADD, path="members", value=[{"value": user_id}])],
            schemas=[iam.PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
        )
        print(f"  ✓ Added {user_email} to {DEMO_PERSONA}")
    else:
        print(f"  ✓ {user_email} already in {DEMO_PERSONA}")


def cleanup_sp_secrets(w: WorkspaceClient, sp_numeric_id: str, sp_display_name: str, keep: int = 1) -> None:
    """Delete all but the oldest `keep` secrets for the SP."""
    r = requests.get(
        f"{w.config.host}/api/2.0/accounts/servicePrincipals/{sp_numeric_id}/credentials/secrets",
        headers=w.config.authenticate(),
    )
    if r.status_code == 404:
        print(f"  ⚠  SP {sp_display_name} ({sp_numeric_id}) not found — was the app recreated? Re-run --before.")
        return
    r.raise_for_status()
    secrets = sorted(r.json().get("secrets", []), key=lambda s: s.get("create_time", ""))
    to_delete = secrets[keep:]
    if not to_delete:
        print(f"  ✓ {len(secrets)} secret(s), nothing to delete (platform secret preserved)")
        return
    deleted = 0
    for s in to_delete:
        d = requests.delete(
            f"{w.config.host}/api/2.0/accounts/servicePrincipals/{sp_numeric_id}/credentials/secrets/{s['id']}",
            headers=w.config.authenticate(),
        )
        if d.status_code == 200:
            deleted += 1
    print(f"  ✓ Deleted {deleted}/{len(to_delete)} demo secrets. {len(secrets) - deleted} retained.")


def verify_connections(w: WorkspaceClient) -> None:
    for name in [CONN_GITHUB, CONN_CUSTMCP]:
        try:
            conn = w.connections.get(name)
            print(f"  ✓ {conn.name} ({conn.credential_type})")
        except Exception:
            print(f"  ✗ {name} — MISSING (Tab 6 broken)")


def check_app_status(w: WorkspaceClient, app_name: str) -> bool:
    try:
        app = w.apps.get(app_name)
        state = app.compute_status.state.value if app.compute_status else "UNKNOWN"
        ok = state == "ACTIVE"
        symbol = "✓" if ok else "✗"
        print(f"  {symbol} {app_name}: {state}")
        return ok
    except Exception as e:
        print(f"  ✗ {app_name}: {e}")
        return False


# ── Main flows ────────────────────────────────────────────────────────────────

def run_before(w: WorkspaceClient, profile: str) -> None:
    sep = "=" * 60

    # ── 1. App status ──────────────────────────────────────────────────────
    print(f"\n{sep}\n[1/7] App status\n{sep}")
    check_app_status(w, MAIN_APP)
    check_app_status(w, MCP_APP)

    # ── 2. Resolve SP UUIDs dynamically ───────────────────────────────────
    print(f"\n{sep}\n[2/7] SP onboarding (main app)\n{sep}")
    main_sp = get_app_sp(w, MAIN_APP)
    if not main_sp:
        print("  ✗ Cannot proceed without main app SP")
        sys.exit(1)
    print(f"  Main SP: {main_sp['client_id']} (numeric: {main_sp['numeric_id']})")
    ensure_group_member(w, main_sp["numeric_id"], EXEC_GROUP)
    grant_warehouse(w, main_sp["client_id"])
    run_uc_grants(w, main_sp["client_id"])
    upsert_quota_viewers(w, main_sp["client_id"])

    mcp_sp = get_app_sp(w, MCP_APP)
    if mcp_sp:
        print(f"\n  MCP SP: {mcp_sp['client_id']}")
        grant_warehouse(w, mcp_sp["client_id"])
        run_uc_grants(w, mcp_sp["client_id"])
        upsert_quota_viewers(w, mcp_sp["client_id"])
    else:
        print(f"  ⚠  {MCP_APP} not found — Tab 4 may not work")

    # Update cleanup_sp_secrets.py with current numeric ID
    cleanup_script = Path(__file__).parent / "cleanup_sp_secrets.py"
    if cleanup_script.exists():
        content = cleanup_script.read_text()
        updated = re.sub(r'SP_ID\s*=\s*"[^"]*"', f'SP_ID = "{main_sp["numeric_id"]}"', content)
        if updated != content:
            cleanup_script.write_text(updated)
            print(f"  ✓ cleanup_sp_secrets.py → SP_ID={main_sp['numeric_id']}")

    # ── 3. Refresh custmcp UC connection ───────────────────────────────────
    print(f"\n{sep}\n[3/7] Refresh {CONN_CUSTMCP}\n{sep}")
    custmcp_url = mcp_sp["url"] if mcp_sp else ""
    if custmcp_url:
        refresh_custmcp_conn(w, main_sp["client_id"], custmcp_url)
    else:
        print(f"  ⚠  Could not get custom MCP app URL — skipping connection refresh")

    # ── 4. Reset approval_requests ─────────────────────────────────────────
    print(f"\n{sep}\n[4/7] Reset approval_requests\n{sep}")
    reset_approval_requests(w)

    # ── 5. Reset user to West Rep ──────────────────────────────────────────
    print(f"\n{sep}\n[5/7] Reset persona → {DEMO_PERSONA}\n{sep}")
    reset_user_group(w)

    # ── 6. Verify connections ──────────────────────────────────────────────
    print(f"\n{sep}\n[6/7] Verify UC connections\n{sep}")
    verify_connections(w)

    # ── 7. Summary ─────────────────────────────────────────────────────────
    print(f"\n{sep}\n[7/7] Summary\n{sep}")
    print("✅  Demo ready.")
    print(f"   Persona: West Rep (authz_showcase_west)")
    print(f"   approval_requests: reset to 3 seed rows (opp001/opp004/opp007)")
    print(f"   custmcp connection: refreshed (~1h TTL)")
    print(f"")
    print(f"⚠️  Tab 6 bearer token expires in ~1h.")
    print(f"   Re-run: python3 seed/demo.py --before --profile {profile}")


def run_after(w: WorkspaceClient, profile: str) -> None:
    sep = "=" * 60

    # ── 1. Reset approval_requests ─────────────────────────────────────────
    print(f"\n{sep}\n[1/3] Reset approval_requests\n{sep}")
    reset_approval_requests(w)

    # ── 2. Reset user to West Rep ──────────────────────────────────────────
    print(f"\n{sep}\n[2/3] Reset persona → {DEMO_PERSONA}\n{sep}")
    reset_user_group(w)

    # ── 3. Cleanup SP secrets ─────────────────────────────────────────────
    print(f"\n{sep}\n[3/3] Cleanup SP secrets\n{sep}")
    main_sp = get_app_sp(w, MAIN_APP)
    if main_sp:
        cleanup_sp_secrets(w, main_sp["numeric_id"], main_sp["name"])
    else:
        print(f"  ⚠  Could not resolve main SP — run manually: python3 seed/cleanup_sp_secrets.py")

    print(f"\n{sep}")
    print("✅  Post-demo cleanup complete.")
    print(f"   Next demo: python3 seed/demo.py --before --profile {profile}")


def run_status(w: WorkspaceClient) -> None:
    sep = "=" * 60
    print(f"\n{sep}\nStatus\n{sep}")

    # Apps
    print("\nApps:")
    check_app_status(w, MAIN_APP)
    check_app_status(w, MCP_APP)

    # Connections
    print("\nUC connections:")
    verify_connections(w)

    # User group
    me = w.current_user.me()
    my_groups = [g.display for g in (me.groups or []) if g.display and g.display.startswith("authz_showcase_")]
    print(f"\nYour persona groups: {my_groups or '(none)'}")

    # SP info
    main_sp = get_app_sp(w, MAIN_APP)
    if main_sp:
        print(f"\nMain SP: {main_sp['client_id']} (numeric: {main_sp['numeric_id']})")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", default="adb-wx1")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--before", action="store_true", help="Pre-demo setup (run before every demo)")
    group.add_argument("--after",  action="store_true", help="Post-demo cleanup (run after every demo)")
    group.add_argument("--status", action="store_true", help="Quick status check")
    args = parser.parse_args()

    w = WorkspaceClient(profile=args.profile)
    print(f"Workspace: {w.config.host}")

    if args.before:
        run_before(w, args.profile)
    elif args.after:
        run_after(w, args.profile)
    else:
        run_status(w)
