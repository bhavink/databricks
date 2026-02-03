# FHIR R4 API Documentation

> **Source**: Healthcare Connector  
> **Version**: 1.0  
> **Created**: 2026-02-02  
> **Status**: Phase 1 Complete

---

## Research Log

| Source Type | URL | Accessed (UTC) | Confidence | What it confirmed |
|-------------|-----|----------------|------------|-------------------|
| Official Docs | https://hl7.org/fhir/R4/http.html | 2026-02-02 | High | RESTful API, search params, pagination |
| Official Docs | https://hl7.org/fhir/R4/patient.html | 2026-02-02 | High | Patient schema, search params |
| Official Docs | https://hl7.org/fhir/R4/observation.html | 2026-02-02 | High | Observation schema, search params |
| Official Docs | https://hl7.org/fhir/R4/search.html | 2026-02-02 | High | Search params, _lastUpdated, pagination |
| Test Server | https://hapi.fhir.org/baseR4 | 2026-02-02 | High | Live endpoint, public access |
| Airbyte | https://airbyte.com/tutorials/healthcare-data-integration-fhir-airbyte-ai-assistant | 2026-02-02 | Medium | OAuth2, pagination patterns |

---

## Authorization

### Supported Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| None | No authentication | Public test servers (HAPI FHIR) |
| API Key | Static token in header | Simple integrations |
| OAuth2 (Client Credentials) | Token-based auth | Production EHR systems |
| SMART on FHIR | OAuth2 + scopes | Patient-facing apps (v2) |

### Preferred Method: OAuth2 Client Credentials

For production use, OAuth2 client credentials flow is recommended.

### Parameters

| Parameter | Location | Required | Description |
|-----------|----------|----------|-------------|
| `client_id` | OAuth request | Yes | Application client ID |
| `client_secret` | OAuth request | Yes | Application secret |
| `token_url` | Config | Yes | Token endpoint URL |
| `scope` | OAuth request | No | Requested scopes (e.g., `system/*.read`) |

### Example Request (No Auth - HAPI FHIR)

```bash
curl -X GET "https://hapi.fhir.org/baseR4/Patient?_count=10" \
  -H "Accept: application/fhir+json"
```

### Example Request (OAuth2)

```bash
# Step 1: Get access token
curl -X POST "https://auth.example.com/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id={id}&client_secret={secret}"

# Step 2: Use token
curl -X GET "https://fhir.example.com/R4/Patient" \
  -H "Authorization: Bearer {access_token}" \
  -H "Accept: application/fhir+json"
```

---

## Object List

| Object | FHIR Resource | Description | Parent Object |
|--------|---------------|-------------|---------------|
| `patients` | Patient | Demographics and administrative info | None |
| `encounters` | Encounter | Healthcare interaction event | patients |
| `observations` | Observation | Measurements and assessments | patients |
| `conditions` | Condition | Clinical conditions and diagnoses | patients |
| `medications` | MedicationRequest | Medication prescriptions | patients |
| `procedures` | Procedure | Clinical procedures performed | patients |
| `practitioners` | Practitioner | Healthcare providers | None |
| `organizations` | Organization | Healthcare organizations | None |

---

## Object Schemas

### Patient

| Field | Type | Description | Nullable |
|-------|------|-------------|----------|
| `id` | string | Logical resource ID | No |
| `meta.versionId` | string | Version identifier | Yes |
| `meta.lastUpdated` | instant | Last modification timestamp | Yes |
| `identifier` | array[Identifier] | Business identifiers (MRN, SSN, etc.) | Yes |
| `active` | boolean | Whether record is in active use | Yes |
| `name` | array[HumanName] | Patient names | Yes |
| `telecom` | array[ContactPoint] | Contact details | Yes |
| `gender` | code | male / female / other / unknown | Yes |
| `birthDate` | date | Date of birth | Yes |
| `deceasedBoolean` | boolean | Deceased indicator | Yes |
| `deceasedDateTime` | dateTime | Date/time of death | Yes |
| `address` | array[Address] | Patient addresses | Yes |
| `maritalStatus` | CodeableConcept | Marital status | Yes |
| `multipleBirthBoolean` | boolean | Multiple birth indicator | Yes |
| `multipleBirthInteger` | integer | Birth order | Yes |
| `photo` | array[Attachment] | Patient photos | Yes |
| `contact` | array[BackboneElement] | Emergency contacts | Yes |
| `communication` | array[BackboneElement] | Languages spoken | Yes |
| `generalPractitioner` | array[Reference] | Primary care providers | Yes |
| `managingOrganization` | Reference | Custodian organization | Yes |
| `link` | array[BackboneElement] | Links to other patient records | Yes |

