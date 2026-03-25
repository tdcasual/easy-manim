from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def _build_settings(tmp_path: Path) -> Settings:
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


def test_download_task_artifact_and_result_urls(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    session_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    context = client.app.state.app_context
    script_path = context.artifact_store.write_script(task_id, "from manim import *\n")
    video_path = context.artifact_store.final_video_path(task_id)
    video_path.write_bytes(b"fake-mp4-data")
    preview_path = context.artifact_store.previews_dir(task_id) / "frame_001.png"
    preview_path.write_bytes(b"png")
    report_path = context.artifact_store.validation_report_path(task_id)
    report_path.write_text('{"decision":"pass"}')

    result = client.get(f"/api/tasks/{task_id}/result", headers={"Authorization": f"Bearer {session_token}"})
    assert result.status_code == 200
    payload = result.json()
    assert payload["video_download_url"] == f"/api/tasks/{task_id}/artifacts/final_video.mp4"
    assert payload["script_download_url"] == f"/api/tasks/{task_id}/artifacts/current_script.py"
    assert payload["preview_download_urls"] == [f"/api/tasks/{task_id}/artifacts/previews/frame_001.png"]
    assert payload["validation_report_download_url"] == f"/api/tasks/{task_id}/artifacts/validations/{report_path.name}"

    video = client.get(
        f"/api/tasks/{task_id}/artifacts/final_video.mp4",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert video.status_code == 200
    assert video.content == b"fake-mp4-data"
    assert video.headers["content-type"].startswith("video/mp4")

    script = client.get(
        f"/api/tasks/{task_id}/artifacts/current_script.py",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert script.status_code == 200
    assert script.text == script_path.read_text()


def test_download_task_artifact_is_agent_scoped(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    _seed_agent(client, "agent-b", "agent-b-secret")
    token_a = _login(client, "agent-a-secret")
    token_b = _login(client, "agent-b-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    task_id = created.json()["task_id"]

    context = client.app.state.app_context
    context.artifact_store.final_video_path(task_id).write_bytes(b"fake-mp4-data")

    forbidden = client.get(
        f"/api/tasks/{task_id}/artifacts/final_video.mp4",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "agent_access_denied"
