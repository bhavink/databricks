import copy
import json
import random

import pytest
from pathlib import Path

from conftest import serverless_plan, full_private_plan, non_pl_plan, rc
from wa_agent import report
from wa_agent.cli import main
from wa_agent.clouds.azure import live as azure_live, tfplan as azure_tfplan
from wa_agent.engine import FAIL, NOT_APPLICABLE, PASS, UNKNOWN, assess, evaluate
from wa_agent.facts import merge


IPS = {"allowed_ip_ranges": ["203.0.113.0/24"]}


def statuses(result):
    return {f.check["id"]: f.status for f in result.findings}


def test_catalog_loads_and_is_consistent(azure_catalog):
    assert len(azure_catalog["checks"]) >= 20
    assert {p["id"] for p in azure_catalog["patterns"]["patterns"]} == set(azure_catalog["patterns"]["detection_order"])


def test_three_valued_logic():
    missing = set()
    assert evaluate({"all_of": [{"fact": "a", "op": "equals", "value": 1},
                                {"fact": "b", "op": "equals", "value": 1}]}, {"a": 2}, missing) is False
    assert evaluate({"any_of": [{"fact": "a", "op": "equals", "value": 1},
                                {"fact": "b", "op": "equals", "value": 1}]}, {"a": 2}, missing) is None
    assert missing == {"b"}


def test_non_pl_plan_detects_pattern_and_surfaces_known_gaps(azure_catalog):
    facts = azure_tfplan.collect(non_pl_plan())
    result = assess(azure_catalog, facts)
    s = statuses(result)

    assert result.detected["id"] == "classic-no-pl"
    for passing in ("AZ-NET-001", "AZ-NET-002", "AZ-NET-003", "AZ-NET-004", "AZ-NET-005",
                    "AZ-NET-007", "AZ-NET-008", "AZ-SRV-001", "AZ-ING-001", "AZ-UC-001", "AZ-UC-002"):
        assert s[passing] == PASS, passing
    # The non-pl reference deployment has no diagnostic settings or serverless egress policy.
    assert s["AZ-OPS-001"] == FAIL
    assert s["AZ-SRV-002"] == FAIL
    assert s["AZ-PL-003"] == NOT_APPLICABLE
    assert s["AZ-STO-002"] == FAIL  # storage firewall not set in config
    # Serverless egress is part of the bare minimum, so it now counts as required.
    assert result.score == {"required_passed": 10, "required_evaluated": 12,
                            "required_unknown": 0, "conformant": False}


def test_full_private_plan(azure_catalog):
    facts = azure_tfplan.collect(full_private_plan())
    result = assess(azure_catalog, facts)
    s = statuses(result)

    assert result.detected["id"] == "classic-full-pl"
    for check in result.target["required"]:
        assert s[check] in (PASS, NOT_APPLICABLE), check
    assert result.score["conformant"] is True
    assert s["AZ-ING-001"] == NOT_APPLICABLE  # public access disabled: nothing public to restrict
    assert s["AZ-SRV-002"] == PASS


def test_declared_target_reports_upgrade_gaps(azure_catalog):
    facts = azure_tfplan.collect(non_pl_plan())
    result = assess(azure_catalog, facts, "classic-dep")
    s = statuses(result)
    assert result.tier_of("AZ-NET-006") == "required"
    assert s["AZ-NET-006"] == FAIL
    assert s["AZ-PL-001"] == FAIL


def test_classic_without_own_vnet_fails_net_001(azure_catalog):
    plan = {"resource_changes": [rc("azurerm_databricks_workspace.this", "azurerm_databricks_workspace",
                                    {"name": "legacy", "custom_parameters": [{"no_public_ip": False}]})]}
    result = assess(azure_catalog, azure_tfplan.collect(plan))
    assert result.detected["id"] == "classic-no-pl"
    assert statuses(result)["AZ-NET-001"] == FAIL


def test_network_outside_plan_is_unknown_not_fail(azure_catalog):
    plan = non_pl_plan()
    plan["resource_changes"] = [r for r in plan["resource_changes"] if "networking" not in r["address"]]
    result = assess(azure_catalog, azure_tfplan.collect(plan))
    finding = next(f for f in result.findings if f.check["id"] == "AZ-NET-003")
    assert finding.status == UNKNOWN
    assert finding.missing_facts == ["network.all_subnets_have_nsg"]


def test_serverless_override(azure_catalog):
    facts = azure_tfplan.collect(non_pl_plan())
    facts["workspace"]["compute_mode"] = "serverless"
    result = assess(azure_catalog, facts)
    assert result.detected["id"] == "serverless"
    assert statuses(result)["AZ-NET-002"] == NOT_APPLICABLE


def test_merge_is_order_independent():
    a = {"governance": {"metastore_assigned": False}, "serverless": {"ncc_private_endpoint_rules": 0}}
    b = {"governance": {"metastore_assigned": True}, "serverless": {"ncc_private_endpoint_rules": 2}}
    assert merge(a, b) == merge(b, a) == {"governance": {"metastore_assigned": True},
                                          "serverless": {"ncc_private_endpoint_rules": 2}}


@pytest.mark.parametrize("fmt", [report.to_markdown, report.to_json])
def test_output_is_deterministic_under_resource_reordering(azure_catalog, fmt):
    plan = non_pl_plan()
    shuffled = copy.deepcopy(plan)
    random.Random(7).shuffle(shuffled["resource_changes"])
    outputs = set()
    for doc in (plan, shuffled, plan):
        facts = azure_tfplan.collect(doc)
        outputs.add(fmt(assess(azure_catalog, facts), azure_catalog, facts))
    assert len(outputs) == 1


def test_plan_evidence_names_terraform_resources():
    facts = azure_tfplan.collect(non_pl_plan())
    ev = facts["_evidence"]
    assert ev["workspace.no_public_ip"] == ["terraform:module.workspace.azurerm_databricks_workspace.this"]
    assert ev["operations.diagnostic_settings"] == ["terraform: no azurerm_monitor_diagnostic_setting in plan"]


