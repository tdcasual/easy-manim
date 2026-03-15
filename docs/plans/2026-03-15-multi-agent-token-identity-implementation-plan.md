# Multi-Agent Token Identity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add transport-compatible token-based agent identity, per-agent default preferences, and agent-scoped task/resource isolation to `easy-manim` without rewriting the existing video workflow engine.

**Architecture:** Keep the current `FastMCP + SQLite + filesystem artifacts` execution core intact. Introduce a thin identity layer that authenticates an MCP session via `authenticate_agent(agent_token)`, resolves an `agent profile`, injects an `effective request config` into task creation, and enforces agent ownership checks for tools and resources.

**Tech Stack:** Python 3.14, Pydantic, FastMCP, SQLite, pytest, local filesystem artifacts, existing task/revision workflow, and `@superpowers:test-driven-development`, `@superpowers:verification-before-completion`, `@superpowers:requesting-code-review`.

---

## Recommended Scope

This plan implements **Phase 1 only**:

1. token-backed agent identity
2. per-agent profile defaults
3. task attribution via `agent_id`
4. MCP session authentication
5. task and resource isolation

It explicitly does **not** implement:

1. session memory
2. long-term preference learning
3. billing or quota systems
4. cloud auth providers

## Implementation Assumptions

1. Canonical transport-compatible token entrypoint is a new MCP tool: `authenticate_agent(agent_token)`.
2. In `auth_mode=required`, task tools and task resources require a previously authenticated MCP session.
3. In `auth_mode=disabled`, the system uses a local anonymous agent profile and preserves the current developer experience.
4. Agent preferences are merged in this fixed order:
   `system defaults -> agent profile -> token override -> request override`
5. Token plaintext is never persisted; only `token_hash` is stored.

---

### Task 1: Persist agent profiles, agent tokens, and task ownership

**Files:**
- Create: `src/video_agent/domain/agent_models.py`
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/adapters/storage/schema.sql`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Test: `tests/unit/domain/test_agent_models.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`

**Step 1: Write the failing tests**

Create `tests/unit/domain/test_agent_models.py` with focused model assertions:

```python
from video_agent.domain.agent_models import AgentProfile, AgentToken


def test_agent_profile_defaults_to_active() -> None:
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    assert profile.status == "active"
    assert profile.profile_json == {}


def test_agent_token_stores_hash_not_plaintext() -> None:
    token = AgentToken(token_hash="abc123", agent_id="agent-a")
    assert token.token_hash == "abc123"
    assert token.status == "active"
