***REMOVED*** Azure Databricks SCIM Provisioning Connector Automation

Azure Databricks [SCIM Connector](https://docs.microsoft.com/en-us/azure/databricks/administration-guide/users-groups/scim/aad) allows you to enable Users and Groups synchronization to a Databricks Workspace from Azure Active Directory (Azure AD). Automation process utilizes [Microsoft Graph API’s](https://docs.microsoft.com/en-us/graph/auth/?view=graph-rest-1.0). To call Microsoft Graph, your app must acquire an access token from the Microsoft identity platform. The access token contains information about your app and the permissions it has for the resources and APIs available through Microsoft Graph. To get an access token, your app must be registered with the Microsoft identity platform and be authorized by either a user or an administrator for access to the Microsoft Graph resources it needs.

***REMOVED*** Authentication and authorization steps

The [basic steps](https://docs.microsoft.com/en-us/graph/auth-v2-service?view=graph-rest-1.0) required to configure a service and get a token from the Microsoft identity platform endpoint that your service can use to call Microsoft Graph under its own identity are:

- Register your app (service principal).
- Configure permissions for Microsoft Graph on your app.
- Get administrator consent.
- Get an AAD access token (for the service principal).
- Use the access token to call Microsoft Graph (configure and run SCIM app).

We will be using the OAuth 2.0 [client credentials grant flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-client-creds-grant-flow) to get access tokens from Azure AD to call Microsoft Graph API’s.

***REMOVED*** Register your app

Follow steps mentioned over [here](https://docs.microsoft.com/en-us/graph/auth-v2-service?view=graph-rest-1.0***REMOVED***1-register-your-app). Please note down

- Application (Client) Id
- Directory (Tenant) Id
- Application (Client) Secret

***REMOVED*** Configure permissions for Microsoft Graph on your app

`API Permissions` → `Configured Permissions` → `Add a Permission` → `Microsoft APIs` → `Microsoft Graph` → Select `Application Permissions` and then select the following permissions

- Application.ReadWrite.All
- Application.ReadWrite.OwnedBy
- Directory.ReadWrite.All

***REMOVED*** Get administrator consent

Typically AAD administrators would login to the portal, locate the `app` (service principal just created) → `API permissions` page and `grant admin consent` and after that we’ll be able to use this service principal to automate the SCIM app provisioning.
At this point we have the service principal configured with a required set of permissions, next using Graph APIs we’ll automate the rest of the workflow.

***REMOVED*** Graph API Calls

API Calls used for this automation could be found over [here](https://docs.microsoft.com/en-us/azure/active-directory/develop/active-directory-graph-api). Please download [postman](https://www.postman.com/) client and give this API collection try.
