"""Load and validate the pattern + check catalogs."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

CATALOG_ROOT = Path(__file__).resolve().parent.parent / "catalog"

PILLARS = {
    "data_ai_governance",
    "interoperability_usability",
    "operational_excellence",
    "security",
    "reliability",
    "performance_efficiency",
    "cost_optimization",
}
SEVERITIES = ("critical", "high", "medium", "low")
FIX_TYPES = {"in_place", "recreate", "additive", "manual"}
# tested: deployed and verified by the repo owner. validated: terraform
# validate + mock-provider tests only, not yet applied.
MATURITY = {"tested", "validated"}
OPS = {"equals", "not_equals", "in", "gte", "lte"}
# Official sources a check must cite at least one of. Repo paths (no
# scheme) are the ground-truth implementation and are optional.
OFFICIAL_DOC_PREFIXES = (
    "https://docs.databricks.com/",
    "https://learn.microsoft.com/",
    "https://www.databricks.com/blog/",
    "https://cloud.google.com/",
    "https://docs.aws.amazon.com/",
)


class CatalogError(ValueError):
    pass


def _validate_rule(rule, where: str):
    if not isinstance(rule, dict):
        raise CatalogError(f"{where}: rule must be a mapping")
    for key in ("all_of", "any_of"):
        if key in rule:
            for i, sub in enumerate(rule[key]):
                _validate_rule(sub, f"{where}.{key}[{i}]")
            return
    if "not" in rule:
        _validate_rule(rule["not"], f"{where}.not")
        return
    if "fact" not in rule or rule.get("op") not in OPS:
        raise CatalogError(f"{where}: needs 'fact' and op in {sorted(OPS)}")


def validate(patterns: dict, checks: list[dict]) -> None:
    ids = [c["id"] for c in checks]
    if len(ids) != len(set(ids)):
        raise CatalogError("duplicate check ids")
    for c in checks:
        where = c.get("id", "<no id>")
        for key in ("id", "title", "pillar", "severity", "rule", "rationale", "sources", "remediation"):
            if key not in c:
                raise CatalogError(f"{where}: missing {key}")
        if c["pillar"] not in PILLARS:
            raise CatalogError(f"{where}: unknown pillar {c['pillar']}")
        if c["severity"] not in SEVERITIES:
            raise CatalogError(f"{where}: unknown severity {c['severity']}")
        if not any(src.startswith(OFFICIAL_DOC_PREFIXES) for src in c["sources"]):
            raise CatalogError(f"{where}: must cite at least one official doc")
        if c["remediation"].get("fix_type") not in FIX_TYPES:
            raise CatalogError(f"{where}: unknown fix_type")
        if c["remediation"].get("maturity", "tested") not in MATURITY:
            raise CatalogError(f"{where}: unknown maturity")
        if not isinstance(c["remediation"].get("caveats", []), list):
            raise CatalogError(f"{where}: caveats must be a list")
        _validate_rule(c["rule"], f"{where}.rule")
        if "when" in c:
            _validate_rule(c["when"], f"{where}.when")

    known = set(ids)
    pattern_ids = {p["id"] for p in patterns["patterns"]}
    if set(patterns["detection_order"]) != pattern_ids:
        raise CatalogError("detection_order must list every pattern exactly once")
    for p in patterns["patterns"]:
        _validate_rule(p["signature"], f"{p['id']}.signature")
        for ref in p["required"] + p["recommended"]:
            if ref not in known:
                raise CatalogError(f"{p['id']}: references unknown check {ref}")


def validate_baselines(baselines: list[dict], patterns: dict, checks: list[dict]) -> None:
    pattern_ids = {p["id"] for p in patterns["patterns"]}
    check_ids = {c["id"] for c in checks}
    ids = [b["id"] for b in baselines]
    if len(ids) != len(set(ids)):
        raise CatalogError("duplicate baseline ids")
    for b in baselines:
        for key in ("id", "name", "use_case", "pattern", "deployment"):
            if key not in b:
                raise CatalogError(f"baseline {b.get('id', '<no id>')}: missing {key}")
        if b["pattern"] not in pattern_ids:
            raise CatalogError(f"baseline {b['id']}: unknown pattern {b['pattern']}")
        for ref in b.get("require") or []:
            if ref not in check_ids:
                raise CatalogError(f"baseline {b['id']}: references unknown check {ref}")
        if b.get("build"):
            _validate_build(b["id"], b["build"], check_ids)


def _validate_build(bid: str, build: dict, check_ids: set) -> None:
    where = f"baseline {bid} build"
    if ("deployment" in build) == ("source" in build):
        raise CatalogError(f"{where}: needs exactly one of deployment (repo) or source (external)")
    if "source" in build:
        src = build["source"]
        for key in ("repo", "ref", "path", "variables", "required"):
            if key not in src:
                raise CatalogError(f"{where}: source missing {key}")
        if not re.fullmatch(r"[0-9a-f]{40}", src["ref"]):
            raise CatalogError(f"{where}: source.ref must be a full commit SHA (reviewed, immutable)")
        if not src["repo"].startswith("https://github.com/databricks/"):
            raise CatalogError(f"{where}: external sources must be official Databricks repositories")
        if set(src["required"]) - set(src["variables"]):
            raise CatalogError(f"{where}: required lists undeclared variables")
    if not build.get("stages"):
        raise CatalogError(f"{where}: needs at least one stage")
    for gap in build.get("known_gaps") or []:
        if gap.get("check") not in check_ids or not gap.get("reason"):
            raise CatalogError(f"{where}: known_gaps entries need a known check and a reason")


def load_controls(root: Path = CATALOG_ROOT) -> dict:
    data = yaml.safe_load((root / "controls.yaml").read_text(encoding="utf-8"))
    ids = [c["id"] for c in data["controls"]]
    if len(ids) != len(set(ids)):
        raise CatalogError("duplicate control ids")
    for c in data["controls"]:
        if c["phase"] not in data["phases"]:
            raise CatalogError(f"control {c['id']}: unknown phase {c['phase']}")
        if c["pillar"] not in PILLARS:
            raise CatalogError(f"control {c['id']}: unknown pillar {c['pillar']}")
    return data


def attach_controls(checks: list[dict], controls: dict, cloud: str) -> None:
    by_id = {c["id"]: c for c in controls["controls"]}
    for c in checks:
        control = by_id.get(c.get("control"))
        if control is None:
            raise CatalogError(f"{c['id']}: unknown or missing control {c.get('control')!r}")
        if control["pillar"] != c["pillar"]:
            raise CatalogError(f"{c['id']}: pillar {c['pillar']} differs from control {control['id']} ({control['pillar']})")
        phase = controls["phases"][control["phase"]]
        c["phase"] = control["phase"]
        c["phase_name"] = phase["name"]
        c["guide_url"] = controls["guide"][cloud] + phase["slug"]


def load(cloud: str, root: Path = CATALOG_ROOT) -> dict:
    base = root / cloud
    patterns = yaml.safe_load((base / "patterns.yaml").read_text(encoding="utf-8"))
    checks = yaml.safe_load((base / "checks.yaml").read_text(encoding="utf-8"))["checks"]
    validate(patterns, checks)
    controls = load_controls(root)
    attach_controls(checks, controls, cloud)
    baselines_file = base / "baselines.yaml"
    baselines = yaml.safe_load(baselines_file.read_text(encoding="utf-8"))["baselines"] if baselines_file.exists() else []
    validate_baselines(baselines, patterns, checks)
    return {"version": patterns["catalog_version"], "cloud": cloud, "patterns": patterns, "checks": checks,
            "baselines": baselines, "controls": controls}
