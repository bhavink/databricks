"""New workspace: turn a baseline into a ready-to-run deployment folder.

The output is a new directory holding:

- the tested Terraform, copied from this repo (`terraform/`): only files
  tracked in git, so local tfvars, state or keys are never copied;
- inputs per Terraform root: required variables filled from `--set
  name=value` answers (unanswered ones are `REPLACE_ME_*`);
- one tfvars file per stage, layered on top of the inputs;
- a README with every command (plan -> assess -> apply -> verify).

A baseline offers one or more builds (e.g. one root that creates everything,
or a network root followed by a workspace root). With several, the user
picks one: builds are peers, there is no hidden default. A stage may run in
a different root than the one before it; stage values can refer to answers
(`${var.name}`) and to an earlier root's outputs (`outputs`).

Nothing existing is modified. The Terraform is used as-is; the user runs it
and `verify` checks the resulting state. Baselines without tested Terraform
have no build, and `new` refuses rather than improvise.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

from .catalog import CATALOG_ROOT

REPO_ROOT = CATALOG_ROOT.parent.parent
REPO_URL = "https://github.com/bhavink/databricks"
PLACEHOLDER = "REPLACE_ME"
# Set from the environment, never written to files.
DEFAULT_ENV = ("databricks_account_id",)
# Never bundled, even if someone committed them.
NEVER_BUNDLE = ("*.tfstate", "*.tfstate.*", "terraform.tfvars", "*.tfplan", "*.plan", "*-key.json",
                "*-credentials.json", "*.pem", "*.key", ".terraform.lock.hcl")
# Without git, only these are copied.
FALLBACK_SUFFIXES = (".tf", ".tftest.hcl", ".yaml", ".yml", ".md", ".sh")
FALLBACK_NAMES = ("terraform.tfvars.example", "terraform.tfvars.remove")
_LOCAL_SOURCE = re.compile(r'^\s*source\s*=\s*"(\.{1,2}/[^"]+)"', re.M)
_REF = re.compile(r"\$\{var\.([A-Za-z0-9_]+)\}")

SIGN_IN = {
    "azure": ["az login",
              "export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)"],
    "gcp": ["gcloud auth login",
            "export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)"],
}
LIVE_SCAN = {
    "azure": "wa-agent collect live --cloud azure --workspace <name-or-arm-id> --profile <ws> --account-profile <acct> "
             "-o live.facts.json",
    "gcp": "wa-agent collect live --cloud gcp --workspace <name-or-url> --profile <ws> --account-profile <acct> "
           "-o live.facts.json",
}


# ---------------------------------------------------------------- variables

def _variable_blocks(text: str):
    for m in re.finditer(r'^variable\s+"([A-Za-z0-9_]+)"\s*\{', text, re.M):
        i, depth = m.end(), 1
        while depth and i < len(text):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        yield m.group(1), text[m.end():i - 1]


def deployment_variables(directory: Path) -> dict[str, dict]:
    """name -> {"required": bool, "description": str} from every *.tf in a root."""
    out = {}
    for tf in sorted(directory.glob("*.tf")):
        for name, body in _variable_blocks(tf.read_text(encoding="utf-8")):
            desc = re.search(r'^\s*description\s*=\s*"((?:[^"\\]|\\.)*)"', body, re.M)
            out[name] = {
                "required": not re.search(r"^\s*default\s*=", body, re.M),
                "description": desc.group(1) if desc else "",
            }
    return out


def declared_variables(deployment: str, repo_root: Path = REPO_ROOT) -> set[str]:
    return set(deployment_variables(repo_root / deployment))


def example_assignments(directory: Path, names: list[str]) -> set[str]:
    """Variables assigned in a root's committed example config files."""
    found = set()
    for name in names:
        path = directory / name
        if path.is_file():
            found |= set(re.findall(r"^([A-Za-z0-9_]+)\s*=", path.read_text(encoding="utf-8"), re.M))
    return found


def auto_tfvars(directory: Path, repo_root: Path = REPO_ROOT) -> list[str]:
    """Committed *.auto.tfvars of a root (Terraform loads them automatically)."""
    tracked = _tracked(directory, repo_root)
    return sorted(p.name for p in directory.glob("*.auto.tfvars")
                  if tracked is None or p.relative_to(repo_root).as_posix() in tracked)


# ---------------------------------------------------------------- builds

def builds(baseline: dict) -> list[dict]:
    """The baseline's builds; a single `build` is a build with id "default"."""
    if baseline.get("builds"):
        return baseline["builds"]
    return [{"id": "default", **baseline["build"]}] if baseline.get("build") else []


