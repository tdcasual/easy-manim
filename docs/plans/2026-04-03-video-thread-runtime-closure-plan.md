# Video Thread Runtime Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the remaining gaps between the current thread-native video runtime and the target product shape where each video is a durable collaboration space supporting safe rationale review, continuous owner-agent discussion, and multi-agent iteration over time.

**Architecture:** Keep `video_thread_surface` as the single owner-facing read model, but finish the missing discussion-runtime layer instead of continuing to overload `iteration_detail` and `composer`. The remaining work should formalize one stable `discussion_runtime` contract, route owner follow-ups through explicit continuity/reply policy, expose richer iteration comparison and participant continuity, and then perform a cleanup pass across docs, tests, and obsolete transitional assumptions.

**Tech Stack:** FastAPI, Pydantic, SQLite, thread-native video domain models, React, TypeScript, Vitest, pytest.

---

## Current Progress Summary

The redesign has already crossed the most dangerous architectural boundary:

- `video_thread`, `video_iteration`, `video_turn`, `video_result`, and `video_agent_run` are now first-class durable runtime objects.
- The owner panel no longer depends on task-lineage reconstruction for core thread facts.
- `video_thread_surface` already exposes stable owner-facing sections for:
  - rationale: `selection_summary`, `latest_explanation`, `decision_notes`, `rationale_snapshots`
  - provenance: `artifact_lineage`, `production_journal`, `history`
  - continuity: `authorship`, `composer.target`, `participants`, `responsibility`
  - execution: `process`, `iteration_detail.execution_summary`
  - discussion structure: `discussion_groups`
- Thread-native revision continuity already survives:
  - explicit addressed participant targeting
  - revision inheritance into iteration responsibility and task metadata
  - lifecycle projection from execution tasks into stable `video_agent_run`
- Frontend already has a viable placeholder workbench and can submit owner discussion turns with:
  - addressed participant continuity
  - iteration-scoped reply anchors
  - result anchoring

This means the system is no longer missing its core runtime spine. What remains is mostly contract completion, UI composition completion, and cleanup.

## Remaining Design Gaps

The current implementation is strong, but it still falls short of the full product requirement in six ways:

1. Discussion runtime is still implicit.
   - The frontend can continue a discussion, but the canonical “active discussion under this video” contract is still spread across `discussion_groups`, `composer`, and `iteration_detail.execution_summary`.

2. The owner-facing “talk under the video” panel is not yet first-class.
   - The placeholder exists, but there is no top-level runtime section that tells the frontend exactly what thread to show, how to reply, and what sort of follow-up is recommended.

3. Multi-agent continuity is durable but not yet fully explorable.
   - Responsibility and targeting exist, but the owner still lacks one explicit runtime panel explaining which participant is currently expected to respond, which participants shaped the current state, and whether the next turn should continue one thread or start another.

4. Iteration comparison and branch navigation are still shallow.
   - The owner can inspect iterations and current rationale, but there is not yet a stable comparison-oriented contract answering “how does this iteration differ from the previous one” or “which branch should I continue.”

5. The current read model still contains transitional overlap.
   - `discussion_groups`, `composer`, and `iteration_detail.execution_summary` partially overlap in concern.
   - This is acceptable during migration, but not as the final architecture.

6. Basic closure work is not yet done.
   - We still need contract consolidation, cleanup of transitional assumptions, and a final verification/documentation pass so the runtime is easier to extend safely.

## Recommended Closure Strategy

Use a four-phase closure sequence:

1. Finish the missing runtime contracts.
2. Land the dedicated frontend discussion runtime panel.
3. Fill the remaining iteration/branch/multi-agent inspection gaps.
4. Do a deliberate cleanup and ship-readiness pass.

This order is recommended because:

- Phase 1 removes the largest remaining ambiguity in the read model.
- Phase 2 turns the owner experience into the intended product shape.
- Phase 3 improves power and clarity without destabilizing the core interaction model.
- Phase 4 ensures we stop in a clean, supportable state rather than a half-migrated one.

## Target End State

The work should be considered complete when all of the following are true:

1. A video detail page contains one explicit “discussion under the video” runtime surface.
2. The frontend can render that surface with zero inference from raw turns, runs, or iteration metadata.
3. Owner follow-ups automatically preserve:
   - iteration scope
   - result scope
   - reply continuity
   - addressed participant continuity
4. The owner can understand:
   - why the current version looks this way
   - who shaped it
   - which discussion thread is currently active
   - what the next expected reply mode is
5. The system supports durable subsequent iteration by:
   - owner
   - one shaping agent
   - additional helper/reviewer agents
6. Docs and tests clearly describe the new runtime and no longer depend on task-centric mental models where the thread runtime has replaced them.

---

## Phase 1: Formalize `discussion_runtime`

### Purpose

Create one stable top-level read model that answers:

