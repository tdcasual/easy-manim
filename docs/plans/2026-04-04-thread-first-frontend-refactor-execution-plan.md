# Thread-First Frontend Refactor Execution Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the frontend so the thread page is the canonical video collaboration workspace and task pages become operator/task shells instead of parallel collaboration surfaces.

**Architecture:** The thread page should be rebuilt around a two-level data model: thread surface as page truth and selected iteration detail as inspected-iteration truth. The primary review flow should stay shallow and owner-facing, while process-heavy runtime panels move into a collapsed secondary operator layer.

**Tech Stack:** React, React Router, TypeScript, Vitest, Testing Library, Vite

---

## Context

Use these documents before implementation:

- [thread-first-frontend-refactor-guide.md](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/docs/runbooks/thread-first-frontend-refactor-guide.md)
- [thread-first-frontend-todo-checklist.md](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/docs/runbooks/thread-first-frontend-todo-checklist.md)
- [video-thread-surface-contract.md](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/docs/runbooks/video-thread-surface-contract.md)

Use these implementation references:

- [App.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/app/App.tsx)
- [VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)
- [SelectedVersionHero.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/SelectedVersionHero.tsx)
- [ThreadDiscussionPanel.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/ThreadDiscussionPanel.tsx)
- [VersionTimeline.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VersionTimeline.tsx)
- [ProcessDetailsAccordion.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/ProcessDetailsAccordion.tsx)
- [VideoThreadWorkbench.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadWorkbench.tsx)
- [videoThreadsApi.ts](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/lib/videoThreadsApi.ts)
- [TaskDetailPageV2.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/tasks/TaskDetailPageV2.tsx)

## Execution Rules

- Follow TDD for every behavior change: failing test, verify red, minimal implementation, verify green.
- Keep task detail and thread detail responsibilities separate.
- Do not add client-side inference when the backend surface already projects the meaning.
- Prefer small commits after each task.

### Task 1: Lock Route Ownership

**Files:**
- Modify: [ui/src/app/App.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/app/App.tsx)
- Modify: [ui/src/app/App.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/app/App.test.tsx)
- Test: [ui/src/features/tasks/TaskDetailPageV2.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/tasks/TaskDetailPageV2.test.tsx)

**Step 1: Write the failing tests**

- Add or update the route-level test so authenticated access to `/threads/:threadId` renders the thread page.
- Add or update the task detail test so a task with `thread_id` links to `/threads/:threadId`.

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- src/app/App.test.tsx src/features/tasks/TaskDetailPageV2.test.tsx
```

Expected:

- one or more assertions fail because old route or old task-detail wording still exists

**Step 3: Write minimal implementation**

- Ensure `/threads/:threadId` is present as the canonical route in `App.tsx`
- Keep `/videos/:threadId` only as compatibility
- Update task detail copy so the thread page is framed as the canonical workspace

**Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix ui test -- src/app/App.test.tsx src/features/tasks/TaskDetailPageV2.test.tsx
```

Expected:

- all targeted tests pass

**Step 5: Commit**

```bash
git add ui/src/app/App.tsx ui/src/app/App.test.tsx ui/src/features/tasks/TaskDetailPageV2.tsx ui/src/features/tasks/TaskDetailPageV2.test.tsx
git commit -m "refactor: make thread route the canonical collaboration entry"
```

### Task 2: Centralize Thread Page Orchestration

**Files:**
- Modify: [ui/src/features/videoThreads/VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)
- Modify: [ui/src/lib/videoThreadsApi.ts](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/lib/videoThreadsApi.ts)
- Test: [ui/src/features/videoThreads/VideoThreadPage.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.test.tsx)

**Step 1: Write the failing test**

- Add a thread page test that proves page-level orchestration owns:
  - initial surface fetch
  - selected iteration detail fetch
  - refresh after mutation
  - current title at top of page

**Step 2: Run test to verify it fails**

Run:

```bash
npm --prefix ui test -- src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected:

- test fails because orchestration is split incorrectly or title/state ownership is missing

**Step 3: Write minimal implementation**

- Keep fetch logic in `VideoThreadPage`
- Keep derived state in `VideoThreadPage`
- Ensure thread title is visible at page top independent of operator panel state
- Keep child components mostly presentational

**Step 4: Run test to verify it passes**

Run:

```bash
npm --prefix ui test -- src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected:

- targeted thread tests pass

**Step 5: Commit**

```bash
git add ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/lib/videoThreadsApi.ts ui/src/features/videoThreads/VideoThreadPage.test.tsx
git commit -m "refactor: centralize thread page orchestration"
```

### Task 3: Rebuild The Primary Review Flow

**Files:**
- Modify: [ui/src/features/videoThreads/SelectedVersionHero.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/SelectedVersionHero.tsx)
- Modify: [ui/src/features/videoThreads/ThreadDiscussionPanel.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/ThreadDiscussionPanel.tsx)
- Modify: [ui/src/features/videoThreads/VersionTimeline.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VersionTimeline.tsx)
- Modify: [ui/src/features/videoThreads/VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)
- Test: [ui/src/features/videoThreads/VideoThreadPage.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.test.tsx)

**Step 1: Write the failing tests**

