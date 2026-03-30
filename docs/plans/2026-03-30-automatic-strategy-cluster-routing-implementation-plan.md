# Automatic Strategy Cluster Routing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically route new tasks to active cluster-specific strategies based on prompt text, while preserving explicit cluster overrides and global fallback behavior.

**Architecture:** Keep runtime strategy selection inside `TaskService.create_video_task(...)`. Add a lightweight keyword-based router that inspects active strategy profiles with `prompt_cluster != None` and optional `params["routing"]["keywords"]`, picks the best-matching cluster strategy for the prompt, and otherwise falls back to the existing global active strategy (`prompt_cluster=None`). Only request-shaping fields from the strategy should be merged into the task request profile.

**Tech Stack:** Python, FastAPI, SQLite, pytest

---

## Recommended Order

1. Add failing tests for automatic cluster routing and global fallback.
2. Implement minimal routing helpers in task service.
3. Keep explicit request cluster precedence unchanged.
4. Verify regressions across task creation and guarded strategy evaluation.

## Pre-flight

Read these files before implementation:

- `src/video_agent/application/task_service.py`
- `src/video_agent/application/preference_resolver.py`
- `src/video_agent/adapters/storage/sqlite_store.py`
- `src/video_agent/server/http_api.py`
- `tests/integration/test_task_service_create_get.py`
- `tests/integration/test_http_task_api.py`

### Task 1: Add Failing Tests for Automatic Routing

**Files:**
- Modify: `tests/integration/test_task_service_create_get.py`
- Modify: `tests/integration/test_http_task_api.py`

**Step 1: Add failing task-service test for keyword-routed cluster strategy**

Write a test that:

- seeds:
  - one global active strategy with `prompt_cluster=None`
  - one cluster active strategy with `prompt_cluster="geometry"`
  - cluster strategy params:
    - `routing: {"keywords": ["triangle", "geometry"]}`
    - `style_hints: {"tone": "teaching"}`
- creates a task with prompt `"explain triangle area proof"`
- asserts:
  - cluster strategy is selected
  - `task.style_hints["tone"] == "teaching"`

**Step 2: Add failing task-service fallback test**

Write a test that:

- uses the same setup
- creates a task with a prompt that matches no routing keywords
- asserts the global strategy is selected instead

**Step 3: Add failing HTTP routing test**

Extend `tests/integration/test_http_task_api.py` with a test that:

- seeds a cluster strategy with routing keywords
- calls `POST /api/tasks` without `strategy_prompt_cluster`
- uses a prompt containing one of the routing keywords
- asserts stored task `strategy_profile_id` equals that cluster strategy id

**Step 4: Run tests to verify they fail**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_task_service_create_get.py \
  tests/integration/test_http_task_api.py -q
```

Expected: FAIL because task creation does not infer clusters from prompt text.

### Task 2: Implement Automatic Cluster Routing

**Files:**
- Modify: `src/video_agent/application/task_service.py`

**Step 1: Add strategy request filtering**

Create a helper that converts `strategy.params` into request overrides by keeping only:

- `style_hints`
- `output_profile`
- `validation_profile`

Ignore routing metadata during request merge.

**Step 2: Add keyword-routing helper**

Create helpers that:

- normalize prompt text for case-insensitive matching
- extract routing keywords from `strategy.params["routing"]["keywords"]`
- score each active cluster strategy by number of keyword matches
- choose the best matching active cluster strategy when score > 0

Tie-breaker:

- higher match count first
- then longer matched keyword length
- then stable strategy id ordering

**Step 3: Update active strategy resolution**

Keep precedence:

- explicit `strategy_prompt_cluster`
- automatic keyword-routed cluster strategy
- global active strategy

### Task 3: Verify Regressions

**Files:**
- No code changes required unless regressions surface

**Step 1: Run backend regression**

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/unit/application/test_preference_resolver.py \
  tests/integration/test_task_service_create_get.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_http_eval_api.py \
  tests/integration/test_mcp_tools.py -q
```

Expected: PASS

**Step 2: Run frontend build**

```bash
npm run build
```

Expected: PASS

**Step 3: Commit**

```bash
git add src/video_agent/application/task_service.py \
  tests/integration/test_task_service_create_get.py \
  tests/integration/test_http_task_api.py \
  docs/plans/2026-03-30-automatic-strategy-cluster-routing-implementation-plan.md
git commit -m "feat: auto-route cluster strategies from prompts"
```
