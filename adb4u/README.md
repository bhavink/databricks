Azure Databricks Security Best Practices
==============
- Documenting and sharing security best practices related to platform deployment and configuration.
- [Security Guide](https://bit.ly/adbsecurityguide)

***REMOVED******REMOVED*** 🚀 New Modular Terraform Structure

This repository provides **production-ready, modular Terraform templates** for Azure Databricks deployments.

***REMOVED******REMOVED******REMOVED*** 📁 Repository Structure

```
adb4u/
├── docs/                      ***REMOVED*** 📚 All documentation centralized here
│   ├── README.md              ***REMOVED*** Documentation index
│   ├── 01-QUICKSTART.md       ***REMOVED*** Quick start guide
│   ├── TROUBLESHOOTING.md     ***REMOVED*** ⚠️ Common issues & solutions
│   ├── DEPLOYMENT-CHECKLIST.md ***REMOVED*** Pre-flight checklist
│   ├── 03-AUTHENTICATION.md   ***REMOVED*** Authentication setup
│   ├── modules/               ***REMOVED*** Module documentation
│   └── patterns/              ***REMOVED*** Pattern-specific guides
│
├── deployments/               ***REMOVED*** Pre-built deployment patterns
│   ├── non-pl/                ***REMOVED*** ✅ Non-Private Link (Ready)
│   ├── full-private/          ***REMOVED*** 🚧 Full Private (Coming soon)
│   └── hub-spoke/             ***REMOVED*** 🚧 Hub-Spoke (Future)
│
├── modules/                   ***REMOVED*** Reusable Terraform modules
│   ├── networking/            ***REMOVED*** VNet, subnets, NSG, NAT
│   ├── workspace/             ***REMOVED*** Databricks workspace
│   └── unity-catalog/         ***REMOVED*** Metastore, storage, credentials
│
└── templates/                 ***REMOVED*** Legacy templates (reference only)
```

***REMOVED******REMOVED******REMOVED*** 🎯 Deployment Patterns

***REMOVED******REMOVED******REMOVED******REMOVED*** 1. **Non-Private Link (Non-PL)** ✅ Production Ready
- **Control Plane**: Public
- **Data Plane**: Private (NPIP)
- **Egress**: NAT Gateway
- **Storage**: Service Endpoints
- **Cost**: ~$58/month

👉 **[Quick Start Guide →](./docs/01-QUICKSTART.md)**  
⚠️ **[Troubleshooting Guide →](./docs/TROUBLESHOOTING.md)** - Review before deploying!

***REMOVED******REMOVED******REMOVED******REMOVED*** 2. **Full Private (Air-gapped)** 🚧 Coming Soon
- **Control Plane**: Private Link
- **Data Plane**: Private (NPIP)
- **Egress**: None (isolated)
- **Storage**: Private Link
- **Cost**: ~$100/month

***REMOVED******REMOVED******REMOVED******REMOVED*** 3. **Hub-Spoke with Firewall** 🚧 Future
- Enterprise-scale multi-workspace deployments

***REMOVED******REMOVED******REMOVED*** ✨ Key Features

- ✅ **Secure Cluster Connectivity (NPIP)**: Always enabled
- ✅ **Unity Catalog**: Mandatory, regional metastore
- ✅ **Flexible Networking**: Create new or BYOV
- ✅ **Service Endpoint Policies**: Enhanced storage security
- ✅ **Modular Design**: Reusable, composable components
- ✅ **Well-Documented**: Comprehensive guides in `/docs`

***REMOVED******REMOVED******REMOVED*** 🚀 Quick Start

```bash
***REMOVED*** Navigate to deployment
cd deployments/non-pl

***REMOVED*** Configure
cp terraform.tfvars.example terraform.tfvars
***REMOVED*** Edit terraform.tfvars with your values

***REMOVED*** Deploy
export TF_VAR_databricks_account_id="<your-account-id>"
terraform init
terraform plan
terraform apply
```

**Full guide:** See [docs/01-QUICKSTART.md](./docs/01-QUICKSTART.md)

***REMOVED******REMOVED******REMOVED*** 📚 Documentation

All documentation is centralized in the **[docs/](./docs/)** folder:

- **[Quick Start Guide](./docs/01-QUICKSTART.md)** - Deploy your first workspace
- **[Authentication Guide](./docs/02-AUTHENTICATION.md)** - Configure credentials
- **[Module Documentation](./docs/modules/)** - Detailed module reference
- **[Pattern Guides](./docs/patterns/)** - Pattern-specific documentation

---

***REMOVED******REMOVED*** Legacy Content (Below)

The following content documents historical best practices and patterns. For new deployments, use the modular structure above.

***REMOVED******REMOVED*** Architecture Overview

```mermaid
graph TB
    subgraph "Corporate Network"
        Users[Users/Developers]
        CorpNet[Corporate VPN/Network]
    end

    subgraph "Azure AD"
        AAD[Azure Active Directory]
        SP[Service Principals]
        Groups[User Groups]
    end

    subgraph "Azure Databricks - Control Plane"
        WebApp[Web Application]
        RestAPI[REST API]
        IPAccess[IP Access Lists]
    end

    subgraph "Azure Databricks - Data Plane VNet"
        Workspace[Databricks Workspace]
        Clusters[Compute Clusters]
        DBFS[DBFS with CMK]
        Notebooks[Notebooks with CMK]
        Secrets[Secret Scopes]
    end

    subgraph "Azure Data Services"
        ADLS[ADLS Gen2]
        KeyVault[Azure Key Vault]
        ADF[Azure Data Factory]
        Synapse[Azure Synapse]
        PowerBI[Power BI]
    end

    Users -->|Authenticate| AAD
    AAD -->|AAD Token| WebApp
    AAD -->|AAD Token| RestAPI
    Users -->|Via| CorpNet
    CorpNet -->|Allowed IPs| IPAccess
    IPAccess --> WebApp
    WebApp --> Workspace
    RestAPI --> Workspace
    Workspace --> Clusters
    Clusters -->|Encrypted| DBFS
    Clusters -->|Encrypted| Notebooks
    Clusters -->|Read Secrets| KeyVault
    Clusters -->|Service Principal/MSI| ADLS
    ADF -->|Orchestrate| Clusters
    Clusters -->|Write Data| Synapse
    PowerBI -->|Query| Clusters
    SP -->|Automate| RestAPI
    Groups -->|Access Control| Workspace

    style AAD fill:***REMOVED***0078D4
    style Workspace fill:***REMOVED***FF3621
    style ADLS fill:***REMOVED***0078D4
    style KeyVault fill:***REMOVED***0078D4
```



Topics
------------

   Ready to use
   ------------
   - **Preventing Data Exfiltration** - Secure Deployments
      - [Deployment walk thru video]()

```mermaid
sequenceDiagram
    participant User
    participant CorpNetwork as Corporate Network
    participant ADB_Control as ADB Control Plane
    participant VNet as Secure VNet
    participant ADB_Data as ADB Data Plane
    participant Storage as Secure Storage

    User->>CorpNetwork: Connect via VPN
    CorpNetwork->>ADB_Control: Access Request (IP Validated)
    ADB_Control->>ADB_Control: Check IP Access List
    ADB_Control->>VNet: Route to Private VNet
    VNet->>ADB_Data: Deploy Cluster (No Public IP)
    ADB_Data->>Storage: Access Data (Private Endpoint)
    Storage-->>ADB_Data: Data Response (No Internet)
    ADB_Data-->>User: Results (Controlled Path)
    Note over ADB_Data,Storage: No public internet access<br/>No data exfiltration possible
```
   -  **Authenticating API calls using AAD tokens** - Securely accessing Azure Databricks REST API using AAD tokens
      - [Video walk thru]()
      - [Using Service Principal AAD Tokens]()

```mermaid
sequenceDiagram
    participant App as Application/Script
    participant AAD as Azure Active Directory
    participant ADB_API as Azure Databricks REST API
    participant Workspace as Databricks Workspace

    App->>AAD: Request AAD Token<br/>(Client ID + Secret/Certificate)
    AAD->>AAD: Validate Credentials
    AAD-->>App: Return Access Token<br/>(Resource: 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d)
    App->>ADB_API: API Call with Bearer Token<br/>(Authorization: Bearer <token>)
    ADB_API->>AAD: Validate Token
    AAD-->>ADB_API: Token Valid + Claims
    ADB_API->>Workspace: Execute Request<br/>(with user/SP identity)
    Workspace-->>ADB_API: Response
    ADB_API-->>App: API Response

    Note over App,AAD: Service Principal or User Identity
    Note over ADB_API,Workspace: No Personal Access Tokens needed
```
   -  **Accessing ADLS Gen2** - options available to read/write data from ADLS Gen2
      - [Demo video]()

```mermaid
sequenceDiagram
    participant User
    participant Cluster as ADB Cluster
    participant AAD as Azure Active Directory
    participant KeyVault as Azure Key Vault
    participant ADLS as ADLS Gen2

    Note over User,ADLS: Option 1: Service Principal with Secrets
    User->>Cluster: Configure spark.conf<br/>(fs.azure.account.auth.type)
    Cluster->>KeyVault: Retrieve SP Credentials
    KeyVault-->>Cluster: Client ID + Secret
    Cluster->>AAD: Request Access Token
    AAD-->>Cluster: OAuth Token
    Cluster->>ADLS: Access Data (Bearer Token)
    ADLS-->>Cluster: Data Response

    Note over User,ADLS: Option 2: Managed Service Identity (MSI)
    User->>Cluster: Enable MSI on Cluster
    Cluster->>AAD: Request Token (MSI Endpoint)
    AAD-->>Cluster: Token (via IMDS)
    Cluster->>ADLS: Access Data with MSI Token
    ADLS-->>Cluster: Data Response

    Note over User,ADLS: Option 3: AAD Passthrough (User Identity)
    User->>Cluster: Enable AAD Passthrough
    Cluster->>AAD: Use User's AAD Token
    Cluster->>ADLS: Access as User Identity
    ADLS-->>Cluster: Data (User Permissions Apply)
```
   -  **Users and Groups Management** - Automate users/groups onboarding and management
      - [Demo video]()

```mermaid
sequenceDiagram
    participant Admin as Admin/Automation
    participant AAD as Azure Active Directory
    participant SCIM as SCIM API
    participant ADB as Databricks Workspace
    participant Groups as User Groups
    participant ACL as Access Controls

    Note over Admin,ACL: Automated User Provisioning via SCIM
    Admin->>AAD: Define Users & Groups
    AAD->>SCIM: Sync via SCIM Connector
    SCIM->>ADB: Provision Users
    SCIM->>Groups: Create/Update Groups
    Groups-->>ADB: Groups Synced

    Note over Admin,ACL: Manual/API-based Management
    Admin->>ADB: Create Group (REST API)
    ADB-->>Admin: Group Created
    Admin->>ADB: Add Users to Group
    Admin->>ACL: Assign Permissions<br/>(Workspace, Clusters, Jobs, etc)
    ACL-->>ADB: Permissions Applied

    Note over Admin,ACL: Access Validation
    Admin->>ADB: User Login
    ADB->>AAD: Validate User
    AAD-->>ADB: User Claims + Group Membership
    ADB->>ACL: Check Permissions
    ACL-->>ADB: Grant Access Based on Groups
    ADB-->>Admin: Access Granted
```

   Work in progress
   ------------

   -  **IP Access List** - Connect to Azure Databricks only through existing corporate networks with a secure perimeter
   -  **Platform tokens** - Manage Azure Databricks platform tokens
   -  **Working with Secrets**
   -  **Bring Your Own Keys (Customer Managed Keys)**
         - DBFS
         - Notebooks
   -  **Securely and Efficiently connect to:**
         - ADF
         - Power BI
         - Synapse DW

```mermaid
graph LR
    subgraph "Network Security"
        IPList[IP Access Lists]
        VPN[Corporate VPN]
    end

    subgraph "Identity & Access"
        Tokens[Platform Token Management]
        AAD2[AAD Authentication]
    end

    subgraph "Data Protection"
        Secrets[Secret Scopes]
        KV2[Azure Key Vault]
        CMK_DBFS[CMK for DBFS]
        CMK_NB[CMK for Notebooks]
    end

    subgraph "Integration Security"
        ADF2[Azure Data Factory]
        PBI[Power BI]
        Synapse2[Azure Synapse]
    end

    VPN -->|Allowed IPs| IPList
    IPList --> AAD2
    AAD2 --> Tokens
    Tokens --> Secrets
    Secrets --> KV2
    KV2 --> CMK_DBFS
    KV2 --> CMK_NB
    AAD2 --> ADF2
    AAD2 --> PBI
    AAD2 --> Synapse2

    style CMK_DBFS fill:***REMOVED***FFD700
    style CMK_NB fill:***REMOVED***FFD700
    style Secrets fill:***REMOVED***90EE90
    style IPList fill:***REMOVED***87CEEB
```

***REMOVED******REMOVED******REMOVED*** Customer Managed Keys (CMK) Flow

```mermaid
sequenceDiagram
    participant Admin as Administrator
    participant AKV as Azure Key Vault
    participant ADB_Control as ADB Control Plane
    participant ADB_Data as ADB Data Plane
    participant DBFS as DBFS Storage
    participant NB as Notebook Storage

    Note over Admin,NB: Setup Phase
    Admin->>AKV: Create Encryption Key
    Admin->>AKV: Grant ADB Access Policy
    Admin->>ADB_Control: Configure CMK<br/>(Key Vault URI + Key Name)
    ADB_Control->>AKV: Validate Access
    AKV-->>ADB_Control: Access Confirmed

    Note over Admin,NB: Runtime Encryption
    ADB_Data->>AKV: Request Encryption Key
    AKV-->>ADB_Data: Return Key
    ADB_Data->>DBFS: Write Data (Encrypted with CMK)
    ADB_Data->>NB: Store Notebook (Encrypted with CMK)

    Note over Admin,NB: Runtime Decryption
    ADB_Data->>AKV: Request Decryption Key
    AKV-->>ADB_Data: Return Key
    ADB_Data->>DBFS: Read Data (Decrypt with CMK)
    ADB_Data->>NB: Load Notebook (Decrypt with CMK)
    DBFS-->>ADB_Data: Decrypted Data
    NB-->>ADB_Data: Decrypted Notebook

    Note over Admin,NB: Key Rotation
    Admin->>AKV: Rotate Key
    AKV->>ADB_Control: Notify Key Update
    ADB_Control->>ADB_Data: Re-encrypt with New Key
```

