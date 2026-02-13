#!/usr/bin/env python3
"""
Databricks IP Range Extractor

Extract IP ranges from Databricks published IP ranges for egress allowlisting.
Filters by cloud provider and region, outputs JSON suitable for firewall rules.

Usage:
    python extract-databricks-ips.py --cloud aws
        # Per cloud: CSV (default) with cloud, region, type, cidr, ipVersion, service
    python extract-databricks-ips.py --cloud aws --region us-east-1,us-west-2,eu-west-1
        # Multiple regions (comma-separated); output includes both inbound and outbound
    python extract-databricks-ips.py --cloud aws --region us-east-1 --type outbound
        # Single region, outbound only (egress allowlisting)
    python extract-databricks-ips.py --list-regions --cloud aws

Default output: CSV. Omit --type to include both inbound and outbound.
Input: --source or --file with URL or local JSON path.
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Official Databricks IP ranges (AWS, Azure, GCP – inbound/outbound)
# https://docs.databricks.com/security/network/ip-ranges.html
DEFAULT_URL = "https://www.databricks.com/networking/v1/ip-ranges.json"


def _normalize_prefixes(data):
    """
    Normalize API response to a flat list of prefix entries.
    Official API uses: platform, region, service, type, ipv4Prefixes[], ipv6Prefixes[].
    Sample/legacy uses: cidr, ipVersion, cloudProvider, region, service.
    Output: list of {cidr, ipVersion, cloudProvider, region, service, type (optional)}.
    """
    prefixes = data.get("prefixes", [])
    if not prefixes:
        return []

    first = prefixes[0]
    # Official API format: has ipv4Prefixes or ipv6Prefixes arrays
    if "ipv4Prefixes" in first or "ipv6Prefixes" in first:
        out = []
        for entry in prefixes:
            platform = entry.get("platform", "").lower()
            region = entry.get("region", "")
            service = entry.get("service", "")
            typ = entry.get("type", "")
            for cidr in entry.get("ipv4Prefixes") or []:
                out.append({
                    "cidr": cidr,
                    "ipVersion": "ipv4",
                    "cloudProvider": platform,
                    "region": region,
                    "service": service,
                    "type": typ,
                })
            for cidr in entry.get("ipv6Prefixes") or []:
                out.append({
                    "cidr": cidr,
                    "ipVersion": "ipv6",
                    "cloudProvider": platform,
                    "region": region,
                    "service": service,
                    "type": typ,
                })
        return out

    # Legacy/sample format: already has cidr, cloudProvider, etc.
    return list(prefixes)


def load_ip_ranges(source=None):
    """Load IP ranges from URL or local file. Normalizes official API format to flat prefix list."""

    data = None

    # Explicit source: URL or local path
    if source:
        if source.startswith(("http://", "https://")):
            try:
                with urllib.request.urlopen(source, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
            except urllib.error.URLError as e:
                print(f"Error fetching URL: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            local_path = Path(source)
            if local_path.exists():
                with open(local_path, "r") as f:
                    data = json.load(f)
            else:
                print(f"Error: File not found: {local_path}", file=sys.stderr)
                sys.exit(1)

    # No source: fetch from official URL only
    if data is None:
        try:
            with urllib.request.urlopen(DEFAULT_URL, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            print("Error: Cannot load IP ranges from URL.", file=sys.stderr)
            print(f"URL: {DEFAULT_URL}", file=sys.stderr)
            print(f"Error: {e}", file=sys.stderr)
            print("Use --file /path/to/ip-ranges.json for a local or cached file.", file=sys.stderr)
            sys.exit(1)

    # Normalize prefixes to flat list (official API uses ipv4Prefixes/ipv6Prefixes per entry)
    data["prefixes"] = _normalize_prefixes(data)
    return data


def _parse_regions(region_arg):
    """Parse --region into 'all' or a list of region names (comma-separated)."""
    if not region_arg or region_arg.strip().lower() == "all":
        return "all"
    parts = [p.strip() for p in region_arg.split(",") if p.strip()]
    return parts if parts else "all"


def extract_ips(data, cloud="all", region="all", ipv4_only=False, ipv6_only=False,
                service=None, active_only=False, type_filter="all"):
    """Extract and filter IP ranges based on criteria.
    region: 'all' or a list of region names (e.g. ['us-east-1', 'eu-west-1']).
    """
    prefixes = data.get("prefixes", [])
    filtered = []
    regions_set = None
    if isinstance(region, list) and len(region) > 0:
        regions_set = {r.lower() for r in region}

    for entry in prefixes:
        # Filter by cloud provider (API uses "platform", normalized to "cloudProvider")
        if cloud != "all" and entry.get("cloudProvider", "").lower() != cloud.lower():
            continue

        # Filter by region (single or multiple)
        if regions_set is not None:
            if entry.get("region", "").lower() not in regions_set:
                continue
        elif region != "all" and not isinstance(region, list):
            if entry.get("region", "").lower() != region.lower():
                continue

        # Filter by type (inbound/outbound) – for egress allowlisting use "outbound"
        # Legacy/sample data may have no "type"; then we include the entry
        if type_filter != "all" and entry.get("type") and entry.get("type", "").lower() != type_filter.lower():
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

    # Build flat records for both JSON and CSV (include type when present, e.g. from official API)
    flat_records = []
    for entry in filtered_entries:
        rec = {
            "cidr": entry.get("cidr"),
            "ipVersion": entry.get("ipVersion"),
            "cloudProvider": entry.get("cloudProvider"),
            "region": entry.get("region"),
            "service": entry.get("service"),
        }
        if entry.get("type"):
            rec["type"] = entry.get("type")
        flat_records.append(rec)

    if output_format == "json":
        return flat_records

    elif output_format == "csv":
        # Standard columns: cloud, region, type (inbound/outbound), cidr, ipVersion, service
        # Type column always present; empty when data has no type (legacy).
        def csv_escape(s):
            s = str(s) if s is not None else ""
            if "," in s or '"' in s or "\n" in s:
                return '"' + s.replace('"', '""') + '"'
            return s

        header = "cloud,region,type,cidr,ipVersion,service"
        lines = [header]
        for entry in filtered_entries:
            row = ",".join([
                csv_escape(entry.get("cloudProvider", "")),
                csv_escape(entry.get("region", "")),
                csv_escape(entry.get("type", "")),
                csv_escape(entry.get("cidr", "")),
                csv_escape(entry.get("ipVersion", "")),
                csv_escape(entry.get("service", "")),
            ])
            lines.append(row)
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
  %(prog)s --file https://www.databricks.com/networking/v1/ip-ranges.json
  %(prog)s --file ./downloaded-ip-ranges.json     # Local file
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
        metavar="REGION[,REGION,...]",
        help="Region(s): one name, or comma-separated (e.g. us-east-1,us-east-2,eu-west-1). Default: all"
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
        help="Filter by service type (e.g., Databricks, serverless-egress)"
    )

    parser.add_argument(
        "--type", "-t",
        choices=["inbound", "outbound", "all"],
        default="all",
        dest="type_filter",
        help="Filter by direction: outbound for egress allowlisting (default: all)"
    )

    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Include only currently active IPs (not future or deprecated)"
    )

    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv", "simple"],
        default="csv",
        help="Output format: csv (cloud,region,type,cidr,...), json, or simple. Default: csv"
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
        dest="source",
        metavar="URL_OR_PATH",
        help="URL (https://...) or path to local JSON file. Same as --file."
    )
    parser.add_argument(
        "--file",
        dest="source",
        metavar="URL_OR_PATH",
        help="URL or path to local IP ranges JSON (online or downloaded file)"
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

    # Parse region: "all" or list of regions (comma-separated)
    regions_parsed = _parse_regions(args.region)

    # Extract and filter
    filtered = extract_ips(
        data,
        cloud=args.cloud,
        region=regions_parsed,
        ipv4_only=args.ipv4_only,
        ipv6_only=args.ipv6_only,
        service=args.service,
        active_only=args.active_only,
        type_filter=args.type_filter,
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
