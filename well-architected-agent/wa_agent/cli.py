"""Command line interface.

  python -m wa_agent demo                       # no setup: full report from a real, sanitized recording
  python -m wa_agent doctor [--workspace <name>]  # prerequisites; preflight a real scan
  python -m wa_agent baselines --cloud azure
  python -m wa_agent patterns --cloud azure
  python -m wa_agent collect tfplan --cloud azure --plan plan.json -o facts.json
  python -m wa_agent collect live --cloud azure --workspace <arm id> [--profile P] [--account-profile A] -o facts.json
  python -m wa_agent new --baseline classic-full-pl --option cmk --out ./my-ws \
      --set location=eastus2 --set allowed_ip_ranges='["203.0.113.0/24"]'
  python -m wa_agent verify --tf-json state.json --baseline classic-full-pl --option cmk
  python -m wa_agent assess --cloud azure --facts facts.json [--facts more.json] \
      [--set workspace.compute_mode=serverless] [--baseline classic-full-pl] [--option public-access] \
      [--format md|json] [--fail-on-gaps]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import catalog as catalog_mod
from . import report
from .engine import assess
from .clouds import CLOUDS, collector
from .facts import apply_override, canonical, merge


def _write(text: str, path: str | None):
    if path:
        # Rule 1: never modify an existing artifact; outputs go to new files only.
        target = Path(path)
        if target.exists():
            raise ValueError(f"{path} already exists; the agent never overwrites files, choose a new path")
        target.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def cmd_patterns(args) -> int:
    cat = catalog_mod.load(args.cloud)
    for p in sorted(cat["patterns"]["patterns"], key=lambda p: (p["compute_mode"], p["tier"], p["id"])):
        print(f"{p['id']:<28} tier {p['tier']}  {p['compute_mode']:<10} {p['name']}")
    return 0


def cmd_baselines(args) -> int:
    cat = catalog_mod.load(args.cloud)
    for b in cat["baselines"]:
        extra = f"  +{len(b['require'])} required" if b.get("require") else ""
        print(f"{b['id']:<34} {b['pattern']:<26} {b['deployment']}{extra}")
        print(f"{'':<34} {b['use_case'].strip()}")
    print("\nDetails: wa-agent show <baseline>", file=sys.stderr)
    return 0


def cmd_show(args) -> int:
    from .describe import to_markdown

    _write(to_markdown(catalog_mod.load(args.cloud), args.baseline), args.output)
    return 0


def cmd_diagram(args) -> int:
    from .diagram import to_markdown

    _write(to_markdown(json.loads(Path(args.tf_json).read_text(encoding="utf-8")), args.workspace), args.output)
    return 0


def cmd_collect(args) -> int:
    module = collector(args.cloud, args.source)
    if args.source == "tfplan":
        facts = module.collect(json.loads(Path(args.plan).read_text(encoding="utf-8")), workspace=args.workspace)
    else:
        facts = module.collect(args.workspace, databricks_profile=args.profile, account_profile=args.account_profile)
    _write(canonical(facts), args.output)
    return 0


def cmd_assess(args) -> int:
    cat = catalog_mod.load(args.cloud)
    facts: dict = {}
    for path in args.facts:
        facts = merge(facts, json.loads(Path(path).read_text(encoding="utf-8")))
    for assignment in args.set or []:
        apply_override(facts, assignment)
    result = assess(cat, facts, args.target, args.baseline, args.option or ())
    render = report.to_json if args.format == "json" else report.to_markdown
    _write(render(result, cat, facts), args.output)
    if args.fail_on_gaps and not result.score["conformant"]:
        return 1
    return 0


def cmd_verify(args) -> int:
    """Post-apply validation: did the deployment do what the baseline requires?"""
    cat = catalog_mod.load(args.cloud)
    doc = json.loads(Path(args.tf_json).read_text(encoding="utf-8"))
    facts = collector(args.cloud, "tfplan").collect(doc, workspace=args.workspace)
    kind = "state" if facts["source"] == "terraform-state" else "plan"  # before extra facts are merged
    for path in args.facts or []:
        facts = merge(facts, json.loads(Path(path).read_text(encoding="utf-8")))
    result = assess(cat, facts, baseline_id=args.baseline, options=args.option or ())
    render = report.to_json if args.format == "json" else report.to_markdown
    _write(render(result, cat, facts), args.output)
    score = result.score
    verdict = "PASS" if score["conformant"] else "FAIL"
    print(f"verify {verdict}: Terraform {kind} vs baseline {args.baseline} — "
          f"{score['required_passed']}/{score['required_evaluated']} required controls passed, "
          f"{score['required_unknown']} not evaluable", file=sys.stderr)
    return 0 if score["conformant"] else 1


def cmd_new(args) -> int:
    from .new import generate, parse_answer

    cat = catalog_mod.load(args.cloud)
    answers = {}
    for assignment in args.set or []:
        name, sep, raw = assignment.partition("=")
        if not sep or not name:
            raise ValueError(f"--set {assignment!r}: expected name=value")
        answers[name.strip()] = parse_answer(raw)
    written = generate(cat, args.baseline, args.out, answers, build_id=args.build, options=args.option or ())
    for path in written:
        print(path)
    print(f"next: read {args.out}/README.md — you run Terraform; the agent changes nothing", file=sys.stderr)
    return 0


def cmd_doctor(args) -> int:
    from .doctor import preflight, run

    if args.workspace:
        return preflight(args.workspace, args.profile, args.account_profile, show_ids=args.show_ids)
    return run(show_ids=args.show_ids)


DEMO_FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "azure" / "live-backend-pl-ws1.calls.json"


def cmd_demo(args) -> int:
    """Full assessment of a real (sanitized) workspace recording. No cloud access."""
    from .clouds.azure import live

    cat = catalog_mod.load("azure")
    facts = live.replay(json.loads(DEMO_FIXTURE.read_text(encoding="utf-8")))
    result = assess(cat, facts, baseline_id=args.baseline)
    print("DEMO: replaying a sanitized recording of a real Azure workspace; no cloud calls are made.\n",
          file=sys.stderr)
    _write(report.to_markdown(result, cat, facts), args.output)
    return 0


def _utf8_stdio() -> None:
    # Output uses ✔ ✘ → —; Windows consoles and redirects default to legacy code pages.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv=None) -> int:
    _utf8_stdio()
    parser = argparse.ArgumentParser(prog="wa_agent", description="Databricks Well-Architected agent (deterministic core)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("patterns", help="list reference patterns")
    p.add_argument("--cloud", default="azure", choices=CLOUDS)
    p.set_defaults(func=cmd_patterns)

    b = sub.add_parser("baselines", help="list use-case baselines")
    b.add_argument("--cloud", default="azure", choices=CLOUDS)
    b.set_defaults(func=cmd_baselines)

    s = sub.add_parser("show", help="what a baseline (or pattern) requires, in plain language")
    s.add_argument("baseline", help="baseline or pattern id (see `baselines`, `patterns`)")
    s.add_argument("--cloud", default="azure", choices=CLOUDS)
    s.add_argument("-o", "--output")
    s.set_defaults(func=cmd_show)

    g = sub.add_parser("diagram", help="architecture diagram + resource manifest from a Terraform plan or state")
    g.add_argument("--tf-json", required=True, help="terraform show -json output (plan or state)")
    g.add_argument("--workspace", help="workspace address or name, when there are several")
    g.add_argument("-o", "--output")
    g.set_defaults(func=cmd_diagram)

    c = sub.add_parser("collect", help="collect normalized facts (read-only)")
    c.add_argument("source", choices=["tfplan", "live"])
    c.add_argument("--cloud", default="azure", choices=CLOUDS)
    c.add_argument("--plan", help="terraform show -json output (tfplan)")
    c.add_argument("--workspace", help="live: name, URL, numeric id or ARM id; tfplan: address or name "
                   "when the plan has several workspaces")
    c.add_argument("--profile", help="Databricks CLI workspace profile (default: auto-match by host)")
    c.add_argument("--account-profile", help="Databricks CLI account profile (default: auto-match if unique)")
    c.add_argument("-o", "--output")
    c.set_defaults(func=cmd_collect)

    a = sub.add_parser("assess", help="assess facts against a reference pattern")
    a.add_argument("--cloud", default="azure", choices=CLOUDS)
    a.add_argument("--facts", action="append", required=True, help="facts JSON (repeatable; merged)")
    a.add_argument("--set", action="append", help="override a fact: path=value")
    a.add_argument("--baseline", help="use-case baseline id (see `baselines`); default: detected pattern")
    a.add_argument("--target", help="raw target pattern id (advanced; see `patterns`)")
    a.add_argument("--option", action="append", metavar="ID",
                    help="baseline option to hold the workspace to (repeatable; see `show <baseline>`)")
    a.add_argument("--format", choices=["md", "json"], default="md")
    a.add_argument("--fail-on-gaps", action="store_true", help="exit 1 if required controls fail or are unknown")
    a.add_argument("-o", "--output")
    a.set_defaults(func=cmd_assess)

    v = sub.add_parser("verify", help="validate a Terraform state (or plan) against a baseline")
    v.add_argument("--cloud", default="azure", choices=CLOUDS)
    v.add_argument("--tf-json", required=True, help="terraform show -json output (state after apply, or a plan)")
    v.add_argument("--baseline", required=True, help="baseline the deployment was meant to build")
    v.add_argument("--option", action="append", metavar="ID",
                    help="baseline option to hold the workspace to (repeatable; see `show <baseline>`)")
    v.add_argument("--facts", action="append", help="extra facts to merge (e.g. live account-level facts)")
    v.add_argument("--workspace", help="workspace address or name, when the state has several workspaces")
    v.add_argument("--format", choices=["md", "json"], default="md")
    v.add_argument("-o", "--output")
    v.set_defaults(func=cmd_verify)

    n = sub.add_parser("new", help="deployment folder for a new workspace from a baseline's tested Terraform")
    n.add_argument("--cloud", default="azure", choices=CLOUDS)
    n.add_argument("--baseline", required=True)
    n.add_argument("--out", required=True, help="new directory to create (must not exist)")
    n.add_argument("--build", help="which build, when the baseline offers several (see `show <baseline>`)")
    n.add_argument("--option", action="append", metavar="ID",
                    help="baseline option to hold the workspace to (repeatable; see `show <baseline>`)")
    n.add_argument("--set", action="append", metavar="NAME=VALUE",
                   help="answer a Terraform variable (repeatable); JSON values for lists/booleans")
    n.set_defaults(func=cmd_new)

    d = sub.add_parser("doctor", help="check prerequisites; with --workspace, preflight a real scan (read-only)")
    d.add_argument("--workspace", help="workspace name, URL, numeric id or ARM id to preflight")
    d.add_argument("--profile", help="Databricks CLI workspace profile (default: auto-match by host)")
    d.add_argument("--account-profile", help="Databricks CLI account profile (default: auto-match if unique)")
    d.add_argument("--show-ids", action="store_true", help="do not redact identifiers (local use only)")
    d.set_defaults(func=cmd_doctor)

    m = sub.add_parser("demo", help="see a full report from a real, sanitized workspace recording (no setup)")
    m.add_argument("--baseline", default="classic-full-pl")
    m.add_argument("-o", "--output")
    m.set_defaults(func=cmd_demo)

    args = parser.parse_args(argv)
    if args.command == "collect":
        if args.source == "tfplan" and not args.plan:
            parser.error("tfplan requires --plan")
        if args.source == "live" and not args.workspace:
            parser.error("live requires --workspace")
    try:
        return args.func(args)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("If this looks like a bug, open an issue with the output of `wa-agent doctor` (it is redacted): "
              "https://github.com/bhavink/databricks/issues/new?template=wa-agent-problem.yml", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
