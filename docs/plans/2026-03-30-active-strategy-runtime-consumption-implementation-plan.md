# Active Strategy Runtime Consumption Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make active strategy profiles actually affect newly created tasks by merging strategy params into the effective request profile and persisting which strategy was applied.

**Architecture:** Keep task creation centered in `TaskService.create_video_task(...)`. Add a lightweight strategy resolution step before effective request config is built: global active strategies (`prompt_cluster=None`) apply automatically, and cluster-specific active strategies apply only when the request explicitly includes `strategy_prompt_cluster`. Persist the selected `strategy_profile_id` on the task and expose it in task snapshots for diagnostics.

**Tech Stack:** Python, FastAPI, SQLite, pytest

---

## Recommended Order

1. Add failing task-service tests for global and cluster-scoped strategy application.
2. Add minimal request plumbing for `strategy_prompt_cluster`.
3. Implement active strategy resolution and request-profile merging.
4. Verify HTTP/MCP surfaces and task snapshots expose the selected strategy id.

## Pre-flight

Read these files before implementation:

- `src/video_agent/application/task_service.py`
- `src/video_agent/application/preference_resolver.py`
- `src/video_agent/adapters/storage/sqlite_store.py`
- `src/video_agent/domain/models.py`
- `src/video_agent/server/mcp_tools.py`
- `src/video_agent/server/http_api.py`
- `tests/integration/test_task_service_create_get.py`
- `tests/integration/test_http_task_api.py`

### Task 1: Add Failing Tests for Runtime Strategy Application

**Files:**
- Modify: `tests/integration/test_task_service_create_get.py`
- Modify: `tests/integration/test_http_task_api.py`

**Step 1: Add failing task-service test for global active strategy**

Write a test that:

- creates an active strategy with:
  - `scope="global"`
  - `prompt_cluster=None`
  - `params={"style_hints": {"tone": "teaching"}, "output_profile": {"quality_preset": "production"}}`
- creates a task with no explicit overrides
- loads the persisted task from the store
- asserts:
  - `task.strategy_profile_id == strategy.strategy_id`
  - `task.style_hints["tone"] == "teaching"`
  - `task.output_profile["quality_preset"] == "production"`

**Step 2: Add failing task-service test for explicit override precedence**

In the same file, write a test that:

- uses the same active global strategy
- creates a task with explicit `style_hints={"tone": "dramatic"}`
- asserts:
  - the strategy is still selected
  - `task.style_hints["tone"] == "dramatic"`

**Step 3: Add failing cluster-scoped HTTP test**

Extend `tests/integration/test_http_task_api.py` with a test that:

- seeds one active strategy with `prompt_cluster="beta"`
- creates a task through `POST /api/tasks` with:
  - `strategy_prompt_cluster="beta"`
- asserts from the stored task:
  - `strategy_profile_id` is set
  - merged style hints include strategy params

Also verify a request without `strategy_prompt_cluster` does not pick that cluster-scoped strategy.

**Step 4: Run tests to verify they fail**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_task_service_create_get.py \
  tests/integration/test_http_task_api.py -q
```

Expected: FAIL because task creation does not resolve active strategies and the HTTP create payload does not accept `strategy_prompt_cluster`.

### Task 2: Add Strategy Resolution Inputs to Task Creation

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/domain/models.py`

**Step 1: Add request input**

Add optional `strategy_prompt_cluster: str | None = None` to:

- `TaskService.create_video_task(...)`
- MCP tool payload plumbing
- FastMCP tool signature
- HTTP `CreateTaskRequest`

**Step 2: Expose selected strategy on diagnostics**

Add `strategy_profile_id: str | None = None` to `VideoTaskSnapshot` and include it when building snapshots.

### Task 3: Implement Active Strategy Resolution

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify only if needed: `src/video_agent/adapters/storage/sqlite_store.py`

**Step 1: Resolve active strategy before merging request config**

Add a helper that:

- if `strategy_prompt_cluster` is provided:
  - selects the matching active strategy for `scope="global"` and that cluster
- otherwise:
  - selects the active global strategy with `prompt_cluster is None`

If no strategy matches, return `None`.

**Step 2: Merge strategy params with correct precedence**

Use effective order:

- system defaults
- agent profile
- token override
- active strategy params
- explicit request overrides

Persist:

- `strategy_profile_id`
- merged request profile

**Step 3: Run tests to verify they pass**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_task_service_create_get.py \
  tests/integration/test_http_task_api.py -q
```

Expected: PASS

### Task 4: Verify Regressions

**Files:**
- No code changes required unless a regression surfaces

**Step 1: Run backend regression**

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_task_service_create_get.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_http_eval_api.py \
  tests/unit/application/test_preference_resolver.py -q
```

Expected: PASS

**Step 2: Commit**

```bash
git add src/video_agent/application/task_service.py \
  src/video_agent/domain/models.py \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/server/fastmcp_server.py \
  src/video_agent/server/http_api.py \
  tests/integration/test_task_service_create_get.py \
  tests/integration/test_http_task_api.py \
  docs/plans/2026-03-30-active-strategy-runtime-consumption-implementation-plan.md
git commit -m "feat: apply active strategies during task creation"
```