def test_markdown_contains_fix_and_sources(azure_catalog):
    facts = azure_tfplan.collect(non_pl_plan())
    md = report.to_markdown(assess(azure_catalog, facts), azure_catalog, facts)
    assert "### AZ-OPS-001" in md
    assert "azurerm_monitor_diagnostic_setting" in md
    assert "https://github.com/bhavink/databricks/blob/master/adb4u/deployments/non-pl" in md
    assert "## Upgrade path" in md
    assert "## Prescription" in md and report.READ_ONLY_NOTICE in md
    assert "from `terraform: no azurerm_monitor_diagnostic_setting in plan`" in md
    assert "**Ground-truth repo (tested):**" in md
    assert "validated" not in md  # everything in the repo is battle-tested
    beyond = md.split("## Beyond target")[1].split("## Not evaluable")[0]
    assert "AZ-NET-006" in beyond and "```hcl" not in beyond


def test_cli_end_to_end(tmp_path, capsys):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(full_private_plan()), encoding="utf-8")
    facts = tmp_path / "facts.json"
    assert main(["collect", "tfplan", "--plan", str(plan), "-o", str(facts)]) == 0
    assert main(["assess", "--facts", str(facts), "--format", "json", "--fail-on-gaps"]) == 0
    assert json.loads(capsys.readouterr().out)["score"]["conformant"] is True
    assert main(["assess", "--facts", str(facts), "--target", "classic-dep", "--fail-on-gaps",
                 "-o", str(tmp_path / "r.md")]) == 1


def test_live_collector_with_fake_cli(azure_catalog):
    vnet = "/subscriptions/s/resourceGroups/rg/providers/Microsoft.Network/virtualNetworks/v"
    ws_id = "/subscriptions/s/resourceGroups/rg/providers/Microsoft.Databricks/workspaces/ws"
    subnet = {"delegations": [{"serviceName": "Microsoft.Databricks/workspaces"}],
              "networkSecurityGroup": {"id": "nsg"}, "natGateway": {"id": "nat"},
              "serviceEndpoints": [{"service": "Microsoft.Storage"}], "serviceEndpointPolicies": [{"id": "sep"}]}
    responses = {
        ("az", "databricks", "workspace", "show"): {
            "id": ws_id, "name": "ws", "sku": {"name": "premium"}, "publicNetworkAccess": "Enabled",
            "requiredNsgRules": "AllRules", "workspaceUrl": "adb-1.azuredatabricks.net",
            "parameters": {"customVirtualNetworkId": {"value": vnet}, "enableNoPublicIp": {"value": True},
                           "customPublicSubnetName": {"value": "pub"}, "customPrivateSubnetName": {"value": "priv"}},
        },
        ("az", "network", "vnet", "subnet"): subnet,
        ("az", "network", "private-dns", "zone"): [],
        ("az", "monitor", "diagnostic-settings", "list"): [],
        ("az", "resource", "list"): [{"id": "ac"}],
        ("databricks", "-o", "json", "--host"): None,
    }

    def fake(args):
        for prefix, value in responses.items():
            if tuple(args[: len(prefix)]) == prefix:
                return value
        return None

    facts = azure_live.collect(ws_id, run=fake, databricks_profile="ws")
    result = assess(azure_catalog, facts)
    s = statuses(result)
    assert result.detected["id"] == "classic-no-pl"
    assert s["AZ-NET-005"] == PASS
    assert s["AZ-OPS-001"] == FAIL
    assert s["AZ-UC-002"] == PASS
    assert s["AZ-ING-001"] == UNKNOWN  # no Databricks CLI access in this fake


FIXTURES = __import__("pathlib").Path(__file__).parent / "fixtures" / "azure"


