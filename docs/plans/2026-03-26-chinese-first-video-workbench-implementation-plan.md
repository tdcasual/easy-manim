# Chinese-First Video Workbench Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver the first implementation slice of the Chinese-first video workbench by adding human-readable task titles, a recent-videos API path, a dedicated `视频` page, and title-first task/video surfaces across the existing console.

**Architecture:** Extend the current task-centric backend instead of introducing a second content model. Keep `task_id` as the internal stable identifier, add `display_title` as the UI-facing task/video name, expose recent playable videos through an HTTP aggregation endpoint, and update the React console to consume those richer payloads. Ship this in small vertical slices so each task ends with passing tests and a working UI increment.

**Tech Stack:** Python, FastAPI, SQLite, Pydantic models, pytest, TypeScript, React, Vite, React Router, Testing Library, Vitest, existing HTTP session auth, and `@superpowers:test-driven-development`, `@superpowers:verification-before-completion`.

---

## Scope for This Plan

This implementation plan intentionally focuses on the next product-significant slice, not the entire long-range design:

1. Add `display_title` and `title_source` to the task domain and HTTP API.
2. Derive a stable Chinese-first display title from the initial prompt.
3. Add a recent-videos aggregation endpoint for the web UI.
4. Add a dedicated `视频` page in the React app.
5. Switch task/video surfaces to title-first presentation while keeping `task_id` secondary.

This plan does **not** attempt to ship all later ideas yet:

1. Manual title editing UI
2. Version comparison timeline
3. Natural-language change summaries between versions
4. Advanced search/filter persistence

## Task 1: Add task display-title fields to the backend domain

**Files:**
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Test: `tests/unit/test_task_service.py` or create `tests/unit/test_task_title_derivation.py`

**Step 1: Write the failing test**

Add a backend unit test that creates a task from a Chinese prompt and asserts:

1. `task_id` still exists
2. `display_title` is populated
3. `title_source == "prompt"`
4. the title is shorter and more human-readable than the full prompt

Example assertion shape:

```python
def test_create_task_derives_display_title_from_prompt():
    task = service.create_video_task("做一个蓝色圆形开场动画，画面干净简洁")
    assert task.task_id.startswith("task-")
    assert task.display_title == "蓝色圆形开场动画"
    assert task.title_source == "prompt"
```

**Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/unit/test_task_title_derivation.py -q
```

Expected: FAIL because the task model does not yet carry display-title fields.

**Step 3: Write minimal implementation**

Implement:

1. `display_title` and `title_source` in the task domain model
2. persistence support in SQLite
3. migration for existing databases
4. deterministic title derivation helper in task creation flow

Keep the first version simple and deterministic:

1. trim whitespace
2. split on major punctuation
3. keep the first concise Chinese phrase
4. clamp length to a readable range
5. fall back to the original prompt fragment if no better title can be derived

**Step 4: Run the test to verify it passes**

Run:

```bash
pytest tests/unit/test_task_title_derivation.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/domain/models.py src/video_agent/application/task_service.py src/video_agent/adapters/storage/sqlite_store.py src/video_agent/adapters/storage/sqlite_schema.py tests/unit/test_task_title_derivation.py
git commit -m "feat: add task display titles"
```

## Task 2: Expose display titles on task HTTP responses

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Test: `tests/integration/test_http_task_api.py`

**Step 1: Write the failing test**

Extend the HTTP task API integration tests to assert that:

1. `POST /api/tasks` returns `display_title`
2. `GET /api/tasks` returns each item's `display_title`
3. `GET /api/tasks/{task_id}` returns `display_title` and `title_source`

Example assertion shape:

```python
assert created["display_title"] == "蓝色圆形开场动画"
assert listed["items"][0]["display_title"] == "蓝色圆形开场动画"
```

**Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/integration/test_http_task_api.py -q
```

Expected: FAIL because those fields are not yet serialized.

**Step 3: Write minimal implementation**

Update the service and HTTP payload builders so task creation, task list, and task detail all include:

1. `display_title`
2. `title_source`

Keep response compatibility:

1. retain `task_id`
2. do not remove existing fields

**Step 4: Run the test to verify it passes**

Run:

