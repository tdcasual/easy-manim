# Video Thread Artifact Lineage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a stable `artifact_lineage` section to `video_thread_surface` so the UI and agents can read visible result-to-result evolution without inferring lineage from scattered thread facts.

**Architecture:** Keep this slice projection-only. Build lineage hops from existing thread runtime truth: iterations, results, product-safe turns, and runs. Expose one top-level read model plus render-contract hints, then render a placeholder panel in the video thread workbench.

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
- `surface.artifact_lineage.title`
- `surface.artifact_lineage.selected_result_id`
- at least one origin lineage item
- a revision lineage item with `from_result_id` and `to_result_id`
- `status == "selected"` for the selected hop
- frontend heading `Artifact Lineage`

**Step 2: Run tests to verify they fail**

Run: `./.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py tests/integration/test_mcp_video_thread_tools.py -q`

Expected: FAIL because `artifact_lineage` is missing from the surface.

Run: `cd ui && npm test -- src/features/videoThreads/VideoThreadPage.test.tsx`

Expected: FAIL because the UI does not render the new panel.

### Task 2: Add Domain Models And Projection Logic

**Files:**
- Modify: `src/video_agent/domain/video_thread_models.py`
- Modify: `src/video_agent/application/video_projection_service.py`

**Step 1: Add the new models**

Add:
- `VideoThreadArtifactLineageItem`
- `VideoThreadArtifactLineage`

Each item should include:
- `lineage_id`
- `iteration_id`
- `from_result_id`
- `to_result_id`
- `change_summary`
- `change_reason`
- `trigger_turn_id`
- `trigger_label`
- `actor_display_name`
- `actor_role`
- `emphasis`
- `status`

**Step 2: Project minimal lineage hops**

Rules:
- create one hop per iteration that has a visible result or source-result anchor
- use `iteration.source_result_id` for the incoming edge
- use selected or latest iteration result for the outgoing edge
- use product-safe turns and runs for visible reason and actor metadata
- never expose hidden reasoning

**Step 3: Update render contract**

Add `artifact_lineage` to:
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
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.css`

**Step 1: Add typed client models**

Mirror the backend `artifact_lineage` structure in TypeScript.

**Step 2: Render the panel**

Add an `Artifact Lineage` panel that:
- lists lineage hops as cards
- shows `from_result_id -> to_result_id`
- shows status and emphasis
- shows change summary and reason
- shows trigger and actor metadata

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
- `artifact_lineage`
- stable lineage-hop semantics
- zero-inference expectation for UI consumers

**Step 2: Run full verification**

Run: `./.venv-codex-verify/bin/python -m pytest -q`

Expected: PASS.

Run: `cd ui && npm test`

Expected: PASS.
