#!/usr/bin/env python3
"""
Post-demo reset script. Run after every demo session.

Usage:
    DATABRICKS_CONFIG_PROFILE=adb-wx1 python seed/reset_demo.py

What it does:
- Gets your current user ID via SCIM
- Lists current authz_showcase_* group memberships
- Removes you from all authz_showcase groups except authz_showcase_west
- Confirms you are in authz_showcase_west
- Checks app is RUNNING
"""

import sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import iam

PROFILE = "adb-wx1"
KEEP_GROUP = "authz_showcase_west"
GROUP_PREFIX = "authz_showcase_"


def main():
    w = WorkspaceClient(profile=PROFILE)

    # 1. Get current user
    me = w.current_user.me()
    user_id = me.id
    user_email = me.user_name
    print(f"User: {user_email} (id={user_id})")

    # 2. List current authz_showcase group memberships
    my_groups = [g for g in (me.groups or []) if g.display and g.display.startswith(GROUP_PREFIX)]
    print(f"Current authz_showcase groups: {[g.display for g in my_groups] or '(none)'}")

    # 3. Remove from all except KEEP_GROUP
    to_remove = [g for g in my_groups if g.display != KEEP_GROUP]
    for g in to_remove:
        print(f"  Removing from {g.display} ...")
        # Look up the group by name to get its SCIM ID
        groups_found = list(w.groups.list(filter=f"displayName eq {g.display}"))
        if not groups_found:
            print(f"  WARNING: group {g.display} not found via list — skipping")
            continue
        group_id = groups_found[0].id
        try:
            w.groups.patch(
                id=group_id,
                operations=[
                    iam.Patch(
                        op=iam.PatchOp.REMOVE,
                        path=f'members[value eq "{user_id}"]',
                    )
                ],
                schemas=[iam.PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
            )
            print(f"  Removed from {g.display}")
        except Exception as e:
            print(f"  WARNING: could not remove from {g.display}: {e}")

    # 4. Confirm in west group
    west_groups = list(w.groups.list(filter=f"displayName eq {KEEP_GROUP}"))
    if not west_groups:
        print(f"ERROR: {KEEP_GROUP} group not found")
        sys.exit(1)

    west_group = w.groups.get(id=west_groups[0].id)
    member_ids = [m.value for m in (west_group.members or [])]
    if user_id in member_ids:
        print(f"Confirmed: in {KEEP_GROUP}")
    else:
        print(f"WARNING: not in {KEEP_GROUP} — adding now ...")
        w.groups.patch(
            id=west_groups[0].id,
            operations=[
                iam.Patch(op=iam.PatchOp.ADD, path="members", value=[{"value": user_id}])
            ],
            schemas=[iam.PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
        )
        print(f"Added to {KEEP_GROUP}")

    # 5. Check app state
    try:
        app = w.apps.get("authz-showcase")
        state = app.compute_status.state.value if app.compute_status else "UNKNOWN"
        if state == "ACTIVE":
            print("App state: RUNNING")
        else:
            print(f"WARNING: App state={state} (expected RUNNING)")
    except Exception as e:
        print(f"WARNING: could not check app state: {e}")

    print()
    print("Demo reset complete. You are West Rep. App is running.")
    print()
    print("Remember to run: python seed/refresh_custmcp_token.py before next demo (token expires ~1h)")


if __name__ == "__main__":
    main()
