# In `Public Preview`

# databricks SCIM API for Users and Groups Management

This documents the endpoints for the [SCIM Users & Groups API](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/scim/).

- Azure Databricks supports SCIM, or System for Cross-domain Identity Management, an open standard that allows you to automate user provisioning using a REST API and JSON. 
- The Azure Databricks SCIM API follows version 2.0 of the SCIM protocol.
- An Azure Databricks administrator can invoke all SCIM API endpoints.
- Non-admin users can invoke the Me Get endpoint, the Users Get endpoint to read user display names and IDs, and the Group Get endpoint to read group display names and IDs.

# Authentication
[To authenticate to Databricks REST APIs, you can use Azure Databricks personal access tokens or Azure Active Directory tokens.](https://docs.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/aad/)

- Section linked above describes how to get, use, and refresh Azure AD tokens. For Azure Databricks personal access tokens, see Authenticate using Azure Databricks personal access tokens.
- Options available:
    - Use the Azure Active Directory Authentication Library (ADAL) to programmatically get an Azure AD access token for a user.
    - Define a service principal in Azure Active Directory and get an Azure AD access token for the service principal rather than a user. You configure the service principal as one on which authentication and authorization policies can be enforced in Azure Databricks. Service principals in an Azure Databricks workspace can have different fine-grained access control than regular users (user principals).

### published [postman collection](https://documenter.getpostman.com/view/2644780/SzmYAMWw) and api doc

### What are the goals?

- Azure Databricks supports SCIM, or System for Cross-domain Identity Management, an open standard that allows you to automate user provisioning using a REST API and JSON. 
- The Azure Databricks SCIM API follows version 2.0 of the SCIM protocol.
