# Video Discussion And Owner Review Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn each video task into a durable collaboration object that supports owner review actions, full generation trace visibility, and future human-plus-agent discussion/iteration, while shipping a frontend placeholder in the current task detail page.

**Architecture:** Extend the existing task-centric workflow model rather than creating a parallel chat system. The root task becomes the anchor for two stable contracts: `workflow_review_controls` for owner actioning and a new discussion/trace contract for “how this video was made” plus “what should happen next”. In phase 1, the UI renders a read-first placeholder discussion surface under the video player and keeps owner review behavior consistent through action-specific refresh semantics; in later phases, owner messages and agent responses are persisted into the same root-task collaboration timeline so revisions, explanations, and follow-up design requests remain attached to one video lineage.

**Tech Stack:** FastAPI, Pydantic, SQLite task events, existing review bundle builder, React, TypeScript, Vitest, pytest.

---

## Recommended Product Shape

Use one root-task-centered “video collaboration thread” instead of separate review/chat systems.

- `workflow_review_controls` remains the owner action surface in the right sidebar.
- A new main-column section below the video player becomes `Video Discussion & Process`.
- That section is backed by stable read models, not ad-hoc event parsing in the UI.
- Phase 1 is read-first plus placeholder composer.
- Phase 2 adds owner message submission and agent response generation.
- Phase 3 lets follow-up revisions spawn new child tasks while preserving one continuous thread across the root task lineage.

This is the recommended approach because it reuses existing `task_events`, `recent_agent_runs`, `collaboration`, `case_memory`, and workflow lineage instead of introducing a disconnected conversation system.

## Non-Goals For Phase 1

- Do not build free-form real-time chat transport.
- Do not expose raw chain-of-thought.
- Do not let frontend infer agent rationale from unstructured event payloads.
- Do not split discussions per child task; anchor discussion to the root task lineage.

## Functional Requirements

1. Every video detail page shows a visible placeholder for discussion and process history under the video player.
2. Each video lineage has a stable read contract that explains:
   - what the owner asked for
   - what the generator/planner/reviewer/repairer did
   - what decisions were made
   - what child attempts were created
   - what follow-up action is recommended
3. Owner review actions refresh the correct data scope based on action outcome.
4. Future owner messages such as “why did you do this” or “change the title animation” can be added without redesigning the page or contract.
5. The system must preserve iterative context across multiple agent and human turns on the same root task.

## Contract Strategy

### Keep

- `GET /api/tasks/{task_id}/review-bundle`
- `workflow_review_controls`
- `task_events`
- `recent_agent_runs`
- `collaboration`
- `branch_scoreboard`
- `arbitration_summary`

### Add

Add a new stable read model inside `ReviewBundle`, tentatively named `video_discussion_surface`.

Suggested shape:

```python
class VideoDiscussionSurface(BaseModel):
    root_task_id: str
    thread_status: Literal["idle", "awaiting_owner", "awaiting_agent", "in_revision", "resolved"] = "idle"
    summary: str = ""
    prompt_context: str = ""
    latest_follow_up_prompt: str | None = None
    placeholder_enabled: bool = True
    composer: VideoDiscussionComposer | None = None
    process_timeline: list[VideoProcessTimelineItem] = Field(default_factory=list)
    discussion_entries: list[VideoDiscussionEntry] = Field(default_factory=list)
    suggested_next_actions: list[VideoDiscussionSuggestedAction] = Field(default_factory=list)
```

Key rules:

- `process_timeline` is for system/agent-visible milestones.
- `discussion_entries` is for owner and agent conversational turns.
- `suggested_next_actions` is for structured next steps such as `ask_why`, `request_change`, `start_revision`, `accept_current`.
- Frontend must not reconstruct this from `task_events` directly once the surface exists.

## Refresh Semantics

Add an explicit action refresh contract to `ApplyReviewDecisionResponse`.

Suggested shape:

