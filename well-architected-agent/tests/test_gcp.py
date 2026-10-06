"""GCP: catalog, plan/state collector, live collector, builds. Plans are shaped like the gcpdb4u roots."""

import json

import pytest

from conftest import rc
from wa_agent import catalog
from wa_agent.clouds.gcp import live as gcp_live, tfplan as gcp_tfplan
from wa_agent.engine import FAIL, NOT_APPLICABLE, PASS, UNKNOWN, assess
from wa_agent.facts import merge


IPS = {"allowed_ip_ranges": ["203.0.113.0/24"]}


@pytest.fixture(scope="module")
def gcp_catalog():
    return catalog.load("gcp")


def statuses(result):
    return {f.check["id"]: f.status for f in result.findings}


def plan(*changes):
    return {"format_version": "1.2", "resource_changes": list(changes)}


def workspace(**kw):
    values = {"workspace_name": "labs-ws1", "network_id": "net-1", "private_access_settings_id": None,
              "managed_services_customer_managed_key_id": None, "storage_customer_managed_key_id": None}
    values.update(kw)
    return rc("databricks_mws_workspaces.databricks_workspace", "databricks_mws_workspaces", values)


def infra4db(restricted=False, psc=True):
    """infra4db: VPC, subnet with PGA, NAT, deny-all egress, googleapis DNS, PSC endpoints."""
    changes = [
        rc("google_compute_network.vpc", "google_compute_network", {"name": "dbx-vpc"}),
        rc('google_compute_subnetwork.subnets["us-central1"]', "google_compute_subnetwork",
           {"name": "subnet-us-central1", "ip_cidr_range": "10.0.0.0/24", "private_ip_google_access": True}),
        rc('google_compute_router_nat.nats["us-central1"]', "google_compute_router_nat", {}),
        rc("google_compute_firewall.deny_egress_all", "google_compute_firewall",
           {"direction": "EGRESS", "deny": [{"protocol": "all"}], "destination_ranges": ["0.0.0.0/0"]}),
        rc("google_dns_managed_zone.private_googleapis", "google_dns_managed_zone",
           {"dns_name": "googleapis.com.", "visibility": "private"}),
        rc("google_dns_record_set.private_googleapis_cname", "google_dns_record_set",
           {"name": "*.googleapis.com.", "rrdatas": ["restricted.googleapis.com." if restricted else "private.googleapis.com."]}),
    ]
    if psc:
        changes += [
            rc('google_compute_subnetwork.psc_subnets["us-central1"]', "google_compute_subnetwork",
               {"name": "psc-subnet-us-central1", "ip_cidr_range": "10.1.255.0/28", "private_ip_google_access": True}),
            rc("google_dns_managed_zone.databricks", "google_dns_managed_zone",
               {"dns_name": "gcp.databricks.com.", "visibility": "private"}),
        ]
    return plan(*changes)


def byovpc_psc_cmek(public=False):
    return plan(
        workspace(private_access_settings_id="pas-1", managed_services_customer_managed_key_id="k1",
                  storage_customer_managed_key_id="k1"),
        rc("databricks_mws_networks.databricks_network", "databricks_mws_networks",
           {"vpc_endpoints": [{"dataplane_relay": ["relay-ep"], "rest_api": ["ws-ep"]}]}),
        rc("databricks_mws_vpc_endpoint.relay_vpce", "databricks_mws_vpc_endpoint", {}),
        rc("databricks_mws_vpc_endpoint.workspace_vpce", "databricks_mws_vpc_endpoint", {}),
        rc("databricks_mws_private_access_settings.pas", "databricks_mws_private_access_settings",
           {"public_access_enabled": public, "private_access_level": "ACCOUNT"}),
        rc("databricks_metastore_assignment.this", "databricks_metastore_assignment", {}),
    )


def guardrails(ip_acl=True):
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
                       {"list_type": "ALLOW", "enabled": True})]
    return plan(*changes)


def collected(*plans):
    facts: dict = {}
    for p in plans:
        facts = merge(facts, gcp_tfplan.collect(p))
    return facts