def select_build(baseline: dict, build_id: str | None) -> dict:
    options = builds(baseline)
    if not options:
        raise ValueError(
            f"baseline {baseline['id']!r} has no tested deployment in this repo; it is for assessing "
            f"existing workspaces (assess, verify) against {baseline['deployment']}. "
            f"The agent does not improvise Terraform."
        )
    if build_id is None:
        if len(options) == 1:
            return options[0]
        listing = "; ".join(f"{b['id']} ({b.get('for', '').strip()})" for b in options)
        raise ValueError(f"baseline {baseline['id']!r} has several builds; choose one with --build: {listing}")
    for b in options:
        if b["id"] == build_id:
            return b
    raise ValueError(f"baseline {baseline['id']!r} has no build {build_id!r}; choose from {[b['id'] for b in options]}")


def stage_root(build: dict, stage: dict) -> str:
    return stage.get("deployment") or build["deployment"]


def roots(build: dict) -> list[str]:
    """Distinct Terraform roots, in the order stages first use them."""
    seen: list[str] = []
    for stage in build["stages"]:
        root = stage_root(build, stage)
        if root not in seen:
            seen.append(root)
    return seen


# ---------------------------------------------------------------- rendering

def _key(k: str) -> str:
    return k if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", k) else json.dumps(k)


