# Authentication Patterns for Databricks AI Products

> **Technical overview for authentication and authorization across Databricks AI products**
>
> For the complete token flows, OAuth scope reference, identity models, and known gaps, see the canonical reference: [reference/identity-and-auth-reference.md](reference/identity-and-auth-reference.md)
>
> For the OBO vs M2M decision framework, see: [reference/obo-vs-m2m-decision-matrix.md](reference/obo-vs-m2m-decision-matrix.md)

---

## Important Disclaimers

### Multi-Cloud Documentation

This guide primarily links to **AWS Databricks documentation** for consistency. However, all authentication concepts apply universally across **AWS, Azure, and GCP**.

- [AWS Documentation](https://docs.databricks.com/aws/en/)
- [Azure Documentation](https://learn.microsoft.com/en-us/azure/databricks/)
- [GCP Documentation](https://docs.databricks.com/gcp/en/)

### Guidance vs Official Documentation

- This guide represents **practical guidance and best practices**, not official Databricks positions
- Always consult [official Databricks documentation](https://docs.databricks.com) for authoritative information
- Databricks features evolve rapidly - **verify current capabilities** and syntax in official docs

---

## Overview

Databricks provides a **unified authentication and authorization model** that works consistently across all AI products (Genie Space, Agent Bricks, Databricks Apps, Model Serving, Vector Search, AI/BI Dashboards).

### Three Universal Authentication Patterns

Every Databricks AI application uses one or more of these three patterns:

| Pattern | Token Type | Identity in Audit | Use Case |
|---------|-----------|-------------------|----------|
| **Automatic Passthrough (M2M)** | Short-lived SP token | SP UUID | Batch jobs, automation, shared resources |
| **On-Behalf-Of User (OBO)** | User token | Human email | User-facing apps, per-user data access |
| **Manual Credentials** | External API key | Depends on service | External LLMs, external MCP, third-party SaaS |

### When to Use Each

| Question | Answer |
|---|---|
| User should only see their data? | **OBO** -- UC row filters, column masks, ABAC fire as the user |
| Everyone sees the same data? | **M2M** -- SP credentials, shared access |
| Need human identity in platform audit? | **OBO** where possible; app-level audit for M2M paths |
| External API or third-party service? | **Manual Credentials** |
| Background/batch processing? | **M2M** |

### Key Resources

| Topic | Document |
|---|---|
| Complete auth reference (token flows, scopes, identity models, gaps) | [reference/identity-and-auth-reference.md](reference/identity-and-auth-reference.md) |
| OBO vs M2M decision framework | [reference/obo-vs-m2m-decision-matrix.md](reference/obo-vs-m2m-decision-matrix.md) |
| UC authorization layers | [02-AUTHORIZATION-WITH-UC.md](02-AUTHORIZATION-WITH-UC.md) |
| UC policy design (`current_user()` vs `is_member()`) | [UC-POLICY-DESIGN-PRINCIPLES.md](UC-POLICY-DESIGN-PRINCIPLES.md) |
| Genie authorization cookbook | [reference/genie-authorization-cookbook.md](reference/genie-authorization-cookbook.md) |
| Observability and audit architecture | [reference/observability-and-audit.md](reference/observability-and-audit.md) |
| Implementation patterns (AuthZ Showcase) | [scenarios/07-AuthZ-SHOWCASE/docs/AUTHZ-PATTERNS.md](scenarios/07-AuthZ-SHOWCASE/docs/AUTHZ-PATTERNS.md) |

---

## Pattern 1: Automatic Passthrough (M2M)

The platform issues short-lived credentials for a dedicated service principal tied to declared resources at log time.

- **How it works**: Resources declared when logging the agent; platform auto-provisions an SP with least-privilege access
- **UC enforcement**: SP-level permissions (grants on catalogs, schemas, tables)
- **Audit trail**: SP UUID in `system.access.audit` -- human identity is NOT captured
- **Docs**: [Automatic Passthrough](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#automatic-authentication-passthrough), [OAuth M2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m.html)

---

## Pattern 2: On-Behalf-Of User (OBO)

The agent or app runs as the end user. UC enforces row filters, column masks, and ABAC policies per user.

- **How it works**: User identity passed via OAuth token; client initialized inside `predict()` at request time
- **UC enforcement**: Per-user row filters, column masks, ABAC, governed tags
- **Audit trail**: Human email in `system.access.audit`
- **Scope requirement**: Declare required scopes (`sql`, `dashboards.genie`, `model-serving`, etc.)
- **Docs**: [OBO Auth](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#on-behalf-of-user-authentication), [OAuth U2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-u2m.html)

> For the complete OAuth scope map (including undocumented Azure-specific scopes, the `sql` scope gotcha, and the two configuration paths), see [reference/identity-and-auth-reference.md](reference/identity-and-auth-reference.md#4-oauth-scope-reference).

---

## Pattern 3: Manual Credentials

External API keys or SP OAuth credentials stored in Databricks Secrets for services outside the platform.

- **How it works**: Credentials stored in workspace secrets or environment variables; combined with M2M or OBO for Databricks resources
- **UC enforcement**: None (external to Databricks)
- **Audit trail**: External service logs only
- **Docs**: [Manual Auth](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#manual-authentication), [Secrets](https://docs.databricks.com/aws/en/security/secrets/)

---

## Databricks AI Products

| Product | Description | Documentation |
|---------|-------------|---------------|
| **Genie Space** | AI/BI chatbot for natural language queries on data | [Docs](https://docs.databricks.com/en/genie/index.html) |
| **AI/BI Dashboards** | Intelligence dashboards with natural language | [Docs](https://docs.databricks.com/en/dashboards/index.html) |
| **Agent Bricks** | Production-grade AI agents with declarative templates | [Docs](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/) |
| **Databricks Apps** | Custom applications with Streamlit, Dash, Gradio | [Docs](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html) |
| **Model Serving** | Deployed ML models and LLM endpoints | [Docs](https://docs.databricks.com/en/machine-learning/model-serving/index.html) |
| **Vector Search** | Embedding retrieval and similarity search | [Docs](https://docs.databricks.com/aws/en/vector-search/vector-search) |

### Agent Bricks Use Cases

| Use Case | Status | Documentation |
|----------|--------|---------------|
| [Knowledge Assistant](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/knowledge-assistant) | GA | Turn documents into a chatbot |
| [Information Extraction](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/key-info-extraction) | Beta | Unstructured text to structured insights |
| [Custom LLM](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/custom-llm) | Beta | Summarization, text transformation |
| [Multi-Agent Supervisor](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/multi-agent-supervisor) | Beta | Multi-agent systems with Genie + agents |
| [AI/BI Genie](https://docs.databricks.com/aws/en/genie/) | GA | Tables to expert AI chatbot |
| [Code Your Own](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent) | GA | Build with OSS libraries |

---

## Related Resources

- [Unity Catalog Access Control](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control) -- Four layers of access control
- [Agent Framework Authentication](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication) -- Detailed auth setup
- [ABAC (Attribute-Based Access Control)](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac)
- [Row Filters & Column Masks](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-row-filter-column-mask.html)

---

*Last updated: 2026-03-12 -- Slimmed to overview; detailed content consolidated into [reference/identity-and-auth-reference.md](reference/identity-and-auth-reference.md)*
