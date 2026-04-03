# Week 2 Comparison And Governance Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the highest-value remaining product gap after the thread-native runtime closure pass by adding explicit iteration comparison, then align collaboration governance and choose the first orchestration extraction seam.

**Architecture:** Extend the existing `video_thread_surface` instead of inventing another owner-facing runtime object. `iteration_compare` should become a single explicit section answering “what changed from the previous cut and why?” Governance work should reconcile workflow-level collaboration permissions with thread-native participant continuity. Refactor work this week should stop at seam selection and plan finalization unless the comparison contract finishes early and remains stable.

**Tech Stack:** Python, FastAPI, SQLite, Pydantic, React, TypeScript, Vitest, pytest

---

## Scope Summary

Week 2 covers three tracks:

1. implement `iteration_compare`
2. reconcile workflow collaboration ACL direction with thread-native runtime
3. choose the first orchestration extraction with a ready-to-run follow-up plan

If `iteration_compare` is unstable, pause the other two tracks and finish it first.

## Task 1: Land `iteration_compare`

**Files:**
- Modify: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/domain/video_thread_models.py`
- Modify: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/video_projection_service.py`
- Modify: `/Users/lvxiaoer/Documents/codeWork/easy-manim/ui/src/lib/videoThreadsApi.ts`
- Modify: `/Users/lvxiaoer/Documents/codeWork/easy-manim/ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Modify: `/Users/lvxiaoer/Documents/codeWork/easy-manim/ui/src/features/videoThreads/VideoThreadWorkbench.css`
- Modify: `/Users/lvxiaoer/Documents/codeWork/easy-manim/docs/runbooks/video-thread-surface-contract.md`
- Test: `/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/unit/application/test_video_projection_service.py`
- Test: `/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_http_video_threads_api.py`
- Test: `/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_fastmcp_video_thread_resources.py`
- Test: `/Users/lvxiaoer/Documents/codeWork/easy-manim/ui/src/features/videoThreads/VideoThreadPage.test.tsx`

### Step 1.1: Write the failing backend tests

Add tests that prove `video_thread_surface` exposes one explicit `iteration_compare` section with at least:

- previous iteration id
- current iteration id
- previous result id
- current result id
- visible change summary
- rationale shift summary
- continuity status

Prefer adding assertions to existing video-thread projection tests before creating new test files.

### Step 1.2: Run the targeted backend tests and verify red

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/p0-session-memory/.venv-codex-verify/bin/python -m pytest -q /Users/lvxiaoer/Documents/codeWork/easy-manim/tests/unit/application/test_video_projection_service.py /Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_http_video_threads_api.py /Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_fastmcp_video_thread_resources.py
```

Expected: FAIL because `iteration_compare` does not exist yet.

### Step 1.3: Implement the minimal backend contract

Implementation notes:

- prefer the selected/current iteration
- compare to the nearest previous visible iteration
- derive summaries from existing stable facts such as:
  - selected results
  - decision notes
  - rationale snapshots
  - authorship or responsibility continuity
- avoid adding a free-form diff engine

### Step 1.4: Write the failing frontend test

Extend `VideoThreadPage.test.tsx` to prove the page renders:

- the comparison section title
- previous vs current identifiers or labels
- change summary
- continuity preserved vs changed

### Step 1.5: Run the frontend test and verify red

Run:

```bash
npm --prefix /Users/lvxiaoer/Documents/codeWork/easy-manim/ui test -- src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected: FAIL because the comparison panel is missing.

### Step 1.6: Implement the minimal frontend panel

Use only stable contract fields from `iteration_compare`.

Do not:

- scan raw iteration arrays in React to compute previous/current diffs
- derive continuity state from string heuristics in the UI

### Step 1.7: Re-run targeted tests and verify green

Run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/p0-session-memory/.venv-codex-verify/bin/python -m pytest -q /Users/lvxiaoer/Documents/codeWork/easy-manim/tests/unit/application/test_video_projection_service.py /Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_http_video_threads_api.py /Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_fastmcp_video_thread_resources.py
npm --prefix /Users/lvxiaoer/Documents/codeWork/easy-manim/ui test -- src/features/videoThreads/VideoThreadPage.test.tsx
```

Expected: PASS.

### Step 1.8: Commit

```bash
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim add src/video_agent/domain/video_thread_models.py src/video_agent/application/video_projection_service.py ui/src/lib/videoThreadsApi.ts ui/src/features/videoThreads/VideoThreadWorkbench.tsx ui/src/features/videoThreads/VideoThreadWorkbench.css ui/src/features/videoThreads/VideoThreadPage.test.tsx docs/runbooks/video-thread-surface-contract.md tests/unit/application/test_video_projection_service.py tests/integration/test_http_video_threads_api.py tests/integration/test_fastmcp_video_thread_resources.py
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim commit -m "feat: add iteration comparison runtime surface"
```

