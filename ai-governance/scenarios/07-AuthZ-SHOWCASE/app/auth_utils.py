"""
auth_utils.py — User identity and UC security context helpers.

Called by app.py to build the sidebar identity panel and explain
which row filters / column masks are active for the current user.
"""

import requests

# Ordered highest-privilege → lowest; first match wins for persona label
AUTHZ_GROUPS_ORDERED = [
    "authz_showcase_admin",
    "authz_showcase_executives",
    "authz_showcase_finance",
    "authz_showcase_managers",
    "authz_showcase_east",
    "authz_showcase_west",
]

PERSONA_LABELS = {
    "authz_showcase_admin":      "Admin",
    "authz_showcase_executives": "Executive",
    "authz_showcase_finance":    "Finance Analyst",
    "authz_showcase_managers":   "Regional Manager",
    "authz_showcase_east":       "East Sales Rep",
    "authz_showcase_west":       "West Sales Rep",
}


def get_user_context(host: str, token: str) -> dict:
    """
    Return a dict describing the current user's identity and active UC policies.

    Keys:
      email          – user's Databricks email
      display_name   – display name or email
      persona        – highest-privilege authz_showcase persona label
      authz_groups   – list of authz_showcase_* groups the user belongs to
      row_filters    – human-readable description of active row filters
      masked_cols    – human-readable list of columns that are NULL for this user
    """
    r = requests.get(
        f"{host.rstrip('/')}/api/2.0/preview/scim/v2/Me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    r.raise_for_status()
    user = r.json()
    all_groups = [g.get("display", "") for g in user.get("groups", [])]
    authz_groups = [g for g in AUTHZ_GROUPS_ORDERED if g in all_groups]

    # Detect persona: highest-privilege group wins
    persona = "No authz_showcase group assigned"
    for g in AUTHZ_GROUPS_ORDERED:
        if g in authz_groups:
            persona = PERSONA_LABELS[g]
            break

    # Row filter description
    is_elevated = any(
        g in authz_groups
        for g in [
            "authz_showcase_admin",
            "authz_showcase_executives",
            "authz_showcase_finance",
            "authz_showcase_managers",
        ]
    )
    if is_elevated:
        row_filters = ["none — all rows visible (elevated persona)"]
    elif "authz_showcase_west" in authz_groups:
        row_filters = [
            "region = WEST (opportunities + customers)",
            "rep_email = self (opportunities only)",
        ]
    elif "authz_showcase_east" in authz_groups:
        row_filters = [
            "region = EAST (opportunities + customers)",
            "rep_email = self (opportunities only)",
        ]
    else:
        row_filters = ["⚠ not in any authz_showcase group — add yourself to a group"]

    # Column mask description — each column visible only to specific groups
    masked_cols = []
    if not any(
        g in authz_groups
        for g in ["authz_showcase_admin", "authz_showcase_executives", "authz_showcase_finance"]
    ):
        masked_cols.append("margin_pct on opportunities")
        masked_cols.append("cost_price on products")
    if not any(
        g in authz_groups
        for g in ["authz_showcase_admin", "authz_showcase_executives", "authz_showcase_managers"]
    ):
        masked_cols.append("is_strategic on opportunities")
    if not any(
        g in authz_groups
        for g in [
            "authz_showcase_admin",
            "authz_showcase_executives",
            "authz_showcase_finance",
            "authz_showcase_managers",
        ]
    ):
        masked_cols.append("contract_value on customers")

    email = user.get("userName", "")
    return {
        "email":        email,
        "display_name": user.get("displayName") or email,
        "persona":      persona,
        "authz_groups": authz_groups,
        "row_filters":  row_filters,
        "masked_cols":  masked_cols if masked_cols else ["none — all columns visible"],
    }
