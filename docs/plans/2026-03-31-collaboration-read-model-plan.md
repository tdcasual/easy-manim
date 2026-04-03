# Collaboration Read Model Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a unified collaboration summary read model that is exposed consistently through `ReviewBundle` and runtime status.

**Architecture:** Reuse `WorkflowCollaborationService` as the single source for collaboration summaries instead of rebuilding participant and audit views separately in `ReviewBundleBuilder` and `RuntimeService`. Keep the first slice intentionally small: summarize active participants, role/capability counts, and recent collaboration audit events.

**Tech Stack:** Python, FastAPI, MCP, Pydantic, SQLite, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/unit/application/test_workflow_collaboration_service.py`
- Modify: `tests/integration/test_review_bundle_builder.py`
- Modify: `tests/integration/test_runtime_status_tool.py`

**Step 1: Add unit coverage for collaboration summary building**

Write tests that prove:
- workflow summary exposes active participants
- role and capability counts are aggregated
- recent participant audit events are included in order

**Step 2: Run unit tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/unit/application/test_workflow_collaboration_service.py -q`

Expected: FAIL because summary APIs do not exist yet.

**Step 3: Add integration coverage**

Write tests that prove:
- `ReviewBundle` exposes `collaboration_summary`
- runtime status exposes aggregated `collaboration_summary`

**Step 4: Run targeted integration tests to verify they fail**

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py::test_review_bundle_builder_exposes_collaboration_summary -q`
- `.venv/bin/python -m pytest tests/integration/test_runtime_status_tool.py::test_runtime_status_exposes_collaboration_summary -q`

Expected: FAIL because the new fields do not exist yet.

### Task 2: Add Shared Read Models

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/workflow_collaboration_service.py`

**Step 1: Add collaboration summary models**

Add small typed models for:
- active participants
- role/capability count maps
- recent participant events
- workflow summary and runtime summary payloads

**Step 2: Build summaries in `WorkflowCollaborationService`**

Implement:
- workflow-level summary by `task_id`
- system/runtime-level aggregate summary across root workflows

### Task 3: Expose The Read Model

**Files:**
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/server/app.py` if dependency wiring changes

**Step 1: Add `collaboration_summary` to `ReviewBundle`**

Populate it from the collaboration service.

**Step 2: Add `collaboration_summary` to runtime status**

Populate it from the collaboration service through `RuntimeService`.

### Task 4: Verify

**Step 1: Run targeted tests**

Run:
- `.venv/bin/python -m pytest tests/unit/application/test_workflow_collaboration_service.py -q`
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py tests/integration/test_runtime_status_tool.py -q`

Expected: PASS

**Step 2: Run full suite**

Run: `.venv/bin/python -m pytest -q`

Expected: PASS
