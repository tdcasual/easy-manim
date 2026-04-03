# Workflow Participant Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add explicit owner-managed workflow participant APIs so workflow collaborators can be shared through HTTP and MCP instead of only test seeding.

**Architecture:** Keep workflow participation rooted at the workflow `root_task_id`, and expose a thin owner-only management surface that reuses the existing `workflow_participants` persistence model. Add the smallest practical API slice first: `list`, `add/update`, and `remove`, while preserving the current rule that collaborators do not gain generic `task:mutate` authority.

**Tech Stack:** Python, FastAPI, MCP, Pydantic, SQLite, pytest

---

### Task 1: Add Failing Integration Tests

**Files:**
- Modify: `tests/integration/test_mcp_multi_agent_workflow_tools.py`
- Modify: `tests/integration/test_http_multi_agent_workflow_api.py`

**Step 1: Write the failing MCP tests**

Add tests for:
- owner can add a workflow participant and list it
- owner can remove a workflow participant
- non-owner cannot manage workflow participants

**Step 2: Run MCP targeted tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`

Expected: FAIL because management tools do not exist yet.

**Step 3: Write the failing HTTP tests**

Add tests for:
- owner can `GET /api/tasks/{task_id}/workflow-participants`
- owner can `POST /api/tasks/{task_id}/workflow-participants`
- owner can `DELETE /api/tasks/{task_id}/workflow-participants/{agent_id}`
- non-owner receives `403`

**Step 4: Run HTTP targeted tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`

Expected: FAIL because the routes do not exist yet.

### Task 2: Add Minimal Service And Storage Support

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/domain/review_workflow_models.py`

**Step 1: Add owner-only workflow participant helpers**

Implement:
- list workflow participants for a task lineage
- upsert a workflow participant for a task lineage
- delete a workflow participant for a task lineage

**Step 2: Keep authorization narrow**

Rules:
- owner-only for add/remove/list
- require `task:read` for list and `task:mutate` for add/remove
- always normalize to the workflow `root_task_id`

**Step 3: Add any missing store helper**

If needed, add `delete_workflow_participant(...)` and keep return values deterministic.

### Task 3: Expose MCP And HTTP APIs

**Files:**
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/http_api.py`

**Step 1: Add MCP tools**

Implement:
- `list_workflow_participants`
- `upsert_workflow_participant`
- `remove_workflow_participant`

**Step 2: Add HTTP request model and routes**

Implement:
- `GET /api/tasks/{task_id}/workflow-participants`
- `POST /api/tasks/{task_id}/workflow-participants`
- `DELETE /api/tasks/{task_id}/workflow-participants/{agent_id}`

**Step 3: Preserve deterministic errors**

Use existing auth normalization:
- `401` for unauthenticated in required auth mode
- `403` for owner or scope violations

### Task 4: Verify

**Files:**
- Modify: `tests/unit/adapters/storage/test_sqlite_store.py` if store coverage needs extension

**Step 1: Run targeted tests**

Run:
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`

Expected: PASS

**Step 2: Run full suite**

Run: `.venv/bin/python -m pytest -q`

Expected: PASS
