# Video Discussion Surface Contract

This runbook defines the stable read/write contract for the `video_discussion_surface` inside:

- `GET /api/tasks/{task_id}/review-bundle`
- `GET /api/tasks/{task_id}/discussion-thread`
- `video-discussion://{task_id}/thread.json`

## Scope

Use one root-task-anchored discussion thread per video lineage.

- The thread is anchored to `root_task_id`, not the currently viewed child task.
- Owners and collaborators may read the discussion surface through `review-bundle`.
- Only the workflow owner may submit discussion messages.

Do not rebuild this surface from raw `task_events` in UI consumers once `video_discussion_surface` is present.

## Stable Read Model

Read these fields in this order:

1. `video_discussion_surface.summary`
2. `video_discussion_surface.thread_summary`
3. `video_discussion_surface.current_iteration_goal`
4. `video_discussion_surface.latest_agent_position`
5. `video_discussion_surface.rationale_cards`
6. `video_discussion_surface.current_owner_action_required`
7. `video_discussion_surface.current_agent_role_expected`
8. `video_discussion_surface.awaiting_participants`
9. `video_discussion_surface.thread_resolution_state`
10. `video_discussion_surface.iterations`
11. `video_discussion_surface.render_contract`
12. `video_discussion_surface.lineage_tasks`
13. `video_discussion_surface.participants`
14. `video_discussion_surface.participant_timeline`
15. `video_discussion_surface.composer`
16. `video_discussion_surface.discussion_entries`
17. `video_discussion_surface.process_timeline`
18. `video_discussion_surface.suggested_next_actions`

Top-level task fields and raw event payloads are supporting context only.

## Semantics

- `process_timeline`: product-safe system and agent milestones.
- `thread_summary`: one-line snapshot of where the thread currently stands.
- `current_iteration_goal`: the explicit owner-facing goal that the current lineage is trying to satisfy.
- `latest_agent_position`: the latest product-safe agent stance, explanation, or execution position for this thread.
- `rationale_cards`: product-safe snapshots of visible planning, review, and revision rationale. Never treat them as hidden chain-of-thought.
- `current_owner_action_required`: explicit owner-next-step signal. Current stable values:
  - `none`
  - `review_latest_result`
  - `provide_follow_up`
- `current_agent_role_expected`: the next visible agent role that the thread expects when agent-side work is pending.
- `awaiting_participants`: ordered participant/role list describing who the thread is currently waiting on.
- `thread_resolution_state`: thread-level resolution token, currently:
  - `open`
  - `needs_revision`
  - `resolved`
- `iterations`: stable per-turn iteration objects connecting owner requests, agent replies, and resulting child attempts.
  - `iteration_id`, `kind`, `title`, `summary`
  - `requested_action`, `preserve_working_parts`
  - `resolved_outcome`, `result_summary`
  - `selected_result_task_id`, `source_task_id`
  - `owner_entry_id`, `agent_reply_entry_id`
  - `result_task_id`, `status`
  - `created_at`, `updated_at`, `is_active`, `is_latest`
- `render_contract`: presentation defaults for the discussion surface.
- `participants`: stable thread participants for visible owner and workflow collaborators.
- `participant_timeline`: product-safe collaboration events such as workflow participant changes and workflow memory changes.
- `discussion_entries`: owner and agent turns that belong to the shared video thread.
- `suggested_next_actions`: typed affordances for common intents such as asking why a design was chosen or requesting a change.
- `latest_follow_up_prompt`: the latest owner follow-up request currently shaping the thread.
- `lineage_tasks`: stable per-attempt summaries for the root task lineage, including:
  - `task_id`, `parent_task_id`, `status`, `phase`, `delivery_status`
  - `summary`: what this attempt is trying to do in product-safe language
  - `rationale`: why this attempt exists or why the lineage moved in this direction
  - `is_viewed`, `is_active`, `is_selected`, `is_latest`
- `participants`: stable participant chips for UI consumers, including:
  - `participant_id`, `participant_type`, `role`, `display_name`, `agent_id`, `capabilities`
- `participant_timeline`: collaboration activity records, including:
  - `event_id`, `event_type`, `title`, `summary`, `created_at`
  - `participant_id`, `agent_id`, `role`, `memory_id`
- `thread_resource`: canonical machine-readable URI for the discussion thread, currently `video-discussion://{task_id}/thread.json`.

Do not expose raw chain-of-thought, hidden prompts, or private reasoning traces in any of these fields.
`summary` and `rationale` must stay intentionally authored, concise, and safe to show directly in product surfaces.

## Render Contract

`render_contract` is the presentation source of truth for discussion defaults:

- `surface_tone`: top-level tone token for the discussion surface.
- `display_priority`: whether the discussion surface should compete for attention.
- `section_order`: canonical order for visible discussion sections.
- `default_focus_section_id`: section to focus first.
- `default_expanded_section_ids`: sections expanded on first render.
- `section_presentations[]`: per-section display hints.
  - `section_id`
  - `title`
  - `summary`
  - `tone`
  - `collapsible`
- `sticky_primary_action_id`: suggested action to preselect when the UI needs one primary thread action.

Consumers should not infer section order, section titles, default expansion, or primary-action choice from raw arrays when `render_contract` is present.
When `iterations` is present, consumers should prefer it over reconstructing iteration chains from `discussion_entries` plus `lineage_tasks`.
When responsibility fields are present, consumers should prefer them over inferring "who acts next" from `thread_status` or raw participant lists.

## Root Anchoring Rules

- Persist discussion events on the root task.
- Preserve the originating `task_id` on each entry so the UI can show which attempt a turn belongs to.
- Child tasks should read the same root-thread history when they request `review-bundle`.
- Thread-specific consumers should prefer `GET /api/tasks/{task_id}/discussion-thread`, which returns the same stable surface without requiring sidebar review data.

## Composer Contract

`composer` is the source of truth for submission affordances:

- `title`
- `placeholder`
- `submit_label`
- `disabled`
- `disabled_reason`

If `composer.disabled` is `true`, the UI should not submit discussion messages.

## Submission Contract

Owners submit follow-ups with:

- `POST /api/tasks/{task_id}/discussion-messages`

Request body:

- `title`
- `summary`
- `requested_action`
- `preserve_working_parts`

Current `requested_action` values:

- `discuss`: append the owner message and refresh the current thread.
- `revise`: append the owner message, append an agent reply, create a child revision, and return navigate semantics.

## Refresh Contract

Submission responses may include:

- `created_task_id`
- `refresh_scope`
- `refresh_task_id`

Consumers should respect these fields exactly rather than inferring navigation or refresh behavior from the presence of discussion entries.

## UI Entry Point

The typed UI consumer entry point lives in [tasksApi.ts](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/p0-session-memory/ui/src/lib/tasksApi.ts) as:

- `getReviewBundle()`
- `createTaskDiscussionMessage()`
