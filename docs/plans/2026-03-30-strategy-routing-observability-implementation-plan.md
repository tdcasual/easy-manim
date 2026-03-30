# Strategy Routing Observability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose strategy routing configuration and runtime state through a profile API endpoint and the profile UI.

**Architecture:** Keep strategy observability read-only. Add `GET /api/profile/strategies` that returns strategy summaries derived from `StrategyProfile` storage, including routing keywords and guarded rollout state. Extend `ui/src/lib/profileApi.ts` and `ProfilePageV2.tsx` to fetch and render a compact "Strategy Routing" diagnostics section using the existing profile page layout patterns.

**Tech Stack:** Python, FastAPI, SQLite, React, TypeScript, pytest, Vitest

---

## Recommended Order

1. Add failing backend and frontend tests for strategy summaries.
2. Implement the backend endpoint and response shaping.
3. Wire the profile API client and render a read-only diagnostics section.
4. Run compact regression and UI build.

## Pre-flight

Read these files before implementation:

- `src/video_agent/server/http_api.py`
- `src/video_agent/adapters/storage/sqlite_store.py`
- `src/video_agent/domain/strategy_models.py`
- `tests/integration/test_http_profile_api.py`
- `ui/src/lib/profileApi.ts`
- `ui/src/features/profile/ProfilePageV2.tsx`
- `ui/src/features/profile/ProfilePageV2.test.tsx`

### Task 1: Add Failing Tests

**Files:**
- Modify: `tests/integration/test_http_profile_api.py`
- Modify: `ui/src/features/profile/ProfilePageV2.test.tsx`

**Step 1: Add failing backend test**

Add a test that:

- seeds one strategy profile with:
  - `prompt_cluster="geometry"`
  - `params["routing"]["keywords"] = ["triangle", "geometry"]`
  - `metrics["guarded_rollout"]["consecutive_shadow_passes"] = 2`
- calls `GET /api/profile/strategies`
- asserts:
  - response status is `200`
  - first item has `strategy_id`
  - `routing_keywords == ["triangle", "geometry"]`
  - `guarded_rollout["consecutive_shadow_passes"] == 2`

**Step 2: Add failing frontend test**

Extend `ProfilePageV2.test.tsx` so mocked fetch also returns `/api/profile/strategies`, then assert the page renders:

- section label like `Strategy Routing`
- strategy id
- routing keyword text
- guarded rollout text such as `shadow passes`

**Step 3: Run tests to verify they fail**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_http_profile_api.py -q
npm test -- src/features/profile/ProfilePageV2.test.tsx
```

Expected: FAIL because the endpoint and UI section do not exist yet.

### Task 2: Implement Backend Strategy Summary Endpoint

**Files:**
- Modify: `src/video_agent/server/http_api.py`

**Step 1: Add summary shaping helper**

Create a helper that converts a `StrategyProfile` into JSON with:

- `strategy_id`
- `scope`
- `prompt_cluster`
- `status`
- `routing_keywords`
- `params`
- `guarded_rollout`
- `last_eval_run`
- `created_at`
- `updated_at`

Routing keywords should be derived from `params["routing"]["keywords"]` and normalized to strings.

**Step 2: Add endpoint**

Add:

```python
@app.get("/api/profile/strategies")
```

Require `profile:read` and return:

```python
{"items": [...]}
```

Use deterministic sorting:

- active first
- then updated_at descending

### Task 3: Implement Profile UI Diagnostics

**Files:**
- Modify: `ui/src/lib/profileApi.ts`
- Modify: `ui/src/features/profile/ProfilePageV2.tsx`
- Modify only if needed: `ui/src/features/profile/ProfilePageV2.css`

**Step 1: Add typed API client**

Define `StrategyProfileSummary` and add `listProfileStrategies(token)`.

**Step 2: Fetch strategy summaries on refresh**

Load strategy summaries alongside profile, scorecard, runtime status, and suggestions.

**Step 3: Render a read-only "Strategy Routing" section**

Show, for each of the first few strategies:

- `strategy_id`
- status
- cluster
- routing keywords
- last promotion mode
- guarded rollout summary

Use existing compact card/list patterns rather than introducing a new page or editor.

### Task 4: Verify

**Files:**
- No code changes required unless regressions surface

**Step 1: Run backend regression**

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_http_profile_api.py \
  tests/integration/test_task_service_create_get.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_http_eval_api.py -q
```

Expected: PASS

**Step 2: Run frontend test and build**

```bash
npm test -- src/features/profile/ProfilePageV2.test.tsx
npm run build
```

Expected: PASS
