# Cloud-Agnostic Authentication Flows — Reference Diagrams

> **Official Documentation:** [Agent Bricks](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/) | [Agent Authentication](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication) | [OAuth M2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m.html) | [OAuth U2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-u2m.html)

This visual reflects a "workspace-prod" environment using Databricks Agent Bricks, Databricks Apps, Unity Catalog governance, and integrations with vector search, customer models, foundational models, external models, Genie Space, and AI/BI Genie dashboards.

## Agent Bricks Supported Use Cases

| Use Case | Description | Status |
|----------|-------------|--------|
| [**Knowledge Assistant**](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/knowledge-assistant) | Turn documents into a chatbot that answers questions and cites sources | GA |
| [**Information Extraction**](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/key-info-extraction) | Transform unstructured text into structured insights | Beta |
| [**Custom LLM**](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/custom-llm) | Custom text generation (summarization, transformation) | Beta |
| [**Multi-Agent Supervisor**](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor) | Multi-agent AI systems with Genie Spaces and agents | Beta |
| [**AI/BI Genie**](https://docs.databricks.com/aws/en/genie/) | Turn tables into an expert AI chatbot | GA |
| [**Code Your Own**](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent) | Build with OSS libraries and Agent Framework | GA |

## Key Authentication Behaviors

- **[Automatic authentication passthrough](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#automatic-authentication-passthrough)** uses short‑lived OAuth tokens for a least‑privilege service principal tied to declared resources ("run as owner"-like behavior).
- **[On‑behalf‑of‑user (OBO)](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#on-behalf-of-user-authentication)** runs the agent as the end user; Unity Catalog enforces row/column security, masks, and ABAC policies per user; initialize user-authenticated clients inside `predict()` at request time; scopes restrict the APIs the agent can call.
- **[Manual credentials](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#manual-authentication)** are used for external services (e.g., external LLM APIs or external MCP servers) and can also be used for Databricks resources via OAuth M2M for service principals when needed.
- **Foundation models** in `system.ai` are accessed as Databricks-managed resources under UC governance once workspace prerequisites are enabled.
- **[Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/)** support app authorization (dedicated app service principal) and user authorization (OBO with scopes) with UC enforcing fine‑grained policies on the latter.

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

- **[Automatic passthrough](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#automatic-authentication-passthrough):** endpoint acts via short‑lived service principal credentials against declared dependencies.
- **[OBO](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#on-behalf-of-user-authentication):** user identity known at request time; initialize in `predict()`; UC policies (including [ABAC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac)) applied per user; scopes limit reachable APIs.
- **[External model/MCP](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#manual-authentication):** authenticate with manual credentials; combine with SP or OBO for Databricks resources as needed.
- **[Foundation model (system.ai)](https://docs.databricks.com/aws/en/machine-learning/model-serving/foundation-model-overview.html)** appears as Databricks-managed resource governed via UC integration once configured.

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

| Pattern | Token Type | UC Enforced | Use Case | Docs |
|---------|-----------|-------------|----------|------|
| **Automatic passthrough** | Short‑lived SP token | ✅ SP permissions | Batch jobs, automation | [Docs](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m.html) |
| **OBO** | User token | ✅ Per-user + ABAC | User-facing apps | [Docs](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-u2m.html) |
| **Manual credentials** | External API key | ❌ External | Third-party APIs | [Docs](https://docs.databricks.com/aws/en/security/secrets/) |

### Key Points

- **[Automatic passthrough](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#automatic-authentication-passthrough)** → short‑lived SP token; least‑privilege; resources declared at log time.
- **[OBO](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#on-behalf-of-user-authentication)** → runs as the end user; UC policies (row filters, column masks, [ABAC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac)) enforce per-user governance; declare scopes and initialize in `predict()`.
- **[Manual credentials](https://docs.databricks.com/aws/en/security/secrets/)** → external model/MCP; optionally SP OAuth M2M for Databricks resources in automation.
- **[Foundation model (system.ai)](https://docs.databricks.com/aws/en/machine-learning/model-serving/foundation-model-overview.html)** → accessible as Databricks-managed resources with UC governance when workspace is configured.
- **[Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/)** → app SP (fixed permissions) vs OBO (per-user UC with scopes).

## Related Documentation

- [Unity Catalog Access Control](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control) — Four layers of access control
- [Authorization Flows](authorization-flows.md) — Visual reference for UC authorization
- [Agent Bricks](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/) — Production AI agents
- [Agent Framework Authentication](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication) — Detailed auth setup
