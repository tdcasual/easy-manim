# Owner Review Panel Contract

This runbook defines the stable read contract for owner-side workflow review surfaces.

## Scope

Use `GET /api/tasks/{task_id}/review-bundle` or MCP `get_review_bundle` and read `workflow_review_controls`.

Owner-only:
- `workflow_review_controls` is present for the workflow owner.
- collaborators and non-owners receive `workflow_review_controls: null`.

Do not reconstruct owner review panel state from top-level task fields, recent events, or action payloads when `workflow_review_controls` is present.

## Stable Read Model

Read these fields in this order:

1. `workflow_review_controls.render_contract`
2. `workflow_review_controls.panel_header`
3. `workflow_review_controls.action_sections`
4. `workflow_review_controls.status_summary`
5. `workflow_review_controls.applied_action_feedback`

Treat `suggested_next_actions`, `available_actions`, `recent_memory_events`, and raw action payloads as supporting detail, not the primary render contract.

## Render Contract

`render_contract` is the presentation source of truth for panel-level defaults:

- `panel_tone`: top-level tone token for the owner review panel.
- `display_priority`: whether the panel should compete for attention.
- `badge_order`: canonical badge order for `panel_header.badges`.
- `section_order`: canonical section order for `action_sections.items`.
- `default_focus_section_id`: section to focus first.
- `default_expanded_section_ids`: sections expanded on first render.
- `section_presentations[]`: per-section display hints.
  - `section_id`
  - `tone`
  - `collapsible`
- `sticky_primary_action_id`: CTA that may stay pinned.
- `sticky_primary_action_emphasis`: CTA emphasis token for layouts with one persistent action.
- `applied_feedback_dismissible`: whether footer feedback may be user-dismissed.

Consumers should not infer any of the above from badge ids, section ids, or action states when `render_contract` is present.

## Header

`panel_header` is the header source of truth:

- `title`
- `tone`
- `summary`
- `badges[]`
- `highlighted_event`

Use `render_contract.badge_order` to order `panel_header.badges`; do not preserve backend insertion order by accident.

## Sections

`action_sections.items` is the renderable section list:

- each section already includes `section_id`, `title`, `summary`, and `items`
- each action card already includes `button_label`, `action_family`, `blocked`, `is_primary`, and typed `intent`

Use `render_contract.section_order` and `render_contract.section_presentations` instead of inferring section priority or collapsibility from `section_id`.

## Footer

`applied_action_feedback` is the footer source of truth when present:

- it explains the latest applied workflow-memory mutation
- it includes the recommended follow-up action id when one exists
- `render_contract.applied_feedback_dismissible` decides whether the footer can be dismissed

Do not synthesize footer copy from `recent_memory_events` plus `status_summary` in consumers.

## UI Entry Point

The typed UI consumer entry point lives in [tasksApi.ts](/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/p0-session-memory/ui/src/lib/tasksApi.ts) as `getReviewBundle()`.

New UI work should start from that typed API helper rather than issuing ad-hoc fetches for review bundle data.
