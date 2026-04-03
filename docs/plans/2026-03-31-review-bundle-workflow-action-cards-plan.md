# Review Bundle Workflow Action Cards Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an owner-only `available_actions` panel under `workflow_review_controls` so UI and workflow agents can consume ready-to-render review action cards without inferring labels, availability, or payload structure from multiple fields.

**Architecture:** Keep `suggested_next_actions` as the recommendation layer, but add a richer `available_actions` read model that normalizes each review action into a stable card. `ReviewBundleBuilder` should derive the cards from existing signals: task status, acceptance blockers, workflow memory recommendations, workflow memory action-contract examples, and current pinned memory state.

**Key Semantics:**
- Only the owner sees `available_actions`.
- Every card is read-only and includes action identity, title, summary, blocked state, reasons, and request payload.
- Cards cover the main review decisions (`accept`, `revise`, `retry`) plus workflow-memory-aware combined actions such as `pin_and_revise`.
- One card should be marked as primary so callers do not need to cross-reference `suggested_next_actions` to choose the default CTA.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- owner review controls expose `available_actions` with a primary `pin_and_revise` card when unpinned workflow memory recommendations exist
- blocked `accept` is still exposed as a non-primary card with blocker reasons
- completed ready tasks expose an unblocked primary `accept` card

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because the controls object does not yet expose `available_actions`.

### Task 2: Implement Action Card Read Models

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add typed action-card models and populate them from the existing workflow review signals without introducing new write APIs.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
