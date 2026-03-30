# Guaranteed Video Delivery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure the agent keeps degrading and retrying until it delivers at least one playable video artifact instead of stopping at the first terminal failure.

**Architecture:** Keep the existing lineage-based task model, but add a lineage-level delivery outcome that can resolve to a successful descendant or a deterministic emergency fallback artifact. Reuse the current `failure_contract -> recovery_plan -> auto_repair` path for the first recovery layer, then add bounded degradation tiers and a final `ffmpeg`-based emergency video writer so the system can still deliver a valid MP4 when normal generation paths fail.

**Tech Stack:** Python, FastAPI, SQLite, pytest, React, TypeScript, Vitest, ffmpeg, ffprobe

---

## Assumptions

- The delivery guarantee means "guarantee a playable video file," not "guarantee the original prompt is fully satisfied."
- This guarantee is only realistic when the runtime is healthy enough to run at least `ffmpeg` and `ffprobe`.
- Quality may degrade across attempts, and the final artifact may be marked as `degraded` or `emergency_fallback`.
- The current dedicated worktree is `/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/agent-capability-gap-closure`.

## Approach Options

### Option A: Infinite blind retries

Keep retrying the same or lightly edited prompt until something passes.

Why not:

- wasteful,
- unbounded,
- likely to loop on structural failures,
- still cannot guarantee a video.

### Option B: Bounded degradation with deterministic final fallback

Use normal generation first, then targeted repair, then simplified generation, then template generation, then a deterministic emergency MP4 writer.

Why this is recommended:

- preserves current architecture,
- keeps costs bounded,
- gives us explicit observability per degradation tier,
- can genuinely guarantee an artifact when the runtime is healthy.

### Option C: Human escalation after bounded retries

Stop after bounded retries and require a human to intervene.

Why not as the main path:

- useful as a safety rail,
- but it does not meet the user's requirement of "don't fail-stop without a video."

## Recommended Direction

Implement Option B.

Keep attempt-level `status` semantics intact for individual task nodes, but add lineage-level delivery fields so:

- the root request can remain "delivery pending" while child attempts continue,
- the root result endpoint can resolve to the best successful descendant,
- the UI can say "delivered via degraded fallback" instead of "failed."

Do not add new coarse `TaskStatus` enum values in this phase. Keep `completed/failed/cancelled` for attempts, and introduce separate delivery metadata for lineage outcome.

## Pre-flight

Read these files before implementation:

- `src/video_agent/domain/enums.py`
- `src/video_agent/domain/models.py`
- `src/video_agent/domain/recovery_models.py`
- `src/video_agent/config.py`
- `src/video_agent/application/task_service.py`
- `src/video_agent/application/workflow_engine.py`
- `src/video_agent/application/auto_repair_service.py`
- `src/video_agent/application/recovery_policy_service.py`
- `src/video_agent/application/failure_contract.py`
- `src/video_agent/adapters/storage/sqlite_schema.py`
- `src/video_agent/adapters/storage/sqlite_store.py`
- `src/video_agent/adapters/storage/artifact_store.py`
- `src/video_agent/adapters/rendering/manim_runner.py`
- `src/video_agent/adapters/rendering/frame_extractor.py`
- `src/video_agent/server/http_api.py`
- `src/video_agent/server/mcp_tools.py`
- `ui/src/lib/tasksApi.ts`
- `ui/src/features/tasks/TaskDetailPageV2.tsx`
- `tests/integration/test_auto_repair_loop.py`
- `tests/integration/test_auto_repair_status.py`
- `tests/integration/test_workflow_completion.py`
- `tests/integration/test_http_task_api.py`
- `tests/integration/test_mcp_tools.py`

## Target Outcome

After implementation, the desired runtime behavior is:

1. Primary generation runs as today.
2. If it fails and the issue is retryable, `AutoRepairService` can still create a targeted repair child.
3. If repair is exhausted or inapplicable, the system creates a degraded generation child with reduced capability demands.
4. If degraded generation still cannot deliver, the system emits a deterministic emergency MP4 for the root request.
5. Root task reads and result APIs resolve to the delivered descendant or fallback artifact, with metadata that clearly says how degraded the result is.

