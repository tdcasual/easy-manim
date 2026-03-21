# Agent Self-Serve API and Agent Improvement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a non-UI, agent-self-serve `easy-manim` service where agents log in once, use a plain HTTP JSON API, remain isolated by stable `agent_id`, and can improve independently over time through auditable per-agent memory, profile suggestions, and evaluation loops.

**Architecture:** Keep the current `FastMCP + SQLite + local filesystem artifacts` execution core intact. Add a sibling FastAPI-based HTTP API with a persisted opaque session layer, reuse the existing task/memory services behind shared app wiring, and model long-term agent improvement around stable `agent_id` rather than raw token identity. Build learning in three layers: per-agent telemetry, explicit profile suggestions, and an optional guarded auto-apply loop.

**Tech Stack:** Python 3.14, FastAPI, uvicorn, Pydantic, FastMCP, SQLite, pytest, local filesystem artifacts, existing task/revision/session-memory/persistent-memory services, and `@superpowers:test-driven-development`, `@superpowers:verification-before-completion`, `@superpowers:requesting-code-review`.

---

## Recommended Scope

This plan deliberately separates the work into three delivery bands.

**Band 1: Must ship**
1. Plain HTTP API runtime
2. Persisted login sessions
3. Session-authenticated task and memory endpoints
4. Scope and policy enforcement
5. End-to-end docs and operator runbooks

**Band 2: Strongly recommended next**
1. Per-agent telemetry and scorecards
2. Explicit profile suggestion generation
3. Profile read/apply API

**Band 3: Fast follow**
1. Guarded auto-apply learning
2. Agent-aware eval and regression gates
3. Session durability and deployment hardening

## Product Assumptions

1. Long-lived identity is `agent_id`, not `token_hash`.
2. Each agent normally holds one login token, but the model must tolerate token rotation later.
3. The public agent-facing surface is a JSON HTTP API, not a human UI.
4. Agents should log in once, receive an opaque session credential, and reuse it across requests.
5. The API must never expose internal `session_id` directly.
6. `session memory` remains session-scoped, `persistent memory` remains agent-scoped, and profile evolution is layered on top.
7. The first production target is single-instance deployment; shared-session multi-instance deployment is a later hardening step.

## Recommended Approach

**Recommended: sibling HTTP API + persisted opaque sessions + explicit learning pipeline**
- Keep MCP intact for MCP-native clients.
- Add a separate HTTP API for agent clients that prefer ordinary request/response calls.
- Persist agent sessions in SQLite so login-once survives independent HTTP requests.
- Route all per-agent improvement through `agent_id`, not token identity.
- Start with explicit profile suggestion/apply, then add guarded auto-apply only after scorecards and regression checks exist.

**Why this is the right approach**
- Fastest path to a usable self-serve API without rewriting the workflow engine.
- Reuses existing task ownership, session memory, and persistent memory primitives.
- Preserves auditability for later “independent improvement” work.
- Avoids the common mistake of coupling long-term learning to a revocable token.

**Alternative A: only expose MCP over streamable HTTP**
- Cheapest short-term engineering path.
- Still leaves non-MCP clients without a clean login/session model.
- Does not solve plain HTTP API ergonomics or future OpenAPI/discoverability.

**Alternative B: per-request bearer token only**
- Simpler backend than persisted sessions.
- Worse ergonomics for agent callers that naturally keep a working session.
- Makes “login once, then use the service” less explicit and complicates future session-scoped memory tooling.

## Parallelization Notes

Use multiple subagents, but keep write scopes disjoint.

**Track A: HTTP platform**
- Task 1
- Task 2
- Task 3
- Task 4
- Task 5
- Task 6

**Track B: auth/policy hardening**
- Task 7
- Task 8

**Track C: agent improvement**
- Task 9
- Task 10
- Task 11
- Task 12

**Track D: eval/docs/ops**
- Task 13
- Task 14

Run Tracks A and D in parallel after Task 2. Start Track C after Task 6 lands and Track B schema changes stabilize.

### Task 1: Add the HTTP API runtime scaffold

**Files:**
- Modify: `pyproject.toml`
- Create: `src/video_agent/server/http_api.py`
- Create: `src/video_agent/server/api_main.py`
- Test: `tests/integration/test_http_api.py`

**Step 1: Write the failing test**

Create `tests/integration/test_http_api.py` with a minimal FastAPI smoke check:

```python
from fastapi.testclient import TestClient

from video_agent.config import Settings
from video_agent.server.http_api import create_http_api


def test_http_api_exposes_health_and_openapi(tmp_path) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "video_agent.db",
        artifact_root=tmp_path / "data" / "tasks",
        run_embedded_worker=False,
    )
    app = create_http_api(settings)
    client = TestClient(app)

    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert openapi.json()["info"]["title"] == "easy-manim API"
```

**Step 2: Run the test to verify it fails**

Run:

```bash
source .venv/bin/activate && \
python -m pytest tests/integration/test_http_api.py -q
```

Expected: FAIL because `http_api.py` and `api_main.py` do not exist yet and runtime deps are missing.

**Step 3: Write minimal implementation**

Update `pyproject.toml` runtime dependencies:

```toml
dependencies = [
  "pydantic>=2,<3",
  "mcp[cli]>=1,<2",
  "httpx>=0.27,<1",
  "Pillow>=10,<12",
  "fastapi>=0.116,<1",
  "uvicorn>=0.35,<1",
]
```

Create `src/video_agent/server/http_api.py`:

```python
from fastapi import FastAPI

from video_agent.config import Settings
from video_agent.server.app import create_app_context


def create_http_api(settings: Settings) -> FastAPI:
    context = create_app_context(settings)
    app = FastAPI(title="easy-manim API", version="0.1.0")
    app.state.app_context = context

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready"}

    return app
```

Create `src/video_agent/server/api_main.py`:

```python
from __future__ import annotations

import uvicorn

from video_agent.server.main import build_parser, build_settings
from video_agent.server.http_api import create_http_api


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = build_settings(args.data_dir, run_embedded_worker=not args.no_embedded_worker)
    app = create_http_api(settings)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
```

