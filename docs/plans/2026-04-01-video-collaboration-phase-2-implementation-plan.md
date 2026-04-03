# Video Collaboration Phase 2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the current owner review panel plus video discussion thread into a durable multi-iteration collaboration system where each video records explicit iteration objects, product-safe rationale, responsibility state, and frontend workbench structure for long-lived human-plus-agent refinement.

**Architecture:** Keep the existing root-task-anchored collaboration thread as the single source of truth and continue extending stable read models instead of introducing a separate chat subsystem. The next phase builds on the existing `workflow_review_controls` and `video_discussion_surface` contracts by adding stronger iteration write-state, explanation snapshots, responsibility metadata, richer UI presentation, and thread-level storage/observability guarantees. All behavior changes should stay TDD-first and should preserve zero-inference rendering for both HTTP and MCP consumers.

**Tech Stack:** FastAPI, Pydantic, SQLite task events, existing workflow collaboration service, review bundle builder, React, TypeScript, Vitest, pytest.

---

## Current Baseline

The following are already in place and should be preserved:

- `workflow_review_controls` stable contract with:
  - `panel_header`
  - `action_sections`
  - `status_summary`
  - `applied_action_feedback`
  - `render_contract`
- `video_discussion_surface` stable contract with:
  - `summary`
  - `thread_summary`
  - `current_iteration_goal`
  - `latest_agent_position`
  - `iterations`
  - `render_contract`
  - `lineage_tasks`
  - `participants`
  - `participant_timeline`
  - `composer`
  - `discussion_entries`
  - `process_timeline`
  - `suggested_next_actions`
- HTTP and MCP discussion thread entry points:
  - `GET /api/tasks/{task_id}/discussion-thread`
  - `video-discussion://{task_id}/thread.json`
- UI placeholder wiring in:
  - `ui/src/features/tasks/TaskDetailPageV2.tsx`
  - `ui/src/features/tasks/TaskDiscussionPlaceholder.tsx`
  - `ui/src/lib/tasksApi.ts`

## Phase 2 Objectives

1. Turn `iterations[]` from a display-only chain into a durable per-iteration state model.
2. Expose product-safe rationale cards so owners can ask “why” without relying on raw message flow.
3. Add responsibility metadata so multi-agent collaboration shows who is expected to act next.
4. Evolve the frontend from a placeholder thread into a structured iteration workbench.
5. Add storage and observability safeguards so long-running video threads remain reliable.

## Safety Rules

- Do not expose raw chain-of-thought, hidden prompts, or private agent reasoning.
- Do not let the frontend reconstruct iteration state from raw `task_events` once the read model exposes it.
- Do not break root-task anchoring: all discussion and iteration history remains lineage-wide.
- Do not revert unrelated dirty worktree changes.
- Always use `apply_patch` for manual edits.
- Use `.venv-codex-verify/bin/python` for Python verification.

## Recommended Sequencing

Execute tasks in order. Task 1 through Task 4 are on the critical path for product capability. Task 5 and Task 6 are hardening tasks that should land before calling the collaboration system “complete”.

### Task 1: Add Iteration Write-State Contract

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Modify: `src/video_agent/application/multi_agent_workflow_service.py`
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `ui/src/lib/tasksApi.ts`
- Test: `tests/integration/test_multi_agent_workflow_service.py`
- Test: `tests/integration/test_review_bundle_builder.py`
- Test: `tests/integration/test_http_multi_agent_workflow_api.py`
- Test: `tests/integration/test_fastmcp_server.py`
- Test: `tests/integration/test_mcp_multi_agent_workflow_tools.py`
- Test: `ui/src/lib/tasksApi.test.ts`

**Step 1: Write the failing tests**

Add tests that require each iteration to expose:

- `requested_action`
- `preserve_working_parts`
- `resolved_outcome`
- `result_summary`
- `selected_result_task_id`
- `source_task_id`

Also add response assertions requiring `POST /discussion-messages` to return:

- `iteration_id`
- enough data to correlate the created child task and iteration state

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/integration/test_multi_agent_workflow_service.py -k discussion_iteration -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_review_bundle_builder.py -k video_discussion_surface -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -k discussion_iteration -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_fastmcp_server.py -k video_discussion_thread_resource -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -k discussion -q
cd ui && npm test -- --run src/lib/tasksApi.test.ts
```

Expected: FAIL because the new fields are not defined yet.

**Step 3: Write the minimal implementation**

Implement the following:

- Extend `VideoDiscussionIteration` with the new write-state fields.
- Extend `VideoDiscussionMessageOutcome` and typed transport models to return the iteration id and correlation metadata.
- Teach `ReviewBundleBuilder` to derive stable iteration write-state from:
  - discussion entries
  - child lineage tasks
  - selected/active task metadata
  - requested action data returned by submission flows
- Keep the implementation intentionally minimal:
  - no new storage table yet
  - no separate iteration endpoint yet
  - derive from existing thread data where possible

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/domain/review_workflow_models.py src/video_agent/application/review_bundle_builder.py src/video_agent/application/multi_agent_workflow_service.py src/video_agent/server/http_api.py src/video_agent/server/fastmcp_server.py src/video_agent/server/mcp_tools.py ui/src/lib/tasksApi.ts tests/integration/test_multi_agent_workflow_service.py tests/integration/test_review_bundle_builder.py tests/integration/test_http_multi_agent_workflow_api.py tests/integration/test_fastmcp_server.py tests/integration/test_mcp_multi_agent_workflow_tools.py ui/src/lib/tasksApi.test.ts
git commit -m "feat: add discussion iteration write-state contract"
```

