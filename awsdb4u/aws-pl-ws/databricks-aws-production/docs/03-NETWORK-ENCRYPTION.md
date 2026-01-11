***REMOVED*** 03 - Network Security & Encryption

> **Network Guide**: Traffic flows, security groups, and encryption layers visualized.

***REMOVED******REMOVED*** Quick Reference

```
🔒 2 Encryption Layers (Independent):
├── S3 Bucket Encryption (enable_encryption)
└── Workspace CMK (enable_workspace_cmk)

🛡️ 2 Security Groups:
├── Workspace SG (cluster nodes)
└── VPCE SG (VPC endpoints)

🌐 Regional VPC Endpoints (Cost Optimized):
├── S3 Gateway Endpoint (FREE)
├── STS Interface Endpoint
└── Kinesis Interface Endpoint
```

---

***REMOVED******REMOVED*** 1. Traffic Flow Patterns

***REMOVED******REMOVED******REMOVED*** 1.1 Databricks API Call Flow (Private Link)

```mermaid
%%{init: {'theme': 'base'}}%%
sequenceDiagram
    autonumber
    participant C as Cluster Node<br/>10.0.1.5
    participant DNS as VPC DNS<br/>10.0.0.2
    participant RT as Route Table
    participant SG as Security Group
    participant VPCE as VPC Endpoint<br/>10.0.3.5
    participant DB as Databricks<br/>Control Plane
    
    C->>DNS: Resolve dbc-*.cloud.databricks.com
    DNS-->>C: Returns 10.0.3.5 (private IP)
    C->>RT: Lookup route for 10.0.3.5
    RT-->>C: Use "local" route (VPC-internal)
    C->>SG: Check egress rule TCP 8443
    SG-->>C: Allow (rule: TCP 8443-8451 → vpce_sg)
    C->>VPCE: Send request to 10.0.3.5:8443
    VPCE->>DB: Forward via Private Link
    DB-->>VPCE: Response
    VPCE-->>C: Response
```

**Key Points:**
- DNS returns **private IP** when Private Link enabled
- Traffic uses VPC "local" route (no NAT)
- Security groups enforce 8443-8451 port range
- VPCE forwards to Databricks control plane privately

