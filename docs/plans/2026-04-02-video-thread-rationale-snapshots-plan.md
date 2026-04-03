# Video Thread Rationale Snapshots Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a stable `rationale_snapshots` section to `video_thread_surface` so the workbench can render canonical product-safe why notes across iterations without inferring them from events.

**Architecture:** Keep this slice projection-only. Build one canonical rationale snapshot per iteration from existing visible thread facts: selected-result rationale for the current iteration, latest visible agent explanation, and owner request or iteration goal fallback. Expose a typed top-level section plus render-contract hints, then render a placeholder panel in the video thread workbench.

**Tech Stack:** FastAPI, Pydantic, SQLite, React, TypeScript, pytest, Vitest.

---

### Task 1: Add Failing Tests

**Files:**
- Modify: `tests/unit/application/test_video_projection_service.py`
- Modify: `tests/integration/test_video_thread_surface_projection.py`
- Modify: `tests/integration/test_http_video_threads_api.py`
- Modify: `tests/integration/test_fastmcp_video_thread_resources.py`
- Modify: `tests/integration/test_mcp_video_thread_tools.py`
- Modify: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`

**Step 1: Write the failing tests**

Add expectations for:
- `surface.rationale_snapshots.title`
- `surface.rationale_snapshots.current_iteration_id`
- one snapshot per visible iteration
- selected-rationale priority for the current iteration
- frontend heading `Rationale Snapshots`

**Step 2: Run tests to verify they fail**

Run: `./.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py tests/integration/test_mcp_video_thread_tools.py -q`

Expected: FAIL because `rationale_snapshots` is missing from the surface.

Run: `cd ui && npm test -- src/features/videoThreads/VideoThreadPage.test.tsx`

Expected: FAIL because the UI does not render the new panel.

### Task 2: Add Domain Models And Projection Logic

**Files:**
- Modify: `src/video_agent/domain/video_thread_models.py`
- Modify: `src/video_agent/application/video_projection_service.py`

**Step 1: Add the new models**

Add:
- `VideoThreadRationaleSnapshot`
- `VideoThreadRationaleSnapshots`

Each item should include:
- `snapshot_id`
- `iteration_id`
- `snapshot_kind`
- `title`
- `summary`
- `source_turn_id`
- `source_result_id`
- `actor_display_name`
- `actor_role`
- `emphasis`
- `status`

**Step 2: Project minimal snapshots**

Rules:
- at most one snapshot per iteration
- prefer current selected rationale
- then latest agent explanation
- then owner goal / iteration goal fallback

**Step 3: Update render contract**

Add `rationale_snapshots` to:
- `panel_order`
- `default_expanded_panels` when items exist
- `panel_presentations`

**Step 4: Run targeted backend verification**

Run the same targeted backend pytest command.

Expected: PASS.

### Task 3: Render Placeholder UI

**Files:**
- Modify: `ui/src/lib/videoThreadsApi.ts`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`

**Step 1: Add typed client models**

Mirror the backend `rationale_snapshots` structure in TypeScript.

**Step 2: Render the panel**

Add a `Rationale Snapshots` panel that:
- lists one snapshot card per iteration
- shows title, kind, and status
- shows summary
- shows actor and source metadata

**Step 3: Run frontend targeted verification**

Run: `cd ui && npm test -- src/features/videoThreads/VideoThreadPage.test.tsx`

Expected: PASS.

Run: `cd ui && npm run build`

Expected: PASS.

### Task 4: Update Contract And Verify End-To-End

**Files:**
- Modify: `docs/runbooks/video-thread-surface-contract.md`

**Step 1: Document the new section**

Describe:
- `rationale_snapshots`
- canonical cross-iteration why semantics
- zero-inference expectation for UI consumers

**Step 2: Run full verification**

Run: `./.venv-codex-verify/bin/python -m pytest -q`

Expected: PASS.

Run: `cd ui && npm test`

Expected: PASS.
