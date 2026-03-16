# Agent Persistent Memory Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an agent-scoped persistent memory layer that can promote session summaries into immutable snapshots, expose minimal MCP management tools, and allow `create_video_task` plus `revise_video_task` to explicitly reuse selected memories.

**Architecture:** Keep the existing `session-only memory` system intact and add a separate persistent layer centered on an `agent_memories` store plus a `PersistentMemoryService`. Promotion remains explicit, persistent snapshots remain immutable except for soft-disable, and request-time reuse is controlled through explicit `memory_ids` instead of automatic retrieval. Optional `memo0 / embedding` enhancement lives behind a best-effort adapter so the base workflow still works when enhancement is unavailable.

**Tech Stack:** Python 3.14, Pydantic, FastMCP, SQLite, pytest, existing task/revision workflow, local filesystem artifacts, and `@superpowers:test-driven-development`, `@superpowers:verification-before-completion`, `@superpowers:requesting-code-review`.

---

## Recommended Scope

This plan implements:

1. a new `agent_memories` persistent store
2. explicit `promote_session_memory`
3. MCP tools for `promote / list / get / disable`
4. explicit `memory_ids` on `create_video_task` and `revise_video_task`
5. prompt injection via `Persistent memory context: ...`
6. optional enhancement hooks for `memo0 / embedding`

It does **not** implement:

1. automatic promotion after successful tasks
2. automatic retrieval or similarity search at request time
3. persistent memory on `retry` or `auto-repair`
4. in-place editing of stored memory snapshots
5. rewriting `agent_profiles` to store memory

## Implementation Assumptions

1. Each promote operation creates one immutable persistent snapshot.
2. Persistent memories are always agent-scoped and must pass ownership checks before use.
3. Session memory and persistent memory remain separate prompt sections.
4. The enhancement layer is best-effort: base promotion succeeds even if enhancement cannot run.
5. Selected persistent memory IDs must be stored on tasks for later replay and auditing.

---

### Task 1: Persist immutable agent memory snapshots

**Files:**
- Create: `src/video_agent/domain/agent_memory_models.py`
- Modify: `src/video_agent/adapters/storage/schema.sql`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Test: `tests/unit/domain/test_agent_memory_models.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`

**Step 1: Write the failing tests**

Create `tests/unit/domain/test_agent_memory_models.py`:

```python
from video_agent.domain.agent_memory_models import AgentMemoryRecord


def test_agent_memory_record_defaults_to_active() -> None:
    record = AgentMemoryRecord(
        memory_id="mem-1",
        agent_id="agent-a",
        source_session_id="session-1",
        summary_text="Use a light background and clear labels.",
        summary_digest="digest-1",
        lineage_refs=["video-task://task-1/task.json"],
        snapshot={"entry_count": 1},
    )

    assert record.status == "active"
    assert record.disabled_at is None
```

Extend `tests/unit/adapters/storage/test_sqlite_store.py`:

```python
from video_agent.domain.agent_memory_models import AgentMemoryRecord


def test_store_round_trips_agent_memory_record(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    record = AgentMemoryRecord(
        memory_id="mem-1",
        agent_id="agent-a",
        source_session_id="session-1",
        summary_text="Use a light background and clear labels.",
        summary_digest="digest-1",
        lineage_refs=["video-task://task-1/task.json"],
        snapshot={"entry_count": 1},
    )

    store.create_agent_memory(record)
    loaded = store.get_agent_memory("mem-1")

    assert loaded is not None
    assert loaded.agent_id == "agent-a"
    assert loaded.summary_text == "Use a light background and clear labels."
    assert loaded.lineage_refs == ["video-task://task-1/task.json"]


def test_store_disables_agent_memory_without_deleting_it(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    record = AgentMemoryRecord(
        memory_id="mem-1",
        agent_id="agent-a",
        source_session_id="session-1",
        summary_text="Use a light background.",
        summary_digest="digest-1",
        lineage_refs=["video-task://task-1/task.json"],
        snapshot={"entry_count": 1},
    )

    store.create_agent_memory(record)
    assert store.disable_agent_memory("mem-1") is True

    loaded = store.get_agent_memory("mem-1")
    assert loaded is not None
    assert loaded.status == "disabled"
    assert loaded.disabled_at is not None
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/unit/domain/test_agent_memory_models.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  -q
```

