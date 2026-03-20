from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.server.http_api import create_http_api


def _build_http_task_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        run_embedded_worker=False,
        auth_mode="required",
    )


def _seed_agent(client: TestClient, agent_id: str, secret: str) -> None:
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id=agent_id,
            name=agent_id,
            profile_json={"style_hints": {"tone": f"{agent_id}-tone"}},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
        )
    )


def _login(client: TestClient, secret: str) -> str:
    response = client.post("/api/sessions", json={"agent_token": secret})
    assert response.status_code == 200
    return response.json()["session_token"]


def test_task_create_list_get_result_roundtrip(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    login_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    listed = client.get("/api/tasks", headers={"Authorization": f"Bearer {login_token}"})
    assert listed.status_code == 200
    assert any(item["task_id"] == task_id for item in listed.json()["items"])

    snapshot = client.get(f"/api/tasks/{task_id}", headers={"Authorization": f"Bearer {login_token}"})
    assert snapshot.status_code == 200
    assert snapshot.json()["task_id"] == task_id
    assert snapshot.json()["agent_id"] == "agent-a"

    result = client.get(f"/api/tasks/{task_id}/result", headers={"Authorization": f"Bearer {login_token}"})
    assert result.status_code == 200
    assert result.json()["task_id"] == task_id
    assert result.json()["ready"] is False


def test_task_revise_retry_cancel_endpoints_are_agent_scoped(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    login_token_a = _login(client, "agent-a-secret")
    login_token_b = _login(client, "agent-b-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {login_token_a}"},
    )
    task_id = created.json()["task_id"]

    forbidden_revise = client.post(
        f"/api/tasks/{task_id}/revise",
        json={"feedback": "make it blue"},
        headers={"Authorization": f"Bearer {login_token_b}"},
    )
    assert forbidden_revise.status_code == 403
    assert forbidden_revise.json()["detail"] == "agent_access_denied"

    revised = client.post(
        f"/api/tasks/{task_id}/revise",
        json={"feedback": "make it blue"},
        headers={"Authorization": f"Bearer {login_token_a}"},
    )
    assert revised.status_code == 200
    revised_snapshot = client.get(
        f"/api/tasks/{revised.json()['task_id']}",
        headers={"Authorization": f"Bearer {login_token_a}"},
    )
    assert revised_snapshot.status_code == 200
    assert revised_snapshot.json()["parent_task_id"] == task_id

    context = client.app.state.app_context
    stored = context.store.get_task(task_id)
    assert stored is not None
    stored.status = TaskStatus.FAILED
    stored.phase = TaskPhase.FAILED
    context.store.update_task(stored)

    forbidden_retry = client.post(
        f"/api/tasks/{task_id}/retry",
        headers={"Authorization": f"Bearer {login_token_b}"},
    )
    assert forbidden_retry.status_code == 403
    assert forbidden_retry.json()["detail"] == "agent_access_denied"

    retried = client.post(
        f"/api/tasks/{task_id}/retry",
        headers={"Authorization": f"Bearer {login_token_a}"},
    )
    assert retried.status_code == 200

    forbidden_cancel = client.post(
        f"/api/tasks/{task_id}/cancel",
        headers={"Authorization": f"Bearer {login_token_b}"},
    )
    assert forbidden_cancel.status_code == 403
    assert forbidden_cancel.json()["detail"] == "agent_access_denied"

    cancelled = client.post(
        f"/api/tasks/{task_id}/cancel",
        headers={"Authorization": f"Bearer {login_token_a}"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["task_id"] == task_id
    assert cancelled.json()["status"] == "cancelled"