```bash
pytest tests/integration/test_http_task_api.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/task_service.py src/video_agent/server/http_api.py src/video_agent/server/mcp_tools.py tests/integration/test_http_task_api.py
git commit -m "feat: expose task display titles over http"
```

## Task 3: Add a recent-videos aggregation endpoint

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/server/http_api.py`
- Create or Modify: `tests/integration/test_http_recent_videos_api.py`

**Step 1: Write the failing test**

Add an integration test for a new endpoint, for example:

`GET /api/videos/recent`

Assert that completed tasks with final videos return:

1. `task_id`
2. `display_title`
3. `status`
4. `updated_at`
5. `latest_summary`
6. `latest_video_url`
7. `latest_preview_url`
8. `title_source`

Also assert that tasks without playable results are excluded or clearly marked, depending on the chosen contract.

**Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/integration/test_http_recent_videos_api.py -q
```

Expected: FAIL because the endpoint does not exist.

**Step 3: Write minimal implementation**

Implement a task-service helper that:

1. lists recent tasks visible to the current agent
2. resolves latest result summary and video artifact availability
3. builds a compact aggregation payload for the UI

Then expose it through FastAPI. Keep it simple:

1. most recent first
2. bounded list size
3. same session auth rules as other task reads

**Step 4: Run the test to verify it passes**

Run:

```bash
pytest tests/integration/test_http_recent_videos_api.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/task_service.py src/video_agent/server/http_api.py tests/integration/test_http_recent_videos_api.py
git commit -m "feat: add recent videos api"
```

## Task 4: Add frontend API client support for display titles and recent videos

**Files:**
- Modify: `ui/src/lib/tasksApi.ts`
- Create: `ui/src/lib/videosApi.ts`
- Modify: `ui/src/lib/api.ts`
- Test: `ui/src/features/tasks/TasksPage.test.tsx`
- Create: `ui/src/features/videos/VideosPage.test.tsx`

**Step 1: Write the failing tests**

Add or extend frontend tests to assert that:

1. the task list renders `display_title` rather than only `task_id`
2. a new recent-videos client can fetch and render aggregated video entries

Example assertion shape:

```tsx
expect(await screen.findByText("蓝色圆形开场动画")).toBeInTheDocument();
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
npm --prefix ui test -- TasksPage.test.tsx VideosPage.test.tsx
```

Expected: FAIL because the typed clients and page do not exist yet.

**Step 3: Write minimal implementation**

Implement:

1. task client types carrying `display_title`
2. dedicated `videosApi.ts` for recent-videos fetches
3. resource URL resolution helpers if the new endpoint returns relative artifact paths

**Step 4: Run the tests to verify they pass**

Run:

```bash
npm --prefix ui test -- TasksPage.test.tsx VideosPage.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui/src/lib/tasksApi.ts ui/src/lib/videosApi.ts ui/src/lib/api.ts ui/src/features/tasks/TasksPage.test.tsx ui/src/features/videos/VideosPage.test.tsx
git commit -m "feat: add frontend recent videos client"
```

## Task 5: Build the dedicated 视频 page

**Files:**
- Create: `ui/src/features/videos/VideosPage.tsx`
- Create: `ui/src/app/pages/VideosPage.tsx`
- Modify: `ui/src/app/App.tsx`
- Modify: `ui/src/app/ui.tsx`
- Modify: `ui/src/styles/theme.css`
- Test: `ui/src/features/videos/VideosPage.test.tsx`

**Step 1: Write the failing test**

Create a page test that asserts:

1. `视频` navigation is present
2. the page renders recent video cards using `display_title`
3. each card exposes `继续修订` or `查看详情`

**Step 2: Run the test to verify it fails**

Run:

```bash
npm --prefix ui test -- VideosPage.test.tsx
```

Expected: FAIL because the page and route do not exist.

**Step 3: Write minimal implementation**

Build the first dedicated `视频` page with:

1. title-first cards
2. playable preview or poster
3. task status
4. summary
5. links to task detail

Also add:

1. `视频` nav item in the shell
2. route wiring
3. minimal responsive styles

**Step 4: Run the test to verify it passes**

Run:

```bash
npm --prefix ui test -- VideosPage.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui/src/features/videos/VideosPage.tsx ui/src/app/pages/VideosPage.tsx ui/src/app/App.tsx ui/src/app/ui.tsx ui/src/styles/theme.css ui/src/features/videos/VideosPage.test.tsx
git commit -m "feat: add videos page"
```

## Task 6: Switch task surfaces to title-first presentation

**Files:**
- Modify: `ui/src/features/tasks/TasksPage.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPage.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPage.test.tsx`
- Modify: `ui/src/features/tasks/TasksPage.test.tsx`

**Step 1: Write the failing test**

Update the tasks-page and task-detail tests to assert:

1. list cards show `display_title`
2. task detail title uses `display_title`
3. `task_id` remains visible as secondary metadata only

Example assertion shape:

```tsx
expect(await screen.findByRole("heading", { name: /蓝色圆形开场动画/i })).toBeInTheDocument();
expect(screen.getByText("task-1")).toBeInTheDocument();
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
npm --prefix ui test -- TasksPage.test.tsx TaskDetailPage.test.tsx
```

Expected: FAIL because the UI still treats the ID as the dominant label.

**Step 3: Write minimal implementation**

Update task views so:

1. `display_title` is the primary task label
2. `task_id` is shown in metadata bands or captions
3. recent-videos cards and task cards use the same naming hierarchy

**Step 4: Run the tests to verify they pass**

Run:

```bash
npm --prefix ui test -- TasksPage.test.tsx TaskDetailPage.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui/src/features/tasks/TasksPage.tsx ui/src/features/tasks/TaskDetailPage.tsx ui/src/features/tasks/TasksPage.test.tsx ui/src/features/tasks/TaskDetailPage.test.tsx
git commit -m "feat: make task ui title-first"
```

## Task 7: Verification pass for the shipped slice

**Files:**
- Modify: `docs/runbooks/local-dev.md` if API/UI behavior changed
- Modify: `README.md` only if needed

**Step 1: Run backend verification**

Run:

```bash
pytest tests/integration/test_http_task_api.py tests/integration/test_http_recent_videos_api.py -q
```

Expected: PASS

If collection fails because the local environment is missing optional runtime dependencies, install the documented dev dependencies first and rerun. Do not claim backend verification passed without a real rerun.

**Step 2: Run frontend verification**

Run:

```bash
npm --prefix ui test
npm --prefix ui run build
```

Expected:

1. all Vitest suites PASS
2. Vite production build PASS

**Step 3: Smoke-check the main flows manually**

Run the app locally and verify:

1. login still works
2. task creation still works
3. `任务` page shows title-first cards
4. `视频` page loads recent playable entries
5. task detail shows `display_title` plus secondary `task_id`

**Step 4: Update docs**

If the new `视频` route or title fields affect operator usage, update the local-dev/runbook docs with:

1. the new page purpose
2. the new API endpoint
3. any local setup needed

**Step 5: Commit**

```bash
git add README.md docs/runbooks/local-dev.md
git commit -m "docs: update workbench usage docs"
```

## Recommended Execution Order

Follow this order strictly:

1. backend title fields
2. HTTP exposure of title fields
3. recent-videos API
4. frontend API wiring
5. dedicated `视频` page
6. title-first task surfaces
7. final verification

This order keeps each layer unblocked by the previous one and avoids building frontend placeholders against unstable contracts.

## Risks to Watch

1. Existing tasks in SQLite will not have `display_title`; migration and fallback behavior must be safe.
2. The title derivation helper can become too “smart” and unstable. Keep it deterministic first.
3. Recent-videos aggregation can turn into an N+1 artifact lookup path if implemented carelessly.
4. UI tests will become flaky if they assert on internal IDs as primary labels after the title-first shift.

## Definition of Done

This implementation slice is done when:

1. backend tasks carry `display_title` and `title_source`
2. the HTTP API exposes those fields
3. `GET /api/videos/recent` or equivalent returns recent playable entries
4. the React app has a dedicated `视频` page
5. task and video surfaces are title-first, with `task_id` demoted to secondary metadata
6. frontend tests and build pass
7. backend tests for the new API surface pass in a dependency-complete environment
