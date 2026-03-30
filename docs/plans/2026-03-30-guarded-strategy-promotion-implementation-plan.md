# Guarded Strategy Promotion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a guarded path from shadow strategy evaluation to controlled strategy application, including limited canary activation and automatic rollback bookkeeping.

**Architecture:** Keep the current `EvaluationService -> SQLite strategy profile metrics -> HTTP API/UI` shape. Extend strategy-promotion settings with explicit guarded auto-apply controls, persist guarded rollout state on strategy profiles, and reuse the existing eval decision timeline so application and rollback events are visible without introducing a new table. Apply and rollback only switch strategy profile status inside the same `scope + prompt_cluster` slice; runtime consumption of active strategies remains a separate future step.

**Tech Stack:** Python, FastAPI, SQLite, pytest, React, TypeScript, Vitest

---

## Recommended Order

1. Add failing backend tests for guarded apply and rollback before changing production code.
2. Implement minimal rollout settings and storage state transitions.
3. Wire `EvaluationService.run_strategy_challenger(...)` to compute guarded decisions from current history.
4. Verify API payloads and existing UI surfaces still render the new decision kinds and modes.

## Pre-flight

Read these files before implementation:

- `src/video_agent/config.py`
- `src/video_agent/domain/strategy_models.py`
- `src/video_agent/application/policy_promotion_service.py`
- `src/video_agent/application/eval_service.py`
- `src/video_agent/adapters/storage/sqlite_store.py`
- `src/video_agent/server/http_api.py`
- `tests/integration/test_eval_strategy_promotion.py`
- `tests/integration/test_http_eval_api.py`
- `ui/src/features/evals/EvalsPageV2.tsx`
- `ui/src/features/evals/EvalDetailPageV2.tsx`

### Task 1: Add Failing Tests for Guarded Apply and Rollback

**Files:**
- Modify: `tests/integration/test_eval_strategy_promotion.py`
- Modify: `tests/integration/test_http_eval_api.py`

**Step 1: Write the failing test for guarded auto-apply**

Extend `tests/integration/test_eval_strategy_promotion.py` with a test that:

- builds settings with:
  - `strategy_promotion_enabled=True`
  - `strategy_promotion_guarded_auto_apply_enabled=True`
  - `strategy_promotion_guarded_auto_apply_min_shadow_passes=2`
  - `strategy_promotion_min_quality_gain=0.0`
- seeds:
  - one existing active strategy in cluster `beta`
  - one candidate strategy in cluster `beta`
- runs the challenger twice for the candidate strategy
- asserts after the second run:
  - candidate status becomes `active`
  - previous active strategy becomes `superseded`
  - result payload reports:
    - `promotion_decision["mode"] == "guarded_auto_apply"`
    - `promotion_decision["applied"] is True`
  - newest timeline item has `kind == "strategy_promotion_applied"`

**Step 2: Write the failing test for guarded rollback**

In the same file, add a test that:

- reuses the same setup
- first triggers guarded auto-apply for the candidate
- then tightens `strategy_promotion_min_quality_gain` back to `0.01`
- runs the challenger again for the now-active candidate
- asserts:
  - candidate status becomes `rolled_back`
  - previous strategy becomes `active` again
  - result payload reports:
    - `promotion_decision["mode"] == "guarded_auto_rollback"`
    - `promotion_decision["applied"] is True`
    - `promotion_decision["approved"] is False`
  - newest timeline item has `kind == "strategy_promotion_rollback"`

**Step 3: Write the failing API visibility test**

Extend `tests/integration/test_http_eval_api.py` with a test that seeds one applied decision and confirms:

```python
response = client.get("/api/profile/strategy-decisions", headers=auth_headers)
assert response.status_code == 200
assert response.json()["items"][0]["kind"] == "strategy_promotion_applied"
assert response.json()["items"][0]["promotion_decision"]["mode"] == "guarded_auto_apply"
```

