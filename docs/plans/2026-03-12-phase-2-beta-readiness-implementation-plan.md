# Phase 2 Beta Readiness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the current local-first v1 into a beta-ready system with a real LLM provider, a standalone worker process, basic operational MCP tools, and reproducible deployment assets.

**Architecture:** Keep the existing local-first shape: `FastMCP` remains the API surface, SQLite remains the task/lease store, and filesystem artifacts remain the source of truth for videos and reports. Add one provider abstraction for real code generation, split the worker into a separate process, and expose operational visibility through MCP tools/resources and structured task logs.

**Tech Stack:** Python 3.13, `FastMCP`, `pydantic`, SQLite, `httpx`, `pytest`, Docker, GitHub Actions.

---

## Phase 2 Scope

### Week 1 - Real LLM provider integration

**Goal:** Replace the hardcoded stub-only generation path with a configurable real provider while preserving deterministic local tests.

**Exit criteria:**
1. The app can switch between `stub` and `openai_compatible` provider modes via config.
2. Provider authentication, timeout, and upstream failure paths produce standardized issue codes.
3. Existing tests continue to pass in `stub` mode.

### Task 1: Expand configuration for provider and process modes

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/video_agent/config.py`
- Modify: `.env.example`
- Modify: `docs/runbooks/local-dev.md`
- Test: `tests/unit/test_settings.py`

**Step 1: Write the failing test**

```python
from video_agent.config import Settings


def test_settings_exposes_llm_and_worker_runtime_fields() -> None:
    settings = Settings()
    assert settings.llm_provider == "stub"
    assert settings.llm_model == "stub-manim-v1"
    assert settings.llm_timeout_seconds == 60
    assert settings.llm_max_retries == 2
    assert settings.run_embedded_worker is True
    assert settings.worker_poll_interval_seconds == 0.2
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_settings.py -q`
Expected: FAIL because the new settings fields do not exist yet.

**Step 3: Write minimal implementation**

Add the following to `src/video_agent/config.py`:

```python
class Settings(BaseModel):
    llm_provider: str = "stub"
    llm_model: str = "stub-manim-v1"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2
    run_embedded_worker: bool = True
    worker_poll_interval_seconds: float = 0.2
```

Update `.env.example` with:
- `EASY_MANIM_LLM_PROVIDER`
- `EASY_MANIM_LLM_MODEL`
- `EASY_MANIM_LLM_BASE_URL`
- `EASY_MANIM_LLM_API_KEY`
- `EASY_MANIM_RUN_EMBEDDED_WORKER`

Update `docs/runbooks/local-dev.md` to explain stub mode versus real provider mode.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_settings.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/video_agent/config.py .env.example docs/runbooks/local-dev.md tests/unit/test_settings.py
git commit -m "feat: add provider and worker runtime settings"
```

### Task 2: Add an OpenAI-compatible HTTP client adapter

**Files:**
- Modify: `pyproject.toml`
- Create: `src/video_agent/adapters/llm/openai_compatible_client.py`
- Modify: `src/video_agent/adapters/llm/__init__.py`
- Test: `tests/unit/adapters/llm/test_openai_compatible_client.py`

**Step 1: Write the failing tests**

```python
import httpx

from video_agent.adapters.llm.openai_compatible_client import OpenAICompatibleLLMClient


def test_openai_compatible_client_returns_first_message_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "from manim import Scene\nclass GeneratedScene(Scene):\n    pass\n"}}
                ]
            },
        )

    client = OpenAICompatibleLLMClient(
        base_url="https://example.test/v1",
        api_key="secret",
        model="gpt-4.1-mini",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert "GeneratedScene" in client.generate_script("draw a circle")


def test_openai_compatible_client_raises_normalized_error_on_401() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    client = OpenAICompatibleLLMClient(
        base_url="https://example.test/v1",
        api_key="secret",
        model="gpt-4.1-mini",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    with pytest.raises(ProviderAuthError):
        client.generate_script("draw a circle")
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/adapters/llm/test_openai_compatible_client.py -q`
Expected: FAIL because the adapter and normalized errors do not exist yet.

**Step 3: Write minimal implementation**

Add `httpx>=0.27,<1` to runtime dependencies in `pyproject.toml`.

Implement in `src/video_agent/adapters/llm/openai_compatible_client.py`:
- `OpenAICompatibleLLMClient`
- `ProviderAuthError`
- `ProviderRateLimitError`
- `ProviderTimeoutError`
- `ProviderResponseError`

Use a minimal request shape:

