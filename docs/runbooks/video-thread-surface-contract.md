# Video Thread Surface Contract

`video_thread_surface` is the owner-facing read model for the thread-native video collaboration runtime.

Current top-level sections:

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
- `conversation`
- `history`
- `production_journal`
- `discussion_groups`
- `discussion_runtime`
- `participant_runtime`
- `process`
- `participants`
- `actions`
- `composer`
- `iteration_detail`
- `render_contract`

Rules:

- UI consumers should render directly from this projection.
- Explanations and process notes must remain `product_safe`.
- `current_focus` is the primary visual anchor.
- `current_focus.current_result_author_display_name`, `current_focus.current_result_author_role`, and `current_focus.current_result_selection_reason` are the stable owner-facing explanation fields for the currently selected or active version.
- `selection_summary` is the explicit owner-facing answer to "why this version?" and should mirror the currently active selection rationale instead of forcing clients to extract it from `current_focus`.
- `latest_explanation` is the explicit owner-facing answer to "what did the agent most recently explain?" and may fall back to the latest visible process summary when no dedicated explanation turn exists yet.
- `decision_notes` is the explicit owner-facing answer to "why is the video shaped this way right now?" It should project product-safe rationale notes from stable thread facts such as selected-result rationale, latest visible explanation, and the active iteration goal so clients do not assemble or rank these notes themselves.
- `artifact_lineage` is the explicit owner-facing answer to "which visible result evolved into which result?" It should project product-safe lineage hops from thread iterations, result links, owner trigger turns, and shaping agent facts so clients do not infer artifact ancestry from `history`, `production_journal`, or raw iteration metadata.
- `rationale_snapshots` is the explicit owner-facing answer to "what was the canonical rationale for each visible iteration?" It should project at most one product-safe rationale snapshot per iteration, preferring selected-result rationale when a visible result is actually selected, then the latest visible agent explanation, then the owner goal.
- `authorship` is the explicit owner-facing answer to "who most recently shaped this version?" It should prefer the latest relevant agent run, then fall back to the latest visible agent turn, then the assigned responsible role.
- `next_recommended_move` is the explicit owner-facing answer to "what should happen next?" and carries the recommended action id/label plus the current owner-action state.
- `history.cards` is the explicit owner-facing answer to "how did this video get here?" It should be built only from product-safe turns, result-selection rationale, and runtime summaries. It must never expose hidden reasoning.
- `production_journal` is the explicit owner-facing answer to "how was this version produced?" It should project stable iteration, run, and result milestones in chronological order, including direct resource refs when available.
- `discussion_groups.groups[]` is the explicit owner-facing answer to "which discussion threads are active around this video?" Each group should project one owner prompt root plus its direct replies so clients do not reconstruct reply chains themselves.
- `discussion_runtime` is the explicit owner-facing answer to "which discussion under this video is active right now, and how should the next follow-up be sent?" It should project the active iteration-scoped discussion group, reply continuity, result anchoring, addressed participant continuity, and stable suggested follow-up modes so the frontend never guesses which question/answer pair or shaping participant should receive the next owner turn.
- `participant_runtime` is the explicit owner-facing answer to "which participant am I currently talking to, who else recently shaped this iteration, and does the next follow-up stay with the same agent?" It should project the expected responder plus concise recent contributor summaries so the frontend does not derive participant continuity from `participants`, raw turns, or raw runs.
- `iteration_detail` is the explicit owner-facing answer to "what exactly happened in the currently inspected iteration?" The surface-level summary should identify the selected iteration, its canonical resource URI, visible turn/run/result counts, and a stable `execution_summary` so the workbench shell can fetch and place a detail pane without guessing targets or synthesizing runtime state from raw runs.
- `conversation.turns` and `history.cards` may carry `intent_type`, `reply_to_turn_id`, and `related_result_id` so clients can render structured collaboration semantics such as "this was a why-question", "this explanation answered that question", or "this revision request targeted the selected result".
- `discussion_groups.groups[]` should carry `prompt_intent_type`, `status`, `related_result_id`, and reply metadata so the frontend can render stable discussion clusters without inferring answered/open state.
- `discussion_runtime` should carry stable `continuity_scope`, `reply_policy`, `default_intent_type`, `default_reply_to_turn_id`, `default_related_result_id`, addressed participant/agent identity, active thread title/summary, latest owner/agent turn anchors, and `suggested_follow_up_modes` so the frontend can render and submit the active "discussion under the video" experience with zero inference.
- `participant_runtime` should carry stable expected participant identity, expected role, continuity mode, follow-up target lock state, and recent contributor summaries so the frontend can explain current multi-agent continuity without reconstructing ownership or recency rules from raw runtime facts.
- `production_journal.entries[]` should carry stable `entry_kind`, `stage`, `status`, actor labels, ids, and `resource_refs` so the frontend can render a placeholder process log without joining iterations, runs, results, or artifacts client-side.
- `decision_notes.items[]` should carry stable `note_kind`, `title`, `summary`, `emphasis`, source ids, and actor labels so the frontend can render a dedicated rationale panel without reconstructing "why" notes from `selection_summary`, `latest_explanation`, or iteration metadata.
- `artifact_lineage.items[]` should carry stable `from_result_id`, `to_result_id`, `change_summary`, `change_reason`, trigger metadata, actor labels, `status`, and `emphasis` so the frontend can render visible result evolution without reconstructing parent-child result hops client-side.
- `rationale_snapshots.items[]` should carry stable `snapshot_kind`, `iteration_id`, `headline`, `summary`, source ids, actor labels, and `status` so the frontend can render cross-iteration rationale memory without stitching together `decision_notes`, `history`, or per-iteration turn scans.
- `iteration_detail` should carry stable `selected_iteration_id`, `resource_uri`, visible item counts, and `execution_summary` in the surface. The detail resource at `GET /api/video-threads/{thread_id}/iterations/{iteration_id}` and `video-thread://{thread_id}/iterations/{iteration_id}.json` should carry the selected iteration object plus product-safe `execution_summary`, `turns`, `runs`, and `results` so the frontend can render a current-iteration dossier without joining raw thread tables client-side.
- `iteration_detail.turns[]` may carry `addressed_participant_id`, `addressed_agent_id`, and `addressed_display_name` so the frontend can show which visible owner prompts were explicitly directed at which participant without reconstructing reply intent from speaker metadata alone.
- `iteration_detail.execution_summary` is the explicit owner-facing answer to "who is executing this iteration right now, against which task/result, and in what phase?" It should prefer the latest projected thread-native `video_agent_run`, then fall back to the iteration's explicit continuity target when no run exists yet, so clients never infer active execution from raw run arrays, task records, or author heuristics.
- `iteration_detail.execution_summary` should also carry iteration-scoped discussion anchors such as `discussion_group_id`, `reply_to_turn_id`, `latest_owner_turn_id`, and `latest_agent_turn_id` so the frontend can continue the currently inspected video conversation without reconstructing which visible question/answer pair should receive the next owner follow-up.
- `intent_type` should use product-safe collaboration verbs such as `generate`, `discuss`, `request_explanation`, and `request_revision` rather than internal workflow phase names.
- `participants.items` is the durable thread participant roster. The owner should always appear when the thread exists.
- `participants.management` is the owner-facing participant governance contract. It carries invite/remove affordance labels, default role/capabilities, removable ids, and viewer-scoped disabled reasons so the frontend does not infer mutation rules.
- Thread participant mutation is owner-scoped at runtime. `POST /api/video-threads/{thread_id}/participants` and `DELETE /api/video-threads/{thread_id}/participants/{participant_id}` are reserved for the thread owner even when other authenticated agents can read the thread.
- The current frontend consumes `participants.management` directly and exposes inline invite/remove controls inside the participants panel.
- `actions.items` and `composer` carry display copy, disabled state, and contextual guidance so the workbench does not infer action semantics client-side.
- `composer.target` is the explicit owner-facing answer to "where will the next message land?" It should identify the targeted iteration, visible result, explicitly addressed participant/agent continuity target, and expected agent role/display name so the frontend can render and submit follow-ups without guessing anchoring semantics.
- `composer.target.addressed_participant_id`, `composer.target.addressed_agent_id`, and `composer.target.addressed_display_name` are the durable thread-native continuity fields for "talk to the agent that shaped this video." They should prefer the explicitly responsible participant, then the latest addressed owner turn on the selected iteration, then the latest visible iteration/runtime agent continuity facts before falling back thread-wide.
- Authority boundary summary:
  - `discussion_runtime` answers "which discussion thread is active and how should the next follow-up attach?"
  - `participant_runtime` answers "which participant is expected now and who else recently shaped this iteration?"
  - `discussion_groups` answers "what visible grouped discussion threads exist under this video?"
  - `composer.target` answers "where will the submit action land if the owner sends a new turn right now?"
  - `iteration_detail.execution_summary` answers "what is the currently inspected iteration doing at runtime?"
