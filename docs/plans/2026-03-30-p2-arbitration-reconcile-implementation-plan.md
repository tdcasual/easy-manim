# P2 Arbitration Reconcile Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure startup/watchdog reconciliation can recover a completed accepted challenger that should already have won, so cases do not stay stuck on an outdated incumbent after restart or interruption.

**Architecture:** Reuse the existing automatic challenger arbitration logic instead of inventing a second reconcile-only selector. `TaskReliabilityService` should detect unresolved completed challenger leaves, call the workflow engine's deterministic arbitration helper, and append explicit reliability events when it promotes or preserves the incumbent.

**Tech Stack:** Python, Pydantic, SQLite, existing `TaskReliabilityService`/`WorkflowEngine`/`DeliveryCaseService`, pytest

---

### Task 1: Add failing reconciliation test

**Files:**
- Modify: `tests/integration/test_task_reliability_reconciler.py`

**Step 1: Write the failing test**

Create a root task whose persisted state looks like this:

- root is completed, delivered, and still points to incumbent
- challenger child is completed, delivered, `branch_kind == "challenger"`
- challenger has an accepted quality score and final video artifact
- case selection still points to incumbent

After creating a fresh app context, assert startup reconciliation:

- switches root `resolved_task_id` to challenger
- switches case `selected_task_id` to challenger
- exposes challenger video through `get_video_result(...)`
- appends a `task_reliability_reconciled` event describing arbitration promotion

**Step 2: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_task_reliability_reconciler.py::test_startup_reconciler_promotes_completed_accepted_challenger_after_restart -q
```

Expected: FAIL because reconciliation does not yet evaluate challenger arbitration.

### Task 2: Implement arbitration-aware reconciliation

**Files:**
- Modify: `src/video_agent/application/task_reliability_service.py`

**Step 1: Detect unresolved challenger leaves**

Before generic delivered-descendant sync, detect:

- leaf is a challenger
- leaf is completed and delivered
- root still points somewhere else

**Step 2: Reuse workflow-engine auto arbitration**

Call the workflow engine arbitration helper and record its decision.

If it promotes:

- append a reliability event like `auto_arbitration_promoted`

If it does not:

- append a reliability event like `auto_arbitration_kept_incumbent`

**Step 3: Run focused reconcile tests**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_task_reliability_reconciler.py::test_startup_reconciler_promotes_completed_accepted_challenger_after_restart tests/integration/test_task_reliability_reconciler.py::test_startup_reconciler_syncs_root_to_existing_delivered_descendant -q
```

Expected: PASS

### Task 3: Run verification

**Files:**
- No code changes

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_task_reliability_reconciler.py tests/integration/test_workflow_completion.py tests/integration/test_guaranteed_video_delivery.py tests/integration/test_auto_repair_loop.py -q
```

Expected: PASS
