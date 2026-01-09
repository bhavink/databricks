***REMOVED*** Deployment Guide: Using This Databricks Private Link Implementation

> **Related Documentation:**
> - 🚀 [docs/QUICK_START.md](docs/QUICK_START.md) - Quick deployment for first-time users
> - 📐 [ARCHITECTURE.md](ARCHITECTURE.md) - Complete architecture diagrams and traffic flows
> - 🧹 [docs/DESTROY_GUIDE.md](docs/DESTROY_GUIDE.md) - Safe destruction procedures
> - 📁 [docs/DIRECTORY_STRUCTURE.md](docs/DIRECTORY_STRUCTURE.md) - File organization reference

This guide explains how to use the optional VPC endpoint implementation in different scenarios:
- Deploy to another AWS account or region
- Adapt to Azure Databricks (Private Endpoints)
- Adapt to GCP Databricks (Private Service Connect)
- Use architecture diagrams as reference

---

***REMOVED******REMOVED*** Table of Contents

1. [Deploy to Another AWS Account/Region](***REMOVED***scenario-1-deploy-to-another-aws-accountregion)
2. [Adapt to Azure Databricks](***REMOVED***scenario-2-adapt-to-azure-databricks)
3. [Adapt to GCP Databricks](***REMOVED***scenario-3-adapt-to-gcp-databricks)
4. [Use Architecture Diagrams Only](***REMOVED***scenario-4-just-use-the-architecture-diagrams)
5. [Quick Reference Checklist](***REMOVED***quick-reference-checklist)
6. [Key Files to Reference](***REMOVED***key-files-to-reference)
7. [Common Pitfalls to Avoid](***REMOVED***common-pitfalls-to-avoid)

---

***REMOVED******REMOVED*** Scenario 1: Deploy to Another AWS Account/Region

***REMOVED******REMOVED******REMOVED*** Steps:

**1. Copy the Terraform Code:**
```bash
***REMOVED*** Copy the entire modular-version3 directory
cp -r modular-version3 my-new-workspace
cd my-new-workspace
```

**2. Update Configuration Files:**

**`terraform.tfvars`:**
```hcl
***REMOVED*** Update with your specific values
databricks_account_id = "YOUR-ACCOUNT-ID"
databricks_client_id            = "YOUR-SERVICE-PRINCIPAL-CLIENT-ID"
databricks_client_secret        = "YOUR-SERVICE-PRINCIPAL-SECRET"
aws_account_id       = "YOUR-AWS-ACCOUNT-ID"
aws_profile          = "YOUR-AWS-PROFILE"

***REMOVED*** Choose your region (VPC endpoints auto-detected!)
region = "us-east-1"  ***REMOVED*** or any supported region

***REMOVED*** Update VPC CIDR to avoid conflicts
vpc_cidr = "10.1.0.0/22"
private_subnet_cidrs = ["10.1.1.0/24", "10.1.2.0/24"]
privatelink_subnet_cidrs = ["10.1.3.0/26", "10.1.3.64/26"]
public_subnet_cidrs = ["10.1.0.0/26", "10.1.0.64/26"]

***REMOVED*** Private Link configuration (true = enabled, false = disabled)
enable_private_link = true  ***REMOVED*** Your choice

***REMOVED*** Unique S3 bucket names (random suffix added automatically)
root_storage_bucket_name = "my-company-root"
unity_catalog_bucket_name = "my-company-uc-metastore"
```

**3. Initialize and Deploy:**
```bash
terraform init
terraform plan
terraform apply
```

**4. Reuse PAS Across Multiple Workspaces (Optional):**

**First workspace:**
```hcl
existing_private_access_settings_id = ""  ***REMOVED*** Creates new PAS
```

After apply, note the output:
```bash
terraform output private_access_settings_id
***REMOVED*** Output: "pas-abc123456"
```

**Second workspace in same account:**
```hcl
existing_private_access_settings_id = "pas-abc123456"  ***REMOVED*** Reuses PAS
```

---

***REMOVED******REMOVED*** Scenario 2: Adapt to Azure Databricks

***REMOVED******REMOVED******REMOVED*** Steps:

**1. Create New Azure Project Structure:**
```bash
mkdir azure-databricks-privatelink
cd azure-databricks-privatelink

***REMOVED*** Create module structure
mkdir -p modules/{networking,databricks_workspace,unity_catalog}
```

**2. Convert Provider Configuration:**

**`main.tf`:**
```hcl
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.70"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
}

provider "databricks" {
  alias      = "account"
  host       = "https://accounts.azuredatabricks.net"
  account_id = var.databricks_account_id
  client_id     = var.databricks_client_id
  client_secret = var.databricks_client_secret
}
```

