
## Workspace Architecture

From [here](https://docs.gcp.databricks.com/getting-started/overview.html#high-level-architecture): Databricks is built on GCP and operates out of a `control plane` and a `compute plane`.

The `control plane` includes the backend services that Databricks manages in its own Google Cloud account. Notebook commands and many other workspace configurations are stored in the control plane and encrypted at rest.

The `compute plane` is where your data is processed. There are `two` types of compute planes depending on the compute that you are using.

For `serverless` compute, the serverless compute resources run in a serverless compute plane in your Databricks account.

For `classic` Databricks compute, the compute resources are in your Google Cloud resources in what is called the classic compute plane. This refers to the network in your Google Cloud resources and its resources.

To learn more about classic compute and serverless compute, see [Types of compute](https://docs.gcp.databricks.com/en/compute/index.html#types-of-compute).

### High-Level Architecture

```mermaid
graph TB
    subgraph "Databricks Control Plane<br/>(Databricks GCP Account)"
        CP[Control Plane Services]
        WEB[Web Application]
        JOBS_SVC[Jobs Service]
        NOTEBOOK[Notebook Storage]
        CLUSTER_MGR[Cluster Manager]
        META[Metastore Service]
    end
    
    subgraph "Customer GCP Account"
        subgraph "Classic Compute Plane"
            VPC[Customer VPC]
            SUBNET[Subnets]
            GCE[GCE Instances<br/>Databricks Runtime]
            NAT[Cloud NAT]
        end
        
        subgraph "Serverless Compute Plane<br/>(Managed by Databricks)"
            SCP[Serverless Resources]
            SCP_VPC[Databricks Serverless VPC]
        end
        
        subgraph "Storage"
            GCS[GCS Buckets<br/>Data Lake]
            BQ[BigQuery<br/>Data Warehouse]
            WSTORAGE[Workspace Storage]
        end
    end
    
    WEB --> CLUSTER_MGR
    CLUSTER_MGR --> GCE
    JOBS_SVC --> GCE
    JOBS_SVC --> SCP
    NOTEBOOK --> GCE
    
    GCE --> VPC
    VPC --> SUBNET
    SUBNET --> GCE
    NAT --> VPC
    
    GCE --> GCS
    GCE --> BQ
    SCP --> GCS
    SCP --> BQ
    
    CP -.Secure Cluster<br/>Connectivity.-> GCE
    GCE -.Outbound HTTPS<br/>via NAT.-> CP
    
    SCP_VPC -.Private Google<br/>Access.-> GCS
    
    style CP fill:#1E88E5
    style WEB fill:#1E88E5
    style GCE fill:#43A047
    style SCP fill:#7CB342
    style VPC fill:#4285F4
    style GCS fill:#FF6F00
```

Before you begin, please make sure to familiarize yourself with
- [Serverless compute plane](https://docs.gcp.databricks.com/en/getting-started/overview.html#serverless-compute-plane)
- [Classic compute plane](https://docs.gcp.databricks.com/en/getting-started/overview.html#classic-compute-plane)
- [Workspace storage buckets](https://docs.gcp.databricks.com/en/getting-started/overview.html#workspace-storage-buckets)
- [Type of compute](https://docs.gcp.databricks.com/en/compute/index.html#compute)
- [Databricks Runtime aka dbr](https://docs.gcp.databricks.com/en/compute/index.html#dbr)
- [DBR versioning](https://docs.gcp.databricks.com/en/compute/index.html#runtime-versioning)
- [Unity catalog](https://docs.gcp.databricks.com/en/data-governance/unity-catalog/index.html)
- [Budget policies](https://docs.gcp.databricks.com/en/admin/account-settings/budgets.html)
- [How to get support](https://docs.gcp.databricks.com/en/resources/support.html)

Next we'll zoom into the compute plane architecture.

## High-Level Communication flow between control plane and [classic compute plane](https://docs.gcp.databricks.com/en/security/network/classic/index.html#classic-compute-plane-networking)

### Secure Cluster Connectivity Architecture

```mermaid
sequenceDiagram
    participant User
    participant CP as Control Plane<br/>(Databricks)
    participant SCC as Secure Cluster<br/>Connectivity Relay
    participant GCE as GCE Cluster Nodes<br/>(No Public IPs)
    participant GCS as GCS/GAR<br/>(Private Google Access)
    
    User->>CP: Create Cluster Request
    CP->>GCE: Initialize Cluster
    
    Note over GCE: Cluster nodes start<br/>with private IPs only
    
    GCE->>SCC: Establish Outbound<br/>Connection (TLS 1.3)
    activate SCC
    SCC-->>GCE: Connection Established
    
    Note over SCC,GCE: Persistent WebSocket<br/>Connection
    
    CP->>SCC: Send Commands
    SCC->>GCE: Forward Commands
    GCE->>SCC: Return Results
    SCC->>CP: Forward Results
    CP->>User: Display Results
    
    GCE->>GCS: Access Runtime Images<br/>(via Private Google Access)
    GCS-->>GCE: Images/Data
    
    deactivate SCC
    
    Note over User,GCS: All communication encrypted<br/>No inbound connections to cluster
```

### Things to remember

* This communication pattern is called [Secure Cluster Connectivity](https://docs.gcp.databricks.com/security/secure-cluster-connectivity.html) and is enabled by default.
* No public IP addresses on compute plane nodes(GCE instances)
* The secure cluster connectivity relay: compute plane initiate's a network connection to the control plane (egress) secure cluster connectivity relay during databricks [cluster](https://docs.gcp.databricks.com/en/compute/index.html#compute) creation.

## Detailed Deployment Architecture

### Network Communication Flows

```mermaid
graph TB
    subgraph "Databricks Control Plane"
        DCP[Control Plane Services]
        HMS[Managed Hive Metastore]
    end
    
    subgraph "Customer GCP Project"
        subgraph "Customer VPC [1]"
            SUBNET[Node Subnet<br/>/20 to /26]
            
            subgraph "Databricks Cluster"
                DRIVER[Driver Node<br/>Private IP Only]
                WORKER1[Worker Node<br/>Private IP Only]
                WORKER2[Worker Node<br/>Private IP Only]
            end
            
            NAT[Cloud NAT<br/>Egress Appliance]
        end
        
        subgraph "Google Services"
            GAR[Google Artifact Registry<br/>Runtime Images]
            GCS_WS[GCS Workspace Logs]
        end
        
        subgraph "Data Sources"
            GCS_DATA[GCS Data Lake]
            BQ[BigQuery]
            EXT[External Sources]
        end
    end
    
    subgraph "Serverless Compute Plane"
        SCP[Serverless Resources<br/>Databricks Managed VPC]
    end
    
    DRIVER --> SUBNET
    WORKER1 --> SUBNET
    WORKER2 --> SUBNET
    
    SUBNET --> NAT
    
    NAT -->|3: TLS 1.3<br/>Egress to Control Plane| DCP
    NAT -->|4: Hive Metastore<br/>Access| HMS
    
    SUBNET -->|5: Private Google Access<br/>No NAT Required| GAR
    SUBNET -->|6: Private Google Access| GCS_WS
    
    SUBNET -->|7: Private Google Access<br/>Serverless Compute| SCP
    
    SUBNET -->|8: Public Repos<br/>PyPI, CRAN, Maven| NAT
    
    DRIVER -->|9: Data Access| GCS_DATA
    WORKER1 -->|9: Data Access| GCS_DATA
    DRIVER -->|9: Query| BQ
    DRIVER -->|9: External Access| EXT
    
    style DCP fill:#1E88E5
    style SUBNET fill:#4285F4
    style DRIVER fill:#43A047
    style WORKER1 fill:#43A047
    style WORKER2 fill:#43A047
    style NAT fill:#FF6F00
    style SCP fill:#7CB342
    style GCS_DATA fill:#FDD835
```

**Network Flow Descriptions:**

1. **Flow 1:** Classic compute plane resides within your project and it utilizes your vpc
   * Per databricks workspace we need [1 subnet](https://docs.gcp.databricks.com/administration-guide/cloud-configurations/gcp/network-sizing.html):
     * Node Subnet
2. **Flow 3:** Outbound or Egress communication from your vpc to databricks control plane is required. Typically this is achieved by attaching an egress appliance like Cloud NAT to your VPC. In transit traffic is encrypted using TLS 1.3. *`Having an egress path to Databricks control plane is a must have requirement`*
3. **Flow 5,6:** Outbound communication from your vpc to databricks managed Google Artifact Registry (for runtime images) and GCS (for workspace diagnostic logs). When [Private Google Access](https://cloud.google.com/vpc/docs/configure-private-google-access) is enabled on the VPC, traffic stays on Google network/backbone and requires no egress appliance like Cloud NAT.
4. **Flow 7:** Serverless compute plane access using [Private Google Access](https://cloud.google.com/vpc/docs/configure-private-google-access). On Serverless compute VPC's PGA is enabled, traffic stays on Google network/backbone and doesnt travel thru internet.
5. **Flow 4:** Outbound communication from your vpc to databricks managed HIVE Metastore
   * optionally you could also bring your [own hive metastore](https://docs.gcp.databricks.com/data/metastores/external-hive-metastore.html)
6. **Flow 8:** Outbound communication to public repositories to download python, r and java libraries
   * optionally you could have a local mirror of these public repos and avoid downloading it from public sites.
7. **Flow 9:** Accessing your data sources (GCS/BQ/PubSub/Any External source) 