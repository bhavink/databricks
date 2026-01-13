***REMOVED*** Networking Module

**Module**: `modules/networking`  
**Purpose**: Creates or references Azure network infrastructure for Databricks workspace deployment

---

***REMOVED******REMOVED*** Overview

The networking module provides flexible network infrastructure for Azure Databricks deployments. It supports both **creating new network resources** and **using existing infrastructure** (BYOV - Bring Your Own VNet).

***REMOVED******REMOVED******REMOVED*** Key Features

- ✅ **BYOV Support**: Use existing VNet/Subnets/NSG or create new
- ✅ **Secure Cluster Connectivity (NPIP)**: Always enabled, no public IPs on clusters
- ✅ **Subnet Delegation**: Automatically added to all subnets
- ✅ **NAT Gateway**: Optional for internet egress (Non-PL pattern)
- ✅ **Private Link Ready**: Conditional NSG rules for PL deployments
- ✅ **Service Endpoints**: Enabled for Azure Storage and Key Vault
- ✅ **Production-Ready**: Battle-tested NSG rules and configurations

---

***REMOVED******REMOVED*** Architecture

***REMOVED******REMOVED******REMOVED*** Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│ Virtual Network (10.0.0.0/16)                               │
│                                                             │
│  ┌────────────────────────────┐  ┌───────────────────────┐ │
│  │ Public/Host Subnet         │  │ Private/Container     │ │
│  │ (10.0.1.0/26)              │  │ Subnet (10.0.2.0/26)  │ │
│  │                            │  │                       │ │
│  │ - Control Plane Endpoints  │  │ - Databricks Clusters │ │
│  │ - Public facing resources  │  │ - NPIP enabled        │ │
│  │ - NAT Gateway (Non-PL)     │  │ - No public IPs       │ │
│  └────────────────────────────┘  └───────────────────────┘ │
│              │                              │                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Network Security Group (NSG)                         │  │
│  │ - SCC-enabled rules                                  │  │
│  │ - Conditional for Private Link                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ↓
              NAT Gateway (Non-PL)
                   or
              Private Link (PL)
```

---

***REMOVED******REMOVED*** Resources Created

***REMOVED******REMOVED******REMOVED*** When Creating New Network (`use_existing_network = false`)

| Resource Type | Name Pattern | Purpose |
|--------------|--------------|---------|
| `azurerm_virtual_network` | `{prefix}-vnet` | Virtual network container |
| `azurerm_subnet` | `{prefix}-public-subnet` | Host/public subnet |
| `azurerm_subnet` | `{prefix}-private-subnet` | Container/private subnet |
| `azurerm_network_security_group` | `{prefix}-nsg` | Security rules |
| `azurerm_subnet_network_security_group_association` | (auto) | NSG → Subnet bindings |
| `azurerm_public_ip` | `{prefix}-nat-pip` | NAT Gateway public IP (if enabled) |
| `azurerm_nat_gateway` | `{prefix}-nat-gateway` | Internet egress (if enabled) |
| `azurerm_subnet_nat_gateway_association` | (auto) | NAT → Subnet bindings (if enabled) |

***REMOVED******REMOVED******REMOVED*** When Using Existing Network (`use_existing_network = true`)

| Resource Type | Purpose |
|--------------|---------|
| `data.azurerm_virtual_network` | Reference existing VNet |
| `data.azurerm_subnet` | Reference existing public subnet |
| `data.azurerm_subnet` | Reference existing private subnet |
| `data.azurerm_network_security_group` | Reference existing NSG |
| `azurerm_subnet_delegation` | Add Databricks delegation to subnets |
| `azurerm_network_security_rule` | Add required NSG rules (PL only) |

---

***REMOVED******REMOVED*** Variables

***REMOVED******REMOVED******REMOVED*** BYOV Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `use_existing_network` | bool | `false` | Use existing network resources |
| `existing_vnet_name` | string | `""` | Existing VNet name |
| `existing_resource_group_name` | string | `""` | Resource group of existing VNet |
| `existing_public_subnet_name` | string | `""` | Existing public/host subnet |
| `existing_private_subnet_name` | string | `""` | Existing private/container subnet |
| `existing_nsg_name` | string | `""` | Existing NSG name |

**Important**: When `use_existing_network = true`, **ALL** network resources must exist.

***REMOVED******REMOVED******REMOVED*** New Network Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `vnet_address_space` | list(string) | `["10.0.0.0/16"]` | VNet CIDR range |
| `public_subnet_address_prefix` | list(string) | `["10.0.1.0/26"]` | Public subnet CIDR (min /26) |
| `private_subnet_address_prefix` | list(string) | `["10.0.2.0/26"]` | Private subnet CIDR (min /26) |

**Subnet Sizing**:
- Minimum: `/26` (64 IPs) - Small clusters
- Recommended: `/24` (256 IPs) - Production workloads
- Large: `/22` (1024 IPs) - Enterprise scale

***REMOVED******REMOVED******REMOVED*** Private Link Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_private_link` | bool | `false` | Enable Private Link (full isolation) |