def replay(name):
    """Replay sanitized CLI responses recorded from a real workspace."""
    return azure_live.replay(json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def test_live_replay_backend_pl_without_ip_access_lists(azure_catalog):
    # Recorded: back-end + browser-auth private endpoints, public front-end,
    # no IP access lists, default outbound access, Microsoft.Storage.Global SE.
    # Front-end and back-end Private Link with public access on: full Private
    # Link with the public-access option.
    result = assess(azure_catalog, replay("live-backend-pl-ws1.calls.json"))
    s = statuses(result)
    assert result.detected["id"] == "classic-full-pl"
    assert s["AZ-ING-001"] == FAIL
    assert s["AZ-NET-005"] == FAIL
    assert s["AZ-PL-003"] == FAIL  # AllRules with back-end Private Link
    assert s["AZ-NET-007"] == PASS  # Microsoft.Storage.Global counts
    assert s["AZ-DNS-001"] == PASS
    assert s["AZ-UC-001"] == PASS
    assert s["AZ-STO-002"] == FAIL  # DBFS account defaultAction Allow
    assert s["AZ-SRV-001"] == PASS
    assert s["AZ-SRV-002"] == FAIL  # RESTRICTED_ACCESS policy, but DRY_RUN


def test_live_replay_ip_acl_blocked_scanner(azure_catalog):
    # Recorded from an IP the workspace's access list rejects: enforcement is
    # proven, but the allow-list count and metastore stay unknown, not failed.
    facts = replay("live-backend-pl-ws2.calls.json")
    assert facts["access"] == {"ip_access_lists_enabled": True, "context_ingress_enforced": False}
    result = assess(azure_catalog, facts)
    s = statuses(result)
    assert result.detected["id"] == "classic-full-pl"
    assert s["AZ-PL-003"] == PASS  # NoAzureDatabricksRules
    assert s["AZ-NET-007"] == FAIL
    assert s["AZ-UC-001"] == UNKNOWN
    assert s["AZ-UC-002"] == PASS  # ARM lookup still runs
    assert facts["serverless"] == {"ncc_bound": True, "ncc_private_endpoint_rules": 2,  # EXPIRED rule excluded
                                   "network_policy_id": "default-policy",
                                   "egress_restricted": False}  # default-policy: FULL_ACCESS
    assert facts["_evidence"]["access.ip_access_lists_enabled"][0].endswith("'blocked by Databricks IP ACL'")
    assert "enforcement_mode" in facts["_evidence"]["serverless.egress_restricted"][0]
    finding = next(f for f in result.findings if f.check["id"] == "AZ-ING-001")
    assert finding.status == UNKNOWN and finding.missing_facts == ["access.ip_access_list_count"]


def test_baseline_promotes_extra_checks_to_required(azure_catalog):
    facts = azure_tfplan.collect(full_private_plan())
    plain = assess(azure_catalog, facts, baseline_id="classic-full-pl")
    strict = assess(azure_catalog, facts, baseline_id="classic-full-pl", options=["cmk"])
    assert plain.score["conformant"] is True
    assert plain.tier_of("AZ-ENC-001") == "recommended"
    assert strict.tier_of("AZ-ENC-001") == "required"
    assert strict.score["conformant"] is False  # fixture has no CMK
    assert strict.baseline["id"] == "classic-full-pl"
    assert [o["id"] for o in strict.options] == ["cmk"]
    public = assess(azure_catalog, facts, baseline_id="classic-full-pl", options=["public-access"])
    assert plain.tier_of("AZ-PL-004") == "required" and public.tier_of("AZ-PL-004") == "advisory"
    assert public.tier_of("AZ-ING-001") == "required"  # the bare minimum is never waived
    with pytest.raises(ValueError, match="no option"):
        assess(azure_catalog, facts, baseline_id="classic-full-pl", options=["nope"])


def test_baseline_errors(azure_catalog):
    facts = azure_tfplan.collect(non_pl_plan())
    with pytest.raises(ValueError, match="unknown baseline"):
        assess(azure_catalog, facts, baseline_id="nope")
    with pytest.raises(ValueError, match="not both"):
        assess(azure_catalog, facts, target_id="classic-no-pl", baseline_id="classic-no-pl")


def test_baseline_report_flags_compute_mode_mismatch(azure_catalog):
    facts = azure_tfplan.collect(non_pl_plan())
    result = assess(azure_catalog, facts, baseline_id="serverless")
    md = report.to_markdown(result, azure_catalog, facts)
    assert "| Baseline | **Serverless workspace** (`serverless`) |" in md
    assert "Compute mode mismatch" in md
    assert json.loads(report.to_json(result, azure_catalog, facts))["baseline"] == "serverless"


def test_every_baseline_maps_to_existing_repo_path(azure_catalog):
    repo = __import__("pathlib").Path(__file__).resolve().parents[2]
    for b in azure_catalog["baselines"]:
        assert b["deployment"].startswith(("https://www.databricks.com/blog/", "https://learn.microsoft.com/")) or (
            repo / b["deployment"]).exists(), b["deployment"]


@pytest.mark.parametrize("args", [
    ["az", "databricks", "workspace", "update", "--ids", "x"],
    ["az", "network", "vnet", "subnet", "update", "--ids", "x"],
    ["az", "storage", "account", "update", "-n", "x"],
    ["az", "rest", "--method", "put", "--url", "x"],
    ["databricks", "-o", "json", "--profile", "p", "ip-access-lists", "create"],
    ["databricks", "-o", "json", "--profile", "p", "workspace-conf", "set-status"],
    ["databricks", "--profile", "p", "account", "workspace-network-configuration", "update-workspace-network-option-rpc", "1"],
    ["terraform", "apply"],
])
def test_rule1_write_commands_are_refused(args):
    with pytest.raises(azure_live.ReadOnlyViolation):
        azure_live.assert_read_only(args)


def test_rule1_every_command_the_collector_issues_is_allowlisted():
    issued = []
    for name in ("live-backend-pl-ws1.calls.json", "live-backend-pl-ws2.calls.json"):
        for call in json.loads((FIXTURES / name).read_text(encoding="utf-8")):
            azure_live.assert_read_only(call["args"])
            issued.append(azure_live.command_verb(call["args"]))
    assert set(issued) <= azure_live.READ_ONLY_COMMANDS


def state_from_plan(plan):
    """A `terraform show -json` state document with the plan's resources applied."""
    resources = [{"address": r["address"], "mode": "managed", "type": r["type"], "name": r["name"],
                  "values": {k: (v if v is not None else "applied") for k, v in r["change"]["after"].items()}}
                 for r in plan["resource_changes"]]
    for r in resources:
        if r["type"] == "azurerm_private_dns_zone_virtual_network_link":
            r["values"]["private_dns_zone_name"] = "privatelink.azuredatabricks.net"
        if r["type"] == "azurerm_databricks_workspace":
            r["values"]["custom_parameters"] = [{"no_public_ip": True, "virtual_network_id": "/subscriptions/x/vnet"}]
            for key in ("managed_services_cmk_key_vault_key_id", "managed_disk_cmk_key_vault_key_id",
                        "default_storage_firewall_enabled"):
                r["values"][key] = None
    return {"format_version": "1.0", "values": {"root_module": {"resources": resources}}}


def test_verify_state_against_baseline(tmp_path, capsys):
    state = tmp_path / "state.json"
    state.write_text(json.dumps(state_from_plan(full_private_plan())), encoding="utf-8")
    assert main(["verify", "--tf-json", str(state), "--baseline", "classic-full-pl", "-o", str(tmp_path / "a.md")]) == 0
    assert "verify PASS: Terraform state" in capsys.readouterr().err
    assert main(["verify", "--tf-json", str(state), "--baseline", "classic-full-pl", "--option", "cmk",
                 "-o", str(tmp_path / "b.md")]) == 1
    assert "verify FAIL" in capsys.readouterr().err


def test_rule1_outputs_never_overwrite(tmp_path):
    existing = tmp_path / "report.md"
    existing.write_text("user content", encoding="utf-8")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(non_pl_plan()), encoding="utf-8")
    facts = tmp_path / "facts.json"
    assert main(["collect", "tfplan", "--plan", str(plan), "-o", str(facts)]) == 0
    assert main(["assess", "--facts", str(facts), "-o", str(existing)]) == 2
    assert existing.read_text(encoding="utf-8") == "user content"


