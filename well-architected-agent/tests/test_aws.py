"""AWS: catalog, plan/state collector, diagram, builds. Plans are shaped like the awsdb4u roots and the SRA (aws/tf)."""

import json

import pytest

from conftest import rc
from wa_agent import catalog
from wa_agent.clouds.aws import live as aws_live, tfplan as aws_tfplan
from wa_agent.engine import FAIL, NOT_APPLICABLE, PASS, UNKNOWN, assess
from wa_agent.facts import merge


IPS = {"allowed_ip_ranges": ["203.0.113.0/24"]}
OPEN_POLICY = json.dumps({"Statement": [{"Effect": "Allow", "Principal": "*", "Action": "*", "Resource": "*"}]})
BUCKET_POLICY = json.dumps({"Statement": [{"Effect": "Allow", "Principal": "*", "Action": ["s3:GetObject"],
                                           "Resource": ["arn:aws:s3:::my-data/*"]}]})


@pytest.fixture(scope="module")
def aws_catalog():
    return catalog.load("aws")


def statuses(result):
    return {f.check["id"]: f.status for f in result.findings}


def plan(*changes):
    return {"format_version": "1.2", "resource_changes": list(changes)}


def indexed(address, rtype, after):
    """A counted resource: the plan's `name` has no index (rc derives it from the address)."""
    r = rc(address, rtype, after)
    r["name"] = r["name"].split("[")[0]
    return r


def network(nat=True, igw=True, policy=None, prefix="module.networking."):
    changes = [rc(f"{prefix}aws_vpc.this", "aws_vpc", {"cidr_block": "10.0.0.0/22"})]
    for i, az in enumerate(("us-west-2a", "us-west-2b")):
        changes += [
            indexed(f"{prefix}aws_subnet.private[{i}]", "aws_subnet",
                    {"availability_zone": az, "cidr_block": f"10.0.{i}.0/24"}),
            indexed(f"{prefix}aws_subnet.privatelink[{i}]", "aws_subnet",
                    {"availability_zone": az, "cidr_block": f"10.0.3.{i * 64}/26"}),
        ]
    changes.append(rc(f'{prefix}aws_vpc_endpoint.s3', "aws_vpc_endpoint",
                      {"service_name": "com.amazonaws.us-west-2.s3", "vpc_endpoint_type": "Gateway",
                       "policy": policy}))
    if nat:
        changes.append(rc(f"{prefix}aws_nat_gateway.this[0]", "aws_nat_gateway", {}))
    if igw:
        changes.append(rc(f"{prefix}aws_internet_gateway.this", "aws_internet_gateway", {}))
    return changes


def production(private_link=False, public=True, cmk=False):
    """awsdb4u aws-pl-ws/databricks-aws-production: VPC, IP access lists, UC; PrivateLink with enable_private_link."""
    ws = {"workspace_name": "prod-ws", "aws_region": "us-west-2", "network_id": None,
          "private_access_settings_id": None, "managed_services_customer_managed_key_id": "k" if cmk else None,
          "storage_customer_managed_key_id": "k" if cmk else None}
    changes = network() + [
        rc("module.databricks_workspace.databricks_mws_workspaces.workspace", "databricks_mws_workspaces", ws,
           {"network_id": True}),
        rc("module.databricks_workspace.databricks_mws_networks.this", "databricks_mws_networks",
           {"vpc_endpoints": [{"dataplane_relay": None, "rest_api": None}] if private_link else []},
           {"vpc_endpoints": [{"dataplane_relay": True, "rest_api": True}]} if private_link else {}),
        rc("module.databricks_workspace.databricks_workspace_conf.this[0]", "databricks_workspace_conf",
           {"custom_config": {"enableIpAccessLists": "true"}}),
        rc("module.databricks_workspace.databricks_ip_access_list.allowed[0]", "databricks_ip_access_list",
           {"list_type": "ALLOW", "enabled": True}),
        rc("module.unity_catalog.databricks_metastore_assignment.this", "databricks_metastore_assignment", {}),
    ]
    if private_link:
        ws["private_access_settings_id"] = None
        changes[-5]["change"]["after_unknown"]["private_access_settings_id"] = True
        changes += [
            rc("module.databricks_workspace.databricks_mws_private_access_settings.pas[0]",
               "databricks_mws_private_access_settings",
               {"public_access_enabled": public, "private_access_level": "ACCOUNT"}),
            rc("module.networking.aws_vpc_endpoint.workspace[0]", "aws_vpc_endpoint",
               {"service_name": "com.amazonaws.vpce.us-west-2.vpce-svc-1", "vpc_endpoint_type": "Interface"}),
            rc("module.databricks_workspace.databricks_mws_vpc_endpoint.workspace_vpce[0]",
               "databricks_mws_vpc_endpoint", {}),
        ]
    return plan(*changes)


