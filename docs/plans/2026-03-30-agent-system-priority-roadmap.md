# Agent System Priority Roadmap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Strengthen `easy-manim` from a supervised single-owner multi-role workflow into a durable, thread-native collaboration platform with clearer governance and maintainable orchestration seams.

**Architecture:** Keep the current validation-first task engine intact, but move volatile agent state into persistence, align workflow collaboration permissions with the thread-native participant model without opening broad mutation rights, and split orchestration logic out of oversized service classes. The path should preserve today's safe default of supervised execution while making future autonomy features easier to add.

**Tech Stack:** Python, FastAPI, MCP, Pydantic, SQLite, pytest

---

## Priority Summary

- **P0:** Persist session/workflow memory so agent state survives process restarts.
- **P1:** Add unified collaboration governance so workflow participants and thread participants can share one supervised permission model without pretending every collaborator is the owner.
- **P2:** Refactor oversized orchestration modules to keep future agent work from collapsing under complexity.

## Delivery Order

1. P0 first because current session memory is process-local and blocks reliable long-running collaboration.
2. P1 second because the present model still keeps important collaboration rights owner-only and split across workflow/task and thread/video surfaces.
3. P2 third because the system is still operable today, but future change velocity will degrade if orchestration logic stays concentrated.

### Task 1: P0 Persistent Session And Workflow Memory

**Estimate:** 2-3 days

**Files:**
- Modify: `src/video_agent/server/session_memory.py`
- Modify: `src/video_agent/application/session_memory_service.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Test: `tests/unit/application/test_agent_session_service.py`
- Test: `tests/integration/test_review_bundle_builder.py`
- Test: `tests/integration/test_http_multi_agent_workflow_api.py`
- Test: `tests/integration/test_agent_learning_capture.py`

**Step 1: Write the failing persistence test**

Add an integration test that:
- creates a task with `session_id`
- records session memory entries
- recreates `AppContext`
- verifies the same session summary is still available after restart

**Step 2: Run the targeted test to verify it fails**

Run: `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`

Expected: a new restart-oriented session-memory test fails because the current registry is in-memory only.

**Step 3: Add persistent storage for session memory snapshots**

Implementation notes:
- add a SQLite table for session memory snapshots keyed by `session_id`
- store `agent_id`, serialized snapshot JSON, timestamps, and summary digest
- update `SessionMemoryRegistry` to become a thin cache over persistent reads and writes rather than the source of truth
- keep current APIs stable so the rest of the app does not need wide churn

**Step 4: Wire bootstrap and service loading**

Implementation notes:
- initialize the registry with store-backed lookup/save callbacks in `src/video_agent/server/app.py`
- ensure `SessionMemoryService` reads persisted snapshots first
- preserve existing behavior for `clear_session_memory`, `list_snapshots`, and summary generation

**Step 5: Run targeted regression tests**

Run:
- `.venv/bin/python -m pytest tests/integration/test_review_bundle_builder.py -q`
- `.venv/bin/python -m pytest tests/integration/test_agent_learning_capture.py -q`

Expected: PASS

**Step 6: Run the full suite**

Run: `.venv/bin/python -m pytest -q`

Expected: PASS

**Step 7: Commit**

```bash
git add src/video_agent/server/session_memory.py src/video_agent/application/session_memory_service.py src/video_agent/server/app.py src/video_agent/adapters/storage/sqlite_schema.py src/video_agent/adapters/storage/sqlite_store.py tests/integration/test_review_bundle_builder.py tests/integration/test_agent_learning_capture.py
git commit -m "feat: persist agent session memory"
```

### Task 2: P1 Unified Collaboration Governance

**Estimate:** 3-5 days

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/agent_authorization_service.py`
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Modify: `src/video_agent/application/multi_agent_workflow_service.py`
- Modify: `src/video_agent/application/video_thread_service.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Test: `tests/integration/test_mcp_multi_agent_workflow_tools.py`
- Test: `tests/integration/test_http_multi_agent_workflow_api.py`
- Test: `tests/integration/test_agent_auth_tools.py`
- Test: `tests/integration/test_agent_resource_isolation.py`

**Step 1: Write failing authorization tests**

Add tests for:
- reviewer can read review bundle for a delegated workflow
- reviewer can submit structured review decisions
- reviewer cannot create, retry, or revise tasks directly
- non-participants still receive `403`
- thread participants do not automatically gain workflow mutation rights
- thread continuity and workflow decision authority resolve through one shared governance vocabulary

**Step 2: Run the targeted tests to verify they fail**

Run:
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`

Expected: FAIL because access is currently strict owner-only.

**Step 3: Add or align collaboration participation records**

Implementation notes:
- keep explicit workflow participation records such as `workflow_participants`
- preserve explicit thread-native participant records for continuity and addressing
- define shared governance concepts across both instead of forcing one table to replace the other immediately
- keep mutation authority with the owner by default

**Step 4: Extend authorization checks**