- `request_revision` should inherit the selected iteration's active continuity target into the newly created iteration. That means the new iteration should immediately carry `responsible_role` and `responsible_agent_id` when the parent iteration already had an explicit addressed/continuity target, so the owner-facing surface and the downstream runtime agree on who is expected to continue the work.
- `iteration_workbench.selected_iteration_id`, `render_contract.default_focus_panel`, and the presence/order of the summary sections must be stable enough for zero-inference rendering.
- `render_contract.sticky_primary_action_id`, `render_contract.sticky_primary_action_emphasis`, `render_contract.panel_tone`, `render_contract.display_priority`, `render_contract.badge_order`, and `render_contract.panel_presentations[]` are authoritative presentation hints for the workbench shell.
- `render_contract.panel_presentations[]` should carry panel-level tone, emphasis, collapse behavior, and default-open state so the frontend does not guess which cards deserve visual priority.
- `render_contract.panel_order` and `panel_presentations[]` should treat `discussion_runtime`, `participant_runtime`, and `iteration_detail` as first-class panes whenever the surface exposes those runtime sections.
- `iteration_detail.composer_target` should mirror the per-iteration submit target so selecting an older iteration can still produce explicitly targeted discussion or revision follow-ups instead of silently falling back to the thread's current result.
- `POST /api/video-threads/{thread_id}/turns` and `append_video_turn` may carry `addressed_participant_id`, `reply_to_turn_id`, and `related_result_id`. The runtime must persist them onto the owner turn and still derive `addressed_agent_id` so later surface projections can preserve participant continuity and discussion anchoring without frontend-side joins or heuristics.
- Thread-native revision tasks should persist continuity target metadata at task level as well, so later runtime orchestration can recover the intended participant/agent handoff even when it is reading task/task-lineage state instead of thread turns directly.
- When a thread-native task with persisted continuity target actually enters runtime lifecycle execution, the execution layer should project or update one stable `video_agent_run` for that task/iteration so the owner-facing thread surface can observe real planner/generator/reviewer progress as activity from the intended shaping participant rather than losing continuity at worker time.
- Thread-native participant transport is in contract:
  - `GET /api/video-threads/{thread_id}/participants`
  - `POST /api/video-threads/{thread_id}/participants`
  - `DELETE /api/video-threads/{thread_id}/participants/{participant_id}`
- Legacy task discussion transports are out of contract:
  - `/api/tasks/{task_id}/discussion-thread`
  - `/api/tasks/{task_id}/discussion-messages`
  - `video-discussion://...`

## Closure Checklist

- An owner can inspect why the current version exists from `selection_summary`, `decision_notes`, `rationale_snapshots`, and `latest_explanation`.
- An owner can see who is currently responsible from `participant_runtime`, `responsibility`, and `authorship`.
- An owner can continue the active discussion under the video from `discussion_runtime`, `discussion_groups`, and `composer.target`.
- A follow-up owner note preserves reply continuity, result anchoring, and participant continuity through `discussion_runtime` and `composer.target`.
- A revision can branch from the active thread without losing continuity because the runtime persists iteration/result/participant targeting into new iteration responsibility and execution state.
- The frontend should render from `video_thread_surface` plus iteration detail resources without inferring semantics from task lineage or raw workflow memory.
