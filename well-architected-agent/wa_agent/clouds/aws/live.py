"""Live collection for Databricks on AWS: out of scope by design.

AWS workspaces are assessed from Terraform plans (before apply) or state
(after apply) with `collect tfplan --cloud aws`; there is no live collector.
"""

from __future__ import annotations


def collect(workspace: str, run=None, databricks_profile: str | None = None,
            account_profile: str | None = None) -> dict:
    raise RuntimeError("AWS is assessed from Terraform, not scanned live; use `wa-agent collect tfplan --cloud aws "
                       "--plan <terraform show -json output>`")
