***REMOVED*** 01 - Architecture & Deployment Flow

> **Visual Guide**: Understand the Full Private deployment architecture through modular diagrams.

***REMOVED******REMOVED*** Quick Reference

```
📦 6 Terraform Modules → ~35-40 Azure/Databricks Resources
⏱️  15-20 minutes deployment time
🔒 Private Link + NPIP + Unity Catalog + NCC
💰 ~$120-150/month (without compute)
```

---

***REMOVED******REMOVED*** Table of Contents

1. [High-Level Architecture](***REMOVED***1-high-level-architecture)
2. [Module Dependency Flow](***REMOVED***2-module-dependency-flow)
3. [Network Layout](***REMOVED***3-network-layout)
4. [Private Endpoint Architecture](***REMOVED***4-private-endpoint-architecture)
5. [Deployment Sequence](***REMOVED***5-deployment-sequence)
6. [Resource Breakdown](***REMOVED***6-resource-breakdown)

---

***REMOVED******REMOVED*** 1. High-Level Architecture

***REMOVED******REMOVED******REMOVED*** 1.1 Complete System Overview

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
graph TB
    subgraph "Customer Azure Subscription"
        subgraph "VNet 10.178.0.0/20"
            subgraph "Public Subnet /26"
                PUB["Driver Nodes<br/>NO Public IPs<br/>(NPIP)"]
            end
            
            subgraph "Private Subnet /26"
                PRIV["Worker Nodes<br/>NO Public IPs<br/>(NPIP)"]
            end
            
            subgraph "Private Link Subnet /27"
                PE["Private Endpoints<br/>• Databricks 2<br/>• Storage 8"]
            end
        end
        
        subgraph "Storage Layer"
            DBFS["DBFS Storage<br/>Managed by<br/>Databricks"]
            UC_META["UC Metastore<br/>Metadata"]
            UC_EXT["UC External<br/>User Data"]
        end
        
        subgraph "NCC Layer"
            NCC["Network Connectivity<br/>Configuration<br/>Serverless Ready"]
        end
    end
    
    subgraph "Databricks Control Plane"
        DPCP["Databricks SaaS<br/>accounts.azuredatabricks.net<br/>Workspace Management"]
    end
    
    PUB -->|Private Link| PE
    PRIV -->|Private Link| PE
    PE -.->|Private Link<br/>Backend| DPCP
    PE -->|Private DNS| DBFS
    PE -->|Private DNS| UC_META
    PE -->|Private DNS| UC_EXT
    NCC -.->|For Serverless<br/>Manual Setup| DPCP
    
    style DPCP fill:***REMOVED***FF3621,color:***REMOVED***fff
    style PE fill:***REMOVED***FF9900,color:***REMOVED***000
    style NCC fill:***REMOVED***1B72E8,color:***REMOVED***fff
```

**Key Characteristics**:
- ✅ **Control Plane**: Private Link (no public internet)
- ✅ **Data Plane**: NPIP (no public IPs on VMs)
- ✅ **Storage**: Private Endpoints (classic) + NCC (serverless)
- ❌ **NAT Gateway**: Not used (air-gapped)
- ❌ **Internet Egress**: None (requires custom repos)

---

***REMOVED******REMOVED*** 2. Module Dependency Flow

***REMOVED******REMOVED******REMOVED*** 2.1 Terraform Execution Order

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
flowchart TD
    START["terraform apply"] --> RG["1. Resource Group<br/>Tags Applied"]
    RG --> NET["2. Networking Module<br/>VNet + 3 Subnets<br/>NSG Conditionally"]
    NET --> WS["3. Workspace Module<br/>Private Link Enabled<br/>CMK Optional"]
    WS --> PE["4. Private Endpoints Module<br/>Databricks 2<br/>Storage 8<br/>DNS Zones 3"]
    PE --> UC["5. Unity Catalog Module<br/>Metastore<br/>Storage Accounts<br/>Access Connector"]
    UC --> NCC["6. NCC Module Optional<br/>Config + Binding<br/>No PE Rules"]
    NCC --> END["Deployment Complete<br/>Classic Ready"]
    
    style START fill:***REMOVED***569A31,color:***REMOVED***fff
    style END fill:***REMOVED***1B72E8,color:***REMOVED***fff
    style NCC fill:***REMOVED***FF9900,color:***REMOVED***000
    style PE fill:***REMOVED***FF3621,color:***REMOVED***fff
```

**Critical Dependencies**:
- Workspace depends on Networking (VNet + subnets)
- Private Endpoints depend on Workspace (gets workspace ID)
- Unity Catalog depends on Workspace (gets numeric ID)
- NCC depends on Workspace (binds to workspace ID)

