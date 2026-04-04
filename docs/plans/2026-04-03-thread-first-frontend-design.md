# Thread-First Frontend Design

Date: 2026-04-03

## 1. Goal

This document defines a frontend redesign that matches the backend as it exists today.

The core shift is:

- `thread` is the durable video workspace
- `iteration` is one round of direction or revision
- `result` is one visible video version inside an iteration
- `task` is a backend execution record, not the primary product object

The frontend should stop treating `task` as the main user-facing entity for video collaboration.
The user-facing object should be the video thread.

## 2. Why The Current UI Feels Split

The current backend has already moved to a thread-native collaboration model:

- discussion APIs live under `/api/video-threads/*`
- revision is created from a thread iteration
- explanation is requested from a thread iteration
- result selection is done inside a thread
- thread projection already aggregates discussion, lineage, process, iterations, participants, and current focus

But the frontend still centers the main product experience around:

- `/tasks`
- `/tasks/:taskId`
- `/videos` as a recent outputs gallery
- `/videos/:threadId` as a secondary workbench

This creates a model mismatch:

- the backend thinks in `thread -> iteration -> result`
- the frontend still thinks in `task -> result`

The result is that the user sees the player, download, and review controls in one place, but discussion and version reasoning in another place.

## 3. Design Principles

The redesign should follow these rules:

1. One video, one durable home
   The canonical detail page for a work should be the thread page, not the task page.

2. Player first, process second
   The selected version should always be visible near the top. Process data should support the selected version, not overpower it.

3. Discussion must be anchored
   Every discussion action should clearly belong to a thread and, when possible, to a specific iteration/result.

4. Versions are first-class
   Users must be able to see version history, understand what changed, switch focus, and download a concrete version.

5. Task is implementation detail
   Task ids remain visible for debugging and artifact access, but should not define the main navigation model.

6. Progressive disclosure
   Everyday users should see player, current version summary, discussion, version list.
   Deeper operator/process data can stay collapsible.

## 4. Backend Reality To Design Against

The current backend already supports these frontend-facing capabilities.

### 4.1 Thread capabilities already available

- create thread
- load thread
- load thread surface projection
- load iteration detail
- append owner turn
- request revision
- request explanation
- select result
- manage thread participants

This means the frontend does not need to invent a new collaboration protocol for MVP.

### 4.2 Result and artifact capabilities already available

At the data layer, thread results already store:

- `result_id`
- `thread_id`
- `iteration_id`
- `source_task_id`
- `video_resource`
- `preview_resources`
- `script_resource`
- `validation_report_resource`
- `selected`

This is enough to model version cards and attach downloads to a concrete result.

### 4.3 Task capabilities already available

Tasks still matter because they provide:

- execution lifecycle
- delivery status
- artifact download URLs
- lineage through `root_task_id` and `parent_task_id`
- thread and iteration binding through `thread_id` and `iteration_id`

The frontend should keep task detail as an operator/debug surface, not the primary collaboration page.

### 4.4 Important limitation

The backend is strongest at:

- thread surface aggregation
- result selection state
- task-level artifact download

The current API is weaker at:

- directly exposing ready-made download URLs per `thread result`
- giving a single thread endpoint that returns a flattened “version gallery” payload already normalized for UI

For the first frontend refactor, this is acceptable. The frontend can derive version download actions through `source_task_id`.

## 5. New Frontend Information Architecture

### 5.1 Primary routes

Recommended route model:

- `/threads`
  video workspace list, replacing the conceptual role currently split across `/tasks` and `/videos`

- `/threads/:threadId`
  canonical video detail page

- `/tasks/:taskId`
  operator detail page only

### 5.2 Transitional routing

To reduce migration risk:

- keep `/videos` as an alias to the new thread list during transition
- keep `/videos/:threadId` as an alias or redirect to `/threads/:threadId`
- keep links from task detail into thread detail

### 5.3 Navigation model

User navigation should become:

1. open a thread
2. view current selected version
3. read or write discussion under that version context
4. browse prior iterations and results
5. trigger explanation or revision from the same page

## 6. Canonical Thread Detail Page

The thread detail page should become the single place for:

- current version playback
- version switching
- version download
- discussion
- revision requests
- rationale and change history
- optional process inspection

### 6.1 Page layout

Recommended desktop layout:

- top hero
  selected version player + title + status + main actions

- main content, two columns
  left column: discussion and context
  right column: version timeline and iteration navigator

- lower collapsible section
  process journal, agent runs, task metadata, participant management

