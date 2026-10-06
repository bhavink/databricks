"""Drift check: every official doc the catalog cites must resolve, and every
ground-truth repo path must exist. Run in CI on change and weekly.

    python tools/check_links.py
"""

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wa_agent import catalog  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def references(cat: dict) -> dict[str, list[str]]:
    refs: dict[str, list[str]] = {}
    for c in cat["checks"]:
        for s in c["sources"] + ([c["remediation"]["module"]] if c["remediation"].get("module") else []):
            refs.setdefault(s, []).append(c["id"])
    for p in cat["patterns"]["patterns"]:
        for s in p["references"]:
            refs.setdefault(s, []).append(p["id"])
    controls = cat["controls"]
    for phase in controls["phases"].values():
        for cloud_guide in controls["guide"].values():
            refs.setdefault(cloud_guide + phase["slug"], []).append(f"phase:{phase['slug']}")
    for b in cat["baselines"]:
        refs.setdefault(b["deployment"], []).append(b["id"])
        for build in ([b["build"]] if b.get("build") else []) + (b.get("builds") or []):
            for root in [build.get("deployment")] + [st.get("deployment") for st in build.get("stages") or []]:
                if root:
                    refs.setdefault(root, []).append(b["id"])
    return refs


def _fetch(url: str) -> tuple[bool, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "wa-agent-link-check"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status == 200, str(resp.status)
    except urllib.error.HTTPError as e:
        return False, str(e.code)
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        return False, type(e).__name__


def url_ok(url: str, attempts: int = 3) -> tuple[bool, str]:
    """A URL is broken only if it fails every attempt (absorbs transient network errors)."""
    detail = ""
    for attempt in range(attempts):
        ok, detail = _fetch(url)
        if ok or detail == "404":
            return ok, detail
        time.sleep(2 ** attempt)
    return False, detail


def main() -> int:
    failures = 0
    from wa_agent.clouds import CLOUDS

    for cloud in CLOUDS:
        for ref, users in sorted(references(catalog.load(cloud)).items()):
            ok, detail = url_ok(ref) if ref.startswith("http") else ((REPO_ROOT / ref).exists(), "missing path")
            if not ok:
                failures += 1
                print(f"BROKEN {ref} ({detail}) used by {', '.join(sorted(set(users)))}")
    print("all references resolve" if not failures else f"{failures} broken reference(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
