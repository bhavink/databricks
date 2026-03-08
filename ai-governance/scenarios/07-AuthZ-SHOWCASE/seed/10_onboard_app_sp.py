#!/usr/bin/env python3
"""
10_onboard_app_sp.py — Idempotent SP onboarding after any app recreate.

Run this whenever the app is deleted + recreated (new SP UUID / numeric ID):
    python3 seed/10_onboard_app_sp.py --profile <YOUR_CLI_PROFILE>

What it does (all idempotent — safe to re-run):
  1. Reads current SP UUID + numeric ID from the live app
  2. Adds SP to authz_showcase_executives (required for mask_quota is_member() check)
  3. Grants CAN_USE on SQL warehouse
  4. Runs all UC hierarchy grants (USE CATALOG/SCHEMA, SELECT, EXECUTE)
  5. Upserts SP into quota_viewers (used by row filters on sales_reps)
  6. Updates cleanup_sp_secrets.py with the new numeric SP_ID

Also handles the custom MCP app SP (authz-showcase-custom-mcp) for completeness.
"""

import argparse
import re
import requests
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import ComplexValue, Patch, PatchOp, PatchSchema
from databricks.sdk.service.sql import StatementState

# ── Config ────────────────────────────────────────────────────────────────────
WAREHOUSE_ID   = "<YOUR_WAREHOUSE_ID>"
CATALOG        = "authz_showcase"
MAIN_APP       = "authz-showcase"
MCP_APP        = "<YOUR_MCP_APP_NAME>"
EXEC_GROUP     = "authz_showcase_executives"

UC_GRANTS = [
    "GRANT USE CATALOG  ON CATALOG  {cat}                         TO `{sp}`",
    "GRANT USE SCHEMA   ON SCHEMA   {cat}.sales                   TO `{sp}`",
    "GRANT USE SCHEMA   ON SCHEMA   {cat}.knowledge_base          TO `{sp}`",
    "GRANT USE SCHEMA   ON SCHEMA   {cat}.functions               TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.sales.opportunities      TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.sales.sales_reps         TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.sales.quota_viewers      TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.knowledge_base.product_docs          TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.knowledge_base.product_docs_index    TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.knowledge_base.sales_playbooks       TO `{sp}`",
    "GRANT SELECT       ON TABLE    {cat}.knowledge_base.sales_playbooks_index TO `{sp}`",
    "GRANT EXECUTE      ON FUNCTION {cat}.functions.get_rep_quota              TO `{sp}`",
    "GRANT EXECUTE      ON FUNCTION {cat}.functions.calculate_attainment       TO `{sp}`",
    "GRANT EXECUTE      ON FUNCTION {cat}.functions.recommend_next_action      TO `{sp}`",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_app_sp(w: WorkspaceClient, app_name: str) -> dict:
    app = w.apps.get(app_name)
    return {
        "client_id":  app.service_principal_client_id,
        "numeric_id": str(app.service_principal_id),
        "name":       app.service_principal_name,
    }


def add_to_group(w: WorkspaceClient, sp_numeric_id: str, group_display: str) -> None:
    groups = list(w.groups.list(filter=f'displayName eq "{group_display}"'))
    if not groups:
        print(f"  ✗ Group {group_display} not found")
        return
    group = w.groups.get(groups[0].id)
    existing = {m.value for m in (group.members or [])}
    if sp_numeric_id in existing:
        print(f"  ✓ Already in {group_display}")
        return
    w.groups.patch(
        groups[0].id,
        schemas=[PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
        operations=[Patch(
            op=PatchOp.ADD,
            path="members",
            value=[{"value": sp_numeric_id}],
        )],
    )
    print(f"  ✓ Added to {group_display}")


def grant_warehouse(w: WorkspaceClient, sp_client_id: str) -> None:
    r = requests.patch(
        f"{w.config.host}/api/2.0/permissions/warehouses/{WAREHOUSE_ID}",
        headers={**w.config.authenticate(), "Content-Type": "application/json"},
        json={"access_control_list": [
            {"service_principal_name": sp_client_id, "permission_level": "CAN_USE"}
        ]},
    )
    if r.ok:
        print(f"  ✓ Warehouse CAN_USE granted")
    else:
        print(f"  ✗ Warehouse grant failed: {r.json()}")


def run_uc_grants(w: WorkspaceClient, sp_client_id: str) -> None:
    for tmpl in UC_GRANTS:
        sql = tmpl.format(cat=CATALOG, sp=sp_client_id)
        resp = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID, statement=sql, wait_timeout="30s"
        )
        label = sql.split("ON")[0].strip()
        if resp.status.state == StatementState.SUCCEEDED:
            print(f"  ✓ {label}")
        else:
            print(f"  ✗ {label}: {resp.status.error}")


def upsert_quota_viewers(w: WorkspaceClient, sp_client_id: str) -> None:
    sql = f"""
    MERGE INTO {CATALOG}.sales.quota_viewers AS t
    USING (SELECT '{sp_client_id}' AS user_email, 'service_principal' AS role) AS s
    ON t.user_email = s.user_email
    WHEN NOT MATCHED THEN INSERT (user_email, role) VALUES (s.user_email, s.role)
    """
    resp = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID, statement=sql, wait_timeout="30s"
    )
    if resp.status.state == StatementState.SUCCEEDED:
        print(f"  ✓ quota_viewers upserted")
    else:
        print(f"  ✗ quota_viewers upsert failed: {resp.status.error}")


