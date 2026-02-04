# 01 - Architecture & Deployment Flow

> **Visual Guide**: Understand the complete deployment architecture through modular diagrams.

## Quick Reference

```
📦 7 Terraform Modules → 65-70 AWS/Databricks Resources
⏱️  15-20 minutes deployment time
🔒 Private Link + Unity Catalog + CMK Encryption
```

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Module Dependency Flow](#2-module-dependency-flow)
3. [VPC & Network Layout](#3-vpc--network-layout)
4. [Deployment Sequence](#4-deployment-sequence)
5. [Resource Breakdown](#5-resource-breakdown)

---

## 1. High-Level Architecture

### 1.1 Complete System Overview

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1e1e1'}}}%%
%%{init: {'flowchart': {'htmlLabels': false}}}%%
graph TB
    subgraph "AWS Account"
        subgraph "VPC 10.0.0.0/22"
            subgraph "Public Subnets /26"
                NAT["NAT Gateways<br/>2 AZs<br/>High Availability"]
                IGW["Internet<br/>Gateway"]
            end
            
            subgraph "Private Subnets /24 - Databricks Clusters"
                CLUSTER["Cluster Nodes<br/>Spark Workers<br/>502 IPs total"]
            end
            
            subgraph "PrivateLink Subnets /26 - VPC Endpoints"
                VPCE["VPC Endpoints<br/>• Workspace 8443-8451<br/>• Relay SCC 6666<br/>• AWS Services"]
            end
            
            subgraph "Storage Layer"
                S3["S3 Buckets<br/>• DBFS Root<br/>• UC Metastore<br/>• UC External<br/>KMS Encrypted"]
            end
        end
        
        subgraph "IAM Layer"
            ROLES["IAM Roles<br/>• Cross-Account<br/>• UC Metastore<br/>• UC External<br/>• Instance Profile"]
        end
        
        subgraph "Encryption Layer"
            KMS["KMS Keys<br/>• S3 Buckets<br/>• Workspace CMK<br/> DBFS/EBS/MS"]
        end
    end
    
    subgraph "Databricks Control Plane"
        CONTROL["Databricks SaaS<br/>accounts.cloud.databricks.com"]
    end
    
    subgraph "Unity Catalog"
        UC["Metastore<br/>Catalogs<br/>External Locations"]
    end
    
    CLUSTER -->|Private Link| VPCE
    VPCE -.->|Backend Private| CONTROL
    CLUSTER -->|NAT| NAT
    NAT --> IGW
    CLUSTER -->|Gateway Endpoint| S3
    ROLES -->|Permissions| S3
    ROLES -->|Permissions| KMS
    KMS -->|Encrypts| S3
    CONTROL -->|Provisions| UC
    UC -->|Stores Metadata| S3
    
    style CONTROL fill:#FF3621
    style S3 fill:#569A31
    style VPCE fill:#FF9900
    style UC fill:#1B72E8
```

**Key Components:**
- **VPC**: Custom 10.0.0.0/22 CIDR with 3 subnet tiers
- **Private Link**: Optional VPC endpoints for secure connectivity
- **Unity Catalog**: Data governance layer with metastore
- **Encryption**: Optional customer-managed KMS keys
- **High Availability**: Multi-AZ deployment (2 availability zones)

---

## 2. Module Dependency Flow

### 2.1 Terraform Module Execution Order

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1e1e1'}}}%%
flowchart TD
    START["terraform apply"] --> NET["1. Networking Module<br/>VPC, Subnets, Security Groups<br/>VPC Endpoints"]
    NET --> IAM["2. IAM Module<br/>Cross-Account Role<br/>UC Metastore Role<br/>Instance Profile"]
    IAM --> KMS["3. KMS Module Optional<br/>S3 Encryption Key<br/>Workspace CMK<br/>+ UC Role KMS Policy"]
    KMS --> STORAGE["4. Storage Module<br/>S3 Buckets<br/>DBFS Root<br/>UC Buckets"]
    STORAGE --> WORKSPACE["5. Databricks Workspace<br/>MWS Resources<br/>Private Access Settings<br/>Workspace Creation"]
    WORKSPACE --> UC["6. Unity Catalog Module<br/>Metastore Assignment<br/>External Location<br/>Workspace Catalog<br/>+ External Role KMS Policy"]
    UC --> USER["7. User Assignment<br/>Workspace Admin<br/>Permissions"]
    USER --> END["Deployment Complete"]
    
    style START fill:#569A31
    style END fill:#1B72E8
    style KMS fill:#FF9900
    style UC fill:#FF3621
```

**Critical Dependencies:**
- KMS depends on IAM (needs cross-account role ARN)
- Storage depends on KMS (for encrypted buckets)
- Workspace depends on Storage + IAM
- Unity Catalog depends on Workspace (needs workspace ID)
- User Assignment depends on Unity Catalog (must wait for UC resources)

**Docs**: [Databricks Terraform Provider](https://registry.terraform.io/providers/databricks/databricks/latest/docs)

---

## 3. VPC & Network Layout

### 3.1 Subnet Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1e1e1'}}}%%
graph TB
    subgraph "VPC 10.0.0.0/22 1024 IPs"
        subgraph "AZ-1 us-west-1a"
            PUB1["Public Subnet<br/>10.0.0.0/26<br/>62 IPs<br/>NAT GW"]
            PRIV1["Private Subnet<br/>10.0.1.0/24<br/>251 IPs<br/>Clusters"]
            PL1["PrivateLink Subnet<br/>10.0.3.0/26<br/>62 IPs<br/>VPC Endpoints"]
        end
        
        subgraph "AZ-2 us-west-1c"
            PUB2["Public Subnet<br/>10.0.0.64/26<br/>62 IPs<br/>NAT GW"]
            PRIV2["Private Subnet<br/>10.0.2.0/24<br/>251 IPs<br/>Clusters"]
            PL2["PrivateLink Subnet<br/>10.0.3.64/26<br/>62 IPs<br/>VPC Endpoints"]
        end
    end
    
    PUB1 -.->|Internet| IGW[Internet Gateway]
    PUB2 -.->|Internet| IGW
    PRIV1 -->|via| PUB1
    PRIV2 -->|via| PUB2
    
    style PRIV1 fill:#569A31
    style PRIV2 fill:#569A31
    style PL1 fill:#FF9900
    style PL2 fill:#FF9900
```

**IP Allocation:**
- **Public Subnets**: 124 IPs total (NAT Gateways)
- **Private Subnets**: 502 IPs total (Databricks clusters)
- **PrivateLink Subnets**: 124 IPs total (VPC endpoints)
- **Reserved**: AWS reserves first 4 + last 1 IP per subnet

**Docs**: [VPC and Subnets](https://docs.databricks.com/aws/en/administration-guide/cloud-configurations/aws/customer-managed-vpc.html)

### 3.2 Route Table Logic

```
Private Subnet Route Table:
┌─────────────────┬───────────────────┬──────────────────────┐
│   Destination   │      Target       │      Description     │
├─────────────────┼───────────────────┼──────────────────────┤
│  10.0.0.0/22    │      local        │  VPC-internal traffic│
│  0.0.0.0/0      │   nat-gateway     │  Internet via NAT    │
└─────────────────┴───────────────────┴──────────────────────┘

PrivateLink Subnet Route Table:
┌─────────────────┬───────────────────┬──────────────────────┐
│   Destination   │      Target       │      Description     │
├─────────────────┼───────────────────┼──────────────────────┤
│  10.0.0.0/22    │      local        │  VPC-internal only   │
└─────────────────┴───────────────────┴──────────────────────┘
```

---

## 4. Deployment Sequence

### 4.1 End-to-End Flow (Cluster Launch)

```mermaid
%%{init: {'theme': 'base'}}%%
sequenceDiagram
    autonumber
    actor User as User/Admin
    participant WS as Databricks<br/>Workspace UI
    participant CP as Control Plane<br/>via Private Link
    participant VPC as Customer VPC
    participant CLUSTER as Spark Cluster
    participant S3 as S3 DBFS/UC
    participant UC as Unity Catalog
    
    User->>WS: Create Cluster
    WS->>CP: API Call dbc-*.cloud.databricks.com:8443
    Note over WS,CP: DNS returns private IP 10.0.3.x
    CP->>VPC: Launch EC2 Instances
    VPC->>CLUSTER: Provision nodes in private subnets
    CLUSTER->>CP: Register via Relay VPCE:6666
    Note over CLUSTER,CP: Secure Cluster Connectivity
    CLUSTER->>S3: Mount DBFS via Gateway Endpoint
    CLUSTER->>UC: Query catalog metadata
    UC-->>CLUSTER: Return table locations
    CLUSTER->>S3: Read/Write data with UC permissions
    CLUSTER-->>User: Cluster Ready
```

**Timeline:**
1. User action → API call (instant)
2. Control plane → VPC provisioning (30-60s)
3. Cluster startup → registration (2-5 min)
4. Unity Catalog → data access (instant)

**Docs**: [Cluster Creation](https://docs.databricks.com/aws/en/clusters/index.html)

### 4.2 Traffic Path Decision Tree

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1e1e1'}}}%%
flowchart TD
    START["Cluster Node<br/>Initiates Traffic"] --> DNS{DNS Query<br/>What is destination?}
    
    DNS -->|S3 bucket| S3PATH["S3 Gateway Endpoint<br/>FREE, VPC-internal"]
    DNS -->|dbc-*.cloud.databricks.com| DBDNS{Private Link<br/>Enabled?}
    DNS -->|Public internet| NATPATH["NAT Gateway<br/>→ Internet Gateway"]
    
    DBDNS -->|Yes| PRIV["Private IP 10.0.3.x<br/>→ VPC Endpoint<br/>→ Private Link"]
    DBDNS -->|No| NATPATH
    
    S3PATH --> S3["S3 Buckets<br/>DBFS, Unity Catalog"]
    PRIV --> CONTROL["Databricks<br/>Control Plane"]
    NATPATH --> INTERNET["Public Internet<br/>Maven, PyPI, etc"]
    
    style S3PATH fill:#569A31
    style PRIV fill:#FF9900
    style NATPATH fill:#FF3621
```

**Key Decision Points:**
1. **S3 traffic**: Always uses Gateway Endpoint (free)
2. **Databricks API**: Private Link if enabled, else NAT
3. **Public internet**: Always via NAT Gateway

---

## 5. Resource Breakdown

### 5.1 Resources by Category

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1e1e1'}}}%%
pie title "Resource Distribution 70 Total"
    "Networking 30" : 30
    "IAM/Security 12" : 12
    "Storage 4" : 4
    "Databricks 15" : 15
    "Unity Catalog 6" : 6
    "Optional CMK 3" : 3
```

### 5.2 Detailed Resource List

#### Networking Module (30 resources)
```
VPC & Subnets (9):
├── 1 VPC
├── 2 Public subnets
├── 2 Private subnets (Databricks clusters)
├── 2 PrivateLink subnets (VPC endpoints)
└── 2 NAT Gateways

Routing (7):
├── 3 Route tables (public, private, privatelink)
└── 6 Route table associations

VPC Endpoints (6):
├── Databricks Workspace VPCE (8443-8451) [Conditional: Private Link]
├── Databricks Relay VPCE (6666) [Conditional: Private Link]
├── S3 Gateway Endpoint (FREE, regional) [Always]
├── STS Interface Endpoint (regional) [Always]
├── Kinesis Interface Endpoint (regional) [Always]
└── RDS Endpoint: NOT CONFIGURED (Unity Catalog deployment)

Regional Endpoint Benefits:
├── Lower latency (direct regional connections)
├── Reduced cost (no cross-region data transfer)
└── Better security (traffic stays in region) ✅

Security Groups (8):
├── Workspace SG + 6 rules
└── VPCE SG + 1 rule
```

**Docs**: [VPC Requirements](https://docs.databricks.com/aws/en/administration-guide/cloud-configurations/aws/customer-managed-vpc.html)

#### IAM Module (12 resources)
```
Cross-Account Role (3):
├── IAM role
├── IAM policy (inline, Databricks-generated)
└── Policy attachment

Unity Catalog Metastore Role (3):
├── IAM role
├── IAM policy
└── Policy attachment

Instance Profile (3):
├── IAM role
├── IAM policy  
├── IAM instance profile

UC External Location Role (3):
├── Created in Unity Catalog module
├── Workspace-specific
└── Includes workspace ID in name
```

**Docs**: [IAM Roles](https://docs.databricks.com/aws/en/administration-guide/cloud-configurations/aws/iam-roles.html)

#### KMS Module (3 resources - optional)
```
S3 Bucket Encryption:
├── KMS key
├── KMS alias
└── Key policy

Workspace CMK (optional):
├── KMS key (DBFS/EBS/Managed Services)
├── KMS alias
└── Key policy

IAM Policies:
├── UC Metastore role KMS policy
└── UC External role KMS policy
```

**Docs**: [Customer-Managed Keys](https://docs.databricks.com/aws/en/security/keys/customer-managed-keys-managed-services-aws.html)

#### Storage Module (4 resources)
```
S3 Buckets:
├── DBFS Root bucket
├── Unity Catalog metastore bucket
├── Unity Catalog external location bucket
└── Unity Catalog root storage bucket (conditional)
```

**Docs**: [S3 Bucket Configuration](https://docs.databricks.com/aws/en/administration-guide/cloud-configurations/aws/configure-s3-access.html)

#### Databricks Workspace Module (15 resources)
```
MWS Resources:
├── Credentials configuration
├── Storage configuration
├── Network configuration
├── Customer-managed keys (optional)
└── Workspace

Private Access Settings:
├── PAS object (can be reused)
└── Public access control
```

**Docs**: [Workspace Configuration](https://docs.databricks.com/aws/en/getting-started/create-workspace.html)

#### Unity Catalog Module (6+ resources)
```
Metastore:
├── Metastore (or use existing)
├── Workspace assignment
└── Admin grants

External Storage:
├── Storage credential
├── External location
├── IAM role (workspace-specific)
├── IAM policy
└── Location grants

Workspace Catalog:
├── Catalog
├── Default namespace setting
└── Catalog admin grants
```

**Docs**: [Unity Catalog Setup](https://docs.databricks.com/aws/en/data-governance/unity-catalog/create-metastore.html)

### 5.3 Optional vs Required Resources

```
Always Created (55):
├── Networking: VPC, Subnets, NAT, AWS Service Endpoints
├── IAM: All roles
├── Storage: All S3 buckets
├── Workspace: MWS resources
└── Unity Catalog: Metastore assignment, catalog

Optional based on enable_private_link=true (2):
├── Databricks Workspace VPCE
└── Databricks Relay VPCE

Optional based on enable_encryption=true (3):
├── S3 encryption KMS key
└── 2x IAM policies for UC roles

Optional based on enable_workspace_cmk=true (2):
├── Workspace CMK key
└── Key policy

Optional based on existing_private_access_settings_id (1):
├── Private Access Settings (PAS)
```

---

## 6. Configuration Options

### 6.1 Deployment Scenarios

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e1e1e1'}}}%%
flowchart LR
    START["Configuration<br/>Choice"] --> PL{enable_private_link}
    
    PL -->|true| FULL["Full Private Link<br/>All Databricks traffic<br/>via VPC Endpoints"]
    PL -->|false| PUBLIC["Public Internet<br/>via NAT Gateway<br/>Lowest Cost"]
    
    FULL --> ENC{enable_encryption}
    PUBLIC --> ENC
    
    ENC -->|true| CMK["+ S3 KMS Encryption<br/>Customer-Managed Keys"]
    ENC -->|false| NOCMK["AWS-Managed<br/>Encryption"]
    
    CMK --> WCMK{enable_workspace_cmk}
    NOCMK --> WCMK
    
    WCMK -->|true| FULLCMK["+ Workspace CMK<br/>DBFS/EBS/MS Encryption"]
    WCMK -->|false| NOWCMK["Standard Encryption"]
    
    style FULL fill:#569A31
    style PUBLIC fill:#FF9900
    style FULLCMK fill:#1B72E8
```

**Configuration Matrix:**

| Scenario | enable_private_link | enable_encryption | enable_workspace_cmk | Cost |
|----------|-------------------|------------------|---------------------|------|
| **Development** | false | false | false | $ |
| **Production Basic** | true | false | false | $$ |
| **Production Secure** | true | true | false | $$$ |
| **Maximum Security** | true | true | true | $$$$ |

---

## Next Steps

✅ Architecture understood → [02-IAM-SECURITY.md](02-IAM-SECURITY.md) - IAM roles and policies

✅ Ready to deploy → [04-QUICK-START.md](04-QUICK-START.md) - 5-minute deployment

**Docs**: [Databricks AWS Architecture](https://docs.databricks.com/aws/en/getting-started/overview.html)
