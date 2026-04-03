# Review Bundle Workflow Review Controls Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an owner-only `workflow_review_controls` aggregate to `ReviewBundle` so callers can consume current workflow memory state, recent workflow memory audit events, recommendations, and the action contract from one stable location.

**Architecture:** Keep the existing top-level workflow memory fields for compatibility, but introduce one aggregate read model that consolidates the pieces already exposed separately. `ReviewBundleBuilder` should derive the aggregate from the existing root-task state plus `WorkflowCollaborationService` read models.

**Key Semantics:**
- Only the owner sees `workflow_review_controls`.
- The aggregate is read-only and mirrors existing workflow memory state.
- Recent events include workflow memory events only, not participant events.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- owner review bundle exposes `workflow_review_controls` with current state and recent workflow memory events
- collaborator review bundle does not expose `workflow_review_controls`

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because the bundle does not yet expose the aggregate controls field.

### Task 2: Implement The Aggregate Read Model

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add typed controls models and populate them from the existing workflow memory read models plus filtered collaboration events.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
