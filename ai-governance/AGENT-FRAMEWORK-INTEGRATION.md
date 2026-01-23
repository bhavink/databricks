# 02-AUTHORIZATION-WITH-UC.md - Agent Framework Integration Update

> **Date**: January 23, 2026  
> **Change**: Added Agent Framework authentication reference section

---

## Summary

Updated `02-AUTHORIZATION-WITH-UC.md` to include a comprehensive reference to official Databricks Agent Framework authentication documentation, clarifying how authentication patterns integrate with Unity Catalog authorization.

---

## What Was Added

### New Section: "Agent Framework Authentication Reference"

Added after the Pattern Integration section (line ~840) to bridge the gap between:
- **Authentication** (how agents prove identity) - covered in Agent Framework docs
- **Authorization** (what UC allows them to access) - covered in this document

### Content Added:

#### 1. Automatic Authentication Passthrough
- Explanation of how it works with UC (Pattern 1)
- When to use it
- Link to official docs: https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/agent-authentication#automatic-authentication-passthrough

#### 2. On-Behalf-Of-User (OBO) Authentication
- Explanation of how it works with UC (Pattern 2)  
- Per-user row filters and column masks
- Token downscoping for security
- **Security Considerations callout** per user request
- Links to:
  - Main OBO docs: https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/agent-authentication#on-behalf-of-user-authentication
  - Security considerations: https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/agent-authentication#obo-security-considerations

#### 3. Manual Authentication (OAuth/PAT)
- OAuth (recommended) and PAT methods
- When to use manual authentication
- Link to official docs: https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#manual-authentication
- Includes OAuth best practices link per user request

#### 4. Important Note
Added explicit guidance:
> "For complete Agent Framework authentication setup (code examples, MLflow integration, resource declarations), see the official Agent Authentication documentation. This document focuses on **how UC enforces authorization** once authentication is established."

---

## Why This Change

### Problem:
- The `02-AUTHORIZATION-WITH-UC.md` document references "Pattern 1, 2, 3" for authentication
- However, it doesn't explain how **Agent Framework** specifically implements these patterns
- Users need to understand the connection between Agent Framework auth and UC authorization

### Solution:
- Added a bridge section that maps Agent Framework authentication methods to UC authorization patterns
- Included all official documentation links per user request
- Highlighted OBO security considerations (as specifically requested)
- Clarified scope: this doc is about **UC authorization**, Agent Framework docs cover **authentication implementation**

---

## What Was NOT Changed

### Intentionally Preserved:
- **No Python/code examples added** - This document remains focused on SQL and UC concepts
- **No Agent Framework setup code** - Users are directed to official docs for implementation
- **All existing UC content** - Row filters, column masks, GRANTs, ABAC patterns unchanged
- **SQL examples** - All SQL syntax for UC policies remains intact

### Why:
- `02-AUTHORIZATION-WITH-UC.md` is a **UC authorization reference**, not an Agent Framework tutorial
- Agent Framework authentication is complex and changes frequently - official docs are source of truth
- Adding code snippets here would duplicate (and potentially conflict with) official docs
- The document now **references** official docs clearly, maintaining single source of truth

---

## Documentation Links Verified

All links added are to **official Databricks documentation**:

✅ Azure (learn.microsoft.com):
- Main Agent Authentication: https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/agent-authentication
- Automatic Passthrough: https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/agent-authentication#automatic-authentication-passthrough
- OBO Authentication: https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/agent-authentication#on-behalf-of-user-authentication
- OBO Security Considerations: https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/agent-authentication#obo-security-considerations

✅ AWS (docs.databricks.com):
- Manual Authentication: https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#manual-authentication
- OAuth (recommended): https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication#oauth-authentication-recommended

---

## Impact

### User Benefit:
- ✅ Clear understanding of how Agent Framework auth integrates with UC authorization
- ✅ Direct links to official docs for implementation details
- ✅ Security considerations highlighted (OBO scope expansion risks)
- ✅ Guidance on when to use each authentication method
- ✅ No duplicate/conflicting code that could go stale

### Maintenance:
- ✅ Low maintenance burden - we link to official docs instead of duplicating them
- ✅ Official docs are kept up-to-date by Databricks
- ✅ Our doc focuses on UC concepts (stable, mature API)

---

## Verification

To verify the changes are correct:

1. **Check the new section exists:**
   ```bash
   grep -A 10 "Agent Framework Authentication Reference" \
     0-repo/databricks/ai-governance/02-AUTHORIZATION-WITH-UC.md
   ```

2. **Verify all links are valid:**
   - Open each URL to confirm they resolve correctly
   - Check that cloud selector works on Databricks docs

3. **Confirm no code conflicts:**
   ```bash
   grep -c "import\|from databricks\|WorkspaceClient" \
     0-repo/databricks/ai-governance/02-AUTHORIZATION-WITH-UC.md
   # Should return 0
   ```

---

**Status**: ✅ Complete - Agent Framework authentication properly referenced with official documentation links
