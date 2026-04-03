# Phase 3 Video Thread Runtime Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current task-centric collaboration overlay with a first-class video thread runtime that supports durable human-plus-agent discussion, explicit iterations, explicit result selection, explicit agent authorship, and a zero-inference owner workbench for every video.

**Architecture:** Build a new thread-centric runtime instead of extending `ReviewBundleBuilder` and the existing `video_discussion_surface`. Introduce new storage entities and services for `video_thread`, `video_iteration`, `video_turn`, `video_result`, and thread-bound `agent_run`, then expose them through a new `video_thread_surface` projection consumed by HTTP, MCP, and the frontend workbench. Because backward compatibility is not required, the implementation should replace old task-derived discussion APIs and UI composition instead of maintaining a dual-read bridge.

**Tech Stack:** FastAPI, Pydantic, SQLite, existing `VideoTask` execution runtime, MCP/FastMCP, React, TypeScript, Vitest, pytest.

## Completion Status

Status on 2026-04-01: completed.

What landed:

- Task 1 through Task 4 established the thread-centric runtime, storage, bindings, and `video_thread_surface` projection.
- Task 5 exposed thread-native HTTP, MCP, and FastMCP transports for create, surface read, turn append, revision request, explanation request, result selection, and iteration/timeline resources.
- Task 6 added the owner workbench route at `/videos/:threadId`, thread-native API clients, and cross-links from task/video shells into the workbench.
- Task 7 closed the rollout by removing owner-facing dependence on the legacy task discussion transport:
  - `/api/tasks/{task_id}/discussion-thread` and `/api/tasks/{task_id}/discussion-messages` now return explicit `410 legacy_discussion_transport_removed`.
  - `video-discussion://...` is no longer registered in FastMCP.
  - `get_review_bundle` transport payloads no longer expose `video_discussion_surface`.
  - `TaskDetailPageV2` no longer fetches or submits legacy task discussion transport and now routes owners to the video workbench when `thread_id` exists.

---

## Required Skills During Execution

- `@superpowers:test-driven-development` before each implementation task.
- `@superpowers:verification-before-completion` before claiming any slice is done.
- `@superpowers:subagent-driven-development` if this plan is executed in the current session.

## Breaking-Change Assumptions

- Do not preserve the current `video_discussion_surface` contract.
- Do not preserve the current `/api/tasks/{task_id}/discussion-thread` API.
- Do not preserve the current `video-discussion://...` MCP resource naming.
- Do not preserve `TaskDiscussionPlaceholder` as the primary owner collaboration UI.
- Keep `VideoTask` and workflow execution, but demote them beneath the thread runtime.
- Never expose raw chain-of-thought, hidden prompts, or private reasoning traces.

## Current Baseline

The codebase currently still routes collaboration through these task-centric touch points:

- `src/video_agent/application/review_bundle_builder.py`
- `src/video_agent/application/multi_agent_workflow_service.py`
- `src/video_agent/application/workflow_collaboration_service.py`
- `src/video_agent/domain/review_workflow_models.py`
- `src/video_agent/server/http_api.py`
- `src/video_agent/server/fastmcp_server.py`
- `src/video_agent/server/mcp_tools.py`
- `ui/src/features/tasks/TaskDetailPageV2.tsx`
- `ui/src/features/tasks/TaskDiscussionPlaceholder.tsx`
- `ui/src/lib/tasksApi.ts`

Phase 3 should replace these collaboration entry points with explicit thread runtime services and a new workbench surface.

## Recommended Sequencing

Execute tasks in order. Task 1 through Task 4 create the new runtime truth. Task 5 and Task 6 move transport and UI onto that truth. Task 7 removes the old task-derived collaboration surface and closes the rollout.

### Task 1: Introduce Thread-Centric Domain Models And Schema

