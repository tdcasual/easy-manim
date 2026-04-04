# Thread-First Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the human-facing video experience around `thread -> iteration -> result`, with the thread page becoming the canonical video detail page and task detail reduced to an operator/debug shell.

**Architecture:** Keep the existing backend contract and reuse the current `/api/video-threads/*` projection model as the frontend source of truth. Refactor the UI by promoting the current video thread page into a player-first detail page, introducing explicit selected-version and version-list components, and using `source_task_id -> /api/tasks/{taskId}/result` as the bridge for per-version downloads.

**Tech Stack:** React 18, TypeScript, React Router, Vite, Vitest, existing `requestJson` API layer, existing CSS modules/files in `ui/src/features/*`.

---

### Task 1: Establish Canonical Thread Routing

**Files:**
- Modify: `ui/src/app/App.tsx`
- Modify: `ui/src/features/videos/VideosPageV2.tsx`
- Test: `ui/src/features/videos/VideosPageV2.test.tsx`
- Test: `ui/src/app/App.test.tsx`

**Step 1: Write the failing tests**

Add route expectations for thread-first navigation.

```tsx
expect(screen.getByRole("link", { name: /view details/i })).toHaveAttribute(
  "href",
  "/threads/thread-target-001"
);
```

Add route coverage that `/threads/:threadId` renders the thread page and `/videos/:threadId` can stay as a transition alias.

```tsx
<Route path="/threads/:threadId" element={<div>Thread route placeholder</div>} />
```

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- ui/src/features/videos/VideosPageV2.test.tsx ui/src/app/App.test.tsx
```

Expected: FAIL because the app still routes canonical thread links through `/videos/:threadId`.

**Step 3: Write the minimal implementation**

Update routing so thread detail has a canonical route and the gallery links point to it.

```tsx
<Route path="/threads/:threadId" element={<VideoThreadPageLazy />} />
<Route path="/videos/:threadId" element={<Navigate to="/threads/:threadId" replace />} />
```

Update the list/detail href logic in `VideosPageV2.tsx`:

```tsx
const detailHref = video.thread_id
  ? `/threads/${encodeURIComponent(video.thread_id)}`
  : `/tasks/${encodeURIComponent(video.task_id)}`;
```

**Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix ui test -- ui/src/features/videos/VideosPageV2.test.tsx ui/src/app/App.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui/src/app/App.tsx ui/src/features/videos/VideosPageV2.tsx ui/src/features/videos/VideosPageV2.test.tsx ui/src/app/App.test.tsx
git commit -m "feat: add canonical thread routes"
```

### Task 2: Create Selected Version Hero State And Downloads

**Files:**
- Modify: `ui/src/lib/tasksApi.ts`
- Create: `ui/src/features/videoThreads/useTaskArtifactDownloads.ts`
- Create: `ui/src/features/videoThreads/SelectedVersionHero.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadPage.tsx`
- Test: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`
- Test: `ui/src/lib/tasksApi.test.ts`

**Step 1: Write the failing tests**

Add task API coverage for script and validation download URLs.

```tsx
expect(result.script_download_url).toBe("/api/tasks/task-1/artifacts/current_script.py");
expect(result.validation_report_download_url).toBe(
  "/api/tasks/task-1/artifacts/validations/validation_report_v1.json"
);
```

Add thread page tests asserting the selected hero shows:

- selected result summary
- version identity
- download buttons
- fallback behavior when there is no selected result

```tsx
expect(screen.getByRole("button", { name: /download video/i })).toBeInTheDocument();
expect(screen.getByText(/selected result/i)).toBeInTheDocument();
```

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- ui/src/features/videoThreads/VideoThreadPage.test.tsx ui/src/lib/tasksApi.test.ts
```

Expected: FAIL because the thread page does not yet resolve per-version artifact downloads.

**Step 3: Write the minimal implementation**

Extend the frontend task result type:

```ts
export type TaskResult = {
  task_id: string;
  video_download_url?: string | null;
  script_download_url?: string | null;
  validation_report_download_url?: string | null;
  preview_download_urls?: string[] | null;
};
```

Create a small download hook keyed by `task_id`:

```ts
export function useTaskArtifactDownloads(taskId: string | null, token: string | null) {
  // fetch getTaskResult(taskId, token), cache by task id, expose loading/error/data
}
```

Add a hero component:

```tsx
export function SelectedVersionHero({ selectedResult, downloads, threadTitle }: Props) {
  return (
    <section>
      <h1>{threadTitle}</h1>
      <p>{selectedResult?.result_summary || "No selected version yet."}</p>
    </section>
  );
}
```

Wire `VideoThreadPage.tsx` to derive:

- selected iteration
- selected result from `iterationDetail.results`
- `source_task_id`
- task artifact downloads for the selected result

**Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix ui test -- ui/src/features/videoThreads/VideoThreadPage.test.tsx ui/src/lib/tasksApi.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui/src/lib/tasksApi.ts ui/src/features/videoThreads/useTaskArtifactDownloads.ts ui/src/features/videoThreads/SelectedVersionHero.tsx ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/features/videoThreads/VideoThreadPage.test.tsx ui/src/lib/tasksApi.test.ts
git commit -m "feat: add selected version hero and downloads"
```

### Task 3: Move Discussion Under The Video And Make Composer Explicit

**Files:**
- Create: `ui/src/features/videoThreads/ThreadDiscussionPanel.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadPage.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.css`
- Test: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`

**Step 1: Write the failing tests**

Add thread page tests that assert:

- composer renders below selected version content
- default composer mode follows `surface.actions`
- submit routes to:
  - `appendVideoTurn`
  - `requestVideoExplanation`
  - `requestVideoRevision`

```tsx
expect(screen.getByPlaceholderText(/ask why this version was made or request the next change/i)).toBeInTheDocument();
```

Add assertions that the composer context shows iteration/result target metadata.

```tsx
expect(screen.getByText(/reply to/i)).toBeInTheDocument();
expect(screen.getByText(/result:/i)).toBeInTheDocument();
```

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- ui/src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected: FAIL because the page still presents the thread workbench as a broad operator surface instead of an anchored player-plus-discussion layout.

**Step 3: Write the minimal implementation**

Extract discussion rendering into a dedicated panel:

```tsx
export function ThreadDiscussionPanel({ groups, runtime, draft, onDraftChange, onSubmit }: Props) {
  return (
    <section>
      <h2>Discussion</h2>
      <p>{runtime.active_thread_summary}</p>
    </section>
  );
}
```

Keep `VideoThreadWorkbench.tsx` for lower-level process views, but remove responsibility for top-level composer placement.

In `VideoThreadPage.tsx`, render order should become:

```tsx
<SelectedVersionHero ... />
<ThreadDiscussionPanel ... />
<VideoThreadWorkbench ... />
```

**Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix ui test -- ui/src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui/src/features/videoThreads/ThreadDiscussionPanel.tsx ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/features/videoThreads/VideoThreadWorkbench.tsx ui/src/features/videoThreads/VideoThreadWorkbench.css ui/src/features/videoThreads/VideoThreadPage.test.tsx
git commit -m "feat: anchor discussion below selected version"
```

### Task 4: Make Versions First-Class With Select And Download Actions

**Files:**
- Create: `ui/src/features/videoThreads/VersionTimeline.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadPage.tsx`
- Modify: `ui/src/lib/videoThreadsApi.ts`
- Test: `ui/src/lib/videoThreadsApi.test.ts`
- Test: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`

**Step 1: Write the failing tests**

Add API test coverage for `selectVideoResult`.

```ts
await selectVideoResult("thread-1", "iter-1", { result_id: "result-2" }, "sess-token-1");
expect(requestLog).toContain("POST /api/video-threads/thread-1/iterations/iter-1/select-result");
```

Add thread page tests asserting each result card can:

- show selected state
- trigger select result
- open task detail
- show download controls when `source_task_id` exists

```tsx
expect(screen.getByRole("button", { name: /set as current version/i })).toBeInTheDocument();
```

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- ui/src/lib/videoThreadsApi.test.ts ui/src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected: FAIL because the current results section is read-only text.

**Step 3: Write the minimal implementation**

Create a version list component:

```tsx
export function VersionTimeline({ results, selectedResultId, onSelectResult }: Props) {
  return results.map((result) => (
    <article key={result.result_id}>
      <strong>{result.result_id}</strong>
      <button onClick={() => onSelectResult(result.result_id)}>Set as current version</button>
    </article>
  ));
}
```

In `VideoThreadPage.tsx`, wire `selectVideoResult` and refresh surface/iteration detail after selection.

Use `source_task_id` to lazily resolve per-version downloads.

**Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix ui test -- ui/src/lib/videoThreadsApi.test.ts ui/src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui/src/features/videoThreads/VersionTimeline.tsx ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/lib/videoThreadsApi.ts ui/src/lib/videoThreadsApi.test.ts ui/src/features/videoThreads/VideoThreadPage.test.tsx
git commit -m "feat: add version timeline and selection controls"
```

### Task 5: Demote Task Detail To Operator Shell

**Files:**
- Modify: `ui/src/features/tasks/TaskDetailPageV2.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.css`
- Test: `ui/src/features/tasks/TaskDetailPageV2.test.tsx`

**Step 1: Write the failing tests**

Add tests asserting task detail:

- still shows task lifecycle/review controls
- links prominently to thread detail using `/threads/:threadId`
- no longer tries to serve as a collaboration page

```tsx
expect(screen.getByRole("link", { name: /open thread workspace/i })).toHaveAttribute(
  "href",
  "/threads/thread-99"
);
```

Add negative assertions for top-level discussion copy.

```tsx
expect(screen.queryByText(/video collaboration workbench/i)).not.toBeInTheDocument();
```

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- ui/src/features/tasks/TaskDetailPageV2.test.tsx
```

Expected: FAIL because task detail still treats the thread workbench link as a side panel inside the task page.

**Step 3: Write the minimal implementation**