Expected:
- FAIL because `AgentMemoryRecord` does not exist
- FAIL because `SQLiteTaskStore` has no persistent-memory methods
- FAIL because schema has no `agent_memories` table

**Step 3: Write minimal implementation**

Implement:

1. `src/video_agent/domain/agent_memory_models.py`

```python
class AgentMemoryRecord(BaseModel):
    memory_id: str
    agent_id: str
    source_session_id: str
    status: str = "active"
    summary_text: str
    summary_digest: str
    lineage_refs: list[str] = Field(default_factory=list)
    snapshot: dict[str, Any] = Field(default_factory=dict)
    enhancement: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    disabled_at: datetime | None = None
```

2. Add `agent_memories` to `schema.sql` with:
   - `memory_id`
   - `agent_id`
   - `source_session_id`
   - `status`
   - `summary_text`
   - `summary_digest`
   - `lineage_refs_json`
   - `snapshot_json`
   - `enhancement_json`
   - `created_at`
   - `disabled_at`

3. Add `SQLiteTaskStore` methods:
   - `create_agent_memory(...)`
   - `get_agent_memory(...)`
   - `list_agent_memories(...)`
   - `disable_agent_memory(...)`

Keep this task to persistence only. Do not wire MCP tools or prompts yet.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/domain/agent_memory_models.py \
  src/video_agent/adapters/storage/schema.sql \
  src/video_agent/adapters/storage/sqlite_store.py \
  tests/unit/domain/test_agent_memory_models.py \
  tests/unit/adapters/storage/test_sqlite_store.py
git commit -m "feat: persist agent memory snapshots"
```

---

### Task 2: Add persistent memory service and enhancement interface

**Files:**
- Create: `src/video_agent/application/persistent_memory_enhancer.py`
- Create: `src/video_agent/application/persistent_memory_service.py`
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/app.py`
- Test: `tests/unit/application/test_persistent_memory_service.py`
- Test: `tests/unit/test_settings.py`

**Step 1: Write the failing tests**

Create `tests/unit/application/test_persistent_memory_service.py`:

```python
from video_agent.application.persistent_memory_service import PersistentMemoryService
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.session_memory_models import SessionMemorySummary


def test_promote_session_summary_creates_agent_memory_record() -> None:
    created: list[AgentMemoryRecord] = []

    service = PersistentMemoryService(
        create_record=lambda record: created.append(record) or record,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            agent_id="agent-a",
            entries=[],
            lineage_refs=["video-task://task-1/task.json"],
            summary_text="Use a light background.",
            summary_digest="digest-1",
        ),
    )

    record = service.promote_session_memory("session-1", agent_id="agent-a")

    assert record.agent_id == "agent-a"
    assert record.source_session_id == "session-1"
    assert record.summary_text == "Use a light background."
```

Add an enhancement fallback test:

```python
def test_promote_still_succeeds_when_enhancement_is_unavailable() -> None:
    service = PersistentMemoryService(
        create_record=lambda record: record,
        get_session_summary=lambda session_id: SessionMemorySummary(
            session_id=session_id,
            agent_id="agent-a",
            entries=[],
            lineage_refs=["video-task://task-1/task.json"],
            summary_text="Use a light background.",
            summary_digest="digest-1",
        ),
        enhancer=lambda record: {"status": "unavailable", "code": "agent_memory_enhancement_unavailable"},
    )

    record = service.promote_session_memory("session-1", agent_id="agent-a")

    assert record.enhancement["status"] == "unavailable"
```

Extend `tests/unit/test_settings.py`:

```python
def test_settings_define_persistent_memory_defaults() -> None:
    settings = Settings()
    assert settings.persistent_memory_backend == "local"
    assert settings.persistent_memory_enable_embeddings is False
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/unit/application/test_persistent_memory_service.py \
  tests/unit/test_settings.py \
  -q
```

Expected:
- FAIL because `PersistentMemoryService` and the enhancer interface do not exist
- FAIL because persistent-memory settings do not exist

**Step 3: Write minimal implementation**

Implement:

1. `src/video_agent/application/persistent_memory_enhancer.py`

```python
class PersistentMemoryEnhancer(Protocol):
    def __call__(self, record: AgentMemoryRecord) -> dict[str, Any]: ...
```

