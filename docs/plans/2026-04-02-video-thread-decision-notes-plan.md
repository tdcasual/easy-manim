# Video Thread Decision Notes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a stable `decision_notes` section to `video_thread_surface` so each video can expose product-safe reasons for the current direction without forcing clients to infer rationale from scattered summary fields.

**Architecture:** Keep this slice projection-only. Build `decision_notes` from existing stable facts that already exist in the surface pipeline: selected-result rationale, latest visible explanation, and the active iteration goal. Emit typed note cards with stable ids, note kinds, titles, summaries, and source ids so the frontend can render a dedicated “why” panel with zero inference.

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
- `surface.decision_notes.title`
- `surface.decision_notes.items[*].note_kind`
- selection rationale and latest explanation appearing as distinct notes
- UI heading `Decision Notes`

**Step 2: Run tests to verify they fail**

Run: `./.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py tests/integration/test_mcp_video_thread_tools.py -q`

Expected: FAIL because `decision_notes` is missing from the surface.

Run: `cd ui && npm test -- src/features/videoThreads/VideoThreadPage.test.tsx`

Expected: FAIL because the UI does not render the new panel.

### Task 2: Add Domain Models And Projection Logic

**Files:**
- Modify: `src/video_agent/domain/video_thread_models.py`
- Modify: `src/video_agent/application/video_projection_service.py`

**Step 1: Add the new models**

Add:
- `VideoThreadDecisionNote`
- `VideoThreadDecisionNotes`

Each note should include:
- `note_id`
- `note_kind`
- `title`
- `summary`
- `emphasis`
- `source_iteration_id`
- `source_turn_id`
- `source_result_id`
- `actor_display_name`
- `actor_role`

**Step 2: Project minimal decision notes**

Build notes from:
- `selection_summary`
- `latest_explanation`
- active iteration goal

Rules:
- keep content product-safe
- keep note kinds stable
- prefer explicit reasoning summaries over duplicating raw turns

**Step 3: Run tests to verify they pass**

Run the same targeted backend pytest command.

Expected: PASS.

### Task 3: Render Placeholder UI

**Files:**
- Modify: `ui/src/lib/videoThreadsApi.ts`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.css`

**Step 1: Add typed client models**

Mirror the backend `decision_notes` structure in TypeScript.

**Step 2: Render the panel**

Add a `Decision Notes` panel that:
- lists note title and emphasis
- shows summary
- shows actor and source ids when available

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
- `decision_notes`
- stable note semantics
- zero-inference expectation for UI consumers

**Step 2: Run full verification**

Run: `./.venv-codex-verify/bin/python -m pytest -q`

Expected: PASS.

Run: `cd ui && npm test`

Expected: PASS.
