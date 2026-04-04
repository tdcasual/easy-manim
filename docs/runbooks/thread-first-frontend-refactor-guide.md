# Thread-First Frontend Refactor Guide

This guide is for frontend reconstruction against the current thread-native backend and the validated UI behavior now implemented in the app.

Read this together with [video-thread-surface-contract.md](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/docs/runbooks/video-thread-surface-contract.md). The contract explains backend truth. This guide explains how the frontend should be organized around that truth.

## Product Decision

The canonical collaboration page is now the thread page, not the task page.

- Canonical route: `/threads/:threadId`
- Compatibility route: `/videos/:threadId`
- Task detail is an operator shell and jump-off point only
- Discussion, version switching, revision history, and participant continuity belong to the thread page
- Per-version download remains available from the thread page because each visible version maps back to its source task artifact

## Page Model

The frontend should treat the thread page as one page with two layers:

1. Primary review layer
2. Secondary operator layer

Primary review layer order:

1. Thread header
2. Selected version hero
3. Discussion panel
4. Versions timeline

Secondary operator layer:

1. Process details accordion
2. Everything operational and dense lives inside it

This is intentional. The owner-facing task on this page is:

1. See the current chosen cut
2. Understand or discuss it
3. Compare with other versions
4. Only then inspect deeper runtime/process detail if needed

## Route Responsibilities

### `/threads/:threadId`

This route owns:

- current selected version display
- version switching
- grouped discussion under the video
- request revision / ask why / add note actions
- per-version task drill-down and artifact download
- iteration browsing
- process/history inspection
- participant management

### `/tasks/:taskId`

This route owns:

- task execution status
- video playback for that task result
- retry / cancel / revise task controls
- workflow review controls
- link into the thread workspace when `thread_id` exists

This route should not re-implement:

- discussion UI
- version timeline UI
- collaboration history UI
- participant continuity UI

## Frontend Authority Rules

The frontend should stop inferring collaboration semantics from raw task state.

Use these authorities directly:

- “What page am I reviewing?” -> `surface.thread_header`
- “What version is current?” -> `surface.current_focus` plus selected iteration detail result
- “Why is this version current?” -> `surface.selection_summary`
- “What did the agent most recently explain?” -> `surface.latest_explanation`
- “What should the owner do next?” -> `surface.next_recommended_move`
- “Which discussion is active?” -> `surface.discussion_runtime`
- “Where will the next submit land?” -> `surface.composer.target` or `iterationDetail.composer_target`
- “Which version cards exist?” -> `iterationDetail.results`
- “Which iteration am I inspecting?” -> `selectedIterationId`
- “What happened in that iteration?” -> `GET /api/video-threads/{threadId}/iterations/{iterationId}`
- “Who is expected next?” -> `surface.participant_runtime`
- “Which operator/process panels exist?” -> `surface.render_contract`

Do not derive these from:

- task lineage
- legacy task discussion endpoints
- ad hoc joins across task result plus thread summary
- local frontend ranking heuristics

## Data Fetching Model

The page should use a two-level fetch model.

### Level 1: Thread surface

Fetch once on page load and refresh after mutations:

- `GET /api/video-threads/:threadId/surface`

This powers:

- header
- selected version fallback summary
- discussion shell
- participant runtime
- recommendation panels
- operator summary

### Level 2: Iteration detail

Fetch whenever the inspected iteration changes:

- `GET /api/video-threads/:threadId/iterations/:iterationId`

This powers:

- concrete version cards for that iteration
- exact result selection state
- submit routing for that iteration
- visible turns / runs / results in the operator layer

### Download resolution

Downloads are still task-artifact based.

- Convert `video-task://{taskId}/...` to `taskId`
- Use `selectedResult.video_resource` as the first source of truth
- Fall back to iteration run task id or production journal task id only when necessary

## Recommended Component Tree

Suggested top-level split:

- `VideoThreadPage`
- `ThreadHeader`
- `SelectedVersionHero`
- `ThreadDiscussionPanel`
- `VersionTimeline`
- `ProcessDetailsAccordion`
- `VideoThreadWorkbench`

Suggested responsibility split:

### `VideoThreadPage`

Own only orchestration:

- route param
- `surface`
- `iterationDetail`
- `selectedIterationId`
- active composer action
- request in-flight states
- refresh logic after mutations
- task artifact download resolution

### `SelectedVersionHero`

Render only:

- selected result summary
- selected result id
- selected iteration id
- source task id
- video/script/validation downloads

This component should not know discussion rules.

### `ThreadDiscussionPanel`

Render only:

- current active discussion summary
- reply target
- grouped discussion clusters
- conversation turns
- action mode buttons
- composer textarea and submit button

This component should not inspect task data directly.

### `VersionTimeline`

Render only iteration-scoped visible results:

- result cards
- selected/current badge
- set-as-current action
- open task detail
- download video/script

It should not own global discussion state.

### `ProcessDetailsAccordion`

Own only disclosure UI:

- collapsed summary chips
- show/hide button
- operator content mount

### `VideoThreadWorkbench`

This is the dense operator shell. Keep it secondary.

It can render:

- current focus
- decision notes
- artifact lineage
- rationale snapshots
- iteration compare
- authorship
- production journal
- participant runtime
- history
- iteration selector
- iteration detail
- process runs
- participants and management

## State Ownership

Keep state flat and explicit.

Suggested page state:

- `surface: VideoThreadSurface | null`
- `iterationDetail: VideoThreadIterationDetail | null`
- `selectedIterationId: string | null`
- `activeActionId: string | null`
- `draft: string`
- `error: string | null`
- `iterationLoading: boolean`
- `submitting: boolean`
- `selectingResultId: string | null`
- `participantSubmitting: boolean`
- `participantDraft`

Avoid introducing duplicated derived state for:

- selected result summary
- active reply target
- expected participant
- current version reason

Those should stay derived from `surface` plus `iterationDetail`.

## Mutation Model

The frontend should mutate through thread-native endpoints only.

### Submit discussion

- `POST /api/video-threads/:threadId/turns`

Payload should include:

- `iteration_id`
- `title`
- `summary`
- `addressed_participant_id`
- `reply_to_turn_id`
- `related_result_id`

### Request revision

- `POST /api/video-threads/:threadId/iterations/:iterationId/request-revision`

### Request explanation

- `POST /api/video-threads/:threadId/iterations/:iterationId/request-explanation`

### Select result

- `POST /api/video-threads/:threadId/iterations/:iterationId/select-result`

### Manage participants

- `POST /api/video-threads/:threadId/participants`
- `DELETE /api/video-threads/:threadId/participants/:participantId`

After each successful mutation:

1. refresh surface
2. refresh selected iteration detail when the mutation affects iteration-scoped data

## UX Rules For Rebuild

If the frontend is rewritten, preserve these rules:

- Always show the thread title at page top, even when operator details are collapsed
- Always show selected version before any operator/process blocks
- Discussion stays directly under the selected version
- Versions must remain first-class and visible without opening process details
- Process details are secondary and collapsible by default
- Participant management belongs inside the operator layer, not the main review layer
- Task detail should deep-link to the thread workspace instead of embedding collaboration

## What To Delete Or Avoid

During refactor, remove or avoid:

- any frontend dependency on `/api/tasks/{taskId}/discussion-thread`
- any frontend dependency on `/api/tasks/{taskId}/discussion-messages`
- any UI that treats task detail as the main collaboration workspace
- any UI that reconstructs “active discussion” from raw turns client-side
- any UI that reconstructs “expected responder” from raw runs client-side
- any UI that hides versions behind task detail navigation

## Suggested Rebuild Sequence

Recommended order for a clean rewrite:

1. Route cleanup
2. Page shell orchestration
3. Selected version hero
4. Discussion panel
5. Version timeline
6. Process details accordion
7. Dense operator workbench
8. Task detail thread-workspace link cleanup
9. Copy/style polish

## Acceptance Checklist

The rebuild is correct when:

- opening `/threads/:threadId` immediately shows thread title, selected version, discussion, and versions
- switching versions updates the hero and download links without leaving the page
- submitting “request revision”, “ask why”, and “add note” uses thread-native routing metadata
- older iterations can still be inspected and keep their own composer target
- participant invite/remove is still possible, but only inside process details
- task detail links to `/threads/:threadId`
- no collaboration UI depends on legacy task discussion transport

## Current Reference Files

Use these as the working reference implementation:

- [VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)
- [SelectedVersionHero.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/SelectedVersionHero.tsx)
- [ThreadDiscussionPanel.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/ThreadDiscussionPanel.tsx)
- [VersionTimeline.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VersionTimeline.tsx)
- [ProcessDetailsAccordion.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/ProcessDetailsAccordion.tsx)
- [VideoThreadWorkbench.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadWorkbench.tsx)
- [videoThreadsApi.ts](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/lib/videoThreadsApi.ts)
- [TaskDetailPageV2.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/tasks/TaskDetailPageV2.tsx)

## One-Sentence Frontend Rule

Render collaboration from the thread surface, inspect detail from the selected iteration resource, and treat task pages as operator/task shells rather than the video collaboration home.
