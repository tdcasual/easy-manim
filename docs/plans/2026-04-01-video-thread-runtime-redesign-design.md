# Video Thread Runtime Redesign

**Status:** Implemented and closed by the 2026-04-03 runtime closure pass

**Date:** 2026-04-01

**Authoring Context:** This design assumes we do **not** need backward compatibility with the current task-centric collaboration surface. The next phase may replace existing discussion read models, storage assumptions, and UI composition if doing so yields a cleaner long-term architecture.

---

## Goal

Turn the current video agent system from a task-centric workflow engine with a collaboration overlay into a thread-centric video collaboration runtime.

After this redesign, a "video" is no longer treated primarily as a single task plus some derived lineage state. Instead, a video becomes a long-lived collaboration object with:

- a stable thread identity
- explicit iterations
- explicit visible conversation turns
- explicit agent execution runs
- explicit result selection and branching
- explicit responsibility assignment

The system should support a product experience where an owner can keep talking to the agent system under a video, ask why the design evolved in a certain way, request focused changes, compare multiple revisions, and continue iterating with humans plus multiple agent roles over time.

## Closure State

As of 2026-04-03, the thread-native runtime has crossed from redesign into the default owner-facing architecture. The stable owner-facing `video_thread_surface` now includes:

- rationale and provenance sections such as `selection_summary`, `decision_notes`, `artifact_lineage`, `rationale_snapshots`, `authorship`, `history`, and `production_journal`
- continuity and interaction sections such as `discussion_groups`, `discussion_runtime`, `participant_runtime`, `composer`, and `iteration_detail`
- a centralized `render_contract` carrying display priority, tone, and default-open hints for the workbench shell

The remaining design obligation is no longer "invent the runtime", but to extend these stable sections without reintroducing frontend inference or task-centric mental models.

---

## Why Redesign Instead Of Extend

The current architecture is strong enough to prove product value, but it is still fundamentally task-centric:

- `task` is the primary durable object
- discussion is reconstructed from task lineage and root-task events
- iterations are mostly inferred rather than first-class
- responsibility is a derived signal rather than runtime truth
- the owner is effectively talking to a workflow wrapper, not a persistent video thread runtime

That approach was the right Phase 2 choice because it minimized changes and validated the contract shape. It is no longer the right architecture for the next phase.

Continuing to extend the current model would create four structural problems:

1. The system would keep conflating "execution task" with "video collaboration object".
2. `ReviewBundleBuilder` would continue absorbing more domain logic and become the de facto runtime.
3. The product would present agent continuity without storing agent continuity as a first-class concept.
4. Long-lived thread features such as branch comparison, iteration assignment, and per-iteration process history would remain expensive and lossy.

This redesign resolves those issues by making collaboration runtime truth explicit.

---

## Product Principles

The redesign should optimize for these product truths:

1. A user is collaborating on a video, not on an individual task.
2. A video can outlive any single generation attempt.
3. A video can accumulate many iterations, branches, and participants.
4. Owners need safe answers to "why did you do this" without exposing hidden reasoning.
5. Multiple agent roles may contribute to one iteration, but the owner should still experience one coherent thread.
6. UI consumers should render from stable projections rather than infer state from raw events.

---

## Non-Goals

This phase should **not** attempt to build:

- a generic cross-domain chat platform
- a free-form agent messaging product disconnected from video generation
- full chain-of-thought storage or exposure
- arbitrary many-to-many shared editing across users in real time
- a universal workflow abstraction that erases video-specific semantics

This is a video collaboration runtime, not a general agent inbox.

---

## Core Architectural Shift

### Old Mental Model

`task` is primary.

- One root task anchors a lineage.
- Child tasks represent revisions or retries.
- Discussion and iteration state are derived from task lineage and task events.

### New Mental Model

`video_thread` is primary.

- One thread represents one long-lived video collaboration space.
- Iterations belong to the thread.
- Turns belong to iterations.
- Execution tasks are created by iterations, not the other way around.
- Agent runs are attached to iterations and tasks as execution facts.
- UI surfaces are projections of thread state.

This changes the system from "task execution with discussion metadata" to "video collaboration with execution attached".

---

## New Domain Model

### 1. Video Thread

`video_thread` is the top-level durable object for a video collaboration space.

Suggested fields:

- `thread_id`
- `owner_agent_id`
- `title`
- `status`
- `current_iteration_id`
- `selected_result_id`
- `origin_prompt`
- `origin_context_summary`
- `created_at`
- `updated_at`
- `archived_at`

Semantics:

- Represents the canonical collaboration container for one video.
- Owns the visible history, responsibility state, and selected output.
- Remains stable across many execution tasks and branches.