2. `src/video_agent/application/persistent_memory_service.py`
   - `promote_session_memory(session_id, agent_id)`
   - `get_agent_memory(memory_id, agent_id)`
   - `list_agent_memories(agent_id, include_disabled=False)`
   - `disable_agent_memory(memory_id, agent_id)`

3. Add settings in `src/video_agent/config.py`:
   - `persistent_memory_backend: str = "local"`
   - `persistent_memory_enable_embeddings: bool = False`
   - `persistent_memory_embedding_provider: str | None = None`
   - `persistent_memory_embedding_model: str | None = None`

4. Wire `PersistentMemoryService` into `create_app_context(...)`, reusing `session_memory_service.summarize_session_memory(...)` as the summary source.

Keep the enhancement layer best-effort. Do not add MCP tools yet.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/persistent_memory_enhancer.py \
  src/video_agent/application/persistent_memory_service.py \
  src/video_agent/config.py \
  src/video_agent/server/app.py \
  tests/unit/application/test_persistent_memory_service.py \
  tests/unit/test_settings.py
git commit -m "feat: add persistent memory service"
```

---

### Task 3: Expose persistent memory MCP tools with agent isolation

**Files:**
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Test: `tests/integration/test_agent_memory_tools.py`
- Test: `tests/integration/test_fastmcp_server.py`

**Step 1: Write the failing tests**

Create `tests/integration/test_agent_memory_tools.py`:

```python
def test_promote_session_memory_requires_non_empty_session(app_context) -> None:
    payload = promote_session_memory_tool(app_context, {}, agent_principal=agent_principal("agent-a"), session_id="session-1")
    assert payload["error"]["code"] == "agent_memory_empty_session"


def test_agent_can_only_list_own_memories(app_context) -> None:
    seed_agent_memory(app_context, memory_id="mem-a", agent_id="agent-a")
    seed_agent_memory(app_context, memory_id="mem-b", agent_id="agent-b")

    payload = list_agent_memories_tool(app_context, {}, agent_principal=agent_principal("agent-a"))

    assert [item["memory_id"] for item in payload["items"]] == ["mem-a"]


def test_disabled_memory_cannot_be_used_after_disable(app_context) -> None:
    seed_agent_memory(app_context, memory_id="mem-a", agent_id="agent-a")
    payload = disable_agent_memory_tool(app_context, {"memory_id": "mem-a"}, agent_principal=agent_principal("agent-a"))

    assert payload["status"] == "disabled"
```

Extend `tests/integration/test_fastmcp_server.py`:

```python
def test_fastmcp_registers_persistent_memory_tools(tmp_path: Path) -> None:
    async def run() -> None:
        mcp = create_mcp_server(_build_fake_pipeline_settings(tmp_path))
        tool_names = {tool.name for tool in await mcp.list_tools()}
        assert {
            "promote_session_memory",
            "list_agent_memories",
            "get_agent_memory",
            "disable_agent_memory",
        } <= tool_names

    asyncio.run(run())
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/integration/test_agent_memory_tools.py \
  tests/integration/test_fastmcp_server.py \
  -q
```

Expected:
- FAIL because the persistent-memory MCP tools do not exist
- FAIL because FastMCP does not register them
- FAIL because agent isolation checks are missing

**Step 3: Write minimal implementation**

Implement:

1. New MCP tool helpers:
   - `promote_session_memory_tool(...)`
   - `list_agent_memories_tool(...)`
   - `get_agent_memory_tool(...)`
   - `disable_agent_memory_tool(...)`

2. Agent-scope validation:
   - only the current authenticated agent can view or disable their own memories
   - return `agent_memory_forbidden` for cross-agent access

3. FastMCP registration in `src/video_agent/server/fastmcp_server.py`

Make `promote_session_memory()` depend on the current `session_id`, not on a user-supplied arbitrary session from another agent.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/server/fastmcp_server.py \
  tests/integration/test_agent_memory_tools.py \
  tests/integration/test_fastmcp_server.py
git commit -m "feat: expose persistent memory tools"
```

---

### Task 4: Accept explicit `memory_ids` on create and revise

**Files:**
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Test: `tests/integration/test_mcp_tools.py`
- Test: `tests/integration/test_revision_and_cancel.py`
- Test: `tests/integration/test_agent_memory_tools.py`

**Step 1: Write the failing tests**

