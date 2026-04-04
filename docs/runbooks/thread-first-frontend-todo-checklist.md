# Thread-First Frontend TODO Checklist

This checklist is the execution companion to [thread-first-frontend-refactor-guide.md](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/docs/runbooks/thread-first-frontend-refactor-guide.md).

Use it when rebuilding the frontend around the current backend contract.

## Phase 0: Guardrails

- [ ] Stop treating task pages as the collaboration home
- [ ] Stop calling legacy task discussion endpoints
- [ ] Treat `GET /api/video-threads/:threadId/surface` as the main page truth
- [ ] Treat `GET /api/video-threads/:threadId/iterations/:iterationId` as the inspected-iteration truth

Done means:

- no new collaboration UI is built on `/api/tasks/{taskId}/discussion-thread`
- no new collaboration UI is built on `/api/tasks/{taskId}/discussion-messages`
- collaboration semantics are not reconstructed from task lineage in the browser

## Phase 1: Route Cleanup

Target files:

- [App.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/app/App.tsx)
- [VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)
- [TaskDetailPageV2.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/tasks/TaskDetailPageV2.tsx)

Checklist:

- [ ] `/threads/:threadId` is the canonical route
- [ ] `/videos/:threadId` remains only as compatibility
- [ ] task detail links to `/threads/:threadId`
- [ ] task detail no longer embeds or pretends to host collaboration UI

Done means:

- a user can always reach the thread workspace from task detail
- the URL model makes thread identity primary and task identity secondary

## Phase 2: Thread Page Shell

Target files:

- [VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)
- [videoThreadsApi.ts](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/lib/videoThreadsApi.ts)

Checklist:

- [ ] page-level state is owned only in `VideoThreadPage`
- [ ] surface fetch happens on page load
- [ ] iteration detail fetch happens when `selectedIterationId` changes
- [ ] page-level mutation handlers refresh surface after success
- [ ] iteration-scoped mutations also refresh the inspected iteration detail
- [ ] thread title stays visible in the page header

Done means:

- page orchestration is centralized
- child components are mostly render components, not data coordinators

## Phase 3: Selected Version Hero

Target files:

- [SelectedVersionHero.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/SelectedVersionHero.tsx)
- [useTaskArtifactDownloads.ts](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/useTaskArtifactDownloads.ts)

Checklist:

- [ ] selected version summary is visible above discussion
- [ ] selected result id is visible
- [ ] selected iteration id is visible
- [ ] source task id is visible when available
- [ ] video download is available
- [ ] script download is available
- [ ] validation report download is available when available
- [ ] task id is resolved from `selectedResult.video_resource` first

Done means:

- the owner can review and download the current cut without leaving the thread page

## Phase 4: Discussion Panel

Target files:

- [ThreadDiscussionPanel.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/ThreadDiscussionPanel.tsx)
- [VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)

Checklist:

- [ ] discussion is directly below selected version
- [ ] active thread summary is rendered from `surface.discussion_runtime`
- [ ] reply target is rendered from `composer.target` or discussion runtime
- [ ] grouped discussion history is rendered from `surface.discussion_groups`
- [ ] flat visible turns are rendered from `surface.conversation`
- [ ] action modes render from `surface.actions.items`
- [ ] textarea label follows selected action
- [ ] submit routing uses iteration id, reply target, result id, and reply-to turn id from thread-native data

Done means:

- “request revision”, “ask why”, and “add note” all submit against thread-native routing
- the frontend is not guessing who to talk to next

## Phase 5: Versions Timeline

Target files:

- [VersionTimeline.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VersionTimeline.tsx)
- [VideoThreadPage.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.tsx)

Checklist:

- [ ] versions stay visible without opening process details
- [ ] version cards render from `iterationDetail.results`
- [ ] selected/current version is clearly marked
- [ ] non-selected versions can be switched with “set as current version”
- [ ] each version can open its task detail page
- [ ] each version can download its own video and script when task-backed

Done means:

- version comparison and switching happen in-place on the thread page
- task detail is a drill-down, not the only place versions can be used

