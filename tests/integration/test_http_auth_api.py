from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.http_api import create_http_api


def _build_http_auth_settings(tmp_path: Path) -> Settings:
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
            override_json={"style_hints": {"tone": "teaching"}},
        )
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
    assert login.json()["session_id"].startswith("sess-")
    assert login.json()["expires_at"]

    whoami = client.get("/api/whoami", headers={"Authorization": f"Bearer {session_token}"})
    assert whoami.status_code == 200
    assert whoami.json()["agent_id"] == "agent-a"
    assert whoami.json()["name"] == "Agent A"
    assert whoami.json()["profile"]["style_hints"]["tone"] == "patient"
    assert whoami.json()["session_id"] == login.json()["session_id"]

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
