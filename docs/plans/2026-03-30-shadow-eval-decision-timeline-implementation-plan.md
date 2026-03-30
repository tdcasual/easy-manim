# Shadow Eval Decision Timeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make strategy challenger evaluation explicitly shadow-mode and surface a readable decision timeline through the HTTP API and eval UI.

**Architecture:** Keep the current `EvaluationService -> SQLite strategy profile metrics -> HTTP API -> React eval pages` shape. Extend the existing strategy profile metrics payload with a capped decision timeline, add read-only eval/timeline endpoints in `http_api.py`, and render the latest shadow decisions in the existing eval views without introducing new persistence tables.

**Tech Stack:** Python, FastAPI, SQLite, pytest, React, TypeScript, Vitest

---

## Recommended Order

1. Add failing backend tests first so the storage shape and API contract are explicit.
2. Implement shadow decision persistence before UI wiring so the frontend can target real data.
3. Add eval UI tests only after the HTTP payload is stable.
4. Verify backend and frontend separately, then run a small cross-slice regression.

## Pre-flight

Read these files before implementation:

- `src/video_agent/application/eval_service.py`
- `src/video_agent/application/policy_promotion_service.py`
- `src/video_agent/adapters/storage/sqlite_store.py`
- `src/video_agent/domain/strategy_models.py`
- `src/video_agent/server/http_api.py`
- `src/video_agent/adapters/storage/artifact_store.py`
- `tests/integration/test_eval_strategy_promotion.py`
- `tests/integration/test_http_profile_api.py`
- `ui/src/lib/evalsApi.ts`
- `ui/src/features/evals/EvalsPageV2.tsx`
- `ui/src/features/evals/EvalDetailPageV2.tsx`
- `ui/src/features/evals/EvalDetailPageV2.test.tsx`

### Task 1: Make Strategy Challenger Evaluation Explicitly Shadow-Mode

**Files:**
- Modify: `src/video_agent/domain/strategy_models.py`
- Modify: `src/video_agent/application/eval_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `tests/integration/test_eval_strategy_promotion.py`

**Step 1: Write the failing test**

Extend `tests/integration/test_eval_strategy_promotion.py` to assert:

```python
assert result["promotion_mode"] == "shadow"
assert result["promotion_decision"]["mode"] == "shadow"
assert profiles[0].metrics["decision_timeline"][0]["kind"] == "strategy_promotion_shadow"
assert profiles[0].metrics["decision_timeline"][0]["promotion_decision"]["mode"] == "shadow"
```

Also assert the timeline is capped and newest-first if multiple evals are recorded.

**Step 2: Run test to verify it fails**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_eval_strategy_promotion.py -q
```

Expected: FAIL because the result payload and stored metrics do not yet include explicit shadow-mode timeline events.

**Step 3: Write minimal implementation**

- Add optional metadata to `StrategyPromotionDecision`:

```python
mode: str = "shadow"
applied: bool = False
recorded_at: str | None = None
```

- In `EvaluationService.run_strategy_challenger(...)`, return:

```python
"promotion_mode": "shadow"
```

- In `SQLiteTaskStore.record_strategy_eval_run(...)`, persist:
  - `metrics["last_eval_run"]`
  - `metrics["decision_timeline"]` as newest-first, capped to a small fixed size

Each timeline item should include:
- `kind`
- `recorded_at`
- `strategy_id`
- `baseline_run_id`
- `challenger_run_id`
- `promotion_recommended`
- `promotion_decision`

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

### Task 2: Add Read-Only Eval and Strategy Timeline HTTP Endpoints

**Files:**
- Modify: `src/video_agent/server/http_api.py`
- Add: `tests/integration/test_http_eval_api.py`

**Step 1: Write the failing test**

Create `tests/integration/test_http_eval_api.py` covering:

```python
def test_http_profile_evals_lists_eval_summaries(...):
    response = client.get("/api/profile/evals", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["items"][0]["run_id"] == run_id

def test_http_profile_evals_detail_returns_run_summary(...):
    response = client.get(f"/api/profile/evals/{run_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["run_id"] == run_id

def test_http_strategy_timeline_returns_shadow_decisions(...):
    response = client.get("/api/profile/strategy-decisions", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["items"][0]["kind"] == "strategy_promotion_shadow"
```

**Step 2: Run test to verify it fails**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_http_eval_api.py -q
```

Expected: FAIL because the eval and strategy decision endpoints do not exist yet.

**Step 3: Write minimal implementation**

In `http_api.py`, add authenticated read-only endpoints:

- `GET /api/profile/evals`
- `GET /api/profile/evals/{run_id}`
- `GET /api/profile/strategy-decisions`

Contracts:
- Eval endpoints read from `artifact_store.list_eval_summaries()` / `artifact_store.read_eval_summary(run_id)`
- Strategy decisions read from `store.list_strategy_profiles()` and flatten `metrics["decision_timeline"]`
- Reuse `profile:read` scope for strategy decisions and `task:read`/`profile:read` compatible access for eval summaries

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

### Task 3: Surface Shadow Decision Timeline in Eval UI

**Files:**
- Modify: `ui/src/lib/evalsApi.ts`
- Modify: `ui/src/features/evals/EvalsPageV2.tsx`
- Modify: `ui/src/features/evals/EvalDetailPageV2.tsx`
- Modify: `ui/src/features/evals/EvalDetailPageV2.test.tsx`
- Add: `ui/src/features/evals/EvalsPageV2.test.tsx`

**Step 1: Write the failing test**

Add UI tests asserting:

```tsx
test("renders shadow promotion timeline on eval list page", async () => {
  // mock /api/profile/evals and /api/profile/strategy-decisions
  // assert "strategy_promotion_shadow" summary appears
})

test("renders promotion decision details on eval detail page", async () => {
  // mock /api/profile/evals/run-1 and /api/profile/strategy-decisions
  // assert shadow mode, reasons, and delta badges render
})
```

**Step 2: Run test to verify it fails**

Run:

```bash
npm test -- src/features/evals/EvalsPageV2.test.tsx src/features/evals/EvalDetailPageV2.test.tsx
```

Expected: FAIL because the API layer and UI do not yet expose decision timeline data.

**Step 3: Write minimal implementation**

- Extend `ui/src/lib/evalsApi.ts` with:
  - `StrategyDecisionTimelineItem`
  - `listStrategyDecisions(token)`
- In `EvalsPageV2.tsx`, fetch and render a compact “Recent Shadow Decisions” section
- In `EvalDetailPageV2.tsx`, show matching decision cards for the current run id when present

Keep the UI read-only and diagnostic-focused:
- mode
- approved/recommended
- reasons
- deltas
- recorded time

**Step 4: Run test to verify it passes**

Run the same `npm test` command.

Expected: PASS

### Task 4: Verify the Whole Slice

**Files:**
- No code changes required

**Step 1: Run backend verification**

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_http_eval_api.py -q
```

Expected: PASS

**Step 2: Run frontend verification**

```bash
npm test -- src/features/evals/EvalsPageV2.test.tsx src/features/evals/EvalDetailPageV2.test.tsx
npm run build
```

Expected: PASS

**Step 3: Run a compact regression**

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/unit/application/test_policy_promotion_service.py \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_http_profile_api.py -q
```

Expected: PASS