**Docs**: [Private Link Architecture](https://docs.databricks.com/aws/en/security/network/classic/privatelink.html)

***REMOVED******REMOVED******REMOVED*** 1.2 S3 Access Flow

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    C["Cluster Node"] -->|1. S3 API call| RT["Route Table"]
    RT -->|2. Match prefix list| GW["S3 Gateway<br/>Endpoint"]
    GW -->|3. VPC-internal| S3["S3 Bucket"]
    S3 -->|4. If encrypted| KMS["KMS Key<br/>Decrypt"]
    KMS -->|5. Decrypted data| S3
    S3 -->|6. Response| C
    
    style GW fill:***REMOVED***569A31,color:***REMOVED***fff
    style KMS fill:***REMOVED***FF9900,color:***REMOVED***000
```

**Always FREE - No data transfer charges!**

---

***REMOVED******REMOVED*** 2. Security Group Rules

***REMOVED******REMOVED******REMOVED*** 2.1 Workspace Security Group (Cluster Nodes)

**Attached To**: EC2 instances in private subnets

***REMOVED******REMOVED******REMOVED******REMOVED*** Egress Rules (Outbound)
```
Rule 1: Cluster to Cluster Communication
├── Protocol: TCP
├── Port Range: 0-65535
├── Destination: self (workspace_sg)
└── Purpose: Spark worker communication

Rule 2: Cluster to Cluster UDP
├── Protocol: UDP
├── Port Range: 0-65535
├── Destination: self (workspace_sg)
└── Purpose: Spark shuffle operations

Rule 3: Control Plane API (Private Link)
├── Protocol: TCP
├── Port Range: 8443-8451
├── Destination: vpce_sg
└── Purpose: Workspace REST API via VPCE

Rule 4: Secure Cluster Connectivity (Private Link)
├── Protocol: TCP
├── Port Range: 6666
├── Destination: vpce_sg
└── Purpose: Relay/SCC via VPCE

Rule 5: FIPS Encryption (Optional)
├── Protocol: TCP
├── Port Range: 2443
├── Destination: 0.0.0.0/0
└── Purpose: FIPS encryption for compliance security profile

Rule 6: Public Internet (if needed)
├── Protocol: TCP
├── Port Range: 443, 53
├── Destination: 0.0.0.0/0
└── Purpose: Maven, PyPI, DNS
```

***REMOVED******REMOVED******REMOVED******REMOVED*** Ingress Rules (Inbound)
```
Rule 1: TCP from Clusters
├── Protocol: TCP
├── Port Range: 0-65535
├── Source: self (workspace_sg)
└── Purpose: Allow worker-to-worker

Rule 2: UDP from Clusters
├── Protocol: UDP
├── Port Range: 0-65535
├── Source: self (workspace_sg)
└── Purpose: Allow shuffle traffic
```

**Docs**: [Security Groups](https://docs.databricks.com/aws/en/security/network/classic/security-groups.html)

***REMOVED******REMOVED******REMOVED*** 2.2 VPC Endpoint Security Group

**Attached To**: Databricks VPC endpoints (workspace + relay)

***REMOVED******REMOVED******REMOVED******REMOVED*** Egress Rules
```
Rule 1: Allow All Outbound
├── Protocol: All
├── Port Range: All
├── Destination: 0.0.0.0/0
└── Purpose: VPCE to Databricks
```

***REMOVED******REMOVED******REMOVED******REMOVED*** Ingress Rules
```
Rule 1: From Workspace SG (8443-8451)
├── Protocol: TCP
├── Port Range: 8443-8451
├── Source: workspace_sg
└── Purpose: Allow API calls

Rule 2: From Workspace SG (6666)
├── Protocol: TCP
├── Port Range: 6666
├── Source: workspace_sg
└── Purpose: Allow SCC
```

---

***REMOVED******REMOVED*** 3. Encryption Layers

***REMOVED******REMOVED******REMOVED*** 3.1 Dual Encryption Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
flowchart TD
    subgraph "Layer 1: S3 Bucket Encryption"
        KMS1["KMS Key<br/>S3 Encryption"]
        S3["S3 Buckets<br/>• DBFS Root<br/>• UC Metastore<br/>• UC External"]
        KMS1 -->|Encrypts| S3
    end
    
    subgraph "Layer 2: Workspace CMK"
        KMS2["KMS Key<br/>Workspace Storage"]
        DBFS["DBFS Root<br/>at-rest"]
        EBS["EBS Volumes<br/>cluster storage"]
        MS["Managed Services<br/>notebooks, jobs"]
        KMS2 -->|Encrypts| DBFS
        KMS2 -->|Encrypts| EBS
        KMS2 -->|Encrypts| MS
    end
    
    style KMS1 fill:***REMOVED***569A31,color:***REMOVED***fff
    style KMS2 fill:***REMOVED***FF9900,color:***REMOVED***000
```

**Independent Configuration:**
- `enable_encryption = true` → Layer 1 only
- `enable_workspace_cmk = true` → Layer 2 only
- Both can be true simultaneously
- Neither interferes with the other

**Docs**: [Customer-Managed Keys](https://docs.databricks.com/aws/en/security/keys/customer-managed-keys-managed-services-aws.html)

***REMOVED******REMOVED******REMOVED*** 3.2 KMS Key Usage

```
Layer 1 - S3 Bucket Encryption:
├── When: enable_encryption = true
├── Key Created: aws_kms_key.databricks
├── Encrypts: All S3 buckets (SSE-KMS)
└── Permissions: UC roles get KMS permissions

Layer 2 - Workspace CMK:
├── When: enable_workspace_cmk = true
├── Key Created: aws_kms_key.workspace_storage
├── Encrypts: DBFS root, EBS, Managed Services
└── Permissions: In KMS key policy (Databricks service principal)
```

***REMOVED******REMOVED******REMOVED*** 3.3 Key Rotation

```
AWS Automatic Rotation (Enabled by default):
├── Rotates underlying key material annually
├── ARN remains the same
├── Applies to both Layer 1 and Layer 2 keys
└── No action required

Manual Rotation to Different Key:
├── Managed Services CMK: ✅ Supported
├── Storage CMK (DBFS/EBS): ❌ Not supported
└── S3 Bucket keys: ✅ Update S3 bucket config
```

**Docs**: [Key Rotation](https://docs.databricks.com/aws/en/security/keys/configure-customer-managed-keys***REMOVED***rotate-an-existing-key)

---

***REMOVED******REMOVED*** 4. Network Scenarios

***REMOVED******REMOVED******REMOVED*** 4.1 Private Link vs Public Internet

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '***REMOVED***e1e1e1'}}}%%
flowchart TD
    START["enable_private_link"] -->|true| PL["Private Link Path"]
    START -->|false| PUB["Public Internet Path"]
    
    PL --> PLDNS["DNS returns<br/>private IP 10.0.3.x"]
    PLDNS --> PLVPCE["Traffic via<br/>VPC Endpoint"]
    PLVPCE --> PLDB["Databricks<br/>Private Link"]
    
    PUB --> PUBDNS["DNS returns<br/>public IP"]
    PUBDNS --> NAT["Traffic via<br/>NAT Gateway"]
    NAT --> IGW["Internet<br/>Gateway"]
    IGW --> PUBDB["Databricks<br/>Public Internet"]
    
    style PL fill:***REMOVED***569A31,color:***REMOVED***fff
    style PUB fill:***REMOVED***FF9900,color:***REMOVED***000