def test_caveats_render_in_prescription_and_gap(azure_catalog):
    facts = replay("live-backend-pl-ws1.calls.json")
    result = assess(azure_catalog, facts, baseline_id="classic-full-pl")
    md = report.to_markdown(result, azure_catalog, facts)
    assert "**AZ-STO-002**" in md and "(has caveats)" in md
    assert "- Irreversible: enabling it deletes the access connector in the managed" in md


def test_storage_firewall_not_required_for_standard_baseline(azure_catalog):
    facts = azure_tfplan.collect(non_pl_plan())
    result = assess(azure_catalog, facts, baseline_id="classic-no-pl")
    assert result.tier_of("AZ-STO-002") == "advisory"  # non-pl has no private endpoint subnet


def test_every_build_tfvar_is_a_declared_deployment_variable(azure_catalog):
    from wa_agent.new import check_build

    built = [b for b in azure_catalog["baselines"] if b.get("build")]
    # back-end-only Private Link and hub-spoke are assess-only
    assert {b["id"] for b in built} == {b["id"] for b in azure_catalog["baselines"]} - {"classic-dep", "classic-backend-pl"}
    for b in built:
        check_build(b)


def test_new_bundles_tested_terraform_with_inputs_and_stages(azure_catalog, tmp_path):
    from wa_agent.new import generate

    out = tmp_path / "ws"
    generate(azure_catalog, "classic-full-pl", str(out), {"location": "eastus2", "tag_owner": "me@example.com", **IPS})
    assert sorted(p.name for p in out.iterdir()) == [".gitignore", "README.md", "baseline.json", "inputs.tfvars",
                                                    "stage-1-deploy.tfvars", "stage-2-lockdown.tfvars", "terraform"]
    lockdown = (out / "stage-2-lockdown.tfvars").read_text(encoding="utf-8")
    assert 'network_policy_enforcement_mode          = "ENFORCED"' in lockdown
    assert "enable_public_network_access             = false" in lockdown
    inputs = (out / "inputs.tfvars").read_text(encoding="utf-8")
    assert 'location            = "eastus2"' in inputs and '"REPLACE_ME_workspace_prefix"' in inputs
    assert "databricks_account_id =" not in inputs  # env only, never written
    dep = out / "terraform" / "adb4u" / "deployments" / "full-private"
    assert (dep / "main.tf").is_file() and (out / "terraform" / "adb4u" / "modules" / "ncc" / "main.tf").is_file()
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert 'export BOOK="$(pwd)"' in readme and 'cd "$BOOK/terraform/adb4u/deployments/full-private"' in readme
    assert ("-var-file=$BOOK/inputs.tfvars -var-file=$BOOK/stage-1-deploy.tfvars "
            "-var-file=$BOOK/stage-2-lockdown.tfvars") in readme
    assert readme.count("terraform init") == 1  # one root, initialized once
    assert "$env:BOOK" in readme and "$env:TF_VAR_<name>" in readme  # PowerShell equivalent
    assert "az login" in readme and "--cloud azure" in readme
    assert "wa-agent verify --cloud azure --tf-json state.json --baseline classic-full-pl" in readme
    meta = json.loads((out / "baseline.json").read_text(encoding="utf-8"))
    assert meta["placeholders"] == ["diagnostic_log_analytics_workspace_id",  # IP ranges are answered, not REPLACE_ME
                                    "resource_group_name", "tag_keepuntil", "workspace_prefix"]
    assert all(len(h) == 64 for h in meta["files"].values())
    assert not [p for p in out.rglob("*") if p.name.endswith((".tfstate", ".tfvars")) and "terraform" in p.parts]


def test_bundle_never_copies_state_tfvars_or_provider_cache(tmp_path):
    from wa_agent.new import bundle_files

    dep = tmp_path / "adb4u" / "deployments" / "x"
    mod = tmp_path / "adb4u" / "modules" / "m"
    for d in (dep / ".terraform" / "modules", mod / "tests"):
        d.mkdir(parents=True)
    (dep / "main.tf").write_text('module "m" {\n  source = "../../modules/m"\n}\n', encoding="utf-8")
    for name in ("terraform.tfvars", "terraform.tfstate", "terraform.tfstate.backup", ".terraform.lock.hcl",
                 "terraform.tfvars.example", "README.md"):
        (dep / name).write_text("x", encoding="utf-8")
    (dep / ".terraform" / "modules" / "leak.tf").write_text("x", encoding="utf-8")
    (mod / "main.tf").write_text("", encoding="utf-8")
    (mod / "tests" / "m.tftest.hcl").write_text("", encoding="utf-8")
    assert bundle_files("adb4u/deployments/x", tmp_path) == [
        "adb4u/deployments/x/README.md", "adb4u/deployments/x/main.tf", "adb4u/deployments/x/terraform.tfvars.example",
        "adb4u/modules/m/main.tf", "adb4u/modules/m/tests/m.tftest.hcl"]




def test_new_answers_are_validated(azure_catalog, tmp_path):
    from wa_agent.new import parse_answer, render

    assert parse_answer('["10.0.0.0/24"]') == ["10.0.0.0/24"] and parse_answer("true") is True
    assert parse_answer("eastus2") == "eastus2"
    with pytest.raises(ValueError, match="not a variable"):
        render(azure_catalog, "serverless", {"no_such_variable": 1, **IPS})
    with pytest.raises(ValueError, match="TF_VAR_databricks_account_id"):
        render(azure_catalog, "serverless", {"databricks_account_id": "x", **IPS})