## Phase 6: Process Details Accordion

Target files:

- [ProcessDetailsAccordion.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/ProcessDetailsAccordion.tsx)
- [VideoThreadWorkbench.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadWorkbench.tsx)
- [VideoThreadWorkbench.css](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadWorkbench.css)

Checklist:

- [ ] process details are collapsed by default
- [ ] collapsed state still shows useful summary chips
- [ ] expanded state reveals operator/process content
- [ ] expanded workbench does not duplicate the thread page header
- [ ] the owner can review the main flow without ever opening this layer

Done means:

- the main page hierarchy is “review first, operations second”

## Phase 7: Operator Workbench

Target files:

- [VideoThreadWorkbench.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadWorkbench.tsx)

Checklist:

- [ ] current focus panel renders from `surface.current_focus`
- [ ] decision notes render from `surface.decision_notes`
- [ ] artifact lineage renders from `surface.artifact_lineage`
- [ ] rationale snapshots render from `surface.rationale_snapshots`
- [ ] iteration compare renders from `surface.iteration_compare`
- [ ] authorship renders from `surface.authorship`
- [ ] recommended next move renders from `surface.next_recommended_move`
- [ ] production journal renders from `surface.production_journal`
- [ ] participant runtime renders from `surface.participant_runtime`
- [ ] history renders from `surface.history`
- [ ] iteration selector renders from `surface.iteration_workbench`
- [ ] iteration detail panel renders from inspected iteration detail
- [ ] process runs render from `surface.process`
- [ ] participants and invite/remove controls render from `surface.participants`

Done means:

- all dense operational panels are available, but none of them block the main review flow

## Phase 8: Task Detail Cleanup

Target files:

- [TaskDetailPageV2.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/tasks/TaskDetailPageV2.tsx)
- [TaskDetailPageV2.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/tasks/TaskDetailPageV2.test.tsx)

Checklist:

- [ ] task detail presents “Thread workspace” as a dedicated card
- [ ] task detail copy explains the thread page is canonical for discussion, versions, and revision history
- [ ] task detail no longer uses “video workbench” as the primary concept

Done means:

- the mental model is consistent across task pages and thread pages

## Phase 9: State Hygiene

Checklist:

- [ ] no child component independently invents selected version state
- [ ] no child component independently invents active discussion routing
- [ ] no child component independently invents expected responder semantics
- [ ] page state stays minimal and derived where possible
- [ ] task artifact download resolution is centralized

Done means:

- fewer race conditions
- fewer contradictory UI states
- easier refactor and test maintenance

## Phase 10: Regression Coverage

Target tests:

- [VideoThreadPage.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/videoThreads/VideoThreadPage.test.tsx)
- [TaskDetailPageV2.test.tsx](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/features/tasks/TaskDetailPageV2.test.tsx)
- [videoThreadsApi.test.ts](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/codex-thread-first-routing/ui/src/lib/videoThreadsApi.test.ts)

Checklist:

- [ ] thread page test covers selected version above discussion
- [ ] thread page test covers versions as first-class content
- [ ] thread page test covers process details collapsed by default
- [ ] thread page test covers participant management inside process details
- [ ] thread page test covers submit routing for discussion actions
- [ ] task detail test covers canonical thread workspace link
- [ ] task detail test covers `/threads/:threadId` instead of `/videos/:threadId`

Done means:

- the thread-first architecture is protected against regressions

## Final Verification

Run before calling the refactor complete:

- [ ] `npm --prefix ui test`
- [ ] `npm --prefix ui run build`

Optional confidence checks:

- [ ] manually click through `/threads/:threadId`
- [ ] manually switch versions and confirm hero/downloads update
- [ ] manually submit one discussion action and confirm refresh behavior
- [ ] manually verify task detail still routes cleanly into the thread workspace

## One-Line Build Rule

- [ ] If a new piece of collaboration UI needs task data plus thread data plus local inference to decide what to show, stop and push that meaning back into the thread surface contract instead.
