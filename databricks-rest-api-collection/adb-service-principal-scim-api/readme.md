# In `Public Preview`

# databricks SCIM api for Service Principals

This documents the endpoints for the [SCIM API](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/scim/scim-sp) for azure [service principals](https://docs.microsoft.com/azure/active-directory/develop/app-objects-and-service-principals).

You can now use AAD user principals as well as AAD service principals as a **first class identity** in azure databricks.
Follow [this](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/aad/service-prin-aad-token) guide to create and configure service principal to use in ADB.

### published [postman collection](https://documenter.getpostman.com/view/2644780/SzmYAMkH) and api doc

### What are the goals?

- Use an Azure AD access token to access the Databricks REST API.
- Automatically add service principal with an "admin" role to ADB
- Add service principal with a "non-admin" role to ADB
- Manage servcie principal entitlements
