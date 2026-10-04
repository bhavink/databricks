"""MCP server: drive the agent from any MCP-capable assistant (Claude Code,
Codex, Cursor, Gemini CLI, ...).

The tools wrap the same deterministic core as the CLI. No LLM runs inside
the agent; the calling assistant only relays inputs and results. All tools
are read-only: they never write files and never change any environment.

    wa-agent-mcp                 # stdio transport
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import catalog as catalog_mod
from . import report
from .clouds import collector
from .engine import assess as run_assess
from .facts import merge

INSTRUCTIONS = """\
Databricks Well-Architected Agent (deterministic). Rules you must follow when using it:
1. Never change anything: do not create, update or delete resources in the workspace,
   cloud tenant, Terraform or any file on the user's behalf based on these results.
2. Present findings exactly as reported, with their evidence, official docs and
   ground-truth repo links. Do not add, drop or re-rank findings.
3. The user decides what to apply. Offer the prescription; do not apply it.
Typical flow: list_baselines -> preflight(workspace) -> collect_live or collect_tfplan -> assess(facts, baseline).
For a new workspace: new_workspace(baseline) -> user runs Terraform -> verify(tf_json_path, baseline).
"""

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
READ_ONLY_REMOTE = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True)

server = MCPServer(name="databricks-well-architected", instructions=INSTRUCTIONS)


def _render(result, cat, facts, fmt: str) -> str:
    return report.to_json(result, cat, facts) if fmt == "json" else report.to_markdown(result, cat, facts)


@server.tool(annotations=READ_ONLY)
def list_baselines(cloud: str = "azure") -> list[dict]:
    """List use-case baselines: id, name, use case, reference pattern, and the tested deployment that builds it."""
    cat = catalog_mod.load(cloud)
    return [
        {"id": b["id"], "name": b["name"], "use_case": b["use_case"].strip(), "pattern": b["pattern"],
         "deployment": b["deployment"], "extra_required_checks": b.get("require") or []}
        for b in cat["baselines"]
    ]


@server.tool(annotations=READ_ONLY)
def list_patterns(cloud: str = "azure") -> list[dict]:
    """List reference architecture patterns with their required and recommended checks."""
    cat = catalog_mod.load(cloud)
    return [
        {"id": p["id"], "name": p["name"], "tier": p["tier"], "compute_mode": p["compute_mode"],
         "summary": p["summary"].strip(), "required": p["required"], "recommended": p["recommended"]}
        for p in cat["patterns"]["patterns"]
    ]


@server.tool(annotations=READ_ONLY)
def collect_tfplan(tf_json_path: str, cloud: str = "azure") -> dict:
    """Read facts from a `terraform show -json` file (plan or state). Reads the file only."""
    return collector(cloud, "tfplan").collect(json.loads(Path(tf_json_path).read_text(encoding="utf-8")))


@server.tool(annotations=READ_ONLY_REMOTE)
def preflight(workspace: str, profile: str | None = None, account_profile: str | None = None,
              show_ids: bool = False) -> str:
    """Before a scan: resolve the workspace (name, URL, id or ARM id), auto-match Databricks CLI
    profiles, try each data source read-only, and report what is reachable and how to fix the rest."""
    import io

    from .doctor import preflight as run_preflight

    buf = io.StringIO()
    run_preflight(workspace, profile, account_profile, out=buf, show_ids=show_ids)
    return buf.getvalue()


@server.tool(annotations=READ_ONLY_REMOTE)
def collect_live(workspace: str, cloud: str = "azure", profile: str | None = None,
                 account_profile: str | None = None) -> dict:
    """Read facts from a deployed workspace using only allow-listed read commands
    (cloud and databricks CLIs with the user's existing logins). workspace: name, URL, numeric id or ARM id;
    profiles are auto-matched when omitted."""
    return collector(cloud, "live").collect(workspace, databricks_profile=profile, account_profile=account_profile)


@server.tool(annotations=READ_ONLY)
def assess(facts: list[dict], baseline: str | None = None, target: str | None = None,
           cloud: str = "azure", format: str = "md") -> str:
    """Assess facts (one or more fact sets, merged) against a baseline (preferred),
    a raw target pattern, or the detected pattern. Returns the report (md or json)."""
    cat = catalog_mod.load(cloud)
    merged: dict = {}
    for f in facts:
        merged = merge(merged, f)
    return _render(run_assess(cat, merged, target, baseline), cat, merged, format)


@server.tool(annotations=READ_ONLY)
def verify(tf_json_path: str, baseline: str, cloud: str = "azure", format: str = "md") -> dict:
    """Post-apply validation: score a `terraform show -json` state (or plan) against
    the baseline it was meant to build. Returns verdict, score and report."""
    cat = catalog_mod.load(cloud)
    facts = collector(cloud, "tfplan").collect(json.loads(Path(tf_json_path).read_text(encoding="utf-8")))
    result = run_assess(cat, facts, baseline_id=baseline)
    return {
        "verdict": "PASS" if result.score["conformant"] else "FAIL",
        "input": facts["source"],
        "score": result.score,
        "report": _render(result, cat, facts, format),
    }


@server.tool(annotations=READ_ONLY)
def new_workspace(baseline: str, ref: str = "master", cloud: str = "azure") -> dict:
    """Run book for a brand-new workspace: staged tfvars for the baseline's tested
    repo deployment plus step-by-step README (plan -> assess -> apply -> verify).
    Returns file contents; writes nothing. The user saves the files and runs Terraform."""
    from .new import render

    return {"files": render(catalog_mod.load(cloud), baseline, ref)}


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
