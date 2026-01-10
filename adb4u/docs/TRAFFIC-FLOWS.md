***REMOVED*** Traffic Flow and Network Sequences

**Purpose**: Detailed traffic flow diagrams for Azure Databricks deployment patterns

---

***REMOVED******REMOVED*** Overview

This document provides comprehensive traffic flow diagrams showing how Databricks clusters communicate within different network architectures. Understanding these flows is essential for:

- **Network Planning**: Sizing NAT Gateways, planning bandwidth
- **Security Design**: Understanding attack surfaces and data flows
- **Troubleshooting**: Diagnosing connectivity issues
- **Cost Optimization**: Identifying egress charges and optimizing paths
- **Compliance**: Documenting data paths for audits

---

***REMOVED******REMOVED*** Table of Contents

1. [Non-Private Link (Non-PL) Pattern](***REMOVED***non-private-link-non-pl-pattern)
2. [Full Private Link Pattern](***REMOVED***full-private-link-pattern) (Coming Soon)
3. [Hub-Spoke Pattern](***REMOVED***hub-spoke-pattern) (Coming Soon)
4. [Common Traffic Patterns](***REMOVED***common-traffic-patterns)
5. [Performance Metrics](***REMOVED***performance-metrics)
6. [Cost Analysis](***REMOVED***cost-analysis)

---

***REMOVED******REMOVED*** Non-Private Link (Non-PL) Pattern

***REMOVED******REMOVED******REMOVED*** Cluster Startup Sequence

```
┌──────────────┐
│ User / API   │
└──────┬───────┘
       │
       │ 1. Create Cluster (HTTPS)
       │    POST /api/2.0/clusters/create
       ↓
┌─────────────────────────────────────────────────────────────────┐
│ Databricks Control Plane (Public - Azure Region)               │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Cluster Manager                                             │ │
│ │ - Validates request                                         │ │
│ │ - Allocates cluster ID                                      │ │
│ │ - Initiates provisioning                                    │ │
│ └─────────────────────────────────────────────────────────────┘ │
└────────┬────────────────────────────────────────────────────────┘
         │
         │ 2. Provision VMs in customer VNet
         │    (Azure Resource Manager API)
         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Customer VNet (VNet Injection)                                  │
│                                                                 │
│ ┌──────────────────────────┐  ┌──────────────────────────┐    │
│ │ Driver Node VM           │  │ Worker Node VMs          │    │
│ │ (Public Subnet)          │  │ (Private Subnet)         │    │
│ │ - No Public IP (NPIP)    │  │ - No Public IP (NPIP)    │    │
│ └──────────┬───────────────┘  └────────┬─────────────────┘    │
│            │                            │                       │
│            │ 3. Establish secure tunnel │                       │
│            │    to Control Plane        │                       │
│            │    (Outbound HTTPS)        │                       │
│            └────────────────────────────┘                       │
│                            │                                    │
│                            │ Via NAT Gateway                    │
│                            ↓                                    │
│                  ┌─────────────────────┐                       │
│                  │ NAT Gateway          │                       │
│                  │ IP: 203.0.113.45     │                       │
│                  └─────────┬────────────┘                       │
└────────────────────────────┼────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         │ 4a. Heartbeat     │ 4b. Download      │ 4c. Access Storage
         │    to Control     │     User Libs     │     DBFS/UC/External
         │    Plane          │     (PyPI/Maven)  │     + DBR Images
         │    (NSG: AzureDB) │     (NAT Gateway) │     (NSG: Storage)
         ↓                   ↓                   ↓
┌──────────────────┐  ┌──────────────┐  ┌────────────────────────┐
│ Databricks       │  │ Internet     │  │ Azure Storage          │
│ Control Plane    │  │ - PyPI       │  │ (via Service Endpoint) │
│ (NSG Service Tag)│  │ - Maven      │  │ (NSG: Storage tag)     │
│ - Receives       │  │ - Custom     │  │                        │
│   heartbeats     │  │   repos      │  │ ┌────────────────────┐ │
│ - Sends commands │  │              │  │ │ DBFS Root Storage  │ │
│ - Monitors state │  │ NAT Gateway  │  │ │ - Init scripts     │ │
│ - NO NAT used!   │  │ ONLY for     │  │ │ - Cluster logs     │ │
└──────────────────┘  │ user libs!   │  │ │ - Libraries        │ │
                      └──────────────┘  │ └────────────────────┘ │
                                        │                        │
                                        │ ┌────────────────────┐ │
                                        │ │ UC Metastore       │ │
         ┌──────────────────────────────┤ │ - Table metadata   │ │
         │ 5. Worker-to-Worker          │ │ - Schemas          │ │
         │    Communication             │ └────────────────────┘ │
         │    (Within VNet)             │                        │
         ↓                              │ ┌────────────────────┐ │
┌──────────────────────────┐            │ │ External Location  │ │
│ Inter-Worker Traffic     │            │ │ - User data        │ │
│ - Shuffle operations     │            │ │ - Delta tables     │ │
│ - Data redistribution    │            │ └────────────────────┘ │
│ - RPC communication      │            │                        │
│ - Stays within VNet      │            │ ┌────────────────────┐ │
│ - No egress charges      │            │ │ DBR Images         │ │
└──────────────────────────┘            │ │ (Databricks-managed│ │
                                        │ │  dbartifactsprod*) │ │
                                        │ └────────────────────┘ │
                                        └────────────────────────┘

Time: T+0s to T+5min (typical cluster startup)

Legend:
────>  : Data/Control plane traffic
═════> : Storage traffic (Service Endpoints)
- - -> : Monitoring/heartbeat traffic
```

