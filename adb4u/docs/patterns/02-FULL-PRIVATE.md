***REMOVED*** Full Private (Air-Gapped) Deployment Pattern

**Pattern**: `deployments/full-private`  
**Status**: ✅ **Production Ready**

---

***REMOVED******REMOVED*** Overview

The Full Private (Air-Gapped) pattern provides a **fully isolated** Azure Databricks deployment with:
- **Private Link for Control Plane** (UI/API via Private Endpoints)
- **Private Link for Data Plane** (SCC via Private Endpoints)
- **No Internet Egress** (air-gapped - no NAT Gateway)
- **Private Endpoints for all storage** (DBFS, Unity Catalog)
- **Unity Catalog** for data governance
- **Network Connectivity Configuration (NCC)** for serverless compute
- **Customer-Managed Keys (CMK)** enabled by default

***REMOVED******REMOVED******REMOVED*** Use Cases

✅ **Highly regulated industries** (Financial services, Healthcare)  
✅ **Zero-trust network architectures**  
✅ **Air-gapped requirements** (No internet access)  
✅ **Strict data residency** (All traffic on Azure backbone)  
✅ **Compliance mandates** (HIPAA, PCI-DSS, FedRAMP)

---

***REMOVED******REMOVED*** Architecture

***REMOVED******REMOVED******REMOVED*** **High-Level Design**

```
┌──────────────────────────────────────────────────────────────────┐
│ User Network (On-Premises or VPN)                                │
└────────────┬─────────────────────────────────────────────────────┘
             │
             │ (Private DNS resolution)
             │ (VPN or ExpressRoute)
             ↓
┌──────────────────────────────────────────────────────────────────┐
│ Customer VNet (VNet Injection)                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Private Link Subnet                                         │  │
│  │ ┌────────────────────────┐  ┌──────────────────────────┐  │  │
│  │ │ PE: UI/API Endpoint    │  │ PE: Browser Auth         │  │  │
│  │ │ → Control Plane        │  │ → Control Plane          │  │  │
│  │ └────────────────────────┘  └──────────────────────────┘  │  │
│  │ ┌────────────────────────┐  ┌──────────────────────────┐  │  │
│  │ │ PE: DBFS Storage       │  │ PE: UC Storage           │  │  │
│  │ │ → Customer Storage     │  │ → Customer Storage       │  │  │
│  │ └────────────────────────┘  └──────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────┐  ┌──────────────────────────┐   │
│  │ Public/Host Subnet         │  │ Private/Container Subnet │   │
│  │ (10.178.0.0/26)            │  │ (10.178.1.0/26)          │   │
│  │                            │  │                          │   │
│  │ - Driver Nodes             │  │ - Worker Nodes           │   │
│  │ - No Public IPs (NPIP)     │  │ - No Public IPs (NPIP)   │   │
│  │ - NO NAT Gateway           │  │ - NO NAT Gateway         │   │
│  └────────────────────────────┘  └──────────────────────────┘   │
│          │                                   │                    │
│          └───────────────┬───────────────────┘                    │
│                          │                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Network Security Group (NSG)                                │  │
│  │ - Custom rules (when public access disabled)               │  │
│  │ - Worker-to-worker communication                           │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
    │                                      │
    │ (Private Link - Control Plane)       │ (Private Link - Storage)
    ↓                                      ↓
┌──────────────────────────────────────────────────────────────────┐
│ Databricks Control Plane (Microsoft-Managed)                     │
│  - SCC Relay (backend Private Link)                              │
│  - API Service (frontend Private Link)                           │
│  - Cluster Management                                            │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│ Azure Storage (ADLS Gen2) - Customer Subscription                │
│  - DBFS Root Storage (via Private Endpoint)                      │
│  - UC Metastore Storage (via Private Endpoint)                   │
│  - UC External Location (via Private Endpoint)                   │
└──────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│ Network Connectivity Configuration (NCC) - Optional                │
│ - Enables serverless → customer storage connectivity             │
│ - PE rules require manual approval in Azure Portal                │
│ - Setup: See docs/04-SERVERLESS-SETUP.md                          │
└────────────────────────────────────────────────────────────────────┘
```

