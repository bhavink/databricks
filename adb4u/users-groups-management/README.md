Azure Databricks Users and Groups Onboarding Best Practices
==============
- Documenting and sharing security best practices related to onboarding users and groups in Azure Databricks.
- [Security Guide](https://bit.ly/adbsecurityguide)

Automatic provisioning refers to creating user identities and roles in the cloud applications that users need access to. In addition to creating user identities, automatic provisioning includes the maintenance and removal of user identities as status or roles change.Azure Active Directory (Azure AD) has a gallery that contains pre-integrated application for Databricks workspace which enables you for automatic provisioning with Azure AD.

Two options available
------------

| SCIM Provisioning App (Recommended) | SCIM REST API |
|---|---|
|  Enable provisioning to Azure Databricks using Azure Active Directory (Azure AD) |Enable provisioning to Azure Databricks using Azure Databricks SCIM REST API’s
   |
| Fully Automated
  |
 |Requires manual stitching of API calls which then could be run in an automated fashion
|Guide   | Guide  |