### Encounter

| Field | Type | Description | Nullable |
|-------|------|-------------|----------|
| `id` | string | Logical resource ID | No |
| `meta.lastUpdated` | instant | Last modification timestamp | Yes |
| `identifier` | array[Identifier] | Business identifiers | Yes |
| `status` | code | planned / arrived / triaged / in-progress / onleave / finished / cancelled | No |
| `class` | Coding | Classification (inpatient, outpatient, emergency) | No |
| `type` | array[CodeableConcept] | Specific encounter type | Yes |
| `serviceType` | CodeableConcept | Service category | Yes |
| `priority` | CodeableConcept | Urgency | Yes |
| `subject` | Reference(Patient) | Patient reference | Yes |
| `episodeOfCare` | array[Reference] | Episode(s) of care | Yes |
| `basedOn` | array[Reference] | Service requests | Yes |
| `participant` | array[BackboneElement] | Participants (practitioners) | Yes |
| `appointment` | array[Reference] | Appointment references | Yes |
| `period` | Period | Start and end time | Yes |
| `length` | Duration | Duration of encounter | Yes |
| `reasonCode` | array[CodeableConcept] | Reason for encounter | Yes |
| `reasonReference` | array[Reference] | Conditions/observations as reason | Yes |
| `diagnosis` | array[BackboneElement] | Diagnoses | Yes |
| `hospitalization` | BackboneElement | Admission details | Yes |
| `location` | array[BackboneElement] | Locations visited | Yes |
| `serviceProvider` | Reference(Organization) | Responsible organization | Yes |
| `partOf` | Reference(Encounter) | Parent encounter | Yes |

### Observation

| Field | Type | Description | Nullable |
|-------|------|-------------|----------|
| `id` | string | Logical resource ID | No |
| `meta.lastUpdated` | instant | Last modification timestamp | Yes |
| `identifier` | array[Identifier] | Business identifiers | Yes |
| `basedOn` | array[Reference] | Fulfills plan/order | Yes |
| `partOf` | array[Reference] | Part of referenced event | Yes |
| `status` | code | registered / preliminary / final / amended / corrected / cancelled / entered-in-error / unknown | No |
| `category` | array[CodeableConcept] | Classification (vital-signs, laboratory, etc.) | Yes |
| `code` | CodeableConcept | Type of observation (LOINC code) | No |
| `subject` | Reference(Patient) | Patient reference | Yes |
| `focus` | array[Reference] | Actual focus if not subject | Yes |
| `encounter` | Reference(Encounter) | Related encounter | Yes |
| `effectiveDateTime` | dateTime | Clinically relevant time | Yes |
| `effectivePeriod` | Period | Clinically relevant period | Yes |
| `issued` | instant | Date/time made available | Yes |
| `performer` | array[Reference] | Who performed observation | Yes |
| `valueQuantity` | Quantity | Numeric result | Yes |
| `valueCodeableConcept` | CodeableConcept | Coded result | Yes |
| `valueString` | string | Text result | Yes |
| `valueBoolean` | boolean | Boolean result | Yes |
| `valueInteger` | integer | Integer result | Yes |
| `valueRange` | Range | Range result | Yes |
| `valueRatio` | Ratio | Ratio result | Yes |
| `valueSampledData` | SampledData | Waveform data | Yes |
| `valueTime` | time | Time result | Yes |
| `valueDateTime` | dateTime | DateTime result | Yes |
| `valuePeriod` | Period | Period result | Yes |
| `dataAbsentReason` | CodeableConcept | Why result is missing | Yes |
| `interpretation` | array[CodeableConcept] | High/low/normal | Yes |
| `note` | array[Annotation] | Comments | Yes |
| `bodySite` | CodeableConcept | Body site observed | Yes |
| `method` | CodeableConcept | Method used | Yes |
| `specimen` | Reference(Specimen) | Specimen used | Yes |
| `device` | Reference(Device) | Measurement device | Yes |
| `referenceRange` | array[BackboneElement] | Normal ranges | Yes |
| `hasMember` | array[Reference] | Related observations | Yes |
| `derivedFrom` | array[Reference] | Source observations | Yes |
| `component` | array[BackboneElement] | Component observations | Yes |

