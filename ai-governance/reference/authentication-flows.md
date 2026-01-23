# Cloud-Agnostic Agent Bricks Authentication — Workspace Prod

This visual reflects a likely setup for a "workspace-prod" environment using Databricks Agent Bricks, Databricks Apps, Unity Catalog governance, and integrations with vector search, customer models, foundational models, external models, Genie Space, and AI/BI Genie dashboards.

## Key behaviors

- **Automatic authentication passthrough** uses short‑lived OAuth tokens for a least‑privilege service principal tied to declared resources ("run as owner"-like behavior).
- **On‑behalf‑of‑user (OBO)** runs the agent as the end user; Unity Catalog enforces row/column security and masks per user; initialize user-authenticated clients inside predict() at request time; scopes restrict the APIs the agent can call.
- **Manual credentials** are used for external services (e.g., external LLM APIs or external MCP servers) and can also be used for Databricks resources via OAuth M2M for service principals when needed.
- **Foundation models** in system.ai are accessed as Databricks-managed resources under UC governance once workspace prerequisites are enabled.
- **Databricks Apps** support app authorization (dedicated app service principal) and user authorization (OBO with scopes) with UC enforcing fine‑grained policies on the latter.

## 1) Agent Endpoint: Auth Paths and Identities (workspace-prod)

```mermaid
flowchart LR
    %% Entry
    U["End User"] -->|chat/query| EP["Agent Bricks Endpoint: agent-endpoint-ka<br/>workspace-prod"]

    %% Identity issuance
    subgraph Identity_Control["Identity Control"]
        IDP["Databricks OAuth / Token Service"]
        EP -- "Automatic Passthrough<br/>declared resources" --> IDP
        EP -- "OBO Enabled + Scopes" --> IDP
        EP -- "Manual Credentials<br/>SP OAuth / External API Keys" --> SECRETS["Secrets / Env Vars"]
    end

    %% Resulting identities
    IDP -->|short-lived M2M| SP["Service Principal:<br/>sp-agent-workspace-prod"]
    IDP -->|downscoped token<br/>per request| USR["User Identity<br/>OBO"]
    SECRETS --> EXTID["External Credential<br/>Context"]

    %% Databricks-managed resources (UC-governed)
    subgraph Databricks_Managed["Databricks Managed - UC"]
        UC["Unity Catalog<br/>Policies"]
        VS[("Vector Search Endpoint:<br/>uc.catalog_prod.search.vs_index_customers")]
        MS[("Model Serving:<br/>endpoint-customer-model")]
        FM[("Foundational Model:<br/>system.ai/llm")]
        SQL[("SQL Warehouse:<br/>sqlw-prod")]
        GENIE["Genie Space:<br/>genie-space-sales"]
        AIBI["AI/BI Genie Dashboard:<br/>aibi-dashboard-revenue"]
    end

    %% External services
    subgraph External_Services["External Services"]
        XMODEL[("External Hosted Model API:<br/>external-llm")]
        XMCP[("External MCP Server:<br/>external-mcp-server")]
    end

    %% Access paths
    SP --> VS
    SP --> MS
    SP --> FM
    SP --> SQL
    SP --> GENIE

    USR --> VS
    USR --> MS
    USR --> FM
    USR --> SQL
    USR --> GENIE
    USR --> AIBI

    EXTID --> XMODEL
    EXTID --> XMCP

    %% UC governance connections
    UC --> VS
    UC --> SQL
    UC --> MS
    UC --- FM

    %% Notes
    note1["UC enforces per-user row/column policies under OBO;<br/>SP path uses least-privilege permissions<br/>declared at agent log time"]
    note2["External APIs use manual credentials;<br/>UC governs only Databricks-managed<br/>data/resources"]
    USR --- note1
    SP --- note1
    EXTID --- note2

    %% Styling
    classDef sp fill:#fdebd0,stroke:#e67e22,color:#000,stroke-width:1px
    classDef user fill:#d5f5e3,stroke:#27ae60,color:#000,stroke-width:1px
    classDef ext fill:#fce4ec,stroke:#c2185b,color:#000,stroke-width:1px
    classDef res fill:#f2f3f4,stroke:#7f8c8d,color:#000,stroke-width:1px
    classDef uc fill:#e8f8f5,stroke:#1abc9c,color:#000,stroke-width:1px
    classDef note fill:#fff3cd,stroke:#f39c12,color:#000,stroke-dasharray: 5 5

    class SP sp
    class USR user
    class EXTID ext
    class VS,MS,FM,SQL,GENIE,AIBI res
    class UC uc
    class XMODEL,XMCP ext
    class note1,note2 note
```

