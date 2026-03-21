# Human UI Operator Console Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver the first human-facing `easy-manim` web console so operators can log in, create tasks, inspect results, review memory and profile suggestions, and read eval summaries without falling back to CLI, curl, or raw MCP tooling.

**Architecture:** Keep the newly shipped FastAPI HTTP API as the product backend and add a separate frontend workspace under `ui/` built against those endpoints. Start with an operator console, not a public marketing site and not a second control plane: the UI should be a thin client over `/api/sessions`, `/api/tasks`, `/api/memory/*`, `/api/profile/*`, and `/api/profile/evals*`, with session-token auth stored client-side. Optimize for a clean desktop-first workflow that still adapts to tablet/mobile widths.

**Tech Stack:** TypeScript, React, Vite, React Router, TanStack Query, Testing Library, Vitest, Playwright, FastAPI HTTP API, existing opaque session auth, existing task/memory/profile/eval endpoints, and `@superpowers:test-driven-development`, `@superpowers:verification-before-completion`, `@superpowers:requesting-code-review`.

---

## Audit Summary Driving This Plan

Current repo status:

1. There is **no real frontend codebase** yet. No `package.json`, no `ui/`, no templates, no static asset pipeline.
2. The current “UI” is effectively FastAPI OpenAPI docs plus CLI/runbook examples.
3. The backend surface is now rich enough to power a real console:
   - session login/logout
   - task create/list/detail/result/revise/retry/cancel
   - session memory + persistent memory
   - profile read/apply/scorecard/suggestions/evals
4. The biggest product gap is no human-visible console for operators, reviewers, or internal QA.

Recommended next phase:

1. Build a **human operator console** on top of the existing HTTP API.
2. Do **not** build a public dashboard, multi-user admin SaaS shell, or billing/account pages.
3. Treat this as a productization layer over an already-capable backend.

## Recommended Delivery Bands

**Band 1: Must ship**
1. Frontend scaffold and auth session flow
2. Task workspace
3. Result and task detail views
4. Responsive app shell and empty/error/loading states

**Band 2: Strongly recommended next**
1. Session memory and persistent memory views
2. Profile read/apply UI
3. Scorecard and suggestion review/apply flow

**Band 3: Fast follow**
1. Eval history and run detail pages
2. Operator polish, keyboard support, and richer review tools
3. Optional FastAPI static hosting or packaged deployment path

### Task 1: Scaffold the UI workspace and application shell

**Files:**
- Create: `ui/package.json`
- Create: `ui/tsconfig.json`
- Create: `ui/vite.config.ts`
- Create: `ui/index.html`
- Create: `ui/src/main.tsx`
- Create: `ui/src/app/App.tsx`
- Create: `ui/src/app/router.tsx`
- Create: `ui/src/styles/theme.css`
- Create: `ui/src/styles/reset.css`
- Create: `ui/src/app/App.test.tsx`
- Modify: `README.md`
- Modify: `docs/runbooks/local-dev.md`

**Step 1: Write the failing test**

Create `ui/src/app/App.test.tsx` with a minimal shell assertion:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