**Legend**:
- 🔒 **All traffic**: Private (Azure backbone)
- ❌ **No NAT Gateway**: Air-gapped (no internet)
- 🔐 **Private Endpoints**: All connectivity via Private Link

---

***REMOVED******REMOVED*** Key Differences from Non-PL

| Feature | Non-PL | Full Private |
|---------|--------|--------------|
| **Control Plane Access** | Public internet | Private Link only |
| **User Access** | Any internet connection | VPN/ExpressRoute required |
| **Internet Egress** | ✅ NAT Gateway (PyPI/Maven) | ❌ None (air-gapped) |
| **Storage Connectivity** | Service Endpoints | Private Link |
| **Package Management** | Internet repos | Customer repos required |
| **Deployment Complexity** | Low | High |
| **Security Posture** | Secure | Maximum security |

---

***REMOVED******REMOVED*** Traffic Flow: Cluster Startup Sequence

***REMOVED******REMOVED******REMOVED*** High-Level Flow

```mermaid
sequenceDiagram
    actor User
    participant VPN as VPN/ExpressRoute
    participant PE as Private Endpoint
    participant UI as Databricks UI
    participant CP as Control Plane
    participant Cluster as Cluster VMs<br/>(VNet)
    participant Storage as Azure Storage<br/>(Private Link)

    User->>VPN: 1. Connect via VPN
    VPN->>PE: Private DNS resolution
    PE->>UI: Access workspace
    UI->>CP: 2. Create Cluster
    CP->>Cluster: 3. Provision VMs (NPIP)
    Cluster->>CP: 4. Establish SCC (Private Link)
    Cluster->>Storage: 5. Access Storage (Private Link)
    CP->>User: Cluster RUNNING
```

**Timeline**: ~3-5 minutes from creation to ready state

**Key Points**:
- ✅ All traffic via **Private Link** (no public internet)
- ✅ VMs have **no public IPs** (NPIP enabled)
- ✅ **No NAT Gateway** (air-gapped deployment)
- ❌ **No internet access** for package downloads

---

***REMOVED******REMOVED******REMOVED*** Detailed Phase Breakdown

***REMOVED******REMOVED******REMOVED******REMOVED*** **Phase 1: User Access** (Prerequisites)

```
User → VPN/ExpressRoute → Private Link Subnet → Private Endpoint → Databricks UI

Requirements:
- Network connectivity to customer VNet (VPN/ExpressRoute/Bastion)
- Private DNS resolution configured
- IP in allow-list (if IP Access Lists enabled)
```

**Access Methods**:
1. **VPN Connection**: Site-to-site or Point-to-site VPN
2. **ExpressRoute**: Dedicated private connection
3. **Azure Bastion**: Jump box within VNet

---

***REMOVED******REMOVED******REMOVED******REMOVED*** **Phase 2: Cluster Request** (T+0s)

```
User → Private Endpoint (UI/API) → Databricks Control Plane
├─ POST /api/2.0/clusters/create
├─ Payload: {node_type, count, dbr_version}
└─ Response: Cluster ID (pending state)
```

**Network Path**: Private Link → Databricks SaaS (no public internet)

---

***REMOVED******REMOVED******REMOVED******REMOVED*** **Phase 3: VM Provisioning** (T+0s to T+2min)

```mermaid
sequenceDiagram
    participant CP as Control Plane
    participant ARM as Azure ARM
    participant VNet as Customer VNet
    
    CP->>ARM: Create VMs (no public IPs)
    ARM->>VNet: Provision Driver (Public Subnet)
    ARM->>VNet: Provision Workers (Private Subnet)
    VNet-->>ARM: VMs Created
    ARM-->>CP: Provisioning Complete
```

**Resources Created**:
- Driver VM (public subnet, no public IP)
- Worker VMs (private subnet, no public IP)
- Managed disks (encrypted with CMK)
- NSG rules (custom rules when public access disabled)

---

***REMOVED******REMOVED******REMOVED******REMOVED*** **Phase 4: Control Plane Tunnel** (T+2min to T+3min)

```
Cluster VMs → Private Endpoint (Backend) → Control Plane SCC Relay

Protocol: HTTPS/WebSocket (443)
Direction: Outbound only (VNet initiates)
Purpose: Cluster management, commands, monitoring
Routing: Private Link (NOT via public internet)
```