### Task 2: Add Product-Safe Rationale Snapshots

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Modify: `src/video_agent/application/workflow_collaboration_service.py`
- Modify: `ui/src/lib/tasksApi.ts`
- Modify: `ui/src/features/tasks/TaskDiscussionPlaceholder.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.css`
- Test: `tests/integration/test_review_bundle_builder.py`
- Test: `tests/integration/test_http_multi_agent_workflow_api.py`
- Test: `tests/integration/test_fastmcp_server.py`
- Test: `ui/src/lib/tasksApi.test.ts`
- Test: `ui/src/features/tasks/TaskDetailPageV2.test.tsx`

**Step 1: Write the failing tests**

Add tests requiring the discussion surface to expose product-safe rationale fields such as:

- `latest_design_rationale`
- `latest_revision_rationale`
- or a typed `rationale_cards[]` model if a list proves cleaner

Require at least:

- rationale title
- rationale summary
- source role
- applicable iteration id

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/integration/test_review_bundle_builder.py -k rationale -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -k rationale -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_fastmcp_server.py -k rationale -q
cd ui && npm test -- --run src/lib/tasksApi.test.ts src/features/tasks/TaskDetailPageV2.test.tsx
```

Expected: FAIL because rationale cards are missing.

**Step 3: Write the minimal implementation**

Implement the smallest safe version:

- derive rationale snapshots from existing planner/reviewer/repairer summaries
- bind them to the latest iteration when possible
- keep the copy short and product-safe
- never expose raw hidden reasoning

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/domain/review_workflow_models.py src/video_agent/application/review_bundle_builder.py src/video_agent/application/workflow_collaboration_service.py ui/src/lib/tasksApi.ts ui/src/features/tasks/TaskDiscussionPlaceholder.tsx ui/src/features/tasks/TaskDetailPageV2.css tests/integration/test_review_bundle_builder.py tests/integration/test_http_multi_agent_workflow_api.py tests/integration/test_fastmcp_server.py ui/src/lib/tasksApi.test.ts ui/src/features/tasks/TaskDetailPageV2.test.tsx
git commit -m "feat: expose product-safe discussion rationale snapshots"
```

### Task 3: Add Thread Responsibility State

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Modify: `src/video_agent/application/workflow_collaboration_service.py`
- Modify: `ui/src/lib/tasksApi.ts`
- Modify: `ui/src/features/tasks/TaskDiscussionPlaceholder.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.css`
- Test: `tests/integration/test_review_bundle_builder.py`
- Test: `tests/integration/test_http_multi_agent_workflow_api.py`
- Test: `ui/src/features/tasks/TaskDetailPageV2.test.tsx`

**Step 1: Write the failing tests**

Add tests requiring the discussion surface to expose responsibility state such as:

- `current_owner_action_required`
- `current_agent_role_expected`
- `awaiting_participants`
- `thread_resolution_state`

The tests should prove the UI no longer needs to infer “who acts next” from `thread_status` alone.

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/integration/test_review_bundle_builder.py -k responsibility -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -k responsibility -q
cd ui && npm test -- --run src/features/tasks/TaskDetailPageV2.test.tsx
```

Expected: FAIL because responsibility metadata is missing.

**Step 3: Write the minimal implementation**

Implement responsibility state from:

- `thread_status`
- latest iteration state
- workflow participants
- review outcome state

Prefer explicit read model fields over derived frontend logic.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/domain/review_workflow_models.py src/video_agent/application/review_bundle_builder.py src/video_agent/application/workflow_collaboration_service.py ui/src/lib/tasksApi.ts ui/src/features/tasks/TaskDiscussionPlaceholder.tsx ui/src/features/tasks/TaskDetailPageV2.css tests/integration/test_review_bundle_builder.py tests/integration/test_http_multi_agent_workflow_api.py ui/src/features/tasks/TaskDetailPageV2.test.tsx
git commit -m "feat: add discussion responsibility read model"
```

### Task 4: Evolve The Frontend Into An Iteration Workbench

**Files:**
- Modify: `ui/src/features/tasks/TaskDiscussionPlaceholder.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.css`
- Modify: `ui/src/lib/tasksApi.ts`
- Test: `ui/src/features/tasks/TaskDetailPageV2.test.tsx`
- Test: `ui/src/lib/tasksApi.test.ts`

**Step 1: Write the failing tests**

Add UI tests that require:

- a visible iteration workbench area above or alongside raw discussion entries
- selection/focus of the latest iteration
- visible rationale and responsibility state
- stable rendering from `render_contract` plus `iterations`

