"""Plain-language view of a baseline or pattern: its controls by production
guide phase, with check ids only as references. Deterministic."""

from __future__ import annotations

from .engine import apply_baseline

LEVELS = ("required", "recommended")


def label(catalog: dict, check_id: str) -> str:
    """`Title (ID)` for one check, for any list shown to people."""
    check = next(c for c in catalog["checks"] if c["id"] == check_id)
    return f"{check['title']} (`{check_id}`)"


def _target(catalog: dict, ref: str) -> tuple[dict, dict | None]:
    patterns = {p["id"]: p for p in catalog["patterns"]["patterns"]}
    baselines = {b["id"]: b for b in catalog["baselines"]}
    if ref in baselines:
        baseline = baselines[ref]
        return apply_baseline(patterns[baseline["pattern"]], baseline), baseline
    if ref in patterns:
        return patterns[ref], None
    raise ValueError(f"unknown baseline or pattern {ref!r}; choose from {sorted(baselines) + sorted(patterns)}")


def controls(catalog: dict, ref: str) -> list[dict]:
    """Every control of a baseline (or pattern), ordered by phase, level, check id."""
    target, _ = _target(catalog, ref)
    checks = {c["id"]: c for c in catalog["checks"]}
    rows = []
    for level in LEVELS:
        for cid in target[level]:
            c = checks[cid]
            rows.append({"area": c["phase_name"], "phase": c["phase"], "level": level, "control": c["title"],
                         "check": cid, "pillar": c["pillar"], "severity": c["severity"],
                         "guide": c["guide_url"]})
    return sorted(rows, key=lambda r: (r["phase"], LEVELS.index(r["level"]), r["check"]))


def to_markdown(catalog: dict, ref: str) -> str:
    target, baseline = _target(catalog, ref)
    title = baseline["name"] if baseline else target["name"]
    lines = [f"# {title}", ""]
    if baseline:
        lines += [baseline["use_case"].strip(), "",
                  f"Reference pattern: {target['name']} · Builds it: {_where(baseline)}", ""]
    else:
        lines += [target["summary"].strip(), ""]
    rows = controls(catalog, ref)
    req = sum(r["level"] == "required" for r in rows)
    lines += [f"{req} required and {len(rows) - req} recommended controls, by area of the production planning guide.",
              ""]
    area = None
    for r in rows:
        if r["area"] != area:
            area = r["area"]
            lines += ([""] if lines[-1] else []) + [f"## {area}", "", "| Level | Control | Check |", "|---|---|---|"]
        mark = "Required" if r["level"] == "required" else "Recommended"
        lines.append(f"| {mark} | {r['control']} | `{r['check']}` |")
    return "\n".join(lines) + "\n"


def _where(baseline: dict) -> str:
    build = baseline.get("build") or {}
    if "deployment" in build:
        return f"`{build['deployment']}`"
    if "source" in build:
        return f"official Databricks SRA `{build['source']['path']}` @ `{build['source']['ref'][:7]}`"
    return f"`{baseline['deployment']}`"
