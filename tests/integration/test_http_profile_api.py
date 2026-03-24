from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def _build_http_profile_settings(tmp_path: Path) -> Settings:
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
            profile_json={
                "style_hints": {"tone": "patient", "pace": "steady"},
                "output_profile": {"quality_preset": "high_quality"},
            },
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
        )
    )


def test_profile_read_and_apply_patch_are_audited(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_settings(tmp_path)))
    _seed_agent_profile_and_token(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]

    profile = client.get("/api/profile", headers={"Authorization": f"Bearer {session_token}"})
    assert profile.status_code == 200
    assert profile.json()["agent_id"] == "agent-a"
    assert profile.json()["profile"]["style_hints"]["tone"] == "patient"
    assert profile.json()["profile_version"] == 1

    apply = client.post(
        "/api/profile/apply",
        json={"patch": {"style_hints": {"tone": "teaching"}}},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert apply.status_code == 200
    assert apply.json()["applied"] is True
    assert apply.json()["agent_id"] == "agent-a"
    assert apply.json()["profile"]["style_hints"]["tone"] == "teaching"
    assert apply.json()["profile"]["style_hints"]["pace"] == "steady"
    assert apply.json()["profile_version"] == 2
    assert apply.json()["revision_id"]

    refreshed = client.get("/api/profile", headers={"Authorization": f"Bearer {session_token}"})
    assert refreshed.status_code == 200
    assert refreshed.json()["profile"]["style_hints"]["tone"] == "teaching"
    assert refreshed.json()["profile_version"] == 2

    revisions = client.app.state.app_context.store.list_agent_profile_revisions("agent-a")
    assert len(revisions) == 1
    assert revisions[0].patch_json == {"style_hints": {"tone": "teaching"}}
    assert revisions[0].source == "http.profile.apply"


def test_profile_apply_rejects_unknown_patch_keys(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_settings(tmp_path)))
    _seed_agent_profile_and_token(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]

    response = client.post(
        "/api/profile/apply",
        json={"patch": {"name": "forbidden"}},
        headers={"Authorization": f"Bearer {session_token}"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "unsupported_profile_patch_keys"


def test_profile_apply_rejects_non_object_allowlisted_sections(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_settings(tmp_path)))
    _seed_agent_profile_and_token(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]

    for patch in (
        {"style_hints": "teaching"},
        {"output_profile": ["high_quality"]},
        {"validation_profile": None},
    ):
        response = client.post(
            "/api/profile/apply",
            json={"patch": patch},
            headers={"Authorization": f"Bearer {session_token}"},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "invalid_profile_patch_shape"


def test_profile_endpoints_enforce_profile_scopes(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_settings(tmp_path)))
    context = client.app.state.app_context
    context.store.upsert_agent_profile(AgentProfile(agent_id="agent-a", name="Agent A"))
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-read-secret"),
            agent_id="agent-a",
            scopes_json={"allow": ["profile:read"]},
        )
    )

    session_token = client.post("/api/sessions", json={"agent_token": "agent-a-read-secret"}).json()["session_token"]

    profile = client.get("/api/profile", headers={"Authorization": f"Bearer {session_token}"})
    assert profile.status_code == 200

    denied_apply = client.post(
        "/api/profile/apply",
        json={"patch": {"style_hints": {"tone": "teaching"}}},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert denied_apply.status_code == 403
    assert denied_apply.json()["detail"] == "agent_scope_denied"