Extend `tests/integration/test_mcp_tools.py`:

```python
def test_create_video_task_persists_selected_memory_ids(temp_settings) -> None:
    app_context = create_app_context(temp_settings)
    seed_agent_memory(app_context, memory_id="mem-a", agent_id="local-anonymous")

    payload = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1", "memory_ids": ["mem-a"]},
    )

    task = app_context.store.get_task(payload["task_id"])
    assert task is not None
    assert task.selected_memory_ids == ["mem-a"]
```

Extend `tests/integration/test_revision_and_cancel.py`:

```python
def test_revision_can_attach_persistent_memory_ids(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    seed_agent_memory(app_context, memory_id="mem-a", agent_id="local-anonymous")

    child = app_context.task_service.revise_video_task(
        created.task_id,
        feedback="add labels",
        session_id="session-1",
        memory_ids=["mem-a"],
    )
    task = app_context.store.get_task(child.task_id)

    assert task is not None
    assert task.selected_memory_ids == ["mem-a"]
```

Add disabled-memory rejection:

```python
def test_create_rejects_disabled_memory_id(temp_settings) -> None:
    app_context = create_app_context(temp_settings)
    seed_agent_memory(app_context, memory_id="mem-a", agent_id="local-anonymous", status="disabled")

    payload = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1", "memory_ids": ["mem-a"]},
    )

    assert payload["error"]["code"] == "agent_memory_disabled"
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/integration/test_mcp_tools.py \
  tests/integration/test_revision_and_cancel.py \
  tests/integration/test_agent_memory_tools.py \
  -q
```

Expected:
- FAIL because `memory_ids` are not accepted or persisted
- FAIL because persistent memory validation does not happen

**Step 3: Write minimal implementation**

Implement:

1. Extend `VideoTask` with:
   - `selected_memory_ids: list[str] = Field(default_factory=list)`
   - `persistent_memory_context_summary: str | None = None`
   - `persistent_memory_context_digest: str | None = None`

2. Update `TaskService.create_video_task(...)` and `TaskService.revise_video_task(...)` to accept `memory_ids`.

3. Add a helper in `PersistentMemoryService`:
   - `resolve_memory_context(agent_id, memory_ids)` returning:
     - validated IDs
     - combined summary text
     - digest

4. Persist the selected IDs and combined context on tasks for replay.

Do not inject this into the prompt yet. Only validate and persist it.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/domain/models.py \
  src/video_agent/application/task_service.py \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/server/fastmcp_server.py \
  tests/integration/test_mcp_tools.py \
  tests/integration/test_revision_and_cancel.py \
  tests/integration/test_agent_memory_tools.py
git commit -m "feat: accept explicit persistent memory ids"
```

---

### Task 5: Inject persistent memory into create and revise prompts

**Files:**
- Modify: `src/video_agent/adapters/llm/prompt_builder.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Test: `tests/unit/adapters/llm/test_prompt_builder.py`
- Test: `tests/integration/test_workflow_completion.py`
- Test: `tests/integration/test_revision_and_cancel.py`

**Step 1: Write the failing tests**

Extend `tests/unit/adapters/llm/test_prompt_builder.py`:

```python
def test_prompt_builder_includes_persistent_memory_context_when_present() -> None:
    prompt = build_generation_prompt(
        prompt="draw a circle",
        output_profile={"quality_preset": "production"},
        feedback="add labels",
        persistent_memory_context="Always prefer a warm light background and explicit labels.",
    )

    assert "Persistent memory context:" in prompt
    assert "warm light background" in prompt
```

Extend `tests/integration/test_workflow_completion.py`:

```python
def test_create_task_uses_selected_persistent_memory_context(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    seed_agent_memory(
        app_context,
        memory_id="mem-a",
        agent_id="local-anonymous",
        summary_text="Always prefer a warm light background and explicit labels.",
    )

    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
        memory_ids=["mem-a"],
    )
    task = app_context.store.get_task(created.task_id)

    assert task is not None
    assert task.persistent_memory_context_summary is not None
```

Add a no-pollution assertion:

```python
def test_create_without_memory_ids_has_no_persistent_memory_context(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    task = app_context.store.get_task(created.task_id)

    assert task is not None
    assert task.persistent_memory_context_summary is None
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/unit/adapters/llm/test_prompt_builder.py \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_revision_and_cancel.py \
  -q
```

