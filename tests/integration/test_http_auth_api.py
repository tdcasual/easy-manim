from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def _build_http_auth_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
        )
    )


def _seed_agent_profile_and_token(client: TestClient) -> None:
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient", "pace": "steady"}},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
            override_json={"style_hints": {"tone": "teaching"}},
        )
    )


def _delete_runtime_definition(client: TestClient, agent_id: str) -> None:
    context = client.app.state.app_context
    with context.store._connect() as connection:
        connection.execute(
            "DELETE FROM agent_runtime_definitions WHERE agent_id = ?",
            (agent_id,),
        )


def test_http_auth_login_whoami_logout_flow(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_auth_settings(tmp_path)))
    _seed_agent_profile_and_token(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    assert login.status_code == 200
    session_token = login.json()["session_token"]

    assert session_token.startswith("esm_sess.")
    assert login.json()["agent_id"] == "agent-a"
    assert login.json()["name"] == "Agent A"
    assert login.json()["expires_at"]
    assert "session_id" not in login.json()

    whoami = client.get("/api/whoami", headers={"Authorization": f"Bearer {session_token}"})
    assert whoami.status_code == 200
    assert whoami.json()["agent_id"] == "agent-a"
    assert whoami.json()["name"] == "Agent A"
    assert whoami.json()["profile"]["style_hints"]["tone"] == "patient"
    assert "session_id" not in whoami.json()

    logout = client.delete("/api/sessions/current", headers={"Authorization": f"Bearer {session_token}"})
    assert logout.status_code == 200
    assert logout.json() == {"revoked": True}

    revoked = client.get("/api/whoami", headers={"Authorization": f"Bearer {session_token}"})
    assert revoked.status_code == 401
    assert revoked.json()["detail"] == "invalid_session_token"


def test_whoami_requires_bearer_session_token(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_auth_settings(tmp_path)))

    response = client.get("/api/whoami")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing_session_token"


def test_login_rejects_invalid_agent_token(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_auth_settings(tmp_path)))

    response = client.post("/api/sessions", json={"agent_token": "wrong-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_agent_token"


def test_login_rejects_agent_missing_persisted_runtime_definition_after_restart(tmp_path: Path) -> None:
    settings = _build_http_auth_settings(tmp_path)
    initial = TestClient(create_http_api(settings))
    _seed_agent_profile_and_token(initial)
    _delete_runtime_definition(initial, "agent-a")

    restarted = TestClient(create_http_api(settings))

    response = restarted.post("/api/sessions", json={"agent_token": "agent-a-secret"})

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_agent_token"


def test_session_remains_bound_to_issuing_token_across_cache_reset(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_auth_settings(tmp_path)))
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient", "pace": "steady"}},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-create-secret"),
            agent_id="agent-a",
            scopes_json={"allow": ["task:create"]},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-read-secret"),
            agent_id="agent-a",
            scopes_json={"allow": ["task:read"]},
        )
    )

    login = client.post("/api/sessions", json={"agent_token": "agent-a-create-secret"})
    assert login.status_code == 200
    session_token = login.json()["session_token"]

    create = client.post(
        "/api/tasks",
        json={"prompt": "draw a blue circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert create.status_code == 200
    task_id = create.json()["task_id"]
    context.artifact_store.final_video_path(task_id).write_bytes(b"fake-mp4-data")

    # Simulate process restart / cache loss.
    context.session_auth._sessions.clear()

    denied = client.get(
        f"/api/tasks/{task_id}/artifacts/final_video.mp4",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "agent_scope_denied"


def test_session_becomes_invalid_when_issuing_token_is_disabled(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_auth_settings(tmp_path)))
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient", "pace": "steady"}},
        )
    )
    issuing_hash = hash_agent_token("agent-a-secret")
    context.store.issue_agent_token(
        AgentToken(
            token_hash=issuing_hash,
            agent_id="agent-a",
            scopes_json={"allow": ["task:create", "task:read"]},
        )
    )

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    assert login.status_code == 200
    session_token = login.json()["session_token"]

    assert context.store.disable_agent_token(issuing_hash) is True
    context.session_auth._sessions.clear()

    whoami = client.get("/api/whoami", headers={"Authorization": f"Bearer {session_token}"})
    assert whoami.status_code == 401
    assert whoami.json()["detail"] == "invalid_session_token"


def test_http_task_and_runtime_runs_share_gateway_session_id(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_auth_settings(tmp_path)))
    _seed_agent_profile_and_token(client)
    context = client.app.state.app_context

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    assert login.status_code == 200
    session_token = login.json()["session_token"]

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a blue circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert created.status_code == 200

    task = context.store.get_task(created.json()["task_id"])
    runs = context.store.list_agent_runtime_runs(agent_id="agent-a")

    assert task is not None
    assert len(runs) == 2
    assert runs[0].trigger_kind == "authenticate"
    assert runs[1].trigger_kind == "create_video_task"
    assert runs[0].session_id == runs[1].session_id == task.session_id
