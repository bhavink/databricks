/**
 * Azure Databricks workspace in custom VNet
 *
 * Module creates:
 * * Resource group with random prefix
 * * VNet with public and private subnet
 * * Databricks workspace
 */
locals {
  prefix   = "${var.workspace_prefix}-${random_string.naming.result}"
  location = var.rglocation
  cidr     = var.spokecidr
  dbfsname = "${var.workspace_prefix}${random_string.naming.result}" // dbfs name must not have special chars

  // tags that are propagated down to all resources
  tags = {
    Environment = var.tags_environment
    Owner       = lookup(data.external.me.result, "name")
    Epoch       = random_string.naming.result
    Keepuntil   = var.tags_environment
         }
  }

provider "random" {
}

resource "random_string" "naming" {
  special = false
  upper   = false
  length  = 3
}

data "azurerm_client_config" "current" {
}

data "external" "me" {
  program = ["az", "account", "show", "--query", "user"]
}

output "arm_client_id" {
  value = data.azurerm_client_config.current.client_id
}

output "arm_subscription_id" {
  value = data.azurerm_client_config.current.subscription_id
}

output "arm_tenant_id" {
  value = data.azurerm_client_config.current.tenant_id
}

output "azure_region" {
  value = local.location
}

resource "azurerm_resource_group" "this" {
  name     = "${local.prefix}-rg"
  location = local.location
  tags     = local.tags
}

output "resource_group" {
  value = azurerm_resource_group.this.name
}