```python
class ReviewDecisionRefreshContract(BaseModel):
    refresh_scope: Literal["panel_only", "task_and_panel", "navigate"] = "panel_only"
    refresh_task_id: str | None = None
```

Expected behavior:

- `revise` and `retry` with `created_task_id` -> `navigate`
- workflow-memory-only style mutations that do not change current task snapshot -> `panel_only`
- `accept` and any action mutating root-task delivery state -> `task_and_panel`

This removes remaining frontend guesswork.

## UI Recommendation

Place the new placeholder directly below the video player in the main column.

Why this location:

- user explicitly wants to discuss “under the video”
- the sidebar should stay action-oriented
- the main column already holds revision intent and is the natural place for iterative conversation

Phase 1 layout:

1. `Video player`
2. `Video Discussion & Process` placeholder card
3. existing manual revision controls

Phase 1 placeholder contents:

- section title
- one-line explanation that this area will host discussion with the generating agent
- disabled composer with placeholder text
- chips for `Planner`, `Reviewer`, `Repairer`, `Owner`
- read-only timeline summary built from stable contract when available
- empty state or “discussion coming next” copy when no entries exist

## Data Source Mapping

Use existing data as interim backend inputs:

- `prompt`, `feedback` -> owner prompt context
- `task_events` -> raw provenance source
- `recent_agent_runs` -> recent role execution timeline
- `collaboration` and `collaboration_summary` -> structured role snapshots
- `branch_scoreboard` and `arbitration_summary` -> lineage and selection context
- `case_memory` -> durable reasoning breadcrumbs

Do not expose raw chain-of-thought. Summaries should be concise, intentionally authored, and safe for product surfaces.

## Task Breakdown

### Task 1: Document The Unified Contracts

**Files:**
- Modify: `docs/runbooks/owner-review-panel-contract.md`
- Create: `docs/runbooks/video-discussion-surface-contract.md`
- Test: none

**Step 1: Write the contract docs**

Document:

- owner review refresh semantics
- `video_discussion_surface` read model
- placeholder-only phase scope
- root-task lineage anchoring rules

**Step 2: Verify docs are internally consistent**

Check that the new doc:

- distinguishes `process_timeline` vs `discussion_entries`
- forbids UI inference from raw `task_events`
- states that chain-of-thought is not exposed

**Step 3: Commit**

```bash
git add docs/runbooks/owner-review-panel-contract.md docs/runbooks/video-discussion-surface-contract.md
git commit -m "docs: define video discussion and review refresh contracts"
```

### Task 2: Add Backend Read Models For Video Discussion Surface

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Test: `tests/integration/test_review_bundle_builder.py`

**Step 1: Write the failing test**

Add a test proving `ReviewBundle` returns:

- `video_discussion_surface.root_task_id`
- at least one `process_timeline` item from task events or agent runs
- placeholder composer metadata
- suggested discussion actions

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_review_bundle_builder.py -k video_discussion_surface -q
```

Expected: FAIL because the field is not defined yet.

**Step 3: Write minimal implementation**

Add Pydantic models and build the new surface in `ReviewBundleBuilder` using existing `task_events`, `recent_agent_runs`, `collaboration`, and lineage metadata.

**Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/integration/test_review_bundle_builder.py -k video_discussion_surface -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/video_agent/domain/review_workflow_models.py src/video_agent/application/review_bundle_builder.py tests/integration/test_review_bundle_builder.py
git commit -m "feat: expose video discussion surface in review bundle"
```

### Task 3: Add Action Refresh Semantics To Review Decision Outcomes

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/multi_agent_workflow_service.py`
- Modify: `src/video_agent/server/http_api.py`
- Test: `tests/integration/test_http_multi_agent_workflow_api.py`
- Test: `tests/integration/test_mcp_multi_agent_workflow_tools.py`

**Step 1: Write the failing tests**

Add tests asserting:

- `accept` returns `refresh_scope == "task_and_panel"`
- workflow-memory-only or non-navigating mutation returns `refresh_scope == "panel_only"`
- `revise` and `retry` with child creation return `refresh_scope == "navigate"`

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/integration/test_http_multi_agent_workflow_api.py -k refresh_scope -q
pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -k refresh_scope -q
```

