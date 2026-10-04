"""Normalized facts: merge, override and canonical serialization."""

from __future__ import annotations

import hashlib
import json

COMPUTED = "(known after apply)"
# Facts key holding provenance: fact path -> sources it was read from.
EVIDENCE = "_evidence"


def merge(base: dict, other: dict) -> dict:
    """Combine facts from several sources (e.g. a network plan and an
    account-level plan). Order-independent: booleans OR, numbers max,
    other scalars keep the first non-null value."""
    out = dict(base)
    for key, value in other.items():
        if value is None:
            continue
        if key == EVIDENCE:
            merged = {k: list(v) for k, v in (out.get(EVIDENCE) or {}).items()}
            for path, sources in value.items():
                merged[path] = sorted(set(merged.get(path, [])) | set(sources))
            out[EVIDENCE] = merged
            continue
        current = out.get(key)
        if current is None:
            out[key] = value
        elif isinstance(current, dict) and isinstance(value, dict):
            out[key] = merge(current, value)
        elif isinstance(current, bool) and isinstance(value, bool):
            out[key] = current or value
        elif isinstance(current, (int, float)) and isinstance(value, (int, float)):
            out[key] = max(current, value)
        else:
            out[key] = min(current, value, key=lambda v: json.dumps(v, sort_keys=True))
    return out


def apply_override(facts: dict, assignment: str) -> dict:
    """Apply `path=value` (value parsed as JSON, else string)."""
    path, _, raw = assignment.partition("=")
    if not path or not _:
        raise ValueError(f"override must be path=value, got {assignment!r}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = raw
    node = facts
    parts = path.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
    return facts


def canonical(facts: dict) -> str:
    return json.dumps(facts, sort_keys=True, indent=2) + "\n"


def digest(facts: dict, catalog_version: str) -> str:
    payload = json.dumps({"facts": facts, "catalog": catalog_version}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
