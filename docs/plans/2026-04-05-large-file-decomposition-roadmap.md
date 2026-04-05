# Large File Decomposition Roadmap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Continue splitting the remaining oversized backend modules into explicit-dependency helpers while preserving behavior and keeping the existing API surface stable.

**Architecture:** Prioritize service-layer files that still mix orchestration, state mutation, read projections, and transport concerns in the same module. For each split, keep the current public entrypoint in place as a thin facade, extract one responsibility at a time, and lock behavior with RED-GREEN unit tests plus targeted integration regressions before broad verification.

**Tech Stack:** Python, Pydantic, FastAPI, pytest, Ruff, SQLite

---

## Priority Order

1. `src/video_agent/application/task_service.py`
2. `src/video_agent/application/review_bundle_builder.py`
3. `src/video_agent/server/mcp_tools.py`
4. `src/video_agent/server/fastmcp_server.py`
5. `src/video_agent/application/workflow_collaboration_service.py`
6. `src/video_agent/adapters/storage/sqlite_schema.py`
7. `src/video_agent/application/workflow_engine.py` residual cleanup only if still justified after the items above

## Stop Conditions

- Do not merge two unrelated splits into one task.
- Do not change public behavior and transport payload shape in the same step.
- Each task must finish with a fresh focused test run.
- Each phase boundary must finish with `ruff` plus a broader regression pass.

### Task 1: Finish `TaskService` By Extracting Winner Acceptance Flow

**Files:**
- Create: `src/video_agent/application/task_service_acceptance.py`
- Modify: `src/video_agent/application/task_service.py`
- Create: `tests/unit/application/test_task_service_acceptance.py`
- Verify: `tests/integration/test_workflow_completion.py`
- Verify: `tests/integration/test_runtime_status_tool.py`

**Step 1: Write the failing test**

- Add unit tests for:
  - accepting a completed task updates lineage ranking and selected winner
  - root task delivery metadata mirrors the accepted task
  - delivery case callbacks run with the same arbitration summary
  - case memory branch-state and winner-selection records stay intact

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest tests/unit/application/test_task_service_acceptance.py -q
```

Expected: FAIL because `task_service_acceptance.py` does not exist yet.

**Step 3: Write minimal implementation**

- Move `accept_authorized_task` logic into helper functions with explicit dependencies:
  - load lineage and scorecards
  - compute arbitration summary
  - update lineage ranking and root resolution
  - emit event and side-effect callbacks
- Keep `TaskService.accept_authorized_task` as a thin adapter.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest tests/unit/application/test_task_service_acceptance.py tests/integration/test_workflow_completion.py tests/integration/test_runtime_status_tool.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/application/test_task_service_acceptance.py src/video_agent/application/task_service_acceptance.py src/video_agent/application/task_service.py
git commit -m "refactor: extract task winner acceptance flow"
```

### Task 2: Finish `TaskService` By Extracting Snapshot And Result Projection Logic

**Files:**
- Create: `src/video_agent/application/task_service_projection.py`
- Modify: `src/video_agent/application/task_service.py`
- Create: `tests/unit/application/test_task_service_projection.py`
- Verify: `tests/integration/test_task_service_create_get.py`
- Verify: `tests/integration/test_guaranteed_video_delivery.py`
- Verify: `tests/integration/test_task_reliability_reconciler.py`

**Step 1: Write the failing test**

- Add unit tests for:
  - snapshot assembly includes repair state, artifact counts, and failure contract only when expected
  - result projection resolves to selected descendant rather than failed root
  - final video and preview resource lookup respects fallback artifact paths

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest tests/unit/application/test_task_service_projection.py -q
```

Expected: FAIL because the projection helper does not exist yet.

**Step 3: Write minimal implementation**

- Extract `_build_video_task_snapshot`, `get_video_result`, `_resolved_result_task`, `_latest_artifact_resource`, and `_artifact_resources` into a projection helper.
- Keep `TaskService` responsible only for wiring store, artifact store, and settings dependencies.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest tests/unit/application/test_task_service_projection.py tests/integration/test_task_service_create_get.py tests/integration/test_guaranteed_video_delivery.py tests/integration/test_task_reliability_reconciler.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/application/test_task_service_projection.py src/video_agent/application/task_service_projection.py src/video_agent/application/task_service.py
git commit -m "refactor: extract task snapshot and result projections"
```

### Task 3: Split `ReviewBundleBuilder` Workflow Controls And Decision Panel Logic

**Files:**
- Create: `src/video_agent/application/review_bundle_workflow_controls.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Create: `tests/unit/application/test_review_bundle_workflow_controls.py`
- Verify: `tests/integration/test_review_bundle_builder.py`

**Step 1: Write the failing test**

- Add unit tests for:
  - suggested next action selection for `accept`, `retry`, `revise`, and `pin_and_revise`
  - blocked accept action payload stays stable
  - panel header tone and badges match workflow status summary

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest tests/unit/application/test_review_bundle_workflow_controls.py -q
```

Expected: FAIL because the helper module does not exist yet.

**Step 3: Write minimal implementation**