**Files:**
- Create: `src/video_agent/domain/video_thread_models.py`
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/domain/delivery_case_models.py`
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Test: `tests/unit/domain/test_video_thread_models.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`

**Step 1: Write the failing tests**

Add tests that require these first-class models and persistence shapes:

```python
def test_video_thread_defaults_to_active_root() -> None:
    thread = VideoThread(
        thread_id="thread-1",
        owner_agent_id="owner",
        title="Circle explainer",
        origin_prompt="draw a circle",
    )
    assert thread.status == "active"
    assert thread.selected_result_id is None


def test_video_task_can_bind_to_thread_iteration_and_result() -> None:
    task = VideoTask(prompt="draw a circle", thread_id="thread-1", iteration_id="iter-1", result_id="result-1")
    assert task.thread_id == "thread-1"
    assert task.iteration_id == "iter-1"
    assert task.result_id == "result-1"
```

Add storage tests that require new tables and indexes:

- `video_threads`
- `video_iterations`
- `video_turns`
- `video_results`
- `video_thread_participants`
- `video_agent_runs`

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/unit/domain/test_video_thread_models.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/adapters/storage/test_sqlite_store.py -k "video_thread or video_iteration or video_turn or video_result" -q
```

Expected: FAIL because the new models, task bindings, and tables do not exist yet.

**Step 3: Write the minimal implementation**

Implement the smallest clean runtime foundation:

- Create `VideoThread`, `VideoIteration`, `VideoTurn`, `VideoResult`, `VideoThreadParticipant`, and `VideoAgentRun` models in `src/video_agent/domain/video_thread_models.py`.
- Add `thread_id`, `iteration_id`, `result_id`, and `execution_kind` to `VideoTask`.
- Extend `AgentRun` or replace its thread-facing usage so thread and iteration binding are explicit.
- Add new SQLite migrations and indexes for thread-centric tables.
- Add minimal store read/write methods needed by the model and schema tests.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/domain/video_thread_models.py src/video_agent/domain/models.py src/video_agent/domain/delivery_case_models.py src/video_agent/adapters/storage/sqlite_schema.py src/video_agent/adapters/storage/sqlite_store.py tests/unit/domain/test_video_thread_models.py tests/unit/adapters/storage/test_sqlite_store.py
git commit -m "feat: add video thread runtime schema foundation"
```

### Task 2: Add Thread Store APIs And Runtime Services

**Files:**
- Create: `src/video_agent/application/video_thread_service.py`
- Create: `src/video_agent/application/video_iteration_service.py`
- Create: `src/video_agent/application/video_turn_service.py`
- Create: `src/video_agent/application/video_run_binding_service.py`
- Create: `src/video_agent/application/video_policy_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/server/app.py`
- Test: `tests/unit/application/test_video_thread_service.py`
- Test: `tests/unit/application/test_video_iteration_service.py`
- Test: `tests/unit/application/test_video_turn_service.py`
- Test: `tests/unit/application/test_video_run_binding_service.py`
- Test: `tests/unit/application/test_video_policy_service.py`

**Step 1: Write the failing tests**

Add service tests covering:

- thread creation from owner prompt
- iteration creation from owner intent
- turn append with `product_safe` visibility
- result registration and selection
- responsibility assignment and next-role decisions

Example service test:

```python
def test_create_thread_creates_root_iteration() -> None:
    outcome = service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle with a bold title card",
    )
    assert outcome.thread.thread_id.startswith("thread-")
    assert outcome.iteration.parent_iteration_id is None
    assert outcome.turn.turn_type == "owner_request"
```

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_thread_service.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_iteration_service.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_turn_service.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_run_binding_service.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_policy_service.py -q
```

Expected: FAIL because the new services and store APIs are not implemented.

**Step 3: Write the minimal implementation**

Implement the services with clear ownership boundaries:

- `VideoThreadService`: create/load/archive thread and set current selection.
- `VideoIterationService`: create or branch iterations, close iterations, assign responsibility.
- `VideoTurnService`: append owner turns, explanation turns, and status turns with visibility rules.
- `VideoRunBindingService`: attach execution runs and mark latest responsible agent/role.
- `VideoPolicyService`: choose `discuss`, `revise`, `branch`, and next responsible role from runtime truth.
- Wire these services into `create_app_context`.