Recommended mobile layout:

- player
- quick actions
- selected version summary
- version list
- discussion
- process accordion

## 7. Page Sections

### 7.1 Hero: Selected Version

Purpose:

- answer “what is the current accepted version?”
- make play and download obvious

Content:

- thread title
- selected version badge
- selected iteration id
- selected result id
- current result summary
- author/agent summary when available
- main video player
- actions:
  - download video
  - download script
  - download validation report
  - ask why this version
  - request revision

Data sources:

- `surface.current_focus`
- `surface.selection_summary`
- selected item from `iterationDetail.results`
- selected result's `source_task_id`
- task result endpoint for concrete download URLs when needed

### 7.2 Discussion Panel

Purpose:

- put discussion directly under the selected video context
- make iteration visible and understandable

Content:

- grouped discussion threads
- latest owner turn
- latest agent reply
- composer
- mode switch:
  - discuss
  - request explanation
  - request revision

Behavior:

- if current panel focus is a selected result, composer should default to that result
- if the current discussion runtime already has `default_reply_to_turn_id`, reuse it
- if the user switches to another iteration or result, discussion context should visibly update

Data sources:

- `surface.discussion_groups`
- `surface.discussion_runtime`
- `surface.composer`
- `appendVideoTurn`
- `requestVideoExplanation`
- `requestVideoRevision`

### 7.3 Versions Panel

Purpose:

- make every version independently visible and accessible

Each version card should show:

- result id
- iteration id
- created time
- selected/current marker
- summary
- source task id
- actions:
  - preview/focus
  - select as current version
  - download video
  - download script
  - download validation report
  - open task detail

Data source:

- `iterationDetail.results`
- optionally cross-iteration aggregation built from iteration list + iteration detail fetches

Important:

The current backend already stores version-level resources on each result, but task-level download URLs are easier to use immediately.
For the first iteration, resolve downloads via `source_task_id -> /api/tasks/{task_id}/result`.

### 7.4 Iteration Timeline

Purpose:

- explain how the work evolved

Each iteration card should show:

- iteration title
- goal
- requested action
- selected result id
- status
- responsible role/agent

Actions:

- inspect iteration
- jump to its results
- create follow-up revision from this iteration

Data source:

- `surface.iteration_workbench.iterations`
- `getVideoThreadIteration`

### 7.5 Why This Version

Purpose:

- answer “why is this the chosen output?”

Content:

- decision notes
- rationale snapshots
- authorship
- artifact lineage
- iteration compare

This is already present in the projection model and should be reframed as a compact “why” section near the top, not scattered operator panels.

### 7.6 Process And Debug Section

Purpose:

- retain current operational visibility without letting it dominate the main UX

Content:

- production journal
- runs
- participants
- task ids
- validation and workflow metadata

This should live under an accordion such as “Process details”.

## 8. Frontend Domain Model

The frontend should adopt these view models explicitly.

### 8.1 Core entities

- `ThreadShell`
  minimal info for lists and page headers

- `SelectedVersionView`
  top hero player state

- `VersionCardView`
  one downloadable version

- `IterationCardView`
  one revision/generation round

- `DiscussionContextView`
  current reply target, result context, and follow-up mode

- `ProcessEntryView`
  optional operator/debug item

### 8.2 Mapping rules

- thread page identity comes from `thread_id`
- current selected result comes from thread-level selection and iteration-level selection
- version card identity comes from `result_id`
- download identity comes from `source_task_id`
- revision creation identity comes from `thread_id + iteration_id`

### 8.3 Anti-patterns to avoid

Do not model:

- “current page task” as the root object for thread pages
- a flat message list without iteration/result context
- a version list derived only from recent tasks

## 9. Data Fetching Strategy

### 9.1 Initial page load

On thread page entry:

1. fetch `getVideoThreadSurface(threadId)`
2. resolve selected iteration id from:
   - `surface.iteration_detail.selected_iteration_id`
   - else `surface.current_focus.current_iteration_id`
   - else `surface.iteration_workbench.selected_iteration_id`
3. fetch `getVideoThreadIteration(threadId, selectedIterationId)`
4. derive selected version and available actions

### 9.2 Version downloads

For the selected result or focused result:

1. read `source_task_id`
2. fetch `/api/tasks/{taskId}/result`
3. use returned:
   - `video_download_url`
   - `script_download_url`
   - `validation_report_download_url`

Cache by `task_id`.

### 9.3 Iteration switching

When the user selects another iteration:

1. fetch `getVideoThreadIteration`
2. update:
   - version panel
   - discussion composer context
   - selected hero if user is in “inspect iteration” mode

The page should distinguish:

- global selected version
- currently inspected iteration/result

These are related but not always identical.

### 9.4 Mutations

Mutation actions:

- discuss -> `appendVideoTurn`
- ask why -> `requestVideoExplanation`
- ask for change -> `requestVideoRevision`
- set as chosen version -> `selectVideoResult`

After any mutation:

- refresh thread surface
- refresh current iteration detail if still applicable
- refresh task downloads only for newly relevant results

## 10. State Model For The Thread Page

Use separate state buckets.

### 10.1 Server state

- thread surface
- selected iteration detail
- task result download cache by task id

### 10.2 UI state

- inspected iteration id
- inspected result id
- composer mode
- composer draft
- expanded panels
- download in progress states

### 10.3 Derived state

- globally selected result
- focused result
- selected result download actions
- whether composer is targeting current selected result or a historical result

## 11. Recommended Component Breakdown

Recommended components:

- `ThreadListPage`
- `ThreadDetailPage`
- `SelectedVersionHero`
- `VersionTimeline`
- `VersionCard`
- `IterationNavigator`
- `DiscussionPanel`
- `DiscussionComposer`
- `VersionReasoningPanel`
- `ProcessDetailsAccordion`
- `TaskArtifactActions`

Recommended hooks:

- `useThreadSurface(threadId)`
- `useIterationDetail(threadId, iterationId)`
- `useTaskArtifactDownloads(taskId)`
- `useThreadComposerContext(surface, iterationDetail, inspectedResultId)`

## 12. Recommended UX Behaviors

### 12.1 Selected version vs inspected version

Support both states clearly.

- Selected version
  the currently adopted thread output

- Inspected version
  the version the user is browsing right now

If the user inspects an older version:

- the hero should either switch to inspected version
- or show a clear banner: “You are viewing a historical version”

Do not silently mix these states.

### 12.2 Revision flow

When the user requests revision:

- keep them on the same thread page
- create new iteration
- show pending state in timeline
- auto-focus the new iteration once surface refresh confirms it

### 12.3 Explanation flow

When the user asks for explanation:

- keep context on current result
- insert new discussion group/reply into discussion area
- surface latest explanation near the hero

### 12.4 Download behavior

Downloads must always be attached to a concrete version card or selected hero.

Avoid ambiguous “download current video” buttons unless the current result is explicit.

## 13. Migration Plan

### Phase 1: Reframe existing pages

- keep backend unchanged
- keep `/tasks/:taskId` working
- promote thread page into canonical detail page
- move player-first UX into thread page
- add version cards with per-result actions
- move discussion directly below selected version

### Phase 2: Simplify task detail

- reduce task detail to operator/debug shell
- keep:
  - lifecycle
  - quality/review data
  - direct artifact download
  - link to thread page

### Phase 3: Replace `/videos` list with thread list

- stop showing “recent completed tasks” as the main work library
- group by thread where possible
- show latest selected version per thread

### Phase 4: Optional backend improvement

Add a thread-native version artifact endpoint or enrich thread detail results with resolved download URLs.
This is a product improvement, not a blocker for the frontend redesign.

## 14. What Frontend Can Build Immediately Without Backend Changes

Frontend can build now:

- thread-centered detail page
- selected version hero
- discussion under video
- iteration navigator
- per-iteration result list
- “select result” control
- per-version download through `source_task_id -> task result`
- task detail as secondary debug view

Frontend should not wait for backend changes before doing the structural refactor.

## 15. Minimal Backend Additions That Would Help Later

These are optional enhancements, not MVP requirements:

1. thread list endpoint
   Return one row per thread with latest selected result and preview.

2. thread result download URLs
   Add resolved download URLs directly to result payloads in thread detail.

3. explicit selected result payload in surface
   Return a normalized `selected_result` block for the hero without extra derivation.

4. thread-level pagination
   Helpful once thread history grows.

## 16. Final Recommendation

The frontend should be rebuilt around one sentence:

> A video is a conversation-backed thread whose visible outputs are versioned results.

Concretely:

- make `ThreadDetailPage` the primary product page
- put the player and selected version at the top
- put discussion directly under the video
- put versions and iterations beside or below it
- demote `TaskDetailPage` to an operator page
- use `source_task_id` as the bridge for artifact downloads

This gives the frontend a model that already matches the backend instead of fighting it.
