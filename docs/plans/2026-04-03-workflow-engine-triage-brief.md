# Workflow Engine Triage Brief

Date: 2026-04-03

## Objective

Map the main responsibility clusters still concentrated inside [workflow_engine.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/workflow_engine.py), estimate extraction risk, and choose the first narrow seam for follow-up refactor work.

## Responsibility Clusters

### 1. Delivery Resolution And Fallback Policy

Representative methods:

- `_allows_emergency_delivery`
- `_maybe_schedule_degraded_delivery`
- `_finalize_guaranteed_delivery`
- `_mark_delivery_failed`
- `_sync_root_delivery_resolution`
- `_build_degraded_style_hints`
- `_build_degraded_output_profile`
- `_build_degraded_delivery_feedback`

What this cluster owns today:

- deciding whether a failed attempt should stop, schedule degraded delivery, or fall back to guaranteed delivery
- applying the final delivered artifact onto the leaf task and root task
- synchronizing delivery-case state after delivery or failure
- encoding degraded-delivery prompt/profile policy

Coupling notes:

- directly touches `store`, `artifact_store`, `delivery_guarantee_service`, `delivery_case_service`, and `auto_repair_service.task_service`
- is currently reused by [case_reliability_service.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/case_reliability_service.py), which calls private `WorkflowEngine` methods during restart reconciliation

Extraction difficulty:

- Medium

Why:

- the dependency set is real but bounded
- the behavior surface is already coherent
- the current private-method reuse from `CaseReliabilityService` creates an obvious seam pressure

### 2. Repair And Failure Reconciliation

Representative methods and regions:

- failure-handling block around `auto_repair_service.maybe_schedule_repair(...)`
- `_record_repair_state`
- `_record_session_memory_outcome`
- `_record_agent_learning_outcome`

What this cluster owns today:

- deciding whether a failed run schedules repair
- projecting repair attempt metadata onto the root task
- writing learning/session-memory telemetry from task outcomes

Coupling notes:

- spans orchestration outcome handling plus telemetry sinks
- mixes product behavior with observability and learning capture

Extraction difficulty:

- Medium to High

Why:

- repair-state mutation is cohesive
- telemetry recording is cross-cutting and does not yet have a single obvious home
- splitting too early risks creating multiple tiny services with shared task-outcome dependencies

### 3. Challenger Creation, Arbitration, And Promotion

Representative methods:

- `_maybe_schedule_quality_challenger`
- `_record_auto_challenger_decision`
- `_maybe_auto_promote_challenger`
- `_record_auto_arbitration_decision`
- `_record_case_memory_branch_state`
- `_load_quality_scorecard_json`
- `_guarded_rollout_blockers`

What this cluster owns today:

- deciding when to create challenger branches
- building branch scoreboards and arbitration summaries
- automatically promoting an accepted challenger
- recording branch-state and arbitration events back into case memory and delivery-case state

Coupling notes:

- already depends on [branch_arbitration.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/branch_arbitration.py) for the pure scoreboard/arbitration logic
- still owns all side effects, governance checks, and event persistence around that logic
- interacts with `delivery_case_service`, `case_memory_service`, `auto_repair_service.task_service`, and rollout guards

Extraction difficulty:

- Medium to High

Why:

- the decision core is already partly extracted
- the remaining engine code is mostly side effects and policy wiring
- regressions here would affect accepted-challenger promotion and incumbent retention semantics

### 4. Runtime Lifecycle Projection And Logging

Representative methods:

- `_transition`
- `_log`
- `_resolve_render_profile`

What this cluster owns today:

- projecting task phase transitions into store/artifact/event sinks
- writing structured task logs
- translating request/runtime settings into render profile inputs

Coupling notes:

- foundational utility layer used across the whole engine
- not a good early extraction target because most engine flows depend on it

Extraction difficulty:

- High

Why:

- broad fan-out
- low standalone product value from extraction alone

## Existing Supporting Services

### [case_reliability_service.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/case_reliability_service.py)

Already owns:

- startup/watchdog reconciliation
- stale root detection
- orphaned branch handling
- restart-time case recovery

Gap:

- it still reaches back into private `WorkflowEngine` delivery-resolution and arbitration helpers to complete recovery work
- this is the strongest signal that delivery-resolution extraction would reduce real cross-service leakage immediately

### [runtime_service.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/runtime_service.py)

Already owns:

- runtime capabilities and rollout settings
- autonomy-guard inspection
- health/status reporting

Gap:

- it is not a home for orchestration side effects
- it should keep exposing settings and inspections, not absorb delivery or arbitration mutation logic

### [branch_arbitration.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/branch_arbitration.py)

Already owns:

- pure scoreboard construction
- pure arbitration recommendation logic

Gap:

- it intentionally stops before persistence, delivery-case mutation, and task acceptance side effects
- this means promotion wiring can later extract cleanly, but the current engine block is not yet the lowest-risk first move

## Recommended First Extraction Seam

Recommendation: accept the default recommendation and extract delivery resolution before branch promotion.

Why this seam first:

1. The delivery-resolution cluster is more self-contained than the branch-promotion side effects.
2. `CaseReliabilityService` already depends on this behavior through private engine methods, so extraction pays down an active architecture smell immediately.
3. [branch_arbitration.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/branch_arbitration.py) already captures the pure decision core for arbitration, so promotion wiring can wait one step without blocking understanding.
4. Delivery resolution directly governs user-visible success/failure semantics, degraded fallback, and restart recovery, so isolating it gives high risk reduction per unit of change.

Recommendation status:

- Accept `delivery resolution extraction before branch-promotion extraction`

## Likely Files For The First Seam

Create:

- `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/delivery_resolution_service.py`

Modify:

- [workflow_engine.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/workflow_engine.py)
- [case_reliability_service.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/case_reliability_service.py)
- `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/server/app.py`

Possible support touch points:

- `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/delivery_guarantee_service.py`
- `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/task_service.py`

## Suggested Move Order

1. Extract degraded-delivery decision and delivery-finalization helpers into a dedicated service with narrow dependencies.
2. Update `WorkflowEngine` to delegate failure-path delivery resolution to that service.
3. Update `CaseReliabilityService` to call the same service directly instead of invoking private engine methods.
4. Leave challenger creation, arbitration logging, and promotion wiring inside `WorkflowEngine` for the following refactor wave.

## Baseline Tests To Lock Before Refactor

Highest-value characterization set:

- [test_guaranteed_video_delivery.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_guaranteed_video_delivery.py)
- [test_task_reliability_reconciler.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_task_reliability_reconciler.py)
- [test_delivery_case_orchestration.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_delivery_case_orchestration.py)

Secondary regression coverage:

- [test_multi_agent_workflow_service.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_multi_agent_workflow_service.py)
- [test_http_task_reliability_api.py](/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_http_task_reliability_api.py)

## Deferral Notes

- Do not extract lifecycle logging first. It is too cross-cutting and would create broad churn without enough reduction in conceptual risk.
- Do not extract branch promotion first unless a new failure shows that arbitration side effects, not delivery recovery, are the current operational hotspot.
- Keep runtime settings and guard inspection in `RuntimeService`; that service should remain a capability/status provider rather than an orchestration mutation layer.
