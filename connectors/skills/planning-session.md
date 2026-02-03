# Planning Session Skill

## Description

This skill guides the initial planning session for any new Lakeflow Community Connector. It ensures we ask the right questions, challenge assumptions, and define clear scope BEFORE writing any code.

## When to Use

- Starting a new connector project
- Evaluating whether a connector should be built
- Scoping a new phase of an existing connector

---

## Instructions

### Step 1: Understand the Request

Ask clarifying questions about:

1. **Data Source**
   - What is the source system? (SaaS API, database, file format, etc.)
   - What is the official documentation URL?
   - Are there existing connectors? (Airbyte, Singer, dltHub, etc.)

2. **Use Cases**
   - What are the primary use cases?
   - Who are the target users?
   - What analytics/ML will be built on this data?

3. **Data Characteristics**
   - What entities/tables need to be ingested?
   - What is the expected data volume?
   - How frequently does data change?

### Step 2: Challenge Assumptions

Ask critical questions:

1. **Does this connector already exist?**
   - Check Databricks managed connectors
   - Check Lakeflow Community Connectors
   - Check Airbyte/Singer/dltHub

2. **Is Lakeflow Connect the right pattern?**
   - REST API → Good fit
   - Database CDC → Consider managed connector
   - Files in cloud storage → Consider Auto Loader
   - Streaming → Consider Structured Streaming

3. **What are the alternatives?**
   - Could we use Lakehouse Federation instead?
   - Could we use an existing third-party tool?

### Step 3: Define Scope

Establish clear boundaries:

1. **Tables/Resources**
   - Which tables are in scope for v1?
   - Which tables are explicitly out of scope?
   - What's the prioritization?

2. **Ingestion Types**
   - Which tables need `cdc`?
   - Which tables are `append` only?
   - Which need `snapshot`?
   - Do any need `cdc_with_deletes`?

3. **Authentication**
   - What auth methods must be supported in v1?
   - OAuth2? API Key? Basic Auth?
   - Are there different auth for different environments?

4. **Features**
   - Rate limiting required?
   - Retry/backoff?
   - Incremental sync?

### Step 4: Identify Risks

Explicitly call out:

| Risk Category | Questions to Ask |
|---------------|------------------|
| **API Limits** | Rate limits? Pagination limits? Timeout limits? |
| **Auth Complexity** | OAuth flows? Token refresh? MFA? |
| **Schema** | Static or dynamic? How often does it change? |
| **Data Volume** | Expected records per table? Growth rate? |
| **Testing** | Can we test against real/sandbox environment? |
| **Dependencies** | Required libraries? Version constraints? |

### Step 5: Define Acceptance Criteria

Establish "done" criteria:

```markdown
## Acceptance Criteria for {Connector} v1

### Must Have
- [ ] Specific criterion 1
- [ ] Specific criterion 2

### Should Have
- [ ] Specific criterion 3

### Won't Have (v1)
- Explicitly excluded feature 1
- Explicitly excluded feature 2

### Testing
- [ ] Passes generic test suite against {test environment}
- [ ] Incremental sync validated
```

### Step 6: Create Connector Design Doc

Output: Create `sources/{connector}/DESIGN.md` with:

1. Executive Summary (from this session)
2. Scope (tables, auth, features)
3. Risks and mitigations
4. Acceptance criteria
5. Build phases with specific deliverables

---

## Output Template

```markdown
# {Connector} Connector - Design Document

> **Created**: {date}
> **Status**: Planning Complete

## 1. Overview

### Problem Statement
{What problem does this connector solve?}

### Target Users
{Who will use this connector?}

### Use Cases
{Primary use cases}

## 2. Source Analysis

### Source System
- Name: {name}
- Type: {REST API / Database / File Format / etc.}
- Documentation: {URL}

### Existing Solutions
- Databricks managed: {Yes/No - details}
- Community connector: {Yes/No - details}
- Third-party: {Airbyte/Singer/etc. - details}

### Recommendation
{Why build this connector vs alternatives}

## 3. Scope

### In Scope (v1)
| Table | Ingestion Type | Priority |
|-------|---------------|----------|
| {table1} | cdc | P0 |
| {table2} | append | P0 |

### Out of Scope (v1)
- {Feature 1} - Reason
- {Feature 2} - Reason

### Authentication
- v1: {Method}
- Future: {Other methods}

## 4. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {Risk 1} | High/Med/Low | High/Med/Low | {Mitigation} |

## 5. Acceptance Criteria

### Must Have
- [ ] {Criterion 1}
- [ ] {Criterion 2}

### Testing
- [ ] Passes against {test environment}

## 6. Build Phases

### Phase 1: {Description}
- [ ] Deliverable 1
- [ ] Deliverable 2

### Phase 2: {Description}
- [ ] Deliverable 1
```

---

## Checklist Before Proceeding

- [ ] All clarifying questions answered
- [ ] Assumptions explicitly challenged
- [ ] Scope clearly defined (in/out)
- [ ] Risks identified with mitigations
- [ ] Acceptance criteria established
- [ ] Design doc created
- [ ] User has approved the plan
