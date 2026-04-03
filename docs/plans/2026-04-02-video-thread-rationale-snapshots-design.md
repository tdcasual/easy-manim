# Video Thread Rationale Snapshots Design

**Status:** Proposed

**Date:** 2026-04-02

## Goal

Add a stable `rationale_snapshots` section to `video_thread_surface` so the owner can read the canonical product-safe "why" for each visible iteration without reconstructing rationale from `conversation`, `history`, `decision_notes`, or `artifact_lineage`.

This slice should make cross-iteration questions answerable directly:

- "What was the main rationale for the original direction?"
- "What became the canonical why for the revision?"
- "Which rationale is current versus historical?"

## Why This Slice Next

The thread surface now already answers:

- current why through `decision_notes`
- result evolution through `artifact_lineage`
- visible process and discussion through `history`, `discussion_groups`, and `production_journal`

What it still does not answer directly is the stable rationale memory across iterations.

That gap matters because persistent collaboration is not just about the current cut. Owners need a durable explanation trail that survives multiple revisions and lets them compare why the direction changed over time.

## Recommended Approach

Use a projection-only `rationale_snapshots` read model built from existing thread facts:

- iteration goal
- latest product-safe agent explanation in an iteration
- selected-result rationale for the currently selected iteration
- visible owner request turns

Do not create new storage.

This first version should create at most one canonical snapshot per iteration.

## Alternatives Considered

### 1. Add `rationale_snapshots`

Pros:

- directly supports long-lived "why" memory
- complements `decision_notes` instead of replacing it
- keeps one canonical rationale per iteration, reducing duplication

Cons:

- requires a clear priority order to avoid ambiguity

### 2. Expand `decision_notes` instead

Pros:

- fewer top-level sections

Cons:

- would blur current-state rationale with historical rationale memory
- encourages clients to infer which notes are current versus archived

### 3. Reuse `history`

Pros:

- no new panel

Cons:

- `history` is event-shaped, not rationale-shaped
- clients would still need inference

## Contract Shape

Add a new top-level section:

`rationale_snapshots`

Suggested shape:

```json
{
  "title": "Rationale Snapshots",
  "summary": "Canonical product-safe why notes across iterations.",
  "current_iteration_id": "iter-2",
  "items": [
    {
      "snapshot_id": "snapshot-iter-1",
      "iteration_id": "iter-1",
      "snapshot_kind": "owner_goal",
      "title": "Original direction",
      "summary": "Draw a circle.",
      "source_turn_id": "turn-1",
      "source_result_id": "result-1",
      "actor_display_name": "Owner",
      "actor_role": "owner",
      "emphasis": "context",
      "status": "archived"
    },
    {
      "snapshot_id": "snapshot-iter-2",
      "iteration_id": "iter-2",
      "snapshot_kind": "selection_rationale",
      "title": "Why the current revision is selected",
      "summary": "This revision remains aligned with the owner goal.",
      "source_turn_id": null,
      "source_result_id": "result-2",
      "actor_display_name": "Repairer",
      "actor_role": "repairer",
      "emphasis": "primary",
      "status": "current"
    }
  ]
}
```

## Semantics

- `rationale_snapshots` is the explicit owner-facing answer to "what are the canonical why notes across iterations?"
- Each iteration should contribute at most one snapshot.
- `snapshot_kind` should be one of:
  - `owner_goal`
  - `agent_explanation`
  - `selection_rationale`
- `status` should be:
  - `current`
  - `archived`
- `emphasis` should visually prioritize the current snapshot.

## Projection Rules

For each iteration in chronological order:

1. If the iteration is the currently selected iteration and there is a visible selection rationale, emit a `selection_rationale` snapshot.
2. Else if the iteration has a latest product-safe agent explanation, emit an `agent_explanation` snapshot.
3. Else emit an `owner_goal` snapshot from the latest visible owner request or iteration goal.

Field rules:

- `summary` should prefer the selected rationale, then explanation summary, then owner request summary, then iteration goal.
- `source_turn_id` should point at the chosen explanation/owner turn when relevant.
- `source_result_id` should point at the selected or latest visible result for that iteration when available.
- `actor_display_name` and `actor_role` should reflect the chosen rationale source.
- `status` is `current` only for the current iteration.

## UI Expectations

Render `rationale_snapshots` as a dedicated panel near `decision_notes` and `artifact_lineage`.

The first placeholder version should:

- show one card per iteration
- show snapshot title, kind, and status
- show summary
- show actor and source ids when available
- visually emphasize the current snapshot

UI consumers must not infer these snapshots from `history` or `conversation` when this section is present.

## Relationship To Existing Panels

- `decision_notes`: current focused why notes
- `artifact_lineage`: result-to-result evolution
- `rationale_snapshots`: canonical why memory across iterations
- `history`: visible events and milestones

## Testing Strategy

Add TDD coverage for:

- one snapshot per iteration
- current iteration selected-rationale priority
- fallback to agent explanation
- fallback to owner goal
- API and MCP transport
- frontend placeholder rendering