***REMOVED******REMOVED******REMOVED*** Traffic Flow Phases

***REMOVED******REMOVED******REMOVED******REMOVED*** Phase 1: Cluster Creation Request (T+0s)

**Flow**: User → Databricks Control Plane

**Details**:
```
Protocol:      HTTPS (TCP/443)
Authentication: Bearer token / Azure AD token
Direction:     User browser/CLI → control.databricks.azure.net
Payload:       Cluster configuration JSON
- Node type: Standard_DS3_v2
- Worker count: 2-8 (autoscaling)
- Libraries: PyPI packages, Maven JARs
- Init scripts: Cloud storage paths
Response:      Cluster ID and state (PENDING)
Latency:       < 100ms
```

**What Happens**:
1. User authenticates with Azure AD or Databricks PAT token
2. Control plane validates cluster configuration
3. Control plane allocates cluster ID (e.g., `0123-456789-abcd`)
4. Request queued for provisioning
5. User receives cluster ID and polling endpoint

---

***REMOVED******REMOVED******REMOVED******REMOVED*** Phase 2: VM Provisioning (T+0s to T+2min)

**Flow**: Control Plane → Azure Resource Manager → Customer VNet

**Details**:
```
API:           Azure Resource Manager
Action:        Create VM resources in customer subscription
Resources Created:
- Driver VM:    1x Standard_DS3_v2 (public subnet)
- Worker VMs:   2-8x Standard_DS3_v2 (private subnet)
- Managed Disks: OS disk + Data disks per VM
- NICs:         No public IPs (NPIP enabled)
- NSG:          Rules auto-applied by Databricks

Placement:
- Availability Set or Availability Zones (region-dependent)
- Same VNet as workspace configuration
- Subnet delegation: Microsoft.Databricks/workspaces

Encryption:
- Managed Disks: Azure Storage Service Encryption (default)
- CMK: If enabled, Disk Encryption Set applied
```

**What Happens**:
1. Control plane calls Azure Resource Manager APIs
2. VMs created in managed resource group
3. NICs attached to customer subnets (no public IPs)
4. Databricks installs OS and runtime on VMs
5. VMs boot and prepare to join cluster

---

***REMOVED******REMOVED******REMOVED******REMOVED*** Phase 3: Secure Tunnel Establishment (T+2min to T+3min)

**Flow**: Driver/Worker VMs → Control Plane (via NSG Service Tag: AzureDatabricks)

**Details**:
```
Protocol:       HTTPS (TCP/443)
Direction:      Outbound only (initiated from VNet)
Source:         Cluster VMs (no public IPs)
Routing:        NSG Service Tag: AzureDatabricks (NOT NAT Gateway)
Destination:    tunnel.{region}.azuredatabricks.net
Purpose:        
- Control plane registration
- Command execution channel
- Monitoring and logging
Connection:     
- Persistent WebSocket over HTTPS
- Heartbeat every 30 seconds
- Automatic reconnection on failure
Security:
- TLS 1.2+ encryption
- Mutual TLS authentication
- Databricks-signed certificates
- NSG allows outbound to AzureDatabricks service tag
```