- Move these builder concerns into the helper:
  - workflow memory action contract
  - suggested next actions
  - available actions and section grouping
  - status summary and panel header
- Keep `ReviewBundleBuilder.build` and data loading in the main class.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest tests/unit/application/test_review_bundle_workflow_controls.py tests/integration/test_review_bundle_builder.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/application/test_review_bundle_workflow_controls.py src/video_agent/application/review_bundle_workflow_controls.py src/video_agent/application/review_bundle_builder.py
git commit -m "refactor: extract review bundle workflow controls"
```

### Task 4: Split `ReviewBundleBuilder` Render Contract And Action Presentation Logic

**Files:**
- Create: `src/video_agent/application/review_bundle_render_contract.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Create: `tests/unit/application/test_review_bundle_render_contract.py`
- Verify: `tests/integration/test_review_bundle_builder.py`

**Step 1: Write the failing test**

- Add unit tests for:
  - applied action feedback rendering
  - render-contract priority and emphasis rules
  - action-family mapping and button labels

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest tests/unit/application/test_review_bundle_render_contract.py -q
```

Expected: FAIL because the render-contract helper does not exist yet.

**Step 3: Write minimal implementation**

- Move render-contract shaping and action-card presentation helpers out of `review_bundle_builder.py`.
- Leave the root builder responsible for fetching source data and composing the final `ReviewBundle`.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest tests/unit/application/test_review_bundle_render_contract.py tests/integration/test_review_bundle_builder.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/application/test_review_bundle_render_contract.py src/video_agent/application/review_bundle_render_contract.py src/video_agent/application/review_bundle_builder.py
git commit -m "refactor: extract review bundle render contract helpers"
```

### Task 5: Split `mcp_tools.py` By Transport Domain

**Files:**
- Create: `src/video_agent/server/mcp_tools_auth.py`
- Create: `src/video_agent/server/mcp_tools_task.py`
- Create: `src/video_agent/server/mcp_tools_thread.py`
- Create: `src/video_agent/server/mcp_tools_workflow.py`
- Create: `src/video_agent/server/mcp_tools_memory.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Create: `tests/unit/server/test_mcp_tool_helpers.py`
- Verify: `tests/integration/test_mcp_tools.py`
- Verify: `tests/integration/test_agent_auth_tools.py`
- Verify: `tests/integration/test_mcp_multi_agent_workflow_tools.py`
- Verify: `tests/integration/test_agent_memory_tools.py`

**Step 1: Write the failing test**

- Add unit tests for:
  - permission error code normalization
  - auth-required principal enforcement
  - review decision payload normalization
  - representative error payloads for task and workflow tools

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest tests/unit/server/test_mcp_tool_helpers.py -q
```

Expected: FAIL because the helper modules do not exist yet.

**Step 3: Write minimal implementation**

- Group tool wrappers by domain:
  - auth/session
  - task/result
  - thread/participant
  - workflow/review
  - memory/session-memory
- Leave `mcp_tools.py` as a compatibility facade that re-exports the same top-level functions.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest tests/unit/server/test_mcp_tool_helpers.py tests/integration/test_mcp_tools.py tests/integration/test_agent_auth_tools.py tests/integration/test_mcp_multi_agent_workflow_tools.py tests/integration/test_agent_memory_tools.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/server/test_mcp_tool_helpers.py src/video_agent/server/mcp_tools*.py
git commit -m "refactor: split mcp tool wrappers by domain"
```

### Task 6: Split `fastmcp_server.py` Registration Blocks To Mirror `mcp_tools`

**Files:**
- Create: `src/video_agent/server/fastmcp_server_task_registration.py`
- Create: `src/video_agent/server/fastmcp_server_thread_registration.py`
- Create: `src/video_agent/server/fastmcp_server_memory_registration.py`
- Create: `src/video_agent/server/fastmcp_server_resource_registration.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Verify: `tests/integration/test_fastmcp_server.py`

**Step 1: Write the failing test**

- Add or extend tests to prove:
  - tool registration names stay unchanged
  - resource registration names stay unchanged
  - auth/session context plumbing still reaches the underlying services

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest tests/integration/test_fastmcp_server.py -q
```

Expected: targeted failure after moving registration code into new modules.

**Step 3: Write minimal implementation**

- Extract registration groups that parallel the `mcp_tools` domain split.
- Keep `create_mcp_server` as the composition root only.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest tests/integration/test_fastmcp_server.py tests/integration/test_mcp_tools.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/video_agent/server/fastmcp_server*.py tests/integration/test_fastmcp_server.py
git commit -m "refactor: split fastmcp server registrations"
```

### Task 7: Split `WorkflowCollaborationService` Memory Context Builders

**Files:**
- Create: `src/video_agent/application/workflow_collaboration_memory.py`
- Modify: `src/video_agent/application/workflow_collaboration_service.py`
- Create: `tests/unit/application/test_workflow_collaboration_memory.py`
- Verify: `tests/unit/application/test_workflow_collaboration_service.py`
- Verify: `tests/integration/test_multi_agent_workflow_service.py`

**Step 1: Write the failing test**

