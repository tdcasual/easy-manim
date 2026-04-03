# Video Thread Production Journal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a stable `production_journal` section to `video_thread_surface` so each video can show a zero-inference, product-safe record of how the current version was produced.

**Architecture:** Keep this slice projection-only. Build `production_journal` from first-class thread runtime facts that already exist: iterations, agent runs, and results. Do not introduce new storage yet. The backend should emit ordered journal entries with stable ids, titles, summaries, stages, statuses, and resource refs so the frontend can render a placeholder process log without reconstructing chronology from raw turns or task events.

**Tech Stack:** FastAPI, Pydantic, SQLite, React, TypeScript, pytest, Vitest.

---

### Task 1: Add Failing Tests For The New Surface Section

**Files:**
- Modify: `tests/unit/application/test_video_projection_service.py`
- Modify: `tests/integration/test_video_thread_surface_projection.py`
- Modify: `tests/integration/test_http_video_threads_api.py`
- Modify: `tests/integration/test_fastmcp_video_thread_resources.py`
- Modify: `tests/integration/test_mcp_video_thread_tools.py`
- Modify: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`

**Step 1: Write the failing tests**

Add expectations for:
- `surface.production_journal.title`
- `surface.production_journal.entries[*].entry_kind`
- result journal entries carrying `resource_refs`
- UI heading `Production Journal`

**Step 2: Run tests to verify they fail**

Run: `./.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py tests/integration/test_mcp_video_thread_tools.py -q`

Expected: FAIL because `production_journal` is missing from the surface.

Run: `cd ui && npm test -- src/features/videoThreads/VideoThreadPage.test.tsx`

Expected: FAIL because the UI does not render the new panel.

### Task 2: Add Domain Models And Projection Logic

**Files:**
- Modify: `src/video_agent/domain/video_thread_models.py`
- Modify: `src/video_agent/application/video_projection_service.py`

**Step 1: Add the new models**

Add:
- `VideoThreadProductionJournal`
- `VideoThreadProductionJournalEntry`

Each entry should include:
- `entry_id`
- `entry_kind`
- `title`
- `summary`
- `stage`
- `status`
- `iteration_id`
- `task_id`
- `run_id`
- `result_id`
- `actor_display_name`
- `actor_role`
- `resource_refs`

**Step 2: Project minimal journal entries**

Build entries from:
- iterations
- agent runs
- results

Rules:
- order entries chronologically
- keep summaries product-safe
- include result resources directly from `video_result`
- prefer stable, explicit stage labels instead of making the frontend infer them

**Step 3: Run tests to verify they pass**

Run the same targeted backend pytest command.

Expected: PASS.

### Task 3: Render Placeholder UI

**Files:**
- Modify: `ui/src/lib/videoThreadsApi.ts`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.css`

**Step 1: Add typed client models**

Mirror the backend `production_journal` structure in TypeScript.

**Step 2: Render the panel**

Add a `Production Journal` panel that:
- lists entry title, stage, and status
- shows summary
- shows actor and resource refs when available

**Step 3: Run frontend verification**

Run: `cd ui && npm test -- src/features/videoThreads/VideoThreadPage.test.tsx`

Expected: PASS.

Run: `cd ui && npm run build`

Expected: PASS.

### Task 4: Update Contract And Verify End-To-End

**Files:**
- Modify: `docs/runbooks/video-thread-surface-contract.md`

**Step 1: Document the new section**

Describe:
- `production_journal`
- stable entry semantics
- zero-inference expectation for UI consumers

**Step 2: Run full verification**

Run: `./.venv-codex-verify/bin/python -m pytest -q`

Expected: PASS.

Run: `cd ui && npm test`

Expected: PASS.
