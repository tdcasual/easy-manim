# Review Bundle Suggested Next Actions Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an owner-oriented `suggested_next_actions` panel under `workflow_review_controls` so review surfaces can show the most likely next workflow action instead of forcing callers to infer it from raw state.

**Architecture:** Keep the new panel read-only and derived from existing bundle state. Reuse current signals such as acceptance blockers, task status, workflow memory recommendations, and action contract examples to produce a small set of suggested actions with one primary recommendation and optional alternatives.

**Key Semantics:**
- If unpinned workflow memory recommendations exist, prefer `pin_and_revise`.
- If the task is completed and acceptance is not blocked, prefer `accept`.
- If accept is blocked, expose that as a blocked alternative with reasons.
- Only the owner sees the suggested-next-actions panel through `workflow_review_controls`.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- owner review controls recommend `pin_and_revise` when unpinned workflow memory recommendations exist
- completed ready tasks recommend `accept`

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because the controls object does not yet expose suggested next actions.

### Task 2: Implement Suggested Next Actions

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add typed suggested-action models and populate them from the current bundle signals.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
