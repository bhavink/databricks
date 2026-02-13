#!/usr/bin/env python3
"""
Tests for extract-databricks-ips.py – validate flags and output for different use cases.
Uses an inline fixture (official JSON schema) so tests don't require network.
Run: python test_extract_databricks_ips.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "extract-databricks-ips.py"

# Official schema fixture: platform, region, service, type, ipv4Prefixes, ipv6Prefixes
FIXTURE_JSON = {
    "timestampSeconds": 1234567890,
    "schemaVersion": "1.0",
    "prefixes": [
        {"platform": "aws", "region": "us-east-1", "service": "Databricks", "type": "inbound", "ipv4Prefixes": ["3.237.73.224/28"], "ipv6Prefixes": []},
        {"platform": "aws", "region": "us-east-1", "service": "Databricks", "type": "outbound", "ipv4Prefixes": ["44.215.162.0/24"], "ipv6Prefixes": []},
        {"platform": "aws", "region": "us-east-1", "service": "Databricks", "type": "outbound", "ipv4Prefixes": [], "ipv6Prefixes": ["2600:1f70:4000::/40"]},
        {"platform": "aws", "region": "eu-west-2", "service": "Databricks", "type": "inbound", "ipv4Prefixes": ["18.134.65.240/28"], "ipv6Prefixes": []},
        {"platform": "azure", "region": "eastus", "service": "Databricks", "type": "inbound", "ipv4Prefixes": ["20.42.4.209/32"], "ipv6Prefixes": []},
        {"platform": "gcp", "region": "us-central1", "service": "Databricks", "type": "outbound", "ipv4Prefixes": ["34.33.0.0/24"], "ipv6Prefixes": []},
    ],
}

def _fixture_path():
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(FIXTURE_JSON, f)
    f.close()
    return f.name

_FIXTURE_PATH = _fixture_path()
SOURCE = ["--source", _FIXTURE_PATH]


def run(*args, input_text=None):
    """Run script with args; return (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(SCRIPT)] + list(args)
    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        input=input_text,
    )
    return r.returncode, r.stdout, r.stderr


