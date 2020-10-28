
# In `Public Preview`

# End to End [Azure Databricks](https://docs.microsoft.com/en-us/azure/databricks/workspace/) workspace provisioning, setup and configuration.

This documents the endpoints for the [SCIM API](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/scim/scim-sp) for azure [service principals](https://docs.microsoft.com/azure/active-directory/develop/app-objects-and-service-principals).

You can now use AAD user principals as well as AAD service principals as a **first class identity** in azure databricks.
Follow [this](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/aad/service-prin-aad-token) guide to create and configure service principal to use in ADB.

### published [postman collection](https://documenter.getpostman.com/view/2644780/SzmYAMkH) and api doc

### What are the goals?

- Use an Azure AD access token to access the Databricks REST API.
- Automatically add service principal with an "admin" role to ADB
- Add service principal with a "non-admin" role to ADB
- Manage servcie principal entitlements



## 

### Pre-requistes:
- [Azure Service Principal](https://docs.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals)
    Please keep aside service principal
    - client_id
    - client_secret
- [Azure Resource Group](https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/manage-resource-groups-portal#what-is-a-resource-group)
- [AAD Contributor](https://docs.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#contributor) role assigned to `service principal` on `resource group` used to deploy `azure databricks workspace`

### Modules:
- Provisioning Workspace
- Authentication
- Users and Groups Management
- Cluster Policies & Permissions
- Secure acess to workspace within corporate network (IP Access List)
- Databricks Access Token Management