Add a new script entrypoint:

```toml
[project.scripts]
easy-manim-api = "video_agent.server.api_main:main"
```

**Step 4: Run the test to verify it passes**

Run:

```bash
source .venv/bin/activate && \
python -m pip install -e '.[dev]' && \
python -m pytest tests/integration/test_http_api.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/video_agent/server/http_api.py src/video_agent/server/api_main.py tests/integration/test_http_api.py
git commit -m "feat: add http api runtime scaffold"
```

### Task 2: Persist opaque agent login sessions

**Files:**
- Create: `src/video_agent/domain/agent_session_models.py`
- Create: `src/video_agent/application/agent_session_service.py`
- Modify: `src/video_agent/adapters/storage/schema.sql`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/server/app.py`
- Test: `tests/unit/domain/test_agent_session_models.py`
- Test: `tests/unit/application/test_agent_session_service.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`

**Step 1: Write the failing tests**

Create `tests/unit/domain/test_agent_session_models.py`:

```python
from video_agent.domain.agent_session_models import AgentSession


def test_agent_session_defaults_to_active() -> None:
    session = AgentSession(session_id="sess-1", session_hash="hash-1", agent_id="agent-a")
    assert session.status == "active"
    assert session.expires_at is not None
```

Create `tests/unit/application/test_agent_session_service.py`:

```python
from video_agent.application.agent_session_service import AgentSessionService
from video_agent.domain.agent_models import AgentProfile, AgentToken


def test_create_session_returns_plaintext_secret_and_persisted_record() -> None:
    created_records = []

    service = AgentSessionService(
        authenticate_agent=lambda token: (
            "agent-a",
            AgentProfile(agent_id="agent-a", name="Agent A"),
            AgentToken(token_hash="token-hash", agent_id="agent-a"),
        ),
        create_session_record=lambda record: created_records.append(record) or record,
    )

    payload = service.create_session("plain-agent-token")

    assert payload.session_token.startswith("esm_sess.")
    assert created_records[0].agent_id == "agent-a"
