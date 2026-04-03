# Video Thread Collaboration Intents Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn thread-native video collaboration turns into structured collaboration events with explicit owner intent and reply linkage so the system can durably record why a question was asked, what kind of change was requested, and which visible explanation answered which prompt.

**Architecture:** Extend `VideoTurn` and the owner-facing `history.cards` projection instead of adding a second discussion system. Persist `intent_type`, `reply_to_turn_id`, and optional `related_result_id` in turn JSON, populate them from thread service flows, then surface the linkage and intent labels through HTTP, MCP, and the workbench placeholder UI.

**Tech Stack:** FastAPI, Pydantic, SQLite JSON-backed thread storage, React, TypeScript, Vitest, pytest.

---

### Task 1: Add Structured Turn Intent And Reply Linkage

**Files:**
- Modify: `src/video_agent/domain/video_thread_models.py`
- Modify: `src/video_agent/application/video_turn_service.py`
- Modify: `src/video_agent/application/video_thread_service.py`
- Test: `tests/unit/domain/test_video_thread_models.py`
- Test: `tests/unit/application/test_video_turn_service.py`
- Test: `tests/integration/test_http_video_threads_api.py`
- Test: `tests/integration/test_mcp_video_thread_tools.py`

### Task 2: Project Intent-Aware History Cards

**Files:**
- Modify: `src/video_agent/application/video_projection_service.py`
- Modify: `docs/runbooks/video-thread-surface-contract.md`
- Test: `tests/unit/application/test_video_projection_service.py`
- Test: `tests/integration/test_video_thread_surface_projection.py`
- Test: `tests/integration/test_fastmcp_video_thread_resources.py`

### Task 3: Surface Intent Metadata In The Workbench Placeholder

**Files:**
- Modify: `ui/src/lib/videoThreadsApi.ts`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.css`
- Modify: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`
- Test: `ui/src/lib/videoThreadsApi.test.ts`

### Task 4: Verify The Slice

**Run:**

```bash
./.venv-codex-verify/bin/python -m pytest tests/unit/domain/test_video_thread_models.py tests/unit/application/test_video_turn_service.py tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py tests/integration/test_mcp_video_thread_tools.py -q
cd ui && npm test -- src/lib/videoThreadsApi.test.ts src/features/videoThreads/VideoThreadPage.test.tsx
cd ui && npm run build
./.venv-codex-verify/bin/python -m pytest -q
cd ui && npm test
```
