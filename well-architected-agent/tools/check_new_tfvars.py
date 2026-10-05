"""Release check: every tfvar `wa-agent new` emits must be accepted by the real
Terraform root and resolve to the baseline's value when layered as the run book
layers it (inputs.tfvars, then each stage). Needs `terraform`; no cloud
access.

Values are evaluated against the deployment's variable definitions only (types
and validation rules), in a scratch root with no providers or modules: no
`init`, no provider downloads, and no provider auth that could stall in CI.

    python tools/check_new_tfvars.py /path/to/adb4u
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wa_agent import catalog  # noqa: E402
from wa_agent.new import _variable_blocks, deployment_variables, generate  # noqa: E402

# Sample value for every REPLACE_ME_<name> placeholder the catalog emits. A new
# placeholder without a sample fails the check, so this list stays complete.
SAMPLES = {
    "corporate_egress_cidr": "203.0.113.0/24",
    "terraform_runner_egress_cidr": "203.0.113.0/24",
    "log_analytics_workspace_resource_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg"
                                           "/providers/Microsoft.OperationalInsights/workspaces/law",
    "managed_services_cmk_key_uri": "https://kv-wacheck.vault.azure.net/keys/cmk/0123456789abcdef0123456789abcdef",
    "storage_account_resource_id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg"
                                   "/providers/Microsoft.Storage/storageAccounts/stwacheck",
    "workspace_prefix": "wacheck",
    "resource_group_name": "rg-wacheck",
    "location": "eastus2",
    "metastore_id": "00000000-0000-0000-0000-000000000001",
    "tag_owner": "owner@example.com",
    "tag_keepuntil": "12/31/2030",
}
ENV = {"TF_VAR_databricks_account_id": "00000000-0000-0000-0000-000000000000",
       "TF_INPUT": "0"}  # never prompt: a missing value must fail, not hang CI
TIMEOUT = 120


def fill(text: str) -> str:
    out = []
    for line in text.splitlines():
        while '"REPLACE_ME_' in line:
            start = line.index('"REPLACE_ME_')
            end = line.index('"', start + 1) + 1
            name = line[start + len('"REPLACE_ME_'):end - 1]
            if name not in SAMPLES:
                raise SystemExit(f"no sample value for placeholder REPLACE_ME_{name}; add it to SAMPLES")
            line = line[:start] + json.dumps(SAMPLES[name]) + line[end:]
        out.append(line)
    return "\n".join(out) + "\n"


def run(cmd, cwd, **kw):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**os.environ, **ENV},
                              timeout=TIMEOUT, **kw)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 1, "", f"timed out after {TIMEOUT}s: {' '.join(cmd[:3])}")


def variables_only(root: Path, scratch: Path) -> Path:
    """Scratch root holding just the variable blocks of `root`."""
    scratch.mkdir(parents=True)
    blocks = [f'variable "{name}" {{{body}}}\n' for tf in sorted(root.glob("*.tf"))
              for name, body in _variable_blocks(tf.read_text(encoding="utf-8"))]
    (scratch / "variables.tf").write_text("\n".join(blocks), encoding="utf-8")
    return scratch


def main(adb4u_copy: str) -> int:
    root = Path(adb4u_copy).resolve()
    cat = catalog.load("azure")
    failures = 0
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for b in [b for b in cat["baselines"] if b.get("build")]:
            build = b["build"]
            dep, where = root / build["deployment"].removeprefix("adb4u/"), build["deployment"]
            out = tmp / b["id"]
            generate(cat, b["id"], str(out))
            var_files, expected = [], {}
            names = ["inputs.tfvars"] + [f"stage-{i}-{s['name']}.tfvars" for i, s in enumerate(build["stages"], 1)]
            for name in names:
                filled = out / f"filled-{name}"
                filled.write_text(fill((out / name).read_text(encoding="utf-8")), encoding="utf-8")
                var_files.append(f"-var-file={filled}")
            for stage in build["stages"]:
                expected.update(stage["tfvars"])
            expr = "jsonencode({" + ", ".join(f"{k} = var.{k}" for k in sorted(expected)) + "})"
            scratch = variables_only(dep, tmp / f"vars-{b['id']}")
            proc = run(["terraform", "console", "-no-color", *var_files], scratch, input=expr)
            # console exits 0 even when a validation rule rejects a value
            if proc.returncode != 0 or "Error:" in proc.stderr:
                print(f"FAIL {b['id']}: {proc.stderr.strip() or proc.stdout}", flush=True)
                failures += 1
                continue
            got = json.loads(json.loads(proc.stdout.strip().splitlines()[-1]))
            # Placeholder values are the user's to fill; compare everything else exactly.
            want = {k: v for k, v in expected.items() if "REPLACE_ME_" not in json.dumps(v)}
            got = {k: got[k] for k in want}
            if got != want:
                print(f"FAIL {b['id']}: {json.dumps({k: (got[k], want[k]) for k in got if got[k] != want[k]})}", flush=True)
                failures += 1
            else:
                print(f"ok   {b['id']}: {len(expected)} tfvars accepted, {len(want)} resolve as intended in {where}",
                      flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
