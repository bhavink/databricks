# Databricks IP Range Extractor

A Python utility to extract and filter Databricks IP ranges for egress allowlisting in firewalls and network appliances.

## How It Works

```mermaid
flowchart LR
    subgraph Input
        URL[Public URL]
        FILE[Local JSON File]
    end
    
    subgraph Processing
        LOAD[Load IP Ranges]
        FILTER[Apply Filters]
        FORMAT[Format Output]
    end
    
    subgraph Output
        JSON[JSON Array]
        CSV[CSV File]
        SIMPLE[CIDR List]
    end
    
    URL --> LOAD
    FILE --> LOAD
    LOAD --> FILTER
    FILTER --> FORMAT
    FORMAT --> JSON
    FORMAT --> CSV
    FORMAT --> SIMPLE
    
    style LOAD fill:#4285F4
    style FILTER fill:#EA4335
    style FORMAT fill:#34A853
```

---

## Filtering Pipeline

The tool applies filters sequentially to narrow down IP ranges:

```mermaid
flowchart TB
    INPUT[("All Prefixes<br/>~1000+ entries")]
    
    CLOUD{--cloud<br/>aws/azure/gcp}
    REGION{--region<br/>us-east-1, etc.}
    IPV{--ipv4-only<br/>--ipv6-only}
    SVC{--service<br/>serverless-egress}
    ACTIVE{--active-only<br/>exclude deprecated}
    
    OUTPUT[("Filtered Results<br/>Ready for firewall")]
    
    INPUT --> CLOUD
    CLOUD -->|Match| REGION
    CLOUD -->|No match| X1[Excluded]
    REGION -->|Match| IPV
    REGION -->|No match| X2[Excluded]
    IPV -->|Match| SVC
    IPV -->|No match| X3[Excluded]
    SVC -->|Match| ACTIVE
    SVC -->|No match| X4[Excluded]
    ACTIVE -->|Match| OUTPUT
    ACTIVE -->|No match| X5[Excluded]
    
    style INPUT fill:#FDD835
    style OUTPUT fill:#34A853
    style CLOUD fill:#4285F4
    style REGION fill:#4285F4
    style IPV fill:#4285F4
    style SVC fill:#4285F4
    style ACTIVE fill:#4285F4
```

---

## Prerequisites

- Python 3.7 or higher
- No external dependencies (uses standard library only)

```bash
# Verify Python version
python --version
```

---

## Quick Start

```bash
# Extract all AWS IPs
python extract-databricks-ips.py --cloud aws

# Extract AWS us-east-1 only
python extract-databricks-ips.py --cloud aws --region us-east-1

# Save to file
python extract-databricks-ips.py --cloud aws --output aws-ips.json
```

---

## Usage

### Basic Commands

```bash
# All clouds, all regions
python extract-databricks-ips.py

# Filter by cloud provider
python extract-databricks-ips.py --cloud aws
python extract-databricks-ips.py --cloud azure
python extract-databricks-ips.py --cloud gcp

# Filter by region
python extract-databricks-ips.py --cloud aws --region us-east-1
python extract-databricks-ips.py --cloud azure --region eastus

# IPv4 only (for firewalls that don't support IPv6)
python extract-databricks-ips.py --cloud aws --ipv4-only
```

### Output Formats

```bash
# JSON (default) - array of objects
python extract-databricks-ips.py --cloud aws --format json

# CSV - header + rows
python extract-databricks-ips.py --cloud aws --format csv

# Simple - one CIDR per line
python extract-databricks-ips.py --cloud aws --format simple
```

### Discovery Commands

```bash
# List available regions
python extract-databricks-ips.py --list-regions

# List regions for specific cloud
python extract-databricks-ips.py --list-regions --cloud aws

# List available services
python extract-databricks-ips.py --list-services
```

### Using the Public JSON Endpoint

```bash
# Fetch directly from Databricks (when URL is available)
python extract-databricks-ips.py --source https://<insert-url-here> --cloud aws
```

