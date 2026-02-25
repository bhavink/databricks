# LLM Agent: MCP Configuration

How MCP (Model Context Protocol) is configured in two contexts: **Cursor/IDE** (dev-time) and **Databricks-deployed agents** (runtime).

---

## 1. Cursor / IDE MCP (dev-time)

When you run Databricks skills from Cursor (e.g. SQL, jobs, pipelines, Genie), the **MCP server** is configured so Cursor can call Databricks.

**Config file:** workspace root  
- `.mcp.json` or  
- `.cursor/mcp.json`

**Example:**

```json
{
  "mcpServers": {
    "databricks": {
      "command": "/path/to/python",
      "args": ["/path/to/databricks-mcp-server/run_server.py"],
      "env": {
        "DATABRICKS_CONFIG_PROFILE": "adb-wx1"
      }
    }
  }
}
```

- **Profile:** `DATABRICKS_CONFIG_PROFILE` must match a profile in `~/.databrickscfg` (e.g. `adb-wx1`).
- All MCP-based Databricks tools (execute_sql, jobs, pipelines, Genie, dashboards, etc.) use this profile.

**Change workspace:** set `DATABRICKS_CONFIG_PROFILE` to another profile name from `databricks auth profiles`.

---

## 2. Databricks-deployed LLM agent (runtime)

An agent **deployed on Databricks** (Model Serving) is configured to call MCP servers by declaring **resources** at **log time**. The platform uses these to grant access and OAuth scopes.

### Declare MCP at `mlflow.log_model()`

```python
from mlflow.deployments import get_deploy_client

# Resource types for MCP servers the agent will call
resources = [
    DatabricksGenieSpace(genie_space_id="<GENIE_SPACE_ID>"),
    DatabricksVectorSearchIndex(index_name="<CATALOG.SCHEMA.INDEX>"),
    DatabricksFunction(function_name="<CATALOG.SCHEMA.FUNCTION>"),
    DatabricksSQLWarehouse(warehouse_id="<WAREHOUSE_ID>"),
    DatabricksUCConnection(connection_name="<UC_HTTP_CONNECTION>"),  # external MCP
]

mlflow.log_model(
    agent,
    artifact_path="agent",
    resources=resources,
    # ... other params
)
```

### MCP server types (Databricks)

| Type | Resource / URL | OAuth scope (examples) |
|------|----------------|-------------------------|
| **Managed – Genie** | `DatabricksGenieSpace(genie_space_id=...)` | `dashboards.genie` |
| **Managed – Vector Search** | `DatabricksVectorSearchIndex(index_name=...)` | `vectorsearch.*` |
| **Managed – UC Functions** | `DatabricksFunction(function_name=...)` | `unity-catalog` |
| **Managed – DBSQL** | `DatabricksSQLWarehouse(warehouse_id=...)` | `sql.warehouses`, `sql.statement-execution` |
| **External** | `DatabricksUCConnection(connection_name=...)` | Via UC connection |

### OAuth scopes (example)

Only request scopes the agent needs:

```json
{
  "oauth_scopes": [
    "dashboards.genie",
    "vectorsearch.vector-search-endpoints",
    "vectorsearch.vector-search-indexes",
    "unity-catalog",
    "sql.warehouses",
    "sql.statement-execution",
    "serving.serving-endpoints"
  ]
}
```

### Auth for agent → MCP

- **Automatic passthrough:** declare MCP in `resources`; system service principal is used for auth.
- **OBO (on-behalf-of):** agent calls MCP with the end user’s identity (e.g. via `DatabricksMCPClient`).
- **External / custom MCP:** use UC HTTP connection or manual credentials (e.g. secrets); custom MCP on Apps uses OAuth only.

---

## References in this repo

- **MCP integration patterns, URLs, scopes:** `ORCHESTRATION-ARCHITECTURE.md` (§ MCP Integration Patterns, § Dependency Declaration).
- **Auth patterns (including manual for external MCP):** `01-AUTHENTICATION-PATTERNS.md`.
- **Interactive MCP flow:** `interactive/orchestration/mcp-integration.html`.

**Databricks docs:**  
[MCP connect external services](https://docs.databricks.com/aws/en/generative-ai/mcp/connect-external-services) | [Agent framework](https://docs.databricks.com/aws/en/generative-ai/agent-framework/)
