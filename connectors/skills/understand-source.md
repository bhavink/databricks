# Understand Source Skill

## Description

This skill guides research and documentation of a source system's API to enable connector implementation. Based on [upstream understand_and_document_source.md](https://github.com/databrickslabs/lakeflow-community-connectors/blob/master/prompts/understand_and_document_source.md).

## When to Use

- Phase 1 of connector development
- After planning session is complete
- Before implementing any code

---

## Instructions

### Goal

Create comprehensive API documentation file that enables connector implementation. The document must be **complete, source-cited, and implementation-ready**.

### Output

Create `sources/{connector}/{connector}_api_doc.md`

---

## Core Principles

1. **No invention** — Every claim must be backed by research. Mark gaps with `TBD:` and rationale.
2. **Single auth method** — If multiple exist, choose one preferred method; note alternatives.
3. **Complete schemas** — List all fields. No hidden fields behind links.
4. **Read operations only** — Document READ endpoints.
5. **Prefer stable APIs** — Use latest stable version. Avoid deprecated endpoints.

---

## Research Steps

### Step 1: Gather Sources

Research in this priority order:

| Priority | Source Type | Confidence |
|----------|-------------|------------|
| 1 | User-provided documentation | Highest |
| 2 | Official API documentation | High |
| 3 | Airbyte OSS implementation | Medium |
| 4 | Other implementations (Singer, dltHub) | Medium |
| 5 | Technical blogs | Low |

### Step 2: Cross-Reference

Verify every endpoint and schema against **at least two sources**.

### Step 3: Resolve Conflicts

When sources disagree:
- **Official docs** > **Actively maintained OSS** > **Other**
- If unresolved: use safer interpretation, mark `TBD:`

### Step 4: Document Requirements

Fill out every section of the template. If any section cannot be completed, add `TBD:` with explanation.

---

## Documentation Template

```markdown
# {Source_Name} API Documentation

## Research Log

| Source Type | URL | Accessed (UTC) | Confidence | What it confirmed |
|-------------|-----|----------------|------------|-------------------|
| Official Docs | https://... | 2026-02-02 | High | Auth params, rate limits |
| Airbyte | https://... | 2026-02-02 | High | Cursor field, pagination |

## Authorization

- Supported methods: {list all}
- Preferred method: {pick one}
- Parameters: {exact params and where they go}
- Example request:
```
curl -X GET "https://api.example.com/resource" \
  -H "Authorization: Bearer {token}"
```

## Object List

| Object | Description | Parent Object |
|--------|-------------|---------------|
| {object1} | {description} | None |
| {object2} | {description} | {object1} |

## Object Schemas

### {Object 1}

| Field | Type | Description | Nullable |
|-------|------|-------------|----------|
| id | string | Primary key | No |
| name | string | Display name | Yes |
| created_at | datetime | Creation timestamp | No |

## Primary Keys

| Object | Primary Key(s) |
|--------|----------------|
| {object1} | id |
| {object2} | id |

## Ingestion Types

| Object | Type | Cursor Field | Supports Deletes |
|--------|------|--------------|------------------|
| {object1} | cdc | updated_at | No |
| {object2} | append | created_at | No |

## Read API

### List {Object 1}

**Endpoint**: `GET /api/v1/{objects}`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| page | integer | No | Page number |
| per_page | integer | No | Items per page (max 100) |
| updated_since | datetime | No | Filter by update time |

**Pagination**: {cursor-based / offset-based / link-based}

**Rate Limits**: {X requests per Y seconds}

**Example Request**:
```
GET /api/v1/objects?page=1&per_page=100
```

**Example Response**:
```json
{
  "data": [...],
  "pagination": {
    "next_page": 2,
    "total": 500
  }
}
```

## Field Type Mapping

| API Type | Spark Type |
|----------|------------|
| string | StringType |
| integer | LongType |
| boolean | BooleanType |
| datetime | TimestampType |
| array | ArrayType |
| object | StructType |

## Known Quirks

- {Quirk 1}: {Description and workaround}
- {Quirk 2}: {Description and workaround}

## Test Environment

| Environment | URL | Auth | Reliability | Notes |
|-------------|-----|------|-------------|-------|
| Public sandbox | https://... | None | Low-Medium | May have downtime |
| Docker local | localhost:... | None | High | Recommended for CI |
| Production | Varies | OAuth2 | High | Requires credentials |

**Recommendation**: For reliable automated testing, prefer Docker-based environments.
```

---

## Acceptance Checklist

Before completion, verify:

- [ ] All template sections present and complete
- [ ] Every schema field listed (no omissions)
- [ ] One authentication method documented with actionable steps
- [ ] Endpoints include params, examples, and pagination
- [ ] Incremental strategy defines cursor, order, lookback
- [ ] Research Log completed with full URLs
- [ ] No unverifiable claims; gaps marked `TBD:`
