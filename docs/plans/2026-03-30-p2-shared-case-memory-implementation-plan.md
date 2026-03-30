# P2 Shared Case Memory Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persist typed shared case memory for each delivery case and let new repair/challenger branches inherit structured constraints from that memory.

**Architecture:** Use a lightweight artifact-backed case-memory snapshot keyed by root task id instead of introducing a new database table. `WorkflowEngine` and `TaskService` will write structured planner/reviewer/decision facts into the snapshot, `ReviewBundleBuilder` will expose it, and branch creation paths will append a concise shared-constraints preface to child feedback.

**Tech Stack:** Python, Pydantic, JSON artifact storage, existing `WorkflowEngine`/`TaskService`/`ReviewBundleBuilder`, pytest

---

### Task 1: Add failing tests for case memory persistence and inheritance

**Files:**
- Modify: `tests/integration/test_review_bundle_builder.py`
- Modify: `tests/integration/test_workflow_completion.py`

**Step 1: Write failing bundle test**

Run one real workflow with quality threshold high enough to produce a reviewer rejection and queued challenger. Assert `get_review_bundle(...)` exposes `case_memory` with:

- non-empty `planner_notes`
- non-empty `review_findings`
- non-empty `repair_constraints`
- non-empty `delivery_invariants`

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_review_bundle_builder.py::test_review_bundle_builder_exposes_shared_case_memory -q
```

Expected: FAIL because no shared case memory is persisted or surfaced yet.

**Step 3: Write failing inheritance test**

Using the existing auto-challenger flow, assert the queued challenger child feedback now includes a shared constraints preface derived from case memory.

**Step 4: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_workflow_completion.py::test_auto_challenger_feedback_inherits_shared_case_memory_constraints -q
```

Expected: FAIL because child feedback is currently just the raw challenger prompt.

### Task 2: Implement artifact-backed shared case memory

**Files:**
- Create: `src/video_agent/domain/case_memory_models.py`
- Create: `src/video_agent/application/case_memory_service.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/server/app.py`

**Step 1: Add typed case-memory model and artifact IO**

Persist a root-task keyed snapshot containing:

- `planner_notes`
- `review_findings`
- `repair_constraints`
- `branch_comparisons`
- `decision_log`
- `delivery_invariants`

**Step 2: Surface case memory in review bundle**

Expose the snapshot as `bundle.case_memory`.

**Step 3: Run bundle test**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_review_bundle_builder.py::test_review_bundle_builder_exposes_shared_case_memory -q
```

Expected: PASS

### Task 3: Wire updates and feedback inheritance

**Files:**
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/task_service.py`

**Step 1: Record planner and reviewer facts into case memory**

Store:

- planner context after scene planning
- review findings / must-fix issues / recovery hints after review
- branch comparison and arbitration decisions when available
- winner selection decisions

**Step 2: Inherit shared constraints in child feedback**

For challenger and repair-oriented child creation, prepend a concise structured constraints section from current case memory.

**Step 3: Run focused tests**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_review_bundle_builder.py::test_review_bundle_builder_exposes_shared_case_memory tests/integration/test_workflow_completion.py::test_auto_challenger_feedback_inherits_shared_case_memory_constraints -q
```

Expected: PASS

### Task 4: Run verification

**Files:**
- No code changes

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_review_bundle_builder.py tests/integration/test_workflow_completion.py tests/integration/test_multi_agent_workflow_service.py tests/integration/test_task_reliability_reconciler.py -q
```

Expected: PASS
