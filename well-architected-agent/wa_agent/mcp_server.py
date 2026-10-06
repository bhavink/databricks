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


def _titled(cat: dict, ids: list[str]) -> list[dict]:
    checks = {c["id"]: c for c in cat["checks"]}
    return [{"check": i, "control": checks[i]["title"], "area": checks[i]["phase_name"]} for i in ids]


@server.tool(annotations=READ_ONLY)
def list_baselines(cloud: str = "azure") -> list[dict]:
    """List use-case baselines (cloud: azure, gcp or aws): id, name, use case, reference pattern, and the
    builds that create it (several builds are peers: ask the user which one fits). Use
    describe_baseline to show a baseline's controls; present controls by their titles, not by ids."""
    from .new import builds

    cat = catalog_mod.load(cloud)
    return [
        {"id": b["id"], "name": b["name"], "use_case": b["use_case"].strip(), "pattern": b["pattern"],
         "deployment": b["deployment"], "extra_required_controls": _titled(cat, b.get("require") or []),
         "builds": [{"id": x["id"], "for": x.get("for", "").strip()} for x in builds(b)],
         "options": [{"id": o["id"], "name": o["name"], "summary": o["summary"].strip(),
                      "requires": _titled(cat, o.get("require") or []), "waives": _titled(cat, o.get("waive") or [])}
                     for o in b.get("options") or []]}
        for b in cat["baselines"]
    ]


@server.tool(annotations=READ_ONLY)
def describe_baseline(baseline: str, cloud: str = "azure") -> dict:
    """What a baseline (or pattern) requires, in plain language: every control with its area of the
    production planning guide (Network, Storage, Unity Catalog, ...), level (required/recommended)
    and check id as a reference. Show the markdown to the user as-is."""
    from .describe import controls, to_markdown

    cat = catalog_mod.load(cloud)
    return {"markdown": to_markdown(cat, baseline), "controls": controls(cat, baseline)}


@server.tool(annotations=READ_ONLY)
def list_patterns(cloud: str = "azure") -> list[dict]:
    """List reference architecture patterns with their required and recommended controls (titled)."""
    cat = catalog_mod.load(cloud)
    return [
        {"id": p["id"], "name": p["name"], "tier": p["tier"], "compute_mode": p["compute_mode"],
         "summary": p["summary"].strip(), "required": _titled(cat, p["required"]),
         "recommended": _titled(cat, p["recommended"])}
        for p in cat["patterns"]["patterns"]
    ]


@server.tool(annotations=READ_ONLY)
def diagram(tf_json_path: str, workspace: str | None = None) -> str:
    """Architecture diagram (Mermaid) and resource manifest of what a `terraform show -json` plan or
    state deploys. Reads the file only. Show the Markdown to the user as-is."""
    from .diagram import to_markdown

    return to_markdown(json.loads(Path(tf_json_path).read_text(encoding="utf-8")), workspace)


@server.tool(annotations=READ_ONLY)
def collect_tfplan(tf_json_path: str, cloud: str = "azure", workspace: str | None = None) -> dict:
    """Read facts from a `terraform show -json` file (plan or state). Reads the file only.
    workspace: address or name, required when the plan has several workspaces (e.g. the SRA)."""
    return collector(cloud, "tfplan").collect(json.loads(Path(tf_json_path).read_text(encoding="utf-8")),
                                              workspace=workspace)


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
           cloud: str = "azure", format: str = "md", options: list[str] | None = None) -> str:
    """Assess facts (one or more fact sets, merged) against a baseline (preferred),
    a raw target pattern, or the detected pattern. options: the baseline options the
    workspace is held to (list_baselines shows them). Returns the report (md or json)."""
    cat = catalog_mod.load(cloud)
    merged: dict = {}
    for f in facts:
        merged = merge(merged, f)
    return _render(run_assess(cat, merged, target, baseline, options or ()), cat, merged, format)


@server.tool(annotations=READ_ONLY)
def verify(tf_json_path: str, baseline: str, cloud: str = "azure", format: str = "md",
           workspace: str | None = None, options: list[str] | None = None) -> dict:
    """Post-apply validation: score a `terraform show -json` state (or plan) against
    the baseline it was meant to build. Returns verdict, score and report."""
    cat = catalog_mod.load(cloud)
    facts = collector(cloud, "tfplan").collect(json.loads(Path(tf_json_path).read_text(encoding="utf-8")),
                                               workspace=workspace)
    result = run_assess(cat, facts, baseline_id=baseline, options=options or ())
    return {
        "verdict": "PASS" if result.score["conformant"] else "FAIL",
        "input": facts["source"],
        "score": result.score,
        "report": _render(result, cat, facts, format),
    }


@server.tool(annotations=READ_ONLY)
def new_workspace(baseline: str, inputs: dict | None = None, cloud: str = "azure", build: str | None = None,
                  options: list[str] | None = None) -> dict:
    """Deployment for a brand-new workspace from the baseline's tested Terraform (this repo's
    deployment, or the official Databricks SRA pinned to a reviewed commit): inputs.tfvars from
    `inputs` (Terraform variable -> value; unanswered required ones become REPLACE_ME_*), staged
    tfvars and a step-by-step README (plan -> assess -> apply -> verify). When the baseline offers
    several builds, pass `build` (list_baselines shows them); builds are peers with no default. `options`
    switch on baseline options (e.g. cmk). IP access lists are part of the bare minimum: ask the user for
    their known IP ranges and pass them as inputs["allowed_ip_ranges"] (a list of CIDRs); never invent
    them. Returns file contents
    and the list of Terraform files to bundle; writes nothing. To write the folder with the
    Terraform included, the user runs `wa-agent new --baseline <id> --out <dir>`."""
    from .new import render

    files = render(catalog_mod.load(cloud), baseline, inputs, build_id=build, options=options or ())
    manifest = json.loads(files["baseline.json"])
    return {"files": files, "bundle": sorted(manifest.get("files", {})),
            "write_with": f"wa-agent new --cloud {cloud} --baseline {baseline}"
                          + (f" --build {build}" if build else "")
                          + "".join(f" --option {o}" for o in options or []) + " --out <new-dir>"}


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
