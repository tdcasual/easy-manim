# Review Bundle Workflow Applied Action Feedback Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add owner-only `applied_action_feedback` under `workflow_review_controls` so callers can render a footer-style confirmation card that explains the most recent workflow-memory change and the recommended follow-up action.

**Architecture:** Keep this feedback read-only and derive it from the existing recent workflow memory events plus `status_summary`. It should be complementary to `panel_header`: the header explains current status, while `applied_action_feedback` explains the latest applied workflow-memory mutation and what the owner should do next.

**Key Semantics:**
- Only the owner sees `applied_action_feedback` through `workflow_review_controls`.
- If no recent workflow-memory event exists, `applied_action_feedback` should be `None`.
- The feedback should expose the latest event type, memory id, a tone, a short title/summary, and the recommended follow-up action id when available.
- Pin and unpin events should produce different titles/summaries, but both should remain additive read-model data only.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- workflows with a recent `workflow_memory_pinned` event expose `applied_action_feedback` with the pinned memory id and follow-up action id
- workflows with no recent workflow-memory event expose `applied_action_feedback is None`
- ready-to-accept tasks also expose `applied_action_feedback is None`

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because `workflow_review_controls` does not yet expose `applied_action_feedback`.

### Task 2: Implement Applied Action Feedback Read Model

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add typed applied-feedback models and populate them from the latest workflow-memory event plus the current `status_summary`.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