def test_catalog_requires_the_bare_minimum_everywhere(gcp_catalog):
    for p in gcp_catalog["patterns"]["patterns"]:
        assert {"GCP-ING-001", "GCP-SRV-002"} <= set(p["required"]), p["id"]
    assert all(c["guide_url"].startswith("https://docs.databricks.com/gcp/en/lakehouse-architecture/deployment-guide/")
               for c in gcp_catalog["checks"])


def test_new_vpc_build_plans_merge_into_a_conformant_high_security_workspace(gcp_catalog):
    facts = collected(infra4db(), byovpc_psc_cmek(public=False), guardrails(ip_acl=False))
    result = assess(gcp_catalog, facts, baseline_id="classic-full-pl")
    s = statuses(result)
    assert result.detected["id"] == "classic-full-pl"
    assert s["GCP-ING-001"] == NOT_APPLICABLE  # no public front-end
    assert s["GCP-SRV-002"] == PASS and s["GCP-PL-003"] == PASS and s["GCP-ENC-002"] == PASS
    assert s["GCP-WS-001"] == FAIL  # data-leak settings are at their defaults in these roots
    assert s["GCP-OPS-001"] == UNKNOWN  # audit log delivery is account-level, not in these plans


def test_without_guardrails_the_bare_minimum_fails(gcp_catalog):
    s = statuses(assess(gcp_catalog, collected(infra4db(psc=False), plan(workspace())), baseline_id="classic-no-pl"))
    assert s["GCP-ING-001"] == FAIL and s["GCP-SRV-002"] == FAIL
    s = statuses(assess(gcp_catalog, collected(infra4db(psc=False), plan(workspace()), guardrails()),
                        baseline_id="classic-no-pl"))
    assert s["GCP-ING-001"] == PASS and s["GCP-SRV-002"] == PASS and s["GCP-NET-004"] == PASS


def test_dep_needs_restricted_google_apis_and_a_perimeter(gcp_catalog):
    facts = collected(infra4db(restricted=False), byovpc_psc_cmek(), guardrails(ip_acl=False))
    s = statuses(assess(gcp_catalog, facts, baseline_id="classic-dep"))
    assert s["GCP-NET-005"] == PASS  # infra4db's deny-egress-all
    assert s["GCP-NET-006"] == FAIL  # infra4db points *.googleapis.com at private.googleapis.com
    assert s["GCP-NET-007"] == UNKNOWN  # the perimeter isn't in these plans
    restricted = collected(infra4db(restricted=True), byovpc_psc_cmek(),
                           plan(rc("google_access_context_manager_service_perimeter.dbx",
                                   "google_access_context_manager_service_perimeter", {})))
    s = statuses(assess(gcp_catalog, restricted, baseline_id="classic-dep"))
    assert s["GCP-NET-006"] == PASS and s["GCP-NET-007"] == PASS


def test_lpw_plan_with_its_toggles(gcp_catalog):
    lpw = plan(
        workspace(managed_services_customer_managed_key_id="k", storage_customer_managed_key_id="k",
                  network_connectivity_config_id="ncc-1"),
        rc("module.prereqs.google_compute_subnetwork.workspace[0]", "google_compute_subnetwork",
           {"name": "ws-subnet", "ip_cidr_range": "10.1.0.0/24", "private_ip_google_access": True}),
        rc("module.prereqs.google_compute_network.vpc[0]", "google_compute_network", {}),
        rc("databricks_mws_networks.network", "databricks_mws_networks", {"vpc_endpoints": []}),
        *guardrails()["resource_changes"],
    )
    facts = gcp_tfplan.collect(lpw)
    assert facts["workspace"]["customer_managed_vpc"] and facts["workspace"]["public_access_enabled"]
    s = statuses(assess(gcp_catalog, facts, baseline_id="classic-no-pl", options=["cmk"]))
    assert s["GCP-ENC-001"] == s["GCP-ENC-002"] == s["GCP-ING-001"] == s["GCP-SRV-002"] == PASS
    assert s["GCP-NET-004"] == FAIL  # lpw relies on PSC/PGA rather than Cloud NAT in this shape