def _hcl(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_hcl(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{_key(k)} = {_hcl(v)}" for k, v in sorted(value.items())) + " }"
    raise ValueError(f"unsupported tfvars value: {value!r}")


def _tfvars(header: list[str], values: dict) -> str:
    lines = header + [""]
    if values:
        width = max(len(k) for k in values)
        lines += [f"{k:<{width}} = {_hcl(v)}" for k, v in sorted(values.items())]
    return "\n".join(lines) + "\n"


def render_tfvars(baseline: dict, stage: dict, index: int) -> str:
    return _tfvars([
        f"# Stage {index}: {stage['name']} — baseline {baseline['id']}",
        "# Generated by wa-agent new. Layered after the inputs file; later -var-file arguments win.",
    ], stage["tfvars"])


def parse_answer(raw: str):
    """`--set` value: JSON when it parses (lists, booleans, numbers, objects), else a string."""
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def _substitute(value, known: dict):
    """Resolve `${var.name}` from answers and earlier stage values; unresolved -> REPLACE_ME_name."""
    if isinstance(value, str):
        whole = _REF.fullmatch(value)
        if whole and whole.group(1) in known:
            return known[whole.group(1)]
        return _REF.sub(lambda m: str(known[m.group(1)]) if m.group(1) in known else f"{PLACEHOLDER}_{m.group(1)}",
                        value)
    if isinstance(value, list):
        return [_substitute(v, known) for v in value]
    if isinstance(value, dict):
        return {_substitute(k, known): _substitute(v, known) for k, v in value.items()}
    return value


def apply_answers(build: dict, answers: dict | None) -> dict:
    """The build with answers replacing stage values for the same variable, and references resolved."""
    answers = answers or {}
    known = dict(answers)
    stages = []
    for stage in build["stages"]:
        tfvars = {k: answers.get(k, v) for k, v in stage["tfvars"].items()}
        tfvars = {k: _substitute(v, known) for k, v in tfvars.items()}
        for k, v in tfvars.items():
            if PLACEHOLDER not in json.dumps(v):
                known.setdefault(k, v)
        stages.append({**stage, "tfvars": tfvars})
    return {**build, "stages": stages}


def resolve_inputs(build: dict, answers: dict | None, repo_root: Path = REPO_ROOT) -> dict[str, dict]:
    """Per root: required variables not covered elsewhere, plus the answers that root declares."""
    env = set(build.get("env", DEFAULT_ENV))
    answers = dict(answers or {})
    for name in sorted(answers):
        if name in env:
            raise ValueError(f"--set {name}: set it with TF_VAR_{name} instead; it is never written to files")
    declared_any = set()
    out = {}
    for root in roots(build):
        directory = repo_root / root
        variables = deployment_variables(directory)
        declared_any |= set(variables)
        stages = [s for s in build["stages"] if stage_root(build, s) == root]
        staged = {k for s in stages for k in s["tfvars"]} | {k for s in stages for k in s.get("outputs") or {}}
        examples = auto_tfvars(directory, repo_root) + [s["copy_example"] for s in stages if s.get("copy_example")]
        covered = staged | env | example_assignments(directory, examples)
        values = {n: f"{PLACEHOLDER}_{n}" for n, v in variables.items() if v["required"] and n not in covered}
        values.update({k: v for k, v in answers.items() if k in variables and k not in staged})
        out[root] = values
    for name in sorted(answers):
        if name not in declared_any:
            raise ValueError(f"--set {name}: not a variable of {_where(build)}")
    return out


def inputs_file(build: dict, root: str) -> str:
    return "inputs.tfvars" if len(roots(build)) == 1 else f"inputs-{PurePosixPath(root).name}.tfvars"


def placeholders(build: dict, inputs: dict | None = None) -> list[str]:
    found = set()
    sources = [stage["tfvars"] for stage in build["stages"]] + list((inputs or {}).values())
    for tfvars in sources:
        for key, value in tfvars.items():
            if PLACEHOLDER in json.dumps(value):
                found.add(key)
    return sorted(found)


def _where(build: dict) -> str:
    return ", ".join(roots(build))


def check_build(baseline: dict, repo_root: Path = REPO_ROOT, build_id: str | None = None) -> dict:
    """The selected build, after checking every stage value is a declared variable of its root."""
    build = select_build(baseline, build_id)
    for stage in build["stages"]:
        root = stage_root(build, stage)
        unknown = sorted((set(stage["tfvars"]) | set(stage.get("outputs") or {})) - declared_variables(root, repo_root))
        if unknown:
            raise ValueError(f"baseline {baseline['id']} build {build['id']} stage {stage['name']}: "
                             f"not variables of {root}: {unknown}")
    return build


# ---------------------------------------------------------------- bundling

def _tracked(directory: Path, repo_root: Path) -> set[str] | None:
    """Files git would commit under a directory (tracked, or new and not ignored); None without git."""
    try:
        rel = directory.resolve().relative_to(repo_root.resolve()).as_posix()
        # tracked files plus new files git doesn't ignore (a user's real tfvars and state are ignored)
        out = subprocess.run(["git", "-C", str(repo_root), "ls-files", "--cached", "--others",
                              "--exclude-standard", "--", rel],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if out.returncode != 0:
        return None
    return set(out.stdout.split())


def _bundle_ok(name: str, tracked: bool) -> bool:
    if any(fnmatch.fnmatch(name, pat) for pat in NEVER_BUNDLE):
        return False
    return tracked or name.endswith(FALLBACK_SUFFIXES) or name in FALLBACK_NAMES


def bundle_files(deployment: str, repo_root: Path = REPO_ROOT) -> list[str]:
    """Repo-relative paths of a root and every local module it uses, transitively.

    In a git checkout only tracked files are copied (untracked or ignored files,
    such as a user's real tfvars, never are); without git, only Terraform,
    docs and config file types. State, plain tfvars, keys and caches never are.
    """
    seen, queue, files = set(), [PurePosixPath(deployment)], []
    in_git = _tracked(repo_root, repo_root) is not None
    while queue:
        rel = queue.pop()
        if rel in seen:
            continue
        seen.add(rel)
        directory = repo_root / rel
        tracked = _tracked(directory, repo_root) if in_git else None
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or ".terraform" in path.relative_to(directory).parts:
                continue
            relpath = path.relative_to(repo_root).as_posix()
            if in_git and relpath not in (tracked or set()):
                continue
            if _bundle_ok(path.name, in_git):
                files.append(relpath)
            if path.suffix == ".tf" and path.parent == directory:
                for src in _LOCAL_SOURCE.findall(path.read_text(encoding="utf-8")):
                    queue.append(PurePosixPath(_normalize(rel / src)))
    return sorted(set(files))


def _normalize(path: PurePosixPath) -> str:
    parts: list[str] = []
    for part in path.parts:
        if part == "..":
            if not parts:
                raise ValueError(f"module source escapes the repo: {path}")
            parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


def source_commit(repo_root: Path = REPO_ROOT) -> str:
    try:
        out = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() if out.returncode == 0 else "unknown"


def matches_commit(paths: list[str], repo_root: Path = REPO_ROOT) -> bool | None:
    """True when the bundled files are exactly the committed ones; None without git."""
    try:
        out = subprocess.run(["git", "-C", str(repo_root), "status", "--porcelain", "--", *paths],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return None if out.returncode != 0 else out.stdout.strip() == ""


# ---------------------------------------------------------------- run book

def render_readme(baseline: dict, build: dict, inputs: dict, commit: str, cloud: str,
                  repo_root: Path = REPO_ROOT) -> str:
    stages = build["stages"]
    env = list(build.get("env", DEFAULT_ENV))
    workspace = f" --workspace {build['workspace']}" if build.get("workspace") else ""
    links = ", ".join(f"[`{r}`]({REPO_URL}/tree/{commit}/{r})" for r in roots(build))
    named = build["id"] != "default"
    lines = [
        f"# New workspace — {baseline['name']}" + (f" (build `{build['id']}`)" if named else ""),
        "",
        f"Baseline `{baseline['id']}`: {baseline['use_case'].strip()}",
        "",
    ]
    if named:
        lines += [f"Build `{build['id']}`: {build.get('for', '').strip()}", ""]
    lines += [
        f"Tested Terraform: {links} at `{commit}`, copied into `terraform/`.",
        "",
        "> The agent changed nothing. You run every command below; verify afterwards.",
        "",
        "## 0. Prepare",
        "",
    ]
    if build.get("prepare"):
        lines += ["Once, before anything else:", ""] + [f"- {p.strip()}" for p in build["prepare"]] + [""]
    lines += ["```bash", "# from this folder (bash/zsh); never commit these values", 'export BOOK="$(pwd)"']
    lines += SIGN_IN.get(cloud, [])
    lines += [f"export TF_VAR_{name}=<{name}>" for name in env]
    lines += ["```", "",
              "PowerShell: `$env:BOOK = (Get-Location).Path` and `$env:TF_VAR_<name> = \"<value>\"`, "
              "then use `$env:BOOK` wherever `$BOOK` appears.", ""]
    examples = [f"`terraform/{r}/{n}`" for r in roots(build) for n in auto_tfvars(repo_root / r, repo_root)]
    if examples:
        lines += ["Edit the committed example config (values in `<angle brackets>` are placeholders; the "
                  "inputs and stage files override what they set): " + ", ".join(examples) + ".", ""]
    todo = placeholders(build, inputs)
    if todo:
        lines += ["Replace every `REPLACE_ME_*` value in the inputs and stage files: "
                  + ", ".join(f"`{k}`" for k in todo) + ".", ""]

    var_files: dict[str, list[str]] = {}
    initialized: set[str] = set()
    stage_dirs: list[str] = []
    for i, stage in enumerate(stages, 1):
        root = stage_root(build, stage)
        stage_dirs.append(root)
        files = var_files.setdefault(root, [f"-var-file=$BOOK/{inputs_file(build, root)}"])
        files.append(f"-var-file=$BOOK/stage-{i}-{stage['name']}.tfvars")
        lines += [f"## {i}. Stage: {stage['name']}" + (f" (`{root}`)" if len(roots(build)) > 1 else ""), ""]
        if stage.get("note"):
            lines += [f"> {stage['note'].strip()}", ""]
        lines += ["```bash", f'cd "$BOOK/terraform/{root}"']
        if stage.get("copy_example"):
            lines += [f"cp {stage['copy_example']} terraform.tfvars",
                      "# open terraform.tfvars and set every value (this root's own checklist)"]
        if root not in initialized:
            lines += ["terraform init"]
            initialized.add(root)
        outs = [f'-var "{var}=$(terraform -chdir="$BOOK/terraform/{stage_dirs[src["stage"] - 1]}" '
                f'output -raw {src["output"]})"' for var, src in sorted((stage.get("outputs") or {}).items())]
        lines += [
            f"terraform plan {' '.join(files + outs)} -out stage{i}.plan",
            f"terraform show -json stage{i}.plan > stage{i}.plan.json",
            f"wa-agent collect tfplan --cloud {cloud} --plan stage{i}.plan.json{workspace} -o stage{i}.facts.json",
            f"wa-agent assess --cloud {cloud} --facts stage{i}.facts.json --baseline {baseline['id']} "
            f"-o stage{i}.report.md",
            f"wa-agent diagram --tf-json stage{i}.plan.json{workspace} -o stage{i}.architecture.md",
            f"terraform apply stage{i}.plan",
            "```",
            "",
        ]
    multi = len(roots(build)) > 1
    lines += [
        f"## {len(stages) + 1}. Verify",
        "",
        "Check the deployed state against the baseline. Add live facts for controls that",
        "live outside Terraform state (e.g. manually approved private endpoint rules).",
        "",
        "```bash",
    ]
    if multi:
        facts = []
        for root in roots(build):
            short = PurePosixPath(root).name
            lines += [f'terraform -chdir="$BOOK/terraform/{root}" show -json > "$BOOK/state-{short}.json"']
            facts.append(f"--facts $BOOK/{short}.facts.json")
        for root in roots(build):
            short = PurePosixPath(root).name
            lines += [f"wa-agent collect tfplan --cloud {cloud} --plan $BOOK/state-{short}.json{workspace} "
                      f"-o $BOOK/{short}.facts.json"]
        lines += [f"wa-agent assess --cloud {cloud} {' '.join(facts)} --baseline {baseline['id']} -o $BOOK/verify.md",
                  f"wa-agent diagram --tf-json $BOOK/state-{PurePosixPath(roots(build)[-1]).name}.json "
                  "-o $BOOK/architecture.md"]
    else:
        lines += [
            f'cd "$BOOK/terraform/{stage_dirs[-1]}"',
            "terraform show -json > state.json",
            f"wa-agent verify --cloud {cloud} --tf-json state.json{workspace} --baseline {baseline['id']} -o verify.md",
            f"wa-agent diagram --tf-json state.json{workspace} -o architecture.md",
        ]
    lines += ["# optional, from a network the workspace allows:", LIVE_SCAN.get(cloud, LIVE_SCAN["azure"])]
    if not multi:
        lines += [f"wa-agent verify --cloud {cloud} --tf-json state.json{workspace} --facts live.facts.json "
                  f"--baseline {baseline['id']} -o verify-live.md"]
    lines += ["```", "", "Intermediate stages are expected to show gaps (for example public access still on)."]
    gaps = build.get("known_gaps") or []
    if gaps:
        lines += ["After the final stage, these gaps remain by design of the Terraform used; close them yourself:", ""]
        lines += [f"- `{g['check']}`: {g['reason'].strip()}" for g in gaps]
    else:
        lines += ["The final stage is the one that must verify as PASS."]
    lines += ["", "---", "",
              "_Provided as is, without warranty. Review and test before applying; you are responsible for what "
              "you deploy._", ""]
    return "\n".join(lines)


def render(catalog: dict, baseline_id: str, answers: dict | None = None, repo_root: Path = REPO_ROOT,
           book_dir: str | None = None, commit: str | None = None, build_id: str | None = None) -> dict[str, str]:
    """File name -> content for a baseline's run book (Terraform bundle excluded). Writes nothing.

    `book_dir` is accepted for compatibility; paths in the README are relative to $BOOK.
    """
    del book_dir
    baselines = {b["id"]: b for b in catalog["baselines"]}
    if baseline_id not in baselines:
        raise ValueError(f"unknown baseline {baseline_id!r}; choose from {sorted(baselines)}")
    baseline = baselines[baseline_id]
    build = apply_answers(check_build(baseline, repo_root, build_id), answers)
    commit = commit or source_commit(repo_root)
    inputs = resolve_inputs(build, answers, repo_root)
    cloud = catalog.get("cloud", "azure")

    files = {}
    for root, values in inputs.items():
        files[inputs_file(build, root)] = _tfvars([
            f"# Inputs for {root} — baseline {baseline_id}. Generated by wa-agent new; edit freely.",
            f"# Set {', '.join('TF_VAR_' + e for e in build.get('env', DEFAULT_ENV))} in the environment; "
            "never commit secrets.",
        ], values)
    for i, stage in enumerate(build["stages"], 1):
        files[f"stage-{i}-{stage['name']}.tfvars"] = render_tfvars(baseline, stage, i)
    files["README.md"] = render_readme(baseline, build, inputs, commit, cloud, repo_root)
    paths = sorted({p for root in roots(build) for p in bundle_files(root, repo_root)})
    manifest = {
        "baseline": baseline_id,
        "build": build["id"],
        "catalog_version": catalog["version"],
        "placeholders": placeholders(build, inputs),
        "deployments": roots(build),
        "source": REPO_URL,
        "commit": commit,
        "matches_commit": matches_commit(paths, repo_root),
        "files": {p: hashlib.sha256((repo_root / p).read_bytes()).hexdigest() for p in paths},
    }
    if len(roots(build)) == 1:
        manifest["deployment"] = roots(build)[0]
    files["baseline.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    files[".gitignore"] = ("*.plan\n*.plan.json\n*.facts.json\nstate*.json\n*.tfstate*\n.terraform/\n"
                           "inputs*.tfvars\nterraform.tfvars\n")
    return files


def generate(catalog: dict, baseline_id: str, out_dir: str, answers: dict | None = None,
             repo_root: Path = REPO_ROOT, build_id: str | None = None) -> list[Path]:
    """Write the run book and the Terraform it uses into a new directory."""
    out = Path(out_dir)
    files = render(catalog, baseline_id, answers, repo_root, build_id=build_id)
    if out.exists():
        raise ValueError(f"{out_dir} already exists; the agent never overwrites, choose a new directory")
    out.mkdir(parents=True)
    written = []
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")
        written.append(out / name)
    for rel in json.loads(files["baseline.json"])["files"]:
        target = out / "terraform" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((repo_root / rel).read_bytes())
        written.append(target)
    return written
