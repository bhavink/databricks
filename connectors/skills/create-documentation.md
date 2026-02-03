# Create Documentation Skill

## Description

This skill guides creation of user-facing documentation for a connector. Based on [upstream create_connector_documentation.md](https://github.com/databrickslabs/lakeflow-community-connectors/blob/master/prompts/create_connector_documentation.md).

## When to Use

- Phase 4 of connector development
- After tests pass
- Final step before connector is complete

---

## Instructions

### Goal

Generate **public-facing documentation** targeted at end users who will configure and use the connector.

### Input

- `sources/{connector}/lakeflow_connect.py` (implementation)
- `sources/{connector}/{connector}_api_doc.md` (API docs)

### Output

- `sources/{connector}/README.md`

---

## Documentation Requirements

1. **Use code implementation as source of truth**
2. **AVOID mentioning internal implementation terms** (function names, class names, etc.)
3. **Focus on user tasks**: How do I configure? What can I ingest?
4. **Be specific**: Exact parameter names, exact object names

---

## README Template

```markdown
# Lakeflow {Connector Name} Community Connector

This documentation provides setup instructions and reference information for the {Connector Name} connector.

## Overview

{Brief description of what this connector does and what data it ingests.}

## Prerequisites

Before configuring this connector, ensure you have:

- [ ] {Prerequisite 1, e.g., "API credentials from the source system"}
- [ ] {Prerequisite 2, e.g., "Network access to the API endpoint"}
- [ ] {Prerequisite 3, e.g., "Appropriate permissions in Unity Catalog"}

## Setup

### Required Connection Parameters

To configure the connector, provide the following parameters:

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `base_url` | Yes | Base URL of the API | `https://api.example.com` |
| `auth_type` | Yes | Authentication type | `oauth2`, `api_key`, `basic` |
| `api_key` | If auth_type=api_key | API key for authentication | `sk_live_xxx` |

### Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rate_limit` | 10 | Requests per second |
| `timeout` | 30 | Request timeout in seconds |

### Authentication

#### Option 1: API Key

1. Obtain an API key from {source system admin console}
2. Configure the connection with:
   - `auth_type`: `api_key`
   - `api_key`: Your API key

#### Option 2: OAuth2

1. Create an OAuth2 application in {source system}
2. Note your `client_id` and `client_secret`
3. Configure the connection with:
   - `auth_type`: `oauth2`
   - `client_id`: Your client ID
   - `client_secret`: Your client secret
   - `token_url`: Token endpoint URL

### Create a Unity Catalog Connection

A Unity Catalog connection for this connector can be created in two ways:

#### Via UI

1. Navigate to **Catalog** > **External Data** > **Connections**
2. Click **Create Connection**
3. Select **Lakeflow Community Connector**
4. Select **{Connector Name}**
5. Enter the required parameters
6. Click **Create**

#### Via API

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

connection = w.connections.create(
    name="my_{connector}_connection",
    connection_type="LAKEFLOW_COMMUNITY_CONNECTOR",
    options={
        "source": "{connector}",
        "base_url": "https://api.example.com",
        "auth_type": "api_key",
        "api_key": "YOUR_API_KEY",
    }
)
```

## Supported Objects

This connector supports ingesting the following objects:

| Object | Description | Ingestion Type | Primary Key |
|--------|-------------|----------------|-------------|
| `{object1}` | {Description} | CDC | `id` |
| `{object2}` | {Description} | Append | `id` |
| `{object3}` | {Description} | Snapshot | `id` |

### Ingestion Types

- **CDC**: Incremental ingestion with change tracking. Only new and modified records are ingested.
- **Append**: Incremental ingestion of new records only.
- **Snapshot**: Full table refresh on each run.

## Pipeline Configuration

### Basic Example

```yaml
objects:
  - table:
      source_table: "{object1}"
      destination_table: "my_{object1}"
```

### With Table Options

```yaml
objects:
  - table:
      source_table: "{object1}"
      destination_table: "my_{object1}"
      table_configuration:
        scd_type: "SCD_TYPE_1"
        primary_keys: ["id"]
```

### Multiple Objects

```yaml
objects:
  - table:
      source_table: "{object1}"
  - table:
      source_table: "{object2}"
  - table:
      source_table: "{object3}"
```

## Object-Specific Options

Some objects support additional configuration:

### {Object with Options}

| Option | Description | Default |
|--------|-------------|---------|
| `{option1}` | {Description} | `{default}` |

Example:

```yaml
objects:
  - table:
      source_table: "{object}"
      table_configuration:
        {option1}: "{value}"
```

## Limitations

- {Limitation 1}
- {Limitation 2}
- {Limitation 3}

## Troubleshooting

### Common Issues

#### Authentication Errors

**Symptom**: `401 Unauthorized` errors

**Solution**: 
1. Verify your credentials are correct
2. Check that your API key/OAuth app has the required permissions
3. Ensure the token hasn't expired

#### Rate Limiting

**Symptom**: `429 Too Many Requests` errors

**Solution**:
1. Reduce the `rate_limit` parameter
2. Schedule pipelines during off-peak hours

#### Missing Data

**Symptom**: Expected records not appearing

**Solution**:
1. Check the cursor field is updating correctly
2. Verify permissions to access the data in the source system

## Support

For issues specific to this connector, please file an issue at:
{repository URL}/issues
```

---

## Writing Guidelines

### Do

- Use clear, simple language
- Provide specific examples
- Include all parameter names exactly as used
- Document all supported objects
- Explain ingestion types

### Don't

- Mention internal class/function names
- Use technical jargon without explanation
- Leave placeholders unfilled
- Skip error cases

---

## Acceptance Checklist

- [ ] All sections of template filled
- [ ] Prerequisites clearly stated
- [ ] All parameters documented with examples
- [ ] All supported objects listed
- [ ] Pipeline configuration examples provided
- [ ] Troubleshooting section included
- [ ] No internal implementation terms
- [ ] Tested by someone unfamiliar with the connector