### Condition

| Field | Type | Description | Nullable |
|-------|------|-------------|----------|
| `id` | string | Logical resource ID | No |
| `meta.lastUpdated` | instant | Last modification timestamp | Yes |
| `identifier` | array[Identifier] | Business identifiers | Yes |
| `clinicalStatus` | CodeableConcept | active / recurrence / relapse / inactive / remission / resolved | Yes |
| `verificationStatus` | CodeableConcept | unconfirmed / provisional / differential / confirmed / refuted / entered-in-error | Yes |
| `category` | array[CodeableConcept] | problem-list-item / encounter-diagnosis | Yes |
| `severity` | CodeableConcept | Subjective severity | Yes |
| `code` | CodeableConcept | Condition code (SNOMED CT, ICD-10) | Yes |
| `bodySite` | array[CodeableConcept] | Anatomical location | Yes |
| `subject` | Reference(Patient) | Patient reference | No |
| `encounter` | Reference(Encounter) | Related encounter | Yes |
| `onsetDateTime` | dateTime | Onset date/time | Yes |
| `onsetAge` | Age | Onset age | Yes |
| `onsetPeriod` | Period | Onset period | Yes |
| `onsetRange` | Range | Onset range | Yes |
| `onsetString` | string | Onset description | Yes |
| `abatementDateTime` | dateTime | Resolution date | Yes |
| `abatementAge` | Age | Resolution age | Yes |
| `abatementPeriod` | Period | Resolution period | Yes |
| `abatementRange` | Range | Resolution range | Yes |
| `abatementString` | string | Resolution description | Yes |
| `recordedDate` | dateTime | Date recorded | Yes |
| `recorder` | Reference | Who recorded | Yes |
| `asserter` | Reference | Who asserted | Yes |
| `stage` | array[BackboneElement] | Stage/grade | Yes |
| `evidence` | array[BackboneElement] | Supporting evidence | Yes |
| `note` | array[Annotation] | Additional notes | Yes |

### MedicationRequest