- Add unit tests for:
  - planner/reviewer/repairer case-memory item shaping
  - shared persistent memory vs attached task context precedence
  - workflow memory query text composition

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest tests/unit/application/test_workflow_collaboration_memory.py -q
```

Expected: FAIL because the memory helper module does not exist yet.

**Step 3: Write minimal implementation**

- Move role-specific memory item builders and summary construction into a dedicated helper.
- Keep `WorkflowCollaborationService` focused on access control, mutation entrypoints, and root-task coordination.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest tests/unit/application/test_workflow_collaboration_memory.py tests/unit/application/test_workflow_collaboration_service.py tests/integration/test_multi_agent_workflow_service.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/application/test_workflow_collaboration_memory.py src/video_agent/application/workflow_collaboration_memory.py src/video_agent/application/workflow_collaboration_service.py
git commit -m "refactor: extract workflow collaboration memory builders"
```

### Task 8: Split `sqlite_schema.py` Migration Packs

**Files:**
- Create: `src/video_agent/adapters/storage/sqlite_schema_core.py`
- Create: `src/video_agent/adapters/storage/sqlite_schema_learning.py`
- Create: `src/video_agent/adapters/storage/sqlite_schema_delivery.py`
- Create: `src/video_agent/adapters/storage/sqlite_schema_threads.py`
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Create: `tests/unit/adapters/storage/test_sqlite_schema.py`
- Verify: `tests/unit/adapters/storage/test_sqlite_store.py`
- Verify: `tests/unit/adapters/storage/test_sqlite_strategy_store.py`
- Verify: `tests/integration/test_http_api.py`

**Step 1: Write the failing test**

- Add unit tests that bootstrap an empty database and verify all expected tables/indexes still exist after running the new migration pack composition root.

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest tests/unit/adapters/storage/test_sqlite_schema.py -q
```

Expected: FAIL because the split migration modules do not exist yet.

**Step 3: Write minimal implementation**

- Move migration functions into packs by concern:
  - core/task tables
  - learning/session memory
  - delivery/workflow
  - video thread/runtime
- Keep `sqlite_schema.py` as the ordered migration entrypoint only.

**Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/pytest tests/unit/adapters/storage/test_sqlite_schema.py tests/unit/adapters/storage/test_sqlite_store.py tests/unit/adapters/storage/test_sqlite_strategy_store.py tests/integration/test_http_api.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/adapters/storage/test_sqlite_schema.py src/video_agent/adapters/storage/sqlite_schema*.py
git commit -m "refactor: split sqlite schema migration packs"
```

### Task 9: Re-evaluate Residual Large Files And Decide Whether To Keep Splitting

**Files:**
- Verify only

**Step 1: Recompute file sizes**

Run:

```bash
wc -l src/video_agent/application/task_service.py src/video_agent/application/review_bundle_builder.py src/video_agent/server/mcp_tools.py src/video_agent/server/fastmcp_server.py src/video_agent/application/workflow_collaboration_service.py src/video_agent/adapters/storage/sqlite_schema.py src/video_agent/application/workflow_engine.py | sort -nr
```

**Step 2: Run final verification for the phase**

Run:

```bash
.venv/bin/python -m ruff check src tests scripts
.venv/bin/pytest tests/unit/application/test_video_projection_thread_context.py tests/unit/application/test_video_projection_explainability.py tests/unit/application/test_video_projection_collaboration_runtime.py tests/unit/application/test_video_projection_history.py tests/unit/application/test_video_projection_iteration_detail.py tests/unit/application/test_video_projection_composer_target.py tests/unit/application/test_video_projection_render_contract.py tests/unit/application/test_video_projection_iteration_story.py tests/unit/application/test_video_projection_production_journal.py tests/unit/application/test_video_projection_service.py tests/unit/application/test_workflow_quality_escalation.py tests/unit/application/test_task_service_child_tasks.py tests/unit/server/test_http_api_identity_routes.py tests/unit/server/test_http_api_profile_memory_routes.py tests/unit/server/test_http_api_video_thread_routes.py tests/unit/server/test_http_api_task_routes.py tests/integration/test_task_service_create_get.py tests/integration/test_video_thread_surface_projection.py tests/integration/test_import_safety.py tests/integration/test_http_api.py tests/integration/test_http_profile_api.py tests/integration/test_http_memory_api.py tests/integration/test_http_memory_retrieval_api.py tests/integration/test_http_video_threads_api.py tests/integration/test_http_multi_agent_workflow_api.py tests/integration/test_workflow_completion.py tests/integration/test_cli_entrypoints.py tests/e2e/test_http_session_flow.py tests/e2e/test_release_candidate_gate.py -q
```

**Step 3: Decide whether to keep splitting**

- Only continue splitting a file if one of these remains true:
  - file still mixes 3 or more responsibilities
  - file still exceeds roughly 700 to 800 lines
  - there is a natural extraction seam with existing test coverage

**Step 4: Commit plan-follow-up checkpoint**

```bash
git add docs/plans/2026-04-05-large-file-decomposition-roadmap.md
git commit -m "docs: add large file decomposition roadmap"
```
