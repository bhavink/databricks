***REMOVED*** Objectives
Databricks provides two flavors of compute
- Clasic compute
- Serverless compute

* Each workspace is provisioned within the customer's GCP project. [Classic compute](https://docs.gcp.databricks.com/clusters/index.html) resides within customers project and utlizes customers vpc.
* Life cycle of a databricks cluster (classic or serverless) is managed by Databricks Control Plane.
* Compute instance type aka `node's` used by a Databricks cluster is backed by GCE instances aka nodes
* Nodes have Private IP addresses only (classic and serverless compute)
  
* To provide a secure logical isolation between databricks clusters within same workspace (classic or serverless) Databricks implements logical namespace's i.e no two clusters can talk to each other directly, communication is always managed thru databricks control plane.

***REMOVED******REMOVED*** Workspace Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        NET[Network Security]
        COMP[Compute Security]
        DATA[Data Security]
        ACCESS[Access Control]
    end
    
    subgraph "Network Security Controls"
        VPC_SC[VPC Service Controls<br/>Prevent Data Exfiltration]
        FW[VPC Firewall Rules<br/>Restrict Traffic]
        PGA[Private Google Access<br/>No Public Internet]
        NPIP[No Public IPs<br/>Private Nodes Only]
    end
    
    subgraph "Compute Isolation"
        NS1[Cluster Namespace 1<br/>Logical Isolation]
        NS2[Cluster Namespace 2<br/>Logical Isolation]
        NS3[Cluster Namespace 3<br/>Logical Isolation]
        CP_COMM[Communication via<br/>Control Plane Only]
    end
    
    subgraph "Data Protection"
        CMEK[Customer Managed<br/>Encryption Keys]
        UC[Unity Catalog<br/>Fine-grained Access]
        AUDIT[Audit Logging<br/>All Access Tracked]
    end
    
    NET --> VPC_SC
    NET --> FW
    NET --> PGA
    NET --> NPIP
    
    COMP --> NS1
    COMP --> NS2
    COMP --> NS3
    NS1 --> CP_COMM
    NS2 --> CP_COMM
    NS3 --> CP_COMM
    
    DATA --> CMEK
    DATA --> UC
    DATA --> AUDIT
    
    style VPC_SC fill:***REMOVED***E53935
    style FW fill:***REMOVED***E53935
    style NS1 fill:***REMOVED***1E88E5
    style NS2 fill:***REMOVED***1E88E5
    style NS3 fill:***REMOVED***1E88E5
    style CMEK fill:***REMOVED***8E24AA
    style UC fill:***REMOVED***8E24AA
```

***REMOVED******REMOVED*** Optionally
* Configure [VPC Service Control](./security/Configure-VPC-SC.md) to prevent data exfiltration
* Lock down [VPC firewall rules](./security/LockDown-VPC-Firewall-Rules.md)

***REMOVED******REMOVED*** Security Implementation Roadmap

```mermaid
graph LR
    subgraph "Phase 1: Network Foundation"
        P1_1[Customer Managed VPC]
        P1_2[Private IPs Only<br/>No Public Access]
        P1_3[Private Google Access]
    end
    
    subgraph "Phase 2: Traffic Control"
        P2_1[VPC Firewall Rules<br/>Restrict Egress/Ingress]
        P2_2[Cloud NAT<br/>Controlled Egress]
        P2_3[DNS Configuration<br/>Private/Restricted APIs]
    end
    
    subgraph "Phase 3: Advanced Security"
        P3_1[VPC Service Controls<br/>Data Exfiltration Prevention]
        P3_2[Customer Managed Keys<br/>CMEK Encryption]
        P3_3[Private Service Connect<br/>PSC Endpoints]
    end
    
    subgraph "Phase 4: Governance"
        P4_1[Unity Catalog<br/>Fine-grained Permissions]
        P4_2[Audit Logging<br/>Continuous Monitoring]
        P4_3[IP Access Lists<br/>Restrict Workspace Access]
    end
    
    P1_1 --> P1_2 --> P1_3
    P1_3 --> P2_1
    P2_1 --> P2_2 --> P2_3
    P2_3 --> P3_1
    P3_1 --> P3_2 --> P3_3
    P3_3 --> P4_1
    P4_1 --> P4_2 --> P4_3
    
    style P1_1 fill:***REMOVED***4285F4
    style P1_2 fill:***REMOVED***4285F4
    style P1_3 fill:***REMOVED***4285F4
    style P2_1 fill:***REMOVED***FF6F00
    style P2_2 fill:***REMOVED***FF6F00
    style P2_3 fill:***REMOVED***FF6F00
    style P3_1 fill:***REMOVED***E53935
    style P3_2 fill:***REMOVED***E53935
    style P3_3 fill:***REMOVED***E53935
    style P4_1 fill:***REMOVED***8E24AA
    style P4_2 fill:***REMOVED***8E24AA
    style P4_3 fill:***REMOVED***8E24AA
```

***REMOVED******REMOVED*** Cluster-to-Cluster Isolation

```mermaid
sequenceDiagram
    participant C1 as Cluster 1<br/>(Namespace A)
    participant CP as Control Plane<br/>(Communication Hub)
    participant C2 as Cluster 2<br/>(Namespace B)
    participant C3 as Cluster 3<br/>(Namespace C)
    
    Note over C1,C3: Direct cluster communication BLOCKED
    
    C1->>CP: Request to communicate
    CP->>CP: Validate permissions<br/>& namespace isolation
    
    alt Authorized Communication
        CP->>C2: Forward request<br/>(via Control Plane)
        C2->>CP: Response
        CP->>C1: Forward response
    else Unauthorized
        CP->>C1: Access Denied<br/>(Namespace isolation enforced)
    end
    
    Note over C1,C3: Security Benefits:<br/>- Logical isolation<br/>- No direct network access<br/>- Centralized authorization<br/>- Audit trail maintained
    
    C3->>C1: Direct connection attempt
    C1-XC3: Connection refused<br/>(Network isolation)
    
    style C1 fill:***REMOVED***1E88E5
    style C2 fill:***REMOVED***1E88E5
    style C3 fill:***REMOVED***1E88E5
    style CP fill:***REMOVED***43A047
```
  