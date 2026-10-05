# The Well-Architected Agent — the simple guide

> **Disclaimer.** This is a community project, provided **"as is", without
> warranty of any kind**. It is **not** an official Databricks or Microsoft
> product, and it is not supported by either. Findings and Terraform
> suggestions are informational. You are responsible for reviewing, testing
> and approving anything you apply to your environment. The authors and
> contributors accept **no liability** for any damage, outage, data loss,
> security incident or cost arising from using it or acting on its output.
> Always check against the official documentation and your own security and
> compliance requirements.

---

## Start here (3 steps, any OS)

**1. Install `uv`** (it brings everything else the agent needs), then get the agent:

| OS | Install uv |
|---|---|
| macOS / Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (or `brew install uv`) |
| Windows (PowerShell) | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` (or `winget install --id=astral-sh.uv -e`) |

```bash
git clone https://github.com/bhavink/databricks.git
cd databricks/well-architected-agent
```

**2. See it work, no setup or cloud access needed:** a full report from a real, sanitized workspace.

```bash
uv run wa-agent demo
```

**3. Point it at your workspace:** check what it can see, then assess.

```bash
uv run wa-agent doctor                              # tools and logins (output is redacted, safe to share)
uv run wa-agent doctor --workspace <name-or-url>    # preflight: what is reachable, how to fix the rest
uv run wa-agent collect live --cloud azure --workspace <name-or-url> -o ws.facts.json
uv run wa-agent assess --facts ws.facts.json --baseline classic-standard -o report.md
```

**What you need**

| For | You need | Check / fix |
|---|---|---|
| Everything | `uv` | `uv --version` |
| Live Azure scan | Azure CLI, logged in, with the `databricks` extension; Reader on the workspace resource group (and the VNet / DNS zones if they live elsewhere) | `az login` · `az extension add --name databricks` |
| Workspace checks (IP access lists, Unity Catalog, workspace settings) | Databricks CLI profile for the workspace (workspace admin), from a network the workspace allows | `databricks auth login --host https://<workspace-url>` |
| Serverless checks (NCC, network policy) | Databricks account admin profile | `databricks auth login --host https://accounts.azuredatabricks.net --account-id <id>` |
| Plan / state review, new workspaces | Terraform 1.5+ | `terraform version` |

The workspace can be given as a name, URL, numeric id or Azure resource id;
matching Databricks CLI profiles are picked automatically. Anything the agent
can't see is reported as *not evaluable* with the exact fix.

## Self-contained · runs locally · secure

- **Runs on your machine.** No hosted service, no server to deploy, no account to create. Works the same on macOS, Windows and Linux.
- **No telemetry.** The only network calls are read-only API calls to *your* tenant, made through *your* `az` and `databricks` CLIs (plus a one-time dependency download by `uv`).
- **No credentials handled.** It never asks for, stores or prints keys or tokens; it reuses your existing CLI logins.
- **Read-only by construction.** Only allow-listed read commands can run, it never runs Terraform, and it never overwrites a file. Tests enforce all three.
- **Your data stays local.** Facts and reports are written only where you choose; generated files are git-ignored by default. Through an AI assistant (MCP), tool results go to that assistant's model provider under its terms, so choose your assistant accordingly.
- **Safe to share.** `doctor` output is redacted (IDs, names, emails, tokens) so you can paste it into an issue.
- **Auditable.** Open source; the complete list of commands it may run is one table: `READ_ONLY_COMMANDS` in `wa_agent/clouds/azure/live.py`.

