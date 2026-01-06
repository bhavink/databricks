***REMOVED*** Databricks IP Range Extractor

***REMOVED******REMOVED*** Prerequisites

- Python 3.7 or higher
- No external dependencies (uses standard library only)

```bash
***REMOVED*** Verify Python version
python --version
```

---

***REMOVED******REMOVED*** Quick Start

```bash
***REMOVED*** Extract all AWS IPs
python extract-databricks-ips.py --cloud aws

***REMOVED*** Extract AWS us-east-1 only
python extract-databricks-ips.py --cloud aws --region us-east-1

***REMOVED*** Save to file
python extract-databricks-ips.py --cloud aws --output aws-ips.json
```

---

***REMOVED******REMOVED*** Usage

***REMOVED******REMOVED******REMOVED*** Basic Commands

```bash
***REMOVED*** All clouds, all regions
python extract-databricks-ips.py

***REMOVED*** Filter by cloud provider
python extract-databricks-ips.py --cloud aws
python extract-databricks-ips.py --cloud azure
python extract-databricks-ips.py --cloud gcp

***REMOVED*** Filter by region
python extract-databricks-ips.py --cloud aws --region us-east-1
python extract-databricks-ips.py --cloud azure --region eastus

***REMOVED*** IPv4 only (for firewalls that don't support IPv6)
python extract-databricks-ips.py --cloud aws --ipv4-only
```

***REMOVED******REMOVED******REMOVED*** Output Formats

```bash
***REMOVED*** JSON (default) - array of objects
python extract-databricks-ips.py --cloud aws --format json

***REMOVED*** CSV - header + rows
python extract-databricks-ips.py --cloud aws --format csv

***REMOVED*** Simple - one CIDR per line
python extract-databricks-ips.py --cloud aws --format simple
```

***REMOVED******REMOVED******REMOVED*** Discovery Commands

```bash
***REMOVED*** List available regions
python extract-databricks-ips.py --list-regions

***REMOVED*** List regions for specific cloud
python extract-databricks-ips.py --list-regions --cloud aws

***REMOVED*** List available services
python extract-databricks-ips.py --list-services
```

***REMOVED******REMOVED******REMOVED*** Using the Public JSON Endpoint

```bash
***REMOVED*** Fetch directly from Databricks (when URL is available)
python extract-databricks-ips.py --source https://<insert-url-here>/databricks-ip-ranges.json --cloud aws
```

---

***REMOVED******REMOVED*** Output Schema

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

***REMOVED******REMOVED*** Automation Example

***REMOVED******REMOVED******REMOVED*** Weekly Cron Job

```bash
***REMOVED*** Add to crontab (runs every Monday at 6 AM)
0 6 * * 1 python /path/to/extract-databricks-ips.py --source https://<insert-url-here>/databricks-ip-ranges.json --cloud aws --output /etc/firewall/databricks-ips.json
```

***REMOVED******REMOVED******REMOVED*** Simple Bash Script

```bash
***REMOVED***!/bin/bash
***REMOVED*** update-databricks-ips.sh

SCRIPT_DIR="/path/to/databricks-utils/extract-databricks-ips"
OUTPUT_DIR="/etc/firewall/allowlists"
SOURCE_URL="https://<insert-url-here>/databricks-ip-ranges.json"

***REMOVED*** Extract IPs for each cloud
python ${SCRIPT_DIR}/extract-databricks-ips.py \
  --source ${SOURCE_URL} \
  --cloud aws \
  --format simple \
  --output ${OUTPUT_DIR}/databricks-aws.txt

***REMOVED*** Reload firewall rules (example for iptables)
***REMOVED*** /usr/local/bin/reload-firewall.sh
```

---

***REMOVED******REMOVED*** All Options

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

***REMOVED******REMOVED*** Support

- **Documentation**: [Databricks Network Connectivity](https://docs.databricks.com)
- **JSON Endpoint**: `https://<insert-url-here>/databricks-ip-ranges.json`