**Private Link Architecture**:
- **Frontend PE**: UI/API access (user-facing)
- **Backend PE**: SCC Relay (cluster management)
- Both use Azure backbone network (zero public routing)

---

***REMOVED******REMOVED******REMOVED******REMOVED*** **Phase 5: Storage Access** (T+2min onwards)

```mermaid
graph LR
    Cluster[Cluster VMs]
    PE[Private Endpoint]
    
    subgraph Storage["Azure Storage (Customer)"]
        DBFS[DBFS Root]
        UC[UC Metastore]
        ExtLoc[External Location]
    end
    
    Cluster --> PE
    PE --> DBFS
    PE --> UC
    PE --> ExtLoc
    
    style PE fill:***REMOVED***e8f5e9
    style Storage fill:***REMOVED***fff9c4
```

**Access Pattern**:
- DBFS: Init scripts, cluster logs
- UC Metastore: Table metadata, schemas, permissions
- External Location: User data (Delta, Parquet, etc.)

**Authentication**: Managed Identity (Access Connector) via RBAC

---

***REMOVED******REMOVED******REMOVED******REMOVED*** **Phase 6: Package Management** (Air-Gapped)

```
❌ NO internet access for packages

Customer Responsibilities:
1. Host internal PyPI mirror (e.g., JFrog Artifactory, Nexus)
2. Configure pip.conf to point to internal mirror
3. Pre-install libraries via init scripts
4. Use private container registry for custom images
```

**Example Init Script**:
```bash
***REMOVED***!/bin/bash
***REMOVED*** Configure pip to use internal PyPI mirror
cat > /etc/pip.conf << EOF
[global]
index-url = https://pypi.company.internal/simple
trusted-host = pypi.company.internal
EOF

***REMOVED*** Install common libraries from internal mirror
pip install pandas numpy scikit-learn
```

---

***REMOVED******REMOVED******REMOVED*** Network Routing Summary

| Traffic Type | Source | Destination | Path | Authentication |
|--------------|--------|-------------|------|----------------|
| **UI/API Access** | User | Databricks SaaS | VPN → Private Endpoint | AAD/Bearer Token |
| **Control Plane (SCC)** | Cluster VMs | Databricks SaaS | Private Endpoint (Backend) | Databricks-managed |
| **DBFS Access** | Cluster VMs | DBFS (Customer) | Private Endpoint | Managed Identity |
| **UC Metastore** | Cluster VMs | UC Storage (Customer) | Private Endpoint | Managed Identity |
| **External Data** | Cluster VMs | External Location | Private Endpoint | Managed Identity |
| **Worker-to-Worker** | Worker VMs | Worker VMs | Within VNet | N/A |
| **Logs/Metrics** | Cluster VMs | Event Hub | Private Endpoint (optional) | Databricks-managed |
| **Package Downloads** | ❌ | ❌ | **NONE** (air-gapped) | N/A |

**Key Routing**:
- **Zero internet traffic**: All communication via Private Link
- **Private DNS**: Custom DNS zones for Private Endpoints
- **No NAT Gateway**: Air-gapped deployment

---

***REMOVED******REMOVED*** Features

***REMOVED******REMOVED******REMOVED*** Included Features

| Feature | Status | Details |
|---------|--------|---------|
| **Secure Cluster Connectivity (NPIP)** | ✅ Always enabled | No public IPs on clusters |
| **VNet Injection** | ✅ Always enabled | Deploy into customer VNet |
| **Private Link (Control Plane)** | ✅ Always enabled | Frontend (UI/API) + Backend (SCC) |
| **Private Link (Storage)** | ✅ Always enabled | All storage via Private Endpoints |
| **Unity Catalog** | ✅ Mandatory | Data governance and access control |
| **Customer-Managed Keys (CMK)** | ✅ Default enabled | Managed services + Disks + DBFS |
| **BYOV Support** | ✅ Optional | Bring Your Own VNet/Subnets/NSG |
| **IP Access Lists** | ✅ Optional | Restrict workspace access by IP |
| **Private DNS Zones** | ✅ Auto-created | Azure-integrated DNS for Private Endpoints |
| **Service Endpoint Policy (SEP)** | ✅ Optional | Storage egress control for classic compute |
| **NCC (Serverless)** | ✅ Optional | Private Link for serverless compute |

