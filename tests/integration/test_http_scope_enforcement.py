from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.http_api import create_http_api


def _build_http_scope_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        run_embedded_worker=False,
        auth_mode="required",
    )


def test_scope_limited_session_cannot_create_task(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_scope_settings(tmp_path)))
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(agent_id="agent-a", name="Agent A")
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-read-secret"),
            agent_id="agent-a",
            scopes_json={"allow": ["task:read"]},
        )
    )

    login = client.post("/api/sessions", json={"agent_token": "agent-a-read-secret"})
    assert login.status_code == 200
    session_token = login.json()["session_token"]

    response = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "agent_scope_denied"
