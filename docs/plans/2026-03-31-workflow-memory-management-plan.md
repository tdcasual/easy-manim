# Workflow Memory Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a coherent owner-managed workflow memory subsystem that can recommend reusable long-term memories, pin or unpin them at the workflow root, and make later workflow revisions inherit pinned memory by default.

**Architecture:** Treat the root task as the workflow-level memory carrier. Root `selected_memory_ids` remain the source of truth for pinned workflow memory, while child tasks can still attach task-local memory. `WorkflowCollaborationService` owns recommendation and pin management, and `TaskService` inherits workflow-pinned memory for owner revisions when `memory_ids` is omitted.

**Key Semantics:**
- `memory_ids=None` on owner revision means inherit workflow-pinned memory from the root task.
- `memory_ids=[]` on owner revision means explicit clear and do not attach persistent memory.
- Collaborator-triggered workflow revisions remain restricted to inherited workflow memory only.
- Workflow pinning recomputes `persistent_memory_context_summary` and `persistent_memory_context_digest` on the root task.

**Tech Stack:** Python, Pydantic, FastAPI/MCP existing workflow APIs, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/unit/application/test_workflow_collaboration_service.py`
- Modify: `tests/integration/test_revision_and_cancel.py`
- Modify: `tests/integration/test_http_multi_agent_workflow_api.py`
- Modify: `tests/integration/test_mcp_multi_agent_workflow_tools.py`

**Step 1: Add unit coverage for workflow memory recommendation and pin lifecycle**

Write tests that prove:
- owner can request workflow memory recommendations derived from root prompt and case memory
- owner can pin memory to the workflow root and root task digest is recomputed
- owner can unpin memory and the root task context is updated
- non-owner cannot manage workflow memory

**Step 2: Add revision inheritance coverage**

Write a test that proves:
- owner revision with `memory_ids=None` inherits root pinned memory
- owner revision with `memory_ids=[]` clears persistent memory explicitly

**Step 3: Add MCP and HTTP management coverage**

Write integration tests that prove:
- owner can list recommendations and pin/unpin via MCP/HTTP
- non-owner receives access denied

**Step 4: Run targeted tests to verify RED**

Run:
- `.venv/bin/python -m pytest tests/unit/application/test_workflow_collaboration_service.py -q`
- `.venv/bin/python -m pytest tests/integration/test_revision_and_cancel.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`

Expected: FAIL because workflow memory management APIs do not exist yet.

### Task 2: Implement Workflow Memory Management

**Files:**
- Modify: `src/video_agent/application/workflow_collaboration_service.py`
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/task_service.py`

**Step 1: Add workflow recommendation and pin APIs**

Implement owner-only methods that:
- derive a recommendation query from root prompt and latest case-memory review summary
- rank records through `PersistentMemoryService.query_agent_memories(...)`
- pin and unpin root workflow memory ids deterministically
- append audit events for pin and unpin operations

**Step 2: Make owner revisions inherit workflow-pinned memory**

Update owner revision logic so:
- omitted `memory_ids` inherits root workflow memory
- explicit empty list clears memory

### Task 3: Expose Management Surfaces

**Files:**
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/http_api.py`

**Step 1: Add workflow memory recommendation and pin management tools**

Expose owner-only MCP/HTTP surfaces for:
- listing workflow memory recommendations
- pinning workflow memory
- unpinning workflow memory

### Task 4: Verify

**Step 1: Run targeted tests**

Run:
- `.venv/bin/python -m pytest tests/unit/application/test_workflow_collaboration_service.py -q`
- `.venv/bin/python -m pytest tests/integration/test_revision_and_cancel.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`

Expected: PASS

**Step 2: Run full suite**

Run:
- `.venv/bin/python -m pytest -q`

Expected: PASS