**Step 2: Run tests to verify they fail**

Run:

```bash
cd ui && npm test -- --run src/features/tasks/TaskDetailPageV2.test.tsx src/lib/tasksApi.test.ts
```

Expected: FAIL because the richer workbench UI is not rendered yet.

**Step 3: Write the minimal implementation**

Implement:

- dedicated iteration cards
- latest-iteration emphasis
- rationale block
- responsibility block
- keep the composer below the workbench

Do not build a new route or sidebar yet. Keep this within the current task detail layout.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add ui/src/features/tasks/TaskDiscussionPlaceholder.tsx ui/src/features/tasks/TaskDetailPageV2.tsx ui/src/features/tasks/TaskDetailPageV2.css ui/src/lib/tasksApi.ts ui/src/features/tasks/TaskDetailPageV2.test.tsx ui/src/lib/tasksApi.test.ts
git commit -m "feat: render discussion iteration workbench"
```

### Task 5: Add Thread Storage And Performance Safeguards

**Files:**
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/application/workflow_collaboration_service.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`
- Test: `tests/unit/application/test_workflow_collaboration_service.py`
- Test: `tests/integration/test_review_bundle_builder.py`

**Step 1: Write the failing tests**

Add tests requiring:

- efficient loading of long discussion threads
- deterministic ordering for many discussion entries and iterations
- optional persisted iteration metadata if the existing event-only derivation becomes too lossy

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/unit/adapters/storage/test_sqlite_store.py -k discussion -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_workflow_collaboration_service.py -k discussion -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_review_bundle_builder.py -k discussion -q
```

Expected: FAIL because the storage support does not exist yet.

**Step 3: Write the minimal implementation**

Choose the lightest option that preserves contract quality:

- if derivation remains reliable, add indexing and ordering helpers only
- if derivation is starting to leak abstraction, persist minimal iteration metadata

Do not add broad schema complexity unless tests show it is necessary.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/adapters/storage/sqlite_schema.py src/video_agent/adapters/storage/sqlite_store.py src/video_agent/application/workflow_collaboration_service.py src/video_agent/application/review_bundle_builder.py tests/unit/adapters/storage/test_sqlite_store.py tests/unit/application/test_workflow_collaboration_service.py tests/integration/test_review_bundle_builder.py
git commit -m "feat: harden discussion thread storage and ordering"
```

### Task 6: Add Collaboration Observability And Evaluation Coverage

**Files:**
- Modify: `tests/integration/test_http_multi_agent_workflow_api.py`
- Modify: `tests/integration/test_mcp_multi_agent_workflow_tools.py`
- Modify: `tests/integration/test_fastmcp_server.py`
- Create: `tests/integration/test_video_collaboration_thread_regressions.py`
- Optional Modify: `src/video_agent/eval/canary.py`
- Optional Modify: `src/video_agent/application/delivery_canary_service.py`
- Modify: `docs/runbooks/video-discussion-surface-contract.md`

**Step 1: Write the failing tests**

Add regression scenarios covering:

- multiple follow-up iterations on the same root task
- owner-only write permissions
- stable `iterations[]` under MCP and HTTP
- no duplicate iteration generation when child-task feedback matches root-thread follow-up
- render contract remains zero-inference across long threads

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/integration/test_video_collaboration_thread_regressions.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -k discussion -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -k discussion -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_fastmcp_server.py -k discussion -q
```

Expected: FAIL because the new regression coverage does not exist yet.

**Step 3: Write the minimal implementation**

Implement only what the regression tests prove is required:

- bug fixes
- missing transport fields
- contract clarifications
- optional canary additions if useful

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add tests/integration/test_http_multi_agent_workflow_api.py tests/integration/test_mcp_multi_agent_workflow_tools.py tests/integration/test_fastmcp_server.py tests/integration/test_video_collaboration_thread_regressions.py src/video_agent/eval/canary.py src/video_agent/application/delivery_canary_service.py docs/runbooks/video-discussion-surface-contract.md
git commit -m "test: add video collaboration regression coverage"
```

## Final Verification

After all tasks are complete, run:

```bash
.venv-codex-verify/bin/python -m pytest tests/integration/test_multi_agent_workflow_service.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_fastmcp_server.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/adapters/storage/test_sqlite_store.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_workflow_collaboration_service.py -q
cd ui && npm test -- --run src/lib/tasksApi.test.ts src/features/tasks/TaskDetailPageV2.test.tsx src/features/tasks/TasksPageV2.test.tsx
cd ui && npm run build
.venv-codex-verify/bin/python -m pytest -q
cd ui && npm test
```

Expected:

- Python integration and unit tests all PASS.
- UI targeted tests PASS.
- `npm run build` PASS.
- Full backend and frontend test suites PASS.

## Recommended First Slice

Start with **Task 1: Add Iteration Write-State Contract**.

Why:

- It builds directly on the newly landed `iterations[]` baseline.
- It upgrades the collaboration system from “readable thread” to “actionable iteration object”.
- It unlocks rationale, responsibility, and frontend workbench tasks without forcing rework.

