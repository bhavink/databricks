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

## 3) Databricks Apps: OAuth Scope Map

> Verified on Azure Databricks, March 2026. Add ALL scopes upfront — missing scopes only surface at runtime, per feature.

| Scope | Required for | Notes |
|---|---|---|
| `dashboards.genie` | Genie Conversation API (all clouds) | Must be in `user_authorized_scopes` |
| `genie` | Genie Conversation API on **Azure** | **Undocumented Azure-specific requirement** — UI does not show this scope |
| `model-serving` | Agent Bricks / Model Serving OBO | |
| `sql` | Statement Execution API | Adding to `user_authorized_scopes` does NOT embed it in the JWT — use M2M for SQL |
| `unity-catalog` | External MCP proxy `/api/2.0/mcp/external/...` | **Undocumented** — proxy checks USE CONNECTION privilege; missing = 403 |
| `all-apis` | General Databricks REST APIs | Catch-all |
| `offline_access`, `email`, `openid`, `profile`, `iam.*` | OIDC identity baseline | Always required |

**Patch command (run once after any app create or delete+recreate):**
```bash
databricks account custom-app-integration update '<integration-id>' \
  --profile <account-profile> \
  --json '{
    "scopes": ["offline_access","email","iam.current-user:read",
               "openid","dashboards.genie","genie","iam.access-control:read",
               "profile","model-serving","sql","all-apis","unity-catalog"],
    "user_authorized_scopes": ["dashboards.genie","genie","model-serving",
                                "sql","all-apis","unity-catalog"]
  }'
```

**`sql` scope gotcha:** The platform issues a minimal OIDC identity token regardless of `user_authorized_scopes` configuration. Statement Execution API checks the JWT `scope` claim directly and rejects it. Use M2M (`WorkspaceClient()` with no args) for SQL queries; use OBO only for Genie and Agent Bricks.

**OAuth integration reset (nuclear option):** If `unity-catalog` scope is added after users have existing sessions, existing refresh tokens retain original scopes — refreshed access tokens do NOT pick up new scopes. Sign-out or incognito is insufficient if the workspace SSO session is still valid. Only fix: delete and recreate the app (creates a new OAuth integration), then immediately patch the new integration with the full scope set.

## 4) The Two-Proxy Problem (Databricks Apps + Custom MCP)

When a Streamlit app calls a custom MCP server and both are Databricks Apps, each has its own Envoy proxy:

```
User browser
    |  HTTPS + session cookie
    v
[main-app Envoy proxy]              <- Proxy 1
    |  injects X-Forwarded-Access-Token (Token A = user OBO token)
    |  injects X-Forwarded-Email (user email)
    v
app.py (Streamlit)
    |  Authorization: Bearer {Token A}   <- app forwards Token A
    v
[mcp-app Envoy proxy]               <- Proxy 2
    |  STRIPS the incoming Authorization header
    |  injects X-Forwarded-Access-Token (Token B = MCP app SP token)
    |  injects X-Forwarded-Email (user email, derived from Token A)
    v
server/main.py (FastMCP)
    |  Token B sub = MCP SP UUID (NOT the user)
    |  X-Forwarded-Email = correct user email
```

**The problem:** Proxy 2 substitutes its own SP token for the user's token. The MCP server code never sees the user's OBO token.

**The solution:** Use `X-Forwarded-Email` (set by the proxy from the validated incoming token, cannot be forged by the calling app) for user identity. Use `WorkspaceClient()` (M2M, no args) for SQL queries, with explicit `WHERE user_email = '{caller}'` filter in each query.

**What NOT to use in the MCP server:**
- `ModelServingUserCredentials()` — silently falls back to M2M in Databricks Apps context
- `WorkspaceClient(host=host, token=user_token)` — SDK raises conflict error if `DATABRICKS_CLIENT_ID/SECRET` env vars are also set
- The `X-Forwarded-Access-Token` for SQL — the token lacks the `sql` scope claim

> **Last verified:** 2026-03-08, Azure Databricks (adb-wx1). Source: AI Auth Showcase build, Phase 5–6.

## Related Documentation

- [Unity Catalog Access Control](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control) — Four layers of access control
- [Authorization Flows](authorization-flows.md) — Visual reference for UC authorization
- [Agent Bricks](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/) — Production AI agents
- [Agent Framework Authentication](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication) — Detailed auth setup
- [AI Auth Showcase Patterns](../scenarios/07-AuthZ-SHOWCASE/AUTHZ-PATTERNS.md) — Hard-won findings from a working Azure deployment