***REMOVED******REMOVED******REMOVED*** Not Included

| Feature | Status | Reason | Alternative |
|---------|--------|--------|-------------|
| **NAT Gateway** | ❌ Not included | Air-gapped design | Use internal package repos |
| **Service Endpoints** | ❌ Not used | Private Link provides stronger isolation | N/A |
| **Public Internet Egress** | ❌ Not allowed | Air-gapped requirement | Internal repos required |

---

***REMOVED******REMOVED*** Deployment

***REMOVED******REMOVED******REMOVED*** Prerequisites

**Required**:
- Azure subscription with appropriate permissions
- Terraform >= 1.5
- Azure CLI or Service Principal for authentication
- Databricks Account ID
- **VPN or ExpressRoute** to customer VNet
- **Private DNS** configured for Private Link
- **Customer Key Vault** with CMK keys (if using CMK)
- **Internal package repositories** (PyPI, Maven, Docker registry)

**Network Requirements**:
- VNet CIDR: `/16` to `/20` recommended
- Public Subnet: `/26` minimum (64 IPs)
- Private Subnet: `/26` minimum (64 IPs)
- Private Link Subnet: `/27` minimum (32 IPs)

***REMOVED******REMOVED******REMOVED*** Quick Deploy

```bash
***REMOVED*** 1. Navigate to deployment folder
cd deployments/full-private

***REMOVED*** 2. Copy and configure variables
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars

***REMOVED*** 3. Initialize Terraform
terraform init

***REMOVED*** 4. Review deployment plan
terraform plan

***REMOVED*** 5. Deploy
terraform apply
```

***REMOVED******REMOVED******REMOVED*** Deployment Time

- **Initial deployment**: 20-30 minutes
- **Subsequent deployments**: 15-20 minutes
- **Private Endpoint approval**: Manual (add 5-10 minutes)

---

***REMOVED******REMOVED*** Post-Deployment Steps

***REMOVED******REMOVED******REMOVED*** **Critical**: Lock Down Public Access

After successful deployment, **disable public network access**:

```hcl
***REMOVED*** terraform.tfvars
enable_public_network_access = false
```

```bash
terraform apply
```

This enforces **Private Link only** access (no public internet).

---

***REMOVED******REMOVED******REMOVED*** Configure Private DNS

Ensure Private DNS zones are linked to your VNet:

```bash
***REMOVED*** List Private DNS zones
az network private-dns zone list --output table

***REMOVED*** Link to VNet (if not auto-linked)
az network private-dns link vnet create \
  --resource-group <rg-name> \
  --zone-name privatelink.azuredatabricks.net \
  --name databricks-dns-link \
  --virtual-network <vnet-id> \
  --registration-enabled false
```

---

***REMOVED******REMOVED******REMOVED*** Setup Internal Package Repositories

**Required for air-gapped deployments**:

1. **PyPI Mirror**: JFrog Artifactory, Sonatype Nexus, or devpi
2. **Maven Mirror**: Artifactory or Nexus Repository Manager
3. **Docker Registry**: Azure Container Registry (ACR) with Private Link

**Configure Init Scripts**:
```bash
***REMOVED*** /dbfs/init-scripts/configure-repos.sh
***REMOVED***!/bin/bash

***REMOVED*** Configure pip
cat > /etc/pip.conf << EOF
[global]
index-url = https://pypi.company.internal/simple
trusted-host = pypi.company.internal
EOF

***REMOVED*** Configure Maven
mkdir -p /home/ubuntu/.m2
cat > /home/ubuntu/.m2/settings.xml << EOF
<settings>
  <mirrors>
    <mirror>
      <id>company-maven</id>
      <url>https://maven.company.internal/repository/maven-central/</url>
      <mirrorOf>central</mirrorOf>
    </mirror>
  </mirrors>
</settings>
EOF
```

---

***REMOVED******REMOVED*** Security

***REMOVED******REMOVED******REMOVED*** Network Security

**Private Link Isolation**:
- ✅ Zero public internet exposure
- ✅ All traffic on Azure backbone
- ✅ Control Plane accessible only via Private Endpoints
- ✅ Storage accessible only via Private Endpoints