def guardrails(ip_acl=False):
    changes = [
        rc("databricks_mws_network_connectivity_config.this[0]", "databricks_mws_network_connectivity_config", {}),
        rc("databricks_mws_ncc_binding.this[0]", "databricks_mws_ncc_binding", {}),
        rc("databricks_account_network_policy.this[0]", "databricks_account_network_policy",
           {"egress": {"network_access": {"restriction_mode": "RESTRICTED_ACCESS",
                                          "policy_enforcement": {"enforcement_mode": "ENFORCED"}}}}),
        rc("databricks_workspace_network_option.this[0]", "databricks_workspace_network_option", {}),
    ]
    if ip_acl:
        changes += [rc("databricks_workspace_conf.ip_acl[0]", "databricks_workspace_conf",
                       {"custom_config": {"enableIpAccessLists": "true"}}),
                    rc('databricks_ip_access_list.this["office-allow"]', "databricks_ip_access_list",
                       {"list_type": "ALLOW", "enabled": True}),
                    rc("databricks_metastore_assignment.this[0]", "databricks_metastore_assignment", {})]
    return plan(*changes)


def sra(serverless=False, isolated=True):
    """SRA aws/tf: account network policy with egress and context-based ingress limited to IP ranges."""
    ws = {"workspace_name": "sra-ws", "aws_region": "us-west-2"}
    if serverless:
        ws["compute_mode"] = "SERVERLESS"
    else:
        ws.update(managed_services_customer_managed_key_id="k", storage_customer_managed_key_id="k")
    changes = [
        rc("module.databricks_mws_workspace.databricks_mws_workspaces.workspace", "databricks_mws_workspaces", ws,
           {"network_id": not serverless, "private_access_settings_id": not serverless}),
        rc("module.network_policy.databricks_account_network_policy.restrictive_network_policy",
           "databricks_account_network_policy",
           {"egress": {"network_access": {"restriction_mode": "RESTRICTED_ACCESS",
                                          "policy_enforcement": {"enforcement_mode": "ENFORCED"}}},
            "ingress": {"public_access": {"restriction_mode": "RESTRICTED_ACCESS", "allow_rules": [
                {"origin": {"included_ip_ranges": {"ip_ranges": ["203.0.113.0/24"]}}}]}}}),
        rc("module.network_policy.databricks_workspace_network_option.workspace_assignment",
           "databricks_workspace_network_option", {}),
        rc("module.ncc.databricks_mws_network_connectivity_config.ncc", "databricks_mws_network_connectivity_config", {}),
        rc("module.ncc.databricks_mws_ncc_binding.ncc_binding", "databricks_mws_ncc_binding", {}),
        rc("module.uc_assignment.databricks_metastore_assignment.default_metastore", "databricks_metastore_assignment",
           {}),
        rc("module.log_delivery[0].databricks_mws_log_delivery.audit_logs", "databricks_mws_log_delivery",
           {"log_type": "AUDIT_LOGS", "status": "ENABLED"}),
    ]
    if not serverless:
        changes += [
            rc("databricks_mws_networks.create_network[0]", "databricks_mws_networks",
               {"vpc_endpoints": [{"dataplane_relay": None, "rest_api": None}]},
               {"vpc_endpoints": [{"dataplane_relay": True, "rest_api": True}]}),
            rc("databricks_mws_private_access_settings.pas", "databricks_mws_private_access_settings",
               {"public_access_enabled": True, "private_access_level": "ACCOUNT"}),
        ]
        if isolated:
            changes += network(nat=False, igw=False, policy=BUCKET_POLICY, prefix="module.vpc[0].")
    return plan(*changes)


def collected(*plans):
    facts: dict = {}
    for p in plans:
        facts = merge(facts, aws_tfplan.collect(p))
    return facts


def test_catalog_requires_the_bare_minimum_everywhere(aws_catalog):
    for p in aws_catalog["patterns"]["patterns"]:
        assert {"AWS-ING-001", "AWS-SRV-002", "AWS-UC-001"} <= set(p["required"]), p["id"]
    assert {b["id"] for b in aws_catalog["baselines"]} == {
        "classic-no-pl", "classic-backend-pl", "classic-full-pl", "classic-dep", "serverless"}
    sra_def = aws_catalog["external"]["sra"]
    assert len(sra_def["commit"]) == 40 and set(sra_def["required"]) <= set(sra_def["variables"])