Do not integrate HTTP, MCP, or frontend yet.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/application/video_thread_service.py src/video_agent/application/video_iteration_service.py src/video_agent/application/video_turn_service.py src/video_agent/application/video_run_binding_service.py src/video_agent/application/video_policy_service.py src/video_agent/adapters/storage/sqlite_store.py src/video_agent/server/app.py tests/unit/application/test_video_thread_service.py tests/unit/application/test_video_iteration_service.py tests/unit/application/test_video_turn_service.py tests/unit/application/test_video_run_binding_service.py tests/unit/application/test_video_policy_service.py
git commit -m "feat: add video thread runtime services"
```

### Task 3: Bind Tasks And Agent Runs Beneath Iterations

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/domain/delivery_case_models.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/application/video_thread_service.py`
- Modify: `src/video_agent/application/video_iteration_service.py`
- Modify: `src/video_agent/application/video_run_binding_service.py`
- Test: `tests/integration/test_video_thread_runtime_execution.py`
- Test: `tests/integration/test_revision_and_cancel.py`
- Test: `tests/integration/test_runtime_status_tool.py`

**Step 1: Write the failing tests**

Add integration tests that require:

- creating a thread also creates an initial execution task bound to the root iteration
- requesting a revision creates a new iteration and a new child task under that iteration
- thread-bound agent runs identify the latest result author and current responsible role
- runtime status can report active work by `thread_id` and `iteration_id`

Example:

```python
def test_request_revision_creates_new_iteration_and_child_task(app_context) -> None:
    thread = create_thread(app_context)
    outcome = request_revision(app_context, thread.thread_id, summary="Keep the slower opening")
    assert outcome.iteration.source_result_id is not None
    assert outcome.created_task.iteration_id == outcome.iteration.iteration_id
    assert outcome.created_task.parent_task_id is not None
```

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/integration/test_video_thread_runtime_execution.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_revision_and_cancel.py -k "thread or iteration" -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_runtime_status_tool.py -k "thread or iteration" -q
```

Expected: FAIL because tasks and agent runs are not yet bound to thread runtime objects.

**Step 3: Write the minimal implementation**

Implement the binding layer:

- Create tasks from iteration requests rather than from loose discussion messages.
- Persist `thread_id`, `iteration_id`, and `result_id` on tasks and thread-bound runs.
- Register `video_result` when a task delivers a visible output.
- Mark selected result and current iteration in runtime services instead of deriving them from lineage alone.
- Keep existing execution engine behavior where possible, but move ownership of collaboration truth to the new services.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/application/task_service.py src/video_agent/application/runtime_service.py src/video_agent/application/workflow_engine.py src/video_agent/domain/models.py src/video_agent/domain/delivery_case_models.py src/video_agent/adapters/storage/sqlite_store.py src/video_agent/application/video_thread_service.py src/video_agent/application/video_iteration_service.py src/video_agent/application/video_run_binding_service.py tests/integration/test_video_thread_runtime_execution.py tests/integration/test_revision_and_cancel.py tests/integration/test_runtime_status_tool.py
git commit -m "feat: bind execution tasks to video thread iterations"
```

### Task 4: Build The New `video_thread_surface` Projection

**Files:**
- Create: `src/video_agent/application/video_projection_service.py`
- Modify: `src/video_agent/domain/video_thread_models.py`
- Modify: `src/video_agent/application/video_thread_service.py`
- Modify: `src/video_agent/application/video_iteration_service.py`
- Modify: `src/video_agent/application/video_turn_service.py`
- Modify: `src/video_agent/application/video_run_binding_service.py`
- Modify: `src/video_agent/server/app.py`
- Create: `docs/runbooks/video-thread-surface-contract.md`
- Test: `tests/unit/application/test_video_projection_service.py`
- Test: `tests/integration/test_video_thread_surface_projection.py`