### 2. Iteration

`video_iteration` is a first-class unit of collaborative progress.

Suggested fields:

- `iteration_id`
- `thread_id`
- `parent_iteration_id`
- `goal`
- `requested_action`
- `preserve_working_parts`
- `status`
- `resolution_state`
- `focus_summary`
- `selected_result_id`
- `source_result_id`
- `initiated_by_turn_id`
- `responsible_role`
- `responsible_agent_id`
- `created_at`
- `updated_at`
- `closed_at`

Semantics:

- An iteration is not just a display row.
- It captures a distinct owner goal or refinement objective.
- It may produce zero, one, or many execution attempts.
- It may resolve into delivered, rejected, superseded, needs_clarification, or failed states.

### 3. Turn

`video_turn` is a visible message-like object inside an iteration.

Suggested fields:

- `turn_id`
- `thread_id`
- `iteration_id`
- `turn_type`
- `speaker_type`
- `speaker_agent_id`
- `speaker_role`
- `title`
- `summary`
- `visibility`
- `source_run_id`
- `source_task_id`
- `created_at`

Semantics:

- This replaces the loose "discussion entry" concept with a durable object.
- Turns are always attached to an iteration.
- Not every turn is a free-form chat message; many are product-safe summaries of runtime activity.

Suggested stable `turn_type` values:

- `owner_request`
- `owner_follow_up`
- `agent_explanation`
- `agent_plan`
- `agent_revision_notice`
- `review_summary`
- `system_status`

### 4. Result

`video_result` represents a produced visible video state.

Suggested fields:

- `result_id`
- `thread_id`
- `iteration_id`
- `source_task_id`
- `status`
- `video_resource`
- `preview_resources`
- `script_resource`
- `validation_report_resource`
- `result_summary`
- `quality_summary`
- `selected`
- `created_at`

Semantics:

- A thread may have multiple results.
- Selection is explicit rather than inferred only from task lineage.
- Results can be compared independently from the tasks that generated them.

### 5. Execution Task

The existing `task` should survive, but as an execution unit rather than as the top-level collaboration unit.

Additional fields or foreign keys:

- `thread_id`
- `iteration_id`
- `result_id`
- `execution_kind`

Semantics:

- Tasks remain useful for workflow execution, artifact production, validation, and retries.
- They stop being the canonical source of collaboration structure.

### 6. Agent Run

`agent_run` should become visibly associated with iterations.

Suggested fields:

- `run_id`
- `thread_id`
- `iteration_id`
- `task_id`
- `agent_id`
- `role`
- `status`
- `phase`
- `input_summary`
- `output_summary`
- `started_at`
- `ended_at`

Semantics:

- This is what makes "talk to the generating agent" real.
- The system can identify which role and agent most recently shaped the current result.

### 7. Participant

Suggested fields:

- `thread_id`
- `participant_id`
- `participant_type`
- `agent_id`
- `role`
- `display_name`
- `capabilities`
- `joined_at`
- `left_at`

Semantics:

- Participation is thread-scoped, not root-task-scoped.
- Participants may remain attached across many iterations.

---

## Storage Design

Introduce new tables instead of trying to stretch the existing event-only pattern:

- `video_threads`
- `video_iterations`
- `video_turns`
- `video_results`
- `video_thread_participants`
- `video_agent_runs`
- `video_iteration_assignments`
- `video_projection_checkpoints` (optional)

Recommended minimal relationships:

- `video_iterations.thread_id -> video_threads.thread_id`
- `video_turns.iteration_id -> video_iterations.iteration_id`
- `video_results.iteration_id -> video_iterations.iteration_id`
- `video_tasks.iteration_id -> video_iterations.iteration_id`
- `agent_runs.iteration_id -> video_iterations.iteration_id`

This is intentionally denormalized where useful. The design should favor projection stability and traceability over schema purity.

### Event Log

We should still keep an append-only event stream, but it becomes supporting infrastructure, not the primary source of collaboration shape.

Suggested thread event types:

- `thread_created`
- `iteration_created`
- `turn_added`
- `responsibility_assigned`
- `result_registered`
- `result_selected`
- `participant_joined`
- `participant_left`
- `run_started`
- `run_completed`
- `iteration_closed`

The event log remains valuable for auditing, debugging, and rebuilding projections.

---

## Runtime Services

The redesign should split runtime responsibilities into dedicated services.

### 1. `VideoThreadService`

Responsibilities:

- create thread
- load thread
- update thread title/status
- select current result
- archive thread

### 2. `VideoIterationService`

Responsibilities:

- create iteration from owner intent
- branch iteration from prior result
- close iteration
- assign responsibility
- map iteration to execution tasks and results

### 3. `VideoTurnService`

Responsibilities:

- append owner turns
- append product-safe agent explanation turns
- append system status turns
- enforce turn visibility rules

### 4. `VideoRunBindingService`

Responsibilities:

- attach planner/reviewer/repairer/orchestrator runs to iteration
- produce safe run summaries
- mark responsible agent/role
- expose "who is working now" runtime truth

### 5. `VideoProjectionService`

Responsibilities:

- build thread workbench view
- build owner panel summary
- build MCP/HTTP/UI projection payloads
- keep zero-inference contracts stable

### 6. `VideoPolicyService`

Responsibilities:

- decide which role should act next
- decide whether a request becomes discuss vs revise vs branch
- resolve handoff rules
- enforce owner-only write actions when needed

---

## Projection Model

The runtime model should not be exposed directly to the UI. The UI should read a stable projection.

Suggested top-level projection:

- `video_thread_surface`

Suggested structure:

- `thread_header`
- `thread_summary`
- `current_focus`
- `selection_summary`
- `latest_explanation`
- `decision_notes`
- `artifact_lineage`
- `rationale_snapshots`
- `authorship`
- `next_recommended_move`
- `responsibility`
- `iteration_workbench`
- `iteration_detail`
- `history`
- `production_journal`
- `discussion_groups`
- `discussion_runtime`
- `participant_runtime`
- `conversation`
- `process`
- `participants`
- `actions`
- `composer`
- `render_contract`

Authority boundaries for the current runtime:

- `discussion_runtime` answers which discussion thread is active and how the next follow-up should attach.
- `participant_runtime` answers which participant is expected now and who else recently shaped the active iteration.
- `discussion_groups` lists visible grouped discussion history.
- `composer.target` defines submit-time landing semantics.
- `iteration_detail.execution_summary` explains currently inspected iteration execution, not global discussion continuity.

### Current Focus

This becomes the new center of gravity for the UI.

Suggested fields:

- `thread_id`
- `current_iteration_id`
- `current_iteration_goal`
- `current_result_id`
- `current_result_summary`
- `latest_agent_position`
- `latest_explainer_agent`
- `latest_revision_agent`

### Responsibility

Suggested fields:

- `owner_action_required`
- `expected_agent_role`
- `expected_agent_id`
- `awaiting_participants`
- `resolution_state`
- `blocking_reason`

Unlike the current derived version, this should be emitted from runtime truth.

### Iteration Workbench

Suggested fields:

- `iterations[]`
- `selected_iteration_id`
- `latest_iteration_id`
- `branch_groups`
- `comparison_candidates`

Each iteration card should include:

- `goal`
- `status`
- `resolution_state`
- `requested_action`
- `result_summary`
- `responsible_role`
- `responsible_agent_id`
- `latest_turn_summary`
- `latest_run_summary`

### Conversation

Suggested fields:

- `turns[]`
- `visible_rationale_cards[]`
- `safe_process_notes[]`

This keeps chat-like interaction, but still tied to iteration and runtime state.

---

## API Design

Because backward compatibility is not required, we can simplify the surface.

### Recommended Read APIs

- `GET /api/video-threads/{thread_id}`
- `GET /api/video-threads/{thread_id}/surface`
- `GET /api/video-threads/{thread_id}/iterations/{iteration_id}`
- `GET /api/video-threads/{thread_id}/results/{result_id}`

### Recommended Write APIs

- `POST /api/video-threads`
- `POST /api/video-threads/{thread_id}/turns`
- `POST /api/video-threads/{thread_id}/iterations`
- `POST /api/video-threads/{thread_id}/iterations/{iteration_id}/select-result`
- `POST /api/video-threads/{thread_id}/iterations/{iteration_id}/request-revision`
- `POST /api/video-threads/{thread_id}/iterations/{iteration_id}/request-explanation`

### Recommended MCP Resources

- `video-thread://{thread_id}/surface.json`
- `video-thread://{thread_id}/timeline.json`
- `video-thread://{thread_id}/iterations/{iteration_id}.json`

### Recommended MCP Tools

- `create_video_thread`
- `append_video_turn`
- `request_video_revision`
- `request_video_explanation`
- `select_video_result`
- `get_video_thread_surface`

---

## Identity And "Talk To The Generating Agent"

This is the most important product requirement in the next phase.

The system should support the statement:

"This answer came from the agent role and run that most recently shaped the current video result."

To support that, the runtime must track:

- the origin agent that initiated the thread
- the agent run that produced the selected result
- the agent role currently responsible for the active iteration
- the agent run that produced the explanation currently shown to the user

Recommended visible fields:

- `origin_agent_id`
- `current_responsible_agent_id`
- `current_responsible_role`
- `latest_result_agent_id`
- `latest_explanation_agent_id`

The system may still use an orchestrator internally, but the projection should make authorship and responsibility legible.

---

## Safety Model

The redesign must keep a strong visibility boundary.

### Visibility Tiers

1. `product_safe`

- always safe to show in UI
- short rationale cards
- explanation summaries
- review summaries
- safe system notes

2. `operator_safe`

- visible to internal operators and debugging tools
- structured run summaries
- failure classifications
- assignment changes

3. `private`

- internal prompts
- private reasoning traces
- chain-of-thought
- sensitive execution details

Only `product_safe` should power the normal owner-facing thread.

---

## Frontend Shape

The next UI should be a video collaboration workbench rather than a discussion placeholder.

Recommended page composition:

1. Video player and selected result summary
2. Current focus rail
3. Iteration timeline and branches
4. Current iteration detail pane
5. Visible conversation and rationale
6. Process and agent activity
7. Composer with typed intents

Key UX rules:

- The latest active iteration must always be obvious.
- Branches should be inspectable without reading raw task ids.
- Asking "why" should target the current iteration or result explicitly.
- Requesting a change should create or reopen an iteration, not just append a loose message.
- Composer actions should target explicit runtime objects.

---

## Execution Flow Example

### Scenario: Owner Requests A Refinement

1. Owner opens thread.
2. UI shows selected result plus current active iteration.
3. Owner submits "Keep the slower opening, but make the title entrance more deliberate."
4. `VideoIterationService` creates a new iteration linked to the current selected result.
5. `VideoPolicyService` assigns `repairer` as the responsible role.
6. `VideoRunBindingService` creates or links the planner/reviewer/repairer runs needed for execution.
7. A new execution task is created under that iteration.
8. Agent runs produce safe summaries and result artifacts.
9. A result is registered and optionally auto-selected.
10. Projection updates current focus, rationale, responsibility, and visible conversation.

This is the same product outcome as today, but with runtime truth instead of projection-only inference.

---

## Testing Strategy

The redesign should be built test-first around runtime invariants rather than only UI fields.

### Unit Tests

- thread lifecycle
- iteration creation and closure
- turn visibility rules
- responsibility assignment
- result selection
- run binding

### Integration Tests

- owner starts thread, requests revision, gets new iteration and result
- owner asks why, receives product-safe explanation turn
- multiple follow-up iterations remain stable
- multiple branches can coexist and one result can be selected
- thread projection remains deterministic after replay
- non-owner writes are rejected

### Projection Regression Tests

- UI projection ordering
- current focus consistency
- branch grouping
- rationale card sourcing
- responsibility truth

### Migration/Replay Tests

- rebuild projection from stored thread entities
- rebuild projection from event log snapshots

---

## Observability

The runtime should emit metrics keyed by thread and iteration, not just by task.

Suggested metrics:

- `video_threads_created`
- `video_iterations_created`
- `video_turns_added`
- `video_results_registered`
- `video_result_selection_changes`
- `video_iteration_reopened`
- `video_iteration_branch_count`
- `video_thread_projection_rebuild_ms`
- `video_thread_agent_handoff_count`

Suggested logs:

- thread state transitions
- iteration responsibility assignments
- result selection changes
- projection rebuild failures

---

## Rollout Recommendation

Because compatibility is explicitly not required, rollout should favor architectural cleanliness over adapter complexity.

Recommended execution order:

1. Create thread-centric schema and services.
2. Attach tasks and agent runs to iterations.
3. Introduce the new `video_thread_surface` projection.
4. Replace current task-detail discussion UI with thread workbench UI.
5. Remove or deprecate the old task-lineage-derived discussion model.

Do **not** spend time building a dual-read or dual-write bridge unless a concrete migration constraint appears later.

---

## Final Recommendation

The next phase should be named:

**Phase 3: Video Thread Runtime**

Primary architectural decision:

**Promote video collaboration to a first-class runtime with thread, iteration, turn, result, and run objects. Keep task execution as an implementation detail beneath that runtime.**

This is the cleanest path to the product you want:

- continuous discussion under each video
- real agent continuity
- explicit multi-agent participation
- durable human-plus-agent iteration
- branch-aware video refinement
- product-safe explanation and process visibility

Without this shift, the system will keep looking like a sophisticated workflow wrapper. With this shift, it can become the video collaboration operating system you are aiming for.