def test_external_build_is_validated():
    ext = {"sra": {"name": "x", "repo": "https://github.com/databricks/terraform-databricks-sra", "commit": "main",
                   "path": "aws/tf", "license": "x", "variables": ["a"], "required": ["a"]}}
    with pytest.raises(ValueError, match="commit"):
        catalog.validate_external(ext)
    ext["sra"]["commit"] = "0" * 40
    ext["sra"]["required"] = ["b"]
    with pytest.raises(ValueError, match="required"):
        catalog.validate_external(ext)


def test_production_without_guardrails_fails_the_serverless_minimum(aws_catalog):
    facts = collected(production())
    assert facts["network"]["subnet_az_count"] == 2 and facts["network"]["smallest_subnet_prefix_length"] == 24
    result = assess(aws_catalog, facts, baseline_id="classic-no-pl")
    s = statuses(result)
    assert result.detected["id"] == "classic-no-pl"
    assert s["AWS-ING-001"] == PASS and s["AWS-UC-001"] == PASS  # the production root does both
    assert s["AWS-SRV-002"] == FAIL
    assert s["AWS-NET-002"] == s["AWS-NET-003"] == s["AWS-NET-004"] == PASS
    assert s["AWS-NET-005"] == FAIL  # NAT and an internet gateway: egress isn't controlled
    assert s["AWS-NET-006"] == FAIL  # no endpoint policy
    assert s["AWS-OPS-001"] == UNKNOWN  # audit log delivery is account-level, not in this root


def test_production_with_private_link_and_guardrails_is_conformant(aws_catalog):
    facts = collected(production(private_link=True, public=False), guardrails())
    assert facts["private_link"] == {"backend": True, "frontend": True}
    result = assess(aws_catalog, facts, baseline_id="classic-full-pl")
    s = statuses(result)
    assert result.detected["id"] == "classic-full-pl"
    assert s["AWS-ING-001"] == NOT_APPLICABLE  # no public front-end
    assert s["AWS-SRV-002"] == s["AWS-PL-001"] == s["AWS-PL-002"] == s["AWS-PL-003"] == PASS
    assert s["AWS-PL-004"] == FAIL  # ACCOUNT level, recommended only
    public = statuses(assess(aws_catalog, collected(production(private_link=True), guardrails()),
                             baseline_id="classic-full-pl", options=["public-access"]))
    assert public["AWS-ING-001"] == PASS  # the root's IP access list covers the public front-end


def test_sra_isolated_network_is_detected_as_dep(aws_catalog):
    facts = collected(sra())
    net = facts["network"]
    assert net["egress_controlled"] is True and net["nat_gateway"] is False
    assert net["s3_endpoint_policy_restricted"] is True
    assert facts["access"]["public_ingress_ip_restricted"] is True
    result = assess(aws_catalog, facts, baseline_id="classic-dep")
    s = statuses(result)
    assert result.detected["id"] == "classic-dep"
    assert s["AWS-ING-001"] == PASS  # context-based ingress limits public access to IP ranges
    for check in ("AWS-NET-005", "AWS-NET-006", "AWS-SRV-002", "AWS-UC-001", "AWS-ENC-001", "AWS-ENC-002",
                  "AWS-OPS-001"):
        assert s[check] == PASS, check
    assert s["AWS-PL-003"] == FAIL  # the SRA keeps public access on: a known gap of the build


def test_sra_custom_network_leaves_vpc_facts_unknown(aws_catalog):
    facts = collected(sra(isolated=False))
    assert "network" not in facts
    s = statuses(assess(aws_catalog, facts, baseline_id="classic-full-pl", options=["public-access"]))
    assert s["AWS-NET-002"] == s["AWS-NET-003"] == UNKNOWN  # the existing VPC is in another plan
    assert s["AWS-PL-001"] == s["AWS-PL-002"] == PASS


def test_endpoint_policy_must_restrict(aws_catalog):
    assert aws_tfplan._restrictive(BUCKET_POLICY) and not aws_tfplan._restrictive(OPEN_POLICY)
    assert not aws_tfplan._restrictive(None)
    facts = collected(plan(*network(policy=OPEN_POLICY)))
    assert facts["network"]["s3_endpoint_policy_restricted"] is False