def test_new_needs_the_users_known_ip_ranges(azure_catalog):
    from wa_agent.new import render

    with pytest.raises(ValueError, match="known IP ranges"):
        render(azure_catalog, "classic-no-pl")
    with pytest.raises(ValueError, match="whole internet"):
        render(azure_catalog, "classic-no-pl", {"allowed_ip_ranges": ["0.0.0.0/0"]})
    with pytest.raises(ValueError, match="not a CIDR"):
        render(azure_catalog, "classic-no-pl", {"allowed_ip_ranges": ["office"]})
    stage = render(azure_catalog, "classic-no-pl", IPS)["stage-1-deploy.tfvars"]
    assert 'allowed_ip_ranges' in stage and '"203.0.113.0/24"' in stage and "REPLACE_ME_corporate" not in stage


def test_options_switch_on_tested_settings_or_say_how(azure_catalog):
    from wa_agent.new import render

    files = render(azure_catalog, "classic-full-pl", IPS, options=["public-access", "cmk", "data-leak"])
    assert "enable_cmk_managed_services" in files["stage-1-deploy.tfvars"]
    lockdown = files["stage-2-lockdown.tfvars"]
    assert "enable_public_network_access             = true" in lockdown and "203.0.113.0/24" in lockdown
    readme = files["README.md"]
    assert "--option public-access --option cmk --option data-leak" in readme
    assert "do them yourself" in readme and "`data-leak`" in readme  # full-private has no setting for it
    assert json.loads(files["baseline.json"])["options"] == ["public-access", "cmk", "data-leak"]


def test_new_refuses_without_tested_deployment_and_never_overwrites(azure_catalog, tmp_path):
    from wa_agent.new import generate

    cat = copy.deepcopy(azure_catalog)
    cat["baselines"].append({"id": "untested", "name": "x", "use_case": "x", "pattern": "serverless",
                             "deployment": "adb4u/README.md"})
    with pytest.raises(ValueError, match="no tested deployment"):
        generate(cat, "untested", str(tmp_path / "a"))
    (tmp_path / "b").mkdir()
    with pytest.raises(ValueError, match="never overwrites"):
        generate(azure_catalog, "classic-no-pl", str(tmp_path / "b"), IPS)
    assert not (tmp_path / "a").exists()




def test_serverless_workspace_from_official_module_is_detected_and_verifies(azure_catalog):
    facts = azure_tfplan.collect(serverless_plan())
    assert facts["workspace"]["compute_mode"] == "serverless"
    assert facts["workspace"]["public_network_access_enabled"] is True
    assert facts["_evidence"]["workspace.compute_mode"] == ["terraform:azapi_resource.workspace"]
    result = assess(azure_catalog, facts, baseline_id="serverless")
    assert result.score["conformant"], statuses(result)
    high = statuses(assess(azure_catalog, facts, baseline_id="serverless"))
    assert high["AZ-ENC-001"] == FAIL and high["AZ-WS-001"] == FAIL and high["AZ-SRV-003"] == FAIL
    secured = azure_tfplan.collect(serverless_plan(cmk=True, leak_features_off=True, storage_pe=True))
    assert assess(azure_catalog, secured, baseline_id="serverless").score["conformant"]


def test_plan_with_several_workspaces_needs_a_selection(azure_catalog):
    plan = full_private_plan()
    plan["resource_changes"] += serverless_plan()["resource_changes"][:1]  # e.g. SRA hub + spoke
    with pytest.raises(ValueError, match="choose one with --workspace"):
        azure_tfplan.collect(plan)
    spoke = azure_tfplan.collect(plan, workspace="module.workspace.azurerm_databricks_workspace.this")
    assert spoke["workspace"]["compute_mode"] == "classic"
    hub = azure_tfplan.collect(plan, workspace="srvtest-workspace")  # by name
    assert hub["workspace"]["compute_mode"] == "serverless"
    with pytest.raises(ValueError, match="no single workspace"):
        azure_tfplan.collect(plan, workspace="nope")


def test_every_check_maps_to_a_phase_and_control(azure_catalog):
    controls = {c["id"]: c for c in azure_catalog["controls"]["controls"]}
    for check in azure_catalog["checks"]:
        control = controls[check["control"]]
        assert check["phase"] == control["phase"] and check["pillar"] == control["pillar"]
        assert check["guide_url"].startswith("https://learn.microsoft.com/en-us/azure/databricks/lakehouse-architecture/deployment-guide/")


def test_subnet_sizing_and_data_leak_checks_on_real_workspaces(azure_catalog):
    ws1 = statuses(assess(azure_catalog, replay("live-backend-pl-ws1.calls.json")))
    ws2 = statuses(assess(azure_catalog, replay("live-backend-pl-ws2.calls.json")))
    assert ws1["AZ-NET-009"] == PASS     # /23
    assert ws2["AZ-NET-009"] == FAIL     # /26: the guide's minimum, not its recommendation
    assert ws1["AZ-WS-001"] == FAIL      # export, download, clipboard at defaults (enabled)
    assert ws2["AZ-WS-001"] == UNKNOWN   # behind the workspace IP access list


def test_plan_subnet_sizing_and_unset_leak_settings(azure_catalog):
    facts = azure_tfplan.collect(non_pl_plan())
    assert facts["network"]["smallest_subnet_prefix_length"] == 26
    assert facts["access"]["notebook_export_enabled"] is True  # unset in config = Databricks default
    s = statuses(assess(azure_catalog, facts))
    assert s["AZ-NET-009"] == FAIL and s["AZ-WS-001"] == FAIL


