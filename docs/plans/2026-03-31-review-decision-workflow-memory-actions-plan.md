# Review Decision Workflow Memory Actions Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let the workflow owner pin or unpin workflow memory directly when submitting a review decision, so review and workflow-memory management can happen in one round trip.

**Architecture:** Extend the review-decision request and outcome models with explicit workflow memory mutation fields. `MultiAgentWorkflowService` applies owner-requested workflow memory pin updates before it executes the chosen review action, so follow-up revisions inherit the new root workflow memory immediately.

**Key Semantics:**
- `memory_ids` keeps its current meaning: explicit child revision memory attachment.
- `pin_workflow_memory_ids` and `unpin_workflow_memory_ids` mutate root workflow pinned memory.
- Only the owner can apply workflow memory mutations through review decision.
- Review decision responses return the resulting workflow memory state when mutations were applied.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_http_multi_agent_workflow_api.py`
- Modify: `tests/integration/test_mcp_multi_agent_workflow_tools.py`

Write tests that prove:
- owner can pin workflow memory during review decision and the created revision inherits it
- collaborator cannot mutate workflow memory through review decision

Run:
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`

Expected: FAIL because review-decision payloads do not yet support workflow memory mutations.

### Task 2: Implement Review Decision Workflow Memory Mutations

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/workflow_collaboration_service.py`
- Modify: `src/video_agent/application/multi_agent_workflow_service.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/http_api.py`

Implement owner-only workflow memory pin/unpin application in the review-decision flow and include resulting state in the response.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