- what discussion thread is currently active for this video
- what the current continuity scope is
- how the next owner follow-up should be sent
- whether the next message is expected to continue, branch, explain, or revise

### Recommended contract

Add a top-level surface section:

```python
class VideoThreadDiscussionRuntime(BaseModel):
    title: str = "Discussion Runtime"
    summary: str = ""
    active_iteration_id: str | None = None
    active_discussion_group_id: str | None = None
    continuity_scope: Literal["iteration", "result", "thread"] = "iteration"
    reply_policy: Literal["continue_thread", "start_new_thread", "agent_choice"] = "continue_thread"
    default_intent_type: str | None = None
    default_reply_to_turn_id: str | None = None
    default_related_result_id: str | None = None
    addressed_participant_id: str | None = None
    addressed_agent_id: str | None = None
    addressed_display_name: str | None = None
    suggested_follow_up_modes: list[str] = Field(default_factory=list)
    active_thread_title: str | None = None
    active_thread_summary: str = ""
    latest_owner_turn_id: str | None = None
    latest_agent_turn_id: str | None = None
    latest_agent_summary: str = ""
```

### Why this should be a top-level section

- `discussion_groups` is a list.
- `composer` is an input affordance.
- `iteration_detail.execution_summary` is an execution dossier.

None of those is the canonical answer to “what discussion am I currently in under this video?” That is why `discussion_runtime` should be distinct instead of adding more fields to the existing sections.

### Files

- Modify: `src/video_agent/domain/video_thread_models.py`
- Modify: `src/video_agent/application/video_projection_service.py`
- Modify: `ui/src/lib/videoThreadsApi.ts`
- Modify: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`
- Test: `tests/unit/application/test_video_projection_service.py`
- Test: `tests/integration/test_http_video_threads_api.py`
- Test: `tests/integration/test_fastmcp_video_thread_resources.py`
- Modify: `docs/runbooks/video-thread-surface-contract.md`

### Task 1.1: Write the failing backend tests

Add tests proving `video_thread_surface` exposes `discussion_runtime` with:

- iteration-scoped active discussion selection
- stable reply/result/addressed participant defaults
- explicit `reply_policy`
- explicit `suggested_follow_up_modes`

### Task 1.2: Run the backend tests to verify they fail

Run:

```bash
./.venv-codex-verify/bin/python -m pytest -q tests/unit/application/test_video_projection_service.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py -k discussion_runtime
```

Expected: FAIL because the contract is missing.

### Task 1.3: Implement the minimal projection

Build `discussion_runtime` from existing thread facts:

- prefer the selected iteration
- prefer the latest answered/open discussion group on that iteration
- fall back to `iteration_detail.execution_summary` anchors
- align addressed participant and result defaults with `composer.target`

### Task 1.4: Re-run the tests to verify they pass

Run the same command and expect PASS.

### Task 1.5: Commit

```bash
git add src/video_agent/domain/video_thread_models.py src/video_agent/application/video_projection_service.py ui/src/lib/videoThreadsApi.ts ui/src/features/videoThreads/VideoThreadPage.test.tsx tests/unit/application/test_video_projection_service.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py docs/runbooks/video-thread-surface-contract.md
git commit -m "feat: add video thread discussion runtime contract"
```

---

## Phase 2: Land the dedicated “discussion under the video” panel

### Purpose

Turn the current placeholder into the intended primary interaction surface for ongoing discussion with the generating agent(s).

### UI requirements

The panel should render directly from `discussion_runtime` plus `discussion_groups`:

- active discussion header
- addressed participant and continuity scope
- latest owner question and latest agent answer
- follow-up mode chips such as:
  - `ask_why`
  - `request_change`
  - `preserve_direction`
  - `branch_revision`
- composer strategy hint derived from `reply_policy`

### Files

- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.css`
- Modify: `ui/src/features/videoThreads/VideoThreadPage.tsx`
- Test: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`

### Task 2.1: Write the failing frontend test

Add a test proving the page renders:

- “Discussion Runtime”
- active thread title/summary
- reply policy hint
- suggested follow-up modes
- continuity scope metadata

### Task 2.2: Run the frontend test to verify it fails

Run:

```bash
npm test -- src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected: FAIL because the panel is missing.

### Task 2.3: Implement the minimal panel

Render a new section near the composer / discussion area using only stable contract fields.

Do not:

- scan raw turns in the component to compute active discussion
- derive reply mode from string heuristics in the UI

### Task 2.4: Re-run the frontend test

Run the same command and expect PASS.

### Task 2.5: Commit

```bash
git add ui/src/features/videoThreads/VideoThreadWorkbench.tsx ui/src/features/videoThreads/VideoThreadWorkbench.css ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/features/videoThreads/VideoThreadPage.test.tsx
git commit -m "feat: add dedicated discussion runtime panel"
```

---

## Phase 3: Finish multi-agent and iteration-comparison inspection

### Purpose

