# Databricks on GCP
_The best practice guide that you've been looking for_

🔑 **[Authentication Setup Guide →](../guides/authentication.md)** - Need help with GCP/Databricks authentication? Start here!

# Introduction

[Databricks](https://www.databricks.com) provides a data lakehouse platform unifying the best of data warehouses and data lakes in one simple platform to handle all your data, analytics and AI use cases. It's built on an open and reliable data foundation that efficiently handles all data types and applies one common security and governance approach across all of your data and cloud platforms.

## Databricks Lakehouse Platform Components

```mermaid
graph TB
    subgraph "Databricks Lakehouse Platform"
        UI[Web UI & APIs]
        WS[Workspaces]
        
        subgraph "Data Processing"
            NB[Notebooks]
            JOBS[Jobs & Workflows]
            SQL[SQL Analytics]
            ML[ML & MLflow]
        end
        
        subgraph "Compute Options"
            CLASSIC[Classic Compute<br/>Customer VPC]
            SERVERLESS[Serverless Compute<br/>Databricks Managed]
        end
        
        subgraph "Data Governance"
            UC[Unity Catalog]
            SEC[Security & Access Control]
            AUDIT[Audit Logs]
        end
        
        subgraph "Storage Layer"
            DL[Data Lake<br/>GCS Buckets]
            DW[Data Warehouse<br/>BigQuery]
            EXT[External Sources]
        end
    end
    
    UI --> WS
    WS --> NB
    WS --> JOBS
    WS --> SQL
    WS --> ML
    
    NB --> CLASSIC
    NB --> SERVERLESS
    JOBS --> CLASSIC
    JOBS --> SERVERLESS
    SQL --> SERVERLESS
    ML --> CLASSIC
    
    UC --> SEC
    UC --> AUDIT
    
    CLASSIC --> DL
    SERVERLESS --> DL
    SQL --> DW
    CLASSIC --> EXT
    
    style UI fill:#1E88E5
    style WS fill:#1E88E5
    style CLASSIC fill:#43A047
    style SERVERLESS fill:#7CB342
    style UC fill:#8E24AA
    style DL fill:#FF6F00
```

# Objective
In this guide we'll share with you architectural patterns and design guidelines to help you with:
* [Getting Started](Getting-Started.md)
* [Workspace Architecture](Workspace-Architecture.md)
* [Workspace Security Control](Workspace-Security.md)
  * Configure [VPC Service Control](./security/Configure-VPC-SC.md) to prevent data exfiltration
  * Lock down [VPC firewall rules](./security/LockDown-VPC-Firewall-Rules.md)
* [Workspace Provisioning](Workspace-Provisioning.md)
* [Workspace DNS Configuration](DNS-Setup-Guide.md)
* [Identity and Access Management](Identity-And-Access-Management.md)
* [Observability and Monitoring](Observability-And-Monitoring.md)
* [Cost Management, Charge backs & Analysis](Cost-Management-And-Analysis.md)

## Documentation Journey

```mermaid
graph TB
    Start([Start Here])
    GS[Getting Started<br/>Trial, Subscriptions,<br/>Basic Concepts]
    WA[Workspace Architecture<br/>Control & Compute Planes,<br/>Network Design]
    WP[Workspace Provisioning<br/>VPC, Subnets,<br/>Terraform Scripts]
    WS[Workspace Security<br/>VPC SC, Firewall Rules,<br/>Private Access]
    IAM[Identity & Access<br/>Users, Groups,<br/>Service Principals]
    OBS[Observability<br/>Job Monitoring,<br/>Performance Metrics]
    COST[Cost Management<br/>Budgets, Analysis,<br/>Optimization]
    
    Start --> GS
    GS --> WA
    WA --> WP
    WP --> WS
    GS --> IAM
    WP --> OBS
    WP --> COST
    WS -.->|enhances| WP
    IAM -.->|applies to| WP
    OBS -.->|monitors| WP
    COST -.->|optimizes| WP
    
    style Start fill:#FF6F00
    style GS fill:#1E88E5
    style WA fill:#43A047
    style WP fill:#E53935
    style WS fill:#8E24AA
    style IAM fill:#FB8C00
    style OBS fill:#00ACC1
    style COST fill:#FDD835
```

Most of the content is derived from [public docs](https://docs.gcp.databricks.com)


# Contributing

Knowledge when shared gets multiplied. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request.
And if you like it then please give us a star and spread the word!

1. Fork the Project
2. Create your own Branch (`git checkout -b gcpdb4u/mybranch`)
3. Commit your Changes (`git commit -m 'Add something new'`)
4. Push to the Branch (`git push origin gcpdb4u/mybranch`)
5. Open a Pull Request


# Contact

Project Link: [https://github.com/bhavink/databricks/gcpdb4u](https://github.com/bhavink/databricks/gcpdb4u)

