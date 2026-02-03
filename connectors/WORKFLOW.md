# Lakeflow Connector Development Workflow

> This document orchestrates the connector development process using the skills in `skills/`.

---

## Quick Start

When building a new connector:

1. **Copy the checklist below** to your connector's `DESIGN.md`
2. **Work through each phase sequentially**
3. **Get human approval** at each gate before proceeding

---

## Development Checklist Template

Copy this to `sources/{connector}/DESIGN.md` (connector-specific design doc):

```markdown
## Development Progress

### Phase 0: Planning Session ⏳
> Skill: `skills/planning-session.md`

- [ ] Define the data source and use cases
- [ ] Check if connector already exists (Databricks managed, community, third-party)
- [ ] Validate Lakeflow Connect is the right pattern
- [ ] Define scope: tables, auth methods, features for v1
- [ ] Identify risks and mitigations
- [ ] Create this DESIGN.md with all sections
- [ ] **🚦 GATE: Human approval to proceed**

### Phase 1: Understand Source ⏳
> Skill: `skills/understand-source.md`

- [ ] Research official API documentation
- [ ] Cross-reference with existing implementations (Airbyte, Singer, etc.)
- [ ] Create `{connector}_api_doc.md` with all sections:
  - [ ] Authorization documented
  - [ ] Object list complete
  - [ ] Object schemas complete
  - [ ] Primary keys documented
  - [ ] Ingestion types defined
  - [ ] Read API documented with pagination
  - [ ] Field type mapping complete
  - [ ] Research log with URLs
- [ ] **🚦 GATE: API doc reviewed and complete**

### Phase 2: Implement Connector ⏳
> Skill: `skills/implement-connector.md`

- [ ] Create `sources/{connector}/lakeflow_connect.py`
- [ ] Implement `__init__(options)`
- [ ] Implement `list_tables()`
- [ ] Implement `get_table_schema(table_name, table_options)`
- [ ] Implement `read_table_metadata(table_name, table_options)`
- [ ] Implement `read_table(table_name, start_offset, table_options)`
- [ ] Implement `read_table_deletes()` if cdc_with_deletes
- [ ] Verify all patterns followed:
  - [ ] Table name validation in each method
  - [ ] StructType preferred over MapType
  - [ ] LongType preferred over IntegerType
  - [ ] No mock objects
  - [ ] No schema conversion in read_table()
- [ ] **🚦 GATE: Code review complete**

### Phase 3: Test Connector ⏳
> Skill: `skills/test-connector.md`

- [ ] Create `sources/{connector}/test/test_{connector}_lakeflow_connect.py`
- [ ] Create `sources/{connector}/configs/dev_config.json` (temporary)
- [ ] Run tests: `pytest sources/{connector}/test/ -v`
- [ ] All test classes pass:
  - [ ] TestListTables
  - [ ] TestGetTableSchema
  - [ ] TestReadTableMetadata
  - [ ] TestReadTable
  - [ ] TestIncrementalRead
  - [ ] TestReadTableDeletes (if applicable)
- [ ] Tests run against real source (not mocked)
- [ ] **🚦 GATE: All tests green**

### Phase 4: Create Documentation ⏳
> Skill: `skills/create-documentation.md`

- [ ] Create `sources/{connector}/README.md`
- [ ] All sections complete:
  - [ ] Prerequisites
  - [ ] Setup / Connection Parameters
  - [ ] Authentication instructions
  - [ ] Unity Catalog connection instructions
  - [ ] Supported Objects table
  - [ ] Pipeline configuration examples
  - [ ] Troubleshooting section
- [ ] No internal implementation terms
- [ ] Reviewed by someone unfamiliar with connector
- [ ] **🚦 GATE: Docs approved**

### Phase 5: Finalize ⏳
- [ ] Remove `configs/dev_config.json`
- [ ] Verify `.gitignore` excludes configs
- [ ] Run full test suite one more time
- [ ] Quality checklist complete (see DESIGN.md Section 8)
- [ ] Ready for deployment
- [ ] **🚦 GATE: Ready to merge/deploy**
```

---

## Phase Details

### Phase 0: Planning Session

**Purpose**: Ensure we're building the right thing before writing code.

**Key Questions to Answer**:

| Question | Must Answer |
|----------|-------------|
| What is the data source? | Name, type, docs URL |
| Does a connector already exist? | Check Databricks, community, third-party |
| Is Lakeflow Connect the right pattern? | vs Auto Loader, Structured Streaming |
| What tables are in scope for v1? | Prioritized list |
| What auth methods are needed? | OAuth2, API key, etc. |
| What are the risks? | Rate limits, complexity, etc. |

**Output**: `sources/{connector}/DESIGN.md`

**Gate**: Human explicitly approves the plan before proceeding.

---

### Phase 1: Understand Source

**Purpose**: Research and document the source API thoroughly.

**Key Deliverables**:
- Complete API documentation following template
- Research log with all sources cited
- No unverified claims (mark gaps with `TBD:`)

**Output**: `sources/{connector}/{connector}_api_doc.md`

**Gate**: API doc reviewed for completeness.

---

### Phase 2: Implement Connector

**Purpose**: Write the connector code following all patterns.

**Key Rules**:
- Check table_name exists at start of each method
- Prefer StructType over MapType
- Use LongType over IntegerType
- No mock objects
- No schema conversion in read_table()

**Output**: `sources/{connector}/lakeflow_connect.py`

**Gate**: Code review complete.

---

### Phase 3: Test Connector

**Purpose**: Validate implementation against real source.

**Key Requirements**:
- Tests must run against real source (not mocked)
- All interface methods tested
- Incremental sync tested
- Error cases tested

**Output**: `sources/{connector}/test/test_{connector}_lakeflow_connect.py`

**Gate**: All tests pass.

---

### Phase 4: Create Documentation

**Purpose**: Create user-facing documentation.

**Key Requirements**:
- Use code as source of truth
- No internal implementation terms
- All parameters documented
- Examples provided

**Output**: `sources/{connector}/README.md`

**Gate**: Docs reviewed and approved.

---

### Phase 5: Finalize

**Purpose**: Final cleanup and quality checks.

**Key Actions**:
- Remove temporary credentials
- Final test run
- Quality checklist verification

**Gate**: Ready to deploy.

---

## Tips for Success

### Do

- ✅ Get human approval at each gate
- ✅ Follow the skills exactly
- ✅ Test against real sources
- ✅ Document everything
- ✅ Challenge assumptions early

### Don't

- ❌ Skip the planning session
- ❌ Proceed without gate approval
- ❌ Use mocks in tests
- ❌ Commit credentials
- ❌ Rush to implementation

---

## Tracking Multiple Connectors

| Connector | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Status |
|-----------|---------|---------|---------|---------|---------|---------|--------|
| healthcare | ✅ | ✅ | 🚧 | 🚧 | ⏳ | ⏳ | Phase 2/3 in progress |

Legend: ✅ Complete | ⏳ Pending | 🚧 In Progress | ❌ Blocked

---

## Lessons Learned (Updated as we build)

### Virtual Environment

**Always create a venv before starting Python development**:

```bash
cd connectors
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### External Server Reliability

Public test servers (e.g., HAPI FHIR) can be unreliable:

- Implement retry logic with exponential backoff in connectors
- Use `pytest.skip()` for tests that depend on external data
- Consider Docker-based alternatives for reliable local testing

### Test-First Development

Our workflow is: **test first → implementation later**

1. Write test that exercises the interface method
2. Run test (expect failure)
3. Implement just enough to pass
4. Refactor
5. Repeat

If a test fails due to external issues (server down), fix gracefully with skip logic.