def test_every_gcp_build_renders_and_builds_are_peers(gcp_catalog):
    from wa_agent.new import builds, render

    answers = {"lpw": {"google_region": "us-central1", "metastore_name": "ms", **IPS},
               "new-vpc": {"google_region": "us-central1", "network_name": "dbx-vpc", **IPS},
               "existing-vpc": {"google_region": "us-central1", **IPS},
               "default": {"google_region": "us-central1", **IPS}}
    for b in gcp_catalog["baselines"]:
        options = builds(b)
        if b["id"] in ("classic-dep", "classic-backend-pl"):  # assess-only
            assert options == []
            continue
        if b["id"] == "serverless":
            assert [o["id"] for o in options] == ["default"]
            files = render(gcp_catalog, "serverless", answers["default"])
            assert "serverless-ws" in files["README.md"] and "inputs-workspace-guardrails.tfvars" in files
            continue
        assert {o["id"] for o in options} == {"lpw", "new-vpc", "existing-vpc"}
        with pytest.raises(ValueError, match="choose one with --build"):
            render(gcp_catalog, b["id"])
        for o in options:
            files = render(gcp_catalog, b["id"], answers[o["id"]], build_id=o["id"])
            readme = files["README.md"]
            assert "--cloud gcp" in readme and "GOOGLE_OAUTH_ACCESS_TOKEN" in readme
            tv = {k: v for st in o["stages"] for k, v in st["tfvars"].items()}
            assert tv.get("enable_network_policy") is True and tv.get("network_policy_enforcement_mode") == "ENFORCED"


def test_new_vpc_links_roots_and_reads_the_workspace_url(gcp_catalog):
    from wa_agent.new import render

    files = render(gcp_catalog, "classic-full-pl", {"google_region": "us-central1", "network_name": "dbx-vpc", **IPS},
                   build_id="new-vpc", options=["public-access"])
    ws = files["stage-2-workspace.tfvars"]
    assert 'google_vpc_id        = "dbx-vpc"' in ws and 'node_subnet          = "subnet-us-central1"' in ws
    assert 'relay_pe             = "us-central1-relay-psc-ep"' in ws
    readme = files["README.md"]
    assert "cp terraform.tfvars.remove terraform.tfvars" in readme
    assert ('-var "workspace_url=$(terraform -chdir="$BOOK/terraform/gcpdb4u/templates/terraform-scripts/byovpc-psc-ws" '
            'output -raw workspace_url)"') in readme
    assert readme.count("terraform init") == 3  # three roots
    assert "inputs-workspace-guardrails.tfvars" in files
    meta = json.loads(files["baseline.json"])
    assert meta["build"] == "new-vpc" and len(meta["deployments"]) == 3
    assert '"203.0.113.0/24"' in ws  # the PSC root applies the user's IP ranges
    with pytest.raises(ValueError, match="can't do public-access [+] cmk"):
        render(gcp_catalog, "classic-full-pl", {"google_region": "us-central1", **IPS}, build_id="new-vpc",
               options=["public-access", "cmk"])
    private = render(gcp_catalog, "classic-full-pl", {"google_region": "us-central1", **IPS}, build_id="existing-vpc")
    assert "byovpc-psc-cmek-ws" in json.loads(private["baseline.json"])["deployments"][0]


def test_bundle_includes_committed_example_config_but_never_state(gcp_catalog, tmp_path):
    from wa_agent.new import generate

    out = tmp_path / "book"
    generate(gcp_catalog, "classic-no-pl", str(out), {"google_region": "us-central1", **IPS}, build_id="existing-vpc",
             options=["data-leak"])
    root = out / "terraform" / "gcpdb4u" / "templates" / "terraform-scripts"
    acl = (root / "workspace-guardrails" / "ip_access_list.yaml").read_text(encoding="utf-8")
    assert "- 203.0.113.0/24" in acl and "office-allow" not in acl  # written from the answer, not the sample
    assert "disable_data_leak_features" in (out / "stage-2-guardrails.tfvars").read_text(encoding="utf-8")
    assert (root / "byovpc-ws" / "workspace.auto.tfvars").is_file()  # committed example config, used as-is
    assert (root / "workspace-guardrails" / "network_policy.yaml").is_file()
    assert not [p for p in out.rglob("*") if p.name.endswith(".tfstate") or p.name == "terraform.tfvars"]


