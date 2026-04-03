# Review Bundle Workflow Panel Header Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add owner-only `panel_header` under `workflow_review_controls` so callers can render the top of the workflow review panel from one stable aggregate instead of stitching together status summary, badges, and recent memory event hints.

**Architecture:** Keep `panel_header` purely derived from existing review-controls signals: `status_summary`, `action_sections`, and recent workflow memory events. The header should expose a normalized title, tone, summary, compact badges, and an optional highlighted workflow-memory event.

**Key Semantics:**
- Only the owner sees `panel_header` through `workflow_review_controls`.
- `tone` should be derived from the current recommended action and readiness state.
- `summary` should explain the current best next step in one short sentence.
- `badges` should surface recommended action, pending memory recommendations, and blocker count when relevant.
- `highlighted_event` should summarize the latest workflow memory pin/unpin event when one exists.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- pin-and-revise workflows expose an `attention` panel header with badges for recommended action, pending memory, and blockers
- workflows with a recent memory pin expose a highlighted `workflow_memory_pinned` event in the header
- ready-to-accept tasks expose a `ready` panel header with an `accept` recommendation badge and no highlighted event

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because `workflow_review_controls` does not yet expose `panel_header`.

### Task 2: Implement Panel Header Read Model

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add typed panel-header models and populate them from the existing review-controls state.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
