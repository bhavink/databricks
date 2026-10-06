Azure Databricks Security Best Practices
==============
**Production-ready, modular Terraform templates** for secure Azure Databricks deployments.

- **[Complete Documentation →](./docs/)**
- **[Authentication Setup Guide →](../guides/authentication.md)** - New to Terraform? Start here!

---

## Modular Terraform Structure

This repository provides **production-ready, modular Terraform templates** for Azure Databricks deployments with comprehensive documentation, UML diagrams, and troubleshooting guides.

### Repository Structure

```
adb4u/
├── docs/                      # All documentation centralized here
│   ├── README.md              # Documentation index
│   ├── 01-QUICKSTART.md       # Quick start guide
│   ├── 02-DEPLOYMENT-CHECKLIST.md # Pre-flight checklist
│   ├── 03-TRAFFIC-FLOWS.md    # Network traffic patterns
│   ├── 04-TROUBLESHOOTING.md  # Common issues & solutions
│   ├── guides/                # Additional guides
│   │   └── 01-SERVERLESS-SETUP.md
│   ├── modules/               # Module documentation
│   │   ├── 01-NETWORKING.md
│   │   ├── 02-WORKSPACE.md
│   │   ├── 03-UNITY-CATALOG.md
│   │   ├── 04-NCC.md
│   │   ├── 05-CMK.md
│   │   └── 06-SEP.md
│   └── patterns/              # Pattern-specific guides
│       ├── 01-NON-PL.md
│       └── 02-FULL-PRIVATE.md
│
├── deployments/               # Pre-built deployment patterns
│   ├── non-pl/                # Good: Non-Private Link (Ready)
│   ├── full-private/          # Good: Full Private (Ready)
│   ├── byor/                  # Good: Bring Your Own Resources (Ready)
│   ├── serverless/            # Good: Serverless workspace (no VNet needed)
│
├── modules/                   # Reusable Terraform modules
│   ├── networking/            # VNet, subnets, NSG, NAT
│   ├── workspace/             # Databricks workspace
│   ├── unity-catalog/         # Metastore, storage, credentials
│   ├── ncc/                   # Network Connectivity Config (serverless)
│   ├── key-vault/             # Azure Key Vault integration
│   ├── private-endpoints/     # Private Link endpoints
│   ├── service-endpoint-policy/ # Service Endpoint Policies
│   ├── security/              # Security modules (CMK, IP access lists)
│   └── monitoring/            # Diagnostic settings (workspace audit logs)
│
└── archive/                   # Legacy content and templates
    └── LEGACY-CONTENT.md      # Historical reference
```

### Deployment Patterns

#### 1. **Non-Private Link (Non-PL)** Production Ready
- **Control Plane**: Public
- **Data Plane**: Private (NPIP)
- **Egress**: NAT Gateway
- **Storage**: Service Endpoints
- **Serverless**: NCC attached (Service Endpoints or Private Link)

- **[Quick Start Guide →](./docs/01-QUICKSTART.md)**
- **[Serverless Setup →](./docs/guides/01-SERVERLESS-SETUP.md)**
- **[Troubleshooting Guide →](./docs/04-TROUBLESHOOTING.md)** - Review before deploying!

#### 2. **Full Private (Air-gapped)** Production Ready
- **Workspace Access**: Private Link (SCC relay + API)
- **Data Plane**: Private (NPIP)
- **Egress**: None (isolated)
- **Storage**: Private Link
- **Serverless**: NCC attached (Private Link required)

- **[Pattern Documentation →](./docs/patterns/02-FULL-PRIVATE.md)**
- **[Serverless Setup →](./docs/guides/01-SERVERLESS-SETUP.md)**
- **[Troubleshooting Guide →](./docs/04-TROUBLESHOOTING.md)** - Common issues & solutions!

#### 3. **BYOR (Bring Your Own Resources)** Production Ready
- Integrate with existing Azure infrastructure
- Bring your own VNet, Storage Account, Key Vault
- Customer-Managed Keys (CMK) for enhanced security
- Flexible configuration for existing environments

**[BYOR Documentation →](./deployments/byor/README.md)**