**Effect**:
- `true`: Creates NSG rules, no NAT Gateway
- `false`: Databricks manages NSG rules, NAT Gateway optional

***REMOVED******REMOVED******REMOVED*** NAT Gateway Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `enable_nat_gateway` | bool | `true` | Create NAT Gateway for egress |

**When to Enable**:
- ✅ **Non-PL Pattern**: Enable for internet access (PyPI, Maven, etc.)
- ❌ **Private Link Pattern**: Disable (air-gapped, no internet)

***REMOVED******REMOVED******REMOVED*** Required Configuration

| Variable | Type | Description |
|----------|------|-------------|
| `location` | string | Azure region (e.g., `eastus2`) |
| `resource_group_name` | string | Resource group for network resources |
| `workspace_prefix` | string | Naming prefix (lowercase, alphanumeric, max 12 chars) |
| `tags` | map(string) | Tags for all resources |

---

***REMOVED******REMOVED*** Outputs

***REMOVED******REMOVED******REMOVED*** Essential Outputs (IDs)

| Output | Description |
|--------|-------------|
| `vnet_id` | Virtual Network resource ID |
| `vnet_name` | Virtual Network name |
| `public_subnet_id` | Public/host subnet ID |
| `private_subnet_id` | Private/container subnet ID |
| `public_subnet_name` | Public subnet name |
| `private_subnet_name` | Private subnet name |
| `nsg_id` | Network Security Group ID |
| `nsg_name` | NSG name |
| `nat_gateway_id` | NAT Gateway ID (if enabled) |
| `nat_gateway_public_ip` | NAT Gateway public IP (if enabled) |

***REMOVED******REMOVED******REMOVED*** Structured Output

```hcl
output "network_configuration" {
  description = "Complete network configuration"
  value = {
    vnet = {
      id            = azurerm_virtual_network.this[0].id
      name          = azurerm_virtual_network.this[0].name
      address_space = azurerm_virtual_network.this[0].address_space
    }
    subnets = {
      public = {
        id              = azurerm_subnet.public[0].id
        name            = azurerm_subnet.public[0].name
        address_prefix  = azurerm_subnet.public[0].address_prefixes
        service_endpoints = azurerm_subnet.public[0].service_endpoints
      }
      private = {
        id              = azurerm_subnet.private[0].id
        name            = azurerm_subnet.private[0].name
        address_prefix  = azurerm_subnet.private[0].address_prefixes
        service_endpoints = azurerm_subnet.private[0].service_endpoints
      }
    }
    nsg = {
      id   = local.nsg_id
      name = local.nsg_name
    }
    nat_gateway = {
      enabled   = var.enable_nat_gateway
      id        = var.enable_nat_gateway ? azurerm_nat_gateway.this[0].id : null
      public_ip = var.enable_nat_gateway ? azurerm_public_ip.nat[0].ip_address : null
    }
  }
}
```

---

***REMOVED******REMOVED*** NSG Rules

***REMOVED******REMOVED******REMOVED*** Automatic NSG Rule Management

| Deployment Pattern | NSG Rules Managed By |
|-------------------|---------------------|
| **Non-PL** | Databricks (automatic) |
| **Private Link** | This module (manual) |

***REMOVED******REMOVED******REMOVED*** NSG Rules for Private Link

**Inbound Rules**:

| Name | Priority | Source | Destination | Port | Protocol | Purpose |
|------|----------|--------|-------------|------|----------|---------|
| `AllowVnetInBound` | 100 | VirtualNetwork | VirtualNetwork | * | * | Worker-to-worker |
| `AllowControlPlaneInBound` | 110 | AzureDatabricks | VirtualNetwork | * | * | Control plane access |

**Outbound Rules**:

| Name | Priority | Source | Destination | Port | Protocol | Purpose |
|------|----------|--------|-------------|------|----------|---------|
| `AllowVnetOutBound` | 100 | VirtualNetwork | VirtualNetwork | * | * | Worker-to-worker |
| `AllowControlPlaneOutBound` | 110 | VirtualNetwork | AzureDatabricks | 443 | TCP | Control plane comm |
| `AllowSqlOutBound` | 120 | VirtualNetwork | Sql | 3306 | TCP | Metastore access |
| `AllowStorageOutBound` | 130 | VirtualNetwork | Storage | 443 | TCP | DBFS access |
| `AllowEventHubOutBound` | 140 | VirtualNetwork | EventHub | 9093 | TCP | Logging |

**Reference**: [Microsoft Documentation - SCC NSG Rules](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject***REMOVED***network-security-group-rules-for-workspaces)

---

***REMOVED******REMOVED*** Service Endpoints

***REMOVED******REMOVED******REMOVED*** Enabled Service Endpoints

Automatically enabled on both public and private subnets:

- ✅ `Microsoft.Storage` - Azure Storage access
- ✅ `Microsoft.KeyVault` - Key Vault access (for CMK)

**Benefits**:
- Direct Azure backbone routing
- Improved performance
- Required for Service Endpoint Policies

---

***REMOVED******REMOVED*** Subnet Delegation

***REMOVED******REMOVED******REMOVED*** Automatic Delegation

