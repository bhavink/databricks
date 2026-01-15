# How Databricks Accesses Your Cloud

**The Problem:** You're confused about how Databricks actually gets into your AWS/Azure/GCP account to create workspaces and access storage. Terms like "cross-account role," "first-party app," and "service account" are flying around and you just want to understand what's happening.

**This Guide:** Explains in simple terms how Databricks identities work across clouds, why each cloud is different, and how your data stays secure.

---

## Table of Contents

**Quick Navigation:**

- [The Big Picture](#the-big-picture) - Understand the core concept
- [Quick Visual Overview](#quick-visual-overview) - Decision flow diagram
- **Cloud-Specific Details:**
  - [AWS: The "Temporary Key" Model](#aws-the-temporary-key-model)
  - [Azure: The "First-Party App" Model](#azure-the-first-party-app-model)
  - [GCP: The "Service Account" Model](#gcp-the-service-account-model)
- [Unity Catalog: The Universal Data Governance Layer](#unity-catalog-the-universal-data-governance-layer)
- [Security: Why This Design Is Safe](#security-why-this-design-is-safe)
- [Common Questions](#common-questions)
- [Comparison: All Three Clouds](#comparison-all-three-clouds)
- [Visual Summary](#visual-summary)
- [Next Steps](#next-steps)

---

## The Big Picture

Think of Databricks as a **construction company** that needs to build a house (workspace) on your property (cloud account).

**The Question:** How do you give them access without handing over the keys to your entire property?

**The Answer:** Each cloud has a different way of handling this:
- **AWS**: Databricks "borrows" temporary credentials (AssumeRole)
- **Azure**: Databricks is a trusted neighbor with a master key (First-party app)
- **GCP**: Databricks creates a worker who you approve (Service Account)

Let's break down each one...

---

## Quick Visual Overview

```mermaid
flowchart TB
    subgraph "Your Decision"
        Q{Which cloud are you using?}
    end
    
    Q -->|AWS| AWS[AWS: Cross-Account Role<br/>Databricks assumes temporary credentials]
    Q -->|Azure| AZ[Azure: First-Party App<br/>Databricks has built-in access]
    Q -->|GCP| GCP[GCP: Service Account<br/>Databricks creates identity in your account]
    
    AWS --> AWSDetails[You create IAM role<br/>Databricks assumes it<br/>You control via trust policy]
    AZ --> AZDetails[Azure trusts Databricks automatically<br/>You control via RBAC<br/>No setup needed]
    GCP --> GCPDetails[Databricks creates GSA<br/>You grant permissions<br/>You control via IAM]
    
    style AWS fill:#FF9900,color:#000
    style AZ fill:#0078D4,color:#fff
    style GCP fill:#4285F4,color:#fff
```

---

## AWS: The "Temporary Key" Model

### How It Works

Imagine you hire a contractor. Instead of giving them a permanent key, you:
1. Create a special lockbox (IAM role) that opens your door
2. Tell the lockbox "only the contractor can use this" (trust policy)
3. The contractor uses it when needed, but it expires (temporary credentials)

```mermaid
sequenceDiagram
    participant You as You<br/>(Your AWS Account)
    participant DB as Databricks<br/>(Account 414351767826)
    participant IAM as AWS IAM
    participant Resources as AWS Resources<br/>(EC2, VPC, S3)
    
    Note over You,DB: Setup Phase
    You->>IAM: 1. Create Cross-Account Role
    You->>IAM: 2. Set trust policy:<br/>"Only Databricks can use this"
    You->>IAM: 3. Attach permissions:<br/>"Can launch EC2, access S3"
    
    Note over You,DB: Workspace Creation
    DB->>IAM: 4. AssumeRole (with external ID)
    IAM->>IAM: Verify: Is this really Databricks?
    IAM->>DB: ✅ Here are temporary credentials<br/>(valid for 1 hour)
    
    DB->>Resources: 5. Create workspace using temp creds
    DB->>Resources: Launch EC2 instances
    DB->>Resources: Configure VPC/subnets
    DB->>Resources: Access S3 buckets
    
    Note over DB,Resources: Credentials expire automatically
```

### The Roles You Create

You create **multiple roles** for different purposes:

```mermaid
flowchart TD
    subgraph "Databricks Control Plane<br/>Account: 414351767826"
        DB[Databricks SaaS]
    end
    
    subgraph "Your AWS Account"
        subgraph "Workspace Management"
            CROSS[Cross-Account Role<br/>Manages workspace infrastructure]
            STORAGE[Storage Config Role<br/>Accesses DBFS root bucket]
        end
        
        subgraph "Unity Catalog Management"
            UCMETA[UC Metastore Role<br/>Shared across workspaces]
            UCEXT[UC External Role<br/>Per-workspace storage]
        end
        
        subgraph "Cluster Access"
            INSTANCE[Instance Profile<br/>Data access for clusters]
        end
    end
    
    DB -.->|AssumeRole| CROSS
    DB -.->|AssumeRole| STORAGE
    DB -.->|AssumeRole| UCMETA
    DB -.->|AssumeRole| UCEXT
    
    CROSS -->|Launch/Configure| EC2[EC2 Instances]
    STORAGE -->|Read/Write| S3DBFS[DBFS Root S3 Bucket]
    UCMETA -->|Read/Write| S3META[Metastore S3 Bucket]
    UCEXT -->|Read/Write| S3EXT[External S3 Buckets]
    INSTANCE -->|Attached to| EC2
    
    style DB fill:#FF3621,color:#fff
    style CROSS fill:#FF9900,color:#000
    style STORAGE fill:#FF9900,color:#000
    style UCMETA fill:#1B72E8,color:#fff
    style UCEXT fill:#1B72E8,color:#fff
    style INSTANCE fill:#34A853,color:#fff
```

### What Each Role Does

| Role | Purpose | Who Uses It | When Created |
|------|---------|-------------|--------------|
| **Cross-Account Role** | Creates workspace, launches clusters, manages VPC | Databricks control plane | Before workspace |
| **Storage Config Role** | Accesses DBFS root bucket (workspace files) | Databricks control plane | Before workspace |
| **UC Metastore Role** | Accesses Unity Catalog shared storage | Databricks control plane | Before metastore |
| **UC External Role** | Accesses workspace-specific catalog storage | Databricks control plane | During UC setup |
| **Instance Profile** | Gives clusters access to your data | Cluster VMs | Before clusters run |

### Trust Policy: The Security Gate

Every role has a **trust policy** that says "who can use this role":

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::414351767826:root"
    },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {
        "sts:ExternalId": "your-databricks-account-id"
      }
    }
  }]
}
```

**What this means in English:**
- "Let Databricks (account `414351767826`) use this role"
- "But ONLY if they prove they have the right external ID"
- "That external ID is YOUR Databricks account ID"

**Why it's secure:**
- Databricks can't use this role for other customers
- Only YOUR Databricks account can use it
- Credentials expire automatically (temporary)
- You can revoke access anytime by deleting the role

### Unity Catalog Storage Access

Unity Catalog uses a special pattern with an **external_id** for extra security:

```mermaid
sequenceDiagram
    participant You as Your AWS Account
    participant TF as Terraform
    participant DB as Databricks
    participant S3 as S3 Bucket
    
    Note over You,S3: Setup Flow
    You->>TF: 1. Create storage credential<br/>(with placeholder role)
    TF->>DB: 2. Register credential
    DB->>DB: 3. Generate unique external_id
    DB->>TF: 4. Return external_id
    
    TF->>You: 5. Create IAM role with trust policy<br/>(including external_id)
    TF->>You: 6. Attach S3 permissions
    TF->>DB: 7. Update credential with real role ARN
    
    Note over You,S3: Access Flow
    DB->>You: 8. AssumeRole (with external_id)
    You->>You: Verify external_id matches
    You->>DB: ✅ Temporary credentials
    DB->>S3: 9. Access S3 data
```

**Why the external_id?**
- **Prevents confused deputy attack**: Another Databricks customer can't trick Databricks into accessing YOUR data
- **Unique per credential**: Each storage credential gets its own external_id
- **Auto-generated**: You don't pick it, Databricks does

---

## Azure: The "First-Party App" Model

### How It Works

Azure Databricks is **built into Azure** - it's not a separate company accessing your account. Think of it like this:

Imagine Azure is an apartment building:
- You rent an apartment (subscription)
- Databricks is the building's official maintenance service
- The building owner (Microsoft) already gave Databricks a master key
- You control what Databricks can access using apartment rules (RBAC)

```mermaid
sequenceDiagram
    participant You as You<br/>(Azure Subscription)
    participant SP as Service Principal<br/>(Your automation)
    participant ARM as Azure Resource Manager
    participant DB as Azure Databricks<br/>(First-party service)
    participant Resources as Azure Resources<br/>(VNet, Storage)
    
    Note over You,DB: You create workspace (not Databricks)
    You->>SP: 1. Give SP permissions<br/>(Contributor role)
    SP->>ARM: 2. Create Databricks workspace
    ARM->>ARM: 3. Provision managed resource group
    ARM->>DB: 4. Deploy Databricks control plane
    DB->>Resources: 5. Create managed resources<br/>(automatically trusted)
    
    Note over DB,Resources: Databricks accesses resources<br/>using Azure's built-in trust
    DB->>Resources: Configure VNet injection
    DB->>Resources: Access storage accounts
    DB->>Resources: Create private endpoints
```

### Key Differences from AWS

| Aspect | AWS | Azure |
|--------|-----|-------|
| **Who creates workspace** | Databricks (via API) | You (via Azure Portal/Terraform) |
| **Identity setup** | You create cross-account role | Nothing - it's built-in |
| **Trust mechanism** | AssumeRole with external ID | First-party app (trusted by Azure) |
| **Resource management** | Databricks manages in its account | Resources in YOUR subscription |
| **Managed resource group** | Doesn't exist | Auto-created by Azure |

### What You Create

```mermaid
flowchart TD
    subgraph "Your Subscription"
        subgraph "Resources You Control"
            RG[Resource Group]
            WS[Databricks Workspace]
            VNET[VNet/Subnets]
            STORAGE[Storage Accounts]
        end
        
        subgraph "Managed Resource Group<br/>(Azure creates, Databricks uses)"
            NSG[Network Security Groups]
            LB[Load Balancers]
            VMS[Worker VMs]
            DISKS[Managed Disks]
        end
        
        subgraph "Service Principal<br/>(Your automation identity)"
            SP[Service Principal<br/>Used by Terraform]
        end
    end
    
    SP -->|Contributor role| RG
    RG -->|Contains| WS
    RG -->|Contains| VNET
    RG -->|Contains| STORAGE
    
    WS -->|Auto-creates| NSG
    WS -->|Auto-creates| LB
    WS -->|Launches| VMS
    WS -->|Creates| DISKS
    
    style SP fill:#0078D4,color:#fff
    style WS fill:#FF3621,color:#fff
```

### Unity Catalog Storage Access

Azure uses **Managed Identities** instead of service principals for UC:

```mermaid
sequenceDiagram
    participant You as Your Subscription
    participant WS as Databricks Workspace
    participant MI as Managed Identity<br/>(Auto-created)
    participant Storage as Storage Account
    
    Note over You,Storage: Setup
    You->>WS: 1. Create Unity Catalog<br/>storage credential
    WS->>MI: 2. Create managed identity<br/>(access connector)
    WS->>You: 3. Return MI principal ID
    You->>Storage: 4. Grant MI permissions<br/>(Storage Blob Data Contributor)
    
    Note over You,Storage: Access
    WS->>MI: 5. Request token
    MI->>Storage: 6. Access blob storage<br/>(using token)
```

**Why Managed Identity?**
- **No secrets to manage**: No passwords or keys
- **Automatic rotation**: Azure handles credential lifecycle
- **Built-in audit trail**: All access logged in Azure AD

### What Access Connector Does

The **Access Connector** is a special Azure resource that holds the managed identity:

```
Access Connector = Managed Identity Wrapper
```

It lets Databricks:
- Access Azure Data Lake Storage (ADLS Gen2)
- Access storage accounts for Unity Catalog
- Use Azure Key Vault for secrets
- Connect to other Azure services

**You create it once**, reuse it across:
- Multiple workspaces
- Multiple storage credentials
- Multiple Unity Catalog metastores

---

## GCP: The "Service Account" Model

### How It Works

GCP has a unique model where Databricks creates a **service account IN YOUR PROJECT**:

Imagine hiring a new employee:
1. Databricks "hires" someone to work in your office (creates GSA in your project)
2. You decide what this employee can access (grant IAM permissions)
3. The employee works on Databricks' behalf but lives in your org

```mermaid
sequenceDiagram
    participant You as Your GCP Project
    participant DB as Databricks<br/>(accounts.gcp.databricks.com)
    participant GSA as Service Account<br/>(Created by Databricks)
    participant Resources as GCP Resources<br/>(GCS, Compute)
    
    Note over You,DB: Workspace Creation
    You->>DB: 1. Request workspace creation
    DB->>You: 2. Create service account<br/>databricks-compute@project.iam
    DB->>You: 3. This GSA represents Databricks
    
    You->>GSA: 4. Grant permissions<br/>(Compute Admin, Storage Admin)
    
    Note over DB,Resources: Databricks Uses GSA
    DB->>GSA: 5. Impersonate GSA
    GSA->>Resources: 6. Create Compute Engine VMs
    GSA->>Resources: 7. Access GCS buckets
    GSA->>Resources: 8. Configure VPC
```

### The Service Account Pattern

GCP has **MULTIPLE service accounts** working together - some in YOUR project, some in Databricks' project:

```mermaid
flowchart TD
    subgraph DBXProj[Databricks Control Plane Project]
        WS_SA[Workspace SA<br/>Manages workspace infrastructure]
        DELEGATE[Delegate SA<br/>Launches GCE clusters]
        UC_SA[Unity Catalog Storage SA<br/>UC data access]
    end
    
    subgraph YourProj[Your GCP Project]
        subgraph CustomerGSA[Customer-Created GSAs]
            YOUR_SA[Terraform GSA<br/>You create this for Terraform]
        end
        
        subgraph DBXCreatedGSA[Databricks-Created GSAs]
            COMPUTE[Compute SA<br/>Attached to cluster VMs]
        end
        
        subgraph Resources
            VPC[VPC Networks]
            VM[GCE Instances]
            GCS[GCS Buckets]
        end
    end
    
    YOUR_SA -->|Impersonated by Databricks provider| WS_SA
    WS_SA -->|Validates/Creates| COMPUTE
    WS_SA -->|Configures| VPC
    DELEGATE -->|Launches| VM
    VM -->|Has attached| COMPUTE
    COMPUTE -->|Accesses| GCS
    UC_SA -->|Accesses UC-managed storage| GCS
    
    style WS_SA fill:#FF3621,color:#fff
    style DELEGATE fill:#FF9900,color:#000
    style UC_SA fill:#1B72E8,color:#fff
    style YOUR_SA fill:#FBBC04,color:#000
    style COMPUTE fill:#4285F4,color:#fff
```

### Who Creates What and Why

The key to understanding GCP is knowing **which GSA lives where and who creates it**:

#### GSAs in Databricks' Control Plane (They Create & Own)

**1. Workspace SA** - `db-{workspaceid}@prod-gcp-{region}.iam.gserviceaccount.com`
- **Purpose**: Manages your workspace infrastructure
- **Created**: Automatically when workspace is created
- **Lives in**: Databricks' GCP project (not yours)
- **What it does**: Validates and creates the Compute SA in your project, configures VPC, manages workspace resources
- **Permissions**: Uses three custom roles auto-created by Databricks:
  - **Databricks Project Role v2**: Project-level permissions
  - **Databricks Resource Role v2**: Workspace-scoped with IAM condition
  - **Databricks Network Role v2**: VPC network permissions
  - [Full details](https://docs.databricks.com/gcp/en/admin/cloud-configurations/gcp/permissions#required-permissions-for-the-workspace-service-account)

**2. Delegate SA** - `delegate-sa@prod-gcp-{region}.iam.gserviceaccount.com`
- **Purpose**: Launches GCE cluster instances
- **Created**: Pre-existing (one per region)
- **Lives in**: Databricks' GCP project
- **What it does**: Creates and manages Compute Engine VMs for clusters

**3. Unity Catalog Storage SA** - `db-uc-storage-UUID@uc-{region}.iam.gserviceaccount.com`
- **Purpose**: Unity Catalog data access
- **Created**: When you set up Unity Catalog
- **Lives in**: Databricks' UC project
- **What it does**: Accesses GCS buckets for Unity Catalog with scoped, short-lived tokens

#### GSAs in Your Project (You Control Permissions)

**4. Compute SA** - `databricks-compute@{your-project}.iam.gserviceaccount.com`
- **Purpose**: Default identity attached to every cluster VM
- **Created**: Automatically by Databricks Workspace SA (or you can pre-create it)
- **Lives in**: YOUR GCP project
- **What it does**: Cluster VMs use this to access GCS, write logs, send metrics
- **Minimum permissions** (auto-granted): `roles/logging.logWriter` + `roles/monitoring.metricWriter`
- **Additional permissions**: You grant based on data access needs (e.g., Storage Object Viewer)

**5. Terraform/Automation SA** - `terraform-automation@{your-project}.iam.gserviceaccount.com`
- **Purpose**: Used by Terraform to create workspace
- **Created**: By you
- **Lives in**: YOUR GCP project
- **What it does**: Databricks Terraform provider impersonates this to call Databricks APIs
- **Permissions**: `roles/owner` on workspace and VPC projects (simplest), or custom role with [workspace creator permissions](https://docs.databricks.com/gcp/en/admin/cloud-configurations/gcp/permissions#required-permissions-for-the-workspace-creator)

### The Key Difference

Unlike AWS (where YOU create all IAM roles) or Azure (where it's built-in), GCP uses a **hybrid model**:
- Databricks **creates GSAs in THEIR projects** (Workspace SA, Delegate SA, UC SA)
- Databricks **creates GSAs in YOUR project** (Compute SA)
- You **grant permissions** to Databricks' GSAs to access your resources
- You **create your own GSA** for Terraform automation

### How Workspace Creation Works

```mermaid
sequenceDiagram
    participant You as Your Terraform<br/>(using your GSA)
    participant DB as Databricks<br/>Control Plane
    participant WS_SA as Workspace SA<br/>(Databricks project)
    participant Your_Proj as Your GCP Project
    participant Compute_SA as Compute SA<br/>(Your project)
    
    Note over You,Your_Proj: Workspace Creation
    You->>DB: 1. Create workspace<br/>(impersonate your GSA)
    DB->>WS_SA: 2. Create Workspace SA<br/>(in Databricks project)
    WS_SA->>Your_Proj: 3. Validate project access
    WS_SA->>Compute_SA: 4. Create Compute SA<br/>(in your project)
    WS_SA->>Your_Proj: 5. Grant Compute SA roles<br/>(log writer, metric writer)
    WS_SA->>Your_Proj: 6. Validate VPC configuration
    DB->>You: 7. Workspace ready!
    
    Note over You,Your_Proj: Cluster Launch
    You->>DB: 8. Launch cluster
    WS_SA->>Your_Proj: 9. Create GCE instances
    Your_Proj->>Compute_SA: 10. Attach Compute SA to VMs
```

### What Each GSA Does

| Service Account | Lives In | Created By | Purpose | Permissions You Grant |
|-----------------|----------|------------|---------|----------------------|
| **Workspace SA**<br/>`db-{wsid}@prod-gcp-{region}.iam` | Databricks project | Databricks | Manage workspace infra | Custom roles (auto-created):<br/>- Databricks Project Role v2<br/>- Databricks Resource Role v2 |
| **Delegate SA**<br/>`delegate-sa@prod-gcp-{region}.iam` | Databricks project | Databricks (pre-existing) | Launch GCE clusters | Permissions granted via custom roles |
| **Compute SA**<br/>`databricks-compute@project.iam` | Your project | Databricks Workspace SA | Cluster VM identity | Roles you grant:<br/>- Logging Log Writer<br/>- Monitoring Metric Writer |
| **UC Storage SA**<br/>`db-uc-storage-UUID@uc-{region}.iam` | Databricks UC project | Databricks | Unity Catalog storage | Storage Object Admin on UC buckets |
| **Your Terraform SA**<br/>`terraform-automation@project.iam` | Your project | You | Terraform automation | Owner or custom role with workspace creation permissions |

### Unity Catalog Storage Access

GCP Unity Catalog uses a **Databricks-managed GSA** pattern:

```mermaid
sequenceDiagram
    participant You as Your GCP Project
    participant WS as Databricks Workspace
    participant DBGSA as Databricks GSA<br/>(Databricks-owned account)
    participant GCS as GCS Bucket
    
    Note over You,GCS: Setup
    You->>WS: 1. Create storage credential
    WS->>WS: 2. Generate Databricks-managed GSA email
    WS->>You: 3. Return GSA email
    You->>GCS: 4. Grant GSA permissions<br/>(Storage Object Admin)
    
    Note over You,GCS: Access
    WS->>DBGSA: 5. Use Databricks GSA
    DBGSA->>GCS: 6. Access bucket
    
    Note over DBGSA,GCS: The GSA lives in Databricks' GCP<br/>project, not yours
```

**Key Point:** For Unity Catalog, the service account is **created by Databricks in their GCP project**, but you **grant it permissions** in your project.

This is different from workspace compute, where the GSA lives in YOUR project.

### Shared VPC Scenario

If you use **Shared VPC** (common in enterprises), there's another layer:

```mermaid
flowchart TD
    subgraph "Host Project<br/>(Centralized networking)"
        SHARED_VPC[Shared VPC]
        SUBNETS[Subnets]
    end
    
    subgraph "Service Project<br/>(Your Databricks workspace)"
        GSA[databricks-compute GSA]
        VM[Compute VMs]
    end
    
    subgraph "Permissions Required"
        HOST_PERMS[Host project IAM:<br/>Compute Network User]
        SERVICE_PERMS[Service project IAM:<br/>Compute Admin]
    end
    
    GSA -->|Needs| HOST_PERMS
    GSA -->|Needs| SERVICE_PERMS
    GSA -->|Attached to| VM
    VM -->|Uses| SHARED_VPC
    VM -->|Deploys into| SUBNETS
    
    style SHARED_VPC fill:#4285F4,color:#fff
    style GSA fill:#34A853,color:#fff
```

---

## Unity Catalog: The Universal Data Governance Layer

Unity Catalog works **the same across all clouds**, but accesses storage differently:

### The Three-Part Pattern

```mermaid
flowchart LR
    subgraph "1. Identity"
        AWS_ROLE[AWS: IAM Role]
        AZURE_MI[Azure: Managed Identity]
        GCP_GSA[GCP: Service Account]
    end
    
    subgraph "2. Storage Credential"
        SC[Storage Credential<br/>Links identity to Databricks]
    end
    
    subgraph "3. External Location"
        EL[External Location<br/>Maps to actual storage path]
    end
    
    subgraph "4. Catalog/Schema/Table"
        CAT[Catalog]
        SCHEMA[Schema]
        TABLE[Table]
    end
    
    AWS_ROLE -->|Registered in| SC
    AZURE_MI -->|Registered in| SC
    GCP_GSA -->|Registered in| SC
    
    SC -->|Used by| EL
    EL -->|Storage for| CAT
    CAT -->|Contains| SCHEMA
    SCHEMA -->|Contains| TABLE
    
    style SC fill:#FF6B35,color:#fff
    style EL fill:#004E89,color:#fff
    style CAT fill:#1B9AAA,color:#fff
```

### How Each Cloud Handles UC Storage

#### AWS: IAM Role with External ID

```mermaid
sequenceDiagram
    participant UC as Unity Catalog
    participant Role as IAM Role<br/>(In your account)
    participant S3 as S3 Bucket
    
    UC->>Role: 1. AssumeRole<br/>(with external_id)
    Role->>Role: 2. Verify external_id
    Role->>UC: 3. Temporary credentials
    UC->>S3: 4. Access data
```

**Created by:** You (via Terraform)  
**Trust:** AssumeRole with external_id  
**Permissions:** S3 GetObject, PutObject, ListBucket

#### Azure: Managed Identity (Access Connector)

```mermaid
sequenceDiagram
    participant UC as Unity Catalog
    participant MI as Managed Identity<br/>(Access Connector)
    participant ADLS as ADLS Gen2
    
    UC->>MI: 1. Request token
    MI->>MI: 2. Azure AD authenticates
    MI->>UC: 3. Access token
    UC->>ADLS: 4. Access data<br/>(with token)
```

**Created by:** You (via Terraform/Portal)  
**Trust:** Azure AD (automatic)  
**Permissions:** Storage Blob Data Contributor

#### GCP: Databricks-Managed GSA

```mermaid
sequenceDiagram
    participant UC as Unity Catalog
    participant DBGSA as Databricks GSA<br/>(Databricks project)
    participant GCS as GCS Bucket<br/>(Your project)
    
    UC->>DBGSA: 1. Use Databricks GSA
    DBGSA->>GCS: 2. Access bucket<br/>(cross-project)
    
    Note over DBGSA,GCS: You grant permissions to<br/>Databricks' GSA in your project
```

**Created by:** Databricks (in their project)  
**Trust:** GCP IAM (cross-project)  
**Permissions:** Storage Object Admin

---

## Security: Why This Design Is Safe

### Principle of Least Privilege

Each identity only gets permissions it needs:

```mermaid
flowchart TD
    subgraph "AWS Example"
        CROSS[Cross-Account Role]
        CROSS_PERMS[Can: Launch EC2, Configure VPC<br/>Cannot: Access S3, Delete resources]
        
        STORAGE[Storage Config Role]
        STORAGE_PERMS[Can: Read/Write DBFS bucket<br/>Cannot: Launch EC2, Access other buckets]
    end
    
    subgraph "Azure Example"
        SP[Service Principal]
        SP_PERMS[Can: Create workspace, Deploy resources<br/>Cannot: Access data, Modify other resources]
        
        MI[Managed Identity]
        MI_PERMS[Can: Read/Write assigned storage<br/>Cannot: Create resources, Access other storage]
    end
    
    subgraph "GCP Example"
        COMPUTE_GSA[databricks-compute GSA]
        COMPUTE_PERMS[Can: Access assigned buckets<br/>Cannot: Create VMs, Modify IAM]
        
        UC_GSA[UC Storage GSA]
        UC_PERMS[Can: Read/Write catalog storage<br/>Cannot: Access compute, Modify network]
    end
    
    CROSS --> CROSS_PERMS
    STORAGE --> STORAGE_PERMS
    SP --> SP_PERMS
    MI --> MI_PERMS
    COMPUTE_GSA --> COMPUTE_PERMS
    UC_GSA --> UC_PERMS
    
    style CROSS_PERMS fill:#90EE90,color:#000
    style STORAGE_PERMS fill:#90EE90,color:#000
    style SP_PERMS fill:#90EE90,color:#000
    style MI_PERMS fill:#90EE90,color:#000
    style COMPUTE_PERMS fill:#90EE90,color:#000
    style UC_PERMS fill:#90EE90,color:#000
```

### Temporary Credentials (AWS)

AWS credentials **expire automatically**:

```
AssumeRole → Get temp creds → Use for 1 hour → Expired → Request new ones
```

You never give Databricks permanent access keys.

### External IDs Prevent Confused Deputy

**The Attack Without External ID:**
1. Attacker finds your role ARN (it's not secret)
2. Attacker tricks Databricks into using your role
3. Databricks accidentally accesses your S3 data

**How External ID Prevents This:**
```mermaid
sequenceDiagram
    participant Attacker
    participant DB as Databricks
    participant Your_Role as Your IAM Role
    
    Attacker->>DB: Use role arn:aws:iam::YOUR-ACCT:role/your-role
    DB->>Your_Role: AssumeRole<br/>(with Attacker's external_id)
    Your_Role->>Your_Role: Check: external_id = YOUR-ACCOUNT-ID?
    Your_Role->>DB: ❌ Access Denied<br/>(external_id mismatch)
    
    Note over Attacker,Your_Role: Attacker cannot access your data
```

### Audit Trail

Every access is logged:

| Cloud | Log Service | What Gets Logged |
|-------|-------------|------------------|
| **AWS** | CloudTrail | Every AssumeRole call, API calls made with temp creds |
| **Azure** | Activity Log | Resource creation, managed identity token requests |
| **GCP** | Cloud Audit Logs | Service account usage, API calls, permission grants |

---

## Common Questions

### Q: Can Databricks access my data without permission?

**AWS**: No. The IAM role you create defines exact permissions. Databricks can only access what you explicitly allow in the role policy.

**Azure**: No. The managed identity has NO permissions until you grant them (e.g., Storage Blob Data Contributor).

**GCP**: No. The service account has NO permissions until you grant them via IAM bindings.

### Q: What happens if I delete the identity?

**AWS**: Workspace stops working immediately. Databricks can't AssumeRole, so it can't launch clusters or access storage.

**Azure**: Workspace may continue running (resources already created), but you can't create new resources or access storage.

**GCP**: Workspace stops working. Compute VMs can't be created, storage can't be accessed.

### Q: Can Databricks see my credentials?

**AWS**: No. Databricks uses AssumeRole to get temporary credentials from AWS directly. Your permanent credentials stay with you.

**Azure**: No. Databricks uses Azure's token service. Your service principal secret is only used by your Terraform, not shared with Databricks.

**GCP**: No. Databricks impersonates service accounts via GCP's APIs. No credential files are shared.

### Q: Why so many roles/identities?

Each identity serves a different purpose with different permissions:
- **Workspace management**: Create infrastructure
- **Storage access**: Read/write data buckets
- **Compute access**: Clusters accessing user data
- **Unity Catalog**: Centralized governance layer

This **separation** means:
- Smaller blast radius if one is compromised
- Easier to audit what accessed what
- Simpler to grant/revoke specific permissions

### Q: Can I use one identity for everything?

**Technically yes, but don't:**
- Violates least privilege principle
- Harder to audit
- One compromise affects everything
- Can't easily revoke specific access

---

## Comparison: All Three Clouds

| Aspect | AWS | Azure | GCP |
|--------|-----|-------|-----|
| **Who creates workspace identity?** | You (IAM role) | Azure (first-party trust) | Databricks (GSA in your project) |
| **Credential type** | Temporary (AssumeRole) | Token (Managed Identity) | Service Account |
| **Trust mechanism** | External ID | First-party app | Service account impersonation |
| **UC storage identity** | IAM role (you create) | Managed Identity (you create) | Databricks GSA (they create) |
| **Setup complexity** | Medium (multiple roles) | Low (mostly automatic) | Medium (permission grants) |
| **Number of identities** | 4-5 IAM roles | 1-2 managed identities | 2-3 service accounts |
| **Credential rotation** | Automatic (temp creds) | Automatic (Azure handles) | Automatic (GCP handles) |
| **Least privilege** | Via IAM policies | Via RBAC roles | Via IAM bindings |
| **Audit logs** | CloudTrail | Activity Log | Cloud Audit Logs |

---

## Visual Summary

### Identity Flow Comparison

```mermaid
flowchart TB
    subgraph AWS["AWS Model"]
        AWS1[You create IAM roles]
        AWS2[Databricks AssumeRole]
        AWS3[Temporary credentials]
        AWS4[Access resources]
        AWS1 --> AWS2 --> AWS3 --> AWS4
    end
    
    subgraph Azure["Azure Model"]
        AZ1[Azure trusts Databricks]
        AZ2[You deploy workspace]
        AZ3[Managed identity created]
        AZ4[You grant permissions]
        AZ5[Access resources]
        AZ1 --> AZ2 --> AZ3 --> AZ4 --> AZ5
    end
    
    subgraph GCP["GCP Model"]
        GCP1[Databricks creates GSA]
        GCP2[GSA added to your project]
        GCP3[You grant permissions]
        GCP4[Access resources]
        GCP1 --> GCP2 --> GCP3 --> GCP4
    end
    
    style AWS fill:#FF9900,color:#000
    style Azure fill:#0078D4,color:#fff
    style GCP fill:#4285F4,color:#fff
```

---

## Next Steps

Now that you understand how identities work, check out:

1. **[Authentication Guide](./authentication.md)** - Set up Terraform authentication
2. **Cloud-specific deployment guides**:
   - [Azure Databricks](../adb4u/README.md)
   - [AWS Databricks](../awsdb4u/README.md)
   - [GCP Databricks](../gcpdb4u/readme.md)

---

## Still Confused?

**Remember the analogy:**
- **AWS**: Temporary key that expires (safest, but more setup)
- **Azure**: Master key (Microsoft trusts Databricks built-in)
- **GCP**: New employee in your office (you control what they access)

All three are secure, just different approaches based on each cloud's design philosophy.
