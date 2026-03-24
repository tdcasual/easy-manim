from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.models import VideoTask
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def _build_http_memory_settings(tmp_path: Path) -> Settings:
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
        )
    )


def test_session_memory_endpoint_ignores_external_session_id_query(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_memory_settings(tmp_path)))
    _seed_agent_profile_and_token(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]

    context = client.app.state.app_context
    session = context.agent_session_service.resolve_session(session_token)
    context.session_memory_service.record_task_created(
        VideoTask(prompt="draw a circle", session_id=session.session_id, agent_id="agent-a"),
        attempt_kind="create",
    )

    response = client.get(
        "/api/memory/session",
        params={"session_id": "forged-session"},
        headers={"Authorization": f"Bearer {session_token}"},
    )

    assert response.status_code == 200
    assert response.json()["entry_count"] == 1
    assert "session_id" not in response.json()


def test_session_memory_endpoints_are_bound_to_authenticated_session(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_memory_settings(tmp_path)))
    _seed_agent_profile_and_token(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert created.status_code == 200

    memory = client.get("/api/memory/session", headers={"Authorization": f"Bearer {session_token}"})
    assert memory.status_code == 200
    assert memory.json()["entry_count"] == 1
    assert "session_id" not in memory.json()

    summary = client.get("/api/memory/session/summary", headers={"Authorization": f"Bearer {session_token}"})
    assert summary.status_code == 200
    assert summary.json()["entry_count"] == 1
    assert summary.json()["summary_text"]
    assert "session_id" not in summary.json()

    cleared = client.delete("/api/memory/session", headers={"Authorization": f"Bearer {session_token}"})
    assert cleared.status_code == 200
    assert cleared.json()["cleared"] is True
    assert cleared.json()["entry_count"] == 0
    assert "session_id" not in cleared.json()


def test_persistent_memory_endpoints_require_same_agent(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_memory_settings(tmp_path)))
    _seed_agent_profile_and_token(client)
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-b",
            name="Agent B",
            profile_json={"style_hints": {"tone": "direct"}},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-b-secret"),
            agent_id="agent-b",
        )
    )

    token_a = client.post("/api/sessions", json={"agent_token": "agent-a-secret"}).json()["session_token"]
    token_b = client.post("/api/sessions", json={"agent_token": "agent-b-secret"}).json()["session_token"]

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert created.status_code == 200

    promoted = client.post("/api/memories/promote", headers={"Authorization": f"Bearer {token_a}"})
    assert promoted.status_code == 200
    memory_id = promoted.json()["memory_id"]
    assert "source_session_id" not in promoted.json()

    listed = client.get("/api/memories", headers={"Authorization": f"Bearer {token_a}"})
    assert listed.status_code == 200
    assert any(item["memory_id"] == memory_id for item in listed.json()["items"])
    assert all("source_session_id" not in item for item in listed.json()["items"])

    forbidden_get = client.get(f"/api/memories/{memory_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert forbidden_get.status_code == 403
    assert forbidden_get.json()["detail"] == "agent_memory_forbidden"

    forbidden_disable = client.post(
        f"/api/memories/{memory_id}/disable",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden_disable.status_code == 403
    assert forbidden_disable.json()["detail"] == "agent_memory_forbidden"

    fetched = client.get(f"/api/memories/{memory_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert fetched.status_code == 200
    assert fetched.json()["memory_id"] == memory_id
    assert "source_session_id" not in fetched.json()

    disabled = client.post(f"/api/memories/{memory_id}/disable", headers={"Authorization": f"Bearer {token_a}"})
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"
    assert "source_session_id" not in disabled.json()
