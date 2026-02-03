# Lakeflow Healthcare Connector - Design Document

> **Version**: 1.0  
> **Created**: 2026-02-02  
> **Status**: Draft  
> **Parent Doc**: [../../DESIGN.md](../../DESIGN.md) (Generic Connector Design)

---

## 1. Executive Summary

This document defines the **healthcare-specific** design for a Lakeflow Community Connector. For generic patterns, interface definitions, and workflow, see the [parent design document](../../DESIGN.md).

### Problem Statement

Healthcare organizations need to ingest clinical data from:
- **FHIR R4 REST APIs** (Epic, Cerner, HAPI FHIR)
- **HL7v2 files** dumped to cloud storage (S3, GCS, ADLS)
- **HL7v2 streams** from message buses (Kafka, Kinesis, EventHub)

### Target Users

- Healthcare data engineers
- Clinical analytics teams
- Health IT integration specialists

### Use Cases

1. Build patient 360 views from FHIR data
2. Ingest real-time ADT events for bed management
3. Aggregate lab results (ORU messages) for analytics
4. Support regulatory reporting (CMS, state registries)

### Goals (Healthcare-Specific)

1. Support FHIR R4 specification with incremental sync
2. Parse HL7v2 message types (ADT, ORM, ORU, SIU)
3. Handle healthcare-specific authentication (OAuth2, SMART on FHIR)
4. Comply with HIPAA considerations (no PHI in logs)

### Non-Goals (v1)

- Bulk FHIR API ($export) support
- SMART on FHIR authorization flows
- FHIR STU3 or DSTU2 versions
- HL7v3 (CDA) support
- Write-back to source systems

---

## 2. Scope

### In Scope (v1)

| Table | Source | Ingestion Type | Priority |
|-------|--------|---------------|----------|
| `patients` | FHIR Patient | cdc | P0 |
| `encounters` | FHIR Encounter | cdc | P0 |
| `observations` | FHIR Observation | append | P0 |
| `conditions` | FHIR Condition | cdc | P1 |
| `medications` | FHIR MedicationRequest | cdc | P1 |

### Out of Scope (v1)

- HL7v2 file ingestion (Phase 3)
- HL7v2 streaming (Phase 4)
- Bulk FHIR API
- SMART on FHIR auth

### Authentication (v1)

- No auth (HAPI public server)
- API Key
- OAuth2 (client credentials)

---

## 3. Data Model

### 3.1 FHIR R4 Tables

| Table | FHIR Resource | Ingestion Type | Primary Key | Cursor Field |
|-------|---------------|----------------|-------------|--------------|
| `patients` | Patient | cdc | id | meta.lastUpdated |
| `encounters` | Encounter | cdc | id | meta.lastUpdated |
| `observations` | Observation | append | id | meta.lastUpdated |
| `conditions` | Condition | cdc | id | meta.lastUpdated |
| `medications` | MedicationRequest | cdc | id | meta.lastUpdated |

### 3.2 HL7v2 Tables (Phase 3+)

| Table | Message Types | Ingestion Type | Primary Key | Cursor Field |
|-------|---------------|----------------|-------------|--------------|
| `adt_messages` | ADT^A01-A60 | append | message_control_id | message_datetime |
| `orm_messages` | ORM^O01 | append | message_control_id | message_datetime |
| `oru_messages` | ORU^R01 | append | message_control_id | message_datetime |

---

## 4. Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `fhir.resources` | >=7.0.0 | FHIR R4 Pydantic models |
| `requests` | >=2.28.0 | HTTP client |
| `pyspark` | >=3.5.0 | Spark integration |

---

## 5. Build Phases

### Phase 1: Foundation + API Documentation ✅
- [x] Project structure per upstream
- [x] `healthcare_api_doc.md` complete
- [x] Parser unit tests (deferred - FHIR uses `fhir.resources`)

### Phase 2: FHIR API Mode 🚧
- [x] `lakeflow_connect.py` skeleton implemented
- [x] Basic tests pass (with server reliability handling)
- [x] 5 core resources defined: `patients`, `encounters`, `observations`, `conditions`, `medications`
- [ ] OAuth2 client credentials flow
- [ ] Full pagination support
- [ ] Rate limiting

### Phase 3: HL7v2 Files Mode ⏳
- [ ] File discovery + parsing
- [ ] S3/GCS/ADLS support

### Phase 4: HL7v2 Stream Mode ⏳
- [ ] Kafka consumer
- [ ] Offset tracking

### Phase 5: Documentation ⏳
- [ ] `README.md` complete
- [ ] Connector spec YAML

---

## 6. Lessons Learned

### 6.1 HAPI FHIR Server Reliability

The public HAPI FHIR server (`hapi.fhir.org`) is **unreliable** for testing:

| Issue | Frequency | Mitigation |
|-------|-----------|------------|
| 500 Server Errors (`CannotCreateTransactionException`) | Common | Retry with backoff |
| `_sort=_lastUpdated` not supported | Always | Don't use sort param |
| Empty responses | Occasional | Skip test gracefully |

**Recommendation**: For production testing, use a private FHIR server or Docker-based HAPI instance.

### 6.2 Test Resilience Pattern

Tests against external servers should:
1. Implement `pytest.skip()` when server returns no data
2. Not fail CI due to external service unavailability
3. Use `@pytest.mark.integration` to separate from unit tests

---

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FHIR server rate limits | High | Medium | Implement rate limiting |
| Schema variability across servers | Medium | High | Use fhir.resources for validation |
| HL7v2 parsing complexity | Medium | Medium | Start with common segments only |
| Public test server instability | High | Medium | Use Docker HAPI or skip tests gracefully |
| OAuth2 flow complexity | Medium | Medium | Document per-vendor differences |

---

## 8. References

- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [HAPI FHIR Public Server](https://hapi.fhir.org/)
- [fhir.resources PyPI](https://pypi.org/project/fhir.resources/)
- [HAPI FHIR Docker](https://hub.docker.com/r/hapiproject/hapi) - For reliable local testing