Reframe the thread link card:

```tsx
<h3>Thread workspace</h3>
<p>Open the canonical video page for discussion, versions, and revision history.</p>
<Link to={`/threads/${encodeURIComponent(snapshot.thread_id)}`}>Open thread workspace</Link>
```

Keep the rest of the page focused on:

- task status
- player/debug artifacts
- review bundle actions
- task mutations

**Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix ui test -- ui/src/features/tasks/TaskDetailPageV2.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui/src/features/tasks/TaskDetailPageV2.tsx ui/src/features/tasks/TaskDetailPageV2.css ui/src/features/tasks/TaskDetailPageV2.test.tsx
git commit -m "refactor: demote task detail to operator shell"
```

### Task 6: Convert The Thread Page From Workbench To Canonical Product Detail

**Files:**
- Modify: `ui/src/features/videoThreads/VideoThreadPage.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.css`
- Create: `ui/src/features/videoThreads/ProcessDetailsAccordion.tsx`
- Test: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`

**Step 1: Write the failing tests**

Add thread page assertions for the final page hierarchy:

- selected version hero first
- discussion second
- versions/iterations visible without scrolling into process internals
- process details collapsed or visually secondary

```tsx
expect(screen.getByRole("heading", { name: /discussion/i })).toBeInTheDocument();
expect(screen.getByRole("heading", { name: /versions/i })).toBeInTheDocument();
expect(screen.getByRole("button", { name: /process details/i })).toBeInTheDocument();
```

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- ui/src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected: FAIL because operator/process panels are still presented at the same level as user-facing playback and version controls.

**Step 3: Write the minimal implementation**

Use a product-first page composition:

```tsx
<div className="thread-detail-page">
  <SelectedVersionHero ... />
  <div className="thread-detail-page__main">
    <ThreadDiscussionPanel ... />
    <VersionTimeline ... />
  </div>
  <ProcessDetailsAccordion>
    <VideoThreadWorkbench ... />
  </ProcessDetailsAccordion>
</div>
```

Keep `VideoThreadWorkbench.tsx` focused on:

- artifact lineage
- rationale snapshots
- production journal
- participant runtime
- raw iteration detail

**Step 4: Run tests to verify they pass**

Run:

```bash
npm --prefix ui test -- ui/src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/features/videoThreads/VideoThreadWorkbench.tsx ui/src/features/videoThreads/VideoThreadWorkbench.css ui/src/features/videoThreads/ProcessDetailsAccordion.tsx ui/src/features/videoThreads/VideoThreadPage.test.tsx
git commit -m "refactor: make thread page the canonical video detail view"
```

### Task 7: Final Verification And Cleanup

**Files:**
- Modify: `ui/src/app/locale.tsx`
- Modify: `ui/src/features/videos/VideosPageV2.css`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.css`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.css`
- Test: `ui/src/features/videos/VideosPageV2.css.test.ts`
- Test: `ui/src/app/App.css.test.ts`

**Step 1: Write the failing tests**

Add or update text and style assertions so the UI copy matches the thread-first model.

```tsx
expect(screen.getByText(/thread workspace/i)).toBeInTheDocument();
expect(screen.getByText(/selected version/i)).toBeInTheDocument();
```

**Step 2: Run tests to verify they fail**

Run:

```bash
npm --prefix ui test -- ui/src/features/videos/VideosPageV2.css.test.ts ui/src/app/App.css.test.ts
```

Expected: FAIL if legacy copy or styles still encode the old split mental model.

**Step 3: Write the minimal implementation**

Update copy and styling for:

- `videos` list labels
- thread page hero and versions section
- task detail secondary link card
- responsive stacking for hero/discussion/version layout

Keep CSS changes incremental and localized to existing feature files.

**Step 4: Run the full frontend test suite**

Run:

```bash
npm --prefix ui test
npm --prefix ui run build
```

Expected: PASS

**Step 5: Commit**

```bash
git add ui/src/app/locale.tsx ui/src/features/videos/VideosPageV2.css ui/src/features/videoThreads/VideoThreadWorkbench.css ui/src/features/tasks/TaskDetailPageV2.css ui/src/features/videos/VideosPageV2.css.test.ts ui/src/app/App.css.test.ts
git commit -m "chore: polish thread-first frontend experience"
```

## Notes For Execution

- Do not introduce a backend dependency for thread-native download URLs in this plan. Use `source_task_id` plus `getTaskResult` as the first shipping path.
- Preserve existing `/tasks/:taskId` review and operator workflows.
- Prefer extracting new components from `VideoThreadPage.tsx` rather than rewriting the page in one large diff.
- Keep `VideoThreadWorkbench.tsx` alive as the process/debug layer so current projection richness is not lost.
- If routing aliases complicate `Navigate`, implement both `/threads/:threadId` and `/videos/:threadId` temporarily against the same page component first, then tighten redirects later.

## Suggested Execution Order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Task 6
7. Task 7

Plan complete and saved to `docs/plans/2026-04-03-thread-first-frontend-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