Implementation notes:
- separate `task owner` from `workflow collaborator` and `thread participant`
- allow collaborator read access only for explicitly shared resources
- allow reviewer/verifier decision submission without granting direct task mutation
- keep roster mutation owner-scoped on both workflow and thread surfaces unless a future policy explicitly expands them

**Step 5: Surface role-aware collaboration through APIs**

Implementation notes:
- update MCP and HTTP endpoints to resolve collaborator permissions across both workflow and thread transports
- include collaboration role metadata in review bundle payloads and thread surfaces when useful
- keep error codes deterministic for clients

**Step 6: Run targeted regression tests**

Run:
- `.venv/bin/python -m pytest tests/integration/test_mcp_multi_agent_workflow_tools.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_multi_agent_workflow_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_agent_auth_tools.py -q`

Expected: PASS

**Step 7: Run the full suite**

Run: `.venv/bin/python -m pytest -q`

Expected: PASS

**Step 8: Commit**

```bash
git add src/video_agent/application/task_service.py src/video_agent/application/agent_authorization_service.py src/video_agent/application/review_bundle_builder.py src/video_agent/application/multi_agent_workflow_service.py src/video_agent/application/video_thread_service.py src/video_agent/server/mcp_tools.py src/video_agent/server/http_api.py src/video_agent/adapters/storage/sqlite_schema.py src/video_agent/adapters/storage/sqlite_store.py src/video_agent/domain/review_workflow_models.py tests/integration/test_mcp_multi_agent_workflow_tools.py tests/integration/test_http_multi_agent_workflow_api.py tests/integration/test_agent_auth_tools.py tests/integration/test_agent_resource_isolation.py
git commit -m "feat: align collaboration governance across workflow and threads"
```

### Task 3: P2 Orchestration Module Refactor

**Estimate:** 4-6 days

**Files:**
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/task_service.py`
- Create: `src/video_agent/application/delivery_resolution_service.py`
- Create: `src/video_agent/application/branch_promotion_service.py`
- Create: `src/video_agent/application/session_memory_repository.py`
- Modify: `src/video_agent/server/app.py`
- Test: `tests/integration/test_task_reliability_reconciler.py`
- Test: `tests/integration/test_multi_agent_workflow_service.py`
- Test: `tests/integration/test_http_task_reliability_api.py`

**Step 1: Write characterization tests before moving code**

Add or tighten tests around:
- challenger promotion behavior
- delivery resolution sync
- arbitration event recording
- reliability reconciliation after restart

**Step 2: Run targeted tests to lock baseline behavior**

Run:
- `.venv/bin/python -m pytest tests/integration/test_task_reliability_reconciler.py -q`
- `.venv/bin/python -m pytest tests/integration/test_multi_agent_workflow_service.py -q`

Expected: PASS before refactor

**Step 3: Extract delivery resolution logic**

Move code paths related to:
- `_finalize_guaranteed_delivery`
- `_mark_delivery_failed`
- `_sync_root_delivery_resolution`

into `delivery_resolution_service.py` with narrow dependencies.

**Step 4: Extract branch promotion and arbitration logic**

Move code paths related to:
- `_maybe_auto_promote_challenger`
- `_record_auto_arbitration_decision`
- branch scoreboard/arbitration coordination

into `branch_promotion_service.py`.

**Step 5: Reduce `TaskService` ownership surface**

Implementation notes:
- keep task CRUD and authorization in `TaskService`
- move durable session-memory persistence helpers behind a dedicated repository/service
- remove orchestration-only responsibilities that do not belong to task CRUD

**Step 6: Run targeted regression tests**

Run:
- `.venv/bin/python -m pytest tests/integration/test_task_reliability_reconciler.py -q`
- `.venv/bin/python -m pytest tests/integration/test_http_task_reliability_api.py -q`
- `.venv/bin/python -m pytest tests/integration/test_multi_agent_workflow_service.py -q`

Expected: PASS

**Step 7: Run the full suite**

Run: `.venv/bin/python -m pytest -q`

Expected: PASS

**Step 8: Commit**

```bash
git add src/video_agent/application/workflow_engine.py src/video_agent/application/task_service.py src/video_agent/application/delivery_resolution_service.py src/video_agent/application/branch_promotion_service.py src/video_agent/application/session_memory_repository.py src/video_agent/server/app.py tests/integration/test_task_reliability_reconciler.py tests/integration/test_multi_agent_workflow_service.py tests/integration/test_http_task_reliability_api.py
git commit -m "refactor: split agent orchestration services"
```

## Expected Outcomes

- After **P0**, the system can survive restarts without losing agent conversation context.
- After **P1**, the system becomes meaningfully multi-agent across both workflow review and thread-native video discussion while still remaining supervised and safe.
- After **P2**, future changes to autonomy, routing, and strategy promotion become much cheaper and less risky.

## Suggested Stop/Go Rule

- If time is limited, stop after **P1**. That is the point where the agent system becomes materially stronger in product terms.
- Only start **P2** after P0 and P1 are stable in production-like testing, because refactor value compounds only if the behavioral contract is already trustworthy.
