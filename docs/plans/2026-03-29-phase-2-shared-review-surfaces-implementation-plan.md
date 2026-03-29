# Phase 2 Shared Review Surfaces Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the next phase after the March 28 phase-1 work by adding persistent review records, reviewer-facing read surfaces, and per-lineage workflow status without changing task ownership.

**Architecture:** Reuse the existing supervised review-regenerate loop from phase 1. Persist each review decision as an immutable record, derive workflow status from lineage tasks plus those review records, and expose the resulting read models over HTTP and MCP through read-only surfaces. Keep reviewers read-only and keep all mutation paths routed through the current orchestrator-owned `apply_review_decision(...)` flow.

**Tech Stack:** Python, Pydantic, FastAPI, FastMCP, SQLite, pytest, existing task lineage and artifact-store-backed workflow pipeline

---

## Why This Is The Next Stage

Based on the March 28 docs and current repo state:

1. `docs/plans/2026-03-28-agent-reliability-backend-implementation-plan.md` Tasks 7-9 are already represented in the codebase and covered by:
   - `tests/integration/test_http_task_reliability_api.py`
   - `tests/integration/test_mcp_task_reliability_tools.py`
   - `tests/unit/application/test_policy_promotion_service.py`
   - `tests/integration/test_eval_strategy_promotion.py`
2. `docs/plans/2026-03-28-supervised-multi-agent-workflow-implementation-plan.md` phase-1 workflow endpoints and docs are already present.
3. `docs/plans/2026-03-28-multi-agent-workflow-design.md` says the next meaningful step after phase 1 is **Phase 2: Shared review surfaces**:
   - review artifacts or review records
   - reviewer-specific read APIs or resources
   - per-lineage workflow status

This plan turns those phase-2 design bullets into implementation tasks.

### Task 1: Persist Immutable Review Records

**Files:**
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/application/multi_agent_workflow_service.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`
- Test: `tests/integration/test_multi_agent_workflow_service.py`

**Step 1: Write the failing tests**

```python
def test_store_creates_and_lists_review_records() -> None:
    record = store.create_review_record(...)
    listed = store.list_review_records(root_task_id="root-1")

    assert listed[0].review_id == record.review_id
    assert listed[0].decision["decision"] == "revise"


def test_apply_review_decision_persists_review_record(tmp_path: Path) -> None:
    outcome = service.apply_review_decision(...)
    records = app_context.store.list_review_records(root_task_id=created.task_id)

    assert outcome.action == "revise"
    assert records[-1].outcome["action"] == "revise"
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/integration/test_multi_agent_workflow_service.py -q
```

Expected: FAIL because review record persistence does not exist yet.

**Step 3: Write minimal implementation**

Add a review record model in `src/video_agent/domain/review_workflow_models.py` with immutable payloads:

```python
class ReviewRecord(BaseModel):
    review_id: str
    task_id: str
    root_task_id: str
    decision: dict[str, Any]
    bundle_snapshot: dict[str, Any]
    outcome: dict[str, Any]
    actor_role: str | None = None
    created_at: datetime
```

Add SQLite migration and store methods:

```python
create_review_record(...)
list_review_records(root_task_id: str, task_id: str | None = None)
```

Persist the record from `MultiAgentWorkflowService.apply_review_decision(...)` after the policy chooses an action and before returning the outcome.

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/domain/review_workflow_models.py \
  src/video_agent/adapters/storage/sqlite_schema.py \
  src/video_agent/adapters/storage/sqlite_store.py \
  src/video_agent/application/multi_agent_workflow_service.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/integration/test_multi_agent_workflow_service.py
git commit -m "feat: persist immutable review records"
```

### Task 2: Add Per-Lineage Workflow Status Read Model

**Files:**
- Create: `src/video_agent/application/workflow_status_service.py`
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/server/app.py`
- Test: `tests/unit/application/test_workflow_status_service.py`
- Test: `tests/integration/test_multi_agent_workflow_service.py`

**Step 1: Write the failing tests**

```python
def test_workflow_status_summarizes_lineage_attempts_and_latest_review() -> None:
    snapshot = service.get_status(root_task_id="root-1")

    assert snapshot.root_task_id == "root-1"
    assert snapshot.attempt_count == 2
    assert snapshot.last_review_action == "revise"
    assert snapshot.latest_task_id is not None
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/unit/application/test_workflow_status_service.py \
  tests/integration/test_multi_agent_workflow_service.py -q
```

Expected: FAIL because there is no workflow status service yet.

**Step 3: Write minimal implementation**

Add a status model:

```python
class WorkflowStatusSnapshot(BaseModel):
    root_task_id: str
    latest_task_id: str | None = None
    accepted_task_id: str | None = None
    attempt_count: int = 0
    child_attempt_count: int = 0
    current_status: str | None = None
    quality_gate_status: str | None = None
    last_review_action: str | None = None
    workflow_state: str