- Add or update tests proving:
  - selected version appears before discussion
  - discussion appears before versions
  - versions stay visible without opening any operator panel
  - version downloads resolve from the current selected result task

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- src/features/videoThreads/VideoThreadPage.test.tsx -t "video thread page renders the collaboration workbench from thread surface|video thread page shows version cards with select and task actions"
```

Expected:

- ordering or download assertions fail

**Step 3: Write minimal implementation**

- Keep `SelectedVersionHero` focused on selected version summary plus downloads
- Keep `ThreadDiscussionPanel` focused on active discussion and submit controls
- Keep `VersionTimeline` focused on iteration results plus per-version actions
- Render them in the order:
  - thread header
  - selected version
  - discussion
  - versions

**Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix ui test -- src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected:

- thread page tests pass for primary review flow

**Step 5: Commit**

```bash
git add ui/src/features/videoThreads/SelectedVersionHero.tsx ui/src/features/videoThreads/ThreadDiscussionPanel.tsx ui/src/features/videoThreads/VersionTimeline.tsx ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/features/videoThreads/VideoThreadPage.test.tsx
git commit -m "feat: rebuild thread page primary review flow"
```

### Task 4: Move Operator Detail Behind Disclosure

**Files:**
- Create: [ui/src/features/videoThreads/ProcessDetailsAccordion.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/ProcessDetailsAccordion.tsx)
- Modify: [ui/src/features/videoThreads/VideoThreadWorkbench.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadWorkbench.tsx)
- Modify: [ui/src/features/videoThreads/VideoThreadWorkbench.css](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadWorkbench.css)
- Modify: [ui/src/features/videoThreads/VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)
- Test: [ui/src/features/videoThreads/VideoThreadPage.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.test.tsx)

**Step 1: Write the failing tests**

- Add or update tests proving:
  - process details are collapsed by default
  - participant controls are not visible until expanded
  - history/process/operator content becomes visible after expand

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- src/features/videoThreads/VideoThreadPage.test.tsx -t "video thread page renders the collaboration workbench from thread surface|video thread page invites and removes participants from the owner panel"
```

Expected:

- no disclosure control exists yet or operator content is visible too early

**Step 3: Write minimal implementation**

- Add `ProcessDetailsAccordion`
- Place `VideoThreadWorkbench` inside it
- Default accordion closed
- Remove duplicate header from the embedded operator workbench
- Keep the main page title outside the accordion

**Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix ui test -- src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected:

- process-details behavior is green

**Step 5: Commit**

```bash
git add ui/src/features/videoThreads/ProcessDetailsAccordion.tsx ui/src/features/videoThreads/VideoThreadWorkbench.tsx ui/src/features/videoThreads/VideoThreadWorkbench.css ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/features/videoThreads/VideoThreadPage.test.tsx
git commit -m "refactor: demote operator detail behind process disclosure"
```

### Task 5: Stabilize Thread-Native Mutation Semantics

**Files:**
- Modify: [ui/src/features/videoThreads/VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)
- Modify: [ui/src/lib/videoThreadsApi.ts](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/lib/videoThreadsApi.ts)
- Test: [ui/src/features/videoThreads/VideoThreadPage.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.test.tsx)
- Test: [ui/src/lib/videoThreadsApi.test.ts](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/lib/videoThreadsApi.test.ts)

**Step 1: Write the failing tests**

- Add or update tests proving:
  - request revision uses selected iteration id
  - request explanation uses selected iteration id
  - add note uses addressed participant, reply-to turn, and related result
  - result selection refreshes both surface and current iteration detail

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- src/lib/videoThreadsApi.test.ts src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected:

- request payload or refresh assertions fail

**Step 3: Write minimal implementation**

- Keep all collaboration mutations thread-native
- Refresh surface after success
- Refresh selected iteration detail when iteration-scoped state changed

**Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix ui test -- src/lib/videoThreadsApi.test.ts src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected:

- thread-native mutation coverage is green

**Step 5: Commit**

```bash
git add ui/src/lib/videoThreadsApi.ts ui/src/lib/videoThreadsApi.test.ts ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/features/videoThreads/VideoThreadPage.test.tsx
git commit -m "fix: stabilize thread-native mutation routing"
```

### Task 6: Final Regression And Polish

**Files:**
- Modify as needed: [ui/src/features/videoThreads/VideoThreadWorkbench.css](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadWorkbench.css)
- Modify as needed: [ui/src/features/tasks/TaskDetailPageV2.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/tasks/TaskDetailPageV2.tsx)
- Modify as needed: [ui/src/features/videoThreads/VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)
- Test: [ui/src/features/tasks/TaskDetailPageV2.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/tasks/TaskDetailPageV2.test.tsx)
- Test: [ui/src/features/videoThreads/VideoThreadPage.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.test.tsx)

**Step 1: Write any missing regression test**

- Add one final regression only if a polish fix changes behavior

**Step 2: Run targeted tests**

Run:

```bash
npm --prefix ui test -- src/features/tasks/TaskDetailPageV2.test.tsx src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected:

- both suites pass

**Step 3: Run full frontend verification**

Run:

```bash
npm --prefix ui test
npm --prefix ui run build
```

Expected:

- all Vitest suites pass
- TypeScript and Vite build succeed

**Step 4: Commit**

```bash
git add ui/src/features/tasks/TaskDetailPageV2.tsx ui/src/features/tasks/TaskDetailPageV2.test.tsx ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/features/videoThreads/VideoThreadPage.test.tsx ui/src/features/videoThreads/VideoThreadWorkbench.css ui/src/features/videoThreads/VideoThreadWorkbench.tsx ui/src/features/videoThreads/ProcessDetailsAccordion.tsx
git commit -m "polish: finalize thread-first frontend collaboration flow"
```

## Completion Checklist

- `/threads/:threadId` is the main collaboration page
- task detail points to the thread workspace instead of duplicating collaboration
- selected version is the first thing the owner sees
- discussion is directly under the selected version
- versions stay first-class and visible
- dense process details are available but collapsed by default
- all collaboration writes are thread-native
- full frontend test and build verification pass

Plan complete and saved to `docs/plans/2026-04-04-thread-first-frontend-refactor-execution-plan.md`.
