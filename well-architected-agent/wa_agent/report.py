"""Render an Assessment as Markdown or JSON. Output is byte-stable for the
same facts + catalog: fixed sort order, no timestamps."""

from __future__ import annotations

import json

from .engine import FAIL, NOT_APPLICABLE, PASS, UNKNOWN, Assessment
from .clouds import collection_hints
from .describe import label
from .facts import digest

REPO_URL = "https://github.com/bhavink/databricks/blob/master/"
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
TIER_ORDER = {"required": 0, "recommended": 1, "advisory": 2}



READ_ONLY_NOTICE = (
    "This is read-only analysis: the agent made no changes to the workspace, the cloud tenant, "
    "Terraform or any other artifact. What to apply, and when, is your decision."
)


def _source_link(src: str) -> str:
    return src if src.startswith("http") else f"[{src}]({REPO_URL}{src})"


MATURITY_LABEL = {
    "tested": "tested",
    "validated": "validated (terraform validate + mock tests); not yet apply-tested",
}


def _grounding(check: dict) -> list[str]:
    docs = [s for s in check["sources"] if s.startswith("http")]
    repo = [s for s in check["sources"] if not s.startswith("http")]
    maturity = MATURITY_LABEL[check["remediation"].get("maturity", "tested")]
    lines = [f"**Production planning guide:** [Phase {check['phase']}: {check['phase_name']}]({check['guide_url']})",
             "**Official docs:** " + " · ".join(docs)]
    if repo:
        lines.append(f"**Ground-truth repo ({maturity}):** " + " · ".join(_source_link(s) for s in repo))
    else:
        lines.append("**Ground-truth repo:** not implemented in bhavink/databricks yet; the fix below follows the official docs.")
    return lines


def _evidence_lines(finding, facts: dict) -> list[str]:
    sources = facts.get("_evidence") or {}
    lines = ["**Evidence:**", ""]
    for path, value in finding.evidence.items():
        origin = "; ".join(sources.get(path) or ["source not recorded"])
        lines.append(f"- `{path}` = `{json.dumps(value)}` — from `{origin}`")
    return lines


def _sorted(assessment: Assessment, findings):
    return sorted(
        findings,
        key=lambda f: (
            TIER_ORDER[assessment.tier_of(f.check["id"])],
            SEVERITY_ORDER[f.check["severity"]],
            f.check["id"],
        ),
    )


def _upgrade_path(assessment: Assessment, catalog: dict) -> list[dict]:
    """Higher-tier patterns of the same compute mode and what blocks them."""
    status = {f.check["id"]: f.status for f in assessment.findings}
    current = assessment.target
    rows = []
    for p in catalog["patterns"]["patterns"]:
        if p["compute_mode"] != current["compute_mode"] or p["tier"] <= current["tier"]:
            continue
        blocking = sorted(c for c in p["required"] if status[c] != PASS)
        rows.append({"id": p["id"], "name": p["name"], "tier": p["tier"], "blocking": blocking})
    return sorted(rows, key=lambda r: (r["tier"], r["id"]))


def phase_coverage(assessment: Assessment, catalog: dict) -> list[dict]:
    """Per deployment-guide phase: how many controls the catalog checks and their outcome."""
    rows = []
    for number, phase in sorted(catalog["controls"]["phases"].items()):
        findings = [f for f in assessment.findings if f.check["phase"] == number]
        counts = {s: sum(1 for f in findings if f.status == s) for s in (PASS, FAIL, UNKNOWN, NOT_APPLICABLE)}
        rows.append({
            "phase": number,
            "name": phase["name"],
            "guide_url": catalog["controls"]["guide"][catalog["cloud"]] + phase["slug"],
            "checks": len(findings),
            **{s.lower(): n for s, n in counts.items()},
        })
    return rows


