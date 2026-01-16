# Databricks Common Questions & Answers

_Your guide to frequently asked questions across Databricks topics_

**Quick Navigation:**
- [General Concepts](#general-concepts)
- [Networking](#networking)
- [Authentication & Identity](#authentication--identity)
- [Security & Compliance](#security--compliance)
- [Troubleshooting](#troubleshooting)

---

## General Concepts

### Compute Types

**Q: What's the difference between classic compute and serverless compute?**

**A:** Databricks offers two compute types with different networking models:

- **Classic compute plane**:
  - Runs in **your cloud account** (your VPC/VNet)
  - You manage networking (subnets, security groups, NAT, routes)
  - Used for: All-purpose clusters, job clusters with classic compute
  - Covered in the [Networking Guide](./networking.md)

- **Serverless compute plane**:
  - Runs in **Databricks-managed cloud account**
  - Databricks manages networking
  - Used for: SQL warehouses, serverless jobs, serverless notebooks
  - Connectivity to your resources via Network Connectivity Configuration (NCC)
  - See Databricks serverless networking documentation

---

## Networking

### General Networking

**Q: Do I need customer-managed networking, or can I use Databricks defaults?**

**A:** For **classic compute**, it depends on your requirements:

- **Use customer-managed if:**
  - Production workloads with compliance requirements
  - Need to integrate with existing VPC/VNet infrastructure
  - Require Private Link/PrivateLink for private connectivity
  - Limited IP address space (need smaller, right-sized subnets)
  - Want to share VPC/VNet across multiple workspaces
  - Internal policies require network control

- **Databricks-managed is fine for:**
  - POCs and quick prototypes
  - Development and testing environments
  - No compliance requirements
  - Plenty of IP address space
  - Simple, fast deployment

> **Recommendation**: For production, customer-managed networking is the recommended approach.

**Q: Can I convert a workspace from Databricks-managed to customer-managed networking?**

**A:** No. The networking model is set during workspace creation and cannot be changed. However:
- You **can** move a workspace from one customer-managed VPC to another customer-managed VPC
- You **cannot** convert Databricks-managed to customer-managed
- Solution: Create new workspace with customer-managed networking, migrate workloads

**Q: Can multiple workspaces share the same network?**

**A:** Yes! This is a common pattern:

- **AWS**: Multiple workspaces can share the same VPC
  - Each workspace needs 2+ subnets
  - Subnets can be shared across workspaces or unique per workspace
  - Security groups can be shared or unique (unique recommended)

- **Azure**: Multiple workspaces can share the same VNet
  - Each workspace needs its own 2 subnets (public and private)
  - Subnets **cannot** be shared between workspaces
  - Plan IP space accordingly

- **GCP**: Multiple workspaces can share the same VPC
  - Each workspace needs 1 subnet
  - Subnets can be shared or unique

Plan IP capacity for all workspaces combined.

**Q: How much IP space do I really need?**

**A:** Use this formula:

**AWS:**
```
Databricks uses 2 IPs per node
AWS reserves 5 IPs per subnet

Required IPs = (Max concurrent nodes × 2) + 5

Example for 100 nodes:
(100 × 2) + 5 = 205 IPs
Recommend /24 (251 usable IPs)
```

**Azure:**
```
Databricks uses 1 IP per node
Azure reserves 5 IPs per subnet

Required IPs = (Max concurrent nodes) + 5

Example for 100 nodes:
100 + 5 = 105 IPs
Recommend /24 (251 usable IPs)
```

**GCP:**
```
Databricks uses 1 IP per node
GCP reserves 4 IPs per subnet

Required IPs = (Max concurrent nodes) + 4

Example for 100 nodes:
100 + 4 = 104 IPs
Recommend /24 (251 usable IPs)
```

Add 30-50% buffer for growth.

**Q: What happens if I run out of IP addresses?**

**A:** 
- New clusters will fail to start with "Insufficient IP addresses" error
- Existing clusters continue running
- **Mitigation options**:
  - Add larger subnets to existing VPC/VNet
  - Use workspace pools/photon (requires fewer nodes)
  - Create new workspace with larger subnets
  - Share subnets with another workspace (if it has capacity)

---

### AWS Networking

**Q: Why does Databricks require outbound `0.0.0.0/0` access?**

**A:** Databricks clusters need outbound access for:
1. **Control plane communication** - heartbeats, logs, job submissions (required)
2. **Unity Catalog metadata** - via ports 8443-8451 (required)
3. **AWS services** - S3, EC2, STS, Kinesis (required)
4. **Package repositories** - PyPI, Maven, CRAN (optional - can use mirrors)
5. **Legacy Hive metastore** - port 3306 (optional, not needed with Unity Catalog)

Security groups must allow `0.0.0.0/0`. For fine-grained control, use **firewall or proxy** to filter specific destinations.

**Q: Can I block specific outbound destinations?**

**A:** Yes, but use the right layer:
- **Security groups**: Must allow `0.0.0.0/0` (Databricks requirement)
- **Firewall/proxy**: Filter to specific domains and IPs (recommended approach)

This gives you control while meeting Databricks requirements.

**Q: Are VPC endpoints required?**

**A:** No, but recommended:
- **S3 Gateway Endpoint**: Optional but recommended (free, better performance)
- **STS Interface Endpoint**: Optional (reduces NAT costs)
- **PrivateLink Endpoints**: Required only if using AWS PrivateLink

**Q: Why does Databricks use 2 IP addresses per node?**

**A:** Databricks assigns:
1. **Management IP** - control plane communication, logging, metrics
2. **Spark application IP** - data processing, shuffle traffic

This separation improves security and network performance.

**Q: Can I use AWS PrivateLink without customer-managed VPC?**

**A:** No. AWS PrivateLink **requires** customer-managed VPC. You cannot use PrivateLink with Databricks-managed networking.

**Q: Where do I find control plane NAT IPs for my region?**

**A:** See official documentation: [Databricks Control Plane IPs](https://docs.databricks.com/resources/supported-regions.html)

These IPs are needed for:
- S3 bucket policies
- Firewall allow lists
- Network ACLs (if customized)

**Q: Can I access S3 buckets in different regions?**

**A:** Yes, but with considerations:
- **Without regional endpoints**: Cross-region access works via NAT gateway
- **With regional endpoints configured**: Cross-region access is **blocked**
- Only configure regional S3 endpoints if all buckets are in same region
- Traffic goes through NAT gateway (charges apply)

**Q: Do I need NAT Gateway in every Availability Zone?**

**A:** 
- **Minimum**: 1 NAT Gateway (single AZ)
- **Recommended for production**: 1 NAT Gateway per AZ for high availability
- If single NAT Gateway fails, clusters in other AZs cannot reach internet
- Cost vs availability trade-off

**Q: Why do Network ACLs require allowing `0.0.0.0/0` inbound?**

**A:** This is about **stateless return traffic**, not inbound calls:

- Databricks cluster nodes have **no public IPs**
- All connections are outbound-initiated (to control plane, S3, etc.)
- NACLs are **stateless** - they don't track connections
- When a cluster makes an outbound request, the **response** comes back as inbound traffic on ephemeral ports
- NACL must allow this **return traffic** inbound from `0.0.0.0/0`

**This is secure because:**
- Cluster nodes have no public IPs (cannot be reached from internet)
- Real security comes from Security Groups (stateful) and no public IPs
- NACLs should be permissive; use Security Groups for access control

---

### Azure Networking

**Q: Why does Azure require two subnets?**

**A:** Azure Databricks uses subnets differently than AWS:
- **Public subnet**: For Databricks-managed infrastructure (load balancers, internal services)
- **Private subnet**: For your cluster compute nodes (driver and workers)
- Both subnets required, but serve different purposes
- Public subnet is typically small (/26), private subnet sized for clusters

**Q: What is subnet delegation and why is it needed?**

**A:** Subnet delegation grants Azure Databricks permission to create resources in your subnet:
- Private subnet must be delegated to `Microsoft.Databricks/workspaces`
- Allows Databricks to deploy cluster VMs in your subnet
- Public subnet does NOT require delegation
- Delegation is set once during subnet creation

**Q: What are Azure Service Tags and why are they better?**

**A:** Service Tags are Azure-managed labels that represent IP ranges for Azure services:
- **`AzureDatabricks`**: All Databricks control plane IPs for your region
- **`Storage`**: All Azure Storage IPs for your region
- **`Sql`**: All Azure SQL IPs (for legacy metastore)
- **`EventHub`**: All Event Hub IPs (for logging)

**Benefits**:
- No need to maintain IP lists (Azure updates automatically)
- Regional-aware (automatically uses correct IPs for your region)
- Simpler NSG rules compared to AWS `0.0.0.0/0`
- More secure (only allows Azure service IPs, not all internet)

**Q: Can I use the same VNet for multiple workspaces?**

**A:** Yes, with proper planning:
- Each workspace needs its own two subnets (public and private)
- Subnets cannot be shared between workspaces
- Plan IP space accordingly
- Example: 3 workspaces = 6 subnets needed

**Q: Do Azure NSGs have the same stateless issues as AWS NACLs?**

**A:** No! This is a key difference:
- **Azure NSGs are stateful** (like AWS Security Groups)
- They automatically allow return traffic
- No need for complex ephemeral port rules
- Much simpler to configure than AWS NACLs
- No "allow 0.0.0.0/0 inbound" requirement for return traffic

**Q: What's the difference between NAT Gateway and Azure Firewall?**

**A:** 

| Feature | NAT Gateway | Azure Firewall |
|---------|-------------|----------------|
| Purpose | Basic outbound NAT | Advanced security appliance |
| Filtering | None | URL/FQDN, IP, application rules |
| Logging | Basic | Comprehensive |
| Cost | Lower (~$40/month) | Higher (~$1000/month) |
| Use Case | Simple outbound access | Compliance, deep inspection |
| Setup | Simple | Complex |

**Recommendation**: Start with NAT Gateway, add Azure Firewall if compliance requires egress filtering.

**Q: Can I use Azure Private Link without VNet injection?**

**A:** No. Azure Private Link **requires** VNet injection (customer-managed VNet). You cannot use Private Link with Databricks-managed networking.

**Q: How do I access ADLS Gen2 securely?**

**A:** Three options:
1. **Service Endpoints** (recommended for simplicity):
   - Enable on private subnet
   - Traffic stays on Azure backbone
   - Free
2. **Private Endpoints** (maximum security):
   - Deploy private endpoint for storage account
   - Fully private connectivity
   - Additional cost per endpoint
3. **Storage Firewall**:
   - Restrict storage to specific VNets
   - Add exception for Azure Databricks

**Q: Why does Databricks use only 1 IP per node on Azure (vs 2 on AWS)?**

**A:** Different architecture:
- **Azure**: Single IP handles both management and Spark traffic
- **AWS**: Separate IPs for management and Spark (more isolation)
- **Result**: Azure capacity planning is simpler (1:1 ratio)

---

### GCP Networking

**Q: How many subnets does GCP require?**

**A:** GCP requires only **1 subnet** per workspace - simpler than AWS (2) or Azure (2).

**Q: What is Private Google Access and why is it important?**

**A:** Private Google Access allows VMs without external IPs to reach Google services (GCS, Artifact Registry, BigQuery, etc.) using internal IP addresses:

**Benefits:**
- Traffic stays on Google's network backbone (never goes to internet)
- No NAT costs for Google service traffic
- Better performance
- Required for Databricks to access Artifact Registry (runtime images)

**Critical**: Must be **enabled on the subnet** for Databricks to work properly.

**Q: What's the difference between Cloud NAT and Private Google Access?**

**A:**

| Feature | Cloud NAT | Private Google Access |
|---------|-----------|---------------------|
| Purpose | Access to **internet** | Access to **Google services** |
| Traffic Destination | External websites, Databricks control plane | GCS, GAR, BigQuery, etc. |
| Cost | Per GB processed | Free |
| Required For | Databricks control plane access | Google service access |
| Traffic Path | Through NAT to internet | Google backbone only |

**Both are typically needed:**
- Private Google Access: For GCS, Artifact Registry
- Cloud NAT: For Databricks control plane, external package repos

**Q: What is a Shared VPC in GCP?**

**A:** A Shared VPC (also called Cross Project Network or XPN) allows you to separate:
- **Host project**: Contains the VPC network
- **Service project**: Where workspace compute/storage resources are created

**Use cases:**
- Centralized network management
- Separate billing per workspace
- Different teams managing network vs workspaces
- Compliance requirements for project separation

**Note**: Don't confuse this with "sharing a VPC between workspaces" - both standalone and Shared VPCs can host multiple workspaces.

**Q: Can subnets be shared across multiple workspaces?**

**A:** Yes! Unlike Azure (where each workspace needs unique subnets), GCP allows:
- Multiple workspaces sharing the same subnet
- Plan capacity carefully if sharing
- Alternative: Use unique subnets per workspace for isolation

**Q: What is VPC Service Controls (VPC-SC)?**

**A:** VPC Service Controls provides an additional security perimeter around Google Cloud resources:

**Purpose:**
- Prevent data exfiltration
- Enforce security boundaries
- Control data movement between projects
- Complement VPC firewall rules

**When to use:**
- Highly regulated environments (finance, healthcare, government)
- Data residency requirements
- Defense-in-depth security
- Need to prevent accidental data exfiltration

**Note**: VPC-SC is complex to set up. Only implement if compliance requires it.

**Q: What is Private Service Connect (PSC)?**

**A:** Private Service Connect provides private connectivity to Databricks control plane:
- Traffic stays on Google backbone (no internet)
- Enhanced security
- Requires customer-managed VPC
- Premium pricing tier

Similar to AWS PrivateLink or Azure Private Link.

**Q: Do GCP firewall rules work like AWS Security Groups?**

**A:** Similar but with key differences:

| Feature | GCP Firewall Rules | AWS Security Groups |
|---------|-------------------|---------------------|
| Level | VPC-level | Instance-level |
| Statefulness | Stateful | Stateful |
| Default | Deny ingress, allow egress | Deny all unless allowed |
| Tags | Yes (network tags) | No (attach to instances) |
| Complexity | Medium | Medium |

Both automatically allow return traffic (stateful).

**Q: Why does Databricks use only 1 IP per node on GCP (vs 2 on AWS)?**

**A:** Similar to Azure, different architecture:
- **GCP**: Single IP handles both management and Spark traffic
- **AWS**: Separate IPs for management and Spark (more isolation)
- **Result**: GCP capacity planning is simpler (1:1 ratio)

**Q: What happens if I forget to enable Private Google Access?**

**A:** Databricks clusters will fail to start because they cannot:
- Access Artifact Registry to download runtime images
- Access GCS for workspace storage
- Access other Google services

**Fix**: Enable Private Google Access on the subnet and restart cluster creation.

---

## Authentication & Identity

_Coming soon - content from authentication.md will be added here_

---

## Security & Compliance

**Q: Is traffic between control plane and compute plane encrypted?**

**A:** Yes, all traffic is encrypted:
- **In transit**: TLS 1.3 encryption for all control/compute communication
- **At rest**: Storage encryption (S3/ADLS/GCS with SSE or CMK)
- **Secure Cluster Connectivity**: Encrypted WebSocket tunnel
- No unencrypted data transmission

**Q: Can I restrict which storage buckets clusters can access?**

**A:** Yes, multiple layers of control:
1. **Cloud IAM permissions** - limit which buckets role/principal can access
2. **Storage bucket policies** - restrict access to specific VPCs/endpoints/IPs
3. **Unity Catalog** - fine-grained access control on tables/files
4. **VPC/Private Endpoints** - network-level restrictions

Combine these for defense-in-depth.

**Q: How do I audit network traffic?**

**A:** Cloud-specific options:

**AWS:**
- VPC Flow Logs - captures IP traffic
- CloudWatch Logs - Databricks cluster logs
- Unity Catalog audit logs - data access
- AWS CloudTrail - API calls

**Azure:**
- NSG Flow Logs - network traffic
- Azure Monitor - metrics and logs
- Unity Catalog audit logs
- Azure Activity Log - resource changes

**GCP:**
- VPC Flow Logs
- Cloud Logging
- Unity Catalog audit logs
- Cloud Audit Logs

**Q: Can I deploy Databricks in a fully air-gapped environment?**

**A:** No, minimum connectivity required:
- Compute plane must reach control plane (via internet or Private Link)
- Control plane is Databricks-managed (not in your account)
- With Private Link/PrivateLink/PSC, traffic stays on cloud backbone (no internet traversal)
- Can block all other internet access with firewall

---

## Troubleshooting

**Q: Cluster won't start - how do I debug network issues?**

**A:** Follow this checklist:

1. **Check subnet capacity**:
   - AWS: `aws ec2 describe-subnets --subnet-ids <subnet-id>`
   - Azure: Check in Azure Portal under subnet properties
   - GCP: `gcloud compute networks subnets describe <subnet-name>`
   - Look for available IP count

2. **Verify security/firewall rules**:
   - Check egress rules for required ports (443, 8443-8451)
   - Ensure intra-VNet/VPC traffic allowed
   - Verify service tags (Azure) or CIDR ranges correct

3. **Check route tables**:
   - Verify default route (`0.0.0.0/0`) points to NAT Gateway/Firewall
   - Ensure route table associated with correct subnet

4. **Verify NAT/outbound connectivity**:
   - AWS: Check NAT Gateway state
   - Azure: Check NAT Gateway or Azure Firewall
   - GCP: Check Cloud NAT configuration

5. **DNS settings** (AWS only):
   - Ensure DNS hostnames enabled
   - Ensure DNS resolution enabled

**Q: Cluster started but can't access storage - what's wrong?**

**A:** Common causes:

1. **IAM/permissions**:
   - Verify instance profile/managed identity has storage read/write
   - Check trust policy allows Databricks to assume role

2. **Storage access policies**:
   - Check bucket/storage account policies
   - Verify VPC/VNet allowed in firewall rules
   - Check private endpoint configuration

3. **Network connectivity**:
   - Verify VPC/private endpoints configured
   - Check endpoint policies (if restricted)
   - Test connectivity from compute subnet

**Q: How do I test networking before creating workspace?**

**A:** Pre-deployment tests:

1. **Launch test VM** in same subnet
2. **Test outbound connectivity**:
   ```bash
   # Test control plane
   curl -I https://accounts.cloud.databricks.com
   
   # Test storage
   # AWS: curl -I https://s3.<region>.amazonaws.com
   # Azure: curl -I https://<storage>.blob.core.windows.net
   # GCP: curl -I https://storage.googleapis.com
   
   # Test DNS resolution
   nslookup accounts.cloud.databricks.com
   ```
3. **Verify routing**:
   ```bash
   traceroute 8.8.8.8  # Should go through NAT Gateway
   ```
4. **Check security rules** allow required traffic
5. **Verify IAM/permissions** on test VM

---

## Performance & Optimization

_Coming soon - performance-related Q&A will be added here_

---

## How to Use This Guide

1. **Search** - Use Ctrl/Cmd+F to find your question
2. **Navigate** - Use table of contents for topic browsing
3. **Cross-reference** - Questions link to relevant guides
4. **Contribute** - Found an answer elsewhere? It should be here!

---

## Related Guides

- **[Networking Guide](./networking.md)** - Comprehensive networking concepts
- **[Authentication Guide](./authentication.md)** - Set up Terraform authentication
- **[Identities Guide](./identities.md)** - Understand access patterns

---

**Last Updated**: January 15, 2026  
**Maintainer**: Databricks Platform Engineering

---

**Don't see your question?** Check the official documentation or ask in the Databricks Community.
