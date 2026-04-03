# First Orchestration Extraction Plan

Date: 2026-04-03

## Decision

Extract delivery resolution first.

This plan intentionally does **not** start with branch promotion.

## Why Delivery Resolution Wins

### Delivery Resolution Seam

Strengths:

- concentrated around a small set of `workflow_engine.py` methods
- directly reused by restart reconciliation today through private engine calls
- controls user-visible outcomes: delivered, degraded, emergency fallback, failed
- has a bounded dependency set: store, artifact store, delivery guarantee service, delivery case sync, and degraded child-task creation

Risks:

- correctness matters because root-task snapshots and lineage recovery depend on it
- the same logic is exercised both during live execution and during reliability reconciliation

### Branch Promotion Seam

Strengths:

- pure scoreboard/arbitration logic already lives in [branch_arbitration.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/branch_arbitration.py)

Risks:

- remaining engine code is mostly side effects and governance wiring
- interacts with accepted challenger promotion, case memory recording, rollout guards, and delivery-case state
- lower-value as a first cut because the current architecture smell is less immediate than the delivery-reconciliation private-method leakage

Conclusion:

- keep branch promotion for the following wave
- extract delivery resolution now

## Exact Files

Create:

- `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/delivery_resolution_service.py`

Modify:

- [workflow_engine.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/workflow_engine.py)
- [case_reliability_service.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/case_reliability_service.py)
- `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/server/app.py`

Characterization-first test files:

- [test_guaranteed_video_delivery.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_guaranteed_video_delivery.py)
- [test_task_reliability_reconciler.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_task_reliability_reconciler.py)
- [test_delivery_case_orchestration.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_delivery_case_orchestration.py)
- [test_http_task_reliability_api.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_http_task_reliability_api.py)

## Methods To Move First

Move into `DeliveryResolutionService` first:

- `_allows_emergency_delivery`
- `_maybe_schedule_degraded_delivery`
- `_finalize_guaranteed_delivery`
- `_mark_delivery_failed`
- `_sync_root_delivery_resolution`
- `_build_degraded_style_hints`
- `_build_degraded_output_profile`
- `_build_degraded_delivery_feedback`

Leave in `WorkflowEngine` for the first pass:

- the surrounding failure-review flow that decides whether repair already handled the case
- `_record_repair_state`
- `_record_agent_learning_outcome`
- challenger creation and promotion
- arbitration recording
- lifecycle logging and phase transitions

## Proposed Service Shape

`DeliveryResolutionService` should own narrow, side-effectful delivery state mutation.

Suggested responsibilities:

- decide whether degraded delivery can be scheduled
- finalize a delivered artifact onto the leaf task and root task
- mark leaf/root delivery as failed with the same stop reason
- sync root delivery state after a descendant resolves delivery

Suggested constructor dependencies:

- `store`
- `artifact_store`
- `delivery_case_service`
- `delivery_guarantee_service`
- `task_service` or a narrow callback for degraded child creation
- `runtime_settings` or a tiny policy object exposing delivery-related flags

## Execution Sequence

### Step 1. Lock Behavior

Before moving code, tighten or confirm characterization coverage for:

- degraded child creation before emergency fallback
- root delivery sync to delivered descendant
- restart reconciliation after delivered degraded child
- failure propagation when delivery guarantee is disabled
- failure propagation when delivery guarantee throws

### Step 2. Introduce The Service Without Rewiring All Call Sites

- create `delivery_resolution_service.py`
- copy the target methods with minimal signature cleanup
- keep `WorkflowEngine` delegating to the new service

### Step 3. Remove Private Cross-Service Reach-Through

- update `CaseReliabilityService` to call `DeliveryResolutionService` directly instead of invoking `WorkflowEngine` private helpers

### Step 4. Re-run Characterization Tests

- verify both live worker flows and restart reconciliation still pass before any cleanup refactor

## What Intentionally Stays In `workflow_engine.py`

- decision sequencing between validation failure, repair scheduling, and delivery fallback
- workflow-level orchestration logging
- challenger scheduling and promotion policy
- arbitration event persistence
- runtime-phase transitions

This keeps the first extraction bounded to delivery state mutation rather than turning into a broad engine rewrite.

## Stop Conditions

Pause the extraction if any of these happen:

- `CaseReliabilityService` still needs engine-private state after service introduction
- characterization tests reveal hidden coupling between delivery resolution and branch arbitration
- the new service starts absorbing review/repair sequencing instead of just delivery state mutation

## Expected Outcome

After this extraction:

- delivery resolution becomes a first-class seam instead of an engine-private cluster
- restart reconciliation no longer needs to reach through `WorkflowEngine` internals
- branch-promotion extraction can follow later from a cleaner baseline
