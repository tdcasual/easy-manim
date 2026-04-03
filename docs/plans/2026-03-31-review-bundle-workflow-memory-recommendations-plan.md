# Review Bundle Workflow Memory Recommendations Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface workflow memory recommendations directly in the review bundle so the owner can see pinned workflow memory and suggested reusable memories from the same review surface.

**Architecture:** Reuse the existing `WorkflowCollaborationService.list_workflow_memory_recommendations(...)` read model and attach it to `ReviewBundle` as an owner-only field. Collaborators should continue to receive `collaboration_memory_context` only, without private recommendation candidates from the owner's full memory corpus.

**Key Semantics:**
- Owner review bundle includes workflow memory recommendations.
- Collaborator review bundle leaves workflow recommendations empty or `None`.
- The new field is read-only and does not change workflow state.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Write Failing Tests

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`

Write tests that prove:
- owner review bundle exposes workflow memory recommendations
- collaborator review bundle does not expose workflow memory recommendations

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: FAIL because the review bundle does not yet expose the recommendation field.

### Task 2: Implement The Read Model Exposure

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

Add a new optional field on `ReviewBundle` and populate it only for owner-visible review bundles.

### Task 3: Verify

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`

Expected: PASS
