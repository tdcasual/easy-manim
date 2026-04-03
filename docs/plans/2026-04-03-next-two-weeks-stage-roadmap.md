# Next Two Weeks Stage Roadmap

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this roadmap task-by-task when execution starts.

**Goal:** Move `easy-manim` from a successfully landed thread-native video collaboration runtime into a cleaner, more supportable productization phase over the next two weeks.

**Architecture:** Treat the current thread-native video runtime as the new default owner-facing architecture, not as an experiment. The next two weeks should avoid inventing new runtime layers unless they close a clear product gap. Priority should shift toward main-branch cleanup, explicit comparison/branch-inspection contracts, workflow collaboration governance, and reducing orchestration complexity around oversized engine files.

**Tech Stack:** Python, FastAPI, MCP, Pydantic, SQLite, React, TypeScript, Vitest, pytest

---

## Stage Map

The project is no longer in pure architecture discovery. It is now between late-stage migration and early-stage product hardening.

### Stage 1: Validation And Task-Centric Proof

This stage proved:

- task execution could drive agent collaboration
- review bundles could surface safe summaries
- owner workflows could be mediated through supervised automation

This stage is complete.

### Stage 2: Thread-Native Runtime Migration

This stage introduced:

- `video_thread`, `video_iteration`, `video_turn`, `video_result`, and `video_agent_run`
- thread-native owner-facing read models
- durable discussion and participant continuity
- a dedicated video-thread workbench in the frontend

This stage is also complete in its core architectural sense.

### Stage 3: Productization And Runtime Hardening

This is the current stage.

Its characteristics are:

- the new runtime is already real and verified
- the owner-facing experience is usable
- the architecture now needs cleanup, comparison power, and governance
- the biggest risks come from overlap, drift, and oversized orchestration modules rather than from missing core runtime objects

### Stage 4: Platform-Grade Evolution

This future stage should focus on:

- broader autonomy without losing supervision
- stronger multi-agent participation rules
- comparison and branching tools that scale with many iterations
- sustained maintainability of orchestration and memory systems

The project is not there yet.

## Current State Summary

### What Is Already Strong

- The thread-native video collaboration runtime is landed on `main`.
- `video_thread_surface` is the canonical owner-facing read model.
- `discussion_runtime` and `participant_runtime` now make active discussion continuity explicit.
- The frontend can render and submit against stable contracts instead of reconstructing semantics client-side.
- Full verification has already passed on the merged result:
  - `pytest -q`
  - `npm test`
  - `npm run build`

### What Still Makes The Project Feel Mid-Transition

- The root worktree still contains local in-progress edits outside the just-merged runtime line:
  - `src/video_agent/adapters/storage/sqlite_bootstrap.py`
  - `src/video_agent/application/workflow_engine.py`
  - `docs/plans/2026-03-30-agent-system-priority-roadmap.md`
- Cross-iteration comparison and branch navigation are still weaker than discussion continuity.
- Orchestration responsibility is still too concentrated in files such as `workflow_engine.py`.
- The old roadmap for memory, collaboration ACLs, and orchestration refactor remains valid and now needs to be reconciled with the new video-thread runtime reality.

## Two-Week Objective

The next two weeks should not try to start a new architecture wave.

They should accomplish four things:

1. Clean and stabilize the just-landed main branch.
2. Finish the most important missing owner-facing inspection contract: iteration comparison.
3. Reconcile the older agent-system roadmap with the new thread-native runtime.
4. Reduce operational and maintenance risk around orchestration hotspots.

## Week 1: Main-Branch Stabilization And Runtime Cleanup

### Primary Goal

Turn the current state from "merged and passing" into "clean enough to extend safely."

### Track 1: Resolve Local Main-Branch Drift

**Outcome:** The root worktree no longer carries ambiguous leftover edits from before the merge.

**Tasks:**

- audit the remaining local changes in `sqlite_bootstrap.py`, `workflow_engine.py`, and `2026-03-30-agent-system-priority-roadmap.md`
- classify each one as:
  - keep and complete now
  - move into a separate follow-up branch
  - discard as superseded by merged work
- restore a clean root worktree once those decisions are applied

**Success criteria:**

- `git status` on `main` is intentional, understandable, and ideally clean
- no teammate needs tribal knowledge to explain which changes are "real" vs "leftover"

### Track 2: Authority-Boundary Audit

**Outcome:** The runtime remains zero-inference as it grows.

**Tasks:**

- inspect overlap between:
  - `discussion_runtime`
  - `participant_runtime`
  - `discussion_groups`
  - `composer.target`
  - `iteration_detail.execution_summary`
- confirm each question has one canonical answering section
- tighten docs anywhere the authority boundary is still implicit

**Success criteria:**

- future contributors can answer "where should this owner-facing field live?" without guessing
- no new frontend work needs to scan turns, runs, or task lineage

### Track 3: `workflow_engine.py` Triage

**Outcome:** Reduce near-term risk before deeper refactor begins.

**Tasks:**

