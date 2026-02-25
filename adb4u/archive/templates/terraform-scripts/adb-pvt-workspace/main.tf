# Define local variables for use throughout the configuration.
# - `prefix`: Prefix for naming resources, combining a workspace prefix and a random string.
# - `location`: Azure region where resources will be deployed.
# - `cidr`: CIDR block for the network, taken from input variable.
# - `dbfsname`: Name for the DBFS storage, generated without special characters.
# - `tags`: Standard tags for resource identification, propagated to all resources.
locals {
  prefix   = "${var.workspace_prefix}-${random_string.naming.result}"
  location = var.rglocation
  cidr     = var.spokecidr
  dbfsname = "${var.workspace_prefix}${random_string.naming.result}dbfs"
  tags = {
    Environment = var.tags_environment
    Owner       = lookup(data.external.me.result, "name")
    Epoch       = random_string.naming.result
    RemoveAfter = var.tags_removeafter
  }
}

# Generates a random string used in naming conventions across resources.
# - `special`: Excludes special characters from the generated string.
# - `upper`: Generates lowercase letters only.
# - `length`: Length of the random string is set to 3 characters.
resource "random_string" "naming" {
  special = false
  upper   = false
  length  = 3
}

# Fetches information about the currently authenticated Azure client, including
# client ID, subscription ID, and tenant ID, which may be used in resource configuration.
data "azurerm_client_config" "current" {
}

# Retrieves the current Azure account user information using an external data source.
# Executes the `az account show --query user` command and captures the user's name.
data "external" "me" {
  program = ["az", "account", "show", "--query", "user"]
}

# Outputs the client ID of the Azure client to be used in other configurations or for reference.
output "arm_client_id" {
  value = data.azurerm_client_config.current.client_id
}

# Outputs the subscription ID of the Azure client, which can be referenced in other configurations.
output "arm_subscription_id" {
  value = data.azurerm_client_config.current.subscription_id
}

# Outputs the tenant ID of the Azure client, useful for configuring multi-tenant applications.
output "arm_tenant_id" {
  value = data.azurerm_client_config.current.tenant_id
}

# Outputs the Azure region being used for deploying resources, specified in the local variable.
output "azure_region" {
  value = local.location
}

# Creates an Azure Resource Group for deploying resources.
# - `name`: The name is based on the defined prefix.
# - `location`: The region where the resource group is created, specified in the local variable.
# - `tags`: Tags for organizational purposes, assigned to the resource group.
resource "azurerm_resource_group" "this" {
  name     = "${local.prefix}-rg"
  location = local.location
  tags     = local.tags
}

# Outputs the name of the created resource group for reference in other configurations.
output "resource_group" {
  value = azurerm_resource_group.this.name
}
