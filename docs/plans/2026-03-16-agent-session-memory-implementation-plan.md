# Agent Session Memory Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add session-scoped short-term memory that records task and artifact summaries, keeps memory strictly isolated per live MCP session, exposes memory inspection/clear tools, and injects memory only into revise, retry, and auto-repair flows.

**Architecture:** Extend the existing in-memory session layer with a dedicated `SessionMemoryRegistry` that maps the current transport session to a stable `session_id`, then persist that `session_id` on tasks so background auto-repair can keep using the same session memory scope. Build deterministic memory summaries from task lineage, validations, and artifact references, expose them through MCP tools, and store the exact injected memory summary on follow-up tasks for replay/debugging.

**Tech Stack:** Python 3.14, Pydantic, FastMCP, SQLite, pytest, local filesystem artifacts, existing revision/auto-repair workflow, and `@superpowers:test-driven-development`, `@superpowers:verification-before-completion`, `@superpowers:requesting-code-review`.

---

## Recommended Scope

This plan implements **session-only memory**:

1. strict per-live-session isolation
2. readable and clearable memory state
3. deterministic summary export for future persistent memory
4. automatic memory injection only for `revise_video_task`, `retry_video_task`, and auto-repair

It explicitly does **not** implement:

1. cross-session persistent memory
2. transcript storage
3. learned preference promotion
4. database-backed memory retention

## Implementation Assumptions

1. A stable `session_id` must exist independently of `agent_id`.
2. The session memory registry remains in-memory for this phase.
3. `VideoTask.session_id` is persisted so background auto-repair can reuse the original session scope.
4. Empty or missing session memory is not an error; iterative flows proceed with an empty summary.
5. The memory summary is deterministic and compact enough to fit safely inside prompts.

---

### Task 1: Add session memory models and registry

**Files:**
- Create: `src/video_agent/domain/session_memory_models.py`
- Create: `src/video_agent/server/session_memory.py`
- Test: `tests/unit/server/test_session_memory.py`

**Step 1: Write the failing tests**

Create `tests/unit/server/test_session_memory.py` with coverage for session allocation, isolation, and stable empty responses:

```python
from video_agent.server.session_memory import SessionMemoryRegistry


def test_registry_allocates_distinct_session_ids_for_distinct_session_keys() -> None:
    registry = SessionMemoryRegistry()

    session_a = registry.ensure_session("session-a", agent_id="agent-a")
    session_b = registry.ensure_session("session-b", agent_id="agent-a")

    assert session_a.session_id != session_b.session_id


def test_registry_returns_stable_empty_memory_snapshot() -> None:
    registry = SessionMemoryRegistry()
    session = registry.ensure_session("session-a", agent_id="agent-a")

    snapshot = registry.get_snapshot(session.session_id)

    assert snapshot.session_id == session.session_id
    assert snapshot.agent_id == "agent-a"
    assert snapshot.entries == []
    assert snapshot.entry_count == 0


def test_clear_only_removes_the_target_session() -> None:
    registry = SessionMemoryRegistry()
    session_a = registry.ensure_session("session-a", agent_id="agent-a")
    session_b = registry.ensure_session("session-b", agent_id="agent-a")

    registry.clear_session(session_a.session_id)

    assert registry.get_snapshot(session_a.session_id).entry_count == 0
    assert registry.get_snapshot(session_b.session_id).session_id == session_b.session_id
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest tests/unit/server/test_session_memory.py -q
```

Expected:
- FAIL because `SessionMemoryRegistry` and the session memory models do not exist

**Step 3: Write the minimal implementation**

Implement:

1. `src/video_agent/domain/session_memory_models.py` with models such as:

```python
class SessionHandle(BaseModel):
    session_id: str
    agent_id: str | None = None


class SessionMemoryAttempt(BaseModel):
    task_id: str
    attempt_kind: str
    feedback_summary: str | None = None


class SessionMemoryEntry(BaseModel):
    root_task_id: str
    latest_task_id: str
    task_goal_summary: str
    attempts: list[SessionMemoryAttempt] = Field(default_factory=list)


class SessionMemorySnapshot(BaseModel):
    session_id: str
    agent_id: str | None = None
    entries: list[SessionMemoryEntry] = Field(default_factory=list)

    @property
    def entry_count(self) -> int:
        return len(self.entries)
```

