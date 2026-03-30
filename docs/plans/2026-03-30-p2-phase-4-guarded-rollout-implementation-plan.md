# P2 Phase 4 Guarded Rollout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add guarded autonomy on top of the existing native multi-agent orchestration so the system can keep current supervised behavior, expose explicit governance controls, and automatically back off when canary or historical branch signals say autonomy is unsafe.

**Architecture:** Keep the current root-task delivery contract intact. Layer new governance through `Settings`, `RuntimeService`, and `WorkflowEngine` rather than introducing a second orchestrator. Compute autonomy guard decisions from stored runtime signals (`delivery_canary`, delivery summary, challenger/arbitration history), then let workflow helpers return deterministic blocked decisions instead of creating branches or promoting challengers.

**Tech Stack:** Python, Pydantic, SQLite, pytest, React/Vitest

---

### Task 1: Add explicit governance flags without changing current supervised behavior

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `tests/unit/test_settings.py`
- Modify: `tests/integration/test_capability_rollout_profiles.py`
- Modify: `tests/integration/test_runtime_status_tool.py`
- Modify: `tests/integration/test_workflow_completion.py`

**Steps:**

1. Add explicit settings and env support for:
   - `multi_agent_workflow_auto_challenger_enabled`
   - `multi_agent_workflow_auto_arbitration_enabled`
2. Keep existing rollout defaults unchanged for current profiles so `supervised` still behaves like today unless explicitly overridden.
3. Expose both effective flags in runtime status.
4. Gate auto challenger creation and auto challenger promotion inside `WorkflowEngine`.
5. Verify focused tests and then the surrounding multi-agent/reliability suites.

### Task 2: Add guarded rollout profile and runtime autonomy guard

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `tests/integration/test_capability_rollout_profiles.py`
- Modify: `tests/integration/test_runtime_status_tool.py`
- Modify: `tests/integration/test_workflow_completion.py`

**Steps:**

1. Add `autonomy-guarded` rollout profile.
2. Add guarded rollout settings for:
   - `multi_agent_workflow_guarded_rollout_enabled`
   - `multi_agent_workflow_guarded_min_delivery_rate`
   - `multi_agent_workflow_guarded_max_emergency_fallback_rate`
3. Add `autonomy_guard` runtime status derived from:
   - delivery canary health
   - delivery rate
   - emergency fallback rate
4. Block auto challenger and auto arbitration when guard reasons exist.
5. Add focused tests for:
   - missing/unhealthy canary
   - healthy canary + healthy SLO path
   - delivery-rate regression blocking arbitration

### Task 3: Expand delivery summary into multi-agent SLO telemetry

**Files:**
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `tests/integration/test_runtime_status_tool.py`

**Steps:**

1. Extend runtime delivery summary with:
   - `completion_modes`
   - `challenger_branches_completed`
   - `challenger_branches_rejected`
   - `branch_rejection_rate`
   - `arbitration_attempts`
   - `arbitration_successes`
   - `arbitration_success_rate`
   - `repair_loop_saturation_count`
   - `repair_loop_saturation_rate`
2. Base challenger rejection only on cases with explicit branch outcomes so the current candidate does not self-poison the metrics.
3. Add focused runtime-status tests covering mixed primary/repaired branches and repair saturation.

### Task 4: Add rollback-style guarded backoff on historical branch rejection

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `tests/integration/test_runtime_status_tool.py`
- Modify: `tests/integration/test_workflow_completion.py`

**Steps:**

1. Add `multi_agent_workflow_guarded_max_branch_rejection_rate`.
2. Feed historical branch rejection rate into the runtime autonomy guard.
3. Block new autonomous challenger creation when historical branch rejection exceeds the configured threshold.
4. Verify with focused runtime/workflow tests that:
   - explicit historical rejection blocks new autonomy
   - healthy current canary + no historical rejection still allows auto promotion

### Task 5: Surface guarded autonomy in Profile UI

**Files:**
- Modify: `ui/src/lib/runtimeApi.ts`
- Modify: `ui/src/features/profile/ProfilePageV2.tsx`
- Modify: `ui/src/features/profile/ProfilePageV2.test.tsx`

**Steps:**

1. Extend the runtime API type with `autonomy_guard`.
2. Show whether guarded autonomy is `allowed` or `blocked`.
3. Surface the current block reasons so operators can understand why the system backed off.
4. Verify with focused Vitest coverage.

### Verification

Run:

```bash
PYTHONPATH=src pytest tests/unit/test_settings.py tests/integration/test_capability_rollout_profiles.py tests/integration/test_runtime_status_tool.py tests/integration/test_delivery_canary.py tests/integration/test_review_bundle_builder.py tests/integration/test_workflow_completion.py tests/integration/test_multi_agent_workflow_service.py tests/integration/test_task_reliability_reconciler.py tests/integration/test_guaranteed_video_delivery.py tests/integration/test_auto_repair_loop.py tests/integration/test_http_multi_agent_workflow_api.py tests/integration/test_mcp_multi_agent_workflow_tools.py -q
```

Run:

```bash
npm test -- src/features/profile/ProfilePageV2.test.tsx
```

Expected: PASS