Expected: FAIL because the response field is missing.

**Step 3: Write minimal implementation**

Compute refresh scope in `ReviewDecisionOutcome` construction instead of leaving frontend to infer behavior.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/domain/review_workflow_models.py src/video_agent/application/multi_agent_workflow_service.py src/video_agent/server/http_api.py tests/integration/test_http_multi_agent_workflow_api.py tests/integration/test_mcp_multi_agent_workflow_tools.py
git commit -m "feat: add review decision refresh semantics"
```

### Task 4: Consume Full Review Contracts In The Frontend

**Files:**
- Modify: `ui/src/lib/tasksApi.ts`
- Modify: `ui/src/lib/tasksApi.test.ts`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.tsx`
- Modify: `ui/src/features/tasks/TaskReviewPanel.tsx`
- Test: `ui/src/features/tasks/TaskDetailPageV2.test.tsx`

**Step 1: Write the failing tests**

Add frontend tests for:

- `accept` refreshes task snapshot and review panel, not panel only
- `follow_up_action_id` renders as visible “next recommended action” affordance
- `default_focus_section_id` drives initial focus or anchor styling
- local section expansion is preserved across panel-only refresh when section ids are unchanged

**Step 2: Run tests to verify they fail**

Run:

```bash
cd ui && npm test -- --run src/features/tasks/TaskDetailPageV2.test.tsx
```

Expected: FAIL on new refresh and rendering assertions.

**Step 3: Write minimal implementation**

- add new typed response fields in `tasksApi.ts`
- route refresh behavior from backend contract
- make `TaskReviewPanel` consume `follow_up_action_id` and preserve user expansion state when safe

**Step 4: Run tests to verify they pass**

Run:

```bash
cd ui && npm test -- --run src/features/tasks/TaskDetailPageV2.test.tsx
cd ui && npm test -- --run src/lib/tasksApi.test.ts
```

Expected: PASS.

**Step 5: Commit**

```bash
git add ui/src/lib/tasksApi.ts ui/src/lib/tasksApi.test.ts ui/src/features/tasks/TaskDetailPageV2.tsx ui/src/features/tasks/TaskReviewPanel.tsx ui/src/features/tasks/TaskDetailPageV2.test.tsx
git commit -m "feat: align task detail with review refresh contract"
```

### Task 5: Ship The Frontend Placeholder For Video Discussion & Process

**Files:**
- Modify: `ui/src/features/tasks/TaskDetailPageV2.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.css`
- Create or Modify: `ui/src/features/tasks/TaskDiscussionPlaceholder.tsx`
- Modify: `ui/src/app/locale.tsx`
- Test: `ui/src/features/tasks/TaskDetailPageV2.test.tsx`

**Step 1: Write the failing test**

Add a UI test that, when `video_discussion_surface` is present, the page renders a section below the video player with:

- title
- explanatory placeholder copy
- disabled composer
- process timeline summary
- role chips

**Step 2: Run test to verify it fails**

Run:

```bash
cd ui && npm test -- --run src/features/tasks/TaskDetailPageV2.test.tsx
```

Expected: FAIL because the section does not exist.

**Step 3: Write minimal implementation**

Render a dedicated placeholder component below the player using the stable contract. Do not submit messages yet.

**Step 4: Run test to verify it passes**

Run the same command and expect PASS.

**Step 5: Run build**

```bash
cd ui && npm run build
```

Expected: PASS.

**Step 6: Commit**

```bash
git add ui/src/features/tasks/TaskDetailPageV2.tsx ui/src/features/tasks/TaskDetailPageV2.css ui/src/features/tasks/TaskDiscussionPlaceholder.tsx ui/src/app/locale.tsx ui/src/features/tasks/TaskDetailPageV2.test.tsx
git commit -m "feat: add video discussion placeholder to task detail"
```