**3. Convert AWS Resources to Azure Equivalents:**

Reference the plan's Azure section for complete mappings:
- Use `azurerm_virtual_network` instead of `aws_vpc`
- Use `azurerm_subnet` instead of `aws_subnet`
- Use `azurerm_network_security_group` instead of `aws_security_group`
- Use `azurerm_private_endpoint` instead of `aws_vpc_endpoint`

**4. Key Azure-Specific Changes:**

**VPC Endpoints → Private Endpoints:**
```hcl
***REMOVED*** AWS (from plan)
resource "aws_vpc_endpoint" "workspace" {
  count = local.any_databricks_vpce_enabled ? 1 : 0
  ***REMOVED*** ...
}

***REMOVED*** Azure equivalent
resource "azurerm_private_endpoint" "databricks_frontend" {
  count = var.enable_frontend_privatelink ? 1 : 0
  name                = "${var.prefix}-databricks-frontend-pe"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.private_endpoint_subnet_id

  private_service_connection {
    name                           = "${var.prefix}-databricks-psc"
    private_connection_resource_id = azurerm_databricks_workspace.workspace.id
    subresource_names              = ["databricks_ui_api"]
    is_manual_connection           = false
  }
}
```

**Security Groups → NSG Rules:**
```hcl
***REMOVED*** AWS (from plan)
resource "aws_security_group_rule" "workspace_egress_control_plane" {
  type        = "egress"
  from_port   = 8443
  to_port     = 8451
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
  ***REMOVED*** ...
}

***REMOVED*** Azure equivalent
resource "azurerm_network_security_rule" "workspace_outbound_control_plane" {
  name                        = "AllowControlPlaneOutbound"
  priority                    = 200
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["8443-8451"]
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "AzureDatabricks"
  ***REMOVED*** ...
}
```

**5. Follow Azure Best Practices:**
- Backend-only **still requires frontend private endpoint** (same as AWS!)
- Same 4 deployment scenarios apply
- Same ports required (443, 6666, 8443-8451)

**6. Azure-Specific Variables:**
```hcl
variable "azure_subscription_id" {
  type = string
}

variable "location" {
  description = "Azure region (e.g., eastus, westus2)"
  type        = string
}

variable "resource_group_name" {
  type = string
}
```

