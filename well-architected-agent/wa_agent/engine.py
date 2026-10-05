"""Deterministic rules engine.

Rules are evaluated with three-valued logic: True, False, or None (unknown,
because a referenced fact is missing). The same facts + catalog always
produce the same result; no network calls, clocks or randomness here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"

_MISSING = object()


def get_fact(facts: dict, path: str):
    node = facts
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node or node[part] is None:
            return _MISSING
        node = node[part]
    return node


_OPS = {
    "equals": lambda actual, expected: actual == expected,
    "not_equals": lambda actual, expected: actual != expected,
    "in": lambda actual, expected: actual in expected,
    "gte": lambda actual, expected: actual >= expected,
    "lte": lambda actual, expected: actual <= expected,
}


def evaluate(rule: dict, facts: dict, missing: set[str]) -> bool | None:
    """Evaluate a rule; adds unresolved fact paths to `missing`."""
    if "all_of" in rule:
        results = [evaluate(r, facts, missing) for r in rule["all_of"]]
        if False in results:
            return False
        return None if None in results else True
    if "any_of" in rule:
        results = [evaluate(r, facts, missing) for r in rule["any_of"]]
        if True in results:
            return True
        return None if None in results else False
    if "not" in rule:
        result = evaluate(rule["not"], facts, missing)
        return None if result is None else not result

    actual = get_fact(facts, rule["fact"])
    if actual is _MISSING:
        missing.add(rule["fact"])
        return None
    return _OPS[rule["op"]](actual, rule.get("value"))


@dataclass
class Finding:
    check: dict
    status: str
    missing_facts: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)


def _rule_facts(rule: dict) -> list[str]:
    for key in ("all_of", "any_of"):
        if key in rule:
            return [f for r in rule[key] for f in _rule_facts(r)]
    if "not" in rule:
        return _rule_facts(rule["not"])
    return [rule["fact"]]


def run_check(check: dict, facts: dict) -> Finding:
    missing: set[str] = set()
    if "when" in check:
        applies = evaluate(check["when"], facts, missing)
        if applies is False:
            return Finding(check, NOT_APPLICABLE)
        if applies is None:
            return Finding(check, UNKNOWN, sorted(missing))

    result = evaluate(check["rule"], facts, missing)
    evidence = {}
    for path in sorted(set(_rule_facts(check["rule"]))):
        value = get_fact(facts, path)
        evidence[path] = None if value is _MISSING else value
    if result is None:
        return Finding(check, UNKNOWN, sorted(missing), evidence)
    return Finding(check, PASS if result else FAIL, [], evidence)


def detect_pattern(patterns: dict, facts: dict) -> dict | None:
    """First pattern (in detection_order) whose signature is True."""
    by_id = {p["id"]: p for p in patterns["patterns"]}
    for pattern_id in patterns["detection_order"]:
        if evaluate(by_id[pattern_id]["signature"], facts, set()) is True:
            return by_id[pattern_id]
    return None


@dataclass
class Assessment:
    detected: dict | None
    target: dict
    findings: list[Finding]
    baseline: dict | None = None

    def tier_of(self, check_id: str) -> str:
        if check_id in self.target["required"]:
            return "required"
        if check_id in self.target["recommended"]:
            return "recommended"
        return "advisory"

    @property
    def score(self) -> dict:
        required = [f for f in self.findings if self.tier_of(f.check["id"]) == "required"]
        counted = [f for f in required if f.status in (PASS, FAIL)]
        passed = sum(1 for f in counted if f.status == PASS)
        unknown = sum(1 for f in required if f.status == UNKNOWN)
        return {
            "required_passed": passed,
            "required_evaluated": len(counted),
            "required_unknown": unknown,
            "conformant": bool(counted) and passed == len(counted) and unknown == 0,
        }


def apply_baseline(pattern: dict, baseline: dict) -> dict:
    """The baseline's pattern with its extra checks promoted to required."""
    extra = list(baseline.get("require") or [])
    target = dict(pattern)
    target["required"] = pattern["required"] + [c for c in extra if c not in pattern["required"]]
    target["recommended"] = [c for c in pattern["recommended"] if c not in extra]
    return target


def assess(catalog: dict, facts: dict, target_id: str | None = None, baseline_id: str | None = None) -> Assessment:
    patterns = catalog["patterns"]
    by_id = {p["id"]: p for p in patterns["patterns"]}
    detected = detect_pattern(patterns, facts)
    findings = [run_check(c, facts) for c in catalog["checks"]]
    if baseline_id:
        if target_id:
            raise ValueError("pass either --baseline or --target, not both")
        baselines = {b["id"]: b for b in catalog.get("baselines", [])}
        if baseline_id not in baselines:
            raise ValueError(f"unknown baseline {baseline_id!r}; choose from {sorted(baselines)}")
        baseline = baselines[baseline_id]
        return Assessment(detected, apply_baseline(by_id[baseline["pattern"]], baseline), findings, baseline)
    if target_id:
        if target_id not in by_id:
            raise ValueError(f"unknown target pattern {target_id!r}; choose from {sorted(by_id)}")
        target = by_id[target_id]
    elif detected:
        target = detected
    else:
        raise ValueError("could not detect a pattern from facts; pass --baseline or --target")
    return Assessment(detected, target, findings)