def test_serverless_workspaces(aws_catalog):
    srv = plan(rc("databricks_mws_workspaces.this", "databricks_mws_workspaces",
                  {"workspace_name": "srv", "compute_mode": "SERVERLESS", "aws_region": "us-west-2"}))
    facts = collected(srv, guardrails(ip_acl=True))
    assert facts["workspace"]["compute_mode"] == "serverless" and facts["workspace"]["customer_managed_vpc"] is False
    result = assess(aws_catalog, facts, baseline_id="serverless")
    s = statuses(result)
    assert result.detected["id"] == "serverless"
    assert s["AWS-NET-001"] == s["AWS-ENC-002"] == s["AWS-PL-001"] == NOT_APPLICABLE
    assert s["AWS-ING-001"] == s["AWS-SRV-002"] == s["AWS-UC-001"] == PASS
    s = statuses(assess(aws_catalog, collected(sra(serverless=True)), baseline_id="serverless"))
    assert s["AWS-ING-001"] == s["AWS-SRV-002"] == s["AWS-UC-001"] == PASS


def test_diagram_detects_aws_and_lists_each_area_once():
    from wa_agent.diagram import cloud_of, to_markdown

    md = to_markdown(sra())
    assert md == to_markdown(sra())
    assert "no internet path" in md and "S3 gateway endpoint · endpoint policy" in md
    assert "context-based ingress, known IPs" in md and "AWS KMS" in md
    assert "| Network | `aws_vpc` | 1 |" in md and "| Private Link & DNS | `aws_vpc_endpoint` | 1 |" in md
    assert md.count("| Workspace | `databricks_mws_workspaces` | 1 |") == 1
    serverless = plan(rc("databricks_mws_workspaces.this", "databricks_mws_workspaces",
                         {"workspace_name": "srv", "compute_mode": "SERVERLESS", "aws_region": "us-west-2"}))
    assert cloud_of(aws_tfplan.resources(serverless)) == "aws"
    gcp = plan(rc("databricks_mws_workspaces.this", "databricks_mws_workspaces",
                  {"workspace_name": "srv", "compute_mode": "SERVERLESS", "location": "us-east4"}))
    assert cloud_of(aws_tfplan.resources(gcp)) == "gcp"
    nat = to_markdown(production())
    assert "outbound via NAT gateway" in nat and "HTTPS over internet · IP access list" in nat


def test_every_aws_build_renders(aws_catalog):
    from wa_agent.new import builds, render

    region = {"region": "us-west-2", **IPS}
    answers = {"awsdb4u": {**region, "workspace_admin_email": "admin@example.com"},
               "sra": {**region, "resource_prefix": "sra", "admin_user": "admin@example.com"}}
    for b in aws_catalog["baselines"]:
        options = builds(b)
        if b["id"] == "classic-backend-pl":  # assess-only
            assert options == []
            continue
        for o in options:
            build_answers = answers["sra" if o.get("external") else "awsdb4u"]
            if b["id"] == "serverless" and not o.get("external"):
                build_answers = region
            files = render(aws_catalog, b["id"], build_answers, build_id=o["id"] if len(options) > 1 else None)
            readme = files["README.md"]
            assert "--cloud aws" in readme and "DATABRICKS_CLIENT_SECRET" in readme
            assert "collect live" not in readme  # AWS has no live scan
            text = "\n".join(v for k, v in files.items() if k.endswith(".tfvars"))
            assert "client_secret =" not in text  # credentials only from the environment
            if o.get("external"):
                assert "git clone https://github.com/databricks/terraform-databricks-sra" in readme
                assert "bc5af72e46e9ddcf21b7eb246b4e4bad0e3d3be4" in readme
                assert "context_based_ingress_ip_acl" in text and "203.0.113.0/24" in text
                assert not [k for k in files if k.startswith("terraform/")]  # never copied
                meta = json.loads(files["baseline.json"])
                assert meta["external"]["commit"] == "bc5af72e46e9ddcf21b7eb246b4e4bad0e3d3be4"
            elif b["id"] != "serverless":
                assert "allowed_ip_addresses" in text and "203.0.113.0/24" in text


def test_sra_rejects_answers_that_are_not_its_variables(aws_catalog):
    from wa_agent.new import render

    with pytest.raises(ValueError, match="not a variable"):
        render(aws_catalog, "classic-dep", {**IPS, "no_such_variable": "x"})
    with pytest.raises(ValueError, match="TF_VAR_databricks_client_secret"):
        render(aws_catalog, "classic-no-pl", {**IPS, "databricks_client_secret": "x"})


def test_aws_identifiers_are_redacted():
    from wa_agent.redact import redact

    out = redact("arn:aws:sts::123456789012:assumed-role/Admin/me account 123456789012 "
                 "https://dbc-1a2b3c4d-5e6f.cloud.databricks.com")
    assert "123456789012" not in out and "Admin/me" not in out and "1a2b3c4d" not in out


def test_live_scan_is_not_available_yet():
    with pytest.raises(RuntimeError, match="collect tfplan"):
        aws_live.collect("ws")