**Annotations:**

- **Automatic passthrough:** endpoint acts via short‑lived service principal credentials against declared dependencies.
- **OBO:** user identity known at request time; initialize in predict(); UC policies applied per user; scopes limit reachable APIs.
- **External model/MCP:** authenticate with manual credentials; combine with SP or OBO for Databricks resources as needed.
- **Foundation model (system.ai)** appears as Databricks-managed resource governed via UC integration once configured.

## 2) Databricks App Front-End: App vs User Authorization (workspace-prod)

```mermaid
flowchart LR
    U["End User"] --> APP["Databricks App: sales-assistant-app<br/>workspace-prod"]

    subgraph Authorization_Modes["Authorization Modes"]
        APP -- "App authorization" --> APPSP["App Service Principal:<br/>sp-app-sales-assistant"]
        APP -- "User authorization<br/>OBO" --> UTOK["Forwarded User Token"]
    end

    subgraph Databricks_Managed2["Databricks Managed - UC"]
        VS[("Vector Search Endpoint:<br/>uc.catalog_prod.search.vs_index_customers")]
        MS[("Model Serving:<br/>endpoint-customer-model")]
        FM[("Foundational Model:<br/>system.ai/llm")]
        SQL[("SQL Warehouse:<br/>sqlw-prod")]
        UC["Unity Catalog<br/>Policies"]
        GENIE["Genie Space:<br/>genie-space-sales"]
        AIBI["AI/BI Genie Dashboard:<br/>aibi-dashboard-revenue"]
    end

    subgraph External_Services2["External Services"]
        XMODEL[("External Hosted Model API:<br/>external-llm")]
        XMCP[("External MCP Server:<br/>external-mcp-server")]
    end

    %% App SP path (fixed permissions)
    APPSP --> VS
    APPSP --> MS
    APPSP --> FM
    APPSP --> SQL
    APPSP --> GENIE

    %% OBO path (per-user UC)
    UTOK --> VS
    UTOK --> MS
    UTOK --> FM
    UTOK --> SQL
    UTOK --> UC
    UTOK --> GENIE
    UTOK --> AIBI

    %% External integrations direct from the app
    APP --> XMODEL
    APP --> XMCP

    %% Notes
    P1["App authorization: consistent app-wide<br/>permissions via dedicated service principal"]
    P2["User authorization - OBO:<br/>UC row/column security and masks<br/>apply per user; scopes limit actions"]
    P3["External APIs: manual credentials;<br/>UC governs Databricks-managed data only"]

    APPSP --- P1
    UTOK --- P2
    APP --- P3

    %% Styling
    classDef sp fill:#fdebd0,stroke:#e67e22,color:#000,stroke-width:1px
    classDef user fill:#d5f5e3,stroke:#27ae60,color:#000,stroke-width:1px
    classDef res fill:#f2f3f4,stroke:#7f8c8d,color:#000,stroke-width:1px
    classDef uc fill:#e8f8f5,stroke:#1abc9c,color:#000,stroke-width:1px
    classDef ext fill:#fce4ec,stroke:#c2185b,color:#000,stroke-width:1px
    classDef note fill:#fff3cd,stroke:#f39c12,color:#000,stroke-dasharray: 5 5

    class APPSP sp
    class UTOK user
    class VS,MS,FM,SQL,GENIE,AIBI res
    class UC uc
    class XMODEL,XMCP ext
    class P1,P2,P3 note
```

## Quick Reference (cloud-agnostic)

- **Automatic passthrough** → short‑lived SP token; least‑privilege; resources declared at log time.
- **OBO** → runs as the end user; UC policies enforce per-user governance; declare scopes and initialize in predict().
- **Manual credentials** → external model/MCP; optionally SP OAuth M2M for Databricks resources in automation.
- **Foundation model (system.ai) and UC** → accessible as Databricks-managed resources with UC governance when workspace is configured.
- **Databricks Apps** → app SP (fixed permissions) vs OBO (per-user UC with scopes).