---

## Output Schema

### JSON Structure Overview

```mermaid
flowchart TB
    subgraph Source["Source JSON Structure"]
        ROOT["{ }"]
        META["metadata"]
        PREFIXES["prefixes[ ]"]
        
        ROOT --> META
        ROOT --> PREFIXES
        
        ENTRY1["Entry 1"]
        ENTRY2["Entry 2"]
        ENTRYN["Entry N..."]
        
        PREFIXES --> ENTRY1
        PREFIXES --> ENTRY2
        PREFIXES --> ENTRYN
    end
    
    subgraph Entry["Each Prefix Entry"]
        CIDR["cidr: 3.15.8.0/24"]
        IPV["ipVersion: ipv4"]
        CP["cloudProvider: aws"]
        REG["region: us-east-1"]
        SVC["service: serverless-egress"]
        DATES["activeAfter / deprecatedAfter"]
    end
    
    ENTRY1 -.-> CIDR
    ENTRY1 -.-> IPV
    ENTRY1 -.-> CP
    ENTRY1 -.-> REG
    ENTRY1 -.-> SVC
    ENTRY1 -.-> DATES
    
    style ROOT fill:#FDD835
    style PREFIXES fill:#4285F4
    style ENTRY1 fill:#34A853
```

### Output Format Comparison

```mermaid
flowchart LR
    FILTERED[Filtered<br/>Entries]
    
    subgraph Formats["--format options"]
        JSON["json<br/>Array of objects"]
        CSV["csv<br/>Header + rows"]
        SIMPLE["simple<br/>One CIDR per line"]
    end
    
    FILTERED --> JSON
    FILTERED --> CSV
    FILTERED --> SIMPLE
    
    subgraph Examples
        J_OUT["[{cidr, region...}]"]
        C_OUT["cidr,region,...<br/>3.15.8.0/24,us-east-1"]
        S_OUT["3.15.8.0/24<br/>52.27.216.0/23"]
    end
    
    JSON --> J_OUT
    CSV --> C_OUT
    SIMPLE --> S_OUT
    
    style FILTERED fill:#EA4335
    style JSON fill:#4285F4
    style CSV fill:#34A853
    style SIMPLE fill:#FF9800
```

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

### Typical Automation Workflow

```mermaid
flowchart TB
    subgraph Schedule["Scheduled Trigger"]
        CRON["Cron Job<br/>Weekly/Daily"]
    end
    
    subgraph Extract["IP Extraction"]
        FETCH["Fetch from<br/>Databricks URL"]
        FILTER["Filter by<br/>Cloud & Region"]
        SAVE["Save to<br/>Allowlist File"]
    end
    
    subgraph Apply["Firewall Update"]
        RELOAD["Reload<br/>Firewall Rules"]
        VERIFY["Verify<br/>Connectivity"]
    end
    
    CRON --> FETCH
    FETCH --> FILTER
    FILTER --> SAVE
    SAVE --> RELOAD
    RELOAD --> VERIFY
    
    style CRON fill:#FF9800
    style FETCH fill:#4285F4
    style FILTER fill:#4285F4
    style SAVE fill:#34A853
    style RELOAD fill:#EA4335
    style VERIFY fill:#34A853
```

### Weekly Cron Job

```bash
# Add to crontab (runs every Monday at 6 AM)
0 6 * * 1 python /path/to/extract-databricks-ips.py --source https://<insert-url-here> --cloud aws --output /etc/firewall/databricks-ips.json
```

### Simple Bash Script

```bash
#!/bin/bash
# update-databricks-ips.sh

SCRIPT_DIR="/path/to/databricks-utils/extract-databricks-ips"
OUTPUT_DIR="/etc/firewall/allowlists"
SOURCE_URL="https://<insert-url-here>"

# Extract IPs for each cloud
python ${SCRIPT_DIR}/extract-databricks-ips.py \
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
- **JSON Endpoint**: `https://<insert-url-here>`