def _fake_gcp(perimeter=True, restricted=True, logs=True):
    ws = {"workspace_id": 111, "workspace_name": "labs-ws1", "deployment_name": "111.1", "network_id": "net-1",
          "private_access_settings_id": "pas-1", "storage_customer_managed_key_id": "k",
          "managed_services_customer_managed_key_id": "k", "network_connectivity_config_id": "ncc-1",
          "cloud_resource_container": {"gcp": {"project_id": "svc-prj"}}}

    def fake(args):
        a = tuple(args)
        if a[:3] == ("databricks", "auth", "profiles"):
            return {"profiles": [{"name": "acct", "host": "https://accounts.gcp.databricks.com", "valid": True},
                                 {"name": "ws", "host": "https://111.1.gcp.databricks.com", "valid": True}]}
        if "workspaces" in a and "list" in a:
            return [ws]
        if "workspaces" in a and "get" in a:
            return ws
        if "private-access" in a:
            return {"public_access_enabled": False, "private_access_level": "ENDPOINT"}
        if "networks" in a and "get" in a:
            return {"gcp_network_info": {"network_project_id": "host-prj", "vpc_id": "dbx-vpc",
                                         "subnet_id": "subnet-us-central1", "subnet_region": "us-central1"},
                    "vpc_endpoints": {"dataplane_relay": ["r"], "rest_api": ["w"]}}
        if "log-delivery" in a:
            return [{"log_type": "AUDIT_LOGS", "status": "ENABLED"}] if logs else []
        if "get-workspace-network-option-rpc" in a:
            return {"network_policy_id": "np-1"}
        if "get-network-policy-rpc" in a:
            return {"egress": {"network_access": {"restriction_mode": "RESTRICTED_ACCESS",
                                                  "policy_enforcement": {"enforcement_mode": "ENFORCED"}}}}
        if "get-network-connectivity-configuration" in a:
            return {"egress_config": {}}
        if a[:5] == ("gcloud", "compute", "networks", "subnets", "describe"):
            return {"ipCidrRange": "10.0.0.0/24", "privateIpGoogleAccess": True}
        if a[:4] == ("gcloud", "compute", "routers", "list"):
            return [{"nats": [{"name": "nat"}]}]
        if a[:4] == ("gcloud", "compute", "firewall-rules", "list"):
            return [{"direction": "EGRESS", "denied": [{"IPProtocol": "all"}], "destinationRanges": ["0.0.0.0/0"]}]
        if a[:4] == ("gcloud", "dns", "managed-zones", "list"):
            net = [{"networkUrl": "https://www.googleapis.com/compute/v1/projects/host-prj/global/networks/dbx-vpc"}]
            return [{"name": "dbx", "dnsName": "gcp.databricks.com.", "visibility": "private",
                     "privateVisibilityConfig": {"networks": net}},
                    {"name": "gapi", "dnsName": "googleapis.com.", "visibility": "private",
                     "privateVisibilityConfig": {"networks": net}}]
        if a[:4] == ("gcloud", "dns", "record-sets", "list"):
            return [{"name": "*.googleapis.com.", "rrdatas": ["restricted.googleapis.com." if restricted
                                                              else "private.googleapis.com."]}]
        if a[:3] == ("gcloud", "projects", "describe"):
            return {"projectNumber": "999" if "svc-prj" in a else "888"}
        if a[:3] == ("gcloud", "projects", "get-ancestors"):
            return [{"type": "project", "id": "x"}, {"type": "organization", "id": "42"}]
        if a[:4] == ("gcloud", "access-context-manager", "policies", "list"):
            return [{"name": "accessPolicies/7"}]
        if a[:4] == ("gcloud", "access-context-manager", "perimeters", "list"):
            return [{"status": {"resources": ["projects/999"] if perimeter else []}}]
        return None

    return fake