**Step 4: Run tests to verify they fail**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_http_eval_api.py -q
```

Expected: FAIL because guarded settings, state transitions, and applied/rollback timeline kinds do not exist yet.

### Task 2: Add Guarded Promotion Settings and State Transitions

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/domain/strategy_models.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `tests/unit/test_settings.py`

**Step 1: Add rollout settings**

Add to `Settings`:

- `strategy_promotion_guarded_auto_apply_enabled: bool = False`
- `strategy_promotion_guarded_auto_apply_min_shadow_passes: int = 3`
- `strategy_promotion_guarded_auto_rollback_enabled: bool = True`

Update rollout defaults so:

- `conservative`: disabled
- `supervised`: disabled
- `autonomy-lite`: guarded auto-apply enabled

**Step 2: Extend strategy decision model only as needed**

Keep `StrategyPromotionDecision` lean, but allow modes:

- `shadow`
- `guarded_auto_apply`
- `guarded_auto_rollback`

No enum is required yet; string modes are sufficient.

**Step 3: Add SQLite store helpers**

In `sqlite_store.py`, add helpers to:

- locate the current active strategy for a `scope + prompt_cluster`
- activate a promoted strategy and supersede any previously active peer
- rollback a guarded strategy to its stored prior active peer when available

Persist guarded rollout bookkeeping in `profile.metrics["guarded_rollout"]`, including:

- `consecutive_shadow_passes`
- `last_applied_at`
- `rollback_target_strategy_id`
- `rollback_armed`

Keep this state JSON-based; do not add a new table.

**Step 4: Update decision timeline kind selection**

When recording a strategy eval:

- default kind: `strategy_promotion_shadow`
- if `promotion_decision.applied and promotion_decision.approved`: `strategy_promotion_applied`
- if `promotion_decision.applied and not promotion_decision.approved`: `strategy_promotion_rollback`

Also persist `last_eval_run["promotion_mode"]` from the actual decision mode, not a hardcoded `"shadow"`.

**Step 5: Run focused tests**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/unit/test_settings.py \
  tests/integration/test_eval_strategy_promotion.py -q
```

Expected: still FAIL until eval-service orchestration is added.

### Task 3: Wire Guarded Apply and Rollback Into EvaluationService

**Files:**
- Modify: `src/video_agent/application/eval_service.py`
- Modify: `tests/integration/test_eval_strategy_promotion.py`

**Step 1: Compute guarded state before persistence**

In `run_strategy_challenger(...)`:

- load the current strategy profile state
- compute the next consecutive shadow-pass count
- determine:
  - shadow only
  - guarded auto-apply
  - guarded auto-rollback

Rules:

- auto-apply only when:
  - promotion is approved
  - guarded auto-apply is enabled
  - next consecutive shadow-pass count meets threshold
  - challenger is not already active
- rollback only when:
  - promotion is rejected
  - guarded rollback is enabled
  - challenger is currently active
  - profile metrics contain an armed rollback target

**Step 2: Persist the eval run with final decision mode**

Build `promotion_decision` with:

- `mode`
- `applied`
- `recorded_at`

Then call `record_strategy_eval_run(...)`.

**Step 3: Apply status transition after recording**

If the final decision is:

- `guarded_auto_apply`: activate the candidate strategy
- `guarded_auto_rollback`: rollback to the previous active strategy

Re-read the updated profile if needed before returning.

**Step 4: Run tests to verify they pass**

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_http_eval_api.py -q
```

Expected: PASS

### Task 4: Verify Existing Surfaces Stay Stable

**Files:**
- Modify only if needed: `ui/src/lib/evalsApi.ts`
- Modify only if needed: `ui/src/features/evals/EvalsPageV2.test.tsx`
- Modify only if needed: `ui/src/features/evals/EvalDetailPageV2.test.tsx`

**Step 1: Run backend regression**

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin/pytest \
  tests/unit/application/test_policy_promotion_service.py \
  tests/unit/test_settings.py \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_http_profile_api.py \
  tests/integration/test_http_eval_api.py -q
```

Expected: PASS

**Step 2: Run frontend checks**

```bash
npm test -- src/features/evals/EvalsPageV2.test.tsx src/features/evals/EvalDetailPageV2.test.tsx
npm run build
```

Expected: PASS without mandatory UI code changes, because existing decision timeline UI should render new modes and kinds generically.

**Step 3: Commit**

```bash
git add src/video_agent/config.py \
  src/video_agent/domain/strategy_models.py \
  src/video_agent/application/eval_service.py \
  src/video_agent/adapters/storage/sqlite_store.py \
  tests/unit/test_settings.py \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_http_eval_api.py \
  docs/plans/2026-03-30-guarded-strategy-promotion-implementation-plan.md
git commit -m "feat: add guarded strategy promotion"
```
