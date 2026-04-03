# Review Bundle Workflow Action Intents Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enrich owner-only `workflow_review_controls.available_actions` so each action card exposes explicit review intent and workflow-memory mutation preview without requiring callers to parse the raw request payload.

**Architecture:** Keep `available_actions` as the direct-consumption panel model, but add typed submodels for decision intent and memory-change preview. `ReviewBundleBuilder` should derive these fields from the already-produced action payloads so the recommendation logic stays in one place.

**Key Semantics:**
- Only the owner sees the enriched action-card metadata through `workflow_review_controls`.
- Every action card should expose the normalized review decision it will submit, if any.
- Workflow-memory-affecting actions should expose pin/unpin ids and counts in a typed preview model.
- Accept/retry actions should report no workflow-memory mutation.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- `pin_and_revise` cards expose `review_decision == "revise"` and a memory-change preview with one pin id
- blocked `accept` cards expose `review_decision == "accept"` and no memory-change preview
- ready `accept` cards expose `review_decision == "accept"` and no workflow-memory mutation

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because action cards do not yet expose typed intent and mutation preview fields.

### Task 2: Implement Action Intent Read Models

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add typed action-intent and workflow-memory-change preview models, then populate them directly from the existing action payloads.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
