# Video Thread Artifact Lineage Design

**Status:** Proposed

**Date:** 2026-04-02

## Goal

Add a stable `artifact_lineage` section to `video_thread_surface` so the owner can see how the currently discussed video evolved from one visible result to the next without reconstructing that chain from iterations, turns, and results client-side.

This slice should make product-safe questions answerable directly in the UI:

- "Which result is the current cut derived from?"
- "What changed in this hop?"
- "Who pushed this change forward?"
- "Which owner or agent action led to this branch?"

## Why This Slice Next

The current thread surface already answers:

- current focus
- why this version is selected
- latest visible explanation
- who shaped this version
- what happened in discussion and production

What it still does not answer directly is the artifact evolution path.

That gap matters because long-lived video collaboration is not only a conversation problem. It is also a "which concrete version are we talking about right now?" problem. When the owner asks "why did you change this?" or "please keep this part and revise that part," the runtime needs a stable result-to-result chain that the UI and agents can both refer to.

## Recommended Approach

Use a projection-only `artifact_lineage` read model built from facts that already exist in thread runtime truth:

- `VideoIteration.source_result_id`
- `VideoIteration.selected_result_id`
- `VideoResult`
- product-safe owner and agent turns
- product-safe run summaries

Do not introduce new storage tables in this slice.

This first version should prefer explicit runtime links over speculative inference:

- derive lineage anchors from iteration `source_result_id`
- identify the resulting visible cut from iteration `selected_result_id`, falling back to the latest result in that iteration
- associate the hop with the initiating owner turn when present
- associate the hop with the visible shaping agent/run when present

## Alternatives Considered

### 1. Add `artifact_lineage`

Pros:

- directly grounds persistent video discussion in concrete result evolution
- uses existing runtime truth
- low schema risk
- creates a reusable base for later branch comparison and richer rationale snapshots

Cons:

- the first version will be chronological lineage, not a full branch graph

### 2. Add `rationale_snapshots` first

Pros:

- stronger direct answer to "why did you do this?"

Cons:

- overlaps with `decision_notes`
- less concrete for discussing revisions against specific result ids

### 3. Add per-agent discussion panels first

Pros:

- closest to end-state "talk to the generating agent"

Cons:

- risks building UI affordances before result lineage is stable
- would still leave "which artifact are we discussing?" ambiguous

## Contract Shape

Add a new top-level section:

`artifact_lineage`

Suggested shape:

```json
{
  "title": "Artifact Lineage",
  "summary": "How the current video evolved across visible revisions.",
  "selected_result_id": "result-3",
  "items": [
    {
      "lineage_id": "lineage-iter-2",
      "iteration_id": "iter-2",
      "from_result_id": "result-1",
      "to_result_id": "result-2",
      "change_summary": "Slowed the opener and made the title entrance more deliberate.",
      "change_reason": "Owner requested a more deliberate opening while preserving the existing structure.",
      "trigger_turn_id": "turn-4",
      "trigger_label": "Owner requested revision",
      "actor_display_name": "Repairer",
      "actor_role": "repairer",
      "emphasis": "primary",
      "status": "selected"
    }
  ]
}
```

## Semantics

- `artifact_lineage` is the explicit owner-facing answer to "how did this cut evolve from earlier visible cuts?"
- Each item represents one visible lineage hop, not an entire iteration or entire branch.
- `from_result_id` may be `null` for origin generations.
- `to_result_id` should point to the result produced or selected for that hop.
- `change_summary` should describe the visible change or result outcome in product-safe language.
- `change_reason` should explain the visible reason for the hop using product-safe owner or agent language. It must never expose hidden chain-of-thought.
- `trigger_turn_id` and `trigger_label` identify the visible request or explanation that best anchors the hop.
- `actor_display_name` and `actor_role` identify the visible shaping agent for that hop when available.
- `status` should be one of:
  - `selected`
  - `active`
  - `superseded`
  - `origin`

## Projection Rules

For each iteration in chronological order:

1. Resolve `to_result`:
   - prefer `iteration.selected_result_id`
   - else latest result whose `iteration_id` matches
2. Resolve `from_result_id` from `iteration.source_result_id`
3. Resolve `trigger_turn`:
   - prefer `iteration.initiated_by_turn_id`
   - else latest owner product-safe turn in the iteration
4. Resolve shaping actor:
   - prefer latest run in the iteration
   - else latest agent product-safe turn in the iteration
5. Resolve `change_summary`:
   - prefer `to_result.result_summary`
   - else `iteration.focus_summary`
   - else `iteration.goal`
6. Resolve `change_reason`:
   - prefer trigger turn summary
   - else current selection rationale when this hop is selected
   - else latest visible explanation for that iteration
7. Resolve `status`:
   - `selected` if `to_result_id == thread.selected_result_id`
   - `active` if the iteration is current and no selected result exists yet
   - `origin` if `from_result_id is null`
   - else `superseded`

## UI Expectations

The UI should render `artifact_lineage` as a dedicated panel between `decision_notes` and `production_journal`.

The first placeholder version should:

- show each hop as one card
- show `from_result_id -> to_result_id`
- show change summary and reason
- show trigger and actor chips
- visually emphasize the selected hop

The UI must not derive lineage edges from `history`, `conversation`, or `production_journal` when `artifact_lineage` is present.

## Relationship To Existing Panels

- `decision_notes`: answers "why this direction?"
- `artifact_lineage`: answers "which result evolved into which result, and why?"
- `production_journal`: answers "what happened during production?"
- `history`: answers "what visible thread events brought us here?"

These panels should overlap in facts but not in responsibility.

## Testing Strategy

Add TDD coverage for:

- projection of origin hop and revision hop
- selected-hop emphasis and status
- trigger-turn linkage
- actor linkage from run or agent turn
- API and MCP transport of the new section
- frontend placeholder rendering of the lineage cards

## Follow-On Work

Once `artifact_lineage` is stable, the next slice can build on it with:

- `rationale_snapshots`
- result comparison affordances
- explicit branch clusters
- per-agent "why this change" drill-downs