```

Extend `tests/unit/adapters/storage/test_sqlite_store.py` with storage behaviors like:

```python
def test_store_round_trips_agent_profile(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    profile = AgentProfile(
        agent_id="agent-a",
        name="Agent A",
        profile_json={"style_hints": {"tone": "teaching"}},
    )
    store.upsert_agent_profile(profile)

    loaded = store.get_agent_profile("agent-a")

    assert loaded is not None
    assert loaded.profile_json["style_hints"]["tone"] == "teaching"


def test_store_resolves_agent_token_by_hash(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    store.issue_agent_token(
        AgentToken(token_hash="hash-1", agent_id="agent-a", scopes_json={"mode": "default"})
    )

    loaded = store.get_agent_token("hash-1")

    assert loaded is not None
    assert loaded.agent_id == "agent-a"
```

Also add one ownership assertion for tasks:

```python
def test_store_persists_task_agent_id(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    task = VideoTask(prompt="draw a circle", agent_id="agent-a")
    store.create_task(task, idempotency_key="k1")

    loaded = store.get_task(task.task_id)

    assert loaded is not None
    assert loaded.agent_id == "agent-a"
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/domain/test_agent_models.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  -q
```

Expected:
- FAIL because `AgentProfile` / `AgentToken` do not exist
- FAIL because `SQLiteTaskStore` has no agent profile/token methods
- FAIL because `VideoTask` does not carry `agent_id`

**Step 3: Write minimal implementation**

Implement:

1. `src/video_agent/domain/agent_models.py`

```python
class AgentProfile(BaseModel):
    agent_id: str
    name: str
    status: str = "active"
    profile_json: dict[str, Any] = Field(default_factory=dict)
    policy_json: dict[str, Any] = Field(default_factory=dict)


class AgentToken(BaseModel):
    token_hash: str
    agent_id: str
    status: str = "active"
    scopes_json: dict[str, Any] = Field(default_factory=dict)
    override_json: dict[str, Any] = Field(default_factory=dict)
```

2. Extend `VideoTask` with:
   - `agent_id: str | None = None`
   - `effective_request_profile: dict[str, Any] = Field(default_factory=dict)`
   - `effective_profile_digest: str | None = None`

3. Add tables to `schema.sql`:
   - `agent_profiles`
   - `agent_tokens`
   - add `agent_id` column to `video_tasks`

4. Add `SQLiteTaskStore` methods:
   - `upsert_agent_profile(...)`
   - `get_agent_profile(...)`
   - `issue_agent_token(...)`
   - `get_agent_token(...)`

Keep this task narrow: persistence only, no auth flow yet.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/domain/agent_models.py \
  src/video_agent/domain/models.py \
  src/video_agent/adapters/storage/schema.sql \
  src/video_agent/adapters/storage/sqlite_store.py \
  tests/unit/domain/test_agent_models.py \
  tests/unit/adapters/storage/test_sqlite_store.py
git commit -m "feat: persist agent profiles and task ownership"
```

---

### Task 2: Add identity service and preference resolver

**Files:**
- Create: `src/video_agent/application/agent_identity_service.py`
- Create: `src/video_agent/application/preference_resolver.py`
- Modify: `src/video_agent/config.py`
- Test: `tests/unit/application/test_agent_identity_service.py`
- Test: `tests/unit/application/test_preference_resolver.py`
- Test: `tests/unit/test_settings.py`

**Step 1: Write the failing tests**

Create `tests/unit/application/test_agent_identity_service.py`:

```python
from video_agent.application.agent_identity_service import AgentIdentityService
from video_agent.domain.agent_models import AgentProfile, AgentToken


def test_identity_service_resolves_active_token_to_profile() -> None:
    service = AgentIdentityService(
        profile_lookup=lambda agent_id: AgentProfile(agent_id=agent_id, name="Agent A"),
        token_lookup=lambda token_hash: AgentToken(token_hash=token_hash, agent_id="agent-a"),
    )

    principal = service.authenticate("plain-token")

    assert principal.agent_id == "agent-a"
    assert principal.profile.name == "Agent A"
```

Create `tests/unit/application/test_preference_resolver.py`:

```python
from video_agent.application.preference_resolver import resolve_effective_request_config


def test_preference_resolver_uses_expected_precedence() -> None:
    effective = resolve_effective_request_config(
        system_defaults={"style_hints": {"tone": "clean"}},
        profile_json={"style_hints": {"tone": "teaching", "pace": "steady"}},
        token_override_json={"style_hints": {"pace": "brisk"}},
        request_overrides={"style_hints": {"tone": "dramatic"}},
    )

    assert effective["style_hints"] == {"tone": "dramatic", "pace": "brisk"}
```

Extend `tests/unit/test_settings.py` with:

```python
def test_settings_defaults_to_auth_disabled() -> None:
    settings = Settings()
    assert settings.auth_mode == "disabled"
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/application/test_agent_identity_service.py \
  tests/unit/application/test_preference_resolver.py \
  tests/unit/test_settings.py \
  -q
```

Expected:
- FAIL because the new service/resolver modules do not exist
- FAIL because `Settings` lacks `auth_mode`

**Step 3: Write minimal implementation**

Implement:

1. `Settings` additions:
   - `auth_mode: str = "disabled"`
   - `anonymous_agent_id: str = "local-anonymous"`

2. `AgentIdentityService.authenticate(plain_token: str) -> AgentPrincipal`
   - hash plaintext token
   - load token row
   - reject missing/disabled token
   - load owning profile
   - return `AgentPrincipal(agent_id, profile, token)`

3. `resolve_effective_request_config(...)`
   - deep-merge dictionaries in fixed order
   - compute a stable digest string for audit and task snapshots

Keep it pure and side-effect free. Do not wire it into MCP yet.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/agent_identity_service.py \
  src/video_agent/application/preference_resolver.py \
  src/video_agent/config.py \
  tests/unit/application/test_agent_identity_service.py \
  tests/unit/application/test_preference_resolver.py \
  tests/unit/test_settings.py
git commit -m "feat: add agent identity and preference resolution"
```

---

### Task 3: Add MCP session authentication and inject effective profiles into task creation

**Files:**
- Create: `src/video_agent/server/session_auth.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/revision_service.py`
- Test: `tests/integration/test_agent_auth_tools.py`
- Test: `tests/integration/test_mcp_tools.py`

**Step 1: Write the failing tests**

Create `tests/integration/test_agent_auth_tools.py` with flows like:

```python
def test_authenticate_agent_returns_profile_summary(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)

    payload = authenticate_agent_tool(app, {"agent_token": "agent-a-secret"})

    assert payload["agent_id"] == "agent-a"
    assert payload["authenticated"] is True


def test_create_video_task_uses_authenticated_agent_defaults(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)
    session_auth = SessionAuthRegistry()
    session_auth.authenticate("session-a", "agent-a", {"style_hints": {"tone": "teaching"}})

    payload = create_video_task_tool(
        app,
        {"prompt": "draw a circle"},
        agent_principal=session_auth.require("session-a"),
    )

    task = app.store.get_task(payload["task_id"])

    assert task is not None
    assert task.agent_id == "agent-a"
    assert task.style_hints["tone"] == "teaching"
```

Extend `tests/integration/test_mcp_tools.py` with one guardrail:

```python
def test_create_video_task_requires_authenticated_agent_in_required_mode(tmp_path: Path) -> None:
    app_context = create_app_context(_build_required_auth_settings(tmp_path))
    payload = create_video_task_tool(app_context, {"prompt": "draw a circle"})
    assert payload["error"]["code"] == "agent_not_authenticated"
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/integration/test_agent_auth_tools.py \
  tests/integration/test_mcp_tools.py \
  -q
```

Expected:
- FAIL because session auth support does not exist
- FAIL because there is no `authenticate_agent` tool
- FAIL because task creation does not enforce auth mode

**Step 3: Write minimal implementation**

Implement:

1. `SessionAuthRegistry`
   - map MCP session key -> `AgentPrincipal`
   - `authenticate(session_key, principal)`
   - `require(session_key)`

2. Add `authenticate_agent(agent_token)` tool in `fastmcp_server.py`

3. Update `create_video_task` / `revise_video_task` / `retry_video_task` call paths:
   - require authenticated agent when `auth_mode == "required"`
   - resolve effective config with `PreferenceResolver`
   - persist `agent_id`, merged profile, and digest into the created task

4. Preserve `agent_id` and effective profile during revision / retry / auto-repair child creation

Keep the session binding implementation simple:
- if `auth_mode == "disabled"`, use the anonymous local profile
- if `auth_mode == "required"`, reject unauthenticated task mutations

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/server/session_auth.py \
  src/video_agent/server/app.py \
  src/video_agent/server/fastmcp_server.py \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/application/task_service.py \
  src/video_agent/application/revision_service.py \
  tests/integration/test_agent_auth_tools.py \
  tests/integration/test_mcp_tools.py
git commit -m "feat: authenticate MCP sessions as named agents"
```

---

### Task 4: Enforce agent-scoped task and resource access

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/mcp_resources.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Test: `tests/integration/test_agent_resource_isolation.py`
- Test: `tests/integration/test_mcp_tools.py`

**Step 1: Write the failing tests**

Create `tests/integration/test_agent_resource_isolation.py`:

```python
def test_agent_cannot_read_another_agents_task_snapshot(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)
    task_id = _create_task_for_agent(app, agent_id="agent-a")

    with pytest.raises(PermissionError):
        app.task_service.get_video_task_for_agent(task_id, agent_id="agent-b")


def test_agent_cannot_read_another_agents_resource(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)
    task_id = _create_task_with_script_artifact_for_agent(app, agent_id="agent-a")

    with pytest.raises(PermissionError):
        read_resource_for_agent(app, f"video-task://{task_id}/artifacts/current_script.py", agent_id="agent-b")
```

Extend `tests/integration/test_mcp_tools.py` with:

```python
def test_list_video_tasks_only_returns_authenticated_agents_tasks(tmp_path: Path) -> None:
    ...
    assert [item["task_id"] for item in payload["items"]] == [agent_a_task_id]
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/integration/test_agent_resource_isolation.py \
  tests/integration/test_mcp_tools.py \
  -q
```

Expected:
- FAIL because task/resource reads are not agent-scoped
- FAIL because list operations still operate globally

**Step 3: Write minimal implementation**

Implement:

1. `TaskService` helpers:
   - `get_video_task_for_agent(task_id, agent_id)`
   - `get_video_result_for_agent(task_id, agent_id)`
   - `list_video_tasks_for_agent(agent_id, ...)`

2. `mcp_tools.py`:
   - use current authenticated principal for all reads/writes in required auth mode

3. `mcp_resources.py`:
   - validate task ownership before reading any resource under `video-task://...`

4. `fastmcp_server.py`:
   - resource functions should request `Context` where needed so they can resolve the authenticated session principal

Do not add complicated scopes yet. Ownership check is enough for Phase 1.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/task_service.py \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/server/mcp_resources.py \
  src/video_agent/server/fastmcp_server.py \
  tests/integration/test_agent_resource_isolation.py \
  tests/integration/test_mcp_tools.py
git commit -m "feat: scope tasks and resources to authenticated agents"
```

---

### Task 5: Add agent admin CLI and operator docs

**Files:**
- Create: `src/video_agent/agent_admin/main.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/runbooks/beta-ops.md`
- Test: `tests/integration/test_agent_admin_cli.py`

**Step 1: Write the failing tests**

Create `tests/integration/test_agent_admin_cli.py`:

```python
def test_agent_admin_cli_can_create_profile_and_issue_token(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    created = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.agent_admin.main",
            "--data-dir",
            str(data_dir),
            "create-profile",
            "--agent-id",
            "agent-a",
            "--name",
            "Agent A",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert created.returncode == 0

    issued = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.agent_admin.main",
            "--data-dir",
            str(data_dir),
            "issue-token",
            "--agent-id",
            "agent-a",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(issued.stdout)
    assert payload["agent_id"] == "agent-a"
    assert payload["agent_token"]
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest tests/integration/test_agent_admin_cli.py -q
```

Expected:
- FAIL because the CLI module and entrypoint do not exist

**Step 3: Write minimal implementation**

Implement a CLI with subcommands:

1. `create-profile`
2. `issue-token`
3. `disable-token`
4. `inspect-profile`

Output rules:

1. `issue-token` prints the plaintext token once as JSON
2. storage persists only its hash
3. docs explain that lost plaintext tokens must be re-issued, not recovered

Register an executable in `pyproject.toml`:

```toml
[project.scripts]
easy-manim-agent-admin = "video_agent.agent_admin.main:main"
```

Update docs to explain:

1. disabled vs required auth mode
2. how operators create a profile
3. how clients authenticate a session

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/agent_admin/main.py \
  pyproject.toml \
  README.md \
  docs/runbooks/beta-ops.md \
  tests/integration/test_agent_admin_cli.py
git commit -m "feat: add agent profile and token admin CLI"
```

---

### Task 6: Final verification for Phase 1

**Files:**
- Verify: `src/video_agent/domain/agent_models.py`
- Verify: `src/video_agent/application/agent_identity_service.py`
- Verify: `src/video_agent/application/preference_resolver.py`
- Verify: `src/video_agent/server/session_auth.py`
- Verify: `src/video_agent/server/fastmcp_server.py`
- Verify: `src/video_agent/server/mcp_resources.py`
- Verify: `tests/integration/test_agent_auth_tools.py`
- Verify: `tests/integration/test_agent_resource_isolation.py`
- Verify: `tests/integration/test_agent_admin_cli.py`

**Step 1: Run focused verification**

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/domain/test_agent_models.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/unit/application/test_agent_identity_service.py \
  tests/unit/application/test_preference_resolver.py \
  tests/integration/test_agent_auth_tools.py \
  tests/integration/test_agent_resource_isolation.py \
  tests/integration/test_mcp_tools.py \
  tests/integration/test_agent_admin_cli.py \
  -q
```

Expected: PASS

**Step 2: Run full verification**

```bash
source .venv/bin/activate && python -m pytest -q
```

Expected: PASS

**Step 3: Run deterministic release verification**

```bash
source .venv/bin/activate && python scripts/release_candidate_gate.py --mode ci
```

Expected:
- `ok: true`
- no regression in existing repair, quality, and live-provider gates

**Step 4: Run a narrow auth-mode smoke**

```bash
source .venv/bin/activate && \
easy-manim-agent-admin create-profile --data-dir /tmp/easy-manim-auth --agent-id agent-a --name "Agent A" && \
easy-manim-agent-admin issue-token --data-dir /tmp/easy-manim-auth --agent-id agent-a
```

Then:

1. start MCP in `auth_mode=required`
2. call `authenticate_agent(...)`
3. create a task
4. confirm the task snapshot contains `agent_id`

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add token-based multi-agent identity isolation"
```