| Field | Type | Description | Nullable |
|-------|------|-------------|----------|
| `id` | string | Logical resource ID | No |
| `meta.lastUpdated` | instant | Last modification timestamp | Yes |
| `identifier` | array[Identifier] | Business identifiers | Yes |
| `status` | code | active / on-hold / cancelled / completed / entered-in-error / stopped / draft / unknown | No |
| `statusReason` | CodeableConcept | Reason for status | Yes |
| `intent` | code | proposal / plan / order / original-order / reflex-order / filler-order / instance-order / option | No |
| `category` | array[CodeableConcept] | Medication category | Yes |
| `priority` | code | routine / urgent / asap / stat | Yes |
| `doNotPerform` | boolean | Request to not perform | Yes |
| `reportedBoolean` | boolean | Reported vs primary | Yes |
| `reportedReference` | Reference | Source of report | Yes |
| `medicationCodeableConcept` | CodeableConcept | Medication code | Yes |
| `medicationReference` | Reference(Medication) | Medication reference | Yes |
| `subject` | Reference(Patient) | Patient reference | No |
| `encounter` | Reference(Encounter) | Related encounter | Yes |
| `supportingInformation` | array[Reference] | Supporting info | Yes |
| `authoredOn` | dateTime | When request was made | Yes |
| `requester` | Reference | Who requested | Yes |
| `performer` | Reference | Intended performer | Yes |
| `performerType` | CodeableConcept | Type of performer | Yes |
| `recorder` | Reference | Who recorded | Yes |
| `reasonCode` | array[CodeableConcept] | Reason for request | Yes |
| `reasonReference` | array[Reference] | Conditions as reason | Yes |
| `instantiatesCanonical` | array[canonical] | Protocol followed | Yes |
| `instantiatesUri` | array[uri] | External protocol | Yes |
| `basedOn` | array[Reference] | Request fulfilled | Yes |
| `groupIdentifier` | Identifier | Group identifier | Yes |
| `courseOfTherapyType` | CodeableConcept | Course type | Yes |
| `insurance` | array[Reference] | Insurance coverage | Yes |
| `note` | array[Annotation] | Notes | Yes |
| `dosageInstruction` | array[Dosage] | Dosage instructions | Yes |
| `dispenseRequest` | BackboneElement | Dispensing info | Yes |
| `substitution` | BackboneElement | Substitution info | Yes |
| `priorPrescription` | Reference | Prior prescription | Yes |
| `detectedIssue` | array[Reference] | Clinical issues | Yes |
| `eventHistory` | array[Reference] | Lifecycle events | Yes |

---

## Primary Keys

| Object | Primary Key(s) | Notes |
|--------|----------------|-------|
| `patients` | id | Logical resource ID, server-assigned |
| `encounters` | id | Logical resource ID |
| `observations` | id | Logical resource ID |
| `conditions` | id | Logical resource ID |
| `medications` | id | Logical resource ID |
| `procedures` | id | Logical resource ID |
| `practitioners` | id | Logical resource ID |
| `organizations` | id | Logical resource ID |

---

## Ingestion Types

| Object | Type | Cursor Field | Supports Deletes | Notes |
|--------|------|--------------|------------------|-------|
| `patients` | cdc | meta.lastUpdated | No | Records updated frequently |
| `encounters` | cdc | meta.lastUpdated | No | Status changes over time |
| `observations` | append | meta.lastUpdated | No | High volume, rarely updated |
| `conditions` | cdc | meta.lastUpdated | No | Status may change |
| `medications` | cdc | meta.lastUpdated | No | Status changes frequently |
| `procedures` | append | meta.lastUpdated | No | Once recorded, rarely updated |
| `practitioners` | snapshot | - | No | Reference data, low volume |
| `organizations` | snapshot | - | No | Reference data, low volume |

---

## Read API

### List Resources (Search)

**Endpoint**: `GET [base]/[ResourceType]`

**Common Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `_count` | integer | No | Number of results per page (default varies, max 1000) |
| `_lastUpdated` | date | No | Filter by last updated time (supports gt, lt, ge, le prefixes) |
| `_id` | token | No | Filter by resource ID |
| `_sort` | string | No | Sort order (prefix with `-` for descending) |

**Pagination**: Link-based (Bundle.link with relation "next")

**Rate Limits**: Server-dependent (HAPI FHIR: ~10 req/sec, Production EHRs: varies)

### List Patients

**Endpoint**: `GET [base]/Patient`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `_count` | integer | No | Results per page |
| `_lastUpdated` | date | No | Filter by modification time |
| `identifier` | token | No | Patient identifier (e.g., MRN) |
| `name` | string | No | Patient name |
| `birthdate` | date | No | Date of birth |
| `gender` | token | No | Gender code |

**Example Request**:

```bash
GET [base]/Patient?_count=100&_lastUpdated=gt2024-01-01&_sort=-_lastUpdated
```

**Example Response**:

```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 1250,
  "link": [
    {
      "relation": "self",
      "url": "https://fhir.example.com/R4/Patient?_count=100&_lastUpdated=gt2024-01-01"
    },
    {
      "relation": "next",
      "url": "https://fhir.example.com/R4?_getpages=abc123&_getpagesoffset=100&_count=100"
    }
  ],
  "entry": [
    {
      "fullUrl": "https://fhir.example.com/R4/Patient/12345",
      "resource": {
        "resourceType": "Patient",
        "id": "12345",
        "meta": {
          "versionId": "1",
          "lastUpdated": "2024-01-15T10:30:00Z"
        },
        "identifier": [
          {
            "system": "http://hospital.example.com/mrn",
            "value": "MRN12345"
          }
        ],
        "name": [
          {
            "use": "official",
            "family": "Smith",
            "given": ["John", "Q"]
          }
        ],
        "gender": "male",
        "birthDate": "1980-01-15"
      },
      "search": {
        "mode": "match"
      }
    }
  ]
}
```

### List Observations

**Endpoint**: `GET [base]/Observation`

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `_count` | integer | No | Results per page |
| `_lastUpdated` | date | No | Filter by modification time |
| `patient` | reference | No | Patient reference |
| `subject` | reference | No | Subject reference (Patient/Group/Device/Location) |
| `code` | token | No | Observation code (LOINC) |
| `category` | token | No | Category (vital-signs, laboratory, etc.) |
| `date` | date | No | Effective date/time |
| `status` | token | No | Observation status |

**Example Request**:

```bash
GET [base]/Observation?_count=100&_lastUpdated=gt2024-01-01&category=laboratory
```

### Incremental Read Strategy

To read incrementally:

1. **Initial Load**: `GET [base]/[ResourceType]?_count=100&_sort=_lastUpdated`
2. **Track Offset**: Store the highest `meta.lastUpdated` from the response
3. **Subsequent Reads**: `GET [base]/[ResourceType]?_count=100&_lastUpdated=gt{offset}&_sort=_lastUpdated`

**Example**:

```bash
# Initial load
GET [base]/Patient?_count=100&_sort=_lastUpdated

# Response includes patient with meta.lastUpdated = "2024-01-15T10:30:00Z"
# Store this as offset

# Next incremental load
GET [base]/Patient?_count=100&_lastUpdated=gt2024-01-15T10:30:00Z&_sort=_lastUpdated
```

### Pagination

FHIR uses link-based pagination via the Bundle response:

```json
{
  "resourceType": "Bundle",
  "type": "searchset",
  "total": 5000,
  "link": [
    {"relation": "self", "url": "...current page URL..."},
    {"relation": "next", "url": "...next page URL..."},
    {"relation": "previous", "url": "...previous page URL..."}
  ],
  "entry": [...]
}
```

**Rules**:
- Follow `next` links until no more pages
- `total` may be approximate or exact (server-dependent)
- Page URLs are opaque; don't construct them manually

---

## Field Type Mapping

| FHIR Type | Spark Type | Notes |
|-----------|------------|-------|
| `string` | StringType | |
| `boolean` | BooleanType | |
| `integer` | LongType | Use Long to avoid overflow |
| `positiveInt` | LongType | |
| `unsignedInt` | LongType | |
| `decimal` | DoubleType | Or StringType for precision |
| `instant` | TimestampType | ISO 8601 with timezone |
| `dateTime` | TimestampType | May have varying precision |
| `date` | DateType | |
| `time` | StringType | HH:MM:SS format |
| `code` | StringType | |
| `uri` | StringType | |
| `url` | StringType | |
| `canonical` | StringType | |
| `base64Binary` | BinaryType | Or StringType |
| `id` | StringType | 1-64 chars, [A-Za-z0-9\-\.] |
| `Identifier` | StructType | {system, value, use, type, period, assigner} |
| `HumanName` | StructType | {use, text, family, given[], prefix[], suffix[], period} |
| `Address` | StructType | {use, type, text, line[], city, district, state, postalCode, country, period} |
| `ContactPoint` | StructType | {system, value, use, rank, period} |
| `CodeableConcept` | StructType | {coding[], text} |
| `Coding` | StructType | {system, version, code, display, userSelected} |
| `Quantity` | StructType | {value, comparator, unit, system, code} |
| `Period` | StructType | {start, end} |
| `Reference` | StructType | {reference, type, identifier, display} |
| `Annotation` | StructType | {authorReference, authorString, time, text} |
| `array[T]` | ArrayType(T) | |
| `BackboneElement` | StructType | Resource-specific structure |

