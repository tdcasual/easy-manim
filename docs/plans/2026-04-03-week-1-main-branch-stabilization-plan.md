# Week 1 Main-Branch Stabilization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stabilize `main` after the thread-native video runtime merge by eliminating ambiguous local drift, tightening read-model authority boundaries, and producing a concrete orchestration-triage brief around `workflow_engine.py`.

**Architecture:** Do not introduce new runtime features in this week. Treat the video-thread runtime as already landed and focus on removing ambiguity: clean the root worktree, ensure owner-facing section authority is explicit, and map `workflow_engine.py` into extraction-ready responsibility seams. Prefer documentation and narrow cleanup over broad refactors.

**Tech Stack:** Git, Python, FastAPI, SQLite, Pydantic, React, TypeScript, pytest, Vitest

---

## Scope Summary

Week 1 covers three tracks only:

1. clean the remaining root-worktree drift on `main`
2. complete the authority-boundary audit for `video_thread_surface`
3. produce a narrow refactor brief for `workflow_engine.py`

Do **not** start `iteration_compare`, new owner-facing panels, or ACL implementation during this week.

## Task 1: Resolve Root Worktree Drift

**Files:**
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/adapters/storage/sqlite_bootstrap.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/workflow_engine.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/docs/plans/2026-03-30-agent-system-priority-roadmap.md`
- Modify if needed: same files
- Create if needed: `/Users/lvxiaoer/Documents/codeWork/easy-manim/docs/plans/2026-04-03-main-branch-drift-audit.md`

### Step 1.1: Capture the exact current drift

Run:

```bash
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim status -sb
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim diff -- src/video_agent/adapters/storage/sqlite_bootstrap.py
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim diff -- src/video_agent/application/workflow_engine.py
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim diff -- docs/plans/2026-03-30-agent-system-priority-roadmap.md
```

Expected: a complete view of the remaining uncommitted root-worktree edits.

### Step 1.2: Write the drift audit

Create a short audit doc that classifies each remaining change as one of:

- keep and finish in place this week
- move to a separate follow-up branch
- discard because it is superseded by merged `main`

The audit should include:

- file path
- current purpose of the edit
- why it still exists after the merge
- recommended disposition

### Step 1.3: Apply the drift decisions

Implementation notes:

- if a change is superseded, remove it safely
- if a change belongs to a later track, move it to a fresh follow-up branch or stash it with a clear name
- if a change is still needed this week, keep it and continue

Do not leave unexplained residue in the root worktree.

### Step 1.4: Verify the root worktree state is intentional

Run:

```bash
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim status -sb
```

Expected:

- either a clean root worktree
- or a very small, documented, obviously intentional set of remaining files

### Step 1.5: Commit the audit if it changed docs

```bash
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim add docs/plans/2026-04-03-main-branch-drift-audit.md docs/plans/2026-03-30-agent-system-priority-roadmap.md
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim commit -m "docs: audit post-merge main branch drift"
```

Only commit if there are real doc changes.

## Task 2: Tighten `video_thread_surface` Authority Boundaries

**Files:**
- Modify: `/Users/lvxiaoer/Documents/codeWork/easy-manim/docs/runbooks/video-thread-surface-contract.md`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/video_projection_service.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/ui/src/lib/videoThreadsApi.ts`
- Optionally modify: `/Users/lvxiaoer/Documents/codeWork/easy-manim/docs/plans/2026-04-01-video-thread-runtime-redesign-design.md`

### Step 2.1: Inspect the current overlapping sections

Read the current implementation and contract for:

- `discussion_runtime`
- `participant_runtime`
- `discussion_groups`
- `composer.target`
- `iteration_detail.execution_summary`
- `render_contract`

Use:

```bash
rg -n "discussion_runtime|participant_runtime|discussion_groups|composer.target|execution_summary|render_contract" /Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/video_projection_service.py /Users/lvxiaoer/Documents/codeWork/easy-manim/ui/src/features/videoThreads/VideoThreadWorkbench.tsx /Users/lvxiaoer/Documents/codeWork/easy-manim/ui/src/lib/videoThreadsApi.ts /Users/lvxiaoer/Documents/codeWork/easy-manim/docs/runbooks/video-thread-surface-contract.md
```