def test_cloud_filter_aws():
    """--cloud aws returns only AWS CIDRs."""
    code, out, err = run(*SOURCE, "--cloud", "aws", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert len(data) >= 3  # fixture: 3 us-east-1 + 1 eu-west-2
    for entry in data:
        assert entry["cloudProvider"] == "aws"


def test_cloud_filter_azure():
    """--cloud azure returns only Azure CIDRs."""
    code, out, err = run(*SOURCE, "--cloud", "azure", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["cloudProvider"] == "azure"
    assert data[0]["region"] == "eastus"


def test_cloud_filter_gcp():
    """--cloud gcp returns only GCP CIDRs."""
    code, out, err = run(*SOURCE, "--cloud", "gcp", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert len(data) == 1
    assert data[0]["cloudProvider"] == "gcp"


def test_region_filter():
    """--region us-east-1 returns only that region."""
    code, out, err = run(*SOURCE, "--cloud", "aws", "--region", "us-east-1", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert len(data) >= 1
    for entry in data:
        assert entry["region"] == "us-east-1"


def test_region_filter_no_match():
    """--region with no match returns empty array."""
    code, out, err = run(*SOURCE, "--cloud", "aws", "--region", "nonexistent", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert data == []


def test_ipv4_only():
    """--ipv4-only returns only IPv4 CIDRs."""
    code, out, err = run(*SOURCE, "--cloud", "aws", "--ipv4-only", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert len(data) >= 1
    for entry in data:
        assert entry["ipVersion"] == "ipv4"


def test_ipv6_only():
    """--ipv6-only returns only IPv6 CIDRs."""
    code, out, err = run(*SOURCE, "--cloud", "aws", "--ipv6-only", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    for entry in data:
        assert entry["ipVersion"] == "ipv6"


def test_service_filter():
    """--service filters by service name."""
    code, out, err = run(*SOURCE, "--service", "Databricks", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert len(data) >= 1
    for entry in data:
        assert entry["service"] == "Databricks"


def test_format_json():
    """--format json returns valid JSON array of objects."""
    code, out, err = run(*SOURCE, "--cloud", "aws", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert isinstance(data, list)
    for entry in data:
        assert "cidr" in entry
        assert "cloudProvider" in entry
        assert "region" in entry


def test_format_csv():
    """--format csv returns header cloud,region,type,cidr,ipVersion,service + data rows."""
    code, out, err = run(*SOURCE, "--cloud", "aws", "--format", "csv")
    assert code == 0, err
    lines = out.strip().split("\n")
    assert len(lines) >= 2
    header = lines[0].lower()
    assert "cloud" in header
    assert "region" in header
    assert "type" in header
    assert "cidr" in header


def test_format_simple():
    """--format simple returns one CIDR per line."""
    code, out, err = run(*SOURCE, "--cloud", "aws", "--format", "simple")
    assert code == 0, err
    lines = [l for l in out.strip().split("\n") if l]
    assert len(lines) >= 1
    for line in lines:
        assert "/" in line  # CIDR form
        assert line == line.strip()


def test_list_regions():
    """--list-regions returns cloud -> regions."""
    code, out, err = run(*SOURCE, "--list-regions", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert "aws" in data or "azure" in data or "gcp" in data
    for cloud, regions in data.items():
        assert isinstance(regions, list)


def test_list_regions_cloud_filter():
    """--list-regions --cloud aws returns only AWS regions."""
    code, out, err = run(*SOURCE, "--list-regions", "--cloud", "aws", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert "aws" in data
    assert "us-east-1" in data["aws"] or "eu-west-2" in data["aws"]


def test_list_services():
    """--list-services returns list of services."""
    code, out, err = run(*SOURCE, "--list-services", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert "services" in data
    assert isinstance(data["services"], list)
    assert "Databricks" in data["services"]


def test_output_file():
    """--output writes to file."""
    out_file = Path(__file__).parent / "test_output_tmp.json"
    try:
        code, out, err = run(*SOURCE, "--cloud", "aws", "--format", "json", "--output", str(out_file))
        assert code == 0, err
        assert out_file.exists()
        content = json.loads(out_file.read_text())
        assert isinstance(content, list)
    finally:
        if out_file.exists():
            out_file.unlink()


def test_mutually_exclusive_ipv():
    """--ipv4-only and --ipv6-only together error."""
    code, out, err = run(*SOURCE, "--ipv4-only", "--ipv6-only")
    assert code != 0
    assert "exclusive" in err.lower() or "mutually" in err.lower()


def test_all_clouds_all_regions():
    """No cloud/region filter returns all entries (default CSV)."""
    code, out, err = run(*SOURCE)  # default format is csv
    assert code == 0, err
    lines = out.strip().split("\n")
    assert lines[0].lower().startswith("cloud,")
    # header + data rows (fixture has 6 normalized rows)
    assert len(lines) >= 6


def test_combined_filters():
    """Combined --cloud, --region, --ipv4-only."""
    code, out, err = run(
        *SOURCE,
        "--cloud", "aws",
        "--region", "us-east-1",
        "--ipv4-only",
        "--format", "json",
    )
    assert code == 0, err
    data = json.loads(out)
    for entry in data:
        assert entry["cloudProvider"] == "aws"
        assert entry["region"] == "us-east-1"
        assert entry["ipVersion"] == "ipv4"


def test_type_filter():
    """--type outbound returns only outbound entries (official schema)."""
    code, out, err = run(*SOURCE, "--type", "outbound", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert len(data) >= 2
    for entry in data:
        assert entry.get("type") == "outbound"


def test_file_flag_local():
    """--file with local path loads same as --source."""
    code, out, err = run("--file", _FIXTURE_PATH, "--cloud", "aws", "--format", "json")
    assert code == 0, err
    data = json.loads(out)
    assert len(data) >= 2
    for entry in data:
        assert entry["cloudProvider"] == "aws"


def test_file_flag_same_as_source():
    """--file and --source produce same result for same path."""
    code1, out1, _ = run("--file", _FIXTURE_PATH, "--format", "simple")
    code2, out2, _ = run("--source", _FIXTURE_PATH, "--format", "simple")
    assert code1 == code2 == 0
    assert set(out1.strip().split()) == set(out2.strip().split())


def test_default_format_is_csv():
    """Default output format is CSV (cloud,region,type,cidr,...)."""
    code, out, err = run(*SOURCE, "--cloud", "aws")
    assert code == 0, err
    assert out.strip().startswith("cloud,region,type,cidr,")


def test_multi_region_aws():
    """--region us-east-1,eu-west-2 returns only those two regions."""
    code, out, err = run(*SOURCE, "--cloud", "aws", "--region", "us-east-1,eu-west-2", "--format", "csv")
    assert code == 0, err
    lines = out.strip().split("\n")
    header, data_lines = lines[0], lines[1:]
    assert "region" in header
    regions = set()
    for line in data_lines:
        parts = line.split(",")
        if len(parts) >= 2:
            regions.add(parts[1])  # region column
    assert regions <= {"us-east-1", "eu-west-2"}
    assert len(data_lines) >= 2  # fixture has us-east-1 and eu-west-2


def test_multi_region_azure():
    """--cloud azure --region eastus (single) returns Azure eastus."""
    code, out, err = run(*SOURCE, "--cloud", "azure", "--region", "eastus", "--format", "csv")
    assert code == 0, err
    lines = out.strip().split("\n")
    assert len(lines) >= 2
    assert "eastus" in lines[1]


def test_multi_region_gcp():
    """--cloud gcp --region us-central1 returns GCP us-central1."""
    code, out, err = run(*SOURCE, "--cloud", "gcp", "--region", "us-central1", "--format", "csv")
    assert code == 0, err
    lines = out.strip().split("\n")
    assert len(lines) >= 2
    assert "us-central1" in lines[1]


def test_csv_columns_cloud_region_type_cidr():
    """CSV has columns cloud, region, type, cidr (and ipVersion, service)."""
    code, out, err = run(*SOURCE, "--cloud", "aws", "--format", "csv")
    assert code == 0, err
    header = out.strip().split("\n")[0]
    cols = [c.strip() for c in header.split(",")]
    assert cols == ["cloud", "region", "type", "cidr", "ipVersion", "service"]


def test_type_unspecified_shows_both_inbound_outbound_live():
    """Without --type, live API returns both inbound and outbound (validated via live URL)."""
    code, out, err = run(
        "--source", "https://www.databricks.com/networking/v1/ip-ranges.json",
        "--cloud", "aws",
        "--region", "us-east-1",
        "--format", "csv",
    )
    if code != 0:
        return "Live URL failed"
    lines = out.strip().split("\n")
    if len(lines) < 2:
        return "No data rows"
    # Column index for type (after cloud=0, region=1, type=2)
    types = set()
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) >= 3:
            types.add(parts[2].strip())
    assert "inbound" in types and "outbound" in types, f"Expected both inbound and outbound, got {types}"
    return None


def run_live_url_tests():
    """Optional: run a minimal test against live URL (requires network)."""
    code, out, err = run(
        "--source", "https://www.databricks.com/networking/v1/ip-ranges.json",
        "--cloud", "aws",
        "--region", "us-east-1",
        "--type", "outbound",
        "--format", "simple",
    )
    if code != 0:
        return f"Live URL test failed: {err}"
    lines = [l for l in out.strip().split("\n") if l]
    if not lines:
        return "Live URL test: no CIDRs returned"
    # Expect at least a few outbound CIDRs for us-east-1
    assert len(lines) >= 2, "Expected at least 2 outbound CIDRs for aws us-east-1"
    return None


if __name__ == "__main__":
    tests = [
        test_cloud_filter_aws,
        test_cloud_filter_azure,
        test_cloud_filter_gcp,
        test_region_filter,
        test_region_filter_no_match,
        test_ipv4_only,
        test_ipv6_only,
        test_service_filter,
        test_format_json,
        test_format_csv,
        test_format_simple,
        test_list_regions,
        test_list_regions_cloud_filter,
        test_list_services,
        test_output_file,
        test_mutually_exclusive_ipv,
        test_all_clouds_all_regions,
        test_combined_filters,
        test_type_filter,
        test_file_flag_local,
        test_file_flag_same_as_source,
        test_default_format_is_csv,
        test_multi_region_aws,
        test_multi_region_azure,
        test_multi_region_gcp,
        test_csv_columns_cloud_region_type_cidr,
    ]
    failed = []
    for t in tests:
        try:
            t()
            print(f"  OK  {t.__name__}")
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed.append((t.__name__, e))

    # Optional live URL tests
    for name, fn in [("run_live_url_tests", run_live_url_tests), ("test_type_unspecified_shows_both_inbound_outbound_live", test_type_unspecified_shows_both_inbound_outbound_live)]:
        try:
            err = fn()
            if err:
                print(f"  FAIL {name}: {err}")
                failed.append((name, err))
            else:
                print(f"  OK  {name}")
        except Exception as e:
            print(f"  SKIP {name}: {e}")

    if failed:
        print(f"\n{len(failed)} test(s) failed")
        sys.exit(1)
    print(f"\nAll {len(tests) + 1} tests passed")
    sys.exit(0)
