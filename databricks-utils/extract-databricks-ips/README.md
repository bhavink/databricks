# Databricks IP Range Extractor

## Quick Start

```bash
# Extract all AWS IPs
python3 extract-databricks-ips.py --cloud aws

# Extract AWS us-east-1 only
python3 extract-databricks-ips.py --cloud aws --region us-east-1

# Save to file
python3 extract-databricks-ips.py --cloud aws --output aws-ips.json
```

**No dependencies required** - uses Python standard library only.

---

## Usage

### Basic Commands

```bash
# All clouds, all regions
python3 extract-databricks-ips.py

# Filter by cloud provider
python3 extract-databricks-ips.py --cloud aws
python3 extract-databricks-ips.py --cloud azure
python3 extract-databricks-ips.py --cloud gcp

# Filter by region
python3 extract-databricks-ips.py --cloud aws --region us-east-1
python3 extract-databricks-ips.py --cloud azure --region eastus

# IPv4 only (for firewalls that don't support IPv6)
python3 extract-databricks-ips.py --cloud aws --ipv4-only
```

### Output Formats

```bash
# JSON (default) - array of objects
python3 extract-databricks-ips.py --cloud aws --format json

# CSV - header + rows
python3 extract-databricks-ips.py --cloud aws --format csv

# Simple - one CIDR per line
python3 extract-databricks-ips.py --cloud aws --format simple
```

### Discovery Commands

```bash
# List available regions
python3 extract-databricks-ips.py --list-regions

# List regions for specific cloud
python3 extract-databricks-ips.py --list-regions --cloud aws

# List available services
python3 extract-databricks-ips.py --list-services
```

### Using the Public JSON Endpoint

```bash
# Fetch directly from Databricks (when URL is available)
python3 extract-databricks-ips.py --source https://<insert-url-here>/databricks-ip-ranges.json --cloud aws
```

---

## Output Schema

Both JSON and CSV use the same flat structure:

**JSON:**
```json
[
  {
    "cidr": "3.15.8.0/24",
    "ipVersion": "ipv4",
    "cloudProvider": "aws",
    "region": "us-east-1",
    "service": "serverless-egress"
  }
]
```

**CSV:**
```
cidr,ipVersion,cloudProvider,region,service
3.15.8.0/24,ipv4,aws,us-east-1,serverless-egress
```

| Field | Description |
|-------|-------------|
| `cidr` | IP range in CIDR notation |
| `ipVersion` | `ipv4` or `ipv6` |
| `cloudProvider` | `aws`, `azure`, or `gcp` |
| `region` | Cloud-specific region identifier |
| `service` | Service type (e.g., `serverless-egress`, `control-plane-egress`) |

---

## Automation Example

### Weekly Cron Job

```bash
# Add to crontab (runs every Monday at 6 AM)
0 6 * * 1 /usr/bin/python3 /path/to/extract-databricks-ips.py --source https://<insert-url-here>/databricks-ip-ranges.json --cloud aws --output /etc/firewall/databricks-ips.json
```

### Simple Bash Script

```bash
#!/bin/bash
# update-databricks-ips.sh

SCRIPT_DIR="/path/to/databricks-utils/update-ips"
OUTPUT_DIR="/etc/firewall/allowlists"
SOURCE_URL="https://<insert-url-here>/databricks-ip-ranges.json"

# Extract IPs for each cloud
python3 ${SCRIPT_DIR}/extract-databricks-ips.py \
  --source ${SOURCE_URL} \
  --cloud aws \
  --format simple \
  --output ${OUTPUT_DIR}/databricks-aws.txt

# Reload firewall rules (example for iptables)
# /usr/local/bin/reload-firewall.sh
```

---

## All Options

```
--cloud, -c        Cloud provider: aws, azure, gcp, all (default: all)
--region, -r       Region filter (default: all)
--ipv4-only        Include only IPv4 addresses
--ipv6-only        Include only IPv6 addresses
--service, -s      Filter by service type
--active-only      Exclude future/deprecated IPs
--format, -f       Output format (default: json)
                     json   - array of objects
                     csv    - header + rows
                     simple - one CIDR per line
--list-regions     List available regions and exit
--list-services    List available services and exit
--source           Source URL or local file path
--output, -o       Output file (default: stdout)
```

---

## Support

- **Documentation**: [Databricks Network Connectivity](https://docs.databricks.com)
- **JSON Endpoint**: `https://<insert-url-here>/databricks-ip-ranges.json`
