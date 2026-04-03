# Workflow Collaboration Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate workflow collaboration ACLs, participant management, and collaborator decision routing into a dedicated `WorkflowCollaborationService`.

**Architecture:** Keep `TaskService` focused on task lifecycle and owner-authorized mutations, while moving workflow-scoped collaboration concerns into a single application service. Route `ReviewBundleBuilder`, `MultiAgentWorkflowService`, MCP tools, and HTTP participant endpoints through that collaboration service so the collaboration model has one home instead of being spread across several modules.

**Tech Stack:** Python, FastAPI, MCP, Pydantic, SQLite, pytest

---

### Task 1: Lock The Refactor With Characterization Tests

**Files:**
- Create: `tests/unit/application/test_workflow_collaboration_service.py`
- Modify: `tests/integration/test_mcp_multi_agent_workflow_tools.py`
- Modify: `tests/integration/test_http_multi_agent_workflow_api.py`

**Step 1: Write the failing unit tests**

Add tests for:
- participant with `review_bundle:read` gets workflow read access
- participant upsert/remove records root-task audit events
- collaborator mutation path still resolves owner-owned child tasks

**Step 2: Run the new unit tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/unit/application/test_workflow_collaboration_service.py -q`

Expected: FAIL because the service does not exist yet.

**Step 3: Keep the existing integration tests as external contract coverage**

Use existing MCP/HTTP review and participant tests as behavior lock during the refactor.

### Task 2: Introduce `WorkflowCollaborationService`

**Files:**
- Create: `src/video_agent/application/workflow_collaboration_service.py`
- Modify: `src/video_agent/application/task_service.py`

**Step 1: Add the collaboration service**

Implement methods for:
- `require_workflow_access`
- `list_workflow_participants`
- `upsert_workflow_participant`
- `remove_workflow_participant`
- collaborator review-decision mutation helpers

**Step 2: Keep `TaskService` task-centric**

Move workflow-specific owner/collaborator branching out of `TaskService`.
Keep only owner-authorized task operations and owner-neutral internal mutation helpers in `TaskService`.

**Step 3: Preserve audit behavior**

Participant upsert/remove must still write deterministic task events on the workflow root.

### Task 3: Rewire Collaboration Callers

**Files:**
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Modify: `src/video_agent/application/multi_agent_workflow_service.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/server/fastmcp_server.py`

**Step 1: Inject the collaboration service**

Wire it into `AppContext` and pass it to the builder/workflow/API layers.

**Step 2: Switch call sites**

Replace direct `TaskService` workflow ACL usage with `WorkflowCollaborationService`.

**Step 3: Keep server layer thin**

MCP and HTTP participant endpoints should only delegate to the collaboration service.

### Task 4: Verify

**Files:**
- Modify only if regressions require it

**Step 1: Run targeted tests**

Run:
- `.venv/bin/python -m pytest tests/unit/application/test_workflow_collaboration_service.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py tests/integration/test_http_multi_agent_workflow_api.py tests/integration/test_agent_auth_tools.py tests/integration/test_agent_resource_isolation.py -q`

Expected: PASS

**Step 2: Run full suite**

Run: `.venv/bin/python -m pytest -q`

Expected: PASS