test("renders the operator console shell", () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: /easy-manim console/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /tasks/i })).toBeInTheDocument();
});
```

**Step 2: Run the test to verify it fails**

Run:

```bash
npm --prefix ui test -- App.test.tsx
```

Expected: FAIL because the `ui/` workspace does not exist yet.

**Step 3: Write minimal implementation**

Create a Vite + React + TypeScript workspace with:

1. `App` shell with a persistent sidebar/header
2. routes for `Tasks`, `Memory`, `Profile`, and `Evals`
3. a strong visual direction:
   - warm light theme, not generic dark glassmorphism
   - expressive display font + readable body font
   - clear spacing rhythm and non-generic navigation hierarchy
4. base CSS tokens in `theme.css`

**Step 4: Run the tests to verify they pass**

Run:

```bash
npm --prefix ui install
npm --prefix ui test -- App.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui README.md docs/runbooks/local-dev.md
git commit -m "feat: scaffold operator console ui"
```

### Task 2: Add session-authenticated login and API client plumbing

**Files:**
- Create: `ui/src/lib/api.ts`
- Create: `ui/src/lib/session.ts`
- Create: `ui/src/features/auth/LoginPage.tsx`
- Create: `ui/src/features/auth/useSession.ts`
- Create: `ui/src/features/auth/LoginPage.test.tsx`
- Modify: `ui/src/app/router.tsx`
- Modify: `ui/src/app/App.tsx`
- Modify: `src/video_agent/server/http_api.py`
- Test: `tests/integration/test_http_api.py`

**Step 1: Write the failing tests**

Create `ui/src/features/auth/LoginPage.test.tsx`:

```tsx
test("stores session token after successful login", async () => {
  // mock POST /api/sessions
  // submit token form
  // assert session persistence and redirect
});
```

Extend `tests/integration/test_http_api.py` with a small CORS/dev-client readiness check if the chosen frontend architecture uses a separate dev server.

**Step 2: Run the tests to verify they fail**

Run:

```bash
npm --prefix ui test -- LoginPage.test.tsx
source .venv/bin/activate && python -m pytest tests/integration/test_http_api.py -q
```

Expected: FAIL because session client plumbing and any required backend CORS config are not in place.

**Step 3: Write minimal implementation**

Implement:

1. `api.ts` with typed helpers for authenticated requests
2. `session.ts` for reading/writing opaque session token and current identity
3. login page with:
   - single token input
   - pending/error state
   - redirect into the app after success
4. guarded routes so the console does not render protected screens while logged out
5. minimal backend dev support if needed:
   - CORS for the UI dev origin
   - no weakening of auth rules

**Step 4: Run the tests to verify they pass**

Run:

```bash
npm --prefix ui test -- LoginPage.test.tsx
source .venv/bin/activate && python -m pytest tests/integration/test_http_api.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui src/video_agent/server/http_api.py tests/integration/test_http_api.py
git commit -m "feat: add operator console login flow"
```

### Task 3: Build the task workspace and task detail flow

**Files:**
- Create: `ui/src/features/tasks/TasksPage.tsx`
- Create: `ui/src/features/tasks/TaskComposer.tsx`
- Create: `ui/src/features/tasks/TaskList.tsx`
- Create: `ui/src/features/tasks/TaskDetailPage.tsx`
- Create: `ui/src/features/tasks/TaskDetailPage.test.tsx`
- Modify: `ui/src/app/router.tsx`
- Modify: `ui/src/lib/api.ts`
- Test: `tests/integration/test_http_task_api.py`

**Step 1: Write the failing tests**

Create `ui/src/features/tasks/TaskDetailPage.test.tsx`:

```tsx
test("shows task status, artifacts, and result summary", async () => {
  // mock list + detail + result endpoints
  // assert pending then loaded task detail UI
});
```

Add or extend integration coverage for any missing task payload fields needed by the UI.

**Step 2: Run the tests to verify they fail**

Run:

```bash
npm --prefix ui test -- TaskDetailPage.test.tsx
source .venv/bin/activate && python -m pytest tests/integration/test_http_task_api.py -q
```

Expected: FAIL because the task workspace screens do not exist.

**Step 3: Write minimal implementation**

Implement:

1. tasks landing page with:
   - create task form
   - task list filtered to current agent
   - explicit empty state
2. task detail page with:
   - status/phase
   - latest validation summary
   - repair summary
   - result resource links
3. task actions:
   - revise
   - retry
   - cancel
4. polling for active tasks with sensible backoff

**Step 4: Run the tests to verify they pass**

Run:

```bash
npm --prefix ui test -- TaskDetailPage.test.tsx
source .venv/bin/activate && python -m pytest tests/integration/test_http_task_api.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui tests/integration/test_http_task_api.py
git commit -m "feat: add task workspace ui"
```

### Task 4: Add memory and profile management screens

**Files:**
- Create: `ui/src/features/memory/MemoryPage.tsx`
- Create: `ui/src/features/profile/ProfilePage.tsx`
- Create: `ui/src/features/profile/ProfileScorecard.tsx`
- Create: `ui/src/features/profile/ProfilePage.test.tsx`
- Modify: `ui/src/lib/api.ts`
- Modify: `ui/src/app/router.tsx`
- Test: `tests/integration/test_http_memory_api.py`
- Test: `tests/integration/test_http_profile_api.py`

**Step 1: Write the failing tests**

Create `ui/src/features/profile/ProfilePage.test.tsx`:

```tsx
test("renders current profile, scorecard, and apply-patch form", async () => {
  // mock /api/profile and /api/profile/scorecard
  // assert current tone plus scorecard metrics
});
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
npm --prefix ui test -- ProfilePage.test.tsx
source .venv/bin/activate && python -m pytest tests/integration/test_http_memory_api.py tests/integration/test_http_profile_api.py -q
```

Expected: FAIL because the memory/profile screens do not exist yet.

**Step 3: Write minimal implementation**

Implement:

1. session memory page:
   - current session summary
   - clear session action
   - promote-to-persistent affordance
2. persistent memory page section:
   - list
   - disable action
   - useful summaries, not raw JSON dumps
3. profile page:
   - current resolved profile view
   - patch form for `style_hints`, `output_profile`, `validation_profile`
   - scorecard metrics

**Step 4: Run the tests to verify they pass**

Run:

```bash
npm --prefix ui test -- ProfilePage.test.tsx
source .venv/bin/activate && python -m pytest tests/integration/test_http_memory_api.py tests/integration/test_http_profile_api.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui tests/integration/test_http_memory_api.py tests/integration/test_http_profile_api.py
git commit -m "feat: add memory and profile workspace ui"
```

### Task 5: Add suggestion review and eval history screens

**Files:**
- Create: `ui/src/features/profile/SuggestionsPanel.tsx`
- Create: `ui/src/features/evals/EvalsPage.tsx`
- Create: `ui/src/features/evals/EvalDetailPage.tsx`
- Create: `ui/src/features/evals/EvalsPage.test.tsx`
- Modify: `ui/src/app/router.tsx`
- Modify: `ui/src/lib/api.ts`
- Test: `tests/integration/test_http_profile_suggestions_api.py`
- Test: `tests/integration/test_agent_profile_auto_apply.py`
- Test: `tests/integration/test_http_profile_api.py`

**Step 1: Write the failing tests**

Create `ui/src/features/evals/EvalsPage.test.tsx`:

```tsx
test("lists eval runs and opens an agent-scoped eval detail page", async () => {
  // mock /api/profile/evals and /api/profile/evals/{run_id}
  // assert summary cards and detail navigation
});
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
npm --prefix ui test -- EvalsPage.test.tsx
source .venv/bin/activate && python -m pytest tests/integration/test_http_profile_suggestions_api.py tests/integration/test_agent_profile_auto_apply.py tests/integration/test_http_profile_api.py -q
```

Expected: FAIL because these UI views do not exist yet.

**Step 3: Write minimal implementation**

Implement:

1. suggestion review UI:
   - generate suggestions
   - view rationale and patch preview
   - apply/dismiss actions
   - auto-applied badge when status is `applied`
2. eval history UI:
   - list past runs
   - show success rate and active profile digest
   - show detail page with `Agent Slice`, `Quality Slice`, and failures

**Step 4: Run the tests to verify they pass**

Run:

```bash
npm --prefix ui test -- EvalsPage.test.tsx
source .venv/bin/activate && python -m pytest tests/integration/test_http_profile_suggestions_api.py tests/integration/test_agent_profile_auto_apply.py tests/integration/test_http_profile_api.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui tests/integration/test_http_profile_suggestions_api.py tests/integration/test_agent_profile_auto_apply.py tests/integration/test_http_profile_api.py
git commit -m "feat: add suggestion and eval review ui"
```

### Task 6: Harden responsive behavior, accessibility, and deployment path

**Files:**
- Create: `ui/playwright.config.ts`
- Create: `ui/tests/e2e/login-task-flow.spec.ts`
- Create: `ui/tests/e2e/profile-evals-flow.spec.ts`
- Modify: `README.md`
- Modify: `docs/runbooks/local-dev.md`
- Modify: `docs/runbooks/http-api-deploy.md`
- Modify: `tests/e2e/test_http_session_flow.py`

**Step 1: Write the failing end-to-end tests**

Create `ui/tests/e2e/login-task-flow.spec.ts`:

```ts
test("logs in, creates a task, and views the result", async ({ page }) => {
  // login through the web UI
  // create task
  // wait for terminal status
  // assert result summary
});
```

Create `ui/tests/e2e/profile-evals-flow.spec.ts`:

```ts
test("reviews profile suggestions and eval history", async ({ page }) => {
  // navigate to profile/evals
  // assert suggestion actions and eval details render
});
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
npm --prefix ui test
npm --prefix ui run e2e
source .venv/bin/activate && python -m pytest tests/e2e/test_http_session_flow.py -q
```

Expected: FAIL until the UI and docs match the real operator flow.

**Step 3: Write minimal implementation**

Harden:

1. responsive navigation for smaller screens
2. keyboard-visible focus states and semantic landmarks
3. empty/loading/error states across all major screens
4. deployment docs for:
   - local UI + API dev
   - operator login flow
   - token provisioning
   - same-origin vs separate-origin considerations

**Step 4: Run the tests to verify they pass**

Run:

```bash
npm --prefix ui test
npm --prefix ui run e2e
source .venv/bin/activate && python -m pytest tests/e2e/test_http_session_flow.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui README.md docs/runbooks/local-dev.md docs/runbooks/http-api-deploy.md tests/e2e/test_http_session_flow.py
git commit -m "feat: ship first human operator console"
```

## Acceptance Criteria

The next stage is complete when all of the following are true:

1. A real frontend workspace exists under `ui/`.
2. A human can log in with an issued agent token and receive a persistent UI session.
3. A human can create, inspect, revise, retry, and cancel tasks without leaving the browser.
4. Session memory, persistent memory, profile data, suggestions, and eval summaries are visible in the UI.
5. The UI works on desktop and narrow tablet/mobile widths without horizontal overflow.
6. The UI does not look like generic AI slop; it has a clear visual point of view and passes a basic audit/critique review.
7. Frontend unit tests and browser e2e tests run in CI.
8. Docs explain how to run the UI locally with the existing API.

## Recommended Command Sequence For Final Verification

```bash
npm --prefix ui install
npm --prefix ui test
npm --prefix ui run build
npm --prefix ui run e2e
source .venv/bin/activate && python -m pytest tests/e2e/test_http_session_flow.py -q
source .venv/bin/activate && python -m pytest -q
```