```python
payload = {
    "model": self.model,
    "messages": [
        {"role": "system", "content": "Return only runnable Manim Python code."},
        {"role": "user", "content": prompt_text},
    ],
    "temperature": 0,
}
```

POST to `f"{base_url}/chat/completions"`, extract `choices[0].message.content`, and raise normalized exceptions on 401, 429, timeout, or malformed JSON.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/adapters/llm/test_openai_compatible_client.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/video_agent/adapters/llm/__init__.py src/video_agent/adapters/llm/openai_compatible_client.py tests/unit/adapters/llm/test_openai_compatible_client.py
git commit -m "feat: add openai-compatible llm adapter"
```

### Task 3: Wire provider selection into app bootstrap and workflow errors

**Files:**
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Test: `tests/integration/test_generation_provider_failures.py`

**Step 1: Write the failing integration tests**

```python
from video_agent.config import Settings
from video_agent.server.app import create_app_context


def test_create_app_context_uses_stub_provider_by_default(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path / "data")
    app = create_app_context(settings)
    assert app.workflow_engine.llm_client.__class__.__name__ == "StubLLMClient"


def test_generation_auth_failure_becomes_standardized_validation_issue(tmp_path, monkeypatch) -> None:
    settings = Settings(data_dir=tmp_path / "data", llm_provider="openai_compatible")
    app = create_app_context(settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    snapshot = app.task_service.get_video_task(created.task_id)

    assert snapshot.status == "failed"
    assert snapshot.latest_validation_summary["issues"][0]["code"] == "provider_auth_error"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_generation_provider_failures.py -q`
Expected: FAIL because the bootstrap logic cannot choose providers and the workflow does not normalize provider exceptions.

**Step 3: Write minimal implementation**

In `src/video_agent/server/app.py`:
- Add `_build_llm_client(settings: Settings) -> LLMClient`
- Return `StubLLMClient()` when `llm_provider == "stub"`
- Return `OpenAICompatibleLLMClient(...)` when `llm_provider == "openai_compatible"`
- Raise `ValueError` for unsupported providers

In `src/video_agent/application/workflow_engine.py`:
- Catch normalized provider errors around `generate_script`
- Convert them into `ValidationReport` failures with issue codes:
  - `provider_auth_error`
  - `provider_rate_limited`
  - `provider_timeout`
  - `generation_failed`

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_generation_provider_failures.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/server/app.py src/video_agent/application/workflow_engine.py tests/integration/test_generation_provider_failures.py
git commit -m "feat: wire real llm provider selection and failure mapping"
```

---

## Week 2 - Standalone worker process and lease recovery

**Goal:** Split the worker out of the MCP server process so the system can be run and restarted more safely.

**Exit criteria:**
1. The server can run without an embedded worker.
2. A standalone worker process can drain queued tasks.
3. Stale leases are recoverable after worker interruption.

### Task 4: Add standalone worker CLI entrypoint

**Files:**
- Modify: `pyproject.toml`
- Create: `src/video_agent/worker/main.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `docs/runbooks/local-dev.md`
- Test: `tests/integration/test_worker_cli.py`

**Step 1: Write the failing tests**

```python
import subprocess


def test_worker_cli_help() -> None:
    completed = subprocess.run(
        ["python", "-m", "video_agent.worker.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--data-dir" in completed.stdout


def test_server_cli_can_disable_embedded_worker() -> None:
    completed = subprocess.run(
        ["python", "-m", "video_agent.server.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "--no-embedded-worker" in completed.stdout
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_worker_cli.py -q`
Expected: FAIL because the worker CLI and `--no-embedded-worker` flag do not exist.

**Step 3: Write minimal implementation**

In `pyproject.toml` add:

```toml
[project.scripts]
easy-manim-mcp = "video_agent.server.main:main"
easy-manim-worker = "video_agent.worker.main:main"
```

Implement `src/video_agent/worker/main.py` with:
- `--data-dir`
- `--poll-interval`
- `--once`
- loop that creates `AppContext` and calls `run_once()` repeatedly

In `src/video_agent/server/main.py` add:
- `--no-embedded-worker`
- forward that into `build_settings(...)` or app bootstrap flags

Update docs with separate commands:
- server only
- worker only
- local two-process mode

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_worker_cli.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/video_agent/worker/main.py src/video_agent/server/main.py docs/runbooks/local-dev.md tests/integration/test_worker_cli.py
git commit -m "feat: add standalone worker cli"
```

### Task 5: Make FastMCP embedded worker optional

**Files:**
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/app.py`
- Test: `tests/integration/test_fastmcp_server.py`

**Step 1: Write the failing integration test**

```python
from video_agent.config import Settings
from video_agent.server.fastmcp_server import create_mcp_server


async def test_fastmcp_server_can_skip_background_worker(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path / "data", run_embedded_worker=False)
    mcp = create_mcp_server(settings)
    assert mcp is not None
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_fastmcp_server.py -q`
Expected: FAIL because the lifespan always starts a background worker.

**Step 3: Write minimal implementation**

In `src/video_agent/server/app.py` and `src/video_agent/server/fastmcp_server.py`:
- honor `settings.run_embedded_worker`
- only install `_run_background_worker` in lifespan when enabled
- keep default behavior unchanged for current tests

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_fastmcp_server.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/server/fastmcp_server.py src/video_agent/server/app.py tests/integration/test_fastmcp_server.py
git commit -m "feat: make embedded worker optional"
```

### Task 6: Add lease renewal and stale-task recovery

**Files:**
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/worker/worker_loop.py`
- Modify: `src/video_agent/config.py`
- Test: `tests/integration/test_worker_recovery.py`

**Step 1: Write the failing integration tests**

```python
from video_agent.server.app import create_app_context


def test_worker_renews_lease_for_long_running_task(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    claimed = app.store.claim_next_task(worker_id="worker-a", lease_seconds=1)
    app.store.renew_lease(claimed.task_id, worker_id="worker-a", lease_seconds=30)

    leased = app.store.claim_next_task(worker_id="worker-b", lease_seconds=1)
    assert leased is None


def test_stale_running_task_can_be_recovered(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="draw a circle")

    claimed = app.store.claim_next_task(worker_id="worker-a", lease_seconds=0)
    app.store.requeue_stale_tasks()
    recovered = app.store.claim_next_task(worker_id="worker-b", lease_seconds=30)

    assert recovered.task_id == created.task_id
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_worker_recovery.py -q`
Expected: FAIL because lease renewal and stale-task recovery methods do not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/adapters/storage/sqlite_store.py` add:
- `renew_lease(task_id, worker_id, lease_seconds)`
- `requeue_stale_tasks()` that converts stale `running` tasks back to `queued` when no valid lease remains

In `src/video_agent/worker/worker_loop.py`:
- renew lease before and/or after long stages if needed
- call `requeue_stale_tasks()` at loop start

In `src/video_agent/config.py` add:
- `worker_lease_seconds: int = 30`
- `worker_recovery_grace_seconds: int = 5`

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_worker_recovery.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/adapters/storage/sqlite_store.py src/video_agent/worker/worker_loop.py src/video_agent/config.py tests/integration/test_worker_recovery.py
git commit -m "feat: add worker lease renewal and recovery"
```

---

## Week 3 - Operations visibility and task introspection

**Goal:** Add enough operational surface area to inspect tasks, events, and failures without opening SQLite manually.

**Exit criteria:**
1. MCP can list tasks and fetch event history.
2. Structured logs are persisted to disk, not only stored in SQLite events.
3. Metrics can be read as a snapshot for debugging.

### Task 7: Add task list and event query services

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Test: `tests/integration/test_task_ops_service.py`

**Step 1: Write the failing integration tests**

```python
from video_agent.server.app import create_app_context


def test_list_video_tasks_returns_recent_tasks(temp_settings) -> None:
    app = create_app_context(temp_settings)
    app.task_service.create_video_task(prompt="one", idempotency_key="one")
    app.task_service.create_video_task(prompt="two", idempotency_key="two")

    tasks = app.task_service.list_video_tasks(limit=10)
    assert len(tasks) >= 2


def test_get_task_events_returns_event_history(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="one", idempotency_key="events")

    events = app.task_service.get_task_events(created.task_id)
    assert events[0]["event_type"] == "task_created"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_task_ops_service.py -q`
Expected: FAIL because list/event service methods do not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/adapters/storage/sqlite_store.py` add:
- `list_tasks(limit: int = 50, status: str | None = None)`
- `list_events(task_id: str, limit: int = 200)`

In `src/video_agent/application/task_service.py` add:
- `list_video_tasks(...)`
- `get_task_events(task_id)`

Return JSON-friendly dicts with `task_id`, `status`, `phase`, `created_at`, `updated_at`, and event payloads.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_task_ops_service.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/task_service.py src/video_agent/adapters/storage/sqlite_store.py tests/integration/test_task_ops_service.py
git commit -m "feat: add task list and event query services"
```

### Task 8: Expose operations through MCP tools

**Files:**
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Test: `tests/integration/test_mcp_ops_tools.py`

**Step 1: Write the failing integration tests**

```python
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_task_events_tool, list_video_tasks_tool


def test_list_video_tasks_tool_returns_created_tasks(temp_settings) -> None:
    app = create_app_context(temp_settings)
    app.task_service.create_video_task(prompt="one", idempotency_key="one")

    payload = list_video_tasks_tool(app, {"limit": 10})
    assert payload["items"]


def test_get_task_events_tool_returns_event_items(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="one", idempotency_key="events")

    payload = get_task_events_tool(app, {"task_id": created.task_id})
    assert payload["items"][0]["event_type"] == "task_created"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_mcp_ops_tools.py -q`
Expected: FAIL because the MCP operations tools do not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/server/mcp_tools.py` add:
- `list_video_tasks_tool`
- `get_task_events_tool`
- optionally `get_metrics_snapshot_tool`

In `src/video_agent/server/fastmcp_server.py` register:
- `list_video_tasks`
- `get_task_events`
- optional `get_metrics_snapshot`

Keep response shapes small and stable:

```python
{"items": [...], "next_cursor": None}
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_mcp_ops_tools.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/server/mcp_tools.py src/video_agent/server/fastmcp_server.py tests/integration/test_mcp_ops_tools.py
git commit -m "feat: expose task ops via mcp tools"
```

### Task 9: Persist JSONL task logs and expose metrics snapshots

**Files:**
- Modify: `src/video_agent/observability/logging.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/server/mcp_resources.py`
- Test: `tests/integration/test_observability_artifacts.py`

**Step 1: Write the failing integration tests**

```python
from video_agent.server.app import create_app_context


def test_task_log_events_are_written_to_jsonl(tmp_path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    log_path = app.artifact_store.task_dir(created.task_id) / "logs" / "events.jsonl"
    assert log_path.exists()
    assert '"phase": "rendering"' in log_path.read_text()


def test_metrics_snapshot_resource_is_available(tmp_path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    payload = app.metrics.counters
    assert payload["render_runs"] == 1
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_observability_artifacts.py -q`
Expected: FAIL because task logs are not written to JSONL files yet.

**Step 3: Write minimal implementation**

In `src/video_agent/adapters/storage/artifact_store.py` add:
- `task_log_path(task_id: str) -> Path`
- `append_task_log(task_id: str, event: dict[str, Any]) -> Path`

In `src/video_agent/observability/logging.py` add:
- newline-delimited JSON serializer helper if needed

In `src/video_agent/application/workflow_engine.py`:
- call `artifact_store.append_task_log(...)` inside `_log(...)`

In `src/video_agent/server/mcp_resources.py` optionally expose:
- `video-task://{task_id}/logs/events.jsonl`

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_observability_artifacts.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/observability/logging.py src/video_agent/adapters/storage/artifact_store.py src/video_agent/application/workflow_engine.py src/video_agent/server/mcp_resources.py tests/integration/test_observability_artifacts.py
git commit -m "feat: persist structured task logs"
```

---

## Week 4 - Retry semantics, deployment assets, and beta handoff

**Goal:** Finish the minimum operational and release surface needed for beta users.

**Exit criteria:**
1. Failed tasks can be retried with an explicit tool.
2. Docker and CI can run the project in a reproducible way.
3. There is one HTTP transport end-to-end smoke test and a beta runbook.

### Task 10: Add retry flow for failed tasks

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/revision_service.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Test: `tests/integration/test_retry_video_task.py`

**Step 1: Write the failing integration tests**

```python
from video_agent.server.app import create_app_context


def test_retry_video_task_creates_new_child_from_failed_parent(tmp_path) -> None:
    app = create_app_context(_build_failing_generation_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")
    app.worker.run_once()

    retried = app.task_service.retry_video_task(created.task_id)
    snapshot = app.task_service.get_video_task(retried.task_id)

    assert snapshot.parent_task_id == created.task_id
    assert snapshot.status == "queued"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_retry_video_task.py -q`
Expected: FAIL because retry flow does not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/application/task_service.py` add:
- `retry_video_task(task_id: str) -> CreateVideoTaskResult`

Implementation approach:
- require parent task status in `failed`
- create a child task via `RevisionService` with inherited prompt
- append `retry_created` event

In MCP:
- add `retry_video_task` tool

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_retry_video_task.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/task_service.py src/video_agent/application/revision_service.py src/video_agent/server/mcp_tools.py src/video_agent/server/fastmcp_server.py tests/integration/test_retry_video_task.py
git commit -m "feat: add retry flow for failed tasks"
```

### Task 11: Add deployment assets and CI

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `docker-compose.yml`
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`
- Test: `tests/integration/test_cli_entrypoints.py`

**Step 1: Write the failing tests**

```python
import subprocess


def test_mcp_entrypoint_help() -> None:
    completed = subprocess.run(["easy-manim-mcp", "--help"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0


def test_worker_entrypoint_help() -> None:
    completed = subprocess.run(["easy-manim-worker", "--help"], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_cli_entrypoints.py -q`
Expected: FAIL until the worker entrypoint is installed.

**Step 3: Write minimal implementation**

Create `Dockerfile` that:
- installs system deps for `ffmpeg`
- installs Python package with `.[dev]`
- exposes the MCP server command

Create `docker-compose.yml` with:
- one `server` service
- one `worker` service
- shared bind-mounted `data/`

Create CI workflow that runs:
- `python -m pip install -e '.[dev]'`
- `python -m pytest -q`

Update `README.md` with local and container workflows.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_cli_entrypoints.py -q`
Expected: PASS

Then verify deployment assets manually:
- `docker build -t easy-manim-beta .`
- `docker compose up --build`

**Step 5: Commit**

```bash
git add Dockerfile .dockerignore docker-compose.yml .github/workflows/ci.yml README.md tests/integration/test_cli_entrypoints.py
git commit -m "chore: add deployment assets and ci"
```

### Task 12: Add a real HTTP MCP smoke test and beta runbook

**Files:**
- Create: `tests/e2e/test_streamable_http_single_task_flow.py`
- Create: `docs/runbooks/beta-ops.md`
- Modify: `docs/runbooks/release-checklist.md`
- Modify: `docs/runbooks/local-dev.md`

**Step 1: Write the failing e2e test**

```python
async def test_streamable_http_single_task_flow(tmp_path) -> None:
    settings = _build_real_server_settings(tmp_path)
    server = _start_server_subprocess(settings)
    try:
        task_id = await _create_task_over_http("draw a blue circle")
        snapshot = await _poll_task(task_id)
        assert snapshot["status"] == "completed"
        result = await _get_result(task_id)
        assert result["ready"] is True
    finally:
        _stop_server_subprocess(server)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/e2e/test_streamable_http_single_task_flow.py -q`
Expected: FAIL until the helpers and subprocess orchestration are added.

**Step 3: Write minimal implementation and docs**

Implement the e2e test using the official `mcp` Python client and a subprocess-launched server. Document in `docs/runbooks/beta-ops.md`:
- required env vars
- how to run server-only mode
- how to run worker-only mode
- how to create a task and inspect artifacts
- common failure signatures and what to check first

Update `docs/runbooks/release-checklist.md` to include:
- separate worker verification
- real provider smoke verification
- HTTP transport smoke verification

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/e2e/test_streamable_http_single_task_flow.py -q`
Expected: PASS

Then run full verification:
- `python -m pytest -q`

**Step 5: Commit**

```bash
git add tests/e2e/test_streamable_http_single_task_flow.py docs/runbooks/beta-ops.md docs/runbooks/release-checklist.md docs/runbooks/local-dev.md
git commit -m "docs: add beta runbook and http e2e smoke test"
```

---

## Final Verification Checklist

After all tasks are complete, run these commands fresh:

```bash
source .venv/bin/activate
python -m pytest -q
python -m video_agent.server.main --transport stdio --no-embedded-worker
python -m video_agent.worker.main --once
python -m video_agent.server.main --transport streamable-http --host 127.0.0.1 --port 8000 --no-embedded-worker
```

Then manually verify:
1. `create_video_task` returns a `task_id`
2. standalone worker moves the task to a terminal state
3. `list_video_tasks` and `get_task_events` return useful data
4. failed tasks can be retried
5. `logs/events.jsonl` exists for processed tasks
6. `validations/validation_report_v1.json` exists for terminal tasks
7. the HTTP e2e smoke test passes

## Notes for the Implementer

- Keep `stub` mode as the default so local tests stay deterministic.
- Do not replace SQLite or filesystem artifacts in Phase 2.
- Do not introduce distributed queues yet; that belongs to a later phase.
- Prefer normalized issue codes over raw provider exception strings.
- Reuse the current `TaskService` / `WorkflowEngine` / `FastMCP` boundaries instead of inventing a new architecture.
