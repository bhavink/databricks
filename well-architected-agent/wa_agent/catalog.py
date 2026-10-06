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
    for ref in patterns.get("minimum_required") or []:
        if ref not in known:
            raise CatalogError(f"minimum_required references unknown check {ref}")
    pattern_ids = {p["id"] for p in patterns["patterns"]}
    if set(patterns["detection_order"]) != pattern_ids:
        raise CatalogError("detection_order must list every pattern exactly once")
    for p in patterns["patterns"]:
        _validate_rule(p["signature"], f"{p['id']}.signature")
        for ref in p["required"] + p["recommended"]:
            if ref not in known:
                raise CatalogError(f"{p['id']}: references unknown check {ref}")


def validate_external(external: dict) -> None:
    """External Terraform a build may reference: pinned to a commit, never copied into this repo."""
    for eid, e in external.items():
        for key in ("name", "repo", "commit", "path", "license", "variables", "required"):
            if not e.get(key):
                raise CatalogError(f"external {eid}: missing {key}")
        if not e["repo"].startswith("https://github.com/") or not re.fullmatch(r"[0-9a-f]{40}", e["commit"]):
            raise CatalogError(f"external {eid}: needs a GitHub repo and a full 40-character commit")
        if not set(e["required"]) <= set(e["variables"]):
            raise CatalogError(f"external {eid}: required lists variables it doesn't declare")


def validate_baselines(baselines: list[dict], patterns: dict, checks: list[dict], external: dict | None = None) -> None:
    external = external or {}
    validate_external(external)
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
        _validate_options(b, check_ids, set(patterns.get("minimum_required") or []))
        if b.get("build") and b.get("builds"):
            raise CatalogError(f"baseline {b['id']}: use either build or builds, not both")
        if b.get("build"):
            _validate_build(b["id"], b["build"], check_ids, external)
        ids = [x.get("id") for x in b.get("builds") or []]
        if len(ids) != len(set(ids)) or None in ids:
            raise CatalogError(f"baseline {b['id']}: every build needs a unique id")
        for x in b.get("builds") or []:
            if not x.get("for"):
                raise CatalogError(f"baseline {b['id']} build {x['id']}: say who it is for (`for`)")
            _validate_build(f"{b['id']}:{x['id']}", x, check_ids, external)


def _validate_options(b: dict, check_ids: set, minimum: set) -> None:
    options = b.get("options") or []
    ids = [o.get("id") for o in options]
    if len(ids) != len(set(ids)) or None in ids:
        raise CatalogError(f"baseline {b['id']}: every option needs a unique id")
    builds = b.get("builds") or ([{"id": "default", **b["build"]}] if b.get("build") else [])
    by_build = {x["id"]: {st["name"] for st in x["stages"]} for x in builds}
    for o in options:
        where = f"baseline {b['id']} option {o['id']}"
        if not o.get("name") or not o.get("summary"):
            raise CatalogError(f"{where}: needs a name and a summary")
        for ref in (o.get("require") or []) + (o.get("waive") or []):
            if ref not in check_ids:
                raise CatalogError(f"{where}: references unknown check {ref}")
        if set(o.get("waive") or []) & minimum:
            raise CatalogError(f"{where}: the bare minimum can't be waived")
        for entry in o.get("set") or []:
            targets = entry.get("builds") or list(by_build)
            for bid in targets:
                if bid not in by_build:
                    raise CatalogError(f"{where}: unknown build {bid}")
                if entry.get("stage") not in by_build[bid]:
                    raise CatalogError(f"{where}: build {bid} has no stage {entry.get('stage')!r}")
    for x in builds:
        for u in x.get("unsupported") or []:
            if not set(u.get("options") or []) <= set(ids) or not u.get("options") or not u.get("reason"):
                raise CatalogError(f"baseline {b['id']} build {x['id']}: unsupported entries need known options "
                                   "and a reason")


def _validate_build(bid: str, build: dict, check_ids: set, external: dict) -> None:
    where = f"baseline {bid} build"
    if build.get("external"):
        # The one exception to repo-only builds: pinned external Terraform, cloned by the user.
        if build["external"] not in external:
            raise CatalogError(f"{where}: unknown external {build['external']!r}")
        if build.get("deployment") or any(st.get("deployment") for st in build.get("stages") or []):
            raise CatalogError(f"{where}: an external build runs its external root only")
    elif "source" in build or not (build.get("deployment")
                                   or all(st.get("deployment") for st in build.get("stages") or [])):
        raise CatalogError(f"{where}: builds must use a deployment in this repo (deployment: <path>)")
    if not build.get("stages"):
        raise CatalogError(f"{where}: needs at least one stage")
    for i, stage in enumerate(build["stages"], 1):
        if stage.get("ip_access_list") not in (None, "tfvar", "file"):
            raise CatalogError(f"{where} stage {i}: ip_access_list is tfvar or file")
        if stage.get("ip_access_list_var") and stage.get("ip_access_list") != "tfvar":
            raise CatalogError(f"{where} stage {i}: ip_access_list_var needs ip_access_list: tfvar")
        for var, src in (stage.get("outputs") or {}).items():
            if not isinstance(src, dict) or not 1 <= src.get("stage", 0) < i or not src.get("output"):
                raise CatalogError(f"{where} stage {i}: output {var} must come from an earlier stage")
    for gap in build.get("known_gaps") or []:
        if gap.get("check") not in check_ids or not gap.get("reason"):
            raise CatalogError(f"{where}: known_gaps entries need a known check and a reason")


def apply_minimum(patterns: dict) -> None:
    """Make the cloud's bare-minimum checks required in every pattern."""
    minimum = patterns.get("minimum_required") or []
    for p in patterns["patterns"]:
        p["required"] = list(minimum) + [c for c in p["required"] if c not in minimum]
        p["recommended"] = [c for c in p["recommended"] if c not in minimum]


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
    apply_minimum(patterns)
    controls = load_controls(root)
    attach_controls(checks, controls, cloud)
    baselines_file = base / "baselines.yaml"
    data = yaml.safe_load(baselines_file.read_text(encoding="utf-8")) if baselines_file.exists() else {}
    baselines, external = data.get("baselines") or [], data.get("external") or {}
    validate_baselines(baselines, patterns, checks, external)
    # Each external build carries its external definition, so `new` needs nothing else.
    for b in baselines:
        for x in ([b["build"]] if b.get("build") else []) + (b.get("builds") or []):
            if x.get("external"):
                x["external_def"] = dict(external[x["external"]], id=x["external"])
    return {"version": patterns["catalog_version"], "cloud": cloud, "patterns": patterns, "checks": checks,
            "baselines": baselines, "controls": controls, "external": external}
