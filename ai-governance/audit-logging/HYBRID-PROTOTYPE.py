# Databricks notebook source
# MAGIC %md
# MAGIC # Genie Audit Log - Hybrid Prototype
# MAGIC ## Combines System Tables (SQL) + API (Python) for Complete Visibility
# MAGIC 
# MAGIC **Goal**: Connect user → workspace → space → conversation → message → prompt → generated SQL
# MAGIC 
# MAGIC **Architecture**:
# MAGIC 1. System tables provide: space activity, user activity, workspace info, query performance
# MAGIC 2. API provides: conversation details, message content, prompts, attachments (text-to-SQL)
# MAGIC 3. Delta tables store API data
# MAGIC 4. Views join system tables + API data for complete picture

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup
# MAGIC 
# MAGIC **Authentication**: Uses Service Principal with OAuth 2.0 Client Credentials flow
# MAGIC 
# MAGIC **Prerequisites**:
# MAGIC 1. Create a Service Principal in Azure AD
# MAGIC 2. Grant Service Principal access to Databricks workspace
# MAGIC 3. Store credentials in Databricks secrets:
# MAGIC    - `sp_client_id` - Service Principal Application (Client) ID
# MAGIC    - `sp_client_secret` - Service Principal Client Secret
# MAGIC 
# MAGIC **To create secrets**:
# MAGIC ```
# MAGIC databricks secrets create-scope --scope <scope-name>
# MAGIC databricks secrets put-secret --scope <scope-name> --key sp_client_id
# MAGIC databricks secrets put-secret --scope <scope-name> --key sp_client_secret
# MAGIC ```

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *
import requests
import json
from datetime import datetime, timedelta

# Configuration - UPDATE THESE VALUES
DATABRICKS_WS_HOST = spark.conf.get("spark.databricks.workspaceUrl")
DATABRICKS_WS_HOST = f"https://{DATABRICKS_WS_HOST}"

# Get Account ID and construct token URLs
ACC_ID = spark.conf.get("spark.databricks.accountId", None)
ACC_TOKEN_URL = f"https://accounts.azuredatabricks.net/oidc/accounts/{ACC_ID}/v1/token" if ACC_ID else None
WS_TOKEN_URL = f"{DATABRICKS_WS_HOST}/oidc/v1/token"

# Service Principal credentials from secrets
DATABRICKS_SP_CLIENT_ID = dbutils.secrets.get(scope="your_scope", key="sp_client_id")
DATABRICKS_SP_CLIENT_SECRET = dbutils.secrets.get(scope="your_scope", key="sp_client_secret")

# --- Request body ---
payload = {
    "grant_type": "client_credentials",
    "scope": "all-apis"
}

# --- Get workspace token using Service Principal ---
resp_ws = requests.post(
    WS_TOKEN_URL,
    data=payload,
    auth=(DATABRICKS_SP_CLIENT_ID, DATABRICKS_SP_CLIENT_SECRET)
)

if resp_ws.status_code == 200:
    WS_DATABRICKS_ACCESS_TOKEN = resp_ws.json().get('access_token')
    print(f"✅ Workspace authentication successful (status: {resp_ws.status_code})")
else:
    raise Exception(f"❌ Workspace authentication failed (status: {resp_ws.status_code}): {resp_ws.text}")

# Optional: Get account token if needed
ACC_DATABRICKS_ACCESS_TOKEN = None
if ACC_TOKEN_URL:
    resp_acc = requests.post(
        ACC_TOKEN_URL,
        data=payload,
        auth=(DATABRICKS_SP_CLIENT_ID, DATABRICKS_SP_CLIENT_SECRET)
    )
    if resp_acc.status_code == 200:
        ACC_DATABRICKS_ACCESS_TOKEN = resp_acc.json().get('access_token')
        print(f"✅ Account authentication successful (status: {resp_acc.status_code})")

