# P2 Auto Challenger Policy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically spawn one governed challenger branch when a root delivery succeeds technically but still fails the quality gate, while keeping the incumbent video selected until explicit arbitration accepts a challenger.

**Architecture:** Reuse the existing revision path, but introduce an internal challenger-specific branch marker so orchestrator-created challenger tasks are distinguishable from repair/degraded branches. `WorkflowEngine` should schedule a challenger only for delivered-but-needs-revision outcomes, and root delivery resolution must stop auto-promoting challenger completions until `accept_best_version(...)` explicitly selects them.

**Tech Stack:** Python, Pydantic, existing WorkflowEngine/TaskService/DeliveryCaseService, pytest

---

### Task 1: Add Failing Tests for Auto Challenger Scheduling

**Files:**
- Modify: `tests/integration/test_workflow_completion.py`
- Optionally modify: `tests/integration/test_delivery_case_orchestration.py`

**Step 1: Add failing test for delivered-but-needs-revision auto challenger**

Create a settings fixture with:

- `multi_agent_workflow_enabled=True`
- `quality_gate_min_score=0.95`
- `multi_agent_workflow_max_child_attempts=1`

Run one worker pass and assert:

- root task is `completed`
- root `delivery_status == "delivered"`
- root `quality_gate_status == "needs_revision"`
- a queued challenger child exists
- case status becomes `branching`
- case `selected_task_id` remains the root/incumbent
- an orchestrator run records `challenger_created`

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_workflow_completion.py::test_quality_rejected_delivery_auto_queues_challenger_branch -q
```

**Step 3: Add failing test for challenger completion not auto-replacing incumbent**

Using the same settings, run enough worker passes for the challenger child to complete too. Assert:

- challenger task completes
- root `resolved_task_id` still points to the original incumbent root
- case `selected_task_id` still points to the incumbent root
- root result still resolves to the incumbent artifact until explicit accept

**Step 4: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_workflow_completion.py::test_completed_challenger_does_not_replace_incumbent_until_accepted -q
```

### Task 2: Add Challenger Branch Identity and Internal Creation Path

**Files:**
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/multi_agent_workflow_service.py`

**Step 1: Add a lightweight branch marker**

Add a persisted `branch_kind` field to `VideoTask` with values like:

- `None` for incumbent/legacy tasks
- `"challenger"` for orchestrator-created challenger branches

No new SQLite column is required because the value already lives inside `task_json`.

**Step 2: Add an internal challenger creation helper**

Implement a `create_challenger_task(...)` path in `TaskService` that:

- requires a completed, delivered parent
- enforces existing lineage budgets
- creates a revision child
- marks `branch_kind="challenger"`
- persists it with challenger-specific event metadata

**Step 3: Route manual completed-root revise decisions through the challenger helper**

When `MultiAgentWorkflowService` receives `revise` for the currently selected completed task, use `create_challenger_task(...)` instead of the generic revise path.

**Step 4: Re-run the existing challenger review workflow tests**

Run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_multi_agent_workflow_service.py::test_workflow_service_creates_challenger_branch_for_completed_task \
  tests/integration/test_multi_agent_workflow_service.py::test_workflow_service_accepts_completed_task_and_records_winner -q
```

Expected: PASS

### Task 3: Add Workflow-Driven Auto Challenger Scheduling

**Files:**
- Modify: `src/video_agent/application/workflow_engine.py`
- Optionally modify: `src/video_agent/application/delivery_case_service.py`

**Step 1: Schedule an automatic challenger after low-quality delivery**

After a task is successfully delivered and quality-scored:

- if `quality_gate_status != "accepted"`
- and completion mode is not `degraded` / `emergency_fallback`
- and multi-agent workflow is enabled
- and branch budget remains

then create one challenger branch automatically.

**Step 2: Record an auto challenger decision event**

Append structured decision telemetry similar to auto repair:

- `created`
- `reason`
- `child_task_id`
- `quality_gate_status`
- `overall_score`

**Step 3: Prevent automatic incumbent replacement by challenger completion**

Update root-resolution logic so challenger branch completion does not overwrite `root.resolved_task_id` or case selection until `accept_best_version(...)` explicitly chooses it.

**Step 4: Re-run the new auto challenger tests**

Run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_workflow_completion.py::test_quality_rejected_delivery_auto_queues_challenger_branch \
  tests/integration/test_workflow_completion.py::test_completed_challenger_does_not_replace_incumbent_until_accepted -q
```

Expected: PASS

### Task 4: Run Focused Verification

**Files:**
- No code changes

Run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_multi_agent_workflow_service.py \
  tests/integration/test_delivery_case_orchestration.py -q
```

Then run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_guaranteed_video_delivery.py \
  tests/integration/test_task_reliability_reconciler.py \
  tests/integration/test_auto_repair_loop.py \
  tests/integration/test_http_multi_agent_workflow_api.py \
  tests/integration/test_mcp_multi_agent_workflow_tools.py -q
```

Expected: PASS
