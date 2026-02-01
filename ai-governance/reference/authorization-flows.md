# Unity Catalog Authorization Flows — Reference Diagrams

> **Official Documentation:** [Access Control in Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control) | [ABAC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac) | [Row Filters & Column Masks](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-row-filter-column-mask.html) | [Governed Tags](https://docs.databricks.com/aws/en/admin/governed-tags/)

This document provides visual reference diagrams for Unity Catalog authorization, showing how the four layers of access control work together to enforce secure, fine-grained data access.

## Four Layers of Access Control

Access control in Unity Catalog is built on **four complementary layers** that work together:

| Layer | Question Answered | Mechanisms | Docs |
|-------|-------------------|------------|------|
| **1. Workspace Restrictions** | WHERE can users access data? | Workspace bindings on catalogs, external locations, storage credentials | [Docs](https://docs.databricks.com/aws/en/catalogs/binding.html) |
| **2. Privileges & Ownership** | WHO can access WHAT? | GRANTs (`SELECT`, `MODIFY`, etc.), object ownership, admin roles | [Docs](https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/) |
| **3. ABAC Policies** | WHAT data based on tags? | [Governed tags](https://docs.databricks.com/aws/en/admin/governed-tags/) + policies with UDFs for dynamic enforcement | [Docs](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac) |
| **4. Table-Level Filtering** | WHAT rows/columns visible? | Row filters, column masks, dynamic views | [Docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-row-filter-column-mask.html) |

## 1) Four-Layer Authorization Flow

```mermaid
flowchart TB
    subgraph Query["Query Arrives"]
        User["User or Service Principal<br/>Authenticated via OAuth"]
    end
    
    subgraph Layer1["Layer 1: Workspace Restrictions"]
        WS{{"Is workspace<br/>bound to catalog?"}}
        WS -->|No| Deny1["❌ Access Denied<br/>Workspace not authorized"]
        WS -->|Yes| Pass1["✓ Pass to Layer 2"]
    end
    
    subgraph Layer2["Layer 2: Privileges & Ownership"]
        GRANT{{"Has SELECT/MODIFY<br/>GRANT on object?"}}
        GRANT -->|No| Deny2["❌ Access Denied<br/>Missing privilege"]
        GRANT -->|Yes| Pass2["✓ Pass to Layer 3"]
    end
    
    subgraph Layer3["Layer 3: ABAC Policies"]
        ABAC{{"Tag-based policy<br/>matches user?"}}
        ABAC -->|No| Deny3["❌ Access Denied<br/>Policy not satisfied"]
        ABAC -->|Yes| Pass3["✓ Pass to Layer 4"]
    end
    
    subgraph Layer4["Layer 4: Table-Level Filtering"]
        Filter["Apply Row Filters<br/>WHERE owner = current_user()"]
        Mask["Apply Column Masks<br/>CASE WHEN is_member()"]
        Filter --> Mask
        Mask --> Result["✅ Governed Data<br/>Returned"]
    end
    
    User --> WS
    Pass1 --> GRANT
    Pass2 --> ABAC
    Pass3 --> Filter
    
    %% Styling
    classDef layer1 fill:#cffafe,stroke:#06b6d4,color:#000
    classDef layer2 fill:#d1fae5,stroke:#10b981,color:#000
    classDef layer3 fill:#f3e8ff,stroke:#a855f7,color:#000
    classDef layer4 fill:#ffedd5,stroke:#f97316,color:#000
    classDef deny fill:#fecaca,stroke:#ef4444,color:#000
    classDef pass fill:#d1fae5,stroke:#22c55e,color:#000
    classDef result fill:#d1fae5,stroke:#10b981,color:#000,stroke-width:2px
    
    class WS layer1
    class GRANT layer2
    class ABAC layer3
    class Filter,Mask layer4
    class Deny1,Deny2,Deny3 deny
    class Pass1,Pass2,Pass3 pass
    class Result result
```

## 2) ABAC with Governed Tags Flow

```mermaid
flowchart LR
    subgraph Classification["Governed Tags (Classification)"]
        TagDef["Account-level tag definitions<br/>sensitivity: [low, medium, high, critical]<br/>region: [EMEA, AMER, APAC]<br/>domain: [finance, hr, sales]"]
        TagAssign["Tags applied to tables<br/>customer_data:<br/>  sensitivity=high<br/>  region=EMEA"]
    end
    
    subgraph Enforcement["ABAC Policies (Enforcement)"]
        Policy["Policy Definition<br/>IF sensitivity=high<br/>THEN require compliance-team"]
        UDF["UDF: filter_by_sensitivity()<br/>Row filter logic"]
    end
    
    subgraph Runtime["Query Execution"]
        User["User: alice@company.com<br/>Groups: compliance-team, emea-users"]
        Eval["UC evaluates:<br/>1. Table has sensitivity=high<br/>2. Policy requires compliance-team<br/>3. Alice is in compliance-team"]
        Result["✅ Access granted<br/>with policy filters applied"]
    end
    
    TagDef --> TagAssign
    TagAssign --> Policy
    Policy --> UDF
    User --> Eval
    UDF --> Eval
    Eval --> Result
    
    %% Styling
    classDef tags fill:#dbeafe,stroke:#3b82f6,color:#000
    classDef enforce fill:#f3e8ff,stroke:#a855f7,color:#000
    classDef runtime fill:#d1fae5,stroke:#10b981,color:#000
    
    class TagDef,TagAssign tags
    class Policy,UDF enforce
    class User,Eval,Result runtime
```

## 3) Row Filter Evaluation Flow

```mermaid
flowchart TB
    subgraph Query["User Query"]
        Q["SELECT * FROM customers"]
        User["current_user() = alice@company.com"]
    end
    
    subgraph Filter["Row Filter Function"]
        F["CREATE FUNCTION user_filter(owner STRING)<br/>RETURNS BOOLEAN<br/>RETURN owner = current_user()"]
    end
    
    subgraph Data["Table: customers"]
        R1["Row 1: owner=alice@... ✓"]
        R2["Row 2: owner=bob@... ✗"]
        R3["Row 3: owner=alice@... ✓"]
        R4["Row 4: owner=carol@... ✗"]
    end
    
    subgraph Result["Filtered Result"]
        FR["Only Alice's rows returned"]
    end
    
    Q --> F
    User --> F
    F --> R1
    F --> R2
    F --> R3
    F --> R4
    R1 --> FR
    R3 --> FR
    
    %% Styling
    classDef query fill:#dbeafe,stroke:#3b82f6,color:#000
    classDef filter fill:#fef3c7,stroke:#f59e0b,color:#000
    classDef pass fill:#d1fae5,stroke:#10b981,color:#000
    classDef fail fill:#fecaca,stroke:#ef4444,color:#000
    classDef result fill:#d1fae5,stroke:#10b981,color:#000,stroke-width:2px
    
    class Q,User query
    class F filter
    class R1,R3 pass
    class R2,R4 fail
    class FR result
```

## 4) Column Mask Evaluation Flow

```mermaid
flowchart TB
    subgraph Users["Two Different Users"]
        Admin["Admin: admin@company.com<br/>Groups: hr-admins"]
        Regular["Regular: employee@company.com<br/>Groups: employees"]
    end
    
    subgraph Mask["Column Mask Function"]
        M["CREATE FUNCTION mask_ssn(ssn STRING)<br/>RETURNS STRING<br/>RETURN CASE<br/>  WHEN is_member('hr-admins') THEN ssn<br/>  ELSE '***-**-' || RIGHT(ssn, 4)<br/>END"]
    end
    
    subgraph Original["Original Data"]
        O["SSN: 123-45-6789"]
    end
    
    subgraph Results["Results by User"]
        AdminR["Admin sees: 123-45-6789"]
        RegularR["Employee sees: ***-**-6789"]
    end
    
    Admin --> M
    Regular --> M
    M --> Original
    Original --> AdminR
    Original --> RegularR
    
    %% Styling
    classDef admin fill:#d1fae5,stroke:#10b981,color:#000
    classDef regular fill:#dbeafe,stroke:#3b82f6,color:#000
    classDef mask fill:#fef3c7,stroke:#f59e0b,color:#000
    classDef data fill:#f3f4f6,stroke:#6b7280,color:#000
    
    class Admin,AdminR admin
    class Regular,RegularR regular
    class M mask
    class O data
```

## 5) Complete Authorization Flow (All Patterns)

```mermaid
flowchart TB
    subgraph Entry["Request Entry"]
        User["End User"]
        SP["Service Principal"]
    end
    
    subgraph Auth["Authentication Layer"]
        OAuth["Databricks OAuth"]
        P1["Pattern 1: SP Token<br/>(M2M)"]
        P2["Pattern 2: User Token<br/>(U2M/OBO)"]
    end
    
    subgraph UC["Unity Catalog Authorization"]
        L1["Layer 1: Workspace Bindings<br/>Is workspace authorized?"]
        L2["Layer 2: Privileges<br/>Has GRANT on object?"]
        L3["Layer 3: ABAC<br/>Tag policy matches?"]
        L4["Layer 4: Filters/Masks<br/>Row filters + column masks"]
    end
    
    subgraph Data["Data Resources"]
        Tables[(Tables)]
        Views[(Views)]
        Volumes[(Volumes)]
    end
    
    User -->|Login| OAuth
    SP -->|Credentials| OAuth
    
    OAuth -->|Automated job| P1
    OAuth -->|User request| P2
    
    P1 --> L1
    P2 --> L1
    
    L1 --> L2
    L2 --> L3
    L3 --> L4
    
    L4 --> Tables
    L4 --> Views
    L4 --> Volumes
    
    %% Styling
    classDef entry fill:#f3f4f6,stroke:#6b7280,color:#000
    classDef auth fill:#fef3c7,stroke:#f59e0b,color:#000
    classDef layer1 fill:#cffafe,stroke:#06b6d4,color:#000
    classDef layer2 fill:#d1fae5,stroke:#10b981,color:#000
    classDef layer3 fill:#f3e8ff,stroke:#a855f7,color:#000
    classDef layer4 fill:#ffedd5,stroke:#f97316,color:#000
    classDef data fill:#e0e7ff,stroke:#6366f1,color:#000
    
    class User,SP entry
    class OAuth,P1,P2 auth
    class L1 layer1
    class L2 layer2
    class L3 layer3
    class L4 layer4
    class Tables,Views,Volumes data
```

## When to Use Each Mechanism

| Mechanism | Use When | Example | Docs |
|-----------|----------|---------|------|
| **Workspace bindings** | Isolating environments (dev/prod) | Restrict prod catalog to prod workspace | [Docs](https://docs.databricks.com/aws/en/catalogs/binding.html) |
| **Privileges (GRANTs)** | Basic access control | `GRANT SELECT ON TABLE` to group | [Docs](https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/) |
| **ABAC policies** | Centralized, tag-driven governance at scale | All `sensitivity=high` tables require compliance group | [Docs](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac) |
| **Row filters** | Per-user row-level security | Users see only their own records | [Docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-row-filter-column-mask.html) |
| **Column masks** | Sensitive data redaction | Mask SSN for non-HR users | [Docs](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-row-filter-column-mask.html) |
| **Dynamic views** | Complex filtering logic, Delta Sharing | Multi-table joins with embedded filters | [Docs](https://docs.databricks.com/aws/en/views/dynamic-views.html) |

> **Recommendation:** Use [ABAC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac) for centralized, scalable governance. Use row filters and column masks when per-table logic is required or ABAC hasn't been adopted yet.

## Related Documentation

- [Authentication Flows](authentication-flows.md) — Visual reference for authentication patterns
- [Access Control in Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control) — Official four-layer model
- [ABAC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac) — Attribute-based access control
- [Governed Tags](https://docs.databricks.com/aws/en/admin/governed-tags/) — Tag management for ABAC
- [Interactive Scrollytelling: Access Control Layers](../interactive/uc-access-control-layers.html) — Visual explainer