### Step 2.2: Write the “one question, one section” matrix

Add a concise matrix or bullet list to the runbook mapping each owner-facing question to exactly one canonical section.

At minimum cover:

- what discussion is active right now
- who is expected to respond
- what grouped discussion history exists
- where the next submit lands
- what the currently inspected iteration is executing
- which panels deserve default visual emphasis

### Step 2.3: Mark transitional overlap explicitly

If overlap still exists, document it directly instead of leaving it implicit.

Examples:

- `discussion_groups` is history structure, not active-thread authority
- `composer.target` is submit-time landing semantics, not historical explanation
- `iteration_detail.execution_summary` is per-iteration runtime state, not top-level discussion authority

### Step 2.4: Verify the frontend remains zero-inference by inspection

Check that `VideoThreadWorkbench.tsx` is not scanning raw turns or raw runs to reconstruct:

- active discussion thread
- expected responder
- comparison semantics

If no code change is required, record that outcome in the runbook or a short audit note.

### Step 2.5: Commit the contract cleanup

```bash
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim add docs/runbooks/video-thread-surface-contract.md docs/plans/2026-04-01-video-thread-runtime-redesign-design.md
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim commit -m "docs: tighten video thread authority boundaries"
```

## Task 3: Produce `workflow_engine.py` Refactor Triage Brief

**Files:**
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/workflow_engine.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/case_reliability_service.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/runtime_service.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/branch_arbitration.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/docs/plans/2026-03-30-agent-system-priority-roadmap.md`
- Create: `/Users/lvxiaoer/Documents/codeWork/easy-manim/docs/plans/2026-04-03-workflow-engine-triage-brief.md`

### Step 3.1: Map the responsibility clusters in `workflow_engine.py`

Use targeted search to locate:

- delivery guarantee handling
- degraded or emergency delivery
- repair and review reconciliation
- challenger-branch promotion
- branch arbitration recording
- runtime lifecycle projection

Run:

```bash
rg -n "_finalize_guaranteed_delivery|_mark_delivery_failed|_maybe_schedule_degraded_delivery|_maybe_auto_promote_challenger|_record_auto_arbitration_decision|branch_scoreboard|runtime_service" /Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/workflow_engine.py
```

### Step 3.2: Cross-check existing supporting services

Inspect nearby services to avoid recommending duplicate extractions:

- `case_reliability_service.py`
- `runtime_service.py`
- `branch_arbitration.py`

Identify which responsibilities already have natural homes and which are still trapped in the engine.

### Step 3.3: Write the triage brief

The brief should include:

- the main responsibility clusters
- estimated extraction difficulty per cluster
- coupling risks
- recommended first extraction seam
- files likely touched for that seam
- regression tests that should lock baseline behavior before refactor

### Step 3.4: Define the first extraction candidate

Recommendation to evaluate first:

- delivery resolution extraction before branch-promotion extraction

The brief must explicitly accept or reject that recommendation with reasons.

### Step 3.5: Commit the triage brief

```bash
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim add docs/plans/2026-04-03-workflow-engine-triage-brief.md
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim commit -m "docs: add workflow engine triage brief"
```

## Week 1 Verification

At the end of Week 1, run:

```bash
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim status -sb
/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/p0-session-memory/.venv-codex-verify/bin/python -m pytest -q
npm --prefix /Users/lvxiaoer/Documents/codeWork/easy-manim/ui test
npm --prefix /Users/lvxiaoer/Documents/codeWork/easy-manim/ui run build
```

Expected:

- root worktree status is clean or intentionally tiny and documented
- backend regression passes
- frontend regression passes
- frontend build passes

## Week 1 Exit Criteria

Week 1 is complete when:

- the root `main` worktree no longer contains ambiguous leftover edits
- the `video_thread_surface` authority matrix is explicit and stable
- a concrete `workflow_engine.py` extraction brief exists
- no new owner-facing runtime feature work started prematurely

