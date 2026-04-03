# Workflow Collaboration Memory Context Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose a shared, role-aware collaboration memory context so planner/reviewer/repairer views can consume selected long-term memory and workflow case memory through one consistent read model.

**Architecture:** Keep memory access safe and explicit by building workflow collaboration memory only from task-selected persistent memory plus workflow-owned case memory artifacts. Reuse `WorkflowCollaborationService` as the single source of truth, then surface the result through `ReviewBundle` so human or automated reviewers can consume the same role-shaped context.

**Tech Stack:** Python, Pydantic, FastAPI/MCP existing workflow APIs, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/unit/application/test_workflow_collaboration_service.py`
- Modify: `tests/integration/test_review_bundle_builder.py`

**Step 1: Add unit coverage for workflow collaboration memory context**

Write tests that prove:
- selected persistent memory records are loaded into workflow collaboration memory
- planner/reviewer/repairer each get distinct summaries
- case memory notes are folded into the appropriate role summaries

**Step 2: Run the unit test to verify it fails**

Run:
- `.venv/bin/python -m pytest tests/unit/application/test_workflow_collaboration_service.py -q`

Expected: FAIL because the workflow memory context API and models do not exist yet.

**Step 3: Add integration coverage for review bundles**

Write a test that proves `ReviewBundle` exposes `collaboration_memory_context`.

**Step 4: Run the integration test to verify it fails**

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py::test_review_bundle_builder_exposes_collaboration_memory_context -q`

Expected: FAIL because the bundle field is not populated yet.

### Task 2: Add Shared Collaboration Memory Models

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`

**Step 1: Add typed role-aware memory models**

Add models for:
- workflow memory items
- per-role planner/reviewer/repairer memory view
- workflow-level collaboration memory context payload

### Task 3: Build Collaboration Memory Context In The Service Layer

**Files:**
- Modify: `src/video_agent/application/workflow_collaboration_service.py`
- Modify: `src/video_agent/server/app.py` if constructor wiring changes

**Step 1: Build memory context from selected persistent memory and case memory**

Implement a workflow-level builder that:
- resolves root/current task shared memory IDs
- loads selected persistent memories through `PersistentMemoryService`
- reads case memory through `CaseMemoryService`
- emits deterministic role summaries for planner/reviewer/repairer

### Task 4: Expose The Read Model

**Files:**
- Modify: `src/video_agent/application/review_bundle_builder.py`

**Step 1: Add collaboration memory context to `ReviewBundle`**

Populate the new bundle field from `WorkflowCollaborationService`.

### Task 5: Verify

**Step 1: Run targeted tests**

Run:
- `.venv/bin/python -m pytest tests/unit/application/test_workflow_collaboration_service.py -q`
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: PASS

**Step 2: Run full suite**

Run:
- `.venv/bin/python -m pytest -q`

Expected: PASS
