# Networking Module

This module provisions AWS networking resources for Databricks workspace with Private Link.

## Resources Created

### VPC and Subnets
- 1 VPC with DNS support enabled
- 2 Public subnets (for NAT Gateways)
- 2 Private subnets (for Databricks clusters)
- 2 PrivateLink subnets (for VPC endpoints)

### Internet Connectivity
- 1 Internet Gateway
- 2 NAT Gateways (high availability across AZs)
- Route tables for public, private, and PrivateLink subnets

### Security Groups
- Workspace security group (for Databricks clusters)
- VPC Endpoint security group (for Private Link)

### VPC Endpoints
- **Workspace Endpoint** (Frontend - UI/API access)
- **Relay Endpoint** (Backend - Secure Cluster Connectivity)
- **S3 Gateway Endpoint** (cost-effective S3 access)
- **STS Interface Endpoint** (IAM role assumption)
- **Kinesis Interface Endpoint** (logging and lineage)

## Usage

```hcl
module "networking" {
  source = "./modules/networking"
  
  prefix                   = "dbx-abc123"
  region                   = "us-west-2"
  vpc_cidr                 = "10.0.0.0/16"
  private_subnet_cidrs     = ["10.0.1.0/24", "10.0.2.0/24"]
  privatelink_subnet_cidrs = ["10.0.3.0/24", "10.0.4.0/24"]
  public_subnet_cidrs      = ["10.0.101.0/24", "10.0.102.0/24"]
  availability_zones       = ["us-west-2a", "us-west-2b"]
  
  tags = {
    Environment = "Production"
    Project     = "Databricks"
  }
}
```

## Outputs

| Output | Description |
|--------|-------------|
| `vpc_id` | VPC ID |
| `private_subnet_ids` | Private subnet IDs for Databricks clusters |
| `privatelink_subnet_ids` | PrivateLink subnet IDs for VPC endpoints |
| `workspace_security_group_id` | Security group ID for clusters |
| `vpce_security_group_id` | Security group ID for VPC endpoints |
| `workspace_vpce_id` | Workspace VPC endpoint ID |
| `relay_vpce_id` | Relay VPC endpoint ID |

## Network Architecture

```
                                 Internet
                                    |
                            Internet Gateway
                                    |
                    +---------------+---------------+
                    |                               |
              Public Subnet 1                 Public Subnet 2
                NAT Gateway                     NAT Gateway
                    |                               |
              Private Subnet 1                Private Subnet 2
           (Databricks Clusters)          (Databricks Clusters)
                    |                               |
                    +---------------+---------------+
                                    |
                            PrivateLink Subnets
                                    |
                    +---------------+---------------+--------+
                    |               |               |        |
              Workspace VPC    Relay VPC       S3 VPC   STS/Kinesis
               Endpoint        Endpoint       Endpoint   Endpoints
              (Frontend)       (Backend)
```

## Security

- Private subnets have internet access via NAT Gateways (for library downloads)
- PrivateLink subnets are isolated (no internet access)
- All Databricks control plane traffic goes through VPC endpoints
- Security groups enforce least-privilege access