---

## Known Quirks

### 1. Varying _lastUpdated Precision

Different servers return `meta.lastUpdated` with different precision (seconds vs milliseconds). Always parse flexibly.

**Workaround**: Use ISO 8601 parsing that handles variable precision.

### 2. Bundle.total May Be Absent or Approximate

Some servers don't return `total`, or return an approximate count.

**Workaround**: Don't rely on `total` for progress tracking; use pagination links.

### 3. Search Parameter Case Sensitivity

While parameter names are case-sensitive per spec, some servers accept case-insensitive names.

**Workaround**: Always use lowercase parameter names as documented.

### 4. Date Parameter Timezone Handling

Servers may interpret date parameters differently regarding timezones.

**Workaround**: Always include timezone in date parameters (e.g., `2024-01-15T00:00:00Z`).

### 5. Large Result Sets

Some servers limit total results (e.g., 10,000) even with pagination.

**Workaround**: Use date ranges to partition large result sets.

### 6. Reference Format Variability

References may be relative (`Patient/123`), absolute (`https://server/fhir/Patient/123`), or contain version (`Patient/123/_history/1`).

**Workaround**: Parse references to extract resource type and ID, ignore version for matching.

### 7. Nullable Arrays

Empty arrays may be omitted or present as `[]`.

**Workaround**: Treat missing array fields as empty arrays.

### 8. Choice Types

Fields like `value[x]` can be `valueQuantity`, `valueString`, etc. Only one will be present.

**Workaround**: Schema includes all possible types; check which is populated at runtime.

---

## HAPI FHIR Test Server

For testing, use the public HAPI FHIR R4 server:

- **Base URL**: `https://hapi.fhir.org/baseR4`
- **Authentication**: None required
- **Limitations**: 
  - Rate limited (~10 req/sec)
  - Data is synthetic/test data
  - May be reset periodically

### Known Issues (Observed 2026-02-02)

| Issue | HTTP Status | Error Message | Mitigation |
|-------|-------------|---------------|------------|
| Database transaction failures | 500 | `CannotCreateTransactionException` | Retry with exponential backoff |
| Sort parameter not supported | 400/500 | Varies | Don't use `_sort=_lastUpdated` |
| Intermittent timeouts | Timeout | N/A | Increase timeout to 30s, add retries |
| Empty results on load | 200 | `{"total": 0}` | Skip test gracefully |

**Reliability**: **LOW** - This is a public shared server. For reliable CI/CD testing, use Docker-based HAPI:

```bash
# Run local HAPI FHIR server (recommended for CI)
docker run -p 8080:8080 hapiproject/hapi:latest
# Base URL: http://localhost:8080/fhir
```

**Test Commands**:

```bash
# List patients
curl "https://hapi.fhir.org/baseR4/Patient?_count=10" \
  -H "Accept: application/fhir+json"

# Get specific patient
curl "https://hapi.fhir.org/baseR4/Patient/example" \
  -H "Accept: application/fhir+json"

# Search observations by code
curl "https://hapi.fhir.org/baseR4/Observation?code=http://loinc.org|8867-4&_count=10" \
  -H "Accept: application/fhir+json"
```

---

## References

- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [FHIR RESTful API](https://hl7.org/fhir/R4/http.html)
- [FHIR Search](https://hl7.org/fhir/R4/search.html)
- [Patient Resource](https://hl7.org/fhir/R4/patient.html)
- [Observation Resource](https://hl7.org/fhir/R4/observation.html)
- [Condition Resource](https://hl7.org/fhir/R4/condition.html)
- [Encounter Resource](https://hl7.org/fhir/R4/encounter.html)
- [MedicationRequest Resource](https://hl7.org/fhir/R4/medicationrequest.html)
- [HAPI FHIR Server](https://hapi.fhir.org/)
