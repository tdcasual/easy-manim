# P2 Phase 1 Native Case Scaffold Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the first native multi-agent orchestration scaffold by persisting `DeliveryCase` and `AgentRun` records around the existing single-branch workflow without changing current delivery behavior.

**Architecture:** Introduce additive SQLite tables plus lightweight domain/service helpers that mirror the current root-task lifecycle. Root task creation creates a `DeliveryCase`; workflow milestones append role-scoped `AgentRun` records for orchestrator, planner, generator, reviewer, and repairer; root delivery metadata remains the canonical delivery contract and is synced into the case record.

**Tech Stack:** Python, Pydantic, SQLite migrations, existing TaskService/WorkflowEngine, pytest

---

### Task 1: Add Failing Integration Tests for Native Case Persistence

**Files:**
- Create: `tests/integration/test_delivery_case_orchestration.py`
- Read: `tests/integration/test_workflow_completion.py`
- Read: `tests/integration/test_guaranteed_video_delivery.py`

**Step 1: Write the failing test for root task case creation**

Assert that creating a root task automatically creates one `DeliveryCase` with:

- `case_id == root_task_id`
- `root_task_id == task_id`
- `delivery_status == "pending"`
- `selected_task_id is None`

Also assert one orchestrator `AgentRun` exists with a case-created decision payload.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_delivery_case_orchestration.py::test_root_task_creation_creates_delivery_case_and_orchestrator_run -q
```

Expected: FAIL because case/run models and persistence do not exist yet.

**Step 3: Write the failing test for successful workflow role runs**

Assert that after one successful worker pass:

- the case is `completed`
- `delivery_status == "delivered"`
- `selected_task_id == root_task_id`
- planner/generator/reviewer runs exist with completed status

**Step 4: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_delivery_case_orchestration.py::test_successful_workflow_syncs_case_and_role_runs -q
```

**Step 5: Write the failing test for repairer persistence on auto-repair scheduling**

Use a failed-render pipeline with auto repair enabled. Assert that after one worker pass:

- the case is still pending/open
- a repairer run exists
- the repairer decision payload includes `child_task_id`

**Step 6: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_delivery_case_orchestration.py::test_failed_root_with_auto_repair_records_repairer_run -q
```

### Task 2: Add Schema and Store Support

**Files:**
- Create: `src/video_agent/domain/delivery_case_models.py`
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`

**Step 1: Add delivery-case domain models**

Create:

- `DeliveryCase`
- `AgentRun`

Include canonical JSON-friendly fields for status, case/root/task references, decision payloads, and timestamps.

**Step 2: Add SQLite migration**

Create additive tables:

- `delivery_cases`
- `agent_runs`

Store canonical JSON blobs plus selected query columns.

**Step 3: Add store methods**

Add at minimum:

- `upsert_delivery_case(...)`
- `get_delivery_case(...)`
- `get_delivery_case_by_root_task_id(...)`
- `create_agent_run(...)`
- `list_agent_runs(...)`

**Step 4: Run the new tests**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_delivery_case_orchestration.py -q
```

Expected: still FAIL because workflow/task wiring has not been added.

### Task 3: Add DeliveryCase Service and Root Task Wiring

**Files:**
- Create: `src/video_agent/application/delivery_case_service.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/server/app.py`

**Step 1: Add a lightweight synchronization service**

Responsibilities:

- ensure a root case exists
- sync case state from root/leaf delivery metadata
- append orchestrator/planner/generator/reviewer/repairer runs

**Step 2: Wire root-task creation**

When `TaskService.create_video_task(...)` persists a root task:

- create the delivery case
- append an orchestrator case-created run

**Step 3: Wire child-task creation**

When child tasks are created:

- keep them attached to the root case
- update case active task pointer if needed

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_delivery_case_orchestration.py::test_root_task_creation_creates_delivery_case_and_orchestrator_run -q
```

Expected: PASS for the root creation test.

### Task 4: Wire Workflow Milestones to Role Runs

**Files:**
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/auto_repair_service.py`
- Test: `tests/integration/test_delivery_case_orchestration.py`

**Step 1: Record planner run**

After scene spec/scene plan generation, append a completed planner run.

**Step 2: Record generator run**

Record success/failure outcomes for generation/render path.

**Step 3: Record reviewer run**

After validation or failure-context generation, append a reviewer run capturing validation summary, quality state, failure contract, and recovery action.

**Step 4: Record repairer run**

When auto repair is evaluated, append a repairer run whether it created a child or stopped.

**Step 5: Keep case state synced**

On success/failure/fallback/root-resolution changes, sync the `DeliveryCase` record from current root metadata.

**Step 6: Re-run the orchestration tests**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_delivery_case_orchestration.py -q
```

Expected: PASS

### Task 5: Run Regression Verification

**Files:**
- No code changes

Run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_delivery_case_orchestration.py \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_guaranteed_video_delivery.py \
  tests/integration/test_task_reliability_reconciler.py \
  tests/integration/test_multi_agent_workflow_service.py -q
```

Then run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_auto_repair_loop.py \
  tests/integration/test_runtime_status_tool.py \
  tests/integration/test_http_multi_agent_workflow_api.py \
  tests/integration/test_mcp_multi_agent_workflow_tools.py -q
```

Expected: PASS