def test_report_has_phase_coverage(azure_catalog):
    facts = azure_tfplan.collect(non_pl_plan())
    result = assess(azure_catalog, facts)
    data = report.to_dict(result, azure_catalog, facts)
    phases = {row["phase"]: row for row in data["phase_coverage"]}
    assert sorted(phases) == list(range(1, 11))
    assert phases[4]["checks"] > 10 and phases[6]["checks"] == 0
    md = report.to_markdown(result, azure_catalog, facts)
    assert "## Coverage by production planning phase" in md and "_not covered yet_" in md
    assert "**Production planning guide:** [Phase 9: Observability]" in md


def test_doctor_only_runs_read_commands_and_prints_registration(monkeypatch, capsys):
    from wa_agent import doctor

    issued = []
    monkeypatch.setattr(doctor, "_probe", lambda cmd: (issued.append(cmd) or (True, "ok")))
    assert doctor.run() == 0
    assert [c[:2] for c in issued] == [["az", "account"], ["az", "extension"], ["gcloud", "config"], ["databricks", "--version"],
                                      ["databricks", "auth"], ["terraform", "version"], ["uv", "--version"]]
    out = capsys.readouterr().out
    assert "claude mcp add --scope user databricks-wa -- uv run --quiet --frozen --project" in out
    assert "codex mcp add databricks-wa" in out


def test_project_mcp_configs_point_at_the_agent():
    repo = __import__("pathlib").Path(__file__).resolve().parents[2]
    for rel, key in ((".mcp.json", "mcpServers"), (".cursor/mcp.json", "mcpServers")):  # committed configs
        server = json.loads((repo / rel).read_text(encoding="utf-8"))[key]["databricks-wa"]
        assert server["command"] == "uv" and server["args"][-1] == "wa-agent-mcp", rel
        assert "--frozen" in server["args"], rel  # never relock through a private index at launch


def test_workspace_resolves_from_name_url_or_id_and_profiles_auto_match():
    arm = "/subscriptions/s/resourceGroups/rg/providers/Microsoft.Databricks/workspaces/ws1"
    listing = [{"id": arm, "name": "ws1", "workspaceUrl": "adb-1.2.azuredatabricks.net", "workspaceId": "1"}]
    run = lambda args: listing if args[:4] == ["az", "databricks", "workspace", "list"] else None  # noqa: E731
    for ref in ("ws1", "https://adb-1.2.azuredatabricks.net", "1", arm):
        assert azure_live.resolve_workspace(ref, run) == arm
    with pytest.raises(RuntimeError, match="no workspace matching"):
        azure_live.resolve_workspace("nope", run)
    profiles = {"profiles": [
        {"name": "stale", "host": "https://adb-1.2.azuredatabricks.net", "valid": False},
        {"name": "ws", "host": "https://adb-1.2.azuredatabricks.net", "valid": True},
        {"name": "acct", "host": "https://accounts.azuredatabricks.net", "valid": True},
    ]}
    assert azure_live.match_profiles("adb-1.2.azuredatabricks.net", lambda a: profiles) == ("ws", "acct")


def test_demo_runs_without_cloud_access(tmp_path, capsys):
    out = tmp_path / "demo.md"
    assert main(["demo", "-o", str(out)]) == 0
    md = out.read_text(encoding="utf-8")
    assert "## Prescription" in md and "AZ-ING-001" in md
    assert "no cloud calls are made" in capsys.readouterr().err


def test_redaction_masks_ids_secrets_and_learned_names():
    from wa_agent.redact import redact

    # Synthetic values only. Token-shaped strings are assembled at runtime so no
    # credential-like literal exists in source (and secret scanners stay quiet).
    fake_pat = "dapi" + "0123456789abcdef" * 2
    fake_aws = "AKIA" + "ABCDEFGHIJKLMNOP"
    raw = ("ws /subscriptions/11111111-2222-3333-4444-555555555555/resourceGroups/prod-rg/providers/"
           "Microsoft.Databricks/workspaces/fin-ws host adb-9876543210123456.7.azuredatabricks.net "
           f"id 9876543210123456 user jane.doe@example.com token {fake_pat} "
           f"ARM_CLIENT_SECRET=s3cr3t-value AccountKey=abc123== {fake_aws} profile fin-admin")
    out = redact(raw, {"fin-admin"})
    for leaked in ("11111111-2222", "prod-rg", "fin-ws", "9876543210123456", "jane.doe", fake_pat, "s3cr3t",
                   "abc123==", fake_aws, "fin-admin"):
        assert leaked not in out, leaked
    assert "<guid>" in out and "<databricks-token>" in out and "<redacted>" in out


def test_doctor_redacts_by_default(monkeypatch, capsys):
    from wa_agent import doctor

    monkeypatch.setattr(doctor, "_probe", lambda cmd: (True, "Contoso-Prod-Subscription"
                                                       if cmd[:3] == ["az", "account", "show"] else "ok"))
    doctor.run()
    out = capsys.readouterr().out
    assert "Contoso-Prod-Subscription" not in out and "safe to paste into an issue" in out
    assert "issues/new?template=wa-agent-problem.yml" in out
    doctor.run(show_ids=True)
    assert "Contoso-Prod-Subscription" in capsys.readouterr().out




def test_baselines_read_as_titled_controls_by_area(azure_catalog):
    from wa_agent.describe import controls, to_markdown

    rows = controls(azure_catalog, "classic-full-pl")
    assert [r["phase"] for r in rows] == sorted(r["phase"] for r in rows)
    promoted = {r["check"]: r["level"] for r in rows}
    assert promoted["AZ-ENC-001"] == "recommended"  # offered by the cmk option, not chosen
    assert promoted["AZ-UC-001"] == "required"  # bare minimum
    md = to_markdown(azure_catalog, "classic-no-pl")
    assert "## Options" in md and "| `cmk` |" in md and "allowed_ip_ranges" in md
    assert "## Network" in md and "| Required | Workspace is VNet-injected (customer-managed VNet) | `AZ-NET-001` |" in md
    assert to_markdown(azure_catalog, "classic-no-pl").startswith("# Classic — your VNet, no Private Link")
    with pytest.raises(ValueError, match="unknown baseline or pattern"):
        to_markdown(azure_catalog, "nope")


