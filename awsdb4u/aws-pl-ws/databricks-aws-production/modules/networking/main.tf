# ============================================================================
# Networking Module - Provider Configuration
# ============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    databricks = {
      source                = "databricks/databricks"
      version               = "~> 1.50"
      configuration_aliases = [databricks.account]
    }
  }
}

# ============================================================================
# Locals - Conditional Logic for VPC Endpoints
# ============================================================================

locals {
  # Determine if any Databricks VPC endpoints are enabled
  # Used to conditionally create: Databricks VPC endpoints, VPCE security group, and related rules
  any_databricks_vpce_enabled = var.enable_private_link

  # Always create PrivateLink subnets for AWS service endpoints (S3/STS/Kinesis)
  # These endpoints are always created to reduce NAT gateway data transfer costs (S3 gateway is FREE)
  # Databricks VPC endpoints (workspace/relay) also use these subnets when enabled
  privatelink_subnet_count = length(var.privatelink_subnet_cidrs)
}

# ============================================================================
# VPC
# ============================================================================

resource "aws_vpc" "databricks_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-vpc"
  })

  lifecycle {
    # Prevent VPC destruction if resources are still attached
    prevent_destroy = false
  }
}

# ============================================================================
# Public Subnets (for NAT Gateways)
# ============================================================================

resource "aws_subnet" "public" {
  count                   = length(var.public_subnet_cidrs)
  vpc_id                  = aws_vpc.databricks_vpc.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.prefix}-public-subnet-${count.index + 1}"
  })
}

# ============================================================================
# Private Subnets (for Databricks Clusters)
# ============================================================================

resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.databricks_vpc.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.tags, {
    Name = "${var.prefix}-private-subnet-${count.index + 1}"
  })
}

# ============================================================================
# PrivateLink Subnets (for VPC Endpoints)
# ============================================================================

resource "aws_subnet" "privatelink" {
  count             = local.privatelink_subnet_count
  vpc_id            = aws_vpc.databricks_vpc.id
  cidr_block        = var.privatelink_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.tags, {
    Name = "${var.prefix}-privatelink-subnet-${count.index + 1}"
  })
}

# ============================================================================
# Internet Gateway (for Public Subnets)
# ============================================================================

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.databricks_vpc.id

  tags = merge(var.tags, {
    Name = "${var.prefix}-igw"
  })
}

# ============================================================================
# Elastic IPs for NAT Gateways
# ============================================================================

resource "aws_eip" "nat" {
  count  = length(var.public_subnet_cidrs)
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.prefix}-nat-eip-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.igw]
}

# ============================================================================
# NAT Gateways (High Availability - one per AZ)
# ============================================================================

resource "aws_nat_gateway" "nat" {
  count         = length(var.public_subnet_cidrs)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(var.tags, {
    Name = "${var.prefix}-nat-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.igw]
}

# ============================================================================
# Route Table - Public Subnets
# ============================================================================

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.databricks_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = merge(var.tags, {
    Name = "${var.prefix}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count          = length(var.public_subnet_cidrs)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ============================================================================
# Route Tables - Private Subnets (one per AZ for HA NAT)
# ============================================================================

resource "aws_route_table" "private" {
  count  = length(var.private_subnet_cidrs)
  vpc_id = aws_vpc.databricks_vpc.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat[count.index].id
  }

  tags = merge(var.tags, {
    Name = "${var.prefix}-private-rt-${count.index + 1}"
  })
}

resource "aws_route_table_association" "private" {
  count          = length(var.private_subnet_cidrs)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ============================================================================
# Route Table - PrivateLink Subnets (local VPC only, no internet)
# Always created for AWS service endpoints (S3/STS/Kinesis)
# ============================================================================

resource "aws_route_table" "privatelink" {
  vpc_id = aws_vpc.databricks_vpc.id

  tags = merge(var.tags, {
    Name = "${var.prefix}-privatelink-rt"
  })
}

resource "aws_route_table_association" "privatelink" {
  count          = local.privatelink_subnet_count
  subnet_id      = aws_subnet.privatelink[count.index].id
  route_table_id = aws_route_table.privatelink.id
}