```

Extend `tests/unit/adapters/storage/test_sqlite_store.py`:

```python
def test_store_round_trips_agent_session(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    session = AgentSession(
        session_id="sess-1",
        session_hash="hash-1",
        agent_id="agent-a",
    )

    store.create_agent_session(session)
    loaded = store.get_agent_session("hash-1")

    assert loaded is not None
    assert loaded.agent_id == "agent-a"
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/domain/test_agent_session_models.py \
  tests/unit/application/test_agent_session_service.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  -q
```

Expected: FAIL because the session models/service/storage methods do not exist yet.

**Step 3: Write minimal implementation**

Create `src/video_agent/domain/agent_session_models.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentSession(BaseModel):
    session_id: str
    session_hash: str
    agent_id: str
    status: str = "active"
    created_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime = Field(default_factory=lambda: _utcnow() + timedelta(days=7))
    last_seen_at: datetime = Field(default_factory=_utcnow)
    revoked_at: datetime | None = None
```

Create `src/video_agent/application/agent_session_service.py`:

```python
from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from video_agent.application.agent_identity_service import AgentIdentityService
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.agent_session_models import AgentSession


@dataclass
class CreatedAgentSession:
    session_token: str
    session: AgentSession
    profile: AgentProfile
    token: AgentToken


class AgentSessionService:
    def __init__(
        self,
        *,
        authenticate_agent: Callable[[str], tuple[str, AgentProfile, AgentToken]] | None = None,
        create_session_record: Callable[[AgentSession], AgentSession] | None = None,
        lookup_session_record: Callable[[str], AgentSession | None] | None = None,
        revoke_session_record: Callable[[str], bool] | None = None,
        touch_session_record: Callable[[str], AgentSession | None] | None = None,
    ) -> None:
        self.authenticate_agent = authenticate_agent or self._unsupported_auth
        self.create_session_record = create_session_record or (lambda record: record)
        self.lookup_session_record = lookup_session_record or (lambda session_hash: None)
        self.revoke_session_record = revoke_session_record or (lambda session_hash: False)
        self.touch_session_record = touch_session_record or (lambda session_hash: None)

    def create_session(self, plain_agent_token: str) -> CreatedAgentSession:
        agent_id, profile, token = self.authenticate_agent(plain_agent_token)
        plain_session_token = f"esm_sess.{uuid4().hex}.{secrets.token_urlsafe(24)}"
        session = AgentSession(
            session_id=f"sess-{uuid4().hex}",
            session_hash=self.hash_session_token(plain_session_token),
            agent_id=agent_id,
        )
        persisted = self.create_session_record(session)
        return CreatedAgentSession(session_token=plain_session_token, session=persisted, profile=profile, token=token)

    @staticmethod
    def hash_session_token(plain_session_token: str) -> str:
        return hashlib.sha256(plain_session_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _unsupported_auth(_: str):
        raise RuntimeError("authenticate_agent callback is required")
```

Add a new SQLite table:

```sql
CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id TEXT PRIMARY KEY,
    session_hash TEXT NOT NULL UNIQUE,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    revoked_at TEXT
);
```

Add storage methods:
- `create_agent_session(...)`
- `get_agent_session(session_hash)`
- `touch_agent_session(session_hash)`
- `revoke_agent_session(session_hash)`

Wire `AgentSessionService` in `src/video_agent/server/app.py`.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/domain/agent_session_models.py \
  src/video_agent/application/agent_session_service.py \
  src/video_agent/adapters/storage/schema.sql \
  src/video_agent/adapters/storage/sqlite_store.py \
  src/video_agent/server/app.py \
  tests/unit/domain/test_agent_session_models.py \
  tests/unit/application/test_agent_session_service.py \
  tests/unit/adapters/storage/test_sqlite_store.py
git commit -m "feat: persist opaque agent sessions"
```

### Task 3: Add login, whoami, and logout HTTP endpoints

**Files:**
- Modify: `src/video_agent/server/http_api.py`
- Create: `src/video_agent/server/http_auth.py`
- Test: `tests/integration/test_http_auth_api.py`

**Step 1: Write the failing test**

Create `tests/integration/test_http_auth_api.py`:

```python
from fastapi.testclient import TestClient

from video_agent.domain.agent_models import AgentProfile
from video_agent.server.http_api import create_http_api


def test_login_whoami_logout_roundtrip(tmp_path) -> None:
    from video_agent.config import Settings

    settings = Settings(
        data_dir=tmp_path / "data",
        database_path=tmp_path / "data" / "video_agent.db",
        artifact_root=tmp_path / "data" / "tasks",
        run_embedded_worker=False,
        auth_mode="required",
    )
    app = create_http_api(settings)
    ctx = app.state.app_context
    ctx.store.upsert_agent_profile(AgentProfile(agent_id="agent-a", name="Agent A"))
    token_payload = __import__("json").loads(
        __import__("subprocess").check_output(
            [
                ".venv/bin/easy-manim-agent-admin",
                "--data-dir",
                str(tmp_path / "data"),
                "issue-token",
                "--agent-id",
                "agent-a",
            ],
            text=True,
        )
    )

    client = TestClient(app)
    login = client.post("/api/sessions", json={"agent_token": token_payload["agent_token"]})
    assert login.status_code == 200
    session_token = login.json()["session_token"]

    whoami = client.get("/api/whoami", headers={"Authorization": f"Bearer {session_token}"})
    assert whoami.status_code == 200
    assert whoami.json()["agent_id"] == "agent-a"

    logout = client.delete("/api/sessions/current", headers={"Authorization": f"Bearer {session_token}"})
    assert logout.status_code == 200
```

**Step 2: Run the test to verify it fails**

Run:

```bash
source .venv/bin/activate && \
python -m pytest tests/integration/test_http_auth_api.py -q
```

Expected: FAIL because the endpoints and auth dependency do not exist.

**Step 3: Write minimal implementation**

Create `src/video_agent/server/http_auth.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, Request, status

from video_agent.application.agent_identity_service import AgentPrincipal


@dataclass
class ResolvedAgentSession:
    session_token: str
    session_id: str
    agent_principal: AgentPrincipal


def _extract_bearer(authorization: str | None) -> str:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_session_token")
    return authorization.removeprefix("Bearer ").strip()


def resolve_agent_session(request: Request, authorization: str | None = Header(default=None)) -> ResolvedAgentSession:
    context = request.app.state.app_context
    plain_session_token = _extract_bearer(authorization)
    resolved = context.agent_session_service.resolve_session(plain_session_token)
    return ResolvedAgentSession(
        session_token=plain_session_token,
        session_id=resolved.session.session_id,
        agent_principal=resolved.principal,
    )
```

Extend `AgentSessionService` with:
- `resolve_session(plain_session_token)`
- `revoke_session(plain_session_token)`

Add endpoints in `http_api.py`:

```python
@app.post("/api/sessions")
def create_session(payload: SessionLoginRequest) -> dict[str, object]:
    created = context.agent_session_service.create_session(payload.agent_token)
    return {
        "session_token": created.session_token,
        "session_id": created.session.session_id,
        "agent_id": created.profile.agent_id,
        "name": created.profile.name,
        "expires_at": created.session.expires_at.isoformat(),
    }

@app.get("/api/whoami")
def whoami(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
    return {
        "agent_id": resolved.agent_principal.agent_id,
        "name": resolved.agent_principal.profile.name,
        "profile": resolved.agent_principal.profile.profile_json,
        "session_id": resolved.session_id,
    }

@app.delete("/api/sessions/current")
def delete_session(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
    context.agent_session_service.revoke_session(resolved.session_token)
    return {"revoked": True}
```

Note: in the final implementation, do **not** keep `session_id` in the public response; it is acceptable only in this initial failing-to-passing slice if tests need temporary visibility. Remove it in Task 4.

**Step 4: Run the test to verify it passes**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/server/http_api.py src/video_agent/server/http_auth.py src/video_agent/application/agent_session_service.py tests/integration/test_http_auth_api.py
git commit -m "feat: add session login api"
```

### Task 4: Remove public `session_id` leakage and build request-safe session context

**Files:**
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/server/http_auth.py`
- Modify: `src/video_agent/application/agent_session_service.py`
- Test: `tests/integration/test_http_auth_api.py`
- Test: `tests/integration/test_http_memory_api.py`

**Step 1: Write the failing test**

Add assertions that public auth responses never expose internal `session_id`:

```python
def test_login_and_whoami_do_not_expose_internal_session_id(client, issued_token) -> None:
    login = client.post("/api/sessions", json={"agent_token": issued_token})
    assert "session_id" not in login.json()

    token = login.json()["session_token"]
    whoami = client.get("/api/whoami", headers={"Authorization": f"Bearer {token}"})
    assert "session_id" not in whoami.json()
```

Add a regression test proving memory endpoints cannot accept caller-supplied `session_id`:

```python
def test_session_memory_endpoint_ignores_external_session_id_query(client, login_token) -> None:
    response = client.get(
        "/api/memory/session",
        params={"session_id": "forged-session"},
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert response.status_code == 200
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/integration/test_http_auth_api.py \
  tests/integration/test_http_memory_api.py \
  -q
```

Expected: FAIL because `session_id` is still public or the memory path still trusts external input.

**Step 3: Write minimal implementation**

Refine `ResolvedAgentSession` to carry internal `session_id` only in server code.

Remove `session_id` from all public response bodies:

```python
return {
    "session_token": created.session_token,
    "agent_id": created.profile.agent_id,
    "name": created.profile.name,
    "expires_at": created.session.expires_at.isoformat(),
}
```

Add one internal helper to create/lookup request-bound session context:

```python
def current_internal_session_id(resolved: ResolvedAgentSession) -> str:
    return resolved.session_id
```

Ensure all future HTTP task and memory handlers derive internal `session_id` exclusively from `ResolvedAgentSession`, never from request payloads or query params.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/server/http_api.py src/video_agent/server/http_auth.py src/video_agent/application/agent_session_service.py tests/integration/test_http_auth_api.py tests/integration/test_http_memory_api.py
git commit -m "fix: keep internal session ids server-only"
```

### Task 5: Add session-authenticated HTTP task endpoints

**Files:**
- Modify: `src/video_agent/server/http_api.py`
- Create: `tests/integration/test_http_task_api.py`

**Step 1: Write the failing test**

Create `tests/integration/test_http_task_api.py`:

```python
def test_task_create_list_get_result_roundtrip(http_client, login_token) -> None:
    created = http_client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    listed = http_client.get("/api/tasks", headers={"Authorization": f"Bearer {login_token}"})
    assert listed.status_code == 200
    assert any(item["task_id"] == task_id for item in listed.json()["items"])

    snapshot = http_client.get(f"/api/tasks/{task_id}", headers={"Authorization": f"Bearer {login_token}"})
    assert snapshot.status_code == 200
    assert snapshot.json()["task_id"] == task_id

    result = http_client.get(f"/api/tasks/{task_id}/result", headers={"Authorization": f"Bearer {login_token}"})
    assert result.status_code == 200
    assert result.json()["task_id"] == task_id
```

Add mutation coverage:

```python
def test_task_revise_retry_cancel_endpoints_are_agent_scoped(http_client, login_token) -> None:
    ...
```

**Step 2: Run the test to verify it fails**

Run:

```bash
source .venv/bin/activate && \
python -m pytest tests/integration/test_http_task_api.py -q
```

Expected: FAIL because the endpoints do not exist yet.

**Step 3: Write minimal implementation**

Add HTTP handlers that call the existing `TaskService`:

```python
@app.post("/api/tasks")
def create_task(
    payload: CreateTaskRequest,
    resolved: ResolvedAgentSession = Depends(resolve_agent_session),
) -> dict[str, object]:
    result = context.task_service.create_video_task(
        prompt=payload.prompt,
        idempotency_key=payload.idempotency_key,
        output_profile=payload.output_profile,
        style_hints=payload.style_hints,
        validation_profile=payload.validation_profile,
        memory_ids=payload.memory_ids,
        session_id=resolved.session_id,
        agent_principal=resolved.agent_principal,
    )
    return result.model_dump(mode="json")
```

Add endpoints:
- `GET /api/tasks`
- `GET /api/tasks/{task_id}`
- `GET /api/tasks/{task_id}/result`
- `POST /api/tasks/{task_id}/revise`
- `POST /api/tasks/{task_id}/retry`
- `POST /api/tasks/{task_id}/cancel`

Return the same structured payload shapes the MCP tools already return where practical.

**Step 4: Run the test to verify it passes**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/server/http_api.py tests/integration/test_http_task_api.py
git commit -m "feat: add session-authenticated task api"
```

### Task 6: Add secure HTTP memory endpoints

**Files:**
- Modify: `src/video_agent/server/http_api.py`
- Test: `tests/integration/test_http_memory_api.py`

**Step 1: Write the failing test**

Create `tests/integration/test_http_memory_api.py`:

```python
def test_session_memory_endpoints_are_bound_to_authenticated_session(http_client, login_token) -> None:
    create = http_client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert create.status_code == 200

    memory = http_client.get("/api/memory/session", headers={"Authorization": f"Bearer {login_token}"})
    assert memory.status_code == 200
    assert memory.json()["entry_count"] == 1

    summary = http_client.get("/api/memory/session/summary", headers={"Authorization": f"Bearer {login_token}"})
    assert summary.status_code == 200
    assert summary.json()["entry_count"] == 1

    cleared = http_client.delete("/api/memory/session", headers={"Authorization": f"Bearer {login_token}"})
    assert cleared.status_code == 200
    assert cleared.json()["cleared"] is True
```

Add persistent memory coverage:

```python
def test_persistent_memory_endpoints_require_same_agent(http_client, login_token) -> None:
    promoted = http_client.post("/api/memories/promote", headers={"Authorization": f"Bearer {login_token}"})
    assert promoted.status_code in {200, 400}
```

**Step 2: Run the test to verify it fails**

Run:

```bash
source .venv/bin/activate && \
python -m pytest tests/integration/test_http_memory_api.py -q
```

Expected: FAIL because the endpoints do not exist yet.

**Step 3: Write minimal implementation**

Add endpoints:
- `GET /api/memory/session`
- `GET /api/memory/session/summary`
- `DELETE /api/memory/session`
- `POST /api/memories/promote`
- `GET /api/memories`
- `GET /api/memories/{memory_id}`
- `POST /api/memories/{memory_id}/disable`

All session-memory endpoints must use:

```python
session_id = resolved.session_id
```

All persistent-memory endpoints must use:

```python
agent_principal = resolved.agent_principal
```

Do not accept external `session_id` or `agent_id` in the request.

**Step 4: Run the test to verify it passes**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/server/http_api.py tests/integration/test_http_memory_api.py
git commit -m "feat: add secure memory api"
```

### Task 7: Enforce real token scopes and profile policy gates

**Files:**
- Create: `src/video_agent/application/agent_authorization_service.py`
- Modify: `src/video_agent/domain/agent_models.py`
- Modify: `src/video_agent/application/agent_identity_service.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/server/http_auth.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/agent_admin/main.py`
- Test: `tests/unit/application/test_agent_authorization_service.py`
- Test: `tests/integration/test_http_scope_enforcement.py`
- Test: `tests/integration/test_agent_auth_tools.py`

**Step 1: Write the failing tests**

Create `tests/unit/application/test_agent_authorization_service.py`:

```python
from video_agent.application.agent_authorization_service import AgentAuthorizationService
from video_agent.domain.agent_models import AgentProfile, AgentToken


def test_token_scope_can_deny_mutation() -> None:
    service = AgentAuthorizationService()
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    token = AgentToken(token_hash="hash", agent_id="agent-a", scopes_json={"allow": ["task:read"]})

    assert service.is_allowed(profile, token, "task:read") is True
    assert service.is_allowed(profile, token, "task:create") is False
```

Create `tests/integration/test_http_scope_enforcement.py`:

```python
def test_scope_limited_session_cannot_create_task(http_client, issued_read_only_login_token) -> None:
    response = http_client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {issued_read_only_login_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "agent_scope_denied"
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/application/test_agent_authorization_service.py \
  tests/integration/test_http_scope_enforcement.py \
  tests/integration/test_agent_auth_tools.py \
  -q
```

Expected: FAIL because scopes are modeled but not enforced.

**Step 3: Write minimal implementation**

Create `AgentAuthorizationService`:

```python
class AgentAuthorizationService:
    DEFAULT_MUTATION_SCOPES = {
        "task:create",
        "task:read",
        "task:mutate",
        "memory:read",
        "memory:promote",
        "profile:read",
        "profile:write",
    }

    def is_allowed(self, profile: AgentProfile, token: AgentToken, action: str) -> bool:
        allow = set(token.scopes_json.get("allow", []))
        deny = set(token.scopes_json.get("deny", []))
        if action in deny:
            return False
        if allow:
            return action in allow
        profile_deny = set(profile.policy_json.get("deny_actions", []))
        return action not in profile_deny
```

Apply the service in:
- HTTP handlers
- MCP mutating tools
- future profile endpoints

Return `agent_scope_denied` consistently.

Also extend token/session persistence with `last_seen_at` writes on successful login/session resolution.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/agent_authorization_service.py \
  src/video_agent/domain/agent_models.py \
  src/video_agent/application/agent_identity_service.py \
  src/video_agent/application/task_service.py \
  src/video_agent/server/http_auth.py \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/agent_admin/main.py \
  tests/unit/application/test_agent_authorization_service.py \
  tests/integration/test_http_scope_enforcement.py \
  tests/integration/test_agent_auth_tools.py
git commit -m "feat: enforce agent scopes and policy gates"
```

### Task 8: Add a versioned preference baseline and replay-safe resolved profile

**Files:**
- Modify: `src/video_agent/domain/agent_models.py`
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/adapters/storage/schema.sql`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/preference_resolver.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Test: `tests/unit/application/test_preference_resolver.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`
- Test: `tests/integration/test_agent_auth_tools.py`

**Step 1: Write the failing tests**

Extend `tests/unit/application/test_preference_resolver.py`:

```python
from video_agent.application.preference_resolver import build_system_default_request_config


def test_system_default_request_config_includes_render_defaults() -> None:
    defaults = build_system_default_request_config(
        default_quality_preset="production",
        default_frame_rate=60,
        default_pixel_width=1920,
        default_pixel_height=1080,
    )

    assert defaults["output_profile"] == {
        "quality_preset": "production",
        "frame_rate": 60,
        "pixel_width": 1920,
        "pixel_height": 1080,
    }
```

Extend `tests/unit/adapters/storage/test_sqlite_store.py`:

```python
def test_store_increments_profile_version_on_profile_update(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    store.upsert_agent_profile(profile)
    store.upsert_agent_profile(profile.model_copy(update={"profile_json": {"style_hints": {"tone": "teaching"}}}))

    loaded = store.get_agent_profile("agent-a")

    assert loaded is not None
    assert loaded.profile_version == 2
```

Extend `tests/integration/test_agent_auth_tools.py`:

```python
def test_create_video_task_persists_profile_version_and_resolved_defaults(tmp_path: Path) -> None:
    app = create_app_context(_build_agent_auth_settings(tmp_path))
    _seed_agent_profile_and_token(app.store)
    principal = app.agent_identity_service.authenticate("agent-a-secret")

    payload = create_video_task_tool(app, {"prompt": "draw a circle"}, agent_principal=principal)
    task = app.store.get_task(payload["task_id"])

    assert task is not None
    assert task.profile_version == 1
    assert task.effective_request_profile
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/application/test_preference_resolver.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/integration/test_agent_auth_tools.py \
  -q
```

Expected: FAIL because profile versioning and full resolved default capture do not exist yet.

**Step 3: Write minimal implementation**

Add `profile_version` to `AgentProfile`:

```python
class AgentProfile(BaseModel):
    agent_id: str
    name: str
    status: str = "active"
    profile_version: int = 1
    profile_json: dict[str, Any] = Field(default_factory=dict)
    policy_json: dict[str, Any] = Field(default_factory=dict)
```

Add task replay fields to `VideoTask`:

```python
class VideoTask(BaseModel):
    ...
    profile_version: int | None = None
    effective_policy_flags: dict[str, Any] = Field(default_factory=dict)
```

Add one helper in `preference_resolver.py`:

```python
def build_system_default_request_config(
    *,
    default_quality_preset: str,
    default_frame_rate: int | None,
    default_pixel_width: int | None,
    default_pixel_height: int | None,
) -> dict[str, Any]:
    output_profile: dict[str, Any] = {"quality_preset": default_quality_preset}
    if default_frame_rate is not None:
        output_profile["frame_rate"] = default_frame_rate
    if default_pixel_width is not None:
        output_profile["pixel_width"] = default_pixel_width
    if default_pixel_height is not None:
        output_profile["pixel_height"] = default_pixel_height
    return {"output_profile": output_profile}
```

Update `SQLiteTaskStore.upsert_agent_profile(...)` so it increments `profile_version` on update, and add a `profile_version` column to `agent_profiles`.

Update `TaskService.create_video_task(...)` to resolve:

```python
system_defaults = build_system_default_request_config(
    default_quality_preset=self.settings.default_quality_preset,
    default_frame_rate=self.settings.default_frame_rate,
    default_pixel_width=self.settings.default_pixel_width,
    default_pixel_height=self.settings.default_pixel_height,
)
effective_request_profile = resolve_effective_request_config(
    system_defaults=system_defaults,
    profile_json=principal.profile.profile_json,
    token_override_json=principal.token.override_json,
    request_overrides=...,
)
task = VideoTask(
    ...,
    profile_version=principal.profile.profile_version,
    effective_policy_flags=principal.profile.policy_json,
)
```

Use the stored `effective_request_profile`, `profile_version`, and `effective_policy_flags` for later replay and reporting. Do not recompute from current profile state during workflow execution.

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
  src/video_agent/application/task_service.py \
  src/video_agent/application/preference_resolver.py \
  src/video_agent/application/workflow_engine.py \
  tests/unit/application/test_preference_resolver.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/integration/test_agent_auth_tools.py
git commit -m "feat: persist versioned preference baselines"
```

### Task 9: Add per-agent profile read and audited profile apply endpoints

**Files:**
- Create: `src/video_agent/domain/agent_profile_revision_models.py`
- Modify: `src/video_agent/adapters/storage/schema.sql`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/server/http_api.py`
- Test: `tests/integration/test_http_profile_api.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`

**Step 1: Write the failing test**

Create `tests/integration/test_http_profile_api.py`:

```python
def test_profile_read_and_apply_patch_are_audited(http_client, login_token) -> None:
    profile = http_client.get("/api/profile", headers={"Authorization": f"Bearer {login_token}"})
    assert profile.status_code == 200

    apply = http_client.post(
        "/api/profile/apply",
        json={"patch": {"style_hints": {"tone": "teaching"}}},
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert apply.status_code == 200
    assert apply.json()["applied"] is True
```

Extend SQLite tests with an audited revision record.

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/integration/test_http_profile_api.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  -q
```

Expected: FAIL because the API and revision audit store do not exist.

**Step 3: Write minimal implementation**

Add `agent_profile_revisions` table:

```sql
CREATE TABLE IF NOT EXISTS agent_profile_revisions (
    revision_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    patch_json TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

Add endpoints:
- `GET /api/profile`
- `POST /api/profile/apply`

Allowed patch keys in the first slice:
- `style_hints`
- `output_profile`
- `validation_profile`

Reject everything else with `422`.

Apply patches with the existing merge rules:

```python
effective = resolve_effective_request_config(
    profile_json=current_profile.profile_json,
    request_overrides=payload.patch,
)
```

Persist both the updated profile and an audit record.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/domain/agent_profile_revision_models.py src/video_agent/adapters/storage/schema.sql src/video_agent/adapters/storage/sqlite_store.py src/video_agent/server/http_api.py tests/integration/test_http_profile_api.py tests/unit/adapters/storage/test_sqlite_store.py
git commit -m "feat: add audited profile apply api"
```

### Task 10: Record per-agent learning telemetry and scorecard inputs

**Files:**
- Create: `src/video_agent/domain/agent_learning_models.py`
- Create: `src/video_agent/application/agent_learning_service.py`
- Modify: `src/video_agent/adapters/storage/schema.sql`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/eval_service.py`
- Modify: `src/video_agent/server/http_api.py`
- Test: `tests/unit/application/test_agent_learning_service.py`
- Test: `tests/integration/test_agent_learning_capture.py`

**Step 1: Write the failing tests**

Create `tests/unit/application/test_agent_learning_service.py`:

```python
from video_agent.application.agent_learning_service import AgentLearningService


def test_learning_service_records_success_and_quality_signals() -> None:
    written = []
    service = AgentLearningService(write_event=lambda event: written.append(event))

    service.record_task_outcome(
        agent_id="agent-a",
        task_id="task-1",
        session_id="sess-1",
        status="completed",
        issue_codes=["near_blank_preview"],
        quality_score=0.8,
        profile_digest="digest-1",
        memory_ids=["mem-1"],
    )

    assert written[0].agent_id == "agent-a"
    assert written[0].quality_score == 0.8
```

Create `tests/integration/test_agent_learning_capture.py`:

```python
def test_completed_task_writes_agent_learning_event(tmp_path) -> None:
    ...
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/application/test_agent_learning_service.py \
  tests/integration/test_agent_learning_capture.py \
  -q
```

Expected: FAIL because the learning models/service/store do not exist.

**Step 3: Write minimal implementation**

Add `agent_learning_events` table with fields:
- `event_id`
- `agent_id`
- `task_id`
- `session_id`
- `status`
- `issue_codes_json`
- `quality_score`
- `profile_digest`
- `memory_ids_json`
- `created_at`

Create `AgentLearningService.record_task_outcome(...)` and call it from `WorkflowEngine` after a terminal task outcome is known.

Expose a read-only scorecard endpoint:

```python
@app.get("/api/profile/scorecard")
def profile_scorecard(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
    return context.agent_learning_service.build_scorecard(resolved.agent_principal.agent_id)
```

The first scorecard payload should include:
- `completed_count`
- `failed_count`
- `median_quality_score`
- `top_issue_codes`
- `recent_profile_digests`

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/domain/agent_learning_models.py \
  src/video_agent/application/agent_learning_service.py \
  src/video_agent/adapters/storage/schema.sql \
  src/video_agent/adapters/storage/sqlite_store.py \
  src/video_agent/application/workflow_engine.py \
  src/video_agent/application/eval_service.py \
  src/video_agent/server/http_api.py \
  tests/unit/application/test_agent_learning_service.py \
  tests/integration/test_agent_learning_capture.py
git commit -m "feat: record per-agent learning telemetry"
```

### Task 11: Generate explicit profile suggestions from session summaries, persistent memories, and successful outcomes

**Files:**
- Create: `src/video_agent/domain/agent_profile_suggestion_models.py`
- Create: `src/video_agent/application/agent_profile_suggestion_service.py`
- Modify: `src/video_agent/adapters/storage/schema.sql`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/server/http_api.py`
- Test: `tests/unit/application/test_agent_profile_suggestion_service.py`
- Test: `tests/integration/test_http_profile_suggestions_api.py`

**Step 1: Write the failing tests**

Create `tests/unit/application/test_agent_profile_suggestion_service.py`:

```python
from video_agent.application.agent_profile_suggestion_service import AgentProfileSuggestionService
from video_agent.domain.agent_memory_models import AgentMemoryRecord


def test_service_derives_patch_from_persistent_memory_and_recent_success() -> None:
    service = AgentProfileSuggestionService(
        list_memories=lambda agent_id: [
            AgentMemoryRecord(
                memory_id="mem-1",
                agent_id=agent_id,
                source_session_id="sess-1",
                summary_text="Use a steady teaching tone and 1280x720 output.",
                summary_digest="digest-1",
            )
        ],
        list_recent_session_summaries=lambda agent_id: [
            {"session_id": "sess-1", "summary_text": "Successful sessions preferred a teaching tone and steady pacing."}
        ],
        build_scorecard=lambda agent_id: {"completed_count": 5, "median_quality_score": 0.95},
        create_suggestion=lambda suggestion: suggestion,
    )

    suggestion = service.generate_suggestions("agent-a")[0]
    assert suggestion.agent_id == "agent-a"
    assert suggestion.patch
```

Create `tests/integration/test_http_profile_suggestions_api.py`:

```python
def test_profile_suggestions_list_and_apply_flow(http_client, login_token) -> None:
    listed = http_client.get("/api/profile/suggestions", headers={"Authorization": f"Bearer {login_token}"})
    assert listed.status_code == 200
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/application/test_agent_profile_suggestion_service.py \
  tests/integration/test_http_profile_suggestions_api.py \
  -q
```

Expected: FAIL because the suggestion and explicit preference-promotion layer does not exist.

**Step 3: Write minimal implementation**

Add `agent_profile_suggestions` table with fields:
- `suggestion_id`
- `agent_id`
- `patch_json`
- `rationale_json`
- `status`
- `created_at`
- `applied_at`

Create `AgentProfileSuggestionService` that:
- reads recent active persistent memories
- reads recent promoted or summarized session preferences
- reads recent learning scorecard
- generates **small** safe patches only for:
  - `style_hints.tone`
  - `style_hints.pace`
  - `output_profile`
  - `validation_profile`

Create endpoints:
- `POST /api/profile/preferences/propose`
- `POST /api/profile/preferences/promote`
- `POST /api/profile/suggestions/generate`
- `GET /api/profile/suggestions`
- `POST /api/profile/suggestions/{suggestion_id}/apply`
- `POST /api/profile/suggestions/{suggestion_id}/dismiss`

Use an explicit deterministic rule set in the first slice. Do **not** add an LLM dependency here. Persist provenance to the originating `session_id`, `memory_id`, and `profile_version`.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/domain/agent_profile_suggestion_models.py \
  src/video_agent/application/agent_profile_suggestion_service.py \
  src/video_agent/adapters/storage/schema.sql \
  src/video_agent/adapters/storage/sqlite_store.py \
  src/video_agent/server/http_api.py \
  tests/unit/application/test_agent_profile_suggestion_service.py \
  tests/integration/test_http_profile_suggestions_api.py
git commit -m "feat: add explicit profile suggestion flow"
```

### Task 12: Add guarded auto-apply learning mode

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/application/agent_profile_suggestion_service.py`
- Modify: `src/video_agent/server/http_api.py`
- Test: `tests/unit/application/test_agent_profile_suggestion_service.py`
- Test: `tests/integration/test_agent_profile_auto_apply.py`

**Step 1: Write the failing tests**

Add a rule-based auto-apply test:

```python
def test_auto_apply_requires_threshold_and_no_recent_failures() -> None:
    ...
```

Create `tests/integration/test_agent_profile_auto_apply.py`:

```python
def test_auto_apply_mode_only_applies_safe_supported_patch(http_client, login_token) -> None:
    ...
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/application/test_agent_profile_suggestion_service.py \
  tests/integration/test_agent_profile_auto_apply.py \
  -q
```

Expected: FAIL because there is no auto-apply gate yet.

**Step 3: Write minimal implementation**

Add settings:

```python
agent_learning_auto_apply_enabled: bool = False
agent_learning_auto_apply_min_completed_tasks: int = 5
agent_learning_auto_apply_min_quality_score: float = 0.9
agent_learning_auto_apply_max_recent_failures: int = 0
```

Implement `maybe_auto_apply(...)`:

```python
if not settings.agent_learning_auto_apply_enabled:
    return None
if scorecard["completed_count"] < settings.agent_learning_auto_apply_min_completed_tasks:
    return None
if scorecard["median_quality_score"] < settings.agent_learning_auto_apply_min_quality_score:
    return None
if scorecard["failed_count_recent"] > settings.agent_learning_auto_apply_max_recent_failures:
    return None
```

Only auto-apply supported keys from Task 11 and always write:
- a profile revision audit record
- a suggestion status update
- a learning event noting auto-apply

Expose read-only visibility in `/api/profile/scorecard`.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/config.py src/video_agent/server/main.py src/video_agent/application/agent_profile_suggestion_service.py src/video_agent/server/http_api.py tests/unit/application/test_agent_profile_suggestion_service.py tests/integration/test_agent_profile_auto_apply.py
git commit -m "feat: add guarded profile auto-apply"
```

### Task 13: Make evals and regression gates agent-aware

**Files:**
- Modify: `src/video_agent/application/eval_service.py`
- Modify: `src/video_agent/eval/main.py`
- Modify: `src/video_agent/evaluation/reporting.py`
- Modify: `src/video_agent/evaluation/reviewer_digest.py`
- Modify: `src/video_agent/server/http_api.py`
- Test: `tests/integration/test_eval_run_cli.py`
- Test: `tests/unit/evaluation/test_reporting.py`
- Test: `tests/integration/test_http_profile_api.py`
- Docs: `docs/runbooks/real-provider-trial.md`
- Docs: `docs/runbooks/release-checklist.md`

**Step 1: Write the failing tests**

Add CLI coverage:

```python
def test_eval_run_can_target_agent_profile(tmp_path: Path) -> None:
    ...
```

Add reporting coverage:

```python
def test_reporting_includes_agent_breakdown() -> None:
    ...
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/integration/test_eval_run_cli.py \
  tests/unit/evaluation/test_reporting.py \
  -q
```

Expected: FAIL because eval/reporting do not include agent-aware slices yet.

**Step 3: Write minimal implementation**

Add optional eval inputs:
- `--agent-id`
- `--memory-id`
- `--profile-patch-json`

When `--agent-id` is present, the eval run should:
- create tasks as that agent
- record the profile digest used
- emit `report.agent` with:
  - pass rate
  - median quality
  - top issue codes
  - active profile digest

Add HTTP read-only endpoints:
- `GET /api/profile/evals`
- `GET /api/profile/evals/{run_id}`

Update reviewer digest to include “Agent Slice” when present.

**Step 4: Run the tests to verify they pass**

Run the same command again.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/eval_service.py \
  src/video_agent/eval/main.py \
  src/video_agent/evaluation/reporting.py \
  src/video_agent/evaluation/reviewer_digest.py \
  src/video_agent/server/http_api.py \
  tests/integration/test_eval_run_cli.py \
  tests/unit/evaluation/test_reporting.py \
  docs/runbooks/real-provider-trial.md \
  docs/runbooks/release-checklist.md
git commit -m "feat: add agent-aware eval reporting"
```

### Task 14: Final hardening, docs, and end-to-end HTTP deployment path

**Files:**
- Modify: `README.md`
- Modify: `docs/runbooks/local-dev.md`
- Modify: `docs/runbooks/beta-ops.md`
- Modify: `docs/runbooks/release-checklist.md`
- Modify: `tests/e2e/test_streamable_http_single_task_flow.py`
- Create: `tests/e2e/test_http_session_flow.py`
- Optional: `docs/runbooks/http-api-deploy.md`

**Step 1: Write the failing end-to-end test**

Create `tests/e2e/test_http_session_flow.py` with a real login/use/logout flow:

```python
def test_http_session_flow_end_to_end(tmp_path: Path) -> None:
    # start api server in required auth mode
    # issue token
    # log in
    # create task
    # read task
    # read session memory
    # log out
    # verify revoked session can no longer read
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/e2e/test_http_session_flow.py \
  tests/e2e/test_streamable_http_single_task_flow.py \
  -q
```

Expected: FAIL until the docs and end-to-end path match the shipped runtime.

**Step 3: Write the minimal hardening and docs**

Update docs with:
- `easy-manim-api` startup examples
- `curl` login examples
- `Authorization: Bearer <session_token>` examples
- logout and revocation behavior
- warning that `session_id` is internal-only
- warning that single-instance deployment is the supported first production target
- explicit recommendation to run with `EASY_MANIM_AUTH_MODE=required`

Suggested README snippet:

```bash
source .venv/bin/activate
export EASY_MANIM_AUTH_MODE=required
easy-manim-api --host 0.0.0.0 --port 8000

curl -X POST http://127.0.0.1:8000/api/sessions \
  -H 'content-type: application/json' \
  -d '{"agent_token":"<issued_token>"}'
```

Add a deployment runbook section covering:
- reverse proxy / TLS
- sticky single-instance assumption
- token issue flow
- session revocation
- operator recovery after service restart

**Step 4: Run the full verification suite**

Run:

```bash
source .venv/bin/activate && \
python -m pip install -e '.[dev]' && \
python -m pytest -q && \
python scripts/beta_smoke.py --mode ci && \
python scripts/release_candidate_gate.py --mode ci
```

Expected: PASS

Then run focused HTTP/API checks:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/integration/test_http_api.py \
  tests/integration/test_http_auth_api.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_http_memory_api.py \
  tests/integration/test_http_scope_enforcement.py \
  tests/integration/test_http_profile_api.py \
  tests/integration/test_http_profile_suggestions_api.py \
  tests/integration/test_agent_profile_auto_apply.py \
  tests/e2e/test_http_session_flow.py \
  -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add \
  README.md \
  docs/runbooks/local-dev.md \
  docs/runbooks/beta-ops.md \
  docs/runbooks/release-checklist.md \
  docs/runbooks/http-api-deploy.md \
  tests/e2e/test_streamable_http_single_task_flow.py \
  tests/e2e/test_http_session_flow.py
git commit -m "docs: finalize http self-serve deployment path"
```

## Final Delivery Checklist

Before calling the project “done,” verify all of the following:

1. Agents can log in once and reuse a returned opaque session credential across independent HTTP requests.
2. HTTP clients never see or supply internal `session_id`.
3. Different agents cannot read or mutate each other’s tasks, resources, session memory, or persistent memory.
4. Token scopes are enforced consistently in both HTTP and MCP surfaces.
5. Per-agent profile updates are auditable and reversible by reapplying the previous patch.
6. Every task snapshot records `profile_version`, resolved request config, and effective policy flags.
7. Learning telemetry exists per `agent_id` and can be inspected through a scorecard.
8. Profile suggestions are explicit and safe before auto-apply is enabled.
9. Auto-apply is disabled by default and guarded by conservative thresholds.
10. Eval reporting can attribute results to agent profiles, profile versions, and profile digests.
11. Docs include both MCP and plain HTTP usage so agent callers can self-serve.

## Recommended Execution Order

1. Execute Tasks 1-6 to ship the usable self-serve HTTP API.
2. Execute Task 7 immediately after to make the public surface safe.
3. Execute Task 8 before any autonomous learning work so replay and attribution are stable.
4. Execute Tasks 9-11 to unlock per-agent independent improvement.
5. Execute Task 12 only after scorecards and suggestion quality are trustworthy.
6. Execute Tasks 13-14 last to harden rollout and prove stability.

## Notes for the Implementer

1. Do not rebuild the workflow engine. Reuse `TaskService`, `SessionMemoryService`, and `PersistentMemoryService` directly.
2. Do not tie long-term learning to token identity. Always aggregate by stable `agent_id`.
3. Do not expose internal `session_id` or trust caller-supplied `session_id`.
4. Do not auto-apply profile changes until explicit scorecard thresholds exist.
5. Keep Band 1 shippable even if Band 2 and Band 3 slip.
