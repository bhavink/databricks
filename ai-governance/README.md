# AI Governance: Authentication & Authorization for Databricks AI

> **Production-ready authentication and authorization patterns for Databricks AI products**
>
> Covers Genie Space, Agent Bricks, Databricks Apps, Model Serving, and custom MCP servers

---

## Quick Start

New to Databricks AI authentication? Read these in order:

1. [Authentication Patterns](01-AUTHENTICATION-PATTERNS.md) -- Three universal patterns (M2M, OBO, Manual)
2. [Authorization with Unity Catalog](02-AUTHORIZATION-WITH-UC.md) -- UC governance: privileges, ABAC, row filters, column masks
3. [UC Policy Design Principles](UC-POLICY-DESIGN-PRINCIPLES.md) -- `current_user()` vs `is_member()` across all execution contexts

---

## Reference (Canonical Docs)

These are the consolidated reference documents. Start here for any topic.

| Document | Contents |
|----------|----------|
| [Identity and Auth Reference](reference/identity-and-auth-reference.md) | Auth patterns, token flows, two-proxy problem, identity models per service, OAuth scope map, identity fragmentation gaps |
| [OBO vs M2M Decision Matrix](reference/obo-vs-m2m-decision-matrix.md) | Quick decision tree, detailed matrix, audit implications, per-service examples, anti-patterns |
| [Authorization Flows](reference/authorization-flows.md) | UC four-layer access control: workspace bindings, privileges, ABAC, row/column filtering |
| [Genie Authorization Cookbook](reference/genie-authorization-cookbook.md) | Genie security fundamentals, simple multi-team (3 teams), enterprise ABAC (1000+ users), multi-agent supervisor coordination |
| [Observability and Audit](reference/observability-and-audit.md) | Two-layer audit model (app-plane MLflow traces + data-plane system.access.audit), correlation strategy, gaps |
| [UC Policy Design Principles](UC-POLICY-DESIGN-PRINCIPLES.md) | When `current_user()` and `is_member()` work (and don't) across Genie OBO, Apps, Model Serving |
| [AI Gateway Patterns](AI-GATEWAY-PATTERNS.md) | When to use Databricks AI Gateway vs external gateway vs UC-native controls; four traffic patterns |
| [Orchestration Architecture](ORCHESTRATION-ARCHITECTURE.md) | Governed AI orchestration across Model Serving, MCP, AI Gateway, and Lakebase |
| [Federation Exchange Architecture](reference/federation-exchange-architecture.md) | Custom MCP governance: scope-based access, UC connections, supervisor integration, observability stack |

---

## Interactive Visualizations

| Page | Concept | Link |
|------|---------|------|
| Orchestration Hub | Architecture overview | [View](https://bhavink.github.io/databricks/ai-governance/interactive/orchestration/) |
| Agent Auth Methods | Model Serving auth patterns | [View](https://bhavink.github.io/databricks/ai-governance/interactive/orchestration/agent-auth-methods.html) |
| External App Auth | Token federation for external apps | [View](https://bhavink.github.io/databricks/ai-governance/interactive/orchestration/external-app-auth.html) |
| MCP Integration | Managed, External, Custom MCP patterns | [View](https://bhavink.github.io/databricks/ai-governance/interactive/orchestration/mcp-integration.html) |
| AI Gateway Governance | Rate limits, guardrails, inference tables | [View](https://bhavink.github.io/databricks/ai-governance/interactive/orchestration/ai-gateway-governance.html) |
| Databricks Apps | Native OAuth, UC integration | [View](https://bhavink.github.io/databricks/ai-governance/interactive/orchestration/databricks-apps.html) |
| Access Control Layers | UC four-layer authorization | [View](https://bhavink.github.io/databricks/ai-governance/interactive/uc-access-control-layers.html) |
| ABAC + Governed Tags | Tag-based dynamic access control | [View](https://bhavink.github.io/databricks/ai-governance/interactive/uc-abac-governed-tags.html) |
| Row Filters | Row-level security | [View](https://bhavink.github.io/databricks/ai-governance/interactive/uc-row-filters.html) |
| Column Masks | Column-level security | [View](https://bhavink.github.io/databricks/ai-governance/interactive/uc-column-masks.html) |
| OBO Auth Flow | On-Behalf-Of-User authentication | [View](https://bhavink.github.io/databricks/ai-governance/interactive/auth-flow-obo.html) |
| Federation Token Flow | 10-step animated token exchange with token inspector | [View](https://bhavink.github.io/databricks/ai-governance/interactive/federation-token-flow.html) |
| Decision Guide | Choose the right pattern | [View](https://bhavink.github.io/databricks/ai-governance/interactive/decision-guide.html) |

---

## Audit Logging & Monitoring

Comprehensive Genie monitoring and analytics using system tables.

| Component | Description |
|-----------|-------------|
| [Quick Start](audit-logging/genie-aibi/) | System tables-based monitoring for Genie spaces |

Features: Conversation activity tracking, user analytics, query insights, real-time alerting, Delta streaming.

---

## Presentations

| Deck | Topic |
|------|-------|
| [Identity & Governance for AI](presentations/identity-governance-overview.html) | Two patterns (OBO + Federation), shared UC governance, scope model, supervisor integration — 17 slides |
| [Federation Exchange Deep Dive](presentations/federation-deep-dive.html) | Three actors, token anatomy, sequence diagram, embedded animation, API calls, grants checklist — 21 slides |
| [AI Gateway Patterns v2](presentations/ai-gateway-patterns-v2.html) | AI Gateway traffic patterns and decision framework |

---

## Common Questions

**Q: Which authentication pattern should I use?**
A: See the [OBO vs M2M Decision Matrix](reference/obo-vs-m2m-decision-matrix.md).

**Q: How do I enforce per-user data access?**
A: Use OBO + UC row filters. See [Authorization with UC](02-AUTHORIZATION-WITH-UC.md).

**Q: How do I secure a Genie Space for multiple teams?**
A: See the [Genie Authorization Cookbook](reference/genie-authorization-cookbook.md).

**Q: My custom MCP server always shows the SP identity, not the user. Why?**
A: This is the two-proxy problem. See [Identity and Auth Reference](reference/identity-and-auth-reference.md#2-token-flows-and-the-two-proxy-problem).

**Q: Why does `is_member()` return the same result for all Genie users?**
A: Under OBO, `is_member()` may evaluate the execution identity, not the calling user. Use `current_user()` + allowlist table. See [UC Policy Design Principles](UC-POLICY-DESIGN-PRINCIPLES.md).

**Q: How do I audit access when using M2M?**
A: Platform audit records the SP UUID. You need app-level logging with `X-Forwarded-Email` for human identity. See [Observability and Audit](reference/observability-and-audit.md).

**Q: How do I give external users (partners, customers) governed access to Databricks AI tools?**
A: Use the Federation Exchange pattern: external IDP JWT → Databricks token exchange → role-based SPs → UC governance. See [Federation Exchange Architecture](reference/federation-exchange-architecture.md) and the [deep dive presentation](presentations/federation-deep-dive.html).

**Q: What's the difference between OBO and Federation?**
A: OBO = apps ON Databricks (user has a workspace account). Federation = apps OUTSIDE Databricks (user has no Databricks account, authenticates via external IDP). See the [Identity & Governance presentation](presentations/identity-governance-overview.html).

---

## Related Databricks Documentation

- [Agent Bricks](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/)
- [Agent Framework Authentication](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication)
- [Unity Catalog](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [Access Control in UC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/access-control)
- [ABAC](https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac)
- [Row Filters & Column Masks](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-row-filter-column-mask.html)
- [OAuth M2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m.html)
- [OAuth U2M](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-u2m.html)
- [Databricks Apps](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html)
- [Genie Space](https://docs.databricks.com/aws/en/genie/)

---

*Last updated: 2026-03-17 -- Added Federation Exchange presentations, interactive token flow, and architecture reference*
