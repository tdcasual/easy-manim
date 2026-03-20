from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.models import VideoTask
from video_agent.server.http_api import create_http_api


def _build_http_memory_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        run_embedded_worker=False,
        auth_mode="required",
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