- map the major responsibility clusters inside `workflow_engine.py`
- identify which blocks are:
  - delivery resolution
  - degraded/emergency delivery policy
  - repair/review reconciliation
  - branch arbitration and promotion
  - runtime lifecycle projection
- write a small refactor brief rather than performing a broad extraction immediately

**Success criteria:**

- there is a shared understanding of which seam should be extracted first
- the file stops being treated as a single undifferentiated control center

### Week 1 Stop/Go Rule

Do not start new product-facing features in Week 1 unless the local main-branch drift and orchestration hotspot audit are under control.

## Week 2: Comparison And Collaboration Governance

### Primary Goal

Finish the highest-leverage product gap left after the runtime closure pass, then reconnect that work to the older platform roadmap.

### Track 1: Add `iteration_compare`

**Outcome:** Owners can understand how one visible cut differs from the previous one without reconstructing history themselves.

**Recommended contract direction:**

- previous iteration id
- current iteration id
- previous selected result id
- current selected result id
- visible change summary
- rationale shift summary
- continuity preserved vs changed
- branch recommendation or continuation hint

**Files likely involved:**

- `src/video_agent/domain/video_thread_models.py`
- `src/video_agent/application/video_projection_service.py`
- `ui/src/lib/videoThreadsApi.ts`
- `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- `tests/unit/application/test_video_projection_service.py`
- `ui/src/features/videoThreads/VideoThreadPage.test.tsx`
- `docs/runbooks/video-thread-surface-contract.md`

**Success criteria:**

- the owner can answer "what changed and why?" from one explicit surface section
- the frontend still renders without inference from raw iteration history

### Track 2: Reconcile With Workflow Collaboration ACL Roadmap

**Outcome:** The older agent-system roadmap becomes consistent with the new runtime, rather than diverging from it.

**Tasks:**

- revisit the P1 collaboration ACL plan in `2026-03-30-agent-system-priority-roadmap.md`
- restate the ACL goal in thread-native language:
  - thread participants
  - workflow participants
  - reviewer/verifier access
  - owner-only mutation boundaries
- decide whether the next implementation wave should be:
  - review-bundle/workflow ACLs first
  - video-thread participant permissions first
  - a unified participant/governance layer

**Success criteria:**

- there is one coherent participation model across task workflows and video threads
- future collaboration features do not split into two unrelated permission systems

### Track 3: Choose The First Orchestration Extraction

**Outcome:** P2 refactor work starts from one narrow, justified seam rather than a large rewrite.

**Recommendation:**

- start with delivery-resolution extraction before branch-promotion extraction

Reasoning:

- it is easier to bound
- it directly touches reliability and user-visible outcomes
- it reduces risk in the already-conflicted region of `workflow_engine.py`

**Success criteria:**

- one extraction target is chosen with explicit file boundaries
- there is a short execution plan ready for implementation

### Week 2 Stop/Go Rule

If `iteration_compare` is not yet stable, do not open multiple new UI/runtime fronts in parallel. Finish comparison first, then move into ACL or refactor work.

## Priority Order

Use this order over the next two weeks:

1. clean the root `main` worktree and remove ambiguity
2. complete authority-boundary and orchestration triage
3. land `iteration_compare`
4. reconcile and choose the next collaboration ACL direction
5. begin one narrow orchestration extraction

## Risks To Watch

### Risk 1: Reintroducing Frontend Inference

As new panels appear, developers may be tempted to compute continuity or comparison in React.

Mitigation:

- every new owner-facing panel must be backed by a stable projection contract
- tests should keep asserting contract-first rendering

### Risk 2: Two Competing Collaboration Models

The older workflow ACL roadmap and the new video-thread participant system may drift apart.

Mitigation:

- make one explicit governance decision in Week 2
- document whether the next ACL layer is unified or intentionally layered

### Risk 3: `workflow_engine.py` Continues To Accrete

Recent merge and stash recovery already touched the same region, which is a warning sign.

Mitigation:

- do not keep adding unrelated responsibilities to the same area
- extract one narrow service before the next large orchestration change

### Risk 4: False Sense Of Completion

Because the runtime architecture is landed and tests pass, the team may assume the system is "done."

Mitigation:

- treat the current state as productization, not finish line
- prioritize comparison, governance, and maintainability before broader feature expansion

## Acceptance Criteria For The End Of The Two Weeks

This roadmap is successful if, by the end of the two-week window:

- `main` is clean or intentionally cleanly partitioned
- the video-thread runtime has one explicit iteration-comparison surface
- the collaboration-governance direction is documented in thread-native terms
- `workflow_engine.py` has a chosen first extraction seam with a written implementation plan
- the system still passes full backend and frontend verification after that work

## Recommended Execution Mode

Use this roadmap as a sequencing document, not as a single batch implementation plan.

Recommended rhythm:

1. Week 1 closes cleanliness and authority questions.
2. Week 2 lands one product-facing comparison contract plus one governance/refactor decision.

When implementation starts for any one track, create a dedicated plan document and execute it with `executing-plans`.
