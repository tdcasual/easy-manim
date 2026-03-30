# P0 P1 Reliability Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise the current video agent from "usually keeps trying until it delivers" to "recovers across restarts, validates fallback artifacts atomically, detects unhealthy runtime early, and exposes delivery SLO signals clearly enough to operate with confidence."

**Architecture:** Add one reliability coordination layer above the current task lineage model instead of rewriting the workflow engine. Reuse existing root-level delivery metadata (`delivery_status`, `resolved_task_id`, `completion_mode`, `delivery_stop_reason`) and extend it with startup reconciliation, stale-task watchdog handling, atomic emergency artifact delivery, and runtime/canary observability so failures become resumable and diagnosable rather than terminal or silent.

**Tech Stack:** Python, FastAPI, SQLite, pytest, ffmpeg, ffprobe, existing worker loop / runtime status / metrics stack

---

## Scope

### P0

1. Startup delivery reconciler
2. Atomic emergency video writing with playable validation
3. Preflight hard runtime health checks
4. Stuck-task watchdog
5. Crash / restart recovery tests

### P1

1. Real-environment canary command + API visibility
2. Delivery SLO summary + stop-reason observability

### P2

Design only after P0/P1 code is complete and freshly verified.

## Pre-flight

Read these files before implementation:

- `src/video_agent/server/app.py`
- `src/video_agent/worker/worker_loop.py`
- `src/video_agent/application/workflow_engine.py`
- `src/video_agent/application/task_service.py`
- `src/video_agent/application/runtime_service.py`
- `src/video_agent/application/delivery_guarantee_service.py`
- `src/video_agent/adapters/rendering/emergency_video_writer.py`
- `src/video_agent/adapters/storage/artifact_store.py`
- `src/video_agent/adapters/storage/sqlite_store.py`
- `src/video_agent/server/http_api.py`
- `src/video_agent/server/mcp_tools.py`
- `tests/integration/test_guaranteed_video_delivery.py`
- `tests/integration/test_runtime_status_tool.py`
- `tests/integration/test_capability_rollout_profiles.py`
- `tests/integration/test_http_task_reliability_api.py`
- `tests/integration/test_mcp_task_reliability_tools.py`

## Recommended Task Order

1. Atomic fallback writing
2. Runtime hard health checks
3. Reconciler + watchdog
4. Crash/restart tests
5. Canary + SLO visibility
6. P2 design doc

### Task 1: Add Failing Tests for Atomic Emergency Delivery

**Files:**
- Modify: `tests/integration/test_guaranteed_video_delivery.py`
- Test: `tests/integration/test_guaranteed_video_delivery.py`

**Step 1: Write the failing test for invalid fallback artifact rejection**

Add a test where:

- emergency delivery is enabled,
- the fallback writer first creates an invalid file or leaves a truncated file,
- validation fails,
- root task ends with `delivery_status == "failed"` and `delivery_stop_reason == "invalid_emergency_video"` or equivalent,
- no ready result is returned.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_guaranteed_video_delivery.py -q
```

Expected: FAIL because fallback output is not written atomically or re-validated.

**Step 3: Write the failing test for temp-file atomic promotion**

Add a test that asserts the final artifact path only appears after successful validation and that temp files are cleaned up.

**Step 4: Run test to verify it fails**

Run the same command.

### Task 2: Implement Atomic Emergency Video Writer

**Files:**
- Modify: `src/video_agent/adapters/rendering/emergency_video_writer.py`
- Modify: `src/video_agent/application/delivery_guarantee_service.py`
- Modify: `src/video_agent/server/app.py`
- Optionally modify: `src/video_agent/validation/hard_validation.py`
- Test: `tests/integration/test_guaranteed_video_delivery.py`

**Step 1: Introduce validated temp-file writing**

Write the emergency video to a temp path inside the target artifact directory.

**Step 2: Validate playable output before publish**

Use `HardValidator` or equivalent ffprobe-based validation to reject zero-duration / invalid artifacts.

**Step 3: Atomically replace final artifact**

Promote the temp file to the canonical final path only after validation succeeds.

**Step 4: Re-run tests**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_guaranteed_video_delivery.py -q
```

Expected: PASS for the new fallback tests.

### Task 3: Add Failing Tests for Runtime Hard Health Checks

**Files:**
- Modify: `tests/integration/test_runtime_status_tool.py`
- Modify: `tests/integration/test_http_task_reliability_api.py`
- Modify: `tests/integration/test_mcp_task_reliability_tools.py`

**Step 1: Write failing tests for runtime task-processing readiness**

Cover at least:

- artifact root not writable,
- database path not writable or parent missing,
- missing `ffprobe` / `manim`,
- unhealthy state exposed as structured runtime payload, not only implicit failures.

**Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_runtime_status_tool.py \
  tests/integration/test_http_task_reliability_api.py \
  tests/integration/test_mcp_task_reliability_tools.py -q