```

**Comparison:**

| Aspect | Private Link (true) | Public Internet (false) |
|--------|---------------------|-------------------------|
| DNS Resolution | Private IP 10.0.3.x | Public IP | 
| Traffic Path | VPC Endpoint → Private Link | NAT → Internet |
| Data Egress Charges | Lower | Higher |
| Security | No internet exposure | Internet-routable |
| Cost | VPCE charges ~$7.2/day | NAT charges variable |

---

***REMOVED******REMOVED*** 5. Port Requirements

***REMOVED******REMOVED******REMOVED*** 5.1 Critical Ports

```
Databricks Control Plane:
├── 8443-8451: REST API, Unity Catalog, WebSockets
├── 6666: Secure Cluster Connectivity (ONLY with Private Link)
└── 2443: FIPS encryption (ONLY if compliance security profile enabled)

AWS Services:
├── 443: S3 Gateway, STS, Kinesis (via regional VPC endpoints)
└── 3306: MySQL metastore (LEGACY - NOT USED with Unity Catalog)

Public Internet (via NAT Gateway):
├── 443: Maven Central, PyPI, Docker registries
└── 53: DNS resolution
```

***REMOVED******REMOVED******REMOVED*** 5.2 Port 8443-8451 Range Explained

```
Why 9 ports (8443-8451)?

8443: Primary workspace API
8444-8451: WebSocket connections, streaming, long-running jobs

All 9 ports required for full functionality!
```

**Warning**: Restricting to only 8443 will break WebSocket features

**Docs**: [Port Requirements](https://docs.databricks.com/aws/en/security/network/classic/privatelink.html***REMOVED***ports)

---

***REMOVED******REMOVED*** 6. DNS Resolution

***REMOVED******REMOVED******REMOVED*** 6.1 Private DNS for VPC Endpoints

```mermaid
%%{init: {'theme': 'base'}}%%
sequenceDiagram
    participant C as Cluster
    participant DNS as VPC DNS
    participant VPCE as VPC Endpoint
    
    Note over VPCE: private_dns_enabled = true
    C->>DNS: Query dbc-abc123.cloud.databricks.com
    DNS->>VPCE: Check VPCE private hosted zone
    VPCE-->>DNS: Return 10.0.3.5 (private IP)
    DNS-->>C: 10.0.3.5
    
    Note over C: Traffic stays in VPC!