**Step 1: Write the failing tests**

Add projection tests that require a stable `video_thread_surface` with:

- `thread_header`
- `thread_summary`
- `current_focus`
- `responsibility`
- `iteration_workbench`
- `conversation`
- `process`
- `participants`
- `actions`
- `composer`
- `render_contract`

Example assertion:

```python
def test_projection_exposes_zero_inference_owner_surface() -> None:
    surface = projection_service.build_surface(thread_id="thread-1")
    assert surface.current_focus.current_iteration_id == "iter-2"
    assert surface.responsibility.expected_agent_role == "repairer"
    assert surface.render_contract.default_focus_panel == "current_focus"
```

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_projection_service.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_video_thread_surface_projection.py -q
```

Expected: FAIL because the new projection service and contract do not exist.

**Step 3: Write the minimal implementation**

Implement the new projection layer:

- Add projection-facing models for header, focus, responsibility, iteration cards, turn cards, process cards, and render contract.
- Build `video_thread_surface` from thread entities and bound runs rather than from `ReviewBundleBuilder`.
- Keep all owner-facing explanation content `product_safe`.
- Document the contract in `docs/runbooks/video-thread-surface-contract.md`.

Do not keep `video_discussion_surface` as the source of truth.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/application/video_projection_service.py src/video_agent/domain/video_thread_models.py src/video_agent/application/video_thread_service.py src/video_agent/application/video_iteration_service.py src/video_agent/application/video_turn_service.py src/video_agent/application/video_run_binding_service.py src/video_agent/server/app.py docs/runbooks/video-thread-surface-contract.md tests/unit/application/test_video_projection_service.py tests/integration/test_video_thread_surface_projection.py
git commit -m "feat: add video thread surface projection"
```

### Task 5: Replace HTTP And MCP With Thread-Native APIs

