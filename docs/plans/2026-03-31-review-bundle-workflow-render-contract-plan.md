# Review Bundle Workflow Render Contract Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add owner-only `render_contract` under `workflow_review_controls` so UI and workflow agents can render the owner review panel with stable layout defaults instead of inferring section order, default expansion, panel priority, or footer dismissibility from multiple separate fields.

**Architecture:** Keep `render_contract` as a pure presentation aggregate derived from existing read models: `panel_header`, `action_sections`, `status_summary`, and `applied_action_feedback`. It should not introduce any new workflow behavior or write APIs.

**Key Semantics:**
- Only the owner sees `render_contract` through `workflow_review_controls`.
- It should expose panel tone/priority, section order, default focus section, and default expanded sections.
- It should expose the sticky primary action id for layouts that keep one CTA pinned.
- It should expose whether applied feedback is dismissible when a recent workflow-memory update exists.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- `pin_and_revise` workflows expose a high-priority render contract with `recommended` focus and `recommended` plus `blocked` expanded by default
- workflows with recent applied feedback mark that feedback as dismissible
- ready-to-accept tasks expose a normal-priority render contract with only `recommended` expanded and `accept` as the sticky primary action

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because `workflow_review_controls` does not yet expose `render_contract`.

### Task 2: Implement Render Contract Read Model

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add typed render-contract models and populate them from the existing owner review-panel read models.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