**Problem or question?** [Open an issue](https://github.com/bhavink/databricks/issues/new?template=wa-agent-problem.yml) and paste the output of `wa-agent doctor`.

## What is it?

A tool that looks at a Databricks workspace and tells you:

1. **what it is** — which proven architecture it matches,
2. **what's missing** — compared to the baseline you choose,
3. **how to fix it** — with evidence, official docs and tested Terraform.

```mermaid
flowchart LR
  WS["Your workspace<br/>(or Terraform plan/state)"] -->|"read-only scan"| AGENT["Well-Architected Agent"]
  BASE["Baseline you pick<br/>e.g. classic-high-security"] -->|"what good looks like"| AGENT
  AGENT -->|"report"| YOU["You decide<br/>what to apply"]
```

## Why use it?

- **Same answer every time.** Rules, not guesses. Run it twice, get the same report.
- **Every finding has proof.** It shows the value it saw, the exact command or
  Terraform resource it came from, the official doc, and the tested
  implementation in [bhavink/databricks](https://github.com/bhavink/databricks).
- **It tells you what to do, in order.** A ranked prescription, not a wall of warnings.
- **It never changes anything.** Read-only, enforced in code.

## The three rules it always follows

| # | Rule | How it's enforced |
|---|---|---|
| 1 | **Never changes anything** — no edits to the workspace, cloud tenant, Terraform or any file you have | Only allow-listed read commands can run; it never runs Terraform; it refuses to overwrite files |
| 2 | **Grounded in truth, backed by evidence** | Every check must cite an official doc; every fact records where it came from |
| 3 | **You decide** | It only prescribes. Applying anything is up to you |

## When to use it

```mermaid
flowchart TD
  START["Where are you?"] -->|"workspace already running"| ASSESS["Assess<br/>scan the live workspace"]
  START -->|"have Terraform, not applied"| PLAN["Assess the plan<br/>catch gaps before deploying"]
  START -->|"brand-new workspace"| PICK["Pick a baseline"]
  PICK -->|"use the matching tested deployment"| DEPLOY["You run terraform apply"]
  DEPLOY -->|"terraform show -json"| VERIFY["Verify the state<br/>did it build what it should?"]
  ASSESS -->|"report"| DECIDE["You decide what to fix"]
  PLAN -->|"report"| DECIDE
  VERIFY -->|"PASS / FAIL + report"| DECIDE
```

| Situation | Command |
|---|---|
| Health check of a running workspace | `collect live --cloud azure` then `assess` |
| Review Terraform before deploying | `collect tfplan --cloud azure` then `assess` |
| Check a fresh deployment did what it should | `verify --tf-json state.json --baseline ...` |
| Gate a CI pipeline | `assess ... --fail-on-gaps` |

## Pick a baseline

A baseline is **what the workspace is supposed to be**. Pick the one that
matches your use case, just like picking a deployment folder in the repo.

```mermaid
flowchart TD
  Q1["Do you need classic compute<br/>in your own network?"] -->|"no"| SL["serverless"]
  SL -->|"regulated data?"| SLH["serverless-high-security"]
  Q1 -->|"yes"| Q2["Must users reach the<br/>workspace only privately?"]
  Q2 -->|"no, internet + IP lists is fine"| Q3["Private path from<br/>compute to control plane?"]
  Q3 -->|"no"| STD["classic-standard"]
  Q3 -->|"yes"| PL["classic-private-link"]
  Q2 -->|"yes"| Q4["Must all egress be<br/>inspected by a firewall?"]
  Q4 -->|"no"| FP["classic-full-private"]
  FP -->|"regulated data?"| HS["classic-high-security"]
  Q4 -->|"yes"| DEP["classic-exfiltration-protection"]
```

| Baseline | In one line |
|---|---|
| `serverless` | No network to manage. Serverless only. |
| `serverless-high-security` | Serverless + private storage access + customer-managed keys. |
| `classic-standard` | Your VNet, no public IPs, NAT egress, IP-restricted front-end. |
| `classic-private-link` | Compute talks to Databricks privately; users come over the internet. |
| `classic-full-private` | Nothing public. Private Link for users and compute. |
| `classic-high-security` | Full private + keys everywhere + locked-down storage and serverless egress. |
| `classic-exfiltration-protection` | Hub-spoke; every byte of egress goes through a firewall. |

List them any time: `uv run wa-agent baselines`.

## How to run it (5 minutes)

**1. Install**

```bash
cd well-architected-agent
```

**2. Log in (read access is enough)**

```bash
az login
databricks auth login --profile my-workspace     # workspace admin, for IP lists / Unity Catalog
databricks auth login --profile my-account \
  --host https://accounts.azuredatabricks.net --account-id <id>   # optional, for serverless checks
```

**3. Scan and assess**

```bash
uv run wa-agent collect live --cloud azure --workspace <name-or-url> -o out/ws.facts.json
# profiles are matched automatically; pass --profile / --account-profile to override

uv run wa-agent assess --facts out/ws.facts.json --baseline classic-full-private -o out/ws.report.md
```

What happens under the hood:

```mermaid
sequenceDiagram
  actor You
  participant Agent as Well-Architected Agent
  participant ARM as Azure Resource Manager
  participant DBX as Databricks APIs
  You->>Agent: collect live --cloud azure (read-only)
  Agent->>ARM: show workspace, subnets, storage, DNS (GET only)
  ARM-->>Agent: configuration JSON
  Agent->>DBX: get IP lists, metastore, NCC, network policy (GET only)
  DBX-->>Agent: configuration JSON
  Agent-->>You: facts.json (values + where each came from)
  You->>Agent: assess --baseline ...
  Agent-->>You: report.md (prescription, evidence, docs, Terraform)
```

## Use it from any AI assistant

The agent has no LLM inside, so it works the same under any provider. Your
assistant calls its tools over MCP (or runs the CLI) and relays the
deterministic report. Every MCP tool is marked `readOnlyHint: true`,
`destructiveHint: false`, and none of them write files.

```bash
uv run wa-agent doctor    # prints the exact registration command for each assistant
```

| Assistant | Register the MCP server |
|---|---|
| Claude Code | `claude mcp add databricks-wa -- uv run --quiet --frozen --project /abs/path/well-architected-agent wa-agent-mcp` (or open the repo: `.mcp.json` is included) |
| Codex CLI | `codex mcp add databricks-wa -- uv run --quiet --frozen --project /abs/path/well-architected-agent wa-agent-mcp` |
| Cursor | Open the repo (`.cursor/mcp.json` is included), or in `~/.cursor/mcp.json`: `{"mcpServers": {"databricks-wa": {"command": "uv", "args": ["run", "--quiet", "--frozen", "--project", "/abs/path/well-architected-agent", "wa-agent-mcp"]}}}` |
| Gemini CLI | `~/.gemini/settings.json`: the same `mcpServers` block as Cursor |
| VS Code (Copilot) | `.vscode/mcp.json`: `{"servers": {"databricks-wa": {"type": "stdio", "command": "uv", "args": ["run", "--quiet", "--frozen", "--project", "/abs/path/well-architected-agent", "wa-agent-mcp"]}}}` |

`/abs/path/well-architected-agent` is the full path to this folder in your clone
(on Windows, e.g. `C:/Users/you/databricks/well-architected-agent`).

Tools: `list_baselines`, `describe_baseline`, `list_patterns`, `preflight`,
`collect_tfplan`, `collect_live`, `assess`, `verify`, `diagram`, `new_workspace`.

`--frozen` makes the server use the committed lockfile as-is. Keep it: without it,
a machine configured for a private package mirror rewrites `uv.lock` at every launch. Assistants that read
[`AGENTS.md`](AGENTS.md) (Codex, Cursor, and others; `CLAUDE.md` points
there) also get the three rules as instructions.

Then just ask: *"Assess workspace `<arm-id>` against `classic-high-security`."*

```mermaid
flowchart LR
  USER["You"] -->|"ask in plain English"| AI["Any AI assistant<br/>Claude, Codex, Cursor, Gemini"]
  AI -->|"MCP tool calls (read-only)"| MCP["wa-agent-mcp"]
  MCP -->|"same deterministic core as the CLI"| CORE["Rules engine + catalog"]
  CORE -->|"report: prescription, evidence, docs"| AI
  AI -->|"relays the report unchanged"| USER
```

## How to read the report

| Section | What it tells you |
|---|---|
| **Header** | Detected pattern, your baseline, score, conformant yes/no |
| **Prescription** | The fix list, in the order you should do it |
| **Gaps** | Per gap: why it matters, evidence (value + source), official docs, repo implementation, Terraform |
| **Not evaluable** | What it couldn't see and exactly how to let it see it — never guessed |
| **Passed / Not applicable** | What's already fine, and what doesn't apply to this design |
| **Upgrade path** | What stands between you and the next, more secure pattern |

Statuses, simply:

| Status | Meaning |
|---|---|
| `PASS` | Control in place, with evidence |
| `FAIL` | Control missing, with evidence |
| `UNKNOWN` | Couldn't read it (permissions, network, IP lists) — tells you how to fix the access |
| `NOT_APPLICABLE` | Doesn't apply to this design (e.g. VNet checks on serverless) |

## Brand-new workspace

```mermaid
flowchart LR
  B["1. Pick a baseline"] -->|"maps to"| T["2. Tested Terraform<br/>in this repo"]
  T -->|"you answer inputs,<br/>you run plan"| P["3. assess the plan"]
  P -->|"you run apply"| S["4. terraform show -json"]
  S -->|"verify --baseline"| V["5. PASS / FAIL<br/>with evidence"]
```

```bash
wa-agent new --baseline classic-full-private --out ./my-ws --set location=eastus2
```

That creates `./my-ws/` with everything needed:

| File | What it is |
|---|---|
| `terraform/` | The tested Terraform, copied from this repo |
| `inputs.tfvars` | The required settings. Your `--set` answers; anything unanswered is a `REPLACE_ME_*` |
| `stage-N-*.tfvars` | What the baseline turns on, one file per stage (for full private: *deploy*, then *lockdown* from inside your network) |
| `README.md` | Every command, in order |
| `baseline.json` | What was used: baseline, commit, and a checksum of every copied file |

After each `terraform plan`, the README also runs `wa-agent diagram` to draw what
that stage deploys (`stageN.architecture.md`), and once more on the final state
(`architecture.md`).

Each stage is: `terraform plan` → `wa-agent assess` on the plan →
`terraform apply` (you run it) → after the last stage, `wa-agent verify` on
the state. The final stage must verify as **PASS**; if the Terraform used
can't cover a check, the README names it up front.

Account and subscription IDs are set as `TF_VAR_*` environment variables and
are never written to the folder.

## FAQ

**Will it change my workspace?** No. It can only run allow-listed read
commands, never runs Terraform, and won't overwrite files. A test suite checks
that write commands are refused.

**Why "UNKNOWN" instead of a result?** Because guessing is worse than saying
"I couldn't see it". The report tells you what access is missing.

**I was blocked by an IP access list.** That's good news: it proves the lists are
enforced. Run from an allowed network to see their contents.

**Does an LLM decide the findings?** No. Findings come from rules in
`catalog/`. Same input, same output.

**Which clouds?** Azure today. GCP, then AWS, are next.

---

> **Disclaimer (again, because it matters).** Provided "as is", without
> warranty. Not an official Databricks or Microsoft product. You are
> responsible for anything you apply. The authors and contributors are not
> liable for any outcome of using this tool or its output.