def remove_stale_quota_viewers(w: WorkspaceClient, valid_ids: set[str]) -> None:
    """Remove any service_principal rows whose UUID is no longer a live SP."""
    resp = w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=f"SELECT user_email FROM {CATALOG}.sales.quota_viewers WHERE role = 'service_principal'",
        wait_timeout="30s",
    )
    if resp.status.state != StatementState.SUCCEEDED:
        return
    rows = resp.result.data_array or []
    stale = [r[0] for r in rows if r[0] not in valid_ids]
    for uuid in stale:
        del_resp = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement=f"DELETE FROM {CATALOG}.sales.quota_viewers WHERE user_email = '{uuid}' AND role = 'service_principal'",
            wait_timeout="30s",
        )
        if del_resp.status.state == StatementState.SUCCEEDED:
            print(f"  ✓ Removed stale SP {uuid} from quota_viewers")


def update_cleanup_script(sp_numeric_id: str) -> None:
    script = Path(__file__).parent / "cleanup_sp_secrets.py"
    if not script.exists():
        print("  ✗ cleanup_sp_secrets.py not found")
        return
    content = script.read_text()
    updated = re.sub(r'SP_ID\s*=\s*"[^"]*"', f'SP_ID = "{sp_numeric_id}"', content)
    if updated != content:
        script.write_text(updated)
        print(f"  ✓ cleanup_sp_secrets.py → SP_ID = {sp_numeric_id}")
    else:
        print(f"  ✓ cleanup_sp_secrets.py already up to date")


# ── Main ──────────────────────────────────────────────────────────────────────

def onboard(w: WorkspaceClient, app_name: str, include_exec_group: bool = True) -> dict:
    sp = get_app_sp(w, app_name)
    print(f"\n  Name:       {sp['name']}")
    print(f"  UUID:       {sp['client_id']}")
    print(f"  Numeric ID: {sp['numeric_id']}")
    return sp


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", default="<YOUR_CLI_PROFILE>")
    args = parser.parse_args()

    w = WorkspaceClient(profile=args.profile)

    # ── Main app SP ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"App: {MAIN_APP}")
    print(f"{'='*60}")
    main_sp = onboard(w, MAIN_APP)

    print(f"\n[1/5] Group membership (authz_showcase_executives)...")
    add_to_group(w, main_sp["numeric_id"], EXEC_GROUP)

    print(f"\n[2/5] Warehouse CAN_USE...")
    grant_warehouse(w, main_sp["client_id"])

    print(f"\n[3/5] UC grants...")
    run_uc_grants(w, main_sp["client_id"])

    print(f"\n[4/5] quota_viewers upsert...")
    upsert_quota_viewers(w, main_sp["client_id"])

    print(f"\n[5/5] cleanup_sp_secrets.py...")
    update_cleanup_script(main_sp["numeric_id"])

    # ── Custom MCP app SP (needs warehouse + UC grants for Tab 4) ─────────────
    print(f"\n{'='*60}")
    print(f"App: {MCP_APP}")
    print(f"{'='*60}")
    try:
        mcp_sp = onboard(w, MCP_APP)

        print(f"\n[1/3] Warehouse CAN_USE...")
        grant_warehouse(w, mcp_sp["client_id"])

        print(f"\n[2/3] UC grants...")
        run_uc_grants(w, mcp_sp["client_id"])

        print(f"\n[3/3] quota_viewers upsert...")
        upsert_quota_viewers(w, mcp_sp["client_id"])
    except Exception as e:
        print(f"  ✗ MCP app not found or error: {e} (skip if not deployed)")

    # ── Prune stale quota_viewers rows ────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Pruning stale quota_viewers entries...")
    valid_sp_ids = {main_sp["client_id"]}
    try:
        valid_sp_ids.add(mcp_sp["client_id"])
    except NameError:
        pass
    remove_stale_quota_viewers(w, valid_sp_ids)

    print(f"\n{'='*60}")
    print("✅  Done. Both app SPs fully onboarded.")
    print(f"\nNext step if you just recreated the app:")
    print(f"  databricks apps deploy {MAIN_APP} \\")
    print(f"    --source-code-path /Workspace/Users/<YOUR_EMAIL>/authz-showcase \\")
    print(f"    --profile <YOUR_CLI_PROFILE>")