def to_dict(assessment: Assessment, catalog: dict, facts: dict) -> dict:
    return {
        "cloud": catalog["cloud"],
        "catalog_version": catalog["version"],
        "facts_digest": digest(facts, catalog["version"]),
        "workspace": (facts.get("workspace") or {}).get("name"),
        "detected_pattern": assessment.detected["id"] if assessment.detected else None,
        "target_pattern": assessment.target["id"],
        "baseline": assessment.baseline["id"] if assessment.baseline else None,
        "score": assessment.score,
        "findings": [
            {
                "id": f.check["id"],
                "control": f.check["control"],
                "phase": f.check["phase"],
                "title": f.check["title"],
                "pillar": f.check["pillar"],
                "severity": f.check["severity"],
                "tier": assessment.tier_of(f.check["id"]),
                "status": f.status,
                "evidence": {k: {"value": v, "from": (facts.get("_evidence") or {}).get(k, [])}
                             for k, v in f.evidence.items()},
                "missing_facts": f.missing_facts,
                "remediation": f.check["remediation"] if f.status == FAIL else None,
                "sources": f.check["sources"],
            }
            for f in _sorted(assessment, assessment.findings)
        ],
        "upgrade_path": _upgrade_path(assessment, catalog),
        "phase_coverage": phase_coverage(assessment, catalog),
        "notice": READ_ONLY_NOTICE,
    }


def to_json(assessment: Assessment, catalog: dict, facts: dict) -> str:
    return json.dumps(to_dict(assessment, catalog, facts), indent=2, sort_keys=True) + "\n"