## Delivery Metadata Shape

Add lineage-level delivery metadata with minimal surface area:

- `delivery_status`: `pending | delivered | failed`
- `resolved_task_id`: task id that produced the final artifact when available
- `completion_mode`: `primary | repaired | degraded | emergency_fallback`
- `delivery_tier`: `primary | guided_generate | template_generate | emergency`
- `delivery_stop_reason`: nullable string when the guarantee truly cannot complete

Persist this on the root task so API and UI do not need to reconstruct everything from events each time.

### Task 1: Add Failing Tests for Guaranteed Delivery Lifecycle

**Files:**
- Create: `tests/integration/test_guaranteed_video_delivery.py`
- Modify: `tests/integration/test_http_task_api.py`
- Modify: `tests/integration/test_mcp_tools.py`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.test.tsx`

**Step 1: Write the failing integration test for degraded child delivery**

Create `tests/integration/test_guaranteed_video_delivery.py` with a test that:

- boots settings with:
  - `capability_rollout_profile="autonomy-lite"`
  - `auto_repair_enabled=True`
  - new guarantee flag enabled
  - bounded degradation attempts enabled
- uses a fake generation/render path where:
  - primary task fails,
  - targeted repair also fails,
  - a degraded child succeeds
- asserts:
  - root snapshot reports `delivery_status == "delivered"`
  - root snapshot reports `completion_mode == "degraded"`
  - root snapshot reports `resolved_task_id` equal to the successful child
  - `get_video_result(root_task_id)` returns `ready is True`
  - returned video points at the descendant artifact, not the failed root attempt

**Step 2: Write the failing integration test for emergency fallback delivery**

In the same file, add a test where:

- primary generation fails,
- auto-repair is not applicable or budget-exhausted,
- degraded generation also fails,
- emergency video writing succeeds,
- root snapshot reports:
  - `delivery_status == "delivered"`
  - `completion_mode == "emergency_fallback"`
  - `delivery_tier == "emergency"`
- the final video validates with `ffprobe`

**Step 3: Write the failing integration test for true guarantee exhaustion**

Add a test where:

- emergency video writing is disabled or simulated to fail,
- no descendant delivers,
- root snapshot reports:
  - `delivery_status == "failed"`
  - `delivery_stop_reason` is populated
- `get_video_result(root_task_id)` remains `ready is False`

**Step 4: Extend HTTP tests**

Update `tests/integration/test_http_task_api.py` so `/api/tasks/{id}` and `/api/tasks/{id}/result` assert the new payload fields:

```python
assert snapshot.json()["delivery_status"] == "delivered"
assert snapshot.json()["completion_mode"] == "degraded"
assert snapshot.json()["resolved_task_id"] == delivered_child_id
assert result.json()["ready"] is True
assert result.json()["completion_mode"] == "degraded"
```

**Step 5: Extend MCP visibility tests**

Update `tests/integration/test_mcp_tools.py` so `get_video_task` surfaces:

- `delivery_status`
- `resolved_task_id`
- `completion_mode`
- `delivery_stop_reason`

**Step 6: Write the failing UI test**

Update `ui/src/features/tasks/TaskDetailPageV2.test.tsx` with a case that renders a guaranteed-delivery result and asserts the page shows a clear label such as:

- `已保底出片`
- or `简化交付`

and still renders the video player from the resolved artifact.

**Step 7: Run tests to verify they fail**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_guaranteed_video_delivery.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_mcp_tools.py -q

npm test -- src/features/tasks/TaskDetailPageV2.test.tsx
```

Expected: FAIL because delivery guarantee metadata and fallback execution do not exist yet.

### Task 2: Add Delivery Guarantee Settings and Root Metadata

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `tests/unit/test_settings.py`

**Step 1: Add rollout settings**

Add to `Settings`:

- `delivery_guarantee_enabled: bool = False`
- `delivery_guarantee_max_degradation_attempts: int = 2`
- `delivery_guarantee_allow_emergency_video: bool = True`
- `delivery_guarantee_ffmpeg_duration_seconds: int = 4`