```

Create `WorkflowStatusService` that derives status from:

1. `store.list_lineage_tasks(root_task_id)`
2. `store.list_review_records(root_task_id)`
3. accepted-as-best flags already stored on tasks

Wire it into `server/app.py`.

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/workflow_status_service.py \
  src/video_agent/domain/review_workflow_models.py \
  src/video_agent/server/app.py \
  tests/unit/application/test_workflow_status_service.py \
  tests/integration/test_multi_agent_workflow_service.py
git commit -m "feat: derive per-lineage workflow status"
```

### Task 3: Expose Reviewer-Facing Read Surfaces Over MCP and HTTP

**Files:**
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/http_api.py`
- Test: `tests/integration/test_mcp_multi_agent_workflow_tools.py`
- Test: `tests/integration/test_http_multi_agent_workflow_api.py`

**Step 1: Write the failing tests**

```python
def test_http_review_records_and_workflow_status_are_read_only_and_agent_scoped(tmp_path: Path) -> None:
    reviews = client.get(f"/api/tasks/{task_id}/reviews", headers=headers)
    status_payload = client.get(f"/api/tasks/{root_task_id}/workflow-status", headers=headers)

    assert reviews.status_code == 200
    assert status_payload.status_code == 200


def test_mcp_workflow_status_tool_returns_latest_review_action(tmp_path: Path) -> None:
    payload = get_workflow_status_tool(app_context, {"root_task_id": created["task_id"]})

    assert payload["workflow_status"]["last_review_action"] == "revise"
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/integration/test_mcp_multi_agent_workflow_tools.py \
  tests/integration/test_http_multi_agent_workflow_api.py -q
```

Expected: FAIL because these read surfaces do not exist yet.

**Step 3: Write minimal implementation**

Add read-only MCP tools:

```python
list_review_records_tool(...)
get_workflow_status_tool(...)
```

Add read-only HTTP endpoints:

```python
GET /api/tasks/{task_id}/reviews
GET /api/tasks/{task_id}/workflow-status
```

Rules:

1. Keep them behind `task:read`.
2. Keep them agent-scoped like the existing review bundle and task APIs.
3. Return immutable records and derived workflow status only. No new mutation paths.

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/server/fastmcp_server.py \
  src/video_agent/server/http_api.py \
  tests/integration/test_mcp_multi_agent_workflow_tools.py \
  tests/integration/test_http_multi_agent_workflow_api.py
git commit -m "feat: expose review records and workflow status"
```

### Task 4: Documentation, Reviewer Contract, and Regression Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/runbooks/agent-self-serve.md`
- Modify: `docs/plans/2026-03-28-multi-agent-workflow-design.md`
- Modify: `tests/integration/test_http_task_api.py`
- Modify: `tests/integration/test_mcp_tools.py`

**Step 1: Write the failing regression checks**

Add regression assertions proving:

1. existing create/list/get/result flows still behave the same
2. new review-record/status reads do not leak cross-agent data
3. reviewer-only identities can inspect but not mutate

**Step 2: Run targeted regression tests**

Run:

```bash
pytest \
  tests/integration/test_http_task_api.py \
  tests/integration/test_mcp_tools.py \
  tests/integration/test_http_multi_agent_workflow_api.py \
  tests/integration/test_mcp_multi_agent_workflow_tools.py -q
```

Expected: PASS, or focused FAILs that identify outdated assertions.

**Step 3: Update docs**

Document:

1. immutable review records
2. per-lineage workflow status
3. reviewer read-only surfaces and scope expectations
4. that phase 2 still preserves orchestrator-owned mutation

**Step 4: Run the final verification set**

Run:

```bash
pytest \
  tests/unit/domain/test_review_workflow_models.py \
  tests/unit/application/test_workflow_loop_policy.py \
  tests/unit/application/test_workflow_status_service.py \
  tests/unit/test_settings.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/integration/test_review_bundle_builder.py \
  tests/integration/test_multi_agent_workflow_service.py \
  tests/integration/test_mcp_multi_agent_workflow_tools.py \
  tests/integration/test_http_multi_agent_workflow_api.py \
  tests/integration/test_fastmcp_server.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_mcp_tools.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add \
  README.md \
  docs/runbooks/agent-self-serve.md \
  docs/plans/2026-03-28-multi-agent-workflow-design.md \
  tests/integration/test_http_task_api.py \
  tests/integration/test_mcp_tools.py
git commit -m "docs: document phase-2 shared review surfaces"
```

## Notes for the Implementer

1. Do not change `agent_id` task ownership in this phase.
2. Do not add direct reviewer mutation APIs. Reviewers should only read bundles, records, and status.
3. Prefer deriving workflow status from existing lineage tasks plus persisted review records instead of inventing another mutable state machine.
4. Persist full review record payloads in JSON so future specialist reviewer UIs and external runtimes can replay the reasoning without schema churn.
5. Keep the new phase-2 read model minimal. Avoid ACL redesign, shared workflow memory, or direct cross-agent writes until phase 3.
