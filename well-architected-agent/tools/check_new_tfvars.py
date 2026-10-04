"""Release check: every tfvar `wa-agent new` emits must be accepted by the real
deployment and resolve to the baseline's value when layered on the
deployment's terraform.tfvars.example. Needs `terraform`; no cloud access.

    python tools/check_new_tfvars.py /path/to/initialized/adb4u/copy
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wa_agent import catalog  # noqa: E402
from wa_agent.new import generate  # noqa: E402

FILL = {
    "cidr": "203.0.113.0/24",
    "log_analytics_workspace_resource_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg"
                                           "/providers/Microsoft.OperationalInsights/workspaces/law",
}


def fill(text: str) -> str:
    out = []
    for line in text.splitlines():
        if "REPLACE_ME_" in line:
            key = next(k for k in FILL if k in line)
            start = line.index('"REPLACE_ME_')
            end = line.index('"', start + 1) + 1
            line = line[:start] + json.dumps(FILL[key]) + line[end:]
        out.append(line)
    return "\n".join(out) + "\n"


def main(adb4u_copy: str) -> int:
    root = Path(adb4u_copy).resolve()
    cat = catalog.load("azure")
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for b in [b for b in cat["baselines"] if b.get("build")]:
            out = Path(tmp) / b["id"]
            generate(cat, b["id"], str(out))
            dep = root / b["build"]["deployment"].removeprefix("adb4u/")
            var_files = [f"-var-file={dep / 'terraform.tfvars.example'}"]
            expected = {}
            for i, stage in enumerate(b["build"]["stages"], 1):
                filled = out / f"stage-{i}.filled.tfvars"
                filled.write_text(fill((out / f"stage-{i}-{stage['name']}.tfvars").read_text(encoding="utf-8")))
                var_files.append(f"-var-file={filled}")
                expected.update(stage["tfvars"])
            expr = "jsonencode({" + ", ".join(f"{k} = var.{k}" for k in sorted(expected)) + "})"
            proc = subprocess.run(["terraform", "console", "-no-color", *var_files], input=expr,
                                  capture_output=True, text=True, cwd=dep)
            if proc.returncode != 0:
                print(f"FAIL {b['id']}: {proc.stderr.strip().splitlines()[-1] if proc.stderr else proc.stdout}")
                failures += 1
                continue
            got = json.loads(json.loads(proc.stdout.strip().splitlines()[-1]))
            # Placeholder values are the user's to fill; compare everything else exactly.
            want = {k: v for k, v in expected.items() if "REPLACE_ME_" not in json.dumps(v)}
            got = {k: got[k] for k in want}
            if got != want:
                print(f"FAIL {b['id']}: {json.dumps({k: (got[k], want[k]) for k in got if got[k] != want[k]})}")
                failures += 1
            else:
                print(f"ok   {b['id']}: {len(expected)} tfvars accepted, {len(want)} resolve as intended "
                      f"in {b['build']['deployment']}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
