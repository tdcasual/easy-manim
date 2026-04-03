# Review Bundle Workflow Memory Action Contract Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose an owner-only workflow memory action contract through `ReviewBundle` so UIs and agents can submit batch pin/unpin changes during `review-decision` without guessing request shape.

**Architecture:** Keep the contract read-only and derived from the existing workflow memory recommendation state. `ReviewBundleBuilder` should publish field names, batch support, response field name, and a few contextual request examples that use the current pinned and recommended memory ids.

**Key Semantics:**
- Only the owner sees the action contract.
- Contract examples are full `review-decision` request bodies, not loose fragments.
- Contract supports pin-only, unpin-only, and replace-in-one-request examples when the necessary ids are available.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- owner review bundle exposes a workflow memory action contract with batch pin/unpin examples
- collaborator review bundle does not expose the action contract

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because the bundle does not yet expose a workflow memory action contract.

### Task 2: Implement The Contract Read Model

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add typed contract models and populate contextual examples from the current workflow memory recommendation state.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
