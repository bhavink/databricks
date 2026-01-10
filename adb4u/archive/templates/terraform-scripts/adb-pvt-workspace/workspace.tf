# Creates a Databricks Access Connector, which enables Databricks to securely connect 
# to other Azure services. Uses a system-assigned identity for secure authentication.
resource "azurerm_databricks_access_connector" "ac" {
  name                = "${local.prefix}-ac"  # Unique name for the access connector
  resource_group_name = azurerm_resource_group.this.name  # Resource group for the connector
  location            = azurerm_resource_group.this.location  # Region matching the resource group

  identity {
    type = "SystemAssigned"  # Automatically assigns a managed identity for Azure resources
  }

  tags = local.tags  # Tags for resource tracking and management
}

# Creates a Databricks Workspace with network and security configurations for a secure deployment.
resource "azurerm_databricks_workspace" "this" {
  name                                  = "${local.prefix}-workspace"  # Workspace name with unique prefix
  resource_group_name                   = azurerm_resource_group.this.name  # Resource group for the workspace
  location                              = azurerm_resource_group.this.location  # Region for the workspace
  sku                                   = "premium"  # Premium SKU for advanced Databricks features
  tags                                  = local.tags  # Tags for resource tracking and management
  default_storage_firewall_enabled      = true  # Enables firewall for default storage
  access_connector_id                   = azurerm_databricks_access_connector.ac.id  # ID of the Access Connector for secure access
  public_network_access_enabled         = true  # Allows public network access, typically set for private endpoints
  network_security_group_rules_required = "AllRules"  # Requires all NSG rules for enhanced security
  customer_managed_key_enabled          = true  # Enables customer-managed key for workspace data encryption

  # Custom parameters to configure VNet, subnets, and storage for the workspace.
  custom_parameters {
    no_public_ip                                         = var.no_public_ip  # Disables public IP if set to true
    virtual_network_id                                   = azurerm_virtual_network.this.id  # VNet ID for the workspace
    private_subnet_name                                  = azurerm_subnet.private.name  # Private subnet for secure workspace communication
    public_subnet_name                                   = azurerm_subnet.public.name  # Public subnet for workspace access
    public_subnet_network_security_group_association_id  = azurerm_subnet_network_security_group_association.public.id  # NSG association for the public subnet
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.private.id  # NSG association for the private subnet
    storage_account_name                                 = local.dbfsname  # Specifies the name of the storage account
  }

  # Dependencies to ensure proper cleanup of resources, especially subnets and security groups, upon deletion.
  depends_on = [
    azurerm_subnet_network_security_group_association.public,
    azurerm_subnet_network_security_group_association.private,
    databricks_metastore.this  # Ensures metastore is deleted before the workspace
  ]
}

# Output variable for the Azure resource ID of the Databricks Workspace.
# This ID is used for referencing the workspace within Azure management.
output "databricks_azure_workspace_resource_id" {
  value = azurerm_databricks_workspace.this.id  # Outputs the workspace resource ID
}

# Output variable for the Databricks Workspace URL.
# Provides the workspace access URL, following the specific format in Azure Databricks.
output "workspace_url" {
  value = "https://${azurerm_databricks_workspace.this.workspace_url}/"  # Outputs the full workspace URL
}
