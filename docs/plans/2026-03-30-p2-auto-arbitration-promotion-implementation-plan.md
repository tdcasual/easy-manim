# P2 Auto Arbitration Promotion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically promote a completed accepted challenger when stored branch evidence clearly recommends it, while preserving incumbent selection in all other cases.

**Architecture:** Reuse the existing persisted `branch_scoreboard` and `arbitration_summary` logic rather than adding a new runtime arbitrator. The `WorkflowEngine` should evaluate challenger completion with deterministic stored inputs, record an orchestrator arbitration decision, and only then call the existing `accept_best_version(...)` path to finalize winner selection.

**Tech Stack:** Python, Pydantic, SQLite, existing `WorkflowEngine`/`TaskService`/`DeliveryCaseService`, pytest

---

### Task 1: Add failing workflow tests for automatic challenger promotion

**Files:**
- Modify: `tests/integration/test_workflow_completion.py`

**Step 1: Write the failing positive test**

Add a test where:

- root delivery completes with `quality_gate_status == "needs_revision"`
- auto challenger is queued
- before processing challenger, lower the runtime quality threshold enough for challenger completion to become `accepted`
- after challenger finishes, assert:
  - root `resolved_task_id` switches to challenger
  - case `selected_task_id` switches to challenger
  - the returned video result points at challenger artifacts
  - an orchestrator run records automatic arbitration with `recommended_action == "promote_challenger"`
  - a later orchestrator run records `winner_selected`

**Step 2: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_workflow_completion.py::test_completed_accepted_challenger_auto_promotes_to_winner -q
```

Expected: FAIL because no automatic arbitration promotion exists yet.

**Step 3: Write the failing negative-boundary test if needed**

If the positive test alone does not pin down the boundary, keep the existing incumbent-guard test as the negative case:

- accepted challenger missing -> incumbent stays selected

**Step 4: Re-run the focused challenger tests**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_workflow_completion.py::test_quality_rejected_delivery_auto_queues_challenger_branch tests/integration/test_workflow_completion.py::test_completed_challenger_does_not_replace_incumbent_until_accepted tests/integration/test_workflow_completion.py::test_completed_accepted_challenger_auto_promotes_to_winner -q
```

Expected: new test FAILS, guard tests still PASS.

### Task 2: Implement deterministic automatic arbitration in workflow engine

**Files:**
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/delivery_case_service.py`
- Reuse: `src/video_agent/application/branch_arbitration.py`

**Step 1: Add a workflow-engine helper for challenger auto arbitration**

Implement a helper that:

- only evaluates completed delivered challenger branches
- builds a branch scoreboard from stored lineage + scorecards
- computes arbitration summary using existing deterministic logic
- decides whether current challenger should be auto-promoted

**Step 2: Record arbitration evaluation**

Persist an orchestrator audit record with:

- `action: "auto_arbitration_evaluated"`
- `recommended_task_id`
- `recommended_action`
- `reason`
- `selected_task_id`

**Step 3: Auto-select challenger only on explicit promote recommendation**

If arbitration recommends `promote_challenger` for the currently completed branch:

- call `accept_best_version(...)`
- let the existing winner-selection path update root/case state and append `winner_selected`

Otherwise, keep incumbent unchanged.

**Step 4: Run focused workflow tests**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_workflow_completion.py::test_completed_challenger_does_not_replace_incumbent_until_accepted tests/integration/test_workflow_completion.py::test_completed_accepted_challenger_auto_promotes_to_winner -q
```

Expected: PASS

### Task 3: Run verification

**Files:**
- No code changes

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_workflow_completion.py tests/integration/test_multi_agent_workflow_service.py tests/integration/test_delivery_case_orchestration.py tests/integration/test_http_multi_agent_workflow_api.py tests/integration/test_mcp_multi_agent_workflow_tools.py -q
```

Then run:

```bash
PYTHONPATH=src pytest tests/integration/test_guaranteed_video_delivery.py tests/integration/test_task_reliability_reconciler.py tests/integration/test_auto_repair_loop.py -q
```

Expected: PASS