def test_report_lists_controls_by_title_not_bare_ids(azure_catalog):
    facts = azure_tfplan.collect(non_pl_plan())
    md = report.to_markdown(assess(azure_catalog, facts, baseline_id="classic-full-pl", options=["cmk"]),
                            azure_catalog, facts)
    assert "requires Customer-managed key for managed services (`AZ-ENC-001`)" in md
    assert "Options not chosen" in md and "`public-access`" in md


def test_diagram_is_drawn_from_the_plan_and_deterministic():
    from wa_agent.diagram import to_markdown

    classic = to_markdown(non_pl_plan())
    assert classic == to_markdown(non_pl_plan())
    assert 'VNET -->|"outbound via NAT gateway"| NET["Internet"]' in classic
    assert 'USERS -->|"HTTPS over internet · IP access list"| WS' in classic
    assert "| Network | `azurerm_subnet` | 2 |" in classic and "class WS focus" in classic
    private = to_markdown(full_private_plan())
    assert 'USERS -->|"HTTPS via private endpoint only"| WS' in private and "over Private Link" in private
    serverless = to_markdown(serverless_plan(cmk=True, storage_pe=True))
    assert "VNET" not in serverless and "egress restricted and enforced" in serverless
    assert '-->|"encrypts managed services"| WS' in serverless
    for line in classic.splitlines():  # every Mermaid arrow carries a label
        if "-->" in line:
            assert "-->|" in line, line


