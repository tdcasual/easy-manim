# Video Thread History And Render Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a zero-inference collaboration history surface and a richer unified render contract so every video thread can explain how the current video was produced, what was recently decided, and how the owner workbench should prioritize each panel without frontend inference.

**Architecture:** Extend the existing `video_thread_surface` instead of adding a second discussion payload. Introduce a dedicated `history` section with product-safe cards derived from visible turns, result selection, and agent run summaries; then promote the existing `render_contract` from a thin focus hint into an authoritative presentation contract with panel-level tone, emphasis, and expansion defaults. Keep all data thread-native and owner-safe: no raw chain-of-thought, only visible summaries and runtime facts.

**Tech Stack:** FastAPI, Pydantic, SQLite, thread-native projection services, React, TypeScript, Vitest, pytest.

---

### Task 1: Add Thread History And Richer Render Contract Models

**Files:**
- Modify: `src/video_agent/domain/video_thread_models.py`
- Test: `tests/unit/application/test_video_projection_service.py`
- Test: `tests/integration/test_video_thread_surface_projection.py`
- Test: `tests/integration/test_http_video_threads_api.py`
- Test: `tests/integration/test_fastmcp_video_thread_resources.py`

**Step 1: Write the failing tests**

Add tests that require `video_thread_surface` to expose:

- `history.cards[]`
- a typed history card shape with:
  - `card_id`
  - `card_type`
  - `title`
  - `summary`
  - `iteration_id`
  - `actor_display_name`
  - `actor_role`
  - `emphasis`
- richer `render_contract` fields:
  - `badge_order`
  - `sticky_primary_action_emphasis`
  - `panel_presentations[]`

Use assertions that prove:

- the latest visible explanation becomes a history card
- the latest result-selection rationale becomes a history card
- active agent-run output becomes a history card
- `render_contract.panel_presentations` explicitly marks emphasis/tone/default-open behavior for `current_focus`, `next_recommended_move`, `history`, and `composer`

**Step 2: Run tests to verify they fail**

Run:

```bash
./.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py -q
```

Expected: FAIL because the history section and richer render-contract fields do not exist yet.

**Step 3: Write the minimal implementation**

Implement the smallest stable contract:

- add `VideoThreadHistoryCard`, `VideoThreadHistory`, `VideoThreadPanelPresentation`
- extend `VideoThreadRenderContract` with explicit panel presentation hints and sticky action emphasis
- extend `VideoThreadSurface` with `history`

Do not add a new storage table for this slice. The history cards should be projection-only and derived from existing thread data.

**Step 4: Run tests to verify they pass**

Run the same command and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/domain/video_thread_models.py tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py
git commit -m "feat: add video thread history and render contract models"
```

### Task 2: Project History Cards And Render Semantics From Runtime Truth

**Files:**
- Modify: `src/video_agent/application/video_projection_service.py`
- Modify: `docs/runbooks/video-thread-surface-contract.md`
- Test: `tests/unit/application/test_video_projection_service.py`
- Test: `tests/integration/test_video_thread_surface_projection.py`
- Test: `tests/integration/test_http_video_threads_api.py`
- Test: `tests/integration/test_fastmcp_video_thread_resources.py`

**Step 1: Write the failing tests**

Add assertions that prove:

- history cards are ordered newest-first
- explanation cards prefer explicit `agent_explanation` turns over generic run summaries
- selection cards reflect the selected result and selected-result rationale
- process cards reflect the latest visible run output for the current or latest iteration
- `render_contract.badge_order` and `panel_presentations` match thread state:
  - attention state: recommended move emphasized, history expanded, sticky action strong
  - active state: current focus emphasized, history expanded, sticky action normal
  - running-agent state with no result: latest explanation or history can become focus

**Step 2: Run tests to verify they fail**

Run:

```bash
./.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py -q
```

Expected: FAIL because the projection logic still returns the older thin contract.

**Step 3: Write the minimal implementation**

Update `VideoProjectionService` to:

- build a stable `history` section from:
  - selected-result rationale
  - latest visible explanation turn
  - latest visible run output
  - latest owner follow-up or revision request when present
- dedupe repeated summaries so the same text does not appear as multiple adjacent cards
- assign card emphasis:
  - `primary` for the most important current explanation or selection card
  - `supporting` for process/runtime cards
  - `context` for owner follow-up cards
- emit richer `render_contract`:
  - `badge_order`
  - `sticky_primary_action_emphasis`
  - `panel_presentations` with authoritative tone/emphasis/collapsible/default-open values

**Step 4: Run tests to verify they pass**

Run the same command and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/application/video_projection_service.py docs/runbooks/video-thread-surface-contract.md tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py
git commit -m "feat: project video thread history and render semantics"
```

### Task 3: Surface History Cards In The Owner Workbench

**Files:**
- Modify: `ui/src/lib/videoThreadsApi.ts`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.css`
- Modify: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`
- Test: `ui/src/lib/videoThreadsApi.test.ts`
- Test: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`

**Step 1: Write the failing tests**

Add frontend tests that require:

- the workbench to render the new history section
- history cards to show actor, iteration, and emphasis labels
- the workbench shell to consume `render_contract.panel_presentations`
- the sticky primary action emphasis to affect the composer CTA class
- the focus label/footer area to show `default_focus_panel` plus the expanded-panel strategy

**Step 2: Run tests to verify they fail**

Run:

```bash
cd ui && npm test -- src/lib/videoThreadsApi.test.ts src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected: FAIL because the TypeScript types and workbench UI do not yet know about `history` or the richer render contract.

**Step 3: Write the minimal implementation**

Implement placeholder-first UI behavior:

- extend `VideoThreadSurface` TypeScript types with `history` and richer `render_contract`
- render a dedicated history panel in the workbench
- style cards by emphasis and use the panel presentations for shell-level class names and CTA emphasis
- keep the UI intentionally lightweight: no filtering, no iteration switching, no secondary endpoints in this slice

**Step 4: Run tests to verify they pass**

Run:

```bash
cd ui && npm test -- src/lib/videoThreadsApi.test.ts src/features/videoThreads/VideoThreadPage.test.tsx
cd ui && npm run build
```

Expected: PASS.

**Step 5: Commit**

```bash
git add ui/src/lib/videoThreadsApi.ts ui/src/features/videoThreads/VideoThreadWorkbench.tsx ui/src/features/videoThreads/VideoThreadWorkbench.css ui/src/features/videoThreads/VideoThreadPage.test.tsx ui/src/lib/videoThreadsApi.test.ts
git commit -m "feat: render video thread history cards in workbench"
```

### Task 4: Verification And Rollout Check

**Files:**
- Verify only

**Step 1: Run targeted backend and frontend verification**

Run:

```bash
./.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py -q
cd ui && npm test -- src/lib/videoThreadsApi.test.ts src/features/videoThreads/VideoThreadPage.test.tsx
cd ui && npm run build
```

**Step 2: Run full regression verification**

Run:

```bash
./.venv-codex-verify/bin/python -m pytest -q
cd ui && npm test
```

**Step 3: Summarize rollout**

Report:

- what contract fields were added
- what UI placeholder behavior now exists
- what this unlocks for the next slice:
  - persistent per-video thread transcript review
  - per-iteration compare/history views
  - thread-native “talk to the agent that made this” interaction