**Parallel Creation**:
- Private Endpoints and Unity Catalog can create in parallel (both depend only on Workspace)

---

***REMOVED******REMOVED*** 3. Network Layout

***REMOVED******REMOVED******REMOVED*** 3.1 VNet & Subnet Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
graph TB
    subgraph "VNet 10.178.0.0/20 - 4096 IPs"
        subgraph "Public Subnet"
            PUB["10.178.0.0/26<br/>62 usable IPs<br/>Driver Nodes<br/>NPIP Enabled<br/>Delegation: Databricks"]
        end
        
        subgraph "Private Subnet"
            PRIV["10.178.1.0/26<br/>62 usable IPs<br/>Worker Nodes<br/>NPIP Enabled<br/>Delegation: Databricks"]
        end
        
        subgraph "Private Link Subnet"
            PL["10.178.2.0/27<br/>30 usable IPs<br/>Private Endpoints Only<br/>NO Delegation<br/>NO NAT"]
        end
        
        NSG["Network Security Group<br/>Databricks-Managed Rules<br/>Conditional for PL"]
    end
    
    PUB -.->|Associated| NSG
    PRIV -.->|Associated| NSG
    
    style PL fill:***REMOVED***FF9900,color:***REMOVED***000
```

**Subnet Design**:

| Subnet | CIDR | IPs | Purpose | NAT | Delegation |
|--------|------|-----|---------|-----|------------|
| **Public** | /26 | 62 | Driver nodes | ❌ | ✅ Databricks |
| **Private** | /26 | 62 | Worker nodes | ❌ | ✅ Databricks |
| **Private Link** | /27 | 30 | PE only | ❌ | ❌ None |

**NSG Rules**:
- **Non-PL Mode**: Databricks auto-creates rules (no custom rules)
- **Full Private Mode**: Custom rules created when `enable_public_network_access = false`

---

***REMOVED******REMOVED*** 4. Private Endpoint Architecture

***REMOVED******REMOVED******REMOVED*** 4.1 Private Endpoint Topology

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
graph TB
    subgraph "Private Link Subnet"
        subgraph "Databricks Control Plane PE"
            PE_DPCP["PE: UI/API<br/>databricks_ui_api<br/>Port: 443"]
            PE_AUTH["PE: Browser Auth<br/>browser_authentication<br/>SSO/Login"]
        end
        
        subgraph "Storage PE - Auto-Approved"
            PE_DBFS_DFS["PE: DBFS DFS<br/>subresource: dfs"]
            PE_DBFS_BLOB["PE: DBFS Blob<br/>subresource: blob"]
            PE_META_DFS["PE: UC Metastore DFS<br/>subresource: dfs"]
            PE_META_BLOB["PE: UC Metastore Blob<br/>subresource: blob"]
            PE_EXT_DFS["PE: UC External DFS<br/>subresource: dfs"]
            PE_EXT_BLOB["PE: UC External Blob<br/>subresource: blob"]
        end
    end
    
    subgraph "Private DNS Zones"
        DNS_DB["privatelink.azuredatabricks.net"]
        DNS_DFS["privatelink.dfs.core.windows.net"]
        DNS_BLOB["privatelink.blob.core.windows.net"]
    end
    
    PE_DPCP -->|Resolves| DNS_DB
    PE_AUTH -->|Resolves| DNS_DB
    PE_DBFS_DFS -->|Resolves| DNS_DFS
    PE_META_DFS -->|Resolves| DNS_DFS
    PE_EXT_DFS -->|Resolves| DNS_DFS
    PE_DBFS_BLOB -->|Resolves| DNS_BLOB
    PE_META_BLOB -->|Resolves| DNS_BLOB
    PE_EXT_BLOB -->|Resolves| DNS_BLOB
    
    style PE_DPCP fill:***REMOVED***FF3621,color:***REMOVED***fff
    style PE_AUTH fill:***REMOVED***FF3621,color:***REMOVED***fff
```

**Total Private Endpoints**: 10
- **Databricks**: 2 (control plane access)
- **Storage**: 8 (classic cluster access)

**Approval Status**:
- ✅ Auto-approved (same Azure tenant)
- ❌ No manual approval required

**For Serverless** (Not Created by Terraform):
- Customer manually enables in Databricks UI
- Databricks creates additional PE from its Control Plane
- Customer approves in Azure Portal
- See: [04-SERVERLESS-SETUP.md](04-SERVERLESS-SETUP.md)

---

***REMOVED******REMOVED*** 5. Deployment Sequence