## Task 2: Reconcile Workflow Collaboration ACL Direction

**Files:**
- Modify: `/Users/lvxiaoer/Documents/codeWork/easy-manim/docs/plans/2026-03-30-agent-system-priority-roadmap.md`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/workflow_collaboration_service.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/multi_agent_workflow_service.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/video_thread_service.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/server/http_api.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/server/mcp_tools.py`
- Create: `/Users/lvxiaoer/Documents/codeWork/easy-manim/docs/plans/2026-04-03-collaboration-governance-alignment.md`

### Step 2.1: Read the current workflow-side collaboration system

Inspect:

- workflow participants and capabilities
- review-decision authorization
- owner-only workflow participant management

Use:

```bash
rg -n "workflow_participants|authorize_review_decision|participants|can_manage|capabilities" /Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/workflow_collaboration_service.py /Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/multi_agent_workflow_service.py /Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/server/http_api.py /Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/server/mcp_tools.py
```

### Step 2.2: Read the thread-side participant model

Inspect:

- thread participant roster
- participant management rules
- continuity targeting fields

Use:

```bash
rg -n "video_thread_participants|participant_runtime|participants.management|addressed_participant_id|addressed_agent_id" /Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/video_thread_service.py /Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/video_projection_service.py /Users/lvxiaoer/Documents/codeWork/easy-manim/docs/runbooks/video-thread-surface-contract.md
```

### Step 2.3: Write the governance alignment note

The note must answer:

- what is shared between workflow participants and thread participants
- what remains distinct
- where owner-only mutation boundaries should live
- whether the next ACL implementation wave should be:
  - workflow ACL first
  - thread participant permissions first
  - unified governance layer first

### Step 2.4: Update the old roadmap language

Revise `2026-03-30-agent-system-priority-roadmap.md` so the ACL section no longer sounds task-only if the new thread-native model is now the product default.

### Step 2.5: Commit

```bash
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim add docs/plans/2026-03-30-agent-system-priority-roadmap.md docs/plans/2026-04-03-collaboration-governance-alignment.md
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim commit -m "docs: align collaboration governance roadmap"
```

## Task 3: Choose The First Orchestration Extraction Seam

**Files:**
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/workflow_engine.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/case_reliability_service.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/task_service.py`
- Inspect: `/Users/lvxiaoer/Documents/codeWork/easy-manim/src/video_agent/application/branch_arbitration.py`
- Test: `/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_task_reliability_reconciler.py`
- Test: `/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_multi_agent_workflow_service.py`
- Test: `/Users/lvxiaoer/Documents/codeWork/easy-manim/tests/integration/test_http_task_reliability_api.py`
- Create: `/Users/lvxiaoer/Documents/codeWork/easy-manim/docs/plans/2026-04-03-first-orchestration-extraction-plan.md`

### Step 3.1: Lock the current behavior surface by reading the tests

Inspect the existing refactor-sensitive integration tests to understand what must not regress.

### Step 3.2: Compare delivery-resolution and branch-promotion seams

For each seam, evaluate:

- code concentration in `workflow_engine.py`
- existing helper/service support
- coupling to `task_service` and `case_reliability_service`
- regression blast radius

### Step 3.3: Pick one seam and write the extraction plan

The extraction plan should include:

- exact files to create or modify
- which methods move first
- which tests to characterize before moving code
- what remains intentionally inside `workflow_engine.py`

### Step 3.4: Prefer delivery resolution unless the evidence says otherwise

Default recommendation:

- extract delivery resolution first

Only override this if the inspection clearly shows branch-promotion extraction is lower risk.

### Step 3.5: Commit

```bash
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim add docs/plans/2026-04-03-first-orchestration-extraction-plan.md
git -C /Users/lvxiaoer/Documents/codeWork/easy-manim commit -m "docs: choose first orchestration extraction seam"
```

## Week 2 Verification

At minimum, after `iteration_compare` lands, run:

```bash
/Users/lvxiaoer/Documents/codeWork/easy-manim/.worktrees/p0-session-memory/.venv-codex-verify/bin/python -m pytest -q
npm --prefix /Users/lvxiaoer/Documents/codeWork/easy-manim/ui test
npm --prefix /Users/lvxiaoer/Documents/codeWork/easy-manim/ui run build
```

Expected: full backend and frontend verification still pass.

## Week 2 Exit Criteria

Week 2 is complete when:

- `iteration_compare` exists as a stable owner-facing surface
- the frontend renders comparison without inference from raw iteration data
- workflow collaboration governance is reconciled with the thread-native runtime
- one orchestration extraction seam has a concrete implementation plan