**Air-Gapped Architecture**:
- ✅ No NAT Gateway (no internet egress)
- ✅ No public IPs on cluster VMs (NPIP)
- ✅ No Service Endpoints (Private Link only)
- ✅ Custom NSG rules when public access disabled

***REMOVED******REMOVED******REMOVED*** Data Security

**Unity Catalog**:
- ✅ Fine-grained access control (GRANT/REVOKE)
- ✅ Data lineage and audit logging
- ✅ Centralized governance across workspaces

**Storage Security**:
- ✅ Private Link only (no public access)
- ✅ HTTPS-only (TLS 1.2+)
- ✅ Managed identity authentication (no keys)
- ✅ Storage Blob Data Contributor RBAC

**Customer-Managed Keys (CMK)**:
- ✅ Managed services encryption (notebooks, secrets)
- ✅ Managed disks encryption (cluster VMs)
- ✅ DBFS root encryption (workspace storage)
- ✅ Enabled by default in Full Private pattern

---

***REMOVED******REMOVED*** Troubleshooting

See [Full Private Troubleshooting Guide](../../deployments/full-private/docs/06-TROUBLESHOOTING.md) for comprehensive issue resolution.

***REMOVED******REMOVED******REMOVED*** Common Issues

**Issue**: Cannot Access Workspace

**Error**: `Unable to connect to workspace URL`

**Solution**:
1. Verify VPN/ExpressRoute connection to VNet
2. Check Private DNS resolution: `nslookup <workspace-url>`
3. Verify Private Endpoint status in Azure Portal
4. Check IP Access Lists (if enabled)

---

**Issue**: Cluster Cannot Start

**Symptom**: Cluster stuck in `PENDING` state

**Solution**:
1. Verify Private Link connectivity (backend PE)
2. Check NSG rules (especially if custom rules added)
3. Review Azure Activity Log for errors
4. Ensure CMK keys are accessible

---

**Issue**: Cannot Install Libraries

**Error**: `pip install` fails with connection timeout

**Solution**:
This is **expected in air-gapped deployments**. Libraries cannot be downloaded from the internet.

**Workarounds**:
1. Configure internal PyPI mirror (see [Post-Deployment Steps](***REMOVED***setup-internal-package-repositories))
2. Pre-install libraries via init scripts from internal storage
3. Use cluster-scoped libraries from DBFS

---

***REMOVED******REMOVED*** Best Practices

***REMOVED******REMOVED******REMOVED*** Network Planning

- **Private Endpoint Subnet**: `/27` minimum, plan for growth
- **DNS Configuration**: Test Private DNS resolution before deployment
- **VPN/ExpressRoute**: Ensure adequate bandwidth for user traffic
- **Firewall Rules**: Document all allow-list requirements

***REMOVED******REMOVED******REMOVED*** Security Hardening

- **Disable Public Access**: Set `enable_public_network_access = false` after initial deployment
- **IP Access Lists**: Enable even with Private Link for defense-in-depth
- **CMK Rotation**: Configure automatic key rotation in Key Vault
- **Audit Logging**: Enable Azure Monitor and Databricks audit logs

***REMOVED******REMOVED******REMOVED*** Operational Excellence

- **Bastion Host**: Deploy Azure Bastion for emergency access
- **Internal Repos**: Maintain mirrors of PyPI, Maven, Docker registries
- **Runbooks**: Document procedures for common operations
- **Disaster Recovery**: Test Private Link failover scenarios

---

***REMOVED******REMOVED*** References

- **Deployment Documentation**: [deployments/full-private/docs/README.md](../../deployments/full-private/docs/README.md)
- **Architecture Deep Dive**: [deployments/full-private/docs/01-ARCHITECTURE.md](../../deployments/full-private/docs/01-ARCHITECTURE.md)
- **Serverless Setup**: [deployments/full-private/docs/04-SERVERLESS-SETUP.md](../../deployments/full-private/docs/04-SERVERLESS-SETUP.md)
- **Azure Databricks Private Link**: [Microsoft Documentation](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/private-link)
- **Unity Catalog**: [Microsoft Documentation](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/)

---

**Pattern Version**: 1.0  
**Status**: ✅ Production Ready  
**Terraform Version**: >= 1.5