Make the runtime not only usable for one discussion loop, but clearly inspectable when multiple agents and multiple iterations have shaped the video.

### Scope

Add one or both of these explicit contracts:

1. `participant_runtime`
   - who is currently expected to respond
   - who recently contributed to the active iteration
   - whether the next follow-up keeps the same participant or invites another

2. `iteration_compare`
   - previous iteration id
   - current iteration id
   - selected result diff summary
   - rationale change summary
   - continuity preserved vs changed

### Recommendation

Prioritize `iteration_compare` first if the user experience is still “why does this new cut differ from the previous one?”

Prioritize `participant_runtime` first if the user experience is still “which agent am I talking to now?”

Given the current progress, `participant_runtime` is the stronger third step because continuity is now durable but not yet explicit enough for the owner.

### Files

- Modify: `src/video_agent/domain/video_thread_models.py`
- Modify: `src/video_agent/application/video_projection_service.py`
- Modify: `ui/src/lib/videoThreadsApi.ts`
- Modify: `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Test: `tests/unit/application/test_video_projection_service.py`
- Test: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`

### Task 3.1: Write the failing tests

Add tests for one new contract only, not both in one step.

### Task 3.2: Run the tests to verify failure

Use targeted pytest/vitest commands.

### Task 3.3: Implement minimal projection and placeholder rendering

Prefer concise owner-facing summaries rather than complex tables.

### Task 3.4: Re-run tests to verify green

### Task 3.5: Commit

---

## Phase 4: Cleanup and closure

### Purpose

Make the redesign feel finished instead of merely functional.

### Required closure work

1. Contract cleanup
   - review `video_thread_surface` for overlap between:
     - `discussion_runtime`
     - `discussion_groups`
     - `composer`
     - `iteration_detail.execution_summary`
   - document which section is authoritative for which question

2. Transitional logic audit
   - remove any remaining frontend inference that survived migration
   - confirm page submission flows do not reconstruct hidden semantics from raw turns

3. Documentation cleanup
   - update or supersede outdated task-centric discussion docs
   - add one concise runtime overview doc for future contributors

4. Verification cleanup
   - run full backend regression
   - run full frontend regression
   - run frontend build
   - ensure targeted thread runtime tests remain easy to run as a fast smoke suite

5. Final acceptance checklist
   - an owner can inspect why the current version exists
   - an owner can see who is currently responsible
   - an owner can continue the active video discussion under the player
   - a follow-up owner note preserves reply/result/participant continuity
   - a revision can branch from the active thread without losing context
   - the frontend renders without inference from task lineage

### Files

- Modify: `docs/runbooks/video-thread-surface-contract.md`
- Modify: `docs/plans/2026-04-01-video-thread-runtime-redesign-design.md`
- Optionally modify: superseded task-centric discussion docs if they conflict

### Task 4.1: Write the closure checklist into docs

### Task 4.2: Run full verification

Run:

```bash
./.venv-codex-verify/bin/python -m pytest -q
npm test
npm run build
```

Expected: all green.

### Task 4.3: Commit

```bash
git add docs/runbooks/video-thread-surface-contract.md docs/plans/2026-04-01-video-thread-runtime-redesign-design.md
git commit -m "docs: close video thread runtime redesign plan"
```

---

## Suggested Execution Order

Use this exact order:

1. Phase 1: `discussion_runtime`
2. Phase 2: dedicated discussion panel
3. Phase 3: one remaining runtime inspection contract
4. Phase 4: cleanup and closure

Do not start with branch comparison or visual polish first. The highest leverage remaining work is still contract completion.

## Risk Notes

### Risk 1: Overloading `iteration_detail`

If we keep solving discussion-runtime gaps by adding more fields to `iteration_detail`, the design will drift back toward a catch-all details blob.

Mitigation:

- create `discussion_runtime` as a top-level section
- keep `iteration_detail` scoped to inspected iteration dossier

### Risk 2: Frontend inference regression

The page is currently close to zero-inference, but future UI work could quietly reintroduce:

- turn scanning in components
- reply-target guessing
- result-anchor guessing

Mitigation:

- every new panel needs a stable contract
- tests should assert user-visible sections come from API data, not recomputation

### Risk 3: Confusing authority boundaries

If multiple sections answer the same product question, future contributors will keep adding duplicate logic.

Mitigation:

- use the runbook to state one canonical question per section
- explicitly mark transitional overlap where unavoidable

## Completion Criteria

This closure plan is complete when:

- `discussion_runtime` exists and is stable
- the frontend renders a dedicated discussion-under-video panel from it
- one additional multi-agent or iteration-inspection contract is landed
- the contract docs clearly assign authority to each section
- full regression and build are green
- the runtime can reasonably be called the product’s default video collaboration architecture rather than an in-progress migration

Plan complete and saved to `docs/plans/2026-04-03-video-thread-runtime-closure-plan.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per task, review between tasks, fast iteration

2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
