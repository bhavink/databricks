# Lakeflow Community Connectors - Generic Design Document

> **Version**: 1.0  
> **Created**: 2026-02-02  
> **Applies to**: All connectors in this repository

---

## 1. Overview

This document defines the **generic design patterns, workflows, and standards** that apply to ALL Lakeflow Community Connectors built in this repository. Each connector will have its own specific design document that references this generic design.

### References

- [Lakeflow Community Connectors (upstream)](https://github.com/databrickslabs/lakeflow-community-connectors)
- [Lakeflow Connect Documentation](https://docs.databricks.com/aws/en/ingestion/lakeflow-connect/)
- [SDP Python Reference](https://docs.databricks.com/aws/en/ldp/developer/python-ref)

---

## 2. Connector Development Workflow

### 2.1 Mandatory Planning Session

**Before writing any code**, every connector MUST go through a planning session:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PLANNING SESSION                                │
│                                                                         │
│  1. Define the problem                                                  │
│     - What data source are we connecting to?                           │
│     - What are the real-world use cases?                               │
│     - Who are the target users?                                        │
│                                                                         │
│  2. Challenge assumptions                                               │
│     - Does this connector already exist?                               │
│     - Is Lakeflow Connect the right pattern for this source?           │
│     - What are the alternatives?                                       │
│                                                                         │
│  3. Define scope                                                        │
│     - Which tables/resources are in scope for v1?                      │
│     - What ingestion types are needed (cdc, append, snapshot)?         │
│     - What auth methods must be supported?                             │
│                                                                         │
│  4. Identify risks                                                      │
│     - API rate limits?                                                 │
│     - Authentication complexity?                                       │
│     - Schema variability?                                              │
│     - Data volume concerns?                                            │
│                                                                         │
│  5. Acceptance criteria                                                 │
│     - What does "done" look like?                                      │
│     - How will we test?                                                │
│     - What's the MVP?                                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Development Phases

Per [upstream workflow](https://github.com/databrickslabs/lakeflow-community-connectors#developing-new-connectors):

| Phase | Skill | Output | Description |
|-------|-------|--------|-------------|
| **0** | `planning-session` | `{connector}/DESIGN.md` | Planning, questions, scope definition |
| **1** | `understand-source` | `{connector}_api_doc.md` | Research and document source API |
| **2** | `implement-connector` | `lakeflow_connect.py` | Implement LakeflowConnect interface |
| **3** | `test-connector` | `test/test_{connector}_lakeflow_connect.py` | Test against real source |
| **4** | `create-documentation` | `README.md` | User-facing documentation |

---

## 3. LakeflowConnect Interface

All connectors MUST implement this interface from [upstream](https://github.com/databrickslabs/lakeflow-community-connectors/blob/master/sources/interface/lakeflow_connect.py):

```python
class LakeflowConnect:
    def __init__(self, options: dict[str, str]) -> None:
        """Initialize with connection parameters (auth tokens, configs, etc.)"""

    def list_tables(self) -> list[str]:
        """Return names of all tables supported by this connector."""

    def get_table_schema(self, table_name: str, table_options: dict[str, str]) -> StructType:
        """Return the Spark schema for a table."""

    def read_table_metadata(self, table_name: str, table_options: dict[str, str]) -> dict:
        """Return metadata: primary_keys, cursor_field, ingestion_type."""

    def read_table(self, table_name: str, start_offset: dict, table_options: dict[str, str]) -> (Iterator[dict], dict):
        """Yield records as JSON dicts and return the next offset."""

    def read_table_deletes(self, table_name: str, start_offset: dict, table_options: dict[str, str]) -> (Iterator[dict], dict):
        """Optional: Yield deleted records. Required if ingestion_type is 'cdc_with_deletes'."""
```

### 3.1 Ingestion Types

| Type | Description | Required Fields |
|------|-------------|-----------------|
| `snapshot` | Full table reload each time | `primary_keys` |
| `cdc` | Incremental with upserts only | `primary_keys`, `cursor_field` |
| `cdc_with_deletes` | Incremental with upserts AND deletes | `primary_keys`, `cursor_field`, implement `read_table_deletes()` |
| `append` | Incremental append-only | `cursor_field` |

---

## 4. Implementation Rules

Per [upstream implement_connector.md](https://github.com/databrickslabs/lakeflow-community-connectors/blob/master/prompts/implement_connector.md):

### 4.1 Required Patterns

| Rule | Rationale |
|------|-----------|
| Check `table_name` exists at start of each function | Fail fast with clear error |
| Prefer `StructType` over `MapType` | Enforce explicit typing |
| Use `LongType` over `IntegerType` | Avoid overflow |
| Don't flatten nested JSON fields | Preserve structure |
| Use `None` not `{}` for missing StructType fields | Consistent null handling |
| No mock objects in implementation | Real data only |
| No `main()` function | Only implement class methods |
| If `cdc`/`cdc_with_deletes`: require `primary_keys` + `cursor_field` | SDP requirement |

### 4.2 Prohibited Patterns

| Pattern | Why |
|---------|-----|
| Hardcoded credentials | Security risk |
| `print()` statements | Use logging |
| Catching all exceptions silently | Hide errors |
| Infinite loops without timeout | Resource exhaustion |
| Schema conversion in `read_table()` | Return raw JSON |

---

## 5. Directory Structure

Per [upstream project structure](https://github.com/databrickslabs/lakeflow-community-connectors#project-structure):

```
connectors/                             # Root of connector development
├── DESIGN.md                           # THIS FILE - Generic design
├── WORKFLOW.md                         # Development workflow orchestration
│
├── skills/                             # Generic skills for all connectors
│   ├── planning-session.md             # Phase 0: Planning
│   ├── understand-source.md            # Phase 1: API research
│   ├── implement-connector.md          # Phase 2: Implementation
│   ├── test-connector.md               # Phase 3: Testing
│   └── create-documentation.md         # Phase 4: Documentation
│
├── sources/                            # All connectors live here
│   ├── interface/                      # Base interface (from upstream)
│   │   ├── __init__.py
│   │   ├── lakeflow_connect.py         # Base class - DO NOT MODIFY
│   │   └── README.md
│   │
│   └── {connector}/                    # Each connector (e.g., healthcare/)
│       ├── __init__.py
│       ├── DESIGN.md                   # Connector-specific design
│       ├── lakeflow_connect.py         # Main implementation (REQUIRED)
│       ├── {connector}_api_doc.md      # API documentation (REQUIRED)
│       ├── README.md                   # User documentation (REQUIRED)
│       ├── test/
│       │   └── test_{connector}_lakeflow_connect.py
│       └── configs/
│           └── dev_config.json         # Test config (DO NOT COMMIT)
│
├── libs/                               # Shared utilities
│   └── __init__.py
│
├── tests/                              # Generic test suite helpers
│   └── __init__.py
│
└── tools/                              # CLI and deployment
    └── README.md
```

### Current Structure

```
connectors/
├── DESIGN.md                           # ✅ Generic design (this file)
├── WORKFLOW.md                         # ✅ Workflow orchestration
├── pyproject.toml                      # ✅ Python packaging + pytest config
├── .venv/                              # ✅ Virtual environment (not committed)
│
├── skills/                             # ✅ Generic skills
│   ├── planning-session.md
│   ├── understand-source.md
│   ├── implement-connector.md
│   ├── test-connector.md
│   └── create-documentation.md
│
├── sources/
│   ├── __init__.py
│   ├── interface/                      # ✅ Base interface
│   │   ├── __init__.py
│   │   ├── lakeflow_connect.py
│   │   └── README.md
│   │
│   └── healthcare/                     # 🚧 Healthcare connector (Phase 2)
│       ├── __init__.py
│       ├── DESIGN.md                   # ✅ Connector-specific design
│       ├── healthcare_api_doc.md       # ✅ Phase 1 output
│       ├── lakeflow_connect.py         # 🚧 Phase 2 implementation
│       ├── test/
│       │   ├── __init__.py
│       │   └── test_healthcare_lakeflow_connect.py  # ✅ Tests
│       └── configs/
│           └── dev_config.json         # ✅ Test config (DO NOT COMMIT)
│
├── libs/                               # ✅ Placeholder
│   └── __init__.py
├── tests/                              # ✅ Placeholder
│   └── __init__.py
└── tools/                              # ✅ Placeholder
    └── README.md
```

Legend: ✅ Complete | 🚧 In Progress | ⏳ Pending

---

## 6. Testing Requirements

Per [upstream testing requirements](https://github.com/databrickslabs/lakeflow-community-connectors#tests):

### 6.1 Required Tests

| Test Type | Description | Required |
|-----------|-------------|----------|
| Generic test suite | Tests all interface methods against real source | **Yes** |
| Unit tests | Tests for complex parsing/transformation logic | Recommended |
| Write-back testing | Write → read → verify cycle | Optional |

### 6.2 Environment Setup

**ALWAYS use a virtual environment for Python-based development**:

```bash
# Create and activate virtual environment
cd connectors
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 6.3 Test Execution

```bash
# Activate venv first
source .venv/bin/activate

# Run connector tests
pytest sources/{connector}/test/test_{connector}_lakeflow_connect.py -v

# Run with coverage
pytest sources/{connector}/test/ --cov=sources/{connector} --cov-report=html
```

### 6.4 Test Configuration

- Create `sources/{connector}/configs/dev_config.json` for test credentials
- **NEVER commit this file** - add to `.gitignore`
- Remove after testing

### 6.5 External Server Reliability

When testing against public APIs or third-party servers:

| Issue | Impact | Mitigation |
|-------|--------|------------|
| Server temporarily unavailable | Tests fail unpredictably | Use `pytest.skip()` with clear message |
| Rate limiting / 429 errors | Tests fail | Implement exponential backoff |
| Server returns empty data | Tests may pass/fail | Skip gracefully, don't assert on data presence |

**Pattern for resilient tests**:

```python
def test_read_returns_data(self, connector):
    records, offset = connector.read_table("table", None, {})
    records_list = list(records)
    
    # Skip if server returned no data (external issue)
    if not records_list:
        pytest.skip("Server returned no data - may be unavailable")
    
    # Actual assertions only run if we have data
    assert all(isinstance(r, dict) for r in records_list)
```

---

## 7. Documentation Requirements

### 7.1 Required Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| API Documentation | `{connector}_api_doc.md` | Internal - research notes |
| User README | `README.md` | External - how to use |
| Connector DESIGN | `DESIGN.md` | Internal - design decisions |

### 7.2 User README Template

Per [upstream template](https://github.com/databrickslabs/lakeflow-community-connectors/blob/master/prompts/templates/community_connector_doc_template.md):

```markdown
# Lakeflow {Connector} Community Connector

## Prerequisites

## Setup

### Required Connection Parameters

### Create a Unity Catalog Connection

## Supported Objects
```

---

## 8. Quality Checklist

Before a connector is considered complete:

### 8.1 Code Quality

- [ ] All interface methods implemented
- [ ] Table name validation in each method
- [ ] Proper error handling with retry/backoff
- [ ] No hardcoded credentials
- [ ] No mock objects
- [ ] StructType preferred over MapType
- [ ] LongType preferred over IntegerType

### 8.2 Testing

- [ ] Generic test suite passes
- [ ] Tests run against real source (not mocked)
- [ ] Incremental sync tested
- [ ] Error cases tested

### 8.3 Documentation

- [ ] API doc complete (`{connector}_api_doc.md`)
- [ ] User README complete (`README.md`)
- [ ] All connection parameters documented
- [ ] All supported objects documented

### 8.4 Security

- [ ] No credentials in code
- [ ] `dev_config.json` not committed
- [ ] Secrets use Databricks Secrets syntax

---

## 9. Connectors in This Repository

| Connector | Status | Description |
|-----------|--------|-------------|
| `healthcare` | In Progress | FHIR R4 API, HL7v2 files/streams |

---

## Appendix A: Skill Reference

| Skill | When to Use |
|-------|-------------|
| `skills/planning-session.md` | Before starting any new connector |
| `skills/understand-source.md` | Phase 1 - Research source API |
| `skills/implement-connector.md` | Phase 2 - Implement LakeflowConnect |
| `skills/test-connector.md` | Phase 3 - Test implementation |
| `skills/create-documentation.md` | Phase 4 - Create user docs |