Rollout defaults:

- `conservative`: disabled
- `supervised`: enabled only if we want guaranteed delivery without strategy auto-apply
- `autonomy-lite`: enabled

Keep the feature flag explicit so we can ship dark and test safely.

**Step 2: Extend `VideoTask`**

Add root-delivery metadata fields:

- `delivery_status: str | None = None`
- `resolved_task_id: str | None = None`
- `completion_mode: str | None = None`
- `delivery_tier: str | None = None`
- `delivery_stop_reason: str | None = None`

Rules:

- root tasks start with `delivery_status="pending"`
- child tasks can carry `completion_mode` and `delivery_tier`
- when a descendant or fallback delivers, root stores the resolved task id and completion mode

**Step 3: Expose metadata in snapshots and results**

Extend `VideoTaskSnapshot` and `VideoResult` to include:

- `delivery_status`
- `resolved_task_id`
- `completion_mode`
- `delivery_tier`
- `delivery_stop_reason`

**Step 4: Add SQLite migration**

In `sqlite_schema.py`, add a new migration after `008_strategy_profiles`, for example:

- `009_task_delivery_guarantee_fields`

Add nullable columns for the new metadata on `video_tasks`.

**Step 5: Update store serialization**

Ensure `sqlite_store.py` reads and writes the new fields consistently for:

- task creation,
- task updates,
- list/read operations,
- task snapshot reconstruction.

**Step 6: Run focused tests**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/unit/test_settings.py \
  tests/integration/test_http_task_api.py -q
```

Expected: FAIL or partial PASS until fallback orchestration is wired.

### Task 3: Implement a Delivery Guarantee Planner

**Files:**
- Create: `src/video_agent/application/delivery_guarantee_service.py`
- Create: `tests/unit/application/test_delivery_guarantee_service.py`
- Modify: `src/video_agent/domain/recovery_models.py`
- Modify: `src/video_agent/application/failure_contract.py`
- Modify: `src/video_agent/application/recovery_policy_service.py`

**Step 1: Add a dedicated decision model**

Extend `recovery_models.py` or add a sibling model for:

- `DeliveryGuaranteeDecision`
- `created: bool`
- `action: str | None`
- `delivery_tier: str | None`
- `child_task_id: str | None`
- `reason: str`

Actions should be limited to:

- `schedule_degraded_child`
- `emit_emergency_video`
- `stop_failed`

**Step 2: Teach failure/recovery planning about degradation**

Extend `failure_contract.py` and `RecoveryPolicyService.build(...)` so recovery data can suggest:

- `fallback_generation_mode="guided_generate"`
- `fallback_generation_mode="template_generate"`
- `candidate_actions` that include degraded generation before escalation

Keep this deterministic and bounded.

**Step 3: Implement planner rules**

In `delivery_guarantee_service.py`, create logic that:

- inspects the latest failed task, failure contract, lineage depth, and settings
- if degraded attempts remain:
  - creates a child task with simplified generation mode
- else if emergency fallback is enabled:
  - requests emergency video writing
- else:
  - returns `stop_failed`

The planner must not create infinite loops.

**Step 4: Add unit tests**

Write unit tests for:

- retryable render failure with degradation budget remaining
- non-retryable failure that skips directly to emergency fallback
- exhausted degradation budget
- disabled guarantee path

**Step 5: Run focused tests**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/unit/application/test_delivery_guarantee_service.py -q
```

Expected: PASS

### Task 4: Add a Deterministic Emergency Video Writer

**Files:**
- Create: `src/video_agent/adapters/rendering/emergency_video_writer.py`
- Create: `tests/integration/test_emergency_video_writer.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/application/workflow_engine.py`

**Step 1: Implement the writer**

Create `EmergencyVideoWriter` that produces a minimal MP4 using `ffmpeg` directly, without LLM output and without Manim scene generation.

Recommended implementation:

- use `ffmpeg -f lavfi -i color=...`
- emit a short silent video
- avoid text overlay in phase 1 so the fallback does not depend on font availability
- optionally write sidecar JSON or markdown describing:
  - original prompt
  - failure reason
  - completion mode

**Step 2: Register the final artifact**

The writer should:

- write to a temporary path inside the task artifact directory
- promote the MP4 to `artifacts/final_video.mp4`
- optionally emit one preview frame using existing extraction path
- return metadata for `completion_mode="emergency_fallback"`

**Step 3: Add integration coverage**

In `tests/integration/test_emergency_video_writer.py`, verify:

- file exists
- `HardValidator` accepts it
- artifact registration works

**Step 4: Wire the writer into app construction**

Pass the writer into `WorkflowEngine` through `create_app_context(...)` so it is available inside terminal failure handling.

**Step 5: Run focused tests**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_emergency_video_writer.py -q
```

Expected: PASS

### Task 5: Wire Failure Handling Into Guaranteed Delivery

**Files:**
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/auto_repair_service.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/revision_service.py`
- Modify: `tests/integration/test_auto_repair_loop.py`
- Modify: `tests/integration/test_auto_repair_status.py`
- Modify: `tests/integration/test_workflow_completion.py`

**Step 1: Keep failure artifact creation intact**

Do not remove the current `_fail_task(...)` observability behavior. The failed attempt should still persist:

- validation report
- failure context
- failure contract
- repair state event

This preserves debuggability.

**Step 2: Split post-failure orchestration**

After `auto_repair_service.maybe_schedule_repair(task)`:

- if repair child is created, root remains `delivery_status="pending"`
- if no repair child is created and guarantee is enabled, invoke `delivery_guarantee_service`
- if degraded child is created, root remains `delivery_status="pending"`
- if emergency video is emitted, mark root delivered immediately
- if nothing can deliver, mark root failed with a stop reason

**Step 3: Add degraded child creation**

Extend `TaskService` and/or `RevisionService` with a dedicated helper such as:

- `create_degraded_delivery_task(...)`

This helper should:

- derive from the failed parent,
- preserve lineage,
- lower the generation mode,
- inject fallback feedback that explicitly simplifies the output request,
- stamp `delivery_tier` on the child.

**Step 4: Resolve successful descendants to the root**

When a descendant completes successfully:

- update the root task with:
  - `delivery_status="delivered"`
  - `resolved_task_id=child.task_id`
  - `completion_mode`
  - `delivery_tier`
- optionally auto-mark the delivered child as `accepted_as_best`

This is the key step that lets callers poll the original task id and still receive the delivered artifact.

**Step 5: Keep root result resolution lineage-aware**

Update `TaskService.get_video_result(task_id)` so:

- if the requested task has `resolved_task_id`, result assets are read from that resolved task
- if the requested task itself is completed with no indirection, behavior stays unchanged
- if no resolved result exists yet, return `ready=False`

**Step 6: Keep task snapshots lineage-aware**

Update `TaskService.get_video_task(task_id)` so snapshots expose current delivery metadata even when the immediate task node failed.

**Step 7: Run focused tests**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_auto_repair_loop.py \
  tests/integration/test_auto_repair_status.py \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_guaranteed_video_delivery.py -q
```

Expected: PASS

### Task 6: Expose Delivery Guarantee Through HTTP, MCP, and UI

**Files:**
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `ui/src/lib/tasksApi.ts`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.tsx`
- Modify: `ui/src/features/tasks/TasksPageV2.tsx`
- Modify: `ui/src/features/videos/VideosPageV2.tsx`
- Modify: `ui/src/app/locale.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.test.tsx`

**Step 1: Extend API payloads**

Ensure task detail and result payloads include:

- `delivery_status`
- `resolved_task_id`
- `completion_mode`
- `delivery_tier`
- `delivery_stop_reason`

Do not remove existing fields.

**Step 2: Update TypeScript client models**

Extend `ui/src/lib/tasksApi.ts` so the UI can read the new fields without `any`.

**Step 3: Update task detail UX**

In `TaskDetailPageV2.tsx`:

