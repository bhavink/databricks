"""Drive the MCP server over stdio, the way Claude Code / Codex / Cursor do."""

import json
import sys

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from conftest import full_private_plan, non_pl_plan
from test_azure import state_from_plan

SERVER = StdioServerParameters(command=sys.executable, args=["-m", "wa_agent.mcp_server"])


def _payload(result):
    if result.structured_content is not None:
        content = result.structured_content
        return content.get("result", content) if isinstance(content, dict) else content
    return json.loads(result.content[0].text)


async def _session_run(fn):
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await fn(session)


def test_every_tool_is_declared_read_only():
    async def go(session):
        return (await session.list_tools()).tools

    tools = anyio.run(_session_run, go)
    assert {t.name for t in tools} == {"list_baselines", "list_patterns", "collect_tfplan",
                                      "collect_live", "assess", "verify", "new_workspace", "preflight"}
    for t in tools:
        assert t.annotations.read_only_hint is True and t.annotations.destructive_hint is False, t.name


def test_assess_and_verify_over_mcp(tmp_path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(non_pl_plan()), encoding="utf-8")
    state = tmp_path / "state.json"
    state.write_text(json.dumps(state_from_plan(full_private_plan())), encoding="utf-8")

    async def go(session):
        baselines = _payload(await session.call_tool("list_baselines", {}))
        facts = _payload(await session.call_tool("collect_tfplan", {"tf_json_path": str(plan)}))
        md = _payload(await session.call_tool("assess", {"facts": [facts], "baseline": "classic-standard"}))
        verdict = _payload(await session.call_tool("verify", {"tf_json_path": str(state),
                                                              "baseline": "classic-full-private"}))
        book = _payload(await session.call_tool("new_workspace", {"baseline": "classic-full-private"}))
        return baselines, md, verdict, book

    baselines, md, verdict, book = anyio.run(_session_run, go)
    assert set(book["files"]) == {"stage-1-deploy.tfvars", "stage-2-lockdown.tfvars", "README.md",
                                  "baseline.json", ".gitignore"}
    assert "classic-high-security" in {b["id"] for b in baselines}
    assert "## Prescription" in md and "AZ-OPS-001" in md
    assert verdict["verdict"] == "PASS" and verdict["input"] == "terraform-state"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["plan.json", "state.json"]  # nothing written