**Files:**
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/application/video_thread_service.py`
- Modify: `src/video_agent/application/video_iteration_service.py`
- Modify: `src/video_agent/application/video_turn_service.py`
- Modify: `src/video_agent/application/video_projection_service.py`
- Test: `tests/integration/test_http_video_threads_api.py`
- Test: `tests/integration/test_mcp_video_thread_tools.py`
- Test: `tests/integration/test_fastmcp_video_thread_resources.py`

**Step 1: Write the failing tests**

Add integration tests for the new API surface:

- `POST /api/video-threads`
- `GET /api/video-threads/{thread_id}`
- `GET /api/video-threads/{thread_id}/surface`
- `POST /api/video-threads/{thread_id}/turns`
- `POST /api/video-threads/{thread_id}/iterations`
- `POST /api/video-threads/{thread_id}/iterations/{iteration_id}/request-revision`
- `POST /api/video-threads/{thread_id}/iterations/{iteration_id}/request-explanation`
- `POST /api/video-threads/{thread_id}/iterations/{iteration_id}/select-result`

Also add MCP tests for:

- `video-thread://{thread_id}/surface.json`
- `video-thread://{thread_id}/timeline.json`
- `create_video_thread`
- `append_video_turn`
- `request_video_revision`
- `request_video_explanation`
- `select_video_result`
- `get_video_thread_surface`

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/integration/test_http_video_threads_api.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_mcp_video_thread_tools.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_fastmcp_video_thread_resources.py -q
```

Expected: FAIL because the thread-native APIs and resources are not registered yet.

**Step 3: Write the minimal implementation**

Implement the transport layer:

- Add thread-native request/response models to `http_api.py`.
- Register the new FastAPI endpoints and FastMCP tools/resources.
- Route handlers directly to the new thread services and projection service.
- Keep auth and ownership checks consistent with existing task APIs.
- Do not keep `/api/tasks/{task_id}/discussion-thread` or `video-discussion://...` as the main collaboration interface.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/server/http_api.py src/video_agent/server/fastmcp_server.py src/video_agent/server/mcp_tools.py src/video_agent/server/app.py src/video_agent/server/main.py src/video_agent/application/video_thread_service.py src/video_agent/application/video_iteration_service.py src/video_agent/application/video_turn_service.py src/video_agent/application/video_projection_service.py tests/integration/test_http_video_threads_api.py tests/integration/test_mcp_video_thread_tools.py tests/integration/test_fastmcp_video_thread_resources.py
git commit -m "feat: expose thread-native video collaboration APIs"
```

### Task 6: Rewrite The Frontend As A Video Collaboration Workbench

**Files:**
- Create: `ui/src/features/videoThreads/VideoThreadPage.tsx`
- Create: `ui/src/features/videoThreads/VideoThreadPage.test.tsx`
- Create: `ui/src/features/videoThreads/VideoThreadWorkbench.tsx`
- Create: `ui/src/features/videoThreads/VideoThreadWorkbench.css`
- Create: `ui/src/lib/videoThreadsApi.ts`
- Create: `ui/src/lib/videoThreadsApi.test.ts`
- Modify: `ui/src/app/App.tsx`
- Modify: `ui/src/features/videos/VideosPageV2.tsx`
- Modify: `ui/src/features/videos/VideosPageV2.test.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.tsx`
- Modify: `ui/src/features/tasks/TaskDetailPageV2.test.tsx`

**Step 1: Write the failing tests**

Add UI tests that require:

- a dedicated `/videos/:threadId` thread page
- selected result area above the collaboration surface
- current focus rail and responsibility block
- iteration timeline with visible branch state
- conversation pane with product-safe explanation cards
- typed composer actions for discuss, revise, explain, and select result
- task detail page redirecting or linking to the thread workbench instead of hosting the old placeholder

**Step 2: Run tests to verify they fail**

Run:

```bash
cd ui && npm test -- --run src/features/videoThreads/VideoThreadPage.test.tsx src/lib/videoThreadsApi.test.ts src/features/videos/VideosPageV2.test.tsx src/features/tasks/TaskDetailPageV2.test.tsx
```

Expected: FAIL because the thread page, workbench components, and new API client do not exist.

**Step 3: Write the minimal implementation**

Implement the frontend rewrite:

- Add `videoThreadsApi.ts` for the new thread-native HTTP endpoints.
- Add a dedicated `VideoThreadPage` and `VideoThreadWorkbench`.
- Render the workbench from `video_thread_surface` only; do not reconstruct state from task lineage.
- Update video list/task detail entry points so owners land in the thread workbench.
- Remove `TaskDiscussionPlaceholder` from the primary owner flow.

Keep the first version placeholder-light but contract-complete.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add ui/src/features/videoThreads/VideoThreadPage.tsx ui/src/features/videoThreads/VideoThreadPage.test.tsx ui/src/features/videoThreads/VideoThreadWorkbench.tsx ui/src/features/videoThreads/VideoThreadWorkbench.css ui/src/lib/videoThreadsApi.ts ui/src/lib/videoThreadsApi.test.ts ui/src/app/App.tsx ui/src/features/videos/VideosPageV2.tsx ui/src/features/videos/VideosPageV2.test.tsx ui/src/features/tasks/TaskDetailPageV2.tsx ui/src/features/tasks/TaskDetailPageV2.test.tsx
git commit -m "feat: add video collaboration workbench UI"
```

### Task 7: Remove Legacy Task-Centric Collaboration Surface And Close Regressions

**Files:**
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Modify: `src/video_agent/application/multi_agent_workflow_service.py`
- Modify: `src/video_agent/application/workflow_collaboration_service.py`
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `docs/runbooks/video-discussion-surface-contract.md`
- Modify: `docs/runbooks/owner-review-panel-contract.md`
- Create: `tests/integration/test_video_thread_runtime_regressions.py`
- Modify: `tests/integration/test_review_bundle_builder.py`
- Modify: `tests/integration/test_http_multi_agent_workflow_api.py`
- Modify: `tests/integration/test_mcp_multi_agent_workflow_tools.py`
- Modify: `tests/integration/test_fastmcp_server.py`