**Azure References:**
- [Azure Databricks Private Link](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/private-link)
- [Azure Private Link Service](https://learn.microsoft.com/en-us/azure/private-link/)
- [Terraform azurerm_databricks_workspace](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/databricks_workspace)

---

***REMOVED******REMOVED*** Scenario 3: Adapt to GCP Databricks

***REMOVED******REMOVED******REMOVED*** Steps:

**1. Create New GCP Project Structure:**
```bash
mkdir gcp-databricks-psc
cd gcp-databricks-psc

mkdir -p modules/{networking,databricks_workspace,unity_catalog}
```

**2. Convert Provider Configuration:**

**`main.tf`:**
```hcl
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.70"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.region
}

provider "databricks" {
  alias      = "account"
  host       = "https://accounts.gcp.databricks.com"
  account_id = var.databricks_account_id
  ***REMOVED*** Use Google service account for auth
  google_service_account = var.google_service_account
}
```

**3. Convert AWS Resources to GCP Equivalents:**

**VPC Endpoints → PSC Forwarding Rules:**
```hcl
***REMOVED*** AWS (from plan)
resource "aws_vpc_endpoint" "workspace" {
  count = local.any_databricks_vpce_enabled ? 1 : 0
  ***REMOVED*** ...
}

***REMOVED*** GCP equivalent
resource "google_compute_forwarding_rule" "databricks_frontend" {
  count                 = var.enable_frontend_psc ? 1 : 0
  name                  = "${var.prefix}-databricks-frontend-psc"
  region                = var.region
  network               = var.network_self_link
  subnetwork            = var.psc_subnet_self_link
  ip_address            = google_compute_address.frontend_psc_ip.address
  load_balancing_scheme = ""
  target                = var.databricks_frontend_target
}
```

**Security Groups → Firewall Rules:**
```hcl
***REMOVED*** AWS (from plan)
resource "aws_security_group_rule" "workspace_egress_control_plane" {
  type        = "egress"
  from_port   = 8443
  to_port     = 8451
  ***REMOVED*** ...
}

***REMOVED*** GCP equivalent
resource "google_compute_firewall" "workspace_egress_control_plane" {
  name    = "${var.prefix}-workspace-egress-control-plane"
  network = var.network_name
  direction = "EGRESS"

  allow {
    protocol = "tcp"
    ports    = ["443", "8443-8451"]
  }

  target_tags        = ["databricks-cluster"]
  destination_ranges = ["0.0.0.0/0"]
}
```

**4. GCP-Specific Considerations:**
- Use **tags** instead of security groups
- Backend-only **still requires frontend PSC** (same pattern!)
- Private Service Connect uses IP addresses (not DNS by default)

**GCP References:**
- [GCP Databricks Private Service Connect](https://docs.gcp.databricks.com/security/network/classic/private-service-connect.html)
- [Google Cloud Private Service Connect](https://cloud.google.com/vpc/docs/private-service-connect)
- [Terraform google_compute_forwarding_rule](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_forwarding_rule)

---

***REMOVED******REMOVED*** Scenario 4: Just Use the Architecture Diagrams

**If you just want to understand the architecture without Terraform:**

**1. Open `ARCHITECTURE.md`** in this project

**2. Review the diagrams** for your scenario:
- Section 4: Full Private Link
- Section 5: Frontend-Only
- Section 6: Backend-Only (current setup)
- Section 7: Fully Public

**3. Use diagrams to:**
- Explain architecture to stakeholders
- Create manual deployment documentation
- Design network security policies
- Plan multi-cloud deployments
- Train team members

**4. Key takeaways from diagrams:**
- VPC/VNet/Network structure
- Subnet layout and sizing
- Security group/NSG/firewall rules
- Traffic flows for each scenario
- Cost implications

---

***REMOVED******REMOVED*** Quick Reference Checklist

***REMOVED******REMOVED******REMOVED*** Before You Start:

- [ ] **Understand your deployment scenario:**
  - Full Private Link (both)
  - Frontend-only
  - Backend-only
  - Fully public

- [ ] **Know the critical architecture rule:**
  - Backend-only REQUIRES workspace/frontend endpoint (not just relay!)

- [ ] **Have credentials ready:**
  - Databricks account ID
  - Service principal (client ID + secret)
  - Cloud provider credentials (AWS/Azure/GCP)

***REMOVED******REMOVED******REMOVED*** During Implementation:

- [ ] **Update all hardcoded values:**
  - Account IDs
  - Region/location
  - CIDR blocks (avoid conflicts!)
  - Bucket/storage names (must be globally unique)

- [ ] **Verify security rules include:**
  - Port 443 (HTTPS)
  - Port 6666 (SCC/relay)
  - Ports 8443-8451 (control plane + Unity Catalog)
  - DNS ports (53 TCP/UDP)

- [ ] **Test incrementally:**
  - Start with fully public (easiest)
  - Add frontend Private Link
  - Add backend Private Link
  - Validate at each step

***REMOVED******REMOVED******REMOVED*** After Deployment:

- [ ] **Verify connectivity:**
  - Can you access workspace UI?
  - Can you create a cluster?
  - Can cluster run a simple notebook?
  - Is traffic using expected paths?

- [ ] **Document your specific setup:**
  - Which scenario you chose (and why)
  - Any custom modifications
  - Regional considerations
  - Cost analysis

---

***REMOVED******REMOVED*** Key Files to Reference

1. **`ARCHITECTURE.md`** - Visual diagrams and traffic flows
2. **`resilient-twirling-umbrella.md`** (in `~/.claude/plans/`) - Complete implementation plan with Azure/GCP guides
3. **`terraform.tfvars`** - Configuration examples with detailed comments
4. **`modules/networking/security_groups.tf`** - Security rule reference (all required ports)
5. **`modules/databricks_workspace/main.tf`** - Backend-only logic (workspace + relay)

---

***REMOVED******REMOVED*** Common Pitfalls to Avoid

***REMOVED******REMOVED******REMOVED*** ❌ Don't:

- **Forget to create workspace endpoint for backend-only scenarios**
  - Backend Private Link needs BOTH workspace + relay endpoints
  - This is true across AWS, Azure, and GCP

- **Use conflicting CIDR ranges**
  - Check existing VPCs/VNets in your account
  - Avoid Databricks reserved ranges (see terraform.tfvars comments)

- **Skip the 8443-8451 egress rule to 0.0.0.0/0**
  - Causes Databricks security group validation warning
  - Required for control plane API and Unity Catalog

- **Reuse S3 bucket names across accounts**
  - S3 bucket names must be globally unique
  - Module adds random suffix automatically

- **Set `private_access_level = "ENDPOINT"` before testing backend VPCE**
  - Use "ACCOUNT" first (safer default)
  - Test backend VPC endpoint is working
  - Then switch to "ENDPOINT" to route through private relay

***REMOVED******REMOVED******REMOVED*** ✅ Do:

- **Read `ARCHITECTURE.md` first to understand traffic flows**
  - Visual diagrams show exactly how traffic routes
  - Helps debug connectivity issues

- **Test with `private_access_level = "ACCOUNT"` first (safer)**
  - Uses public relay even if backend VPC endpoint exists
  - Allows you to verify endpoint without routing traffic through it

- **Verify VPC endpoint service names for your region**
  - Module auto-detects for 18 AWS regions
  - If using unsupported region, manually specify service names

- **Use PAS reusability for multiple workspaces in same account**
  - PAS is account-level and can be shared
  - Saves configuration and ensures consistency

- **Follow the 4-scenario testing matrix in the plan**
  - Test each scenario independently
  - Validate connectivity at each step

---

***REMOVED******REMOVED*** Cross-Cloud Architecture Comparison

| Aspect | AWS | Azure | GCP |
|--------|-----|-------|-----|
| **Private Connectivity Service** | VPC Endpoints (PrivateLink) | Private Endpoints (Private Link) | Private Service Connect |
| **Frontend Connection** | Workspace VPC Endpoint | Frontend Private Endpoint | Frontend PSC Attachment |
| **Backend Connection** | Relay VPC Endpoint | Backend Private Endpoint | Relay PSC Attachment |
| **Network Security** | Security Groups (instance-level) | Network Security Groups (subnet-level) | Firewall Rules (VPC-level) |
| **DNS Resolution** | Private DNS (Route 53) | Private DNS Zones | Cloud DNS Private Zones |
| **Backend-Only Requirement** | Workspace + Relay endpoints | Frontend + Backend endpoints | Frontend + Backend PSC |
| **Subnet Requirements** | PrivateLink subnets (2 AZs) | Private endpoint subnet | PSC subnet |
| **Cost Model** | $0.01/GB + $7.30/month per interface endpoint | ~$8/month per private endpoint + data | $0.01/GB + monthly charge per PSC |

**Universal Architecture Pattern:**

All three clouds follow the same pattern:
1. Frontend connection for UI/API access (or cluster control plane calls)
2. Backend connection for SCC/relay
3. **Backend-only still requires frontend connection for control plane APIs**
4. Security rules must allow same ports (443, 6666, 8443-8451, etc.)

---

***REMOVED******REMOVED*** Deployment Scenario Summary

***REMOVED******REMOVED******REMOVED*** Private Link Enabled
```hcl
enable_private_link   = true
public_access_enabled = false  ***REMOVED*** Recommended for maximum security
```
- **Use Case:** Production workloads requiring maximum security
- **User Access:** Via Private Link (or optionally public if public_access_enabled=true)
- **Cluster Communication:** Via Private Link (SCC)
- **Resources Created:** Workspace + Relay endpoints + AWS service endpoints
- **Cost:** Higher (~$29/month for VPC endpoints)
- **Security:** Highest - all Databricks traffic private

***REMOVED******REMOVED******REMOVED*** Private Link Disabled
```hcl
enable_private_link = false
```
- **Use Case:** Dev/test, cost optimization
- **User Access:** Via public internet (NAT gateway)
- **Cluster Communication:** Via public internet (NAT gateway)
- **Resources Created:** Only AWS service endpoints (S3/STS/Kinesis)
- **Cost:** Lower (~$15/month for VPC endpoints)
- **Security:** Lower - all Databricks traffic via public internet
- **Cost:** Lowest (AWS service endpoints only)

---

***REMOVED******REMOVED*** Port Reference

All scenarios require these ports for cluster communication:

| Port(s) | Protocol | Purpose |
|---------|----------|---------|
| 443 | TCP | HTTPS (UI, API, libraries, S3) |
| 6666 | TCP | Secure Cluster Connectivity (SCC) |
| 8443 | TCP | Control plane API calls |
| 8444 | TCP | Unity Catalog logging and lineage |
| 8445-8451 | TCP | Future Databricks services |
| 3306 | TCP | External Hive metastore (optional) |
| 53 | TCP/UDP | DNS resolution |
| 0-65535 | TCP/UDP | Inter-cluster communication (same security group) |

---

***REMOVED******REMOVED*** Need Help?

- **Architecture questions:** See `ARCHITECTURE.md` for visual diagrams
- **Implementation details:** See `resilient-twirling-umbrella.md` plan file
- **Azure/GCP specifics:** Check the adaptation guide sections in the plan
- **Security rules:** Review `modules/networking/security_groups.tf`
- **Backend-only logic:** Study `modules/databricks_workspace/main.tf`

**Remember:** Backend-only Private Link requires BOTH workspace and relay endpoints across all cloud providers!
