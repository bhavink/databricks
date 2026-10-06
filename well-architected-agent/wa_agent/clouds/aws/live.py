"""Live collection for Databricks on AWS: not available yet.

Assess AWS workspaces from Terraform plans or state (`collect tfplan --cloud
aws`); a read-only live collector (AWS APIs and the Databricks account API)
is the next step, as it was for Google Cloud.
"""

from __future__ import annotations


def collect(workspace: str, run=None, databricks_profile: str | None = None,
            account_profile: str | None = None) -> dict:
    raise RuntimeError("live collection isn't available for AWS yet; use `wa-agent collect tfplan --cloud aws "
                       "--plan <terraform show -json output>`")