**What Happens**:
1. Driver VM establishes outbound HTTPS connection
2. NSG allows traffic to AzureDatabricks service tag (no NAT traversal)
3. Control plane authenticates VM (mutual TLS)
4. Secure tunnel established (WebSocket over HTTPS)
5. Worker VMs establish similar connections
6. Control plane can now send commands to cluster

---

***REMOVED******REMOVED******REMOVED******REMOVED*** Phase 4a: Control Plane Communication (Ongoing)

**Flow**: Cluster VMs ↔ Control Plane (via NSG Service Tag: AzureDatabricks)

**Details**:
```
Routing:        NSG Service Tag: AzureDatabricks (NOT NAT Gateway)
Protocol:       HTTPS (TCP/443) over persistent tunnel

Heartbeats:
- Frequency:    Every 30 seconds
- Payload:      VM health, resource usage, state
- Timeout:      3 missed heartbeats = cluster unhealthy

Commands:
- Notebook execution
- Job runs
- Library installations
- Cluster resize operations
- Cluster termination

Metrics:
- CPU, memory, disk usage
- Spark metrics (tasks, stages, executors)
- Custom metrics from applications

Logs:
- Driver logs
- Executor logs
- Spark event logs
- Application logs
```

**Traffic Volume**: ~1-5 Mbps per cluster (low)

**Important**: Control plane communication does NOT go through NAT Gateway!

---

***REMOVED******REMOVED******REMOVED******REMOVED*** Phase 4b: User Library Downloads (T+2min to T+4min)

**Flow**: Cluster VMs → NAT Gateway → Internet

**Important**: This is the PRIMARY and ONLY use case for NAT Gateway!

**Details**:
```
Python Packages (PyPI):
- Source:       pypi.org
- Protocol:     HTTPS
- Examples:     pandas, numpy, scikit-learn, tensorflow
- Size:         Varies (10 MB - 1 GB)
- Installation: pip install -r requirements.txt
- Routing:      NAT Gateway

Maven/Ivy (Java/Scala):
- Source:       Maven Central (repo1.maven.org)
- Protocol:     HTTPS
- Examples:     spark-xml, delta-core, custom JARs
- Size:         Varies (1 MB - 100 MB)
- Installation: spark.jars.packages
- Routing:      NAT Gateway

Custom Repositories:
- Source:       Customer-configured (e.g., Artifactory, Nexus)
- Protocol:     HTTPS
- Authentication: If required
- Whitelisting: NAT Gateway IP (203.0.113.45)
- Routing:      NAT Gateway

Databricks Runtime (DBR) Image:
- Source:       Databricks-managed storage accounts (NOT Docker Hub!)
- Protocol:     HTTPS
- Routing:      NSG Service Tag "Storage" (Azure backbone)
- Size:         ~2-5 GB per cluster
- Frequency:    Once per cluster startup
- Caching:      Cached on local disk
- Cost:         $0 egress (uses Storage service tag)
- Reference:    See Data Exfiltration blog for details

Important Notes:
- DBR images come from Microsoft-managed storage (dbartifactsprod*, dblogprod*)
- DBR download uses Storage service tag, NOT NAT Gateway
- NSG allows outbound to Storage service tag for DBR access
- See: https://learn.microsoft.com/en-us/azure/databricks/security/network/data-exfiltration-protection
```

**Traffic Volume**: 500 MB - 2 GB per cluster startup (user libraries only)

**Cost Consideration**: Data egress charges apply (first 100 GB free/month)

**Critical Distinction**:
- **DBR Image**: Databricks-managed storage → NSG Storage tag → $0 egress ✅
- **User Libraries**: PyPI/Maven/Custom → NAT Gateway → Internet → Egress charges ✅

---

***REMOVED******REMOVED******REMOVED******REMOVED*** Phase 4c: Storage Access (T+3min to T+5min)

**Flow**: Cluster VMs → Service Endpoints → Azure Storage (via NSG Service Tag: Storage)

