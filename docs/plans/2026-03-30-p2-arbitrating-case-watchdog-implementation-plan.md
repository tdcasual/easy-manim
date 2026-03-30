# P2 Arbitrating Case Watchdog Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make accepted delivered challengers surface as explicit `arbitrating` delivery cases so startup/watchdog recovery can detect and resolve cases stuck between challenger completion and winner selection.

**Architecture:** Extend `DeliveryCaseService` case-state derivation to mark a case as `arbitrating` only when a delivered accepted challenger exists but has not yet been selected. Keep recovery logic inside the existing `TaskReliabilityService` challenger reconciliation path so restart/watchdog behavior remains deterministic and reuses current arbitration helpers.

**Tech Stack:** Python, Pydantic, SQLite, existing `DeliveryCaseService`/`TaskReliabilityService`/`WorkflowEngine`, pytest

---

### Task 1: Add failing arbitration-state tests

**Files:**
- Modify: `tests/integration/test_delivery_case_orchestration.py`
- Modify: `tests/integration/test_task_reliability_reconciler.py`

**Step 1: Write the failing delivery-case status test**

Create a delivered root plus a delivered accepted challenger child whose `resolved_task_id` still points at the incumbent. Sync the case and assert:

- `case.status == "arbitrating"`
- `case.selected_task_id` still points at the incumbent
- `case.active_task_id` points at the challenger

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_delivery_case_orchestration.py::test_sync_case_marks_delivered_accepted_challenger_as_arbitrating -q
```

Expected: FAIL because the case currently resolves to `completed`.

**Step 3: Write the failing reconcile test**

Persist a stale delivery case with `status == "arbitrating"` around a delivered accepted challenger, then restart and assert reconciliation:

- promotes the challenger
- leaves the case in `completed`
- appends the existing arbitration promotion reliability event

**Step 4: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_task_reliability_reconciler.py::test_startup_reconciler_resolves_arbitrating_case_with_accepted_challenger -q
```

Expected: FAIL because explicit arbitrating-case surfacing is not implemented yet.

### Task 2: Implement explicit arbitrating case status

**Files:**
- Modify: `src/video_agent/application/delivery_case_service.py`

**Step 1: Add a focused helper for arbitrating challenger detection**

Treat a case as `arbitrating` only when:

- root delivery is already `delivered`
- active task differs from current selection
- active task is completed and delivered
- active task is an accepted challenger candidate

**Step 2: Use the helper in `_derive_case_status(...)`**

Keep existing `branching`, `repairing`, `running`, and `completed` semantics intact for all other states.

**Step 3: Run focused case-status test**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_delivery_case_orchestration.py::test_sync_case_marks_delivered_accepted_challenger_as_arbitrating -q
```

Expected: PASS

### Task 3: Verify startup/watchdog recovery still resolves arbitrating cases

**Files:**
- Modify: `tests/integration/test_task_reliability_reconciler.py` if assertions need tightening
- Reuse existing `src/video_agent/application/task_reliability_service.py` behavior unless a minimal fix is required

**Step 1: Run explicit reconcile test**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_task_reliability_reconciler.py::test_startup_reconciler_resolves_arbitrating_case_with_accepted_challenger -q
```

Expected: PASS

**Step 2: Run broader regression**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_delivery_case_orchestration.py tests/integration/test_task_reliability_reconciler.py tests/integration/test_workflow_completion.py tests/integration/test_delivery_canary.py tests/integration/test_multi_agent_workflow_service.py -q
```

Expected: PASS