#### 4. **Serverless** Validated
- **Compute**: Serverless only (`computeMode = Serverless`); no customer VNet for compute
- **Workspace**: ARM `computeMode = Serverless` via AzAPI, the same call as the official [SRA `serverless_workspace` module](https://github.com/databricks/terraform-databricks-sra/tree/main/azure/tf/modules/serverless_workspace); no VNet unless you choose a private front-end
- **Egress**: Serverless network policy (restricted and enforced, or full access)
- **Storage**: NCC private endpoint rules to your storage accounts

**[Serverless Deployment →](./deployments/serverless/README.md)**

#### 5. **Hub-Spoke with Firewall (Data Exfiltration Protection)**
- Guideline: the [Azure data exfiltration protection blog](https://www.databricks.com/blog/data-exfiltration-protection-with-azure-databricks) (definitive for hub-spoke); the [Databricks SRA](https://github.com/databricks/terraform-databricks-sra/tree/main/azure/tf) for reference
- No deployment in this repo by design. The [Well-Architected Agent](../well-architected-agent) assesses hub-spoke workspaces against the blog (`classic-dep` baseline): firewall route, hub peering, firewall application rules and logs, Private Link, service endpoint policies, CMK

### Key Features

- **Secure Cluster Connectivity (NPIP)**: Always enabled
- **Unity Catalog**: Mandatory, regional metastore
- **Network Connectivity Config (NCC)**: Mandatory for serverless compute
- **Flexible Networking**: Create new or BYOV
- **Service Endpoint Policies**: Enhanced storage security
- **Customer-Managed Keys (CMK)**: Optional encryption control
- **Private Link Support**: Full private connectivity option
- **BYOR Support**: Integrate with existing infrastructure
- **Diagnostic Logs** (opt-in): every workspace log category to Log Analytics / Storage / Event Hub (`enable_diagnostic_settings`)
- **Workspace Storage Firewall** (opt-in, Full Private): `enable_default_storage_firewall` with a dedicated access connector — read the caveats in `modules/workspace/variables.tf`
- **Serverless Egress Control** (opt-in): restricted, enforced network policy via `enable_network_policy`
- **Modular Design**: Reusable, composable components
- **Well-Documented**: Comprehensive guides in `/docs`

### Quick Start

```bash
# Navigate to deployment
cd deployments/non-pl

# Configure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy
export TF_VAR_databricks_account_id="<your-account-id>"
terraform init
terraform plan
terraform apply
```

**Full guide:** See [docs/01-QUICKSTART.md](./docs/01-QUICKSTART.md)

### Serverless Compute

**All deployments include Network Connectivity Configuration (NCC)** for serverless SQL Warehouses and Serverless Notebooks.

#### **Serverless Connectivity Options**:

| Pattern | Classic Clusters | Serverless Compute |
|---------|------------------|-------------------|
| **Non-PL** | Service Endpoints (VNet) | Service Endpoints or Private Link (via NCC) |
| **Full Private** | Private Endpoints (VNet) | Private Link (via NCC) |
| **BYOR** | Flexible (based on existing setup) | Configurable via NCC |

**Post-Deployment Setup**:
- **Serverless Setup**: See [docs/guides/01-SERVERLESS-SETUP.md](./docs/guides/01-SERVERLESS-SETUP.md)

**Key Points**:
- NCC is **mandatory** (created automatically like Unity Catalog)
- Classic clusters work immediately after deployment
- Serverless requires additional configuration (manual approval for Private Link)

### Documentation

All documentation is centralized in the **[docs/](./docs/)** folder:

**Getting Started**:
- **[Quick Start Guide](./docs/01-QUICKSTART.md)** - Deploy your first workspace
- **[Deployment Checklist](./docs/02-DEPLOYMENT-CHECKLIST.md)** - Pre-flight validation
- **[Traffic Flows](./docs/03-TRAFFIC-FLOWS.md)** - Network traffic patterns and sequences
- **[Troubleshooting Guide](./docs/04-TROUBLESHOOTING.md)** - Common issues and solutions

**Guides**:
- **[Serverless Setup Guide](./docs/guides/01-SERVERLESS-SETUP.md)** - Enable SQL Warehouses & Notebooks

**Pattern Documentation**:
- **[Non-PL Pattern](./docs/patterns/01-NON-PL.md)** - Non-Private Link deployment
- **[Full Private Pattern](./docs/patterns/02-FULL-PRIVATE.md)** - Air-gapped deployment

**Module Documentation**:
- **[Networking Module](./docs/modules/01-NETWORKING.md)** - VNet, subnets, NSG, NAT
- **[Workspace Module](./docs/modules/02-WORKSPACE.md)** - Databricks workspace configuration
- **[Unity Catalog Module](./docs/modules/03-UNITY-CATALOG.md)** - Metastore and catalogs
- **[NCC Module](./docs/modules/04-NCC.md)** - Network Connectivity Configuration
- **[CMK Module](./docs/modules/05-CMK.md)** - Customer-Managed Keys
- **[SEP Module](./docs/modules/06-SEP.md)** - Service Endpoint Policies

---

## Legacy Content

Historical content and diagrams have been archived. See **[archive/LEGACY-CONTENT.md](./archive/LEGACY-CONTENT.md)** for reference.

**For new deployments, use the modular structure documented above.**

---

**Repository Version**: 2.0