**Details**:
```
Path:
Cluster VMs → Service Endpoint (NSG: Storage tag) → Azure Storage (Azure backbone)
- Never leaves Azure network
- Optimized routing via NSG service tags
- No public internet traversal
- No NAT Gateway involved

Protocol:       HTTPS (TCP/443)
Authentication: Managed Identity (Access Connector)
- No storage account keys exposed
- OAuth 2.0 token-based
- RBAC: Storage Blob Data Contributor

NSG Configuration:
- Outbound rule allows "Storage" service tag
- Traffic routed via Azure backbone network
- Service Endpoints enabled on subnets

DBFS Root Storage (Databricks-managed):
- Init scripts execution:   Read from dbfs:/init-scripts/
- Library caching:          Write to dbfs:/tmp/
- Cluster logs:             Write to dbfs:/cluster-logs/
- Automatic cleanup:        Logs deleted after 30 days
- Routing:                  Service Endpoint (Storage tag)

Unity Catalog Metastore Storage:
- Table metadata queries:   Read table definitions
- Schema information:       Read database/catalog schemas
- Permissions validation:   Check GRANT/REVOKE rules
- Cached locally:           Metadata cached on driver
- Routing:                  Service Endpoint (Storage tag)

External Location Storage (Customer-owned):
- User data access:         Read/Write Delta tables, Parquet
- ACID transactions:        Delta Lake transaction log
- Time travel:              Access historical versions
- Optimize operations:      Compaction, Z-ordering
- Routing:                  Service Endpoint (Storage tag)
```

**Traffic Volume**: Varies (depends on workload, typically GBs-TBs)

**Cost**: **No egress charges** (Service Endpoints keep traffic on Azure backbone via NSG service tags)

**Key Point**: Storage access uses NSG "Storage" service tag + Service Endpoints, NOT NAT Gateway!

---

***REMOVED******REMOVED******REMOVED******REMOVED*** Phase 5: Worker-to-Worker Communication (During execution)

**Flow**: Worker VMs ↔ Worker VMs (Within VNet)

**Details**:
```
Purpose:
- Shuffle operations:       Exchange data between partitions
- Broadcast variables:      Distribute read-only data
- RPC communication:        Spark executor coordination
- Task result collection:   Gather results to driver

Protocol:       TCP (custom Spark protocol)
Ports:          Dynamic ports (ephemeral range)
NSG Rules:      Automatically allowed (VirtualNetwork tag)
Latency:        < 1ms (within same availability zone)
Bandwidth:      Up to 25 Gbps (VM-dependent)

Security:
- Traffic stays within VNet
- No NAT Gateway traversal
- No public internet exposure
- Encryption in transit (Spark TLS if enabled)

Performance:
- Shuffle data is critical path
- Low latency = faster queries
- High bandwidth = better throughput
- Proximity = reduced network hops
```

**Traffic Volume**: Varies (depends on workload, can be TBs for large shuffles)

**Cost**: **No egress charges** (intra-VNet traffic is free)

---

***REMOVED******REMOVED******REMOVED*** Network Path Summary

| Traffic Type | Source | Destination | Path | Protocol | NSG Service Tag | Cost | Latency |
|--------------|--------|-------------|------|----------|----------------|------|---------|
| **Control Plane** | Cluster VMs | Databricks Control Plane | **AzureDatabricks tag** | HTTPS/443 | AzureDatabricks | **No egress** | ~50ms |
| **Package Downloads** | Cluster VMs | PyPI/Maven/Docker Hub | **NAT Gateway → Internet** | HTTPS/443 | N/A | Egress | Varies |
| **DBFS Access** | Cluster VMs | DBFS Storage | **Storage tag + Service Endpoint** | HTTPS/443 | Storage | **No egress** | ~10ms |
| **Unity Catalog** | Cluster VMs | UC Storage | **Storage tag + Service Endpoint** | HTTPS/443 | Storage | **No egress** | ~10ms |
| **External Data** | Cluster VMs | External Location | **Storage tag + Service Endpoint** | HTTPS/443 | Storage | **No egress** | ~10ms |
| **Event Hub (Logs)** | Cluster VMs | Event Hub | **EventHub tag** | HTTPS/9093 | EventHub | **No egress** | ~10ms |
| **Worker-to-Worker** | Worker VMs | Worker VMs | **Within VNet** | Spark/TCP | VirtualNetwork | **No egress** | < 1ms |
| **Workspace UI** | User Browser | Databricks UI | **Direct** | HTTPS/443 | N/A | N/A | ~50ms |