Expected:
- FAIL because `build_generation_prompt(...)` has no persistent-memory argument
- FAIL because tasks do not inject persistent memory context
- FAIL because create/revise do not distinguish session and persistent memory contexts

**Step 3: Write minimal implementation**

Implement:

1. Extend `build_generation_prompt(...)` with:

```python
persistent_memory_context: str | None = None
```

and add a separate prompt section:

```python
if persistent_memory_context:
    lines.append(f"Persistent memory context: {persistent_memory_context}")
```

2. Update `TaskService` to compute persistent memory context only when `memory_ids` are present.

3. Update `WorkflowEngine.run_task(...)` to pass `task.persistent_memory_context_summary` into the prompt builder.

Do not inject persistent memory into `retry` or `auto-repair`.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/adapters/llm/prompt_builder.py \
  src/video_agent/application/task_service.py \
  src/video_agent/application/workflow_engine.py \
  tests/unit/adapters/llm/test_prompt_builder.py \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_revision_and_cancel.py
git commit -m "feat: inject persistent memory into create and revise"
```

---

### Task 6: Add optional `memo0 / embedding` enhancement scaffolding

**Files:**
- Modify: `src/video_agent/application/persistent_memory_service.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Test: `tests/unit/application/test_persistent_memory_service.py`
- Test: `tests/integration/test_agent_memory_tools.py`

**Step 1: Write the failing tests**

Add a best-effort response assertion:

```python
def test_promote_returns_enhancement_warning_without_failing(app_context) -> None:
    app_context.session_memory_registry.ensure_session("session-a", agent_id="agent-a")
    app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-a", agent_principal=agent_principal("agent-a"))
    app_context.persistent_memory_service.enhancer = lambda record: {
        "status": "unavailable",
        "code": "agent_memory_enhancement_unavailable",
    }

    payload = promote_session_memory_tool(app_context, {}, agent_principal=agent_principal("agent-a"), session_id="session-a")

    assert payload["memory_id"]
    assert payload["enhancement"]["code"] == "agent_memory_enhancement_unavailable"
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/unit/application/test_persistent_memory_service.py \
  tests/integration/test_agent_memory_tools.py \
  -q
```

Expected:
- FAIL because promote responses do not surface enhancement state yet

**Step 3: Write minimal implementation**

Implement:

1. Add enhancement metadata to promote responses.
2. Make the service expose best-effort enhancement state whether backend is `local` or a future `memo0`.
3. Keep backend branching shallow: `local` does nothing, `memo0` remains optional and may return `unavailable`.

Do not implement automatic retrieval in this task.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/persistent_memory_service.py \
  src/video_agent/server/mcp_tools.py \
  tests/unit/application/test_persistent_memory_service.py \
  tests/integration/test_agent_memory_tools.py
git commit -m "feat: add persistent memory enhancement hooks"
```

---

### Task 7: Verify the implementation and request review

**Files:**
- Modify: `docs/plans/2026-03-16-agent-persistent-memory-foundation-design.md` (only if implementation drift requires it)
- Modify: `docs/plans/2026-03-16-agent-persistent-memory-foundation-implementation-plan.md` (only if implementation drift requires it)

**Step 1: Run focused regression suites**

Run:

```bash
PATH="/Users/lvxiaoer/Documents/codeWork/easy-manim/.venv/bin:$PATH" \
python -m pytest \
  tests/unit/domain/test_agent_memory_models.py \
  tests/unit/application/test_persistent_memory_service.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/unit/adapters/llm/test_prompt_builder.py \
  tests/integration/test_agent_memory_tools.py \
  tests/integration/test_mcp_tools.py \
  tests/integration/test_revision_and_cancel.py \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_fastmcp_server.py \
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

1. agent ownership checks for all memory operations
2. `memory_ids` replay and prompt injection correctness
3. immutable snapshot semantics versus disable-only updates
4. enhancement-layer failures not breaking base promotion

**Step 4: Commit any last doc alignment updates if needed**

```bash
git add \
  docs/plans/2026-03-16-agent-persistent-memory-foundation-design.md \
  docs/plans/2026-03-16-agent-persistent-memory-foundation-implementation-plan.md
git commit -m "docs: align persistent memory plan with implementation"
```