2. `src/video_agent/server/session_memory.py` with:
   - `ensure_session(session_key, agent_id)`
   - `get_session_id(session_key)`
   - `get_snapshot(session_id)`
   - `clear_session(session_id)`

Keep this task intentionally narrow: session identity + empty-state registry only. Do not wire it into the app yet.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/domain/session_memory_models.py \
  src/video_agent/server/session_memory.py \
  tests/unit/server/test_session_memory.py
git commit -m "feat: add session memory registry"
```

---

### Task 2: Persist `session_id` and memory context fields on tasks

**Files:**
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/adapters/storage/schema.sql`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`
- Test: `tests/integration/test_revision_and_cancel.py`

**Step 1: Write the failing tests**

Extend `tests/unit/adapters/storage/test_sqlite_store.py`:

```python
def test_store_persists_task_session_id_and_memory_context(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    task = VideoTask(
        prompt="draw a circle",
        session_id="session-1",
        memory_context_summary="Recent attempts already established a light background.",
        memory_context_digest="digest-1",
    )

    store.create_task(task, idempotency_key="mem-1")
    loaded = store.get_task(task.task_id)

    assert loaded is not None
    assert loaded.session_id == "session-1"
    assert loaded.memory_context_summary == "Recent attempts already established a light background."
    assert loaded.memory_context_digest == "digest-1"
```

Extend `tests/integration/test_revision_and_cancel.py`:

```python
def test_revision_inherits_parent_session_id(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )

    child = app_context.task_service.revise_video_task(created.task_id, feedback="add labels")
    task = app_context.store.get_task(child.task_id)

    assert task is not None
    assert task.session_id == "session-1"
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/integration/test_revision_and_cancel.py \
  -q
```

Expected:
- FAIL because `VideoTask` has no `session_id`
- FAIL because memory context fields are missing
- FAIL because revisions do not preserve session scope yet

**Step 3: Write the minimal implementation**

Implement:

1. Extend `VideoTask` in `src/video_agent/domain/models.py` with:

```python
session_id: str | None = None
memory_context_summary: str | None = None
memory_context_digest: str | None = None
```

2. Ensure `VideoTask.from_revision(...)` carries `session_id` forward and leaves the child ready for a newly computed `memory_context_summary`.

3. Add `session_id` to `video_tasks` in `schema.sql` and backfill it via `_ensure_column(...)` in `SQLiteTaskStore.initialize()`.

4. Persist `session_id` in `create_task(...)` and `update_task(...)`.

Do not compute any memory summary yet; just make the task model and storage capable of carrying it.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/domain/models.py \
  src/video_agent/adapters/storage/schema.sql \
  src/video_agent/adapters/storage/sqlite_store.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/integration/test_revision_and_cancel.py
git commit -m "feat: persist task session ids"
```

---

### Task 3: Add session memory service and record task lineage into memory

**Files:**
- Create: `src/video_agent/application/session_memory_service.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/auto_repair_service.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/config.py`
- Test: `tests/unit/application/test_session_memory_service.py`
- Test: `tests/unit/test_settings.py`
- Test: `tests/integration/test_revision_and_cancel.py`
- Test: `tests/integration/test_auto_repair_loop.py`

**Step 1: Write the failing tests**

Create `tests/unit/application/test_session_memory_service.py`:

```python
from video_agent.application.session_memory_service import SessionMemoryService
from video_agent.server.session_memory import SessionMemoryRegistry
from video_agent.domain.models import VideoTask


def test_create_task_is_recorded_but_not_injected_into_its_own_context() -> None:
    registry = SessionMemoryRegistry()
    session = registry.ensure_session("session-a", agent_id="agent-a")
    service = SessionMemoryService(registry=registry)
    task = VideoTask(prompt="draw a circle", session_id=session.session_id)

    service.record_task_created(task, attempt_kind="create")
    summary = service.summarize_session_memory(session.session_id)

    assert summary.entry_count == 1
    assert task.memory_context_summary is None


def test_summary_is_available_for_followup_attempts() -> None:
    registry = SessionMemoryRegistry()
    session = registry.ensure_session("session-a", agent_id="agent-a")
    service = SessionMemoryService(registry=registry)
    root = VideoTask(prompt="draw a circle", session_id=session.session_id)

    service.record_task_created(root, attempt_kind="create")
    summary = service.summarize_session_memory(session.session_id)

    assert "draw a circle" in summary.summary_text
    assert summary.summary_digest is not None
```

Extend `tests/integration/test_revision_and_cancel.py`:

```python
def test_revision_child_receives_memory_context_summary(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )

    child = app_context.task_service.revise_video_task(created.task_id, feedback="add title")
    stored = app_context.store.get_task(child.task_id)

    assert stored is not None
    assert stored.memory_context_summary is not None
    assert stored.memory_context_digest is not None
```

Extend `tests/integration/test_auto_repair_loop.py`:

```python
def test_auto_repair_child_keeps_parent_session_scope(tmp_path: Path) -> None:
    app = create_app_context(_build_failing_render_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle", session_id="session-1")

    app.worker.run_once()

    tasks = app.store.list_tasks(limit=10)
    child_ids = [item["task_id"] for item in tasks if item["task_id"] != created.task_id]
    child_task = app.store.get_task(child_ids[0])

    assert child_task is not None
    assert child_task.session_id == "session-1"
    assert child_task.memory_context_summary is not None
```

Extend `tests/unit/test_settings.py` with sane defaults:

```python
def test_settings_define_session_memory_limits() -> None:
    settings = Settings()
    assert settings.session_memory_max_entries == 5
    assert settings.session_memory_max_attempts_per_entry == 3
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/unit/application/test_session_memory_service.py \
  tests/unit/test_settings.py \
  tests/integration/test_revision_and_cancel.py \
  tests/integration/test_auto_repair_loop.py \
  -q
```

Expected:
- FAIL because the session memory service does not exist
- FAIL because `TaskService` does not record or summarize session memory
- FAIL because `AutoRepairService` does not reuse the parent task's session scope
- FAIL because settings have no session memory limits

**Step 3: Write the minimal implementation**

Implement:

1. `src/video_agent/application/session_memory_service.py` with methods such as:
   - `record_task_created(task, attempt_kind)`
   - `get_session_memory(session_id)`
   - `summarize_session_memory(session_id)`
   - `clear_session_memory(session_id)`
   - `compute_summary_digest(summary_text)`

2. Add settings in `src/video_agent/config.py`:

```python
session_memory_max_entries: int = 5
session_memory_max_attempts_per_entry: int = 3
session_memory_summary_char_limit: int = 2000
```

3. Wire the registry and service into `create_app_context(...)`.

4. Update `TaskService`:
   - accept `session_id` on `create_video_task(...)`
   - record root tasks into session memory after persistence
   - compute `memory_context_summary` only for `revise_video_task(...)` and `retry_video_task(...)`
   - carry `session_id` into child tasks

5. Update `AutoRepairService` so background repairs read the failed parent's `session_id`, compute a summary if present, and pass it into child task creation.

Keep the summary deterministic and compact. Do not add MCP tools yet.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/session_memory_service.py \
  src/video_agent/application/task_service.py \
  src/video_agent/application/auto_repair_service.py \
  src/video_agent/server/app.py \
  src/video_agent/config.py \
  tests/unit/application/test_session_memory_service.py \
  tests/unit/test_settings.py \
  tests/integration/test_revision_and_cancel.py \
  tests/integration/test_auto_repair_loop.py
git commit -m "feat: add session memory service"
```

---

### Task 4: Expose session memory tools through FastMCP

**Files:**
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Test: `tests/integration/test_mcp_tools.py`
- Test: `tests/integration/test_fastmcp_server.py`
- Create: `tests/integration/test_session_memory_tools.py`

**Step 1: Write the failing tests**

Create `tests/integration/test_session_memory_tools.py`:

```python
def test_get_session_memory_returns_stable_empty_payload(app_context) -> None:
    payload = get_session_memory_tool(app_context, {}, session_id="session-1")

    assert payload["session_id"] == "session-1"
    assert payload["entries"] == []
    assert payload["entry_count"] == 0


def test_clear_session_memory_only_clears_target_session(app_context) -> None:
    app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-a")
    app_context.task_service.create_video_task(prompt="draw a square", session_id="session-b")

    cleared = clear_session_memory_tool(app_context, {}, session_id="session-a")
    memory_a = get_session_memory_tool(app_context, {}, session_id="session-a")
    memory_b = get_session_memory_tool(app_context, {}, session_id="session-b")

    assert cleared["cleared"] is True
    assert memory_a["entry_count"] == 0
    assert memory_b["entry_count"] == 1
```

Extend `tests/integration/test_fastmcp_server.py`:

```python
def test_fastmcp_registers_session_memory_tools(tmp_path: Path) -> None:
    async def run() -> None:
        mcp = create_mcp_server(_build_fake_pipeline_settings(tmp_path))
        tool_names = {tool.name for tool in await mcp.list_tools()}
        assert {
            "get_session_memory",
            "summarize_session_memory",
            "clear_session_memory",
        } <= tool_names

    asyncio.run(run())
```

Also add a same-agent-two-session isolation test:

```python
def test_same_agent_sessions_do_not_share_memory(tmp_path: Path) -> None:
    async def run() -> None:
        settings = _build_fake_pipeline_settings(tmp_path)
        settings.auth_mode = "required"
        settings.run_embedded_worker = False
        _seed_agent(settings)

        mcp_a = create_mcp_server(settings)
        mcp_b = create_mcp_server(settings)

        await mcp_a.call_tool("authenticate_agent", {"agent_token": "agent-a-secret"})
        await mcp_b.call_tool("authenticate_agent", {"agent_token": "agent-a-secret"})
        await mcp_a.call_tool("create_video_task", {"prompt": "draw a circle"})

        _, memory_a = await mcp_a.call_tool("get_session_memory", {})
        _, memory_b = await mcp_b.call_tool("get_session_memory", {})

        assert memory_a["entry_count"] == 1
        assert memory_b["entry_count"] == 0
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/integration/test_session_memory_tools.py \
  tests/integration/test_fastmcp_server.py \
  tests/integration/test_mcp_tools.py \
  -q
```

Expected:
- FAIL because the session memory tools do not exist
- FAIL because `FastMCP` does not register them
- FAIL because current tool wiring does not resolve or pass a `session_id`

**Step 3: Write the minimal implementation**

Implement:

1. New tool helpers in `src/video_agent/server/mcp_tools.py`:
   - `get_session_memory_tool(...)`
   - `summarize_session_memory_tool(...)`
   - `clear_session_memory_tool(...)`

2. Update `create_video_task_tool(...)`, `revise_video_task_tool(...)`, and `retry_video_task_tool(...)` to accept a `session_id`.

3. Update `src/video_agent/server/fastmcp_server.py`:
   - ensure a stable `session_id` exists for the current `Context`
   - pass `session_id` into task tools
   - register the three new session memory tools

4. Keep responses stable:
   - empty memory does not error
   - clear on empty returns zero counts

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/server/fastmcp_server.py \
  tests/integration/test_session_memory_tools.py \
  tests/integration/test_fastmcp_server.py \
  tests/integration/test_mcp_tools.py
git commit -m "feat: expose session memory tools"
```

---

### Task 5: Inject session memory into generation and targeted repair prompts

**Files:**
- Modify: `src/video_agent/adapters/llm/prompt_builder.py`
- Modify: `src/video_agent/application/repair_prompt_builder.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/task_service.py`
- Test: `tests/unit/adapters/llm/test_prompt_builder.py`
- Test: `tests/unit/application/test_repair_prompt_builder.py`
- Test: `tests/integration/test_auto_repair_loop.py`

**Step 1: Write the failing tests**

Extend `tests/unit/adapters/llm/test_prompt_builder.py`:

```python
def test_prompt_builder_includes_session_memory_context_when_present() -> None:
    prompt = build_generation_prompt(
        prompt="draw a circle",
        output_profile={"quality_preset": "production"},
        feedback="add labels",
        style_hints={"tone": "teaching"},
        memory_context_summary="Recent attempts succeeded with a light background and failed on blank openings.",
    )

    assert "Session memory context:" in prompt
    assert "failed on blank openings" in prompt
```

Extend `tests/unit/application/test_repair_prompt_builder.py`:

```python
def test_repair_feedback_includes_session_memory_context() -> None:
    feedback = build_targeted_repair_feedback(
        issue_code="near_blank_preview",
        failure_context={"summary": "blank opening"},
        memory_context_summary="Earlier attempts already established a working light-background layout.",
    )

    assert "Session memory context:" in feedback
    assert "working light-background layout" in feedback
```

Extend `tests/integration/test_auto_repair_loop.py`:

```python
def test_auto_repair_feedback_carries_session_memory_summary(tmp_path: Path) -> None:
    app = create_app_context(_build_failing_render_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    app.task_service.revise_video_task(created.task_id, feedback="keep the light background")

    app.worker.run_once()

    tasks = app.store.list_tasks(limit=10)
    child_ids = [item["task_id"] for item in tasks if item["task_id"] != created.task_id]
    child_task = app.store.get_task(child_ids[-1])

    assert child_task is not None
    assert "Session memory context:" in (child_task.feedback or "")
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/unit/adapters/llm/test_prompt_builder.py \
  tests/unit/application/test_repair_prompt_builder.py \
  tests/integration/test_auto_repair_loop.py \
  -q
```

Expected:
- FAIL because prompt builders do not accept `memory_context_summary`
- FAIL because workflow execution does not pass memory context into prompts
- FAIL because auto-repair feedback does not mention session memory

**Step 3: Write the minimal implementation**

Implement:

1. Extend `build_generation_prompt(...)` with:

```python
memory_context_summary: str | None = None
```

and render a compact section only when the value is present.

2. Extend `build_targeted_repair_feedback(...)` with the same optional argument and insert it near the top of the repair prompt.

3. Update `WorkflowEngine.run_task(...)` to pass `task.memory_context_summary` into `self.prompt_builder(...)`.

4. Update the task creation paths so only follow-up tasks receive a non-empty `memory_context_summary`.

Verify that the first root `create_video_task(...)` remains memory-clean.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/adapters/llm/prompt_builder.py \
  src/video_agent/application/repair_prompt_builder.py \
  src/video_agent/application/workflow_engine.py \
  src/video_agent/application/task_service.py \
  tests/unit/adapters/llm/test_prompt_builder.py \
  tests/unit/application/test_repair_prompt_builder.py \
  tests/integration/test_auto_repair_loop.py
git commit -m "feat: inject session memory into followup prompts"
```

---

### Task 6: Run verification and request code review

**Files:**
- Modify: `docs/plans/2026-03-16-agent-session-memory-design.md` (only if implementation details drift)
- Modify: `docs/plans/2026-03-16-agent-session-memory-implementation-plan.md` (only if implementation details drift)

**Step 1: Run the focused regression suites**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/unit/server/test_session_memory.py \
  tests/unit/application/test_session_memory_service.py \
  tests/unit/adapters/llm/test_prompt_builder.py \
  tests/unit/application/test_repair_prompt_builder.py \
  tests/integration/test_revision_and_cancel.py \
  tests/integration/test_auto_repair_loop.py \
  tests/integration/test_session_memory_tools.py \
  tests/integration/test_fastmcp_server.py \
  tests/integration/test_mcp_tools.py \
  -q
```

Expected: PASS

**Step 2: Run the full suite**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest -q
```

Expected: PASS

**Step 3: Request code review**

Use `@superpowers:requesting-code-review` and have the reviewer focus on:

1. same-agent multi-session isolation
2. auto-repair behavior when session memory is missing
3. prompt-size growth and summary truncation
4. empty-memory response stability

**Step 4: Commit final verification updates if needed**

```bash
git add docs/plans/2026-03-16-agent-session-memory-design.md docs/plans/2026-03-16-agent-session-memory-implementation-plan.md
git commit -m "docs: align session memory plan with implementation"
```