Both subnets are automatically delegated to `Microsoft.Databricks/workspaces`:

```hcl
delegation {
  name = "databricks-delegation"
  service_delegation {
    name = "Microsoft.Databricks/workspaces"
    actions = [
      "Microsoft.Network/virtualNetworks/subnets/join/action",
      "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
      "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
    ]
  }
}
```

**Important**:
- ✅ Applied to **new** subnets automatically
- ✅ Applied to **existing** subnets via `azurerm_subnet_delegation` resource
- ❌ Cannot be removed once Databricks workspace is deployed

---

***REMOVED******REMOVED*** Usage Examples

***REMOVED******REMOVED******REMOVED*** Example 1: Non-PL with New Network

```hcl
module "networking" {
  source = "../../modules/networking"
  
  ***REMOVED*** Basic Configuration
  location            = "eastus2"
  resource_group_name = azurerm_resource_group.this.name
  workspace_prefix    = "proddb"
  
  ***REMOVED*** Create new network
  use_existing_network = false
  vnet_address_space   = ["10.0.0.0/16"]
  public_subnet_address_prefix  = ["10.0.1.0/24"]
  private_subnet_address_prefix = ["10.0.2.0/24"]
  
  ***REMOVED*** Non-PL Configuration
  enable_private_link = false
  enable_nat_gateway  = true
  
  tags = {
    Environment = "Production"
    Owner       = "platform-team"
  }
}
```

***REMOVED******REMOVED******REMOVED*** Example 2: Private Link with Existing Network (BYOV)

```hcl
module "networking" {
  source = "../../modules/networking"
  
  ***REMOVED*** Basic Configuration
  location            = "eastus2"
  resource_group_name = azurerm_resource_group.this.name
  workspace_prefix    = "proddb"
  
  ***REMOVED*** Use existing network
  use_existing_network        = true
  existing_vnet_name          = "existing-vnet"
  existing_resource_group_name = "existing-rg"
  existing_public_subnet_name  = "databricks-public"
  existing_private_subnet_name = "databricks-private"
  existing_nsg_name           = "databricks-nsg"
  
  ***REMOVED*** Private Link Configuration
  enable_private_link = true
  enable_nat_gateway  = false  ***REMOVED*** No internet access
  
  tags = {
    Environment = "Production"
    Owner       = "platform-team"
  }
}
```

***REMOVED******REMOVED******REMOVED*** Example 3: Non-PL without NAT Gateway

```hcl
module "networking" {
  source = "../../modules/networking"
  
  location            = "eastus2"
  resource_group_name = azurerm_resource_group.this.name
  workspace_prefix    = "devdb"
  
  use_existing_network = false
  enable_private_link  = false
  enable_nat_gateway   = false  ***REMOVED*** No egress, use workspace defaults
  
  tags = {
    Environment = "Development"
  }
}
```

---

***REMOVED******REMOVED*** Best Practices

***REMOVED******REMOVED******REMOVED*** Network Planning

1. **Subnet Sizing**
   - Calculate expected cluster size
   - Account for autoscaling (100% overhead)
   - Use `/24` for production (256 IPs)
   - Reserve capacity for growth

2. **Address Space**
   - Avoid conflicts with other VNets
   - Plan for VNet peering
   - Document IP allocation

***REMOVED******REMOVED******REMOVED*** Security

1. **NSG Rules**
   - ✅ Let Databricks manage rules (Non-PL)
   - ✅ Use module defaults (Private Link)
   - ❌ Don't manually add rules to Databricks NSG

2. **Service Endpoints**
   - Always enabled for better performance
   - Required for Service Endpoint Policies
   - Provides backbone routing

***REMOVED******REMOVED*** Best Practices

***REMOVED******REMOVED******REMOVED*** Issue: NSG Rule Conflicts

**Error**:
```
Security rule conflicts with Microsoft.Databricks-workspaces_UseOnly_databricks-worker-to-worker-inbound
```

**Solution**: Non-PL workspaces auto-create NSG rules. Set `enable_private_link = false` to skip custom rule creation.

***REMOVED******REMOVED******REMOVED*** Issue: Subnet Too Small

**Error**:
```
Subnet does not have enough IP addresses for requested cluster size
```

**Solution**: Use at least `/26` (64 IPs), recommended `/24` (256 IPs).

***REMOVED******REMOVED******REMOVED*** Issue: Delegation Already Exists

**Error**:
```
Subnet is already delegated to Microsoft.Databricks/workspaces
```

**Solution**: This is expected for existing subnets. Module handles this automatically.

---

***REMOVED******REMOVED*** References

- [Azure Databricks Network Architecture](https://learn.microsoft.com/en-us/azure/databricks/security/network/)
- [Secure Cluster Connectivity (NPIP)](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/secure-cluster-connectivity)
- [VNet Injection](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject)
- [NSG Rules for SCC](https://learn.microsoft.com/en-us/azure/databricks/security/network/classic/vnet-inject***REMOVED***network-security-group-rules-for-workspaces)

---

**Module Version**: 1.0  
**Terraform Version**: >= 1.5
