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
| Decision Guide | Choose the right pattern | [View](https://bhavink.github.io/databricks/ai-governance/interactive/decision-guide.html) |

---

## Scenarios

### AI Auth Showcase (Scenario 07)

End-to-end working demonstration of every auth pattern: Genie OBO, Agent Bricks OBO, custom MCP server, external MCP proxy, SQL with user filtering. Verified on Azure Databricks, March 2026.

| Document | Contents |
|----------|----------|
| [README](scenarios/07-AuthZ-SHOWCASE/README.md) | Overview and getting started |
| [SETUP](scenarios/07-AuthZ-SHOWCASE/SETUP.md) | Complete deployment guide |
| [DEMO-GUIDE](scenarios/07-AuthZ-SHOWCASE/DEMO-GUIDE.md) | Demo walkthrough and troubleshooting |
| [DEMO-SCRIPT](scenarios/07-AuthZ-SHOWCASE/DEMO-SCRIPT.md) | Presenter script |
| [Auth Patterns](scenarios/07-AuthZ-SHOWCASE/docs/AUTHZ-PATTERNS.md) | Hard-won implementation details: two-proxy problem, OAuth scope map, code patterns |
| [Best Practices](scenarios/07-AuthZ-SHOWCASE/docs/AUTHZ-BEST-PRACTICES.md) | Decision matrix, confused deputy prevention, proxy architecture decisions |
| [Identity Architecture](scenarios/07-AuthZ-SHOWCASE/docs/IDENTITY-AND-AUDIT-ARCHITECTURE.md) | Complete 16-service identity map, audit gaps, proposed solutions |
| [Observability](scenarios/07-AuthZ-SHOWCASE/observability/OBSERVABILITY.md) | MLflow traces, automated scorers, Lakeview dashboard, alerts |

### Knowledge Assistant

| Scenario | Description |
|----------|-------------|
| [Multi-Team](scenarios/01-KNOWLEDGE-ASSISTANT/multi-team.md) | Engineering teams with team-specific documentation access |

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

*Last updated: 2026-03-12 -- Restructured as clean index after documentation consolidation*