def to_markdown(assessment: Assessment, catalog: dict, facts: dict) -> str:
    data = to_dict(assessment, catalog, facts)
    target = assessment.target
    score = data["score"]
    by_status = {s: [f for f in _sorted(assessment, assessment.findings) if f.status == s]
                 for s in (FAIL, UNKNOWN, PASS, NOT_APPLICABLE)}
    lines = [
        f"# Well-Architected assessment — {data['workspace'] or 'unnamed workspace'}",
        "",
        "| | |",
        "|---|---|",
        f"| Cloud | {data['cloud']} |",
        f"| Detected pattern | {assessment.detected['name'] if assessment.detected else 'none'} |",
        *([f"| Baseline | **{assessment.baseline['name']}** (`{assessment.baseline['id']}`) |",
           f"| Builds it | {_source_link(assessment.baseline['deployment'])} |"] if assessment.baseline else []),
        f"| Target pattern | **{target['name']}** (`{target['id']}`) |",
        f"| Required controls | {score['required_passed']}/{score['required_evaluated']} passed, "
        f"{score['required_unknown']} not evaluable |",
        f"| Conformant | {'yes' if score['conformant'] else 'no'} |",
        *([f"| Scanned with | profile `{facts['_scan'].get('profile') or '—'}`, account profile "
           f"`{facts['_scan'].get('account_profile') or '—'}` |"] if facts.get("_scan") else []),
        f"| Catalog / facts digest | {data['catalog_version']} / `{data['facts_digest']}` |",
        "",
        f"> {target['summary']}",
        "",
    ]
    if assessment.baseline:
        lines += [f"Baseline: {assessment.baseline['use_case'].strip()}", ""]
        extra = assessment.baseline.get("require") or []
        if extra:
            lines += ["Baseline adds required controls:", ""] + [f"- {label(catalog, c)}" for c in extra] + [""]
    if assessment.detected and assessment.detected["id"] != target["id"]:
        lines += [f"Detected `{assessment.detected['id']}`; scoring against the declared target `{target['id']}`.", ""]
    if assessment.detected and assessment.detected["compute_mode"] != target["compute_mode"]:
        lines += [f"> **Compute mode mismatch:** the workspace is `{assessment.detected['compute_mode']}`, "
                  f"the target is `{target['compute_mode']}`. Moving between them means a new workspace.", ""]

    gaps = [f for f in by_status[FAIL] if assessment.tier_of(f.check["id"]) != "advisory"]
    advisory = [f for f in by_status[FAIL] if assessment.tier_of(f.check["id"]) == "advisory"]

    lines += ["## Prescription", ""]
    if gaps:
        lines += ["In priority order (required before recommended, then by severity):", ""]
        for i, f in enumerate(gaps, 1):
            r = f.check["remediation"]
            warn = " ⚠️ has caveats" if r.get("caveats") else ""
            lines.append(f"{i}. **{f.check['id']}** — {r['summary'].strip()} "
                         f"(`{assessment.tier_of(f.check['id'])}`, `{f.check['severity']}`, fix: `{r['fix_type']}`){warn}")
        lines.append("")
    else:
        lines += ["No gaps against the target. Nothing to change.", ""]
    if by_status[UNKNOWN]:
        lines += [f"{len(by_status[UNKNOWN])} check(s) could not be evaluated; see *Not evaluable* before "
                  "treating this as complete.", ""]
    lines += [f"_{READ_ONLY_NOTICE}_", ""]

    lines += [f"## Gaps against target ({len(gaps)})", ""]
    if not gaps:
        lines += ["None.", ""]
    for f in gaps:
        c, r = f.check, f.check["remediation"]
        lines += [
            f"### {c['id']} — {c['title']}",
            "",
            f"`{assessment.tier_of(c['id'])}` · `{c['severity']}` · `{c['pillar']}` · "
            f"phase {c['phase']} {c['phase_name']} · `{c['control']}` · fix: `{r['fix_type']}`",
            "",
            c["rationale"].strip(),
            "",
            *_evidence_lines(f, facts),
            "",
            *_grounding(c),
            "",
            f"**Prescription:** {r['summary'].strip()} Implementation: {_source_link(r['module'])}",
            "",
            "```hcl",
            r["terraform"].rstrip(),
            "```",
            "",
        ]
        if r.get("cli"):
            lines += ["```bash", r["cli"].strip(), "```", ""]
        if r.get("caveats"):
            lines += ["**Before you apply:**", ""] + [f"- ⚠️ {cv.strip()}" for cv in r["caveats"]] + [""]

    if advisory:
        lines += [f"## Beyond target ({len(advisory)})", "",
                  "Controls from higher-tier patterns; see the upgrade path. Full fixes are in `--format json`.", ""]
        lines += [f"- {f.check['id']} — {f.check['title']} (`{f.check['severity']}`)" for f in advisory]
        lines.append("")

    lines += [f"## Not evaluable ({len(by_status[UNKNOWN])})", ""]
    if by_status[UNKNOWN]:
        lines += ["| Check | Tier | Missing fact | How to collect |", "|---|---|---|---|"]
        for f in by_status[UNKNOWN]:
            for fact in f.missing_facts or ["?"]:
                hint = collection_hints(catalog["cloud"]).get(fact.split(".")[0], "")
                lines.append(f"| {f.check['id']} {f.check['title']} | {assessment.tier_of(f.check['id'])} | `{fact}` | {hint} |")
        lines.append("")
    else:
        lines += ["None.", ""]

    lines += [f"## Passed ({len(by_status[PASS])})", ""]
    lines += [f"- {f.check['id']} — {f.check['title']} ({assessment.tier_of(f.check['id'])})" for f in by_status[PASS]] or ["None."]
    lines += ["", f"## Not applicable ({len(by_status[NOT_APPLICABLE])})", ""]
    lines += [f"- {f.check['id']} — {f.check['title']}" for f in by_status[NOT_APPLICABLE]] or ["None."]

    if data["upgrade_path"]:
        lines += ["", "## Upgrade path", "", "| Pattern | Tier | Required controls not yet passing |", "|---|---|---|"]
        for row in data["upgrade_path"]:
            blocking = "<br>".join(label(catalog, c) for c in row["blocking"]) or "none"
            lines.append(f"| {row['name']} (`{row['id']}`) | {row['tier']} | {blocking} |")
    lines += ["", "## Coverage by production planning phase", "",
              "Phases of the Databricks production planning guide and what this assessment checks in each. "
              "Phases with no checks are not covered by the agent yet; review them with the guide.", "",
              "| Phase | Checks | Pass | Fail | Not evaluable | N/A |", "|---|---|---|---|---|---|"]
    for row in data["phase_coverage"]:
        name = f"[{row['phase']}. {row['name']}]({row['guide_url']})"
        if row["checks"]:
            lines.append(f"| {name} | {row['checks']} | {row['pass']} | {row['fail']} | {row['unknown']} | "
                         f"{row['not_applicable']} |")
        else:
            lines.append(f"| {name} | — | | | | _not covered yet_ |")
    lines += ["", "References: " + " · ".join(_source_link(s) for s in target["references"]), "",
              "---", "", f"_{READ_ONLY_NOTICE}_", ""]
    return "\n".join(lines)

