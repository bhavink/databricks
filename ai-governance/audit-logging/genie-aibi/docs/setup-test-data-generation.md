# Genie Test Data Generation Setup Guide

**Purpose:** Generate test conversations in Genie Spaces for demo and testing purposes

**Script:** `python/demo_generate_test_conversations.py` (formerly `genie_conversation_test_data.py`)

**Runtime:** Databricks cluster (notebook or job)

---

## Overview

This script uses the [Genie Conversation API](https://docs.databricks.com/genie/conversation-api.html) to:
1. Start a conversation in each configured Genie Space
2. Ask 1-2 follow-up questions per space
3. Generate audit events that flow through your observability pipeline

**Why Databricks?**
- ✅ Needs `dbutils.secrets` for OAuth credentials
- ✅ Generates audit events in Databricks audit log
- ✅ Events automatically picked up by SDP pipeline
- ✅ No need to manage local credentials

---

## Prerequisites

### 1. Service Principal with Genie Access

You need a service principal (or user) with:
- **Workspace access** to target workspaces
- **Genie Space access** (CAN_USE permission on spaces)
- **API permissions** for Genie Conversation API

**Get credentials:**
```bash
# Service Principal credentials
SP_CLIENT_ID="<your-sp-application-id>"
SP_CLIENT_SECRET="<your-sp-secret>"
```

### 2. Genie Spaces Created

You need at least one Genie Space with:
- ✅ Data sources configured (tables)
- ✅ Sample questions defined (optional but recommended)
- ✅ Test queries that work

**Get Space IDs:**
- Option 1: From Genie UI URL: `https://<workspace>/genie/rooms/<space_id>`
- Option 2: From audit table: `SELECT DISTINCT space_id FROM system.access.audit WHERE action_name = 'genieCreateMessage'`

### 3. Databricks CLI Configured

```bash
# Authenticate
databricks auth login --host https://<workspace>.azuredatabricks.net

# Verify
databricks workspace ls /Workspace/Users/<your-email>
```

---

## Step 1: Create Secrets (One-Time Setup)

Run this **once** from your local machine to store credentials in Databricks:

```bash
cd /path/to/genie-aibi/scripts

# Set credentials
export DATABRICKS_SP_CLIENT_ID="<your-sp-client-id>"
export DATABRICKS_SP_CLIENT_SECRET="<your-sp-secret>"

# Create secret scope and store credentials
python create_genie_obs_secrets.py

# If using non-default profile:
python create_genie_obs_secrets.py --profile <profile-name>
```

**What this does:**
- Creates secret scope: `genie-obs`
- Stores two secrets:
  - `sp_client_id` - Service principal application ID
  - `sp_client_secret` - Service principal secret

**Verify secrets created:**
```bash
databricks secrets list-scopes
# Should show: genie-obs

databricks secrets list --scope genie-obs
# Should show: sp_client_id, sp_client_secret
```

---

## Step 2: Configure Workspaces and Spaces

Edit `python/config.py`:

```python
# Required: List of workspace IDs to generate test data in
WORKSPACE_IDS = [
    "1516413757355523",  # Your workspace 1
    "984752964297111"    # Your workspace 2 (optional)
]

# Optional: Specific spaces per workspace
# None = all spaces (may be many!)
# Dict = specific spaces only
SPACE_IDS_BY_WORKSPACE = {
    "1516413757355523": ["01f0aaabfed41a778b2e5302795ce495"],  # Space 1
    "984752964297111": ["01ef7bef0dbf1545bfd9184f19ad97f6"]   # Space 2
}

# Optional: Workspace URLs (if None, reads from genie_messages_to_fetch table)
WORKSPACE_URLS = {
    "1516413757355523": "https://adb-1516413757355523.3.azuredatabricks.net",
    "984752964297111": "https://adb-984752964297111.11.azuredatabricks.net"
}
```

**Tips:**
- Start with 1-2 spaces for testing
- Use `SPACE_IDS_BY_WORKSPACE = None` to test all spaces (careful if many!)
- Provide `WORKSPACE_URLS` to avoid dependency on `genie_messages_to_fetch` table

---

## Step 3: Upload Files to Databricks Workspace

Upload the Python scripts to your Databricks workspace:

### Option A: Using Databricks CLI

```bash
cd /path/to/genie-aibi

# Upload entire python directory
databricks workspace import-dir \
  python/ \
  /Workspace/Users/<your-email>/genie-obs/python \
  --overwrite

# Verify upload
databricks workspace ls /Workspace/Users/<your-email>/genie-obs/python
```

### Option B: Using Databricks UI

1. Go to Workspace → Users → your email
2. Create folder: `genie-obs/python`
3. Upload files:
   - `config.py`
   - `genie_oauth.py`
   - `genie_message_ingestion.py` (for get_dbutils function)
   - `demo_generate_test_conversations.py`

---

## Step 4: Run from Databricks Notebook

### Create a Test Notebook

1. **Create new notebook:** `Workspace/Users/<your-email>/genie-obs/test-data-generator`
2. **Attach to cluster:** Any cluster with DBR 13.3+ LTS
3. **Add cells:**

#### Cell 1: Add Python directory to path

```python
import sys
sys.path.insert(0, "/Workspace/Users/<your-email>/genie-obs/python")
```

#### Cell 2: Import and run

```python
from demo_generate_test_conversations import main

# Run test data generation
main()
```

#### Expected Output

```
INFO: Starting Genie test data generation
INFO: Workspaces: ['1516413757355523', '984752964297111']
INFO: Spaces per workspace: 1-2 spaces configured

INFO: Workspace 1516413757355523 - Space 01f0aaab...
INFO:   Starting conversation...
INFO:   Conversation ID: 01f10a1b...
INFO:   Polling message (attempt 1/20)...
INFO:   Message COMPLETED in 2.3s
INFO:   Asking follow-up 1/2...
INFO:   Waiting 15s (throughput limit: 5 queries/min)...
INFO:   Follow-up COMPLETED in 1.8s

INFO: Test data generation complete!
INFO: Generated 4 messages across 2 spaces in 2 workspaces
INFO: Next steps:
INFO:   1. Wait 5-10 minutes for audit log to update
INFO:   2. Run SDP pipeline to pick up new events
INFO:   3. Run message ingestion to fetch details
```

---

## Step 5: Run as Databricks Job (Optional)

For scheduled test data generation:

### Create Job via UI

1. **Workflows → Create Job**
2. **Task Configuration:**
   - **Task name:** `Generate Genie Test Data`
   - **Type:** Python script
   - **Source:** Workspace
   - **Path:** `/Workspace/Users/<your-email>/genie-obs/python/demo_generate_test_conversations.py`
3. **Cluster:** Use existing cluster or create new (DBR 13.3+ LTS)
4. **Schedule:** On-demand or cron (e.g., weekly for demos)

### Create Job via CLI

```bash
# Create job definition
cat > test-data-job.json <<EOF
{
  "name": "Genie Test Data Generation",
  "tasks": [{
    "task_key": "generate_test_data",
    "python_script_task": {
      "script_path": "/Workspace/Users/<your-email>/genie-obs/python/demo_generate_test_conversations.py"
    },
    "libraries": [],
    "new_cluster": {
      "spark_version": "13.3.x-scala2.12",
      "node_type_id": "Standard_DS3_v2",
      "num_workers": 0,
      "spark_conf": {
        "spark.databricks.cluster.profile": "singleNode"
      },
      "custom_tags": {
        "ResourceClass": "SingleNode"
      }
    }
  }],
  "max_concurrent_runs": 1
}
EOF

# Create job
databricks jobs create --json-file test-data-job.json

# Run job
databricks jobs run-now --job-id <job-id>
```

---

## Step 6: Verify Results

### Check Audit Log (5-10 min delay)

```sql
-- Check for new Genie events
SELECT
  event_time,
  workspace_id,
  request_params:spaceId::string as space_id,
  request_params:conversationId::string as conversation_id,
  request_params:messageId::string as message_id,
  action_name
FROM system.access.audit
WHERE action_name IN ('genieCreateMessage', 'genieExecuteMessageQuery')
  AND event_date >= current_date()
ORDER BY event_time DESC
LIMIT 20;
```

### Run SDP Pipeline

```bash
# If using Delta Live Tables
databricks pipelines update <pipeline-id> --full-refresh

# Or manually run the notebook that populates genie_messages_to_fetch
```

### Run Message Ingestion

```python
# In a notebook
import sys
sys.path.insert(0, "/Workspace/Users/<your-email>/genie-obs/python")

from genie_message_ingestion import run_ingestion, get_dbutils

run_ingestion(
    workspace_ids=["1516413757355523"],
    space_ids_by_workspace=None,
    dbutils=get_dbutils()
)
```

### Verify in Dashboard

1. Open Genie Observability Dashboard
2. Select workspace filter
3. Check "Prompts & SQL" tab for new messages
4. Verify timestamps match test run

---

## Troubleshooting

### Error: "Cannot find dbutils"

**Cause:** Running outside Databricks or in local Python

**Fix:** Must run on Databricks cluster (notebook or job)

### Error: "Secret not found: genie-obs/sp_client_id"

**Cause:** Secrets not created or wrong scope name

**Fix:**
```bash
# Check secrets exist
databricks secrets list-scopes
databricks secrets list --scope genie-obs

# Recreate if needed
python scripts/create_genie_obs_secrets.py
```

### Error: "Access denied" or "403 Forbidden"

**Cause:** Service principal lacks permissions

**Fix:**
- Check SP has workspace access
- Check SP has Genie Space permissions (CAN_USE)
- Verify credentials are correct

### Error: "No workspace_url for workspace_id"

**Cause:** `WORKSPACE_URLS` is `None` and `genie_messages_to_fetch` table doesn't exist or is empty

**Fix:**
- Set `WORKSPACE_URLS` in `config.py`, OR
- Run SDP pipeline first to populate `genie_messages_to_fetch`

### Test data not appearing in dashboard

**Checklist:**
1. ✅ Wait 5-10 minutes for audit log
2. ✅ Run SDP pipeline to populate `genie_messages_to_fetch`
3. ✅ Run message ingestion to fetch message details
4. ✅ Check `message_details` table has new rows:
   ```sql
   SELECT COUNT(*), MAX(created_timestamp)
   FROM main.genie_analytics.message_details
   WHERE created_date >= current_date()
   ```

### Throughput limit errors

**Symptom:** "429 Too Many Requests"

**Fix:** Script respects 5 queries/min limit (12s between calls). If still hitting limits:
- Reduce number of spaces
- Increase delay between workspaces
- Check other processes aren't hitting same spaces

---

## Configuration Reference

### Config.py Settings

| Setting | Type | Required | Purpose |
|---------|------|----------|---------|
| `WORKSPACE_IDS` | List[str] | ✅ Yes | Workspace IDs to generate data in |
| `SPACE_IDS_BY_WORKSPACE` | Dict or None | ⚠️ Recommended | Specific spaces (None = all spaces) |
| `WORKSPACE_URLS` | Dict or None | ⚠️ Recommended | Workspace URLs (None = read from table) |
| `SECRETS_SCOPE` | str | ✅ Yes | Secret scope name (default: "genie-obs") |

### Sample Questions

The script asks these sample questions per space:

1. **Initial question:** "What are the top 5 items by total value?"
2. **Follow-up 1:** "Show me the trend over the last 30 days"
3. **Follow-up 2:** "Which category has the highest growth?"

**Customize questions:**
Edit the `SAMPLE_QUESTIONS` list in `demo_generate_test_conversations.py`

---

## Best Practices

### ✅ DO

- **Start small:** Test with 1-2 spaces first
- **Set WORKSPACE_URLS:** Avoid dependency on tables
- **Run during demos:** Generate fresh data before presentations
- **Monitor throughput:** Script respects 5 queries/min limit
- **Check audit log:** Verify events appear before running pipeline

### ❌ DON'T

- **Don't run in production spaces:** Use test/dev spaces only
- **Don't run too frequently:** Respect rate limits (max every 15 min)
- **Don't commit credentials:** Always use secrets, never hardcode
- **Don't skip pipeline step:** Test data only useful after ingestion

---

## Integration with Pipeline

**Full observability flow:**

```
1. Generate Test Data (this script)
   ↓ (creates events in audit log)
2. SDP Pipeline
   ↓ (audit → genie_messages_to_fetch)
3. Message Ingestion
   ↓ (API fetch → message_details)
4. Dashboard
   ↓ (visualize)
```

**Timing:**
- Test data generation: 30 sec - 2 min (depends on spaces)
- Audit log delay: 5-10 min
- SDP pipeline: 1-5 min
- Message ingestion: 30 sec - 5 min (depends on message count)

**Total time:** ~15-25 minutes from generation to dashboard

---

## Next Steps

After generating test data:

1. **Verify in audit log** (Step 6)
2. **Run SDP pipeline** to populate `genie_messages_to_fetch`
3. **Run message ingestion** to fetch message details
4. **Open dashboard** and verify data appears
5. **Schedule regular generation** for demos (optional)

For pipeline setup, see:
- Pipeline docs: `../pipelines/genie_observability/README.md`
- Ingestion docs: `../python/README.md`
- Dashboard docs: `genie-observability-dashboard.md`

---

## Support

**For issues with test data generation:**
1. Check this guide's Troubleshooting section
2. Verify secrets exist: `databricks secrets list --scope genie-obs`
3. Test with one space first
4. Check Databricks cluster logs

**For issues with pipeline/ingestion:**
See respective README files in `pipelines/` and `python/` directories

---

**Last Updated:** February 10, 2026
**Script Version:** 1.0
**Requires:** Databricks Runtime 13.3+ LTS