```

### Task 4: Implement Runtime Hard Health Checks

**Files:**
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Test: `tests/integration/test_runtime_status_tool.py`

**Step 1: Add task-processing readiness section**

Expose a structured readiness object such as:

- `task_processing.ready`
- `task_processing.reasons`
- `task_processing.checked_at`

**Step 2: Check hard prerequisites**

At minimum:

- `artifact_root` exists or can be created,
- `artifact_root` is writable,
- database directory is writable,
- core binaries (`manim`, `ffprobe`) are available.

**Step 3: Wire readiness into HTTP and MCP surfaces**

Keep compatibility with existing runtime payloads.

**Step 4: Re-run runtime tests**

Run the command from Task 3 again and verify PASS.

### Task 5: Add Failing Tests for Startup Reconciliation and Watchdog

**Files:**
- Create or modify: `tests/integration/test_task_reliability_reconciler.py`
- Modify: `tests/integration/test_guaranteed_video_delivery.py`
- Modify: `tests/integration/test_workflow_completion.py`

**Step 1: Write failing startup recovery test**

Scenario:

- root task is left `delivery_status="pending"` after a failed child,
- app is recreated,
- reconciler resumes lineage and root eventually resolves or gets a deterministic stop reason.

**Step 2: Write failing stale queued/running watchdog test**

Scenario:

- task remains `queued` or `running` beyond a configured threshold,
- watchdog marks/requeues/escalates it instead of leaving it indefinitely pending.

**Step 3: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_task_reliability_reconciler.py \
  tests/integration/test_guaranteed_video_delivery.py \
  tests/integration/test_workflow_completion.py -q
```

### Task 6: Implement Reconciler and Watchdog

**Files:**
- Create: `src/video_agent/application/task_reliability_service.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/worker/worker_loop.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/application/task_service.py`
- Optionally modify: `src/video_agent/application/workflow_engine.py`
- Test: `tests/integration/test_task_reliability_reconciler.py`

**Step 1: Add store queries for recoverable root lineages**

Need queries for:

- root tasks with `delivery_status = 'pending'`,
- stale `queued` / `running` tasks,
- root lineages with no resolved delivered descendant.

**Step 2: Add reliability service**

Responsibilities:

- startup reconciliation,
- stale task watchdog,
- root lineage stop-reason repair when recovery cannot continue,
- metrics counters for recovered / failed reconciliations.

**Step 3: Trigger reconciliation during app startup**

Call it from `create_app_context(...)` after services are built.

**Step 4: Trigger watchdog during worker polling**

Run lightweight stale-task sweep before or alongside claim/requeue logic.

**Step 5: Re-run tests**

Run the command from Task 5 again and verify PASS.

### Task 7: Add Failing Tests for Delivery SLO Summary

**Files:**
- Modify: `tests/integration/test_runtime_status_tool.py`
- Modify: `tests/integration/test_http_eval_api.py` if needed

**Step 1: Write failing tests for summary metrics**

Expose a compact summary such as:

- `delivery_summary.total_roots`
- `delivery_summary.delivered_roots`
- `delivery_summary.failed_roots`
- `delivery_summary.delivery_rate`
- `delivery_summary.emergency_fallback_rate`
- `delivery_summary.top_stop_reasons`

**Step 2: Run tests to verify failure**

```bash
PYTHONPATH=src pytest tests/integration/test_runtime_status_tool.py -q
```

### Task 8: Implement Delivery SLO Summary

**Files:**
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/server/mcp_tools.py`

**Step 1: Add aggregate root-task query helpers**

Compute summary over root tasks only.

**Step 2: Include delivery SLO summary in runtime status**

Keep it read-only and cheap.

**Step 3: Re-run tests**

```bash
PYTHONPATH=src pytest tests/integration/test_runtime_status_tool.py -q
```

### Task 9: Add Real-Environment Canary

**Files:**
- Create: `src/video_agent/application/delivery_canary_service.py`
- Create: `src/video_agent/eval/canary.py` or similar CLI
- Create: `tests/integration/test_delivery_canary.py`
- Optionally modify: `src/video_agent/server/http_api.py`

**Step 1: Write failing canary test**

The canary should:

- create one minimal render task,
- run the worker,
- verify delivered artifact availability and basic metadata,
- return structured result with duration and completion mode.

**Step 2: Implement minimal canary command**

Keep it local and deterministic; do not depend on external scheduler infrastructure.

**Step 3: Re-run canary tests**

```bash
PYTHONPATH=src pytest tests/integration/test_delivery_canary.py -q
```

### Task 10: Run Focused Verification Suite

**Files:**
- No code changes

Run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_guaranteed_video_delivery.py \
  tests/integration/test_task_reliability_reconciler.py \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_runtime_status_tool.py \
  tests/integration/test_http_task_reliability_api.py \
  tests/integration/test_mcp_task_reliability_tools.py \
  tests/integration/test_delivery_canary.py -q
```

Expected: PASS

### Task 11: Run Broader Reliability Regression

Run:

```bash
PYTHONPATH=src pytest \
  tests/integration/test_auto_repair_loop.py \
  tests/integration/test_agent_learning_capture.py \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_capability_rollout_profiles.py \
  tests/integration/test_agent_profile_auto_apply.py \
  tests/integration/test_runtime_status_tool.py \
  tests/integration/test_multi_agent_workflow_service.py \
  tests/integration/test_http_multi_agent_workflow_api.py \
  tests/integration/test_mcp_multi_agent_workflow_tools.py -q
```

Expected: PASS

### Task 12: Write P2 Design After P0/P1 Are Green

**Files:**
- Create: `docs/plans/2026-03-30-p2-native-multi-agent-design.md`

**Deliverable:**

Design only, no implementation yet. Cover:

- native collaborative multi-agent ownership model,
- planner/reviewer/repairer specialization,
- shared memory and arbitration,
- stronger autonomous rollout governance,
- migration path from current supervised workflow.
