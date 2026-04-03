# Review Bundle Workflow Action Sections Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add owner-only `action_sections` and per-card `action_family` under `workflow_review_controls` so callers can render workflow review actions in stable groups without inferring layout priority or whether a card is a plain review action or a combined workflow-memory action.

**Architecture:** Keep `available_actions` as the canonical flat action list, but enrich each card with a normalized `action_family` and derive a non-overlapping sectioned view from it. Sections should be presentation-ready and ordered by priority: recommended first, then other available actions, then blocked actions.

**Key Semantics:**
- Only the owner sees `action_sections` through `workflow_review_controls`.
- Each action card exposes `action_family` such as `review_decision` or `combined`.
- Sections must be non-overlapping; an action appears in exactly one section.
- Recommended section contains primary actions, available contains non-primary unblocked actions, blocked contains blocked actions.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- `pin_and_revise` owner controls expose `action_sections` ordered as `recommended`, `available`, `blocked`
- the recommended card is `action_family == "combined"`, the plain revise card is `review_decision`, and blocked accept is also `review_decision`
- ready-to-accept tasks expose a single `recommended` section containing the accept card

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because cards do not yet expose `action_family` and review controls do not yet expose `action_sections`.

### Task 2: Implement Action Section Read Models

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add typed section models plus normalized action-family derivation and populate the grouped section view from the existing available-action cards.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest -q`

Expected: PASS