- show a banner when the result was delivered via degradation or emergency fallback
- distinguish:
  - normal success,
  - repaired success,
  - degraded success,
  - emergency fallback success
- if delivery is still pending after an attempt failure, show that the system is continuing automatically rather than presenting the request as simply failed

**Step 4: Update list views if needed**

If tasks or videos list surfaces expose lineage roots, add a light badge for:

- `保底出片`
- `简化交付`

Do not over-design phase 1; task detail is the priority surface.

**Step 5: Run frontend checks**

Run:

```bash
npm test -- src/features/tasks/TaskDetailPageV2.test.tsx
npm run build
```

Expected: PASS

### Task 7: Add Operational Guardrails and Regression Coverage

**Files:**
- Modify: `tests/integration/test_capability_rollout_profiles.py`
- Modify: `tests/integration/test_http_task_reliability_api.py`
- Modify: `tests/integration/test_recent_videos_api.py` if present, otherwise `tests/integration/test_http_recent_videos_api.py`
- Modify: `docs/runbooks/` files only if helpful

**Step 1: Add rollout-profile coverage**

Verify:

- conservative profile keeps guarantee disabled by default
- supervised/autonomy-lite behave as intended

**Step 2: Add recent-videos regression coverage**

Ensure lineage-resolved delivery still shows up in recent videos and points to the resolved artifact.

**Step 3: Add reliability API coverage**

Make sure reliability endpoints report:

- delivery pending,
- delivered via degradation,
- true guarantee exhaustion

**Step 4: Run backend regression pack**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_guaranteed_video_delivery.py \
  tests/integration/test_emergency_video_writer.py \
  tests/integration/test_auto_repair_loop.py \
  tests/integration/test_auto_repair_status.py \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_http_task_reliability_api.py \
  tests/integration/test_http_recent_videos_api.py \
  tests/integration/test_mcp_tools.py \
  tests/integration/test_capability_rollout_profiles.py -q
```

Expected: PASS

### Task 8: Final Verification and Handoff

**Files:**
- No planned code changes

**Step 1: Run the final backend pack**

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_http_profile_api.py \
  tests/integration/test_http_eval_api.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_http_task_reliability_api.py \
  tests/integration/test_http_recent_videos_api.py \
  tests/integration/test_mcp_tools.py \
  tests/integration/test_auto_repair_loop.py \
  tests/integration/test_workflow_completion.py \
  tests/unit/application/test_delivery_guarantee_service.py \
  tests/unit/application/test_policy_promotion_service.py \
  tests/unit/application/test_preference_resolver.py \
  tests/unit/test_settings.py -q
```

Expected: PASS

**Step 2: Run the final frontend pack**

```bash
npm test -- src/features/tasks/TaskDetailPageV2.test.tsx src/features/videos/VideosPageV2.test.tsx
npm run build
```

Expected: PASS

**Step 3: Smoke-test the intended user flow**

Use a controlled local scenario where:

- primary task fails,
- the system continues automatically,
- the original root task id eventually returns a playable video,
- task detail explicitly explains whether the result is degraded.

**Step 4: Commit in small slices**

Recommended commit sequence:

1. `test: add guaranteed video delivery coverage`
2. `feat: add delivery guarantee metadata and migrations`
3. `feat: add degraded delivery planner and emergency video writer`
4. `feat: resolve lineage delivery through task and UI surfaces`

## Open Questions To Resolve During Execution

- Should `supervised` enable guaranteed delivery by default, or should it stay off until more burn-in?
- Should emergency fallback videos include burned-in text in phase 1, or should we keep them textless for maximum reliability?
- Should delivered descendants be auto-marked `accepted_as_best`, or should that stay a manual curation signal?

## Success Criteria

- A failed primary attempt no longer means the user immediately sees terminal failure when guaranteed delivery is enabled.
- Polling the original root task id can eventually return `ready=True` with a playable video.
- The system clearly marks whether the result is normal, repaired, degraded, or emergency fallback.
- Failure artifacts remain intact for debugging.
- The runtime still stops cleanly when even emergency fallback cannot run, with an explicit stop reason.
