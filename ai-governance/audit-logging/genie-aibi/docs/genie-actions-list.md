## Reference: Complete Genie Action List (70+ Actions)

This is the **official comprehensive list** of all Genie action names.

### Space-Level Actions (11 actions)
* `createSpace`, `genieCreateSpace` - Create space
* `updateSpace`, `genieUpdateSpace` - Update space
* `deleteSpace`, `trashSpace`, `genieTrashSpace` - Delete/trash space
* `cloneSpace` - Clone space
* `getSpace`, `genieGetSpace` - Get space
* `genieListSpaces` - List spaces
* `updateGenieColumnConfigs` - Update column configs
* `updateSampleQuestions` - Update sample questions

### Conversation-Level Actions (5 actions)
* `createConversation` - Create conversation
* `updateConversation` - Update conversation
* `deleteConversation` - Delete conversation
* `getConversation` - Get conversation
* `listConversations`, `genieListConversations` - List conversations

### Message-Level Actions (54+ actions)

**Message CRUD:**
* `createConversationMessage`, `genieCreateConversationMessage`, `genieStartConversationMessage`
* `updateConversationMessage`, `regenerateConversationMessage`
* `deleteConversationMessage`
* `cancelMessage`
* `getConversationMessage`, `genieGetConversationMessage`
* `genieListConversationMessages`, `listGenieSpaceMessages`, `listGenieSpaceUserMessages`
* `updateMessageAttachment`

**Query Execution:**
* `executeMessageQuery`, `genieExecuteMessageQuery`
* `executeMessageAttachmentQuery`, `genieExecuteMessageAttachmentQuery`
* `executeQuery`
* `executeFullQueryResult`

**Query Results:**
* `getMessageQueryResult`, `genieGetMessageQueryResult`
* `getMessageAttachmentQueryResult`, `genieGetMessageAttachmentQueryResult`
* `genieGetQueryResultByAttachment`
* `getQueryResult`
* `genieGenerateDownloadFullQueryResult`
* `summarizeSqlExecutionResults`

**Feedback:**
* `updateConversationMessageFeedback`
* `genieSendMessageFeedback`

**Comments:**
* `createConversationMessageComment`
* `deleteConversationMessageComment`
* `listConversationMessageComments`

**Instructions:**
* `createInstruction`
* `updateInstruction`
* `deleteInstruction`
* `listInstructions`

**Curated Questions:**
* `createCuratedQuestion`
* `updateCuratedQuestion`
* `listCuratedQuestions`

**Files:**
* `createFile`
* `deleteFile`

**Evaluation (Testing/QA):**
* `createEvaluationRun`, `getEvaluationRun`, `listEvaluationRuns`
* `cancelEvaluationRun`, `resumeEvaluationRun`
* `createEvaluationResult`, `getEvaluationResult`, `updateEvaluationResult`
* `getEvaluationResultDetails`, `listEvaluationResults`
* `startBenchmarkSuggestions`

---

**Total: 70+ distinct action names**

**Source:** Official Genie action list provided by user