***REMOVED******REMOVED******REMOVED*** 5.1 Resource Creation Timeline

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
sequenceDiagram
    participant TF as Terraform
    participant AZ as Azure
    participant DB as Databricks

    Note over TF,DB: Phase 1: Infrastructure (0-5 min)
    TF->>AZ: Create Resource Group
    TF->>AZ: Create VNet + 3 Subnets
    TF->>AZ: Create NSG
    
    Note over TF,DB: Phase 2: Workspace (5-10 min)
    TF->>DB: Create Workspace (Private Link)
    DB->>AZ: Provision Managed Resources
    DB-->>TF: Workspace ID + URL
    
    Note over TF,DB: Phase 3: Private Endpoints (10-12 min)
    TF->>AZ: Create 3 Private DNS Zones
    TF->>AZ: Create 10 Private Endpoints
    AZ-->>TF: PE Auto-Approved (same tenant)
    
    Note over TF,DB: Phase 4: Unity Catalog (12-17 min)
    TF->>AZ: Create UC Storage Accounts
    TF->>AZ: Create Access Connector
    TF->>DB: Create Metastore
    TF->>DB: Create External Location
    
    Note over TF,DB: Phase 5: NCC (Optional, 17-20 min)
    TF->>DB: Create NCC Config
    TF->>DB: Bind NCC to Workspace
    
    Note over TF,DB: Total: 15-20 minutes
```

**Time Breakdown**:
- **Phase 1**: 0-5 min (network resources)
- **Phase 2**: 5-10 min (workspace provisioning)
- **Phase 3**: 10-12 min (PE + DNS)
- **Phase 4**: 12-17 min (Unity Catalog)
- **Phase 5**: 17-20 min (NCC, if enabled)

**What Takes Long**:
- Workspace provisioning: 5-8 minutes
- Storage account creation: 2-3 minutes each

---

***REMOVED******REMOVED*** 6. Resource Breakdown

***REMOVED******REMOVED******REMOVED*** 6.1 Complete Resource List

***REMOVED******REMOVED******REMOVED******REMOVED*** **Networking Module** (5-6 resources)

| Resource | Type | Purpose |
|----------|------|---------|
| **VNet** | `azurerm_virtual_network` | Customer VNet |
| **Public Subnet** | `azurerm_subnet` | Driver nodes |
| **Private Subnet** | `azurerm_subnet` | Worker nodes |
| **Private Link Subnet** | `azurerm_subnet` | Private Endpoints |
| **NSG** | `azurerm_network_security_group` | Traffic control |
| **NSG Rules** | `azurerm_network_security_rule` | Conditional (PL only) |

***REMOVED******REMOVED******REMOVED******REMOVED*** **Workspace Module** (2-3 resources)

| Resource | Type | Purpose |
|----------|------|---------|
| **Workspace** | `azurerm_databricks_workspace` | Databricks workspace |
| **Disk Encryption Set** | `azurerm_disk_encryption_set` | Optional CMK |

***REMOVED******REMOVED******REMOVED******REMOVED*** **Private Endpoints Module** (13 resources)

| Resource | Type | Count | Purpose |
|----------|------|-------|---------|
| **Private DNS Zone** | `azurerm_private_dns_zone` | 3 | Databricks, DFS, Blob |
| **DNS VNet Link** | `azurerm_private_dns_zone_virtual_network_link` | 3 | Link zones to VNet |
| **Private Endpoint** | `azurerm_private_endpoint` | 10 | 2 Databricks + 8 Storage |

***REMOVED******REMOVED******REMOVED******REMOVED*** **Unity Catalog Module** (8-10 resources)

| Resource | Type | Purpose |
|----------|------|---------|
| **Metastore Storage** | `azurerm_storage_account` | UC metadata |
| **Metastore Container** | `azurerm_storage_container` | Metastore data |
| **External Storage** | `azurerm_storage_account` | User data |
| **External Container** | `azurerm_storage_container` | External data |
| **Access Connector** | `azurerm_databricks_access_connector` | Managed Identity |
| **Role Assignment** | `azurerm_role_assignment` | 2x (metastore + external) |
| **Metastore** | `databricks_metastore` | UC metastore |
| **Metastore Assignment** | `databricks_metastore_assignment` | Bind to workspace |
| **Storage Credential** | `databricks_storage_credential` | Storage access |
| **External Location** | `databricks_external_location` | External data path |

***REMOVED******REMOVED******REMOVED******REMOVED*** **NCC Module** (2 resources, optional)

| Resource | Type | Purpose |
|----------|------|---------|
| **NCC Config** | `databricks_mws_network_connectivity_config` | Serverless connectivity |
| **NCC Binding** | `databricks_mws_ncc_binding` | Attach to workspace |

**Total Resources**: 35-40 (depending on CMK and NCC options)

---

***REMOVED******REMOVED*** 7. Cost Breakdown

***REMOVED******REMOVED******REMOVED*** 7.1 Monthly Infrastructure Cost

| Component | Unit Cost | Quantity | Monthly Cost |
|-----------|-----------|----------|--------------|
| **Private Endpoints** | $0.01/hour | 10 | $75 |
| **VNet** | Free | 1 | $0 |
| **NSG** | Free | 1 | $0 |
| **Storage (UC)** | $0.02/GB | 100 GB | $2 |
| **Access Connector** | Free | 1 | $0 |
| **NCC** | Free | 1 | $0 |
| **Private DNS Zones** | $0.50/zone | 3 | $1.50 |

**Subtotal Infrastructure**: ~$78.50/month

**Workspace (Databricks)**:
- **Premium Tier**: ~$50/month base
- **Classic Clusters**: ~$0.55/DBU (usage-based)
- **Serverless**: ~$0.22/DBU (usage-based)

**Total (without compute)**: ~$120-150/month

---

***REMOVED******REMOVED*** 8. Classic vs. Serverless Paths

***REMOVED******REMOVED******REMOVED*** 8.1 Compute Path Comparison

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
graph LR
    subgraph "Classic Clusters - Works Immediately"
        C_DEPLOY["terraform apply"] --> C_CLUSTER["Create Cluster"]
        C_CLUSTER --> C_VNet["Runs in Customer VNet"]
        C_VNet --> C_PE["Uses VNet<br/>Private Endpoints"]
        C_PE --> C_STORAGE["Access Storage<br/>Auto-Approved"]
    end
    
    subgraph "Serverless - Requires Setup"
        S_DEPLOY["terraform apply"] --> S_NCC["NCC Attached"]
        S_NCC --> S_ENABLE["Enable Serverless<br/>Databricks UI"]
        S_ENABLE --> S_APPROVE["Approve PE<br/>Azure Portal"]
        S_APPROVE --> S_WAREHOUSE["Create SQL Warehouse"]
        S_WAREHOUSE --> S_DB_VNet["Runs in Databricks VNet"]
        S_DB_VNet --> S_NCC_PE["Uses NCC<br/>Private Endpoints"]
        S_NCC_PE --> S_STORAGE["Access Storage<br/>Manual Approval"]
    end
    
    style C_DEPLOY fill:***REMOVED***569A31,color:***REMOVED***fff
    style C_STORAGE fill:***REMOVED***569A31,color:***REMOVED***fff
    style S_APPROVE fill:***REMOVED***FF9900,color:***REMOVED***000
    style S_STORAGE fill:***REMOVED***1B72E8,color:***REMOVED***fff
```