```

**Key Setting**: `private_dns_enabled = true` on VPC endpoint

**Without Private DNS:**
- DNS returns public IP
- Traffic goes via NAT/IGW even with VPC endpoint
- Defeats purpose of Private Link

---

***REMOVED******REMOVED*** 7. Regional Endpoint Configuration (Recommended)

***REMOVED******REMOVED******REMOVED*** 7.1 Why Use Regional Endpoints?

✅ **Already Configured**: This deployment uses regional VPC endpoints for all AWS services:
- **S3**: `com.amazonaws.${region}.s3` (Gateway endpoint - FREE)
- **STS**: `com.amazonaws.${region}.sts` (Interface endpoint)
- **Kinesis**: `com.amazonaws.${region}.kinesis-streams` (Interface endpoint)

✅ **Benefits**:
- **Lower latency**: Direct regional connections to AWS services
- **Reduced cost**: No cross-region data transfer charges
- **Better security**: Traffic stays within your region
- **No internet exposure**: All AWS service traffic via VPC endpoints

**Docs**: [Configure Regional Endpoints](https://docs.databricks.com/aws/en/security/network/classic/customer-managed-vpc***REMOVED***recommended-configure-regional-endpoints)

***REMOVED******REMOVED******REMOVED*** 7.2 Spark Configuration for Regional Endpoints (Optional)

While VPC endpoints handle AWS service traffic automatically, you may optionally configure Spark to use regional S3/STS endpoints explicitly. This is useful for enforcing data residency requirements.

⚠️ **Important**: This configuration prevents cross-region S3 access. Only apply if all your S3 buckets are in the same region.

***REMOVED******REMOVED******REMOVED******REMOVED*** Option A: Notebook-Level Configuration

Add to the beginning of your notebook:

**Scala:**
```scala
%scala
spark.conf.set("fs.s3a.stsAssumeRole.stsEndpoint", "https://sts.<region>.amazonaws.com")
spark.conf.set("fs.s3a.endpoint", "https://s3.<region>.amazonaws.com")
```

**Python:**
```python
%python
spark.conf.set("fs.s3a.stsAssumeRole.stsEndpoint", "https://sts.<region>.amazonaws.com")
spark.conf.set("fs.s3a.endpoint", "https://s3.<region>.amazonaws.com")
```

Replace `<region>` with your AWS region (e.g., `us-west-2`).

***REMOVED******REMOVED******REMOVED******REMOVED*** Option B: Cluster-Level Configuration

Add to cluster **Spark config** (Cluster → Edit → Advanced Options → Spark):

```
spark.hadoop.fs.s3a.endpoint https://s3.<region>.amazonaws.com
spark.hadoop.fs.s3a.stsAssumeRole.stsEndpoint https://sts.<region>.amazonaws.com
```

***REMOVED******REMOVED******REMOVED******REMOVED*** Option C: Cluster Policy (Recommended for All Clusters)

Create or update your cluster policy to enforce regional endpoints for all clusters:

```json
{
  "spark_conf.fs.s3a.endpoint": {
    "type": "fixed",
    "value": "https://s3.<region>.amazonaws.com"
  },
  "spark_conf.fs.s3a.stsAssumeRole.stsEndpoint": {
    "type": "fixed",
    "value": "https://sts.<region>.amazonaws.com"
  }
}
```

***REMOVED******REMOVED******REMOVED*** 7.3 When to Apply Spark Regional Configuration

***REMOVED******REMOVED******REMOVED******REMOVED*** ✅ Apply When:
- All your S3 buckets are in the **same region** as the workspace
- You want to explicitly **prevent cross-region** S3 access
- You're following **strict data residency** requirements (e.g., GDPR, compliance)
- You want to **enforce** regional-only access via cluster policies

***REMOVED******REMOVED******REMOVED******REMOVED*** ❌ Do NOT Apply When:
- You access S3 buckets in **multiple regions** (most common)
- You need **cross-region data replication** or disaster recovery
- You use **global S3 URLs** or multi-region applications
- You're **uncertain** about your S3 bucket locations

***REMOVED******REMOVED******REMOVED*** 7.4 How Regional Endpoints Work

```mermaid
%%{init: {'theme': 'base'}}%%
sequenceDiagram
    participant Cluster as Cluster Node
    participant DNS as VPC DNS
    participant VPCE as VPC Endpoint<br/>(Regional)
    participant S3 as S3 Service<br/>(Regional)
    
    Note over Cluster,S3: Without Spark Config (Default)
    Cluster->>DNS: Resolve s3.amazonaws.com (global)
    DNS-->>Cluster: Private IP (VPC endpoint)
    Cluster->>VPCE: Request via VPC endpoint
    VPCE->>S3: Regional service
    S3-->>VPCE: Response
    VPCE-->>Cluster: Response
    
    Note over Cluster,S3: With Spark Regional Config
    Cluster->>DNS: Resolve s3.<region>.amazonaws.com
    DNS-->>Cluster: Private IP (VPC endpoint)
    Cluster->>VPCE: Request via VPC endpoint
    VPCE->>S3: Regional service (enforced)
    S3-->>VPCE: Response (same region only)
    VPCE-->>Cluster: Response
```

**Key Differences:**
- **Without Spark config**: VPC endpoint routes to regional service automatically, but allows cross-region access via global URL
- **With Spark config**: Explicitly enforces regional-only access by using regional URLs

***REMOVED******REMOVED******REMOVED*** 7.5 Troubleshooting Regional Endpoints

***REMOVED******REMOVED******REMOVED******REMOVED*** Issue: "Access Denied" after applying Spark config
**Cause**: S3 bucket is in a different region than the workspace  
**Solution**: Either move bucket to workspace region, or remove Spark regional config

***REMOVED******REMOVED******REMOVED******REMOVED*** Issue: Cross-region replication stopped working
**Cause**: Regional endpoint config blocks cross-region S3 access  
**Solution**: Remove `fs.s3a.endpoint` and `fs.s3a.stsAssumeRole.stsEndpoint` from Spark config

***REMOVED******REMOVED******REMOVED******REMOVED*** Issue: Can't access buckets with global S3 URLs
**Cause**: Regional config enforces regional URLs only  
**Solution**: Update S3 paths to use regional format: `s3://bucket/path` (Spark handles conversion)

**Docs**: [Troubleshoot Regional Endpoints](https://docs.databricks.com/aws/en/security/network/classic/customer-managed-vpc***REMOVED***troubleshoot-regional-endpoints)

---

***REMOVED******REMOVED*** Next Steps

✅ Network security understood → [04-QUICK-START.md](04-QUICK-START.md) - Deploy now!

✅ Need troubleshooting → [05-TROUBLESHOOTING.md](05-TROUBLESHOOTING.md) - Common issues

**Docs**: [Network Security](https://docs.databricks.com/aws/en/security/network/index.html)
