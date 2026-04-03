# Review Bundle Workflow Status Summary Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an owner-only `status_summary` under `workflow_review_controls` so UI and workflow agents can read the current review readiness and workflow-memory posture from one compact aggregate instead of stitching together blockers, action cards, recommendations, and recent events.

**Architecture:** Keep the status summary read-only and derive it from the existing review controls inputs: acceptance blockers, suggested next actions, current pinned memory state, workflow memory recommendations, and recent workflow memory events. This should sit alongside `available_actions`, not replace it.

**Key Semantics:**
- `status_summary` is owner-only through `workflow_review_controls`.
- It should expose the currently recommended action id, acceptance readiness, and acceptance blockers.
- It should expose pinned-memory count plus pending workflow-memory recommendation count.
- It should expose whether workflow memory updates are pending and the latest workflow memory event when available.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- owner controls expose a `status_summary` with `recommended_action_id == "pin_and_revise"` and pending-memory counts when new memory should be pinned
- owner controls expose the latest workflow memory event in the summary when a pin happened
- completed ready tasks expose `acceptance_ready == True` and `recommended_action_id == "accept"`

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because `workflow_review_controls` does not yet expose `status_summary`.

### Task 2: Implement Status Summary Read Model

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add typed status-summary models and populate them from the existing review-controls signals.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
