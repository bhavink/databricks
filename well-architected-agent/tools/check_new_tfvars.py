"""Release check: every tfvar `wa-agent new` emits must be accepted by the real
Terraform root and resolve to the baseline's value when layered as the run book
layers it (inputs.tfvars, then each stage). Needs `terraform`; no cloud
access.

Values are evaluated against the deployment's variable definitions only (types
and validation rules), in a scratch root with no providers or modules: no
`init`, no provider downloads, and no provider auth that could stall in CI.

    python tools/check_new_tfvars.py [repo-root]
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wa_agent import catalog  # noqa: E402
from wa_agent.clouds import CLOUDS  # noqa: E402
from wa_agent.new import (_variable_blocks, apply_answers, auto_tfvars, builds, check_build,  # noqa: E402
                          generate, inputs_file, roots, stage_root)

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
    # GCP (gcpdb4u roots)
    "databricks_account_console_url": "https://accounts.gcp.databricks.com",
    "databricks_admin_user": "admin@example.com",
    "databricks_workspace_name": "wacheck-ws",
    "google_project_id": "wacheck-prj",
    "google_project_number": "123456789012",
    "google_region": "us-central1",
    "google_vpc_id": "wacheck-vpc",
    "workspace_subnet": "wacheck-subnet",
    "workspace_subnet_cidr": "10.0.0.0/24",
    "google_service_account_email": "automation-sa@wacheck-prj.iam.gserviceaccount.com",
    "metastore_name": "wacheck-ms",
    "network_name": "wacheck-vpc",
}
# The user's known IP ranges (`--set allowed_ip_ranges=...`), required by every build.
ANSWERS = {"allowed_ip_ranges": ["203.0.113.0/24", "198.51.100.10/32"]}
# Values a stage reads from an earlier root's `terraform output`.
OUTPUT_SAMPLES = {"workspace_url": "https://1111111111111111.1.gcp.databricks.com"}
ENV = {"TF_VAR_databricks_account_id": "00000000-0000-0000-0000-000000000000",
       "TF_INPUT": "0"}  # never prompt: a missing value must fail, not hang CI
TIMEOUT = 120


def fill(text: str) -> str:
    """Replace every REPLACE_ME_<name> (whole value or inside a string) with its sample."""
    def sample(m):
        name = m.group(1)
        if name not in SAMPLES:
            raise SystemExit(f"no sample value for placeholder REPLACE_ME_{name}; add it to SAMPLES")
        return SAMPLES[name]
    return re.sub(r"REPLACE_ME_([A-Za-z0-9_]+)", sample, text)


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


def resolves(want, got) -> bool:
    """`got` is what Terraform resolved: objects may carry extra optional attributes at their defaults."""
    if isinstance(want, dict) and isinstance(got, dict):
        return all(k in got and resolves(v, got[k]) for k, v in want.items())
    if isinstance(want, list) and isinstance(got, list):
        return len(want) == len(got) and all(resolves(a, b) for a, b in zip(want, got))
    return want == got


def option_sets(b: dict, build: dict) -> list[tuple[str, ...]]:
    """No options, each option alone, and all of them, minus combinations the build can't do."""
    ids = [o["id"] for o in b.get("options") or []]
    sets = [(), *[(i,) for i in ids], tuple(ids)]
    blocked = [set(u["options"]) for u in build.get("unsupported") or []]
    return [s for s in dict.fromkeys(sets) if not any(x <= set(s) for x in blocked)]


def check(cat: dict, b: dict, build: dict, repo: Path, tmp: Path, options=()) -> list[str]:
    """Failures for one build: every root's values must resolve as the run book layers them."""
    failures = []
    tag = "-".join((cat["cloud"], b["id"], build["id"], *options))
    out = tmp / tag
    generate(cat, b["id"], str(out), dict(ANSWERS), build_id=build["id"], options=options)
    rendered = apply_answers(check_build(b, repo, build["id"], options), dict(ANSWERS))
    for root in roots(rendered):
        stages = [(i, st) for i, st in enumerate(rendered["stages"], 1) if stage_root(rendered, st) == root]
        var_files = [f"-var-file={repo / root / name}" for name in auto_tfvars(repo / root, repo)]
        var_files += [f"-var-file={repo / root / st['copy_example']}" for _, st in stages if st.get("copy_example")]
        for name in [inputs_file(rendered, root)] + [f"stage-{i}-{st['name']}.tfvars" for i, st in stages]:
            filled = out / f"filled-{name}"
            filled.write_text(fill((out / name).read_text(encoding="utf-8")), encoding="utf-8")
            var_files.append(f"-var-file={filled}")
        extra = [f"-var={var}={OUTPUT_SAMPLES[src['output']]}"
                 for _, st in stages for var, src in (st.get("outputs") or {}).items()]
        expected = {}
        for _, st in stages:
            expected.update(json.loads(fill(json.dumps(st["tfvars"]))))
        expr = "jsonencode({" + ", ".join(f"{k} = var.{k}" for k in sorted(expected)) + "})" if expected else '"none"'
        scratch = variables_only(repo / root, tmp / f"vars-{tag}-{Path(root).name}")
        proc = run(["terraform", "console", "-no-color", *var_files, *extra], scratch, input=expr)
        # console exits 0 even when a validation rule rejects a value
        if proc.returncode != 0 or "Error:" in proc.stderr:
            failures.append(f"{root}: {proc.stderr.strip() or proc.stdout}")
            continue
        if expected:
            got = json.loads(json.loads(proc.stdout.strip().splitlines()[-1]))
            diff = {k: (got[k], v) for k, v in expected.items() if not resolves(v, got[k])}
            if diff:
                failures.append(f"{root}: {json.dumps(diff)}")
    return failures


def main(repo_root: str | None = None) -> int:
    repo = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
    failures = 0
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for cloud in CLOUDS:
            cat = catalog.load(cloud)
            for b in cat["baselines"]:
                for build in builds(b):
                    for options in option_sets(b, build):
                        built = check_build(b, repo, build["id"], options)
                        problems = check(cat, b, build, repo, tmp, options)
                        label = (f"{cloud} {b['id']}" + (f" [{build['id']}]" if build["id"] != "default" else "")
                                 + "".join(f" +{o}" for o in options))
                        if problems:
                            failures += 1
                            print(f"FAIL {label}: " + " | ".join(problems), flush=True)
                        else:
                            n = sum(len(st["tfvars"]) for st in built["stages"])
                            print(f"ok   {label}: {n} tfvars resolve as intended in {', '.join(roots(built))}",
                                  flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
