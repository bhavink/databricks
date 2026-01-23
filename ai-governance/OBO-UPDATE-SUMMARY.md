# OBO Implementation Update - Genie Space Deep Dive

> **Date**: January 23, 2026  
> **Change**: Updated OBO authentication code example with current ModelServingUserCredentials implementation

---

## Summary

Updated the OBO authentication section in `03-GENIE-SPACE-DEEP-DIVE.md` to reflect the **current (2024+) implementation** using `ModelServingUserCredentials` instead of the legacy `on_behalf_of` parameter.

---

## What Changed

### Location
File: `/0-repo/databricks/ai-governance/03-GENIE-SPACE-DEEP-DIVE.md`  
Section: **Method 3: On-Behalf-Of (OBO)** (~line 214-225)

### Old Code (Legacy Approach)
```python
from databricks.sdk import WorkspaceClient
from databricks_langchain import GenieAgent

# OBO authentication via SDK
client = WorkspaceClient()
agent = GenieAgent(
    space_id="<genie-space-id>",
    on_behalf_of="customer@email.com"  # Query runs as this user
)
```

### New Code (Current Implementation)
```python
from databricks.sdk import WorkspaceClient
from databricks_langchain import GenieAgent
from databricks_ai_bridge import ModelServingUserCredentials

# 1. Configure the WorkspaceClient for OBO authentication
user_client = WorkspaceClient(credentials_strategy=ModelServingUserCredentials())

# 2. Initialize the GenieAgent with the configured client
agent = GenieAgent(
    genie_space_id="<genie-space-id>",
    genie_agent_name="Genie",  # Optional name
    description="This agent queries sales data",  # Optional description
    client=user_client  # Pass the OBO client here
)

# 3. Use the agent
response = agent.invoke("Show me the total revenue for last month.")
```

---

## Key Improvements

### 1. Correct Authentication Method
- ✅ Uses `ModelServingUserCredentials()` credential strategy
- ✅ Passes configured `WorkspaceClient` to `GenieAgent`
- ❌ Removed deprecated `on_behalf_of` string parameter

### 2. Added Implementation Details

**How It Works:**
- Explained automatic token injection by Model Serving
- Clarified that `ModelServingUserCredentials` looks for injected tokens
- Emphasized user context preservation for UC enforcement

### 3. Critical Requirements Added

**⚠️ Initialize Inside Predict:**
```python
class MyAgent:
    def predict(self, request):
        # Must initialize HERE, not in __init__
        user_client = WorkspaceClient(
            credentials_strategy=ModelServingUserCredentials()
        )
        agent = GenieAgent(genie_space_id="...", client=user_client)
        return agent.invoke(request.query)
```

**Why:** User identity is only known at runtime, not when agent is loaded.

**⚠️ Declare API Scopes:**
```python
from mlflow.models.auth_policy import AuthPolicy, UserAuthPolicy

user_policy = UserAuthPolicy(api_scopes=[
    "dashboards.genie",
    "sql.warehouses",
    "sql.statement-execution"
])
```

**Why:** Ensures least-privilege access via token downscoping.

**⚠️ Library Requirements:**
```bash
pip install databricks-sdk databricks-ai-bridge databricks-langchain
```

**Why:** `databricks-ai-bridge` provides `ModelServingUserCredentials`.

### 4. Added Official Documentation Link
- Link to OBO Authentication docs: https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/agent-authentication#on-behalf-of-user-authentication

---

## Why This Update Was Needed

### Problem with Old Code:
1. **Deprecated API:** The `on_behalf_of` parameter is not the current recommended approach
2. **Missing Context:** Didn't explain how automatic token injection works
3. **Missing Requirements:** Didn't mention critical setup requirements (predict initialization, scope declaration, libraries)
4. **Incomplete Example:** Didn't show how to actually invoke the agent

### Benefits of New Code:
1. ✅ **Current Best Practice:** Uses `ModelServingUserCredentials` as recommended by Databricks
2. ✅ **Complete Example:** Shows full workflow from client setup to invocation
3. ✅ **Production-Ready:** Includes all critical requirements for deployment
4. ✅ **Clear Explanation:** Explains how token injection and credential strategy work
5. ✅ **Official Reference:** Links to authoritative documentation

---

## Impact

### For Users:
- ✅ Can copy-paste working code for OBO authentication
- ✅ Understand why they must initialize inside `predict()`
- ✅ Know which API scopes to declare
- ✅ Have correct library dependencies

### For Maintenance:
- ✅ Code aligned with official Databricks documentation
- ✅ Reduced risk of users implementing deprecated patterns
- ✅ Clear link to official docs for latest updates

---

## Related Changes

This update complements the earlier change to `02-AUTHORIZATION-WITH-UC.md`:
- `02-AUTHORIZATION-WITH-UC.md`: Added **references** to Agent Framework auth (no code)
- `03-GENIE-SPACE-DEEP-DIVE.md`: Updated **implementation code** for Genie-specific OBO

Together, these provide:
1. **Conceptual understanding** (in 02-) of how auth integrates with UC
2. **Practical implementation** (in 03-) of OBO for Genie Space specifically

---

## Verification

To verify the code is correct:

1. **Check official docs match:**
   ```
   https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/agent-authentication#genie-spaces-workspaceclient
   ```

2. **Verify imports:**
   ```python
   from databricks_ai_bridge import ModelServingUserCredentials  # Correct
   ```

3. **Confirm client parameter:**
   ```python
   GenieAgent(client=user_client)  # Correct - passes WorkspaceClient
   ```

4. **Check scope declaration pattern:**
   ```python
   UserAuthPolicy(api_scopes=["dashboards.genie"])  # Correct
   ```

---

**Status**: ✅ Complete - OBO implementation updated to current best practices with comprehensive requirements
