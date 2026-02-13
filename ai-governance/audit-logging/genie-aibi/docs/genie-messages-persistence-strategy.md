## Persistence Strategy for Message Details

### Recommended Approach: Single Denormalized Table

**Table Name:** `main.genie_analytics.message_details`

**Why Single Table:**
* ✅ Simpler queries - no joins needed for basic analysis
* ✅ Better performance - denormalized for analytics
* ✅ Easier maintenance - one table to manage
* ✅ Complete context in one place - message + attachments + query performance

---

### Table Schema (Optimized)

```sql
CREATE TABLE IF NOT EXISTS main.genie_analytics.message_details (
  -- Primary Keys
  workspace_id STRING NOT NULL,
  message_id STRING NOT NULL,

  -- Hierarchy
  space_id STRING NOT NULL,
  conversation_id STRING NOT NULL,
  space_name STRING COMMENT 'Space title from GET /api/2.0/genie/spaces/{space_id}',

  -- Workspace Context
  workspace_name STRING,

  -- Message Content
  content STRING COMMENT 'User question/input',
  status STRING COMMENT 'COMPLETED, FAILED, CANCELED',
  created_timestamp LONG COMMENT 'Unix timestamp in milliseconds',
  updated_timestamp LONG,
  created_date DATE GENERATED ALWAYS AS (DATE(FROM_UNIXTIME(created_timestamp / 1000))),

  -- SQL Generation (from attachments)
  query_sql STRING COMMENT 'SQL extracted from query attachments',
  query_description STRING COMMENT 'What Genie understood from user question',
  statement_id STRING COMMENT 'Links to system.query.history',

  -- Attachments Summary
  attachments_count INT,
  attachments_json STRING COMMENT 'Full attachments array as JSON',

  -- Query Performance (denormalized from system.query.history)
  query_execution_status STRING,
  query_duration_ms LONG,
  query_start_time TIMESTAMP,
  query_end_time TIMESTAMP,
  query_warehouse_id STRING,
  query_read_rows LONG,
  query_read_bytes LONG,
  query_error_message STRING,

  -- API Fetch Metadata
  api_fetch_timestamp TIMESTAMP,
  api_fetch_status STRING,
  api_fetch_error STRING,

  -- Audit Trail
  ingestion_timestamp TIMESTAMP,
  ingestion_batch_id STRING
)
PARTITIONED BY (created_date)
CLUSTER BY (workspace_id, space_id);
```

---

### Change Data Capture (CDC) Strategy

#### **Incremental Load Pattern:**

```python
# Get last successful run timestamp
last_run_timestamp = spark.sql("""
    SELECT MAX(ingestion_timestamp) as last_run
    FROM main.genie_analytics.message_details
""").collect()[0]['last_run']

if last_run_timestamp:
    # Incremental: Only fetch NEW messages since last run
    new_messages = spark.sql(f"""
        SELECT DISTINCT message_id, space_id, conversation_id
        FROM system.access.audit
        WHERE service_name = 'aibiGenie'
          AND action_name IN ('genieGetConversationMessage', 'getConversationMessage')
          AND event_time > '{last_run_timestamp}'
          AND message_id NOT IN (
              SELECT message_id FROM main.genie_analytics.message_details
          )
    """)
else:
    # Initial load: Fetch all messages
    new_messages = messages_for_api
```

#### **Benefits:**
* ✅ Only fetch NEW messages (not already in Delta table)
* ✅ Avoid re-processing same messages
* ✅ Faster execution (fewer API calls)
* ✅ Lower cost (less compute)

---

### Fault Tolerance Strategy

#### **1. Track API Failures**
```python
# Separate table for failed API calls
CREATE TABLE main.genie_analytics.message_fetch_errors (
  workspace_id STRING,
  message_id STRING,
  space_id STRING,
  conversation_id STRING,
  error_type STRING,  -- AUTH_ERROR, TIMEOUT, RATE_LIMITED, FAILED
  error_message STRING,
  error_timestamp TIMESTAMP,
  retry_count INT,
  resolved BOOLEAN DEFAULT FALSE
)
```

#### **2. Retry Logic**
* Retry failed messages in next run
* Exponential backoff for rate limits
* Skip auth errors until permissions granted

#### **3. Batch Processing**
* Process in batches of 100 messages
* Commit each batch to Delta (atomic writes)
* If batch fails, only that batch needs retry

---

### Table Optimization

#### **Partitioning:**
* `PARTITIONED BY (created_date)` - Efficient date-range queries
* Aligns with audit log partition key

#### **Clustering:**
* `CLUSTER BY (workspace_id, space_id)` - Co-locate related data
* Improves query performance for workspace/space filters

#### **Z-Ordering (Optional):**
```sql
OPTIMIZE main.genie_analytics.message_details
ZORDER BY (conversation_id, message_id);
```

---

### Alternative: Separate Attachments Table

**If you prefer normalized design:**

```sql
-- Main table
main.genie_analytics.messages
  - message_id (PK)
  - content, status, timestamps
  - query_sql, statement_id

-- Attachments table (1:N relationship)
main.genie_analytics.message_attachments
  - message_id (FK)
  - attachment_id (PK)
  - attachment_type (QUERY, TEXT, CHART)
  - attachment_json
```

**Trade-offs:**
* ✅ Normalized (less duplication)
* ❌ Requires JOIN for most queries
* ❌ More complex queries
* ❌ Slower performance

**Recommendation:** Use **single denormalized table** for analytics workload.

---

### Implementation Plan

1. **Create Delta table** with optimized schema
2. **Initial load:** Fetch all messages from last 30 days
3. **Schedule notebook:** Run daily/hourly for incremental loads
4. **Monitor:** Track API success rates, errors, performance
5. **Optimize:** Run OPTIMIZE + ZORDER weekly

---

### Related: genie_space_details

Space-level config (title, description, **serialized_space**) is stored in a **separate table**: `main.genie_analytics.genie_space_details`. It is filled by **genie_space_details.py** (separate job), which reads distinct (workspace_id, space_id) from `genie_messages_to_fetch`, calls GET `/api/2.0/genie/spaces/{space_id}?include_serialized_space=true`, and merges by (workspace_id, space_id). Use it for backup/promote and for human-readable space titles in dashboards (join to message_details on workspace_id, space_id). See `sql/genie_observability_schema.sql` and `docs/genie-aibi-data-model-and-architecture.md`.