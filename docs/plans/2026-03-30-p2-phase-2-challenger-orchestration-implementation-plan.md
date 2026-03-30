# P2 Phase 2 Challenger Orchestration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a minimal native challenger-branch and arbitration layer on top of the new `DeliveryCase` scaffold so completed roots can spawn a controlled challenger branch and accepted winners are persisted as orchestrator decisions.

**Architecture:** Reuse the current `revise_video_task` path for challenger branch creation, but upgrade the surrounding orchestration semantics. `DeliveryCase` becomes aware of branching-on-completed roots, `ReviewBundle` exposes branch and case state, and acceptance decisions are persisted through orchestrator runs plus root/case selection metadata.

**Tech Stack:** Python, Pydantic, SQLite, existing TaskService/MultiAgentWorkflowService/ReviewBundleBuilder, pytest

---

### Task 1: Add Failing Tests for Challenger Branching and Arbitration

**Files:**
- Modify: `tests/integration/test_multi_agent_workflow_service.py`
- Optionally modify: `tests/integration/test_http_multi_agent_workflow_api.py`

**Step 1: Add failing test for review bundle case state**

Assert `get_review_bundle(...)` includes:

- `case_status`
- `active_task_id`
- `selected_task_id`
- `branch_candidates`
- `recent_agent_runs`

for a newly created root task.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_multi_agent_workflow_service.py::test_workflow_service_get_review_bundle -q
```

**Step 3: Add failing test for challenger creation from a completed task**

Manually mark a root task completed, then apply a `revise` review decision. Assert:

- `reason == "challenger_created"`
- case status becomes `branching`
- `selected_task_id` remains the delivered root
- `active_task_id` becomes the challenger child
- an orchestrator run records `challenger_created`

**Step 4: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_multi_agent_workflow_service.py::test_workflow_service_creates_challenger_branch_for_completed_task -q
```

**Step 5: Add failing test for winner selection on accept**

Manually mark a root task completed and accepted-quality, apply an `accept` review decision, and assert:

- the task is marked `accepted_as_best`
- case `selected_task_id` points to the accepted task
- orchestrator run records `winner_selected`

**Step 6: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_multi_agent_workflow_service.py::test_workflow_service_accepts_completed_task_and_records_winner -q
```

### Task 2: Extend Review Bundle Models and Builder

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`

**Step 1: Add bundle fields for case/branch visibility**

Include:

- `case_status`
- `active_task_id`
- `selected_task_id`
- `branch_candidates`
- `recent_agent_runs`

**Step 2: Populate from `DeliveryCase` and `AgentRun` store records**

Keep it lightweight and read-only.

**Step 3: Run the bundle test**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_multi_agent_workflow_service.py::test_workflow_service_get_review_bundle -q
```

Expected: PASS for bundle visibility, others still fail.

### Task 3: Add Challenger Branch and Winner Selection Semantics

**Files:**
- Modify: `src/video_agent/application/delivery_case_service.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/multi_agent_workflow_service.py`

**Step 1: Record branch-spawn orchestration**

When a child is created from a completed parent:

- classify it as a challenger branch
- keep current root as selected winner until arbitration changes it
- set case status to `branching`
- append orchestrator run `challenger_created`

**Step 2: Record winner selection**

When review decision `accept` is allowed:

- call `accept_best_version(...)`
- persist orchestrator run `winner_selected`
- sync case selected task and case status

**Step 3: Re-run challenger and winner tests**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_multi_agent_workflow_service.py::test_workflow_service_creates_challenger_branch_for_completed_task tests/integration/test_multi_agent_workflow_service.py::test_workflow_service_accepts_completed_task_and_records_winner -q
```

Expected: PASS

### Task 4: Run Focused Verification

**Files:**
- No code changes

Run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_multi_agent_workflow_service.py \
  tests/integration/test_http_multi_agent_workflow_api.py \
  tests/integration/test_mcp_multi_agent_workflow_tools.py \
  tests/integration/test_delivery_case_orchestration.py -q
```

Then run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_guaranteed_video_delivery.py \
  tests/integration/test_task_reliability_reconciler.py \
  tests/integration/test_auto_repair_loop.py -q
```

Expected: PASS