### Task 6: Add Owner Message Submission Contract

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/server/http_api.py`
- Add or Modify: `src/video_agent/application/video_discussion_service.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Test: `tests/integration/test_http_multi_agent_workflow_api.py`
- Test: `ui/src/lib/tasksApi.ts`
- Test: `ui/src/lib/tasksApi.test.ts`

**Step 1: Write the failing backend test**

Add a test for:

- `POST /api/tasks/{task_id}/discussion-messages`
- root-task anchoring
- persisted owner message entry
- updated `video_discussion_surface.discussion_entries`

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_http_multi_agent_workflow_api.py -k discussion_message -q
```

Expected: FAIL because endpoint and models do not exist.

**Step 3: Write minimal implementation**

Persist owner discussion messages as structured task events on the root task and rebuild the discussion surface from that source.

**Step 4: Run backend test to verify it passes**

Run the same command and expect PASS.

**Step 5: Add frontend request typing**

Add request/response helpers in `ui/src/lib/tasksApi.ts`.

**Step 6: Run frontend tests**

```bash
cd ui && npm test -- --run src/lib/tasksApi.test.ts
```

Expected: PASS.

**Step 7: Commit**

```bash
git add src/video_agent/domain/review_workflow_models.py src/video_agent/server/http_api.py src/video_agent/application/video_discussion_service.py src/video_agent/application/review_bundle_builder.py tests/integration/test_http_multi_agent_workflow_api.py ui/src/lib/tasksApi.ts ui/src/lib/tasksApi.test.ts
git commit -m "feat: add owner video discussion message contract"
```

### Task 7: Connect Agent Replies And Iterative Revision Flow

**Files:**
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/multi_agent_workflow_service.py`
- Modify: `src/video_agent/application/video_discussion_service.py`
- Modify: `tests/integration/test_multi_agent_workflow_service.py`
- Modify: `tests/integration/test_http_multi_agent_workflow_api.py`

**Step 1: Write the failing test**

Add an integration test proving:

- owner asks for a change on a completed root video
- system records message
- a revision child is created or queued
- the thread shows both owner request and agent/system response metadata on the same root lineage

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/integration/test_multi_agent_workflow_service.py -k discussion_iteration -q
```

Expected: FAIL because the workflow does not yet project discussion-driven iterations.

**Step 3: Write minimal implementation**

Translate approved owner discussion requests into structured follow-up actions or revisions while preserving one root-thread history.

**Step 4: Run focused tests**

Run:

```bash
pytest tests/integration/test_multi_agent_workflow_service.py -k discussion_iteration -q
pytest tests/integration/test_http_multi_agent_workflow_api.py -k discussion_iteration -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/video_agent/application/workflow_engine.py src/video_agent/application/multi_agent_workflow_service.py src/video_agent/application/video_discussion_service.py tests/integration/test_multi_agent_workflow_service.py tests/integration/test_http_multi_agent_workflow_api.py
git commit -m "feat: connect video discussion to revision iterations"
```

## Verification Suite

After completing all tasks, run:

```bash
pytest tests/integration/test_review_bundle_builder.py -q
pytest tests/integration/test_http_multi_agent_workflow_api.py -q
pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q
pytest tests/integration/test_multi_agent_workflow_service.py -q
cd ui && npm test -- --run src/lib/tasksApi.test.ts
cd ui && npm test -- --run src/features/tasks/TaskDetailPageV2.test.tsx
cd ui && npm run build
pytest -q
```

Expected:

- all focused backend integration tests pass
- task detail frontend tests pass
- production build passes
- full test suite remains green

## Risks To Watch

- exposing too much raw agent reasoning instead of product-safe summaries
- fragmenting conversation by child task instead of root task
- letting frontend infer semantics from raw events instead of stable contracts
- refreshing too little after actions like `accept`, causing status divergence
- building a placeholder UI that must be thrown away once submission is added

## Recommended Execution Order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Stop and review with product expectations
7. Task 6
8. Task 7