**Key Insight**: NAT Gateway is ONLY for user-initiated internet downloads. All Azure service communication (Databricks, Storage, Event Hub) uses NSG service tags!

---

***REMOVED******REMOVED*** Common Traffic Patterns

***REMOVED******REMOVED******REMOVED*** Notebook Execution

```
1. User opens notebook → Databricks UI (HTTPS)
2. User runs cell → Control Plane → Cluster (via tunnel)
3. Cluster executes code:
   - Reads data from External Location (Service Endpoint)
   - Performs computation (local + worker-to-worker)
   - Writes results to External Location (Service Endpoint)
4. Results returned → Control Plane → UI
5. Logs written to DBFS (Service Endpoint)
```

***REMOVED******REMOVED******REMOVED*** ETL Job Execution

```
1. Scheduler triggers job → Control Plane API (HTTPS)
2. Control Plane starts cluster (if not running)
3. Job notebook/JAR executed on cluster
4. Data flow:
   - Source: External Location (read via Service Endpoint)
   - Transform: In-memory + shuffle (worker-to-worker)
   - Sink: External Location (write via Service Endpoint)
5. Job completion notification → Control Plane
6. Logs and metrics uploaded to DBFS
```

***REMOVED******REMOVED******REMOVED*** ML Model Training

```
1. Data scientist runs training notebook
2. Cluster reads training data from External Location
3. Libraries downloaded (PyPI via NAT Gateway) - one-time
4. Training data loaded into memory/cache
5. Model training:
   - Distributed: Worker-to-worker communication (high volume)
   - Single-node: Local computation
6. Model artifacts written to External Location
7. MLflow tracking data → DBFS
```

---

***REMOVED******REMOVED*** Performance Metrics

***REMOVED******REMOVED******REMOVED*** Latency Characteristics

| Connection | Typical Latency | Notes |
|------------|----------------|-------|
| User → Workspace UI | 50-100ms | Depends on user location |
| UI → Control Plane | 20-50ms | Within Azure region |
| Cluster → Control Plane | 30-80ms | Via NAT Gateway |
| Cluster → Storage (Service Endpoint) | 5-15ms | Same region, Azure backbone |
| Worker ↔ Worker (same AZ) | < 1ms | Within VNet |
| Worker ↔ Worker (cross AZ) | 1-3ms | Cross availability zone |
| Cluster → Internet (NAT) | 10-50ms | Destination-dependent |

***REMOVED******REMOVED******REMOVED*** Bandwidth Characteristics

| Connection | Typical Bandwidth | Notes |
|------------|------------------|-------|
| NAT Gateway | 45 Gbps | Per NAT Gateway |
| VM Network | 1-25 Gbps | VM size-dependent |
| Storage (per VM) | 500 MB/s - 8 GB/s | VM and disk type dependent |
| Worker-to-Worker | Up to 25 Gbps | VM network interface |

---

***REMOVED******REMOVED*** Cost Analysis

***REMOVED******REMOVED******REMOVED*** Data Egress Charges (Azure)

| Destination | Pricing (first 100 GB) | Pricing (next 10 TB) | Use Case |
|-------------|----------------------|-------------------|----------|
| **Internet** | Free | $0.087/GB | PyPI, Maven, Docker Hub |
| **Same Region Storage** | Free | Free | Service Endpoints |
| **Cross-Region Storage** | Free | $0.02/GB | Not typical |
| **Within VNet** | Free | Free | Worker-to-worker |

**Monthly Egress Estimate (Non-PL Pattern)**:

| Traffic Type | Volume/Month | Routing | Cost/Month |
|--------------|-------------|---------|------------|
| Control Plane (heartbeats, commands) | ~5 GB | **NSG: AzureDatabricks tag** | **$0 (Azure backbone)** |
| DBR image downloads | ~50 GB | **NSG: Storage tag** | **$0 (Azure backbone)** |
| User library downloads (PyPI/Maven) | ~10 GB | **NAT Gateway → Internet** | $0 (< 100 GB free) |
| Storage access (DBFS/UC/External) | 1000+ GB | **NSG: Storage tag** | **$0 (Azure backbone)** |
| Event Hub (logs) | ~10 GB | **NSG: EventHub tag** | **$0 (Azure backbone)** |
| Worker-to-worker | 1000+ GB | **Within VNet** | **$0 (intra-VNet)** |
| **TOTAL INTERNET EGRESS** | **~10 GB** | | **$0** (< 100 GB free) |

**Key Takeaway**: 
- **NSG Service Tags** (AzureDatabricks, Storage, EventHub) = $0 egress for ALL Azure services!
- **DBR images** come from Databricks-managed storage via **Storage service tag** = $0 egress!
- **NAT Gateway** only for user libraries (PyPI/Maven) = ~10 GB/month (< 100 GB free tier)
- **Result**: Typical deployment has **$0 egress costs**!

---

***REMOVED******REMOVED*** Security Analysis

***REMOVED******REMOVED******REMOVED*** Attack Surface

| Entry Point | Risk | Mitigation |
|-------------|------|------------|
| **Workspace UI** | Public endpoint | IP Access Lists, Azure AD authentication, MFA |
| **REST API** | Public endpoint | Token authentication, Azure AD, IP restrictions |
| **Cluster VMs** | No public IPs (NPIP) | Not directly accessible from internet |
| **Storage** | Public endpoint | Service Endpoints, RBAC, Azure AD |
| **NAT Gateway** | Outbound only | Stateful firewall, no inbound connections |

***REMOVED******REMOVED******REMOVED*** Data Flow Security

| Flow | Encryption | Authentication | Authorization |
|------|-----------|----------------|---------------|
| User → UI | TLS 1.2+ | Azure AD / PAT | RBAC |
| Cluster → Control Plane | TLS 1.2+, Mutual TLS | Certificate-based | N/A |
| Cluster → Storage | TLS 1.2+ | Managed Identity | RBAC (Storage Blob Data Contributor) |
| Cluster → Internet | TLS 1.2+ | Varies | N/A |
| Worker ↔ Worker | Optional TLS | None (trusted VNet) | N/A |

---

***REMOVED******REMOVED*** Troubleshooting Guide

***REMOVED******REMOVED******REMOVED*** Cannot Reach Control Plane

**Symptom**: Cluster stuck in "Pending" or "Resizing"

**Diagnosis**:
```bash
***REMOVED*** From a test VM in same VNet
curl -v https://tunnel.{region}.azuredatabricks.net
nslookup tunnel.{region}.azuredatabricks.net
traceroute tunnel.{region}.azuredatabricks.net
```

**Common Causes**:
- NAT Gateway not attached to subnets
- NSG blocking outbound HTTPS (443)
- Route table misconfiguration

***REMOVED******REMOVED******REMOVED*** Cannot Download Packages

**Symptom**: `pip install` fails, "Connection timeout"

**Diagnosis**:
```python
***REMOVED*** From Databricks notebook
%sh curl -v https://pypi.org/simple/
%sh ping -c 4 8.8.8.8
```

**Common Causes**:
- NAT Gateway not configured
- No route to internet
- Firewall blocking outbound traffic

***REMOVED******REMOVED******REMOVED*** Cannot Access Storage

**Symptom**: "403 Forbidden" or "Connection timeout" accessing ADLS

**Diagnosis**:
```python
***REMOVED*** From Databricks notebook
dbutils.fs.ls("abfss://...")
```

**Common Causes**:
- Service Endpoints not enabled on subnet
- RBAC not configured (Access Connector)
- Storage firewall blocking VNet
- Incorrect storage account name/path

---

***REMOVED******REMOVED*** References

- [Azure Databricks Network Architecture](https://learn.microsoft.com/en-us/azure/databricks/security/network/)
- [Secure Cluster Connectivity (NPIP)](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/secure-cluster-connectivity)
- [VNet Injection](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject)
- [Service Endpoints](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/service-endpoints)
- [Azure Bandwidth Pricing](https://azure.microsoft.com/en-us/pricing/details/bandwidth/)

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-10  
**Pattern Coverage**: Non-PL (complete), Private Link (coming soon), Hub-Spoke (coming soon)