**Step 1: Write the failing tests**

Add regression tests that require:

- all owner-facing collaboration reads flow through `video_thread_surface`
- old discussion-thread APIs either disappear or return a clear breaking-change error
- `ReviewBundleBuilder` no longer owns discussion truth
- thread replay and projection rebuild remain deterministic across multiple iterations and branches
- owner-only write restrictions still hold under the new thread APIs

**Step 2: Run tests to verify they fail**

Run:

```bash
.venv-codex-verify/bin/python -m pytest tests/integration/test_video_thread_runtime_regressions.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_review_bundle_builder.py -k "video_thread or discussion" -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -k "video_thread or discussion" -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -k "video_thread or discussion" -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_fastmcp_server.py -k "video_thread or discussion" -q
```

Expected: FAIL because the legacy task-centric collaboration surface still exists.

**Step 3: Write the minimal implementation**

Remove or shrink the old layer:

- Remove `video_discussion_surface` as the primary collaboration contract.
- Reduce `ReviewBundleBuilder` back to task/review concerns or remove collaboration responsibilities from it entirely.
- Remove old HTTP/MCP discussion entry points or leave explicit breaking stubs if needed for a short internal transition.
- Update runbooks so the official owner-facing contract is the new `video_thread_surface`.

**Step 4: Run tests to verify they pass**

Run the same commands and expect PASS.

**Step 5: Commit**

```bash
git add src/video_agent/application/review_bundle_builder.py src/video_agent/application/multi_agent_workflow_service.py src/video_agent/application/workflow_collaboration_service.py src/video_agent/domain/review_workflow_models.py src/video_agent/server/http_api.py src/video_agent/server/fastmcp_server.py src/video_agent/server/mcp_tools.py docs/runbooks/video-discussion-surface-contract.md docs/runbooks/owner-review-panel-contract.md tests/integration/test_video_thread_runtime_regressions.py tests/integration/test_review_bundle_builder.py tests/integration/test_http_multi_agent_workflow_api.py tests/integration/test_mcp_multi_agent_workflow_tools.py tests/integration/test_fastmcp_server.py
git commit -m "refactor: replace legacy task discussion surface with video thread runtime"
```

## Final Verification

After all tasks are complete, run:

```bash
.venv-codex-verify/bin/python -m pytest tests/unit/domain/test_video_thread_models.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_thread_service.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_iteration_service.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_turn_service.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_run_binding_service.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_policy_service.py -q
.venv-codex-verify/bin/python -m pytest tests/unit/application/test_video_projection_service.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_video_thread_runtime_execution.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_video_thread_surface_projection.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_http_video_threads_api.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_mcp_video_thread_tools.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_fastmcp_video_thread_resources.py -q
.venv-codex-verify/bin/python -m pytest tests/integration/test_video_thread_runtime_regressions.py -q
cd ui && npm test -- --run src/lib/videoThreadsApi.test.ts src/features/videoThreads/VideoThreadPage.test.tsx src/features/videos/VideosPageV2.test.tsx src/features/tasks/TaskDetailPageV2.test.tsx
cd ui && npm run build
.venv-codex-verify/bin/python -m pytest -q
cd ui && npm test
```

Expected:

- Thread runtime unit tests PASS.
- Thread API and MCP integration suites PASS.
- Frontend workbench tests PASS.
- UI build PASS.
- Full backend and frontend suites PASS.

## Recommended First Slice

Start with **Task 1: Introduce Thread-Centric Domain Models And Schema**.

Why:

- It is the first irreversible architecture decision.
- It prevents later services from falling back to task-lineage inference.
- It gives every later task a real `thread_id` and `iteration_id` backbone instead of a transitional adapter.

## Execution Handoff

Plan complete and saved to `docs/plans/2026-04-01-phase-3-video-thread-runtime-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
