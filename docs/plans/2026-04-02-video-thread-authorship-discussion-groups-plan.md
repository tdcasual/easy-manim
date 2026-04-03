# Video Thread Authorship And Discussion Groups Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add stable owner-facing read models for “who shaped this version” and “what discussion threads are currently active” so a video thread can support persistent, agent-linked follow-up conversation instead of a flat turn list.

**Architecture:** Extend `video_thread_surface` with two new top-level sections: `authorship` and `discussion_groups`. Both should be projection-only for now, derived from thread turns, agent runs, selected result, and iteration state. Keep the UI placeholder-first but zero-inference: the frontend should not need to reconstruct reply chains or agent authorship from raw turns.

**Tech Stack:** FastAPI, Pydantic, SQLite JSON-backed thread store, React, TypeScript, Vitest, pytest.

---

### Task 1: Add Surface Models And Failing Tests
- Add failing tests for `authorship` and `discussion_groups`.

### Task 2: Project Authorship And Reply-Grouped Discussion Threads
- Derive current authorship from the latest responsible run or explanation turn.
- Group owner prompts with explicit replies via `reply_to_turn_id`.

### Task 3: Surface Placeholder UI
- Show authorship card and grouped discussion threads in the workbench.

### Task 4: Verify
- Run targeted backend/frontend checks, then full regressions.
