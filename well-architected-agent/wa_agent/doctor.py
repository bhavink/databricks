"""`wa-agent doctor`: check prerequisites and print how to register the MCP
server with each assistant. Runs only the fixed read-only commands below."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from . import catalog as catalog_mod
from .clouds import CLOUDS
from .redact import RedactingWriter

PROJECT = Path(__file__).resolve().parents[1]
ISSUES_URL = "https://github.com/bhavink/databricks/issues/new?template=wa-agent-problem.yml"

# (label, command, required?) — reads only.
PROBES = [
    ("Azure CLI login", ["az", "account", "show", "--query", "name", "-o", "tsv"], False),
    ("Azure CLI 'databricks' extension", ["az", "extension", "list", "--query", "[?name=='databricks'].version",
                                         "-o", "tsv"], False),
    ("gcloud login (GCP scans)", ["gcloud", "config", "get-value", "account"], False),
    ("Databricks CLI", ["databricks", "--version"], False),
    ("Databricks CLI profiles", ["databricks", "auth", "profiles"], False),
    ("Terraform", ["terraform", "version"], False),
    ("uv (portable MCP launch)", ["uv", "--version"], False),
]


def _probe(cmd: list[str]) -> tuple[bool, str]:
    exe = shutil.which(cmd[0])
    if not exe:
        return False, "not installed"
    try:
        proc = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60, check=False)
    except subprocess.TimeoutExpired:
        return False, "timed out"
    if cmd[:3] == ["databricks", "auth", "profiles"]:
        rows = [line.split() for line in proc.stdout.splitlines()[1:] if line.strip()]
        valid = sum(1 for r in rows if r and r[-1] == "YES")
        return proc.returncode == 0 and valid > 0, f"{len(rows)} profiles, {valid} with a valid login"
    if cmd[:3] == ["az", "extension", "list"]:
        version = proc.stdout.strip()
        return bool(version), (f"v{version}" if version else "missing — run: az extension add --name databricks")
    first = (proc.stdout.strip() or proc.stderr.strip()).splitlines()
    return proc.returncode == 0, (first[0] if first else "")


def registration(project: Path = PROJECT) -> dict[str, str]:
    launch = f"uv run --quiet --frozen --project {project} wa-agent-mcp"
    args = json.dumps(["run", "--quiet", "--frozen", "--project", project.as_posix(), "wa-agent-mcp"])
    return {
        "Claude Code": f"claude mcp add --scope user databricks-wa -- {launch}   (or open the repo: .mcp.json is included)",
        "Codex CLI": f"codex mcp add databricks-wa -- {launch}",
        "Cursor": "open the repo (.cursor/mcp.json is included), then enable it in Settings → MCP",
        "VS Code (Copilot)": f'.vscode/mcp.json: {{"servers": {{"databricks-wa": {{"type": "stdio", "command": "uv", '
                             f'"args": {args}}}}}}}',
        "Gemini CLI": f'~/.gemini/settings.json: {{"mcpServers": {{"databricks-wa": {{"command": "uv", "args": {args}}}}}}}',
    }


REDACTION_NOTE = ("Output is redacted (IDs, names, emails, tokens) and safe to paste into an issue. "
                  "Use --show-ids to see identifiers locally.")


def run(out=None, show_ids: bool = False) -> int:
    out = RedactingWriter(out or sys.stdout, enabled=not show_ids)
    ok = True
    if not show_ids:
        print(REDACTION_NOTE + "\n", file=out)
    print(f"platform: {platform.system()} {platform.release()} ({platform.machine()}) · agent catalog loaded locally",
          file=out)
    for cloud in CLOUDS:
        try:
            cat = catalog_mod.load(cloud)
            print(f"✔ catalog {cloud}: {len(cat['checks'])} checks, {len(cat['baselines'])} baselines "
                  f"(v{cat['version']})", file=out)
        except Exception as exc:  # noqa: BLE001 - report any catalog failure
            ok = False
            print(f"✘ catalog {cloud}: {exc}", file=out)
    for label, cmd, required in PROBES:
        good, detail = _probe(cmd)
        if cmd[:3] == ["az", "account", "show"] and good:
            out.terms.add(detail)
        ok = ok and (good or not required)
        print(f"{'✔' if good else '•'} {label}: {detail}", file=out)
    print("\nRegister the MCP server (read-only tools):", file=out)
    for client, how in registration().items():
        print(f"  {client:<18} {how}", file=out)
    print("\nVerify in the assistant: Claude Code `/mcp`, Codex `codex mcp list`, Cursor Settings → MCP.", file=out)
    print(f"\nProblem? Open an issue: {ISSUES_URL} (paste this redacted output)", file=out)
    return 0 if ok else 1


# Preflight: what each data source returned during a real (read-only) scan.
SOURCES = [
    ("Azure: workspace", ("az", "databricks", "workspace", "show"), "Reader on the workspace resource group; `az login`"),
    ("Azure: subnets", ("az", "network", "vnet", "subnet", "show"), "Reader on the VNet (may be a hub/network subscription)"),
    ("Azure: workspace storage", ("az", "storage", "account", "show"), "Reader on the managed resource group"),
    ("Azure: private DNS", ("az", "network", "private-dns", "zone", "list"), "Reader on the DNS zone subscription"),
    ("Azure: diagnostic settings", ("az", "monitor", "diagnostic-settings", "list"), "Reader on the workspace"),
    ("Databricks: workspace API", ("databricks", "workspace-conf", "get-status"),
     "workspace admin profile (`databricks auth login --host <workspace-url>`), from an allowed network"),
    ("Databricks: account API", ("databricks", "account", "workspaces", "get"),
     "account admin profile (`databricks auth login --host https://accounts.azuredatabricks.net --account-id <id>`)"),
]


def preflight(workspace: str, profile: str | None, account_profile: str | None, out=None,
              show_ids: bool = False) -> int:
    out = RedactingWriter(out or sys.stdout, enabled=not show_ids)
    out.terms |= {workspace, profile or "", account_profile or ""}
    if not show_ids:
        print(REDACTION_NOTE + "\n", file=out)
    from .clouds.azure import live
    from .engine import UNKNOWN, assess

    calls: list[tuple[tuple, object]] = []

    def recording(args):
        result = live.cli_runner(args)
        calls.append((live.command_verb(args), result))
        return result

    try:
        facts = live.collect(workspace, run=recording, databricks_profile=profile, account_profile=account_profile)
    except RuntimeError as exc:
        print(f"✘ {exc}", file=out)
        return 1
    scan = facts["_scan"]
    arm = scan["resolved_to"]
    out.terms |= {scan.get("profile") or "", scan.get("account_profile") or "", scan.get("workspace_url") or "",
                  (facts.get("workspace") or {}).get("name") or "",
                  arm.split("/resourceGroups/")[-1].split("/")[0]}
    print(f"workspace : {arm}", file=out)
    profile_line = scan["profile"] or "— none (pass --profile)"
    if not scan["profile"]:
        listing = live.cli_runner(["databricks", "auth", "profiles", "-o", "json"]) or {}
        host = facts.get("_scan", {}).get("workspace_url") or ""
        stale = sorted(p["name"] for p in listing.get("profiles", [])
                       if host and host in str(p.get("host", "")).lower() and not p.get("valid"))
        out.terms |= set(stale)
        if stale:
            profile_line = (f"— '{stale[0]}' matches this workspace but its login check fails: the login expired, "
                            f"or the workspace IP access list blocks this network. Re-run "
                            f"`databricks auth login --profile {stale[0]}` from an allowed network")
    print(f"profile   : {profile_line}{'  (auto-matched)' if scan.get('profile_auto_matched') else ''}", file=out)
    print(f"account   : {scan['account_profile'] or '— none (pass --account-profile)'}"
          f"{'  (auto-matched)' if scan.get('account_profile_auto_matched') else ''}\n", file=out)
    for label, verb, fix in SOURCES:
        results = [r for v, r in calls if v == verb]
        if not results:
            status, note = "• skipped", ("no profile" if verb[0] == "databricks" else "not needed for this workspace")
        elif any(r == live.IP_ACL_BLOCKED for r in results):
            status, note = "◐ blocked", "IP access list rejected this network (proves lists are enforced); " + fix
        elif verb[0] == "databricks" and not scan["profile"] and verb != ("databricks", "account", "workspaces", "get"):
            status, note = "✘ no login", "needs a valid workspace profile (see 'profile' above)"
        elif all(r is not None for r in results):
            status, note = "✔ ok", ""
        else:
            status, note = "✘ failed", fix
        print(f"  {status:<10} {label:<28} {note}", file=out)
    result = assess(catalog_mod.load("azure"), facts)
    unknown = [f for f in result.findings if f.status == UNKNOWN]
    evaluable = len(result.findings) - len(unknown)
    print(f"\n{evaluable}/{len(result.findings)} checks evaluable; detected pattern: "
          f"{result.detected['id'] if result.detected else 'none'}", file=out)
    if unknown:
        print("not evaluable: " + ", ".join(sorted(f.check['id'] for f in unknown)), file=out)
    print(f"\nProblem? Open an issue: {ISSUES_URL} (paste this redacted output)", file=out)
    print("\nNothing was changed. Run the scan: wa-agent collect live --cloud azure --workspace "
          f"{workspace!r} -o ws.facts.json", file=out)
    return 0