def test_live_scan_reads_account_api_and_gcloud(gcp_catalog):
    facts = gcp_live.collect("labs-ws1", run=_fake_gcp())
    assert facts["_scan"]["account_profile"] == "acct" and facts["_scan"]["profile"] == "ws"
    assert facts["network"] == {"smallest_subnet_prefix_length": 24, "private_google_access": True, "cloud_nat": True,
                                "egress_deny_default": True, "google_apis_endpoint": "restricted",
                                "service_perimeter": True}
    s = statuses(assess(gcp_catalog, facts, baseline_id="classic-dep"))
    for check in ("GCP-NET-005", "GCP-NET-006", "GCP-NET-007", "GCP-PL-001", "GCP-PL-002", "GCP-PL-003",
                  "GCP-PL-004", "GCP-DNS-001", "GCP-ENC-001", "GCP-SRV-002", "GCP-OPS-001"):
        assert s[check] == PASS, check
    s = statuses(assess(gcp_catalog, gcp_live.collect("labs-ws1", run=_fake_gcp(perimeter=False, restricted=False,
                                                                                 logs=False))))
    assert s["GCP-NET-006"] == FAIL and s["GCP-OPS-001"] == FAIL


def test_live_scan_needs_an_account_profile_and_stays_read_only():
    with pytest.raises(RuntimeError, match="--account-profile"):
        gcp_live.collect("labs-ws1", run=lambda args: {"profiles": []} if "profiles" in args else None)
    for args in (["gcloud", "compute", "firewall-rules", "list", "--project", "p"],
                 ["gcloud", "access-context-manager", "perimeters", "list", "--policy", "1"]):
        gcp_live.assert_read_only(args)
    for args in (["gcloud", "compute", "firewall-rules", "delete", "x"],
                 ["gcloud", "access-context-manager", "perimeters", "update", "p"],
                 ["databricks", "account", "workspaces", "delete", "1"]):
        with pytest.raises(Exception):
            gcp_live.assert_read_only(args)


def test_serverless_workspace_has_no_network_and_keeps_the_bare_minimum(gcp_catalog):
    srv = plan(rc("databricks_mws_workspaces.this", "databricks_mws_workspaces",
                  {"workspace_name": "labs-srv", "compute_mode": "SERVERLESS", "location": "us-east4"}),
               *guardrails()["resource_changes"],
               rc("databricks_metastore_assignment.this[0]", "databricks_metastore_assignment", {}))
    facts = gcp_tfplan.collect(srv)
    assert facts["workspace"]["compute_mode"] == "serverless" and facts["workspace"]["customer_managed_vpc"] is False
    result = assess(gcp_catalog, facts, baseline_id="serverless")
    s = statuses(result)
    assert result.detected["id"] == "serverless"
    assert s["GCP-NET-001"] == s["GCP-ENC-002"] == s["GCP-PL-001"] == NOT_APPLICABLE
    assert s["GCP-ING-001"] == s["GCP-SRV-002"] == s["GCP-UC-001"] == PASS
    assert result.tier_of("GCP-UC-001") == "required"  # bare minimum


def test_context_based_ingress_is_read_from_the_network_policy(gcp_catalog):
    rules = guardrails()["resource_changes"]
    for r in rules:
        if r["type"] == "databricks_account_network_policy":
            r["change"]["after"]["ingress_dry_run"] = {"public_access": {"restriction_mode": "RESTRICTED_ACCESS"}}
    facts = gcp_tfplan.collect(plan(workspace(), *rules))
    assert facts["access"]["context_ingress_enforced"] is False  # dry run only
    for r in rules:
        if r["type"] == "databricks_account_network_policy":
            r["change"]["after"]["ingress"] = r["change"]["after"].pop("ingress_dry_run")
    facts = gcp_tfplan.collect(plan(workspace(), *rules))
    assert facts["access"]["context_ingress_enforced"] is True
    result = assess(gcp_catalog, facts, baseline_id="classic-no-pl", options=["context-ingress"])
    assert result.tier_of("GCP-ING-002") == "required" and statuses(result)["GCP-ING-002"] == PASS
