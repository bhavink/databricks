#!/usr/bin/env python3
"""
Databricks IP Range Extractor

Extract IP ranges from Databricks published IP ranges for egress allowlisting.
Filters by cloud provider and region, outputs JSON suitable for firewall rules.

Usage:
    python extract-databricks-ips.py                           # All clouds, all regions
    python extract-databricks-ips.py --cloud aws               # AWS only, all regions
    python extract-databricks-ips.py --cloud aws --region us-east-1
    python extract-databricks-ips.py --cloud azure --region eastus --ipv4-only
    python extract-databricks-ips.py --list-regions aws        # List available regions

No external dependencies required - uses Python standard library only.
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Public URL for Databricks IP ranges
DEFAULT_URL = "https://<insert-url-here>"

# For local development/testing, use sample file
LOCAL_FILE = Path(__file__).parent / "databricks-ip-ranges-sample.json"


def load_ip_ranges(source=None):
    """Load IP ranges from URL or local file."""

    # Priority: explicit source > URL > local file
    if source and source.startswith(("http://", "https://")):
        try:
            with urllib.request.urlopen(source, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            print(f"Error fetching URL: {e}", file=sys.stderr)
            sys.exit(1)

    # Try local file
    local_path = Path(source) if source else LOCAL_FILE
    if local_path.exists():
        with open(local_path, "r") as f:
            return json.load(f)

    # Try default URL as fallback
    try:
        with urllib.request.urlopen(DEFAULT_URL, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"Error: Cannot load IP ranges from URL or local file", file=sys.stderr)
        print(f"URL error: {e}", file=sys.stderr)
        print(f"Local file not found: {local_path}", file=sys.stderr)
        sys.exit(1)


def extract_ips(data, cloud="all", region="all", ipv4_only=False, ipv6_only=False,
                service=None, active_only=False):
    """Extract and filter IP ranges based on criteria."""

    prefixes = data.get("prefixes", [])
    filtered = []

    for entry in prefixes:
        # Filter by cloud provider
        if cloud != "all" and entry.get("cloudProvider", "").lower() != cloud.lower():
            continue

        # Filter by region
        if region != "all" and entry.get("region", "").lower() != region.lower():
            continue

        # Filter by IP version
        ip_version = entry.get("ipVersion", "ipv4")
        if ipv4_only and ip_version != "ipv4":
            continue
        if ipv6_only and ip_version != "ipv6":
            continue

        # Filter by service
        if service and entry.get("service", "").lower() != service.lower():
            continue

        # Filter by active status
        if active_only:
            now = datetime.now(timezone.utc)
            active_after = entry.get("activeAfter")
            deprecated_after = entry.get("deprecatedAfter")

            if active_after:
                try:
                    active_date = datetime.fromisoformat(active_after.replace("Z", "+00:00"))
                    if now < active_date:
                        continue
                except ValueError:
                    pass

            if deprecated_after:
                try:
                    deprecated_date = datetime.fromisoformat(deprecated_after.replace("Z", "+00:00"))
                    if now > deprecated_date:
                        continue
                except ValueError:
                    pass

        filtered.append(entry)

    return filtered


def format_output(filtered_entries, data, cloud, region, output_format="json"):
    """Format the output for egress appliance consumption."""

    # Build flat records for both JSON and CSV
    flat_records = []
    for entry in filtered_entries:
        flat_records.append({
            "cidr": entry.get("cidr"),
            "ipVersion": entry.get("ipVersion"),
            "cloudProvider": entry.get("cloudProvider"),
            "region": entry.get("region"),
            "service": entry.get("service")
        })

    if output_format == "json":
        return flat_records

    elif output_format == "csv":
        lines = ["cidr,ipVersion,cloudProvider,region,service"]
        for entry in filtered_entries:
            lines.append(f"{entry['cidr']},{entry.get('ipVersion','')},{entry.get('cloudProvider','')},{entry.get('region','')},{entry.get('service','')}")
        return "\n".join(lines)

    elif output_format == "simple":
        # Just CIDRs, one per line (for direct import)
        cidrs = sorted(set(r["cidr"] for r in flat_records))
        return "\n".join(cidrs)

    return filtered_entries


def list_regions(data, cloud="all"):
    """List available regions for a cloud provider."""
    prefixes = data.get("prefixes", [])
    regions = {}

    for entry in prefixes:
        provider = entry.get("cloudProvider", "unknown")
        if cloud != "all" and provider.lower() != cloud.lower():
            continue

        if provider not in regions:
            regions[provider] = set()
        regions[provider].add(entry.get("region", "unknown"))

    return {k: sorted(v) for k, v in sorted(regions.items())}


def list_services(data, cloud="all"):
    """List available services."""
    prefixes = data.get("prefixes", [])
    services = set()

    for entry in prefixes:
        if cloud != "all" and entry.get("cloudProvider", "").lower() != cloud.lower():
            continue
        services.add(entry.get("service", "unknown"))

    return sorted(services)


def main():
    parser = argparse.ArgumentParser(
        description="Extract Databricks IP ranges for egress allowlisting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # All IPs, all clouds
  %(prog)s --cloud aws                        # AWS only
  %(prog)s --cloud aws --region us-east-1     # AWS us-east-1 only
  %(prog)s --cloud azure --ipv4-only          # Azure IPv4 only
  %(prog)s --list-regions                     # Show all available regions
  %(prog)s --list-regions --cloud gcp         # Show GCP regions only
  %(prog)s --format simple                    # One CIDR per line
  %(prog)s --source https://example.com/ips.json  # Custom source URL
        """
    )

    parser.add_argument(
        "--cloud", "-c",
        choices=["aws", "azure", "gcp", "all"],
        default="all",
        help="Cloud provider (default: all)"
    )

    parser.add_argument(
        "--region", "-r",
        default="all",
        help="Region filter (default: all). Use --list-regions to see available regions"
    )

    parser.add_argument(
        "--ipv4-only",
        action="store_true",
        help="Include only IPv4 addresses"
    )

    parser.add_argument(
        "--ipv6-only",
        action="store_true",
        help="Include only IPv6 addresses"
    )

    parser.add_argument(
        "--service", "-s",
        help="Filter by service type (e.g., serverless-egress, control-plane-egress)"
    )

    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Include only currently active IPs (not future or deprecated)"
    )

    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv", "simple"],
        default="json",
        help="Output format: json (array of objects), csv (header + rows), simple (one CIDR per line). Default: json"
    )

    parser.add_argument(
        "--list-regions",
        action="store_true",
        help="List available regions and exit"
    )

    parser.add_argument(
        "--list-services",
        action="store_true",
        help="List available services and exit"
    )

    parser.add_argument(
        "--source",
        help="Source URL or file path (default: tries URL then local file)"
    )

    parser.add_argument(
        "--output", "-o",
        help="Output file (default: stdout)"
    )

    args = parser.parse_args()

    # Validate mutually exclusive options
    if args.ipv4_only and args.ipv6_only:
        parser.error("--ipv4-only and --ipv6-only are mutually exclusive")

    # Load data
    data = load_ip_ranges(args.source)

    # Handle list commands
    if args.list_regions:
        regions = list_regions(data, args.cloud)
        if args.format == "json":
            print(json.dumps(regions, indent=2))
        else:
            for cloud, region_list in regions.items():
                print(f"\n{cloud.upper()}:")
                for r in region_list:
                    print(f"  {r}")
        return

    if args.list_services:
        services = list_services(data, args.cloud)
        if args.format == "json":
            print(json.dumps({"services": services}, indent=2))
        else:
            print("Available services:")
            for s in services:
                print(f"  {s}")
        return

    # Extract and filter
    filtered = extract_ips(
        data,
        cloud=args.cloud,
        region=args.region,
        ipv4_only=args.ipv4_only,
        ipv6_only=args.ipv6_only,
        service=args.service,
        active_only=args.active_only
    )

    # Format output
    output = format_output(filtered, data, args.cloud, args.region, args.format)

    # Output
    if isinstance(output, (dict, list)):
        output_str = json.dumps(output, indent=2)
    else:
        output_str = output

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_str)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(output_str)


if __name__ == "__main__":
    main()