def test_cli_show_and_diagram(tmp_path, capsys):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(non_pl_plan()), encoding="utf-8")
    assert main(["show", "classic-no-pl"]) == 0
    assert "## Observability" in capsys.readouterr().out
    out = tmp_path / "architecture.md"
    assert main(["diagram", "--tf-json", str(plan), "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("# Architecture — ws-demo")


def test_run_book_draws_each_stage_and_the_result(azure_catalog):
    from wa_agent.new import render

    readme = render(azure_catalog, "classic-full-pl", IPS)["README.md"]
    assert "wa-agent diagram --tf-json stage1.plan.json -o stage1.architecture.md" in readme
    assert "wa-agent diagram --tf-json state.json -o architecture.md" in readme


def test_answers_override_stage_settings_instead_of_being_shadowed(azure_catalog):
    from wa_agent.new import render

    files = render(azure_catalog, "serverless", {"allowed_ip_ranges": ["198.51.100.7/32"],
                                                 "enable_diagnostic_settings": False, "location": "eastus2"})
    stage = {line.split("=")[0].strip(): line.split("=", 1)[1].strip()
             for line in files["stage-1-deploy.tfvars"].splitlines() if "=" in line and not line.startswith("#")}
    assert stage["allowed_ip_ranges"] == '["198.51.100.7/32"]'
    assert stage["enable_diagnostic_settings"] == "false"
    assert "allowed_ip_ranges" not in files["inputs.tfvars"] and 'location            = "eastus2"' in files["inputs.tfvars"]
    assert "allowed_ip_ranges" not in json.loads(files["baseline.json"])["placeholders"]


def test_live_scan_without_workspace_profile_never_calls_the_workspace_api():
    calls = []

    def run(args):
        calls.append(args)
        return None

    azure_live._databricks(run, {"workspaceUrl": "adb-1.2.azuredatabricks.net", "workspaceId": "1"}, None, None)
    assert not [a for a in calls if a[:1] == ["databricks"] and "--profile" not in a and "account" not in a]
    assert not [a for a in calls if "--host" in a]



def test_this_repo_is_the_only_source_of_terraform(azure_catalog):
    import copy

    from wa_agent.catalog import CatalogError, validate_baselines

    baselines = copy.deepcopy(azure_catalog["baselines"])
    b = next(b for b in baselines if b.get("build"))
    b["build"] = {"source": {"repo": "https://github.com/databricks/terraform-databricks-sra"}, "stages": b["build"]["stages"]}
    with pytest.raises(CatalogError, match="deployment in this repo"):
        validate_baselines(baselines, azure_catalog["patterns"], azure_catalog["checks"])
    for path in Path(__file__).resolve().parents[2].glob("adb4u/deployments/*/*.tf"):
        assert "git::" not in path.read_text(encoding="utf-8"), path  # no external module sources


def test_hub_spoke_is_assessed_not_generated(azure_catalog, tmp_path):
    from wa_agent.new import generate

    with pytest.raises(ValueError, match="no tested deployment"):
        generate(azure_catalog, "classic-dep", str(tmp_path / "x"))


def _hub_spoke_fake(firewall_ip="10.0.0.4", app_rules=True, firewall_logs=True):
    """A spoke whose default route points at an Azure Firewall in a peered hub."""
    spoke_vnet = "/subscriptions/s/resourceGroups/spoke-rg/providers/Microsoft.Network/virtualNetworks/spoke"
    hub_vnet = "/subscriptions/s/resourceGroups/hub-rg/providers/Microsoft.Network/virtualNetworks/hub"
    fw_id = "/subscriptions/s/resourceGroups/hub-rg/providers/Microsoft.Network/azureFirewalls/fw"
    policy_id = "/subscriptions/s/resourceGroups/hub-rg/providers/Microsoft.Network/firewallPolicies/pol"
    rcg_id = f"{policy_id}/ruleCollectionGroups/databricks"
    ws_id = "/subscriptions/s/resourceGroups/spoke-rg/providers/Microsoft.Databricks/workspaces/ws"
    subnet = {"delegations": [{"serviceName": "Microsoft.Databricks/workspaces"}], "networkSecurityGroup": {"id": "nsg"},
              "routeTable": {"id": "rt"}, "addressPrefix": "10.1.0.0/24"}
    rule = {"ruleType": "ApplicationRule" if app_rules else "NetworkRule"}

    def fake(args):
        a = tuple(args)
        if a[:4] == ("az", "databricks", "workspace", "show"):
            return {"id": ws_id, "name": "ws", "sku": {"name": "premium"}, "publicNetworkAccess": "Disabled",
                    "workspaceUrl": "adb-1.azuredatabricks.net",
                    "parameters": {"customVirtualNetworkId": {"value": spoke_vnet}, "enableNoPublicIp": {"value": True},
                                   "customPublicSubnetName": {"value": "pub"}, "customPrivateSubnetName": {"value": "priv"}}}
        if a[:5] == ("az", "network", "vnet", "subnet", "show"):
            return subnet
        if a[:4] == ("az", "network", "route-table", "show"):
            return {"routes": [{"addressPrefix": "0.0.0.0/0", "nextHopType": "VirtualAppliance",
                                "nextHopIpAddress": "10.0.0.4"}]}
        if a[:5] == ("az", "network", "vnet", "peering", "list"):
            return [{"peeringState": "Connected", "remoteVirtualNetwork": {"id": hub_vnet}}]
        if a[:3] == ("az", "resource", "list") and "Microsoft.Network/azureFirewalls" in a:
            return [{"id": fw_id}] if "hub-rg" in a else []
        if a[:3] == ("az", "resource", "show") and fw_id in a:
            return {"properties": {"ipConfigurations": [{"properties": {"privateIPAddress": firewall_ip}}],
                                   "firewallPolicy": {"id": policy_id}}}
        if a[:3] == ("az", "resource", "show") and policy_id in a and rcg_id not in a:
            return {"properties": {"ruleCollectionGroups": [{"id": rcg_id}]}}
        if a[:3] == ("az", "resource", "show") and rcg_id in a:
            return {"properties": {"ruleCollections": [{"rules": [rule]}]}}
        if a[:4] == ("az", "monitor", "diagnostic-settings", "list"):
            return [{"name": "fw-logs"}] if fw_id in a and firewall_logs else []
        return None

    return ws_id, fake


def test_live_hub_spoke_follows_peering_to_the_firewall_and_its_rules(azure_catalog):
    ws_id, fake = _hub_spoke_fake()
    facts = azure_live.collect(ws_id, run=fake, databricks_profile="ws")
    net = facts["network"]
    assert net["hub_peering"] and net["firewall_present"] and net["firewall_application_rules"] and net["firewall_logs"]
    s = statuses(assess(azure_catalog, facts, baseline_id="classic-dep"))
    assert s["AZ-NET-006"] == s["AZ-NET-010"] == s["AZ-NET-011"] == s["AZ-OPS-002"] == PASS
    assert "ruleCollectionGroups" in facts["_evidence"]["network.firewall_application_rules"][0]

    _, fake = _hub_spoke_fake(app_rules=False, firewall_logs=False)
    s = statuses(assess(azure_catalog, azure_live.collect(ws_id, run=fake, databricks_profile="ws"),
                        baseline_id="classic-dep"))
    assert s["AZ-NET-011"] == FAIL and s["AZ-OPS-002"] == FAIL


def test_live_hub_spoke_unknown_when_next_hop_is_not_a_readable_azure_firewall(azure_catalog):
    ws_id, fake = _hub_spoke_fake(firewall_ip="10.9.9.9")  # an NVA, or a firewall we can't read
    facts = azure_live.collect(ws_id, run=fake, databricks_profile="ws")
    assert "firewall_application_rules" not in facts["network"]
    s = statuses(assess(azure_catalog, facts, baseline_id="classic-dep"))
    assert s["AZ-NET-011"] == UNKNOWN and s["AZ-OPS-002"] == UNKNOWN and s["AZ-NET-010"] == PASS


def test_plan_hub_spoke_facts_only_where_the_plan_shows_them(azure_catalog):
    plan = full_private_plan()
    facts = azure_tfplan.collect(plan)
    assert not {"hub_peering", "firewall_application_rules", "firewall_logs"} & set(facts["network"])
    plan["resource_changes"] += [
        rc("module.hub.azurerm_firewall.this", "azurerm_firewall", {"name": "fw"}),
        rc("module.hub.azurerm_firewall_policy_rule_collection_group.databricks",
           "azurerm_firewall_policy_rule_collection_group", {"application_rule_collection": [{"name": "dbx"}]}),
        rc("module.hub.azurerm_monitor_diagnostic_setting.firewall", "azurerm_monitor_diagnostic_setting", {}),
        rc("azurerm_virtual_network_peering.spoke_to_hub", "azurerm_virtual_network_peering", {}),
    ]
    net = azure_tfplan.collect(plan)["network"]
    assert net["hub_peering"] and net["firewall_application_rules"] and net["firewall_logs"]


def test_hub_spoke_reads_stay_on_the_allowlist():
    for args in (["az", "network", "vnet", "peering", "list", "-g", "rg", "--vnet-name", "v"],
                 ["az", "resource", "show", "--ids", "x"]):
        azure_live.assert_read_only(args)
    for args in (["az", "network", "vnet", "peering", "create", "-g", "rg"], ["az", "resource", "delete", "--ids", "x"]):
        with pytest.raises(azure_live.ReadOnlyViolation):
            azure_live.assert_read_only(args)



def test_ip_access_lists_and_serverless_egress_are_required_everywhere(azure_catalog):
    minimum = {"AZ-ING-001", "AZ-SRV-002"}
    for p in azure_catalog["patterns"]["patterns"]:
        assert minimum <= set(p["required"]), p["id"]
        assert not minimum & set(p["recommended"]), p["id"]
    for b in azure_catalog["baselines"]:
        tv = {k: v for st in (b.get("build") or {}).get("stages", []) for k, v in st["tfvars"].items()}
        if b.get("build"):
            assert tv.get("enable_ip_access_lists") is True and tv.get("enable_network_policy") is True, b["id"]
            assert tv.get("network_policy_enforcement_mode") == "ENFORCED", b["id"]
