# AGENTS.md — instructions for AI assistants

Applies to any assistant using or changing this tool: Claude Code, Codex,
Cursor, Gemini CLI, GitHub Copilot, and others.

## What this is

A deterministic, read-only Well-Architected assessor for Databricks. The
findings come from rules in `catalog/`, never from a model. Your job is to
run it and relay its output, not to reinterpret it.

## Hard rules (no exceptions)

1. **Never change anything.** Do not create, update, delete or apply anything
   in the user's workspace, cloud tenant, Terraform, state, or files, whether
   on the basis of a finding or otherwise. Do not run `terraform apply`,
   `az ... update/create/delete`, `databricks ... create/update/set`, or any
   other write. Use only the agent's tools or CLI.
2. **Stay grounded.** Present findings exactly as the report gives them, with
   evidence (value and source), official docs and ground-truth repo links. Do
   not add, drop, soften or re-rank findings. If a check is `UNKNOWN`, say so
   and pass on the report's instructions for collecting the missing fact. Do
   not guess.
3. **The user decides.** Offer the prescription and the Terraform; let the user
   choose what to apply and run it themselves.

## How to run it

Use the MCP server (`wa-agent-mcp`) if it is configured; otherwise use the CLI:

```bash
wa-agent baselines
wa-agent collect live --cloud azure --workspace <arm-id> --profile <ws> --account-profile <acct> -o out/ws.facts.json
wa-agent collect live --cloud gcp --workspace <name-or-url> --account-profile <gcp-acct> -o out/gcp.facts.json
wa-agent assess --facts out/ws.facts.json --baseline <baseline-id> [--option <id>] -o out/ws.report.md
wa-agent verify --tf-json state.json --baseline <baseline-id> [--option <id>]
wa-agent new --baseline <baseline-id> --out <new-dir> --set allowed_ip_ranges='["<cidr>"]' --set name=value
wa-agent new --cloud gcp --baseline <id> --build <lpw|new-vpc|existing-vpc> [--option <id>] --out <new-dir> ...
```

Relay fix caveats (**Before you apply**) and maturity labels verbatim.

Run `preflight` (MCP) or `wa-agent doctor --workspace <name>` before a live scan and relay its fixes.
Ask the user which baseline applies if they haven't said. Never invent a
baseline id; list them first. Pass `--cloud gcp` (or `cloud: "gcp"` in MCP) for Google Cloud.
When a baseline offers several builds, show each one's `for` text and let the user
choose; never pick one for them. On GCP, ask first whether Databricks may create
IAM roles and firewall rules in their project: standard builds (`new-vpc`,
`existing-vpc`) are the common case; `lpw` (least-privilege) is the special case
for teams that must create those themselves.
Baselines have the same ids on every cloud: `classic-no-pl`, `classic-backend-pl`,
`classic-full-pl`, `classic-dep`, `serverless`. Options (`cmk`, `public-access`,
`data-leak`, `context-ingress`, ...) are the user's choice too: show them
(`describe_baseline`) and pass only those the user picks.
IP access lists are part of the bare minimum and need the user's own known IP
ranges (corporate egress, VPN, automation, and the IP they run Terraform from).
Always ask for them and pass them as `allowed_ip_ranges`; never invent, guess or
widen them (0.0.0.0/0 is refused).

## Changing this codebase

- A new check needs an official doc in `sources` (the loader enforces this) and
  a collector that emits its facts, with provenance in `_evidence`.
- `new` only uses tested Terraform from this repo; it is the definitive source.
  Other repositories (e.g. the Databricks SRA) may be cited as references, never
  built from. Never generate Terraform, and never write account or subscription
  IDs to files.
- A new live command must be a read and must be added to `READ_ONLY_COMMANDS`.
  Never add a write verb.
- Keep output deterministic: no timestamps, no randomness, sorted output.
- Fixtures under `tests/fixtures/` must be sanitized: no subscription, tenant
  or account IDs, names or emails.
- Run `pytest` before proposing changes.