**Recommendation**: Deploy → Test Classic → Enable Serverless (if needed)

---

***REMOVED******REMOVED*** 9. Configuration Scenarios

***REMOVED******REMOVED******REMOVED*** 9.1 Deployment Options

**Scenario A: Public Access + IP ACLs** (RECOMMENDED)
```hcl
enable_public_network_access = true
enable_ip_access_lists = true
allowed_ip_ranges = ["YOUR_NETWORK/24"]
enable_ncc = false  ***REMOVED*** Enable later for serverless
```

**Use**: Development, ops-friendly, secure with IP restrictions

---

**Scenario B: Air-Gapped** (MAXIMUM SECURITY)
```hcl
enable_public_network_access = false
enable_ip_access_lists = false
enable_ncc = true  ***REMOVED*** Serverless-ready
```

**Use**: Production, highly regulated, requires VPN/Bastion

---

**Scenario C: Serverless-Ready**
```hcl
enable_public_network_access = true
enable_ip_access_lists = true
enable_ncc = true  ***REMOVED*** Attached, ready for serverless
```

**Use**: SQL analytics, BI reporting, ad-hoc queries

---

***REMOVED******REMOVED*** 10. References

**Azure Databricks Documentation**:
- [Private Link](https://learn.microsoft.com/en-us/azure/databricks/administration-guide/cloud-configurations/azure/private-link)
- [VNet Injection](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject)
- [Unity Catalog](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/)
- [NCC](https://learn.microsoft.com/en-us/azure/databricks/administration-guide/cloud-configurations/azure/ncc)

**Related Documentation**:
- [04-SERVERLESS-SETUP.md](04-SERVERLESS-SETUP.md) - Enable serverless compute
- [README.md](README.md) - Documentation index

---

**Pattern**: Full Private (Private Link + NPIP + Unity Catalog)  
**Deployment Time**: 15-20 minutes  
**Complexity**: Medium-High  
**Cost**: ~$120-150/month (infrastructure + workspace)

**Last Updated**: 2026-01-12
