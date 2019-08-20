***REMOVED******REMOVED*** Provisioning [Azure Databricks workspaces](https://docs.azuredatabricks.net/user-guide/workspace.html) using Service Principals

***REMOVED******REMOVED******REMOVED*** Table of Contents
1. [Prerequisites](***REMOVED***Prerequisites)
2. [Create Service Principal](***REMOVED***Provisioning-Service-Principal-aka-Application)
3. [Download postman](***REMOVED***Download-postman)
4. [Import postman collection](***REMOVED***Import-postman-collection-from-github-repo)
5. [Global variables](***REMOVED***Edit-postman-global-variables)
6. [NSG attached to databricks](***REMOVED***Default-NSG-attached-to-databricks-subnets)
7. [Databricks ARM template](***REMOVED***Databricks-ARM-template)
8. [Working with JSON response](***REMOVED***Extracting-values-out-of-response-body)
9. [API calls](***REMOVED***API-Calls)
10. [Trouble shooting](***REMOVED***Trouble-shooting)
10. [Validating deployment](***REMOVED***Validating-Deployement)


***REMOVED******REMOVED******REMOVED*** Prerequisites

This doc extends the definition of a Service Principal in Azure Active Directory to be used within the realm of Azure Databricks Workspace as a principal, on which authentication/authorization policies can be enforced. The service principals in an Azure Databricks workspace can have different fine grained access control just as regular users (user principals) can. 

For the purpose of this documentation we are assuming that we are using [Service Principals](https://docs.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals) in the [Client](https://docs.microsoft.com/en-us/azure/active-directory/develop/developer-glossary***REMOVED***client-application) Role, and using the [OAuth 2.0 code grant flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v1-protocols-oauth-code) to authenticate to the Azure Databricks resource. 

  - **Pre-create azure resource group** where databricks workspace will be deployed**
  - Create vnet for databricks workspace, if **not present then arm template creates it for you** based on CIDR passed
  - Note: Databricks workspace requires 2 dedicated subnets along with the network security group or NSG attached to these subnets will be created as part of the deployment process, please **do not pre create** them, you can update NSG as per your requirements after the workspace is deployed. Check out CIDR requirements over [here](https://docs.azuredatabricks.net/administration-guide/cloud-configurations/azure/vnet-inject.html***REMOVED***prerequisites)


***REMOVED******REMOVED******REMOVED*** Provisioning Service Principal aka Application

[Use an app identity to access resources](https://docs.microsoft.com/en-us/azure-stack/operator/azure-stack-create-service-principals) covers in detail how you can provision an application (Service Principal) in AAD. 

Here are quicks steps to get you started: 



1. Login to your Azure portal, navigate to Azure Active Directory, App Registrations, New Registrations. You should see a screen similar to this: 


![New App Registrations](https://raw.githubusercontent.com/bhavink/databricks/master/adb-workspace-automation/images/11.png)

<br>(<a href="***REMOVED***">Back to top</a>)
<br>


2. Update API permission, click on "API permissions" and "Add permissions", Select an API , API's my Organization uses and search for "AzureDatabricks"

![API permissions](https://raw.githubusercontent.com/bhavink/databricks/master/adb-workspace-automation/images/13.png)

<br>(<a href="***REMOVED***">Back to top</a>)
<br>


**Select "Delegated Permissions" and make sure that "user impersonation" check box is checked as shown below.**

![Delegate API permission](https://raw.githubusercontent.com/bhavink/databricks/master/adb-workspace-automation/images/14.png)

<br>(<a href="***REMOVED***">Back to top</a>)
<br>

**On the API permissions page, make sure to click "Grant Permissions"**

![Grant permissions](https://raw.githubusercontent.com/bhavink/databricks/master/adb-workspace-automation/images/15.png)

<br>(<a href="***REMOVED***">Back to top</a>)
<br>



3. Once the application is registered, click on “Certificates & secrets” and generate a new client secret. Copy and store that secret in a secure place as this secret is the password for your application. 

![client secret](https://raw.githubusercontent.com/bhavink/databricks/master/adb-workspace-automation/images/12.png)

<br>(<a href="***REMOVED***">Back to top</a>)
<br>

4. Click on “Overview” to look at details like Application(clientId) and Directory (tenant) ID. 

5. **Assign the “Contributor” role to the Service Principal on your Azure Resource**

    Navigate to your Azure Resource Group where you plan to deploy the Databricks workspace, click on the Access Control (IAM) tab and add the “Contributor” role to your service principal. 

![access control](https://raw.githubusercontent.com/bhavink/databricks/master/adb-workspace-automation/images/3.jpg)

<br>(<a href="***REMOVED***">Back to top</a>)
<br>

***REMOVED******REMOVED******REMOVED*** Download postman 
**Download and install it from [here](https://getpostman.com)**


***REMOVED******REMOVED******REMOVED*** Import postman collection from github repo

**git clone [https://github.com/bhavink/databricks.git](https://github.com/bhavink/databricks.git)**

**Collection path within git repo: **adb-workspace-automation/postman-collection/ADB Workspace Automation.postman_collection.json

Import **ADB Workspace Automation.postman_collection.json** file into Postman


![postman collection import](https://raw.githubusercontent.com/bhavink/databricks/master/adb-workspace-automation/images/4.jpg)

<br>(<a href="***REMOVED***">Back to top</a>)
<br>

***REMOVED******REMOVED******REMOVED*** Edit postman global variables

![edit gloabl variables](https://raw.githubusercontent.com/bhavink/databricks/master/adb-workspace-automation/images/5.jpg)

<br>(<a href="***REMOVED***">Back to top</a>)
<br>

**Postman collection global [variables](https://learning.getpostman.com/docs/postman/environments_and_globals/variables/)**

<br>(<a href="***REMOVED***">Back to top</a>)
<br>

<table>
  <tr>
   <td><strong>Variable Name</strong>
   </td>
   <td><strong>Value</strong>
   </td>
   <td><strong>Description</strong>
   </td>
  </tr>
  <tr>
   <td colspan="3" ></td>
  </tr>
  <tr>
   <td colspan="3" ><strong><i>***Azure subscription details***</i></strong>
   </td>
   <tr>
   <td colspan="3" ></td>
  </tr>
  <tr>
   <td><strong>tenantid</strong>
   </td>
   <td>Azure Tenant ID
   </td>
   <td>Locate it <a href="https://techcommunity.microsoft.com/t5/Office-365/How-do-you-find-the-tenant-ID/m-p/89023***REMOVED***M4223">here</a>
   </td>
  </tr>
  <tr>
   <td><strong>subscription_id</strong>
   </td>
   <td>Azure Subscription ID
   </td>
   <td>Locate it <a href="https://portal.azure.com/***REMOVED***blade/Microsoft_Azure_Billing/SubscriptionsBlade">here</a>
   </td>
  </tr>
  <tr>
   <td><strong>client_secret</strong>
   </td>
   <td>Service Principal ID
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td><strong>client_id</strong>
   </td>
   <td>Service Principal Secret
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td><strong>azure_region</strong>
   </td>
   <td>Azure region, ex: <strong>eastus2</strong>
   </td>
   <td>Region where Databricks is deployed
   </td>
  </tr>
  <tr>
   <td><strong>resource_group</strong>
   </td>
   <td>Resource group name
   </td>
   <td>User defined resource group 
   </td>
  </tr>
  <tr>
   <td colspan="3" ></td>
  </tr>
  <tr>
   <td colspan="3" ><strong><i>***Constant’s used***</i></strong>
   </td>
  </tr>
  <tr>
   <td colspan="3" ></td>
  </tr>
  <tr>
   <td><strong>resource</strong>
   </td>
   <td><strong>2ff814a6-3304-4ab8-85cb-cd0e6f879c1d</strong>
   </td>
   <td><strong>Constant,</strong> Azure Databricks Resource ID within azure
   </td>
  </tr>
  <tr>
   <td><strong>management_resource_endpoint</strong>
   </td>
   <td><strong>https://management.core.windows.net/</strong>
   </td>
   <td><strong>Constant</strong>, more details <a href="https://docs.microsoft.com/en-us/azure/role-based-access-control/resource-provider-operations">here</a> 
   </td>
  </tr>
  <tr>
   <td colspan="3" ></td>
  </tr>
  <tr>
   <td colspan="3" ><strong><i>***Databricks deployment via ARM template specific variables***</i></strong>
   </td>
  </tr>
  <tr>
   <td colspan="3" ></td>
  </tr>
  <tr>
   <td><strong>resource_deployment_name</strong>
   </td>
   <td>Ex: <strong>adb-prd-deployment-try1</strong>
   </td>
   <td>unique name given to the ARM deployment
   </td>
  </tr>
  <tr>
   <td><strong>databricks_workspace_name</strong>
   </td>
   <td>Ex: <strong>adb-prd-workspace1</strong>
   </td>
   <td>unique name given to the azure databricks workspace
   </td>
  </tr>
  <tr>
   <td><strong>databricks_vnet_cidr</strong>
   </td>
   <td>Ex: <strong>11.139.13.0/24</strong>
   </td>
   <td>More details <a href="https://docs.azuredatabricks.net/administration-guide/cloud-configurations/azure/vnet-inject.html***REMOVED***prerequisites">here</a>
   </td>
  </tr>
  <tr>
   <td><strong>databricks_vnet_name</strong>
   </td>
   <td>Ex: <strong>adb-prd-vnet1</strong>
   </td>
   <td>unique name given to the vnet where ADB is deployed, if a vnet exists we will use it, otherwise it will create a new one.
   </td>
  </tr>
  <tr>
   <td><strong>databricks_host_subnet_name</strong>
   </td>
   <td>Ex: <strong>adb-prd-host-sub</strong>
   </td>
   <td>unique name given to the subnet within the vnet where ADB is deployed. <strong>We highly recommend that you let ARM template create this subnet</strong> rather than you pre creating it.
   </td>
  </tr>
  <tr>
   <td><strong>databricks_host_subnet_cidr</strong>
   </td>
   <td>Ex: <strong>11.139.13.64/26</strong>
   </td>
   <td>More details <a href="https://docs.azuredatabricks.net/administration-guide/cloud-configurations/azure/vnet-inject.html***REMOVED***prerequisites">here</a>
   </td>
  </tr>
  <tr>
   <td><strong>databricks_container_subnet_name</strong>
   </td>
   <td>Ex: <strong>adb-prd-cntr-sub</strong>
   </td>
   <td>unique name given to the subnet within the vnet where ADB is deployed. <strong>We highly recommend that you let ARM template create this subnet</strong> rather than you pre creating it.
   </td>
  </tr>
  <tr>
   <td><strong>databricks_container_subnet_cidr</strong>
   </td>
   <td>Ex: <strong>11.139.13.128/26</strong>
   </td>
   <td>More details <a href="https://docs.azuredatabricks.net/administration-guide/cloud-configurations/azure/vnet-inject.html***REMOVED***prerequisites">here</a>
   </td>
  </tr>
  <tr>
   <td><strong>databricks_nsg_name</strong>
   </td>
   <td>Ex: <strong>adb-prd-workspace1-nsg</strong>
   </td>
   <td>Network Security Group attached to databricks subnets.
   </td>
  </tr>
  <tr>
   <td><strong>databricks_pricing_tier</strong>
   </td>
   <td>Ex: <strong>premium</strong>
   </td>
   <td>Options available <strong>premium</strong> or <strong>standard</strong> , more details <a href="https://databricks.com/product/azure-pricing">here</a>
   </td>
  </tr>
  <tr>
   <td><strong>databricks_enable_no_public_ip</strong>
   </td>
   <td>Ex: <strong>[bool('false')]</strong>
   </td>
   <td>Spin databricks clusters with <strong>public</strong> ip or <strong>private</strong> ip only.
   </td>
  </tr>
</table>


***REMOVED******REMOVED******REMOVED*** Default NSG attached to databricks subnets

![NSG attached to databricks](https://raw.githubusercontent.com/bhavink/databricks/master/adb-workspace-automation/images/7.png)

<br>(<a href="***REMOVED***">Back to top</a>)
<br>

***REMOVED******REMOVED******REMOVED*** Databricks ARM template

[ARM templates](https://docs.azuredatabricks.net/administration-guide/cloud-configurations/azure/vnet-inject.html***REMOVED***advanced-configuration-using-arm-templates) are utilized in order to deploy databricks workspace, it’s used as a payload body in step ***REMOVED***2 - **_<span style="text-decoration:underline;">deploy databricks using arm template</span>_** ,  we use this template to deploy databricks in a custom vnet i.e. customers own VNET, template is parameterized via global variables set at collection level. We highly recommend that you do not pre create subnets required by databricks workspace and let the arm template create it as part of the deployment process, you have to supply subnet address space, databricks workspace will be deployed with your vnet and a default Network Security Group will be created as per the routes shown earlier and attached to both subnets used by databricks.

```
 "parameters": {
     "workspaceName": {
       "value": "{{databricks_workspace_name}}"
     },
     "pricingTier":{
       "value":"{{databricks_pricing_tier}}"
     },
     "nsgName":{
       "value":"{{databricks_nsg_name}}"
     },
     "vnetName":{
       "value":"{{databricks_vnet_name}}"
     },
     "vnetCidr":{
       "value":"{{databricks_vnet_cidr}}"
     },
     "privateSubnetName":{
       "value":"{{databricks_container_subnet_name}}"
     },
     "publicSubnetName":{
       "value":"{{databricks_host_subnet_name}}"
     },
     "privateSubnetCidr":{
       "value":"{{databricks_container_subnet_cidr}}"
     },
     "publicSubnetCidr":{
       "value":"{{databricks_host_subnet_cidr}}"
     }
```

<br>(<a href="***REMOVED***">Back to top</a>)
<br>

***REMOVED******REMOVED******REMOVED*** Extracting values out of response body


Each API call has a test script which sets variables which are then used by subsequent calls. In this example we are setting the “managment_token” variable based on the “access_token” received in the JSON response.
```
pm.test(pm.info.requestName, () => {
    pm.response.to.not.be.error;
    pm.response.to.not.have.jsonBody('error');
});
pm.globals.set("**management_token**",pm.response.json().**access_token**);
```

<br>(<a href="***REMOVED***">Back to top</a>)
<br>

***REMOVED******REMOVED******REMOVED*** API Calls

The following API based workflow uses Azure service to service calls using the OAuth 2.0 client credentials workflow. More details can be found [here](https://docs.microsoft.com/en-us/azure/active-directory/develop/v1-oauth2-client-creds-grant-flow).


<table>
  <tr>
   <td><strong>API name</strong>
   </td>
   <td><strong>Description</strong>
   </td>
  </tr>
  <tr>
   <td colspan="2" ><strong>Create databricks workspace</strong>
   </td>
  </tr>
  <tr>
   <td>1-get azure management token
   </td>
   <td>Create azure resource management token
   </td>
  </tr>
  <tr>
   <td>2-deploy databricks via arm template
   </td>
   <td>Provisions the Databricks workspace using token generated in ***REMOVED***1 and <a href="https://docs.microsoft.com/en-us/azure/role-based-access-control/resource-provider-operations***REMOVED***microsoftdatabricks">azure resource management</a> API’s and ARM template provided as part of request body.
<p>
Check deployment status using subsequent call - 2.1-check deployment status ,  API uses “<strong>{{resource_deployment_name}}</strong>” set at collection level to get status updates.
<p>
Please note that it takes approximately <strong>10-15 minutes for the Databricks workspace resource </strong>to be provisioned in background.
   </td>
  </tr>
  <tr>
   <td colspan="2" ><strong>Initialize databricks workspace</strong>
   </td>
  </tr>
  <tr>
   <td>3-get an access token for the Databricks resource
   </td>
   <td>Create AAD access token
   </td>
  </tr>
  <tr>
   <td>4-get an access token for the management resource.
   </td>
   <td>Create Azure Resource Management token
   </td>
  </tr>
  <tr>
   <td>5-list node types
   </td>
   <td>Make a <strong>“test”</strong> call to Databricks API using access_token, management_token and adb_workspace_resource_id, this is a required step.
   </td>
  </tr>
  <tr>
   <td colspan="2" ><strong>At this step you have successfully created and launched a databricks workspace using service principal based workflow.</strong>
   </td>
  </tr>
  <tr>
   <td colspan="2" >Subsequent API calls are here to walk you thru additional steps like onboarding User Groups, adding users to groups, setting access control, generating databricks platform token [PAT] and so on using PAT as well as service principal workflow.
   </td>
  </tr>
</table>

<br>(<a href="***REMOVED***">Back to top</a>)
<br>


***REMOVED******REMOVED******REMOVED*** Trouble shooting

Expired tokens you may get errors like this

```
<pre>    Error while parsing token: io.jsonwebtoken.ExpiredJwtException: JWT expired at 2019-08-08T13:28:46Z. Current time: 2019-08-08T16:19:10Z, a difference of 10224117 milliseconds.  Allowed clock skew: 0 milliseconds.</pre></p>
```


Please rerun steps 3 and 4 to regenerate access and management tokens and try again.


<table>
  <tr>
   <td>3-get an access token for the Databricks resource
   </td>
  </tr>
  <tr>
   <td>4-get an access token for the management resource.
   </td>
  </tr>
</table>

<br>(<a href="***REMOVED***">Back to top</a>)
<br>

***REMOVED******REMOVED******REMOVED*** Validating Deployement

While invoking the test API call, “list-node types”, Databricks REST API, if you **run into API timeout issues** then please check that

  - You are using up-to-date global variables.
  - Access tokens not expired
  - Check out Azure monitor → Activity logs to make sure that the workspace is deployed successfully. You can filter events by "Event initiated" = "service principal used" filter



![validate databricks deployment](https://raw.githubusercontent.com/bhavink/databricks/master/adb-workspace-automation/images/9.jpg)

<br>(<a href="***REMOVED***">Back to top</a>)
<br>