HEADERS = {
    "Authorization": f"Bearer {WS_DATABRICKS_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# Target schema and tables
TARGET_SCHEMA = "genie_analytics"
CONVERSATIONS_TABLE = f"{TARGET_SCHEMA}.conversations_detail"
MESSAGES_TABLE = f"{TARGET_SCHEMA}.messages_detail"

spark = SparkSession.builder.getOrCreate()

print(f"\n✅ Configuration complete")
print(f"   Workspace: {DATABRICKS_WS_HOST}")
print(f"   Target schema: {TARGET_SCHEMA}")
print(f"   Auth method: Service Principal (OAuth 2.0)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Get All Active Spaces from System Tables

# COMMAND ----------

# Get all spaces with recent activity (last 30 days)
spaces_df = spark.sql("""
  SELECT DISTINCT
    workspace_id,
    CAST(request_params['space_id'] AS STRING) as space_id,
    COUNT(DISTINCT event_id) as recent_events,
    MAX(event_date) as last_activity_date
  FROM system.access.audit
  WHERE service_name = 'aibiGenie'
    AND event_date >= CURRENT_DATE - INTERVAL 30 DAYS
    AND request_params['space_id'] IS NOT NULL
  GROUP BY workspace_id, CAST(request_params['space_id'] AS STRING)
  HAVING recent_events >= 5
  ORDER BY recent_events DESC
""")

display(spaces_df)
print(f"\n✅ Found {spaces_df.count()} active Genie spaces")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: API Functions - Conversation & Message Details

# COMMAND ----------

def get_conversations(space_id):
    """Get all conversations for a space"""
    url = f"{DATABRICKS_WS_HOST}/api/2.0/genie/spaces/{space_id}/conversations"
    params = {"include_all": "true"}  # Required to return all conversations
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("conversations", [])
    except Exception as e:
        print(f"❌ Error fetching conversations for space {space_id}: {str(e)}")
        return []

def get_conversation_messages(space_id, conversation_id):
    """Get all messages for a conversation"""
    url = f"{DATABRICKS_WS_HOST}/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json().get("messages", [])
    except Exception as e:
        print(f"❌ Error fetching messages for conversation {conversation_id}: {str(e)}")
        return []

def get_message_detail(space_id, conversation_id, message_id):
    """Get detailed message info including attachments (text-to-SQL)"""
    url = f"{DATABRICKS_WS_HOST}/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages/{message_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ Error fetching message {message_id}: {str(e)}")
        return None

print("✅ API functions defined")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Collect Conversation & Message Data
# MAGIC 
# MAGIC **PROTOTYPE MODE**: Processes first space, first 5 conversations, first 10 messages per conversation
# MAGIC 
# MAGIC **To run in PRODUCTION mode**: Remove the [:5] and [:10] limits in the code below

# COMMAND ----------

# PROTOTYPE: Process just the most active space
test_space = spaces_df.first()
space_id = test_space['space_id']
workspace_id = test_space['workspace_id']

print(f"🔍 Processing PROTOTYPE space: {space_id} in workspace: {workspace_id}")
print(f"   (To process all spaces, modify the code to loop through spaces_df)")

# Collect conversations and messages
conversations_data = []
messages_data = []

conversations = get_conversations(space_id)
print(f"\n📊 Found {len(conversations)} conversations")

# PROTOTYPE: Process first 5 conversations
# PRODUCTION: Remove [:5] to process all conversations
for idx, conv in enumerate(conversations[:5], 1):
    conv_id = conv.get("id") or conv.get("conversation_id")
    
    # Store conversation metadata
    conversations_data.append({
        "workspace_id": workspace_id,
        "space_id": space_id,
        "conversation_id": conv_id,
        "title": conv.get("title") or conv.get("name") or "(untitled)",
        "created_timestamp": conv.get("created_timestamp"),
        "last_updated_timestamp": conv.get("last_updated_timestamp"),
        "collected_at": datetime.now().isoformat()
    })
    
    # Get messages for this conversation
    messages = get_conversation_messages(space_id, conv_id)
    print(f"  {idx}. Conversation '{conv.get('title', 'untitled')[:50]}': {len(messages)} messages")
    
    # PROTOTYPE: Process first 10 messages per conversation
    # PRODUCTION: Remove [:10] to process all messages
    for msg in messages[:10]:
        msg_id = msg.get("id") or msg.get("message_id")
        
        # Get detailed message info
        msg_detail = get_message_detail(space_id, conv_id, msg_id)
        if msg_detail:
            # Extract text-to-SQL from attachments
            attachments = msg_detail.get("attachments", [])
            generated_sql = None
            attachment_type = None
            
            if attachments:
                for att in attachments:
                    if att.get("query"):
                        generated_sql = att["query"].get("query")
                        attachment_type = "query"
                        break
            
            messages_data.append({
                "workspace_id": workspace_id,
                "space_id": space_id,
                "conversation_id": conv_id,
                "message_id": msg_id,
                "content": msg_detail.get("content"),  # User prompt/question
                "status": msg_detail.get("status"),
                "user_id": msg_detail.get("user_id"),
                "created_timestamp": msg_detail.get("created_timestamp"),
                "last_updated_timestamp": msg_detail.get("last_updated_timestamp"),
                "generated_sql": generated_sql,  # Text-to-SQL result
                "attachment_type": attachment_type,
                "has_attachments": len(attachments) > 0,
                "attachments_json": json.dumps(attachments) if attachments else None,
                "error": json.dumps(msg_detail.get("error", {})) if msg_detail.get("error") else None,
                "collected_at": datetime.now().isoformat()
            })

print(f"\n✅ Collection complete!")
print(f"   Conversations: {len(conversations_data)}")
print(f"   Messages: {len(messages_data)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Create Delta Tables with API Data

# COMMAND ----------

# Conversations schema
conversations_schema = StructType([
    StructField("workspace_id", StringType(), True),
    StructField("space_id", StringType(), True),
    StructField("conversation_id", StringType(), True),
    StructField("title", StringType(), True),
    StructField("created_timestamp", LongType(), True),
    StructField("last_updated_timestamp", LongType(), True),
    StructField("collected_at", StringType(), True)
])

# Messages schema
messages_schema = StructType([
    StructField("workspace_id", StringType(), True),
    StructField("space_id", StringType(), True),
    StructField("conversation_id", StringType(), True),
    StructField("message_id", StringType(), True),
    StructField("content", StringType(), True),
    StructField("status", StringType(), True),
    StructField("user_id", StringType(), True),
    StructField("created_timestamp", LongType(), True),
    StructField("last_updated_timestamp", LongType(), True),
    StructField("generated_sql", StringType(), True),
    StructField("attachment_type", StringType(), True),
    StructField("has_attachments", BooleanType(), True),
    StructField("attachments_json", StringType(), True),
    StructField("error", StringType(), True),
    StructField("collected_at", StringType(), True)
])

# Create DataFrames
conversations_df = spark.createDataFrame(conversations_data, schema=conversations_schema)
messages_df = spark.createDataFrame(messages_data, schema=messages_schema)

# Write to Delta tables (PROTOTYPE: overwrite mode)
# PRODUCTION: Use merge/append for incremental updates
conversations_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .saveAsTable(CONVERSATIONS_TABLE)

messages_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("mergeSchema", "true") \
    .saveAsTable(MESSAGES_TABLE)

print(f"✅ Created Delta tables:")
print(f"   {CONVERSATIONS_TABLE}: {conversations_df.count()} rows")
print(f"   {MESSAGES_TABLE}: {messages_df.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Create Unified View - Complete Picture

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Create unified view combining system tables + API data
# MAGIC CREATE OR REPLACE VIEW genie_analytics.unified_message_analysis AS
# MAGIC WITH user_mapping AS (
# MAGIC   SELECT DISTINCT
# MAGIC     user_identity.email as user_email,
# MAGIC     CAST(request_params['space_id'] AS STRING) as space_id
# MAGIC   FROM system.access.audit
# MAGIC   WHERE service_name = 'aibiGenie'
# MAGIC     AND user_identity.email IS NOT NULL
# MAGIC ),
# MAGIC workspace_info AS (
# MAGIC   SELECT 
# MAGIC     workspace_id,
# MAGIC     workspace_name
# MAGIC   FROM system.access.workspaces_latest
# MAGIC )
# MAGIC SELECT
# MAGIC   -- Workspace context
# MAGIC   w.workspace_id,
# MAGIC   w.workspace_name,
# MAGIC   
# MAGIC   -- Space context
# MAGIC   m.space_id,
# MAGIC   
# MAGIC   -- Conversation context
# MAGIC   c.conversation_id,
# MAGIC   c.title as conversation_title,
# MAGIC   
# MAGIC   -- Message context
# MAGIC   m.message_id,
# MAGIC   m.content as user_prompt,
# MAGIC   m.generated_sql,
# MAGIC   m.status as message_status,
# MAGIC   
# MAGIC   -- User context
# MAGIC   m.user_id,
# MAGIC   u.user_email,
# MAGIC   
# MAGIC   -- Timestamps
# MAGIC   FROM_UNIXTIME(m.created_timestamp / 1000) as message_created_time,
# MAGIC   FROM_UNIXTIME(c.created_timestamp / 1000) as conversation_created_time,
# MAGIC   
# MAGIC   -- Metadata
# MAGIC   m.has_attachments,
# MAGIC   m.attachment_type,
# MAGIC   m.error
# MAGIC   
# MAGIC FROM genie_analytics.messages_detail m
# MAGIC INNER JOIN genie_analytics.conversations_detail c 
# MAGIC   ON m.conversation_id = c.conversation_id
# MAGIC LEFT JOIN workspace_info w 
# MAGIC   ON m.workspace_id = w.workspace_id
# MAGIC LEFT JOIN user_mapping u 
# MAGIC   ON m.space_id = u.space_id
# MAGIC ORDER BY message_created_time DESC;

# COMMAND ----------

print("✅ Unified view created: genie_analytics.unified_message_analysis")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Query the Complete Picture

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example 1: Show all prompts with their generated SQL
# MAGIC SELECT 
# MAGIC   workspace_name,
# MAGIC   space_id,
# MAGIC   conversation_title,
# MAGIC   user_email,
# MAGIC   user_prompt,
# MAGIC   LEFT(generated_sql, 100) as sql_preview,
# MAGIC   message_created_time
# MAGIC FROM genie_analytics.unified_message_analysis
# MAGIC WHERE generated_sql IS NOT NULL
# MAGIC ORDER BY message_created_time DESC
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example 2: Messages per conversation
# MAGIC SELECT
# MAGIC   workspace_name,
# MAGIC   space_id,
# MAGIC   conversation_title,
# MAGIC   COUNT(DISTINCT message_id) as message_count,
# MAGIC   COUNT(DISTINCT user_email) as unique_users,
# MAGIC   MIN(message_created_time) as first_message,
# MAGIC   MAX(message_created_time) as last_message
# MAGIC FROM genie_analytics.unified_message_analysis
# MAGIC GROUP BY workspace_name, space_id, conversation_title
# MAGIC ORDER BY message_count DESC;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Example 3: User activity with prompt analysis
# MAGIC SELECT
# MAGIC   user_email,
# MAGIC   COUNT(DISTINCT conversation_id) as conversations,
# MAGIC   COUNT(DISTINCT message_id) as messages,
# MAGIC   COUNT(DISTINCT CASE WHEN generated_sql IS NOT NULL THEN message_id END) as messages_with_sql,
# MAGIC   COUNT(DISTINCT space_id) as spaces_accessed,
# MAGIC   COUNT(DISTINCT workspace_id) as workspaces_accessed
# MAGIC FROM genie_analytics.unified_message_analysis
# MAGIC GROUP BY user_email
# MAGIC ORDER BY messages DESC;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Join with System Table Query Performance

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Link messages with actual query execution performance
# MAGIC CREATE OR REPLACE VIEW genie_analytics.message_to_query_performance AS
# MAGIC SELECT
# MAGIC   m.workspace_name,
# MAGIC   m.space_id,
# MAGIC   m.conversation_title,
# MAGIC   m.message_id,
# MAGIC   m.user_email,
# MAGIC   m.user_prompt,
# MAGIC   m.generated_sql,
# MAGIC   
# MAGIC   -- Query performance from system.query.history
# MAGIC   q.statement_id,
# MAGIC   q.execution_status,
# MAGIC   q.statement_type,
# MAGIC   ROUND(q.total_duration_ms / 1000.0, 2) as execution_duration_seconds,
# MAGIC   q.read_rows,
# MAGIC   q.produced_rows,
# MAGIC   ROUND(q.read_bytes / 1024.0 / 1024.0, 2) as read_mb,
# MAGIC   q.from_result_cache as cached,
# MAGIC   q.error_message,
# MAGIC   
# MAGIC   m.message_created_time,
# MAGIC   q.start_time as query_start_time
# MAGIC   
# MAGIC FROM genie_analytics.unified_message_analysis m
# MAGIC LEFT JOIN system.query.history q
# MAGIC   ON m.space_id = q.query_source.genie_space_id
# MAGIC   AND m.message_created_time <= q.start_time
# MAGIC   AND m.message_created_time >= q.start_time - INTERVAL 5 MINUTES
# MAGIC WHERE m.generated_sql IS NOT NULL
# MAGIC ORDER BY m.message_created_time DESC;

# COMMAND ----------

print("✅ Performance view created: genie_analytics.message_to_query_performance")

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Test the joined view
# MAGIC SELECT 
# MAGIC   workspace_name,
# MAGIC   user_email,
# MAGIC   LEFT(user_prompt, 50) as prompt_preview,
# MAGIC   statement_type,
# MAGIC   execution_status,
# MAGIC   execution_duration_seconds,
# MAGIC   read_rows,
# MAGIC   message_created_time
# MAGIC FROM genie_analytics.message_to_query_performance
# MAGIC WHERE execution_status IS NOT NULL
# MAGIC LIMIT 20;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary & Next Steps

# COMMAND ----------

print("""
✅ PROTOTYPE COMPLETE!

What was created:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Delta Tables:
   • genie_analytics.conversations_detail
   • genie_analytics.messages_detail

2. Unified Views:
   • genie_analytics.unified_message_analysis
   • genie_analytics.message_to_query_performance

What you can now query:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ User prompts (questions asked)
✓ Generated SQL (text-to-SQL conversions)
✓ Conversation activity over time
✓ Average messages per conversation
✓ Query performance linked to prompts

Next steps for PRODUCTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Remove [:5] and [:10] limits to process all data
2. Change write mode from "overwrite" to "merge"
3. Schedule this notebook as a daily job
4. Build Databricks SQL dashboard using views
5. Set up alerts on unified views

Query examples in documentation:
• COMPLETE-SOLUTION-SUMMARY.md
• HYBRID-SOLUTION-GUIDE.md
• QUICK-REFERENCE.md
""")

# COMMAND ----------


