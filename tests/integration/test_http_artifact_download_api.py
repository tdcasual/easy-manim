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


def test_download_task_artifact_requires_task_read_scope(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_settings(tmp_path)))
    context = client.app.state.app_context
    context.store.upsert_agent_profile(AgentProfile(agent_id="agent-a", name="agent-a", profile_json={}))
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-read-secret"),
            agent_id="agent-a",
            scopes_json={"allow": ["task:read"]},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-create-secret"),
            agent_id="agent-a",
            scopes_json={"allow": ["task:create"]},
        )
    )

    create_token = _login(client, "agent-a-create-secret")
    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {create_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]
    context.artifact_store.final_video_path(task_id).write_bytes(b"fake-mp4-data")

    no_read_token = create_token
    forbidden = client.get(
        f"/api/tasks/{task_id}/artifacts/final_video.mp4",
        headers={"Authorization": f"Bearer {no_read_token}"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "agent_scope_denied"

    read_token = _login(client, "agent-a-read-secret")
    allowed = client.get(
        f"/api/tasks/{task_id}/artifacts/final_video.mp4",
        headers={"Authorization": f"Bearer {read_token}"},
    )
    assert allowed.status_code == 200
    assert allowed.content == b"fake-mp4-data"


def test_download_task_artifact_rejects_task_internal_files(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {token}"},
    )
    task_id = created.json()["task_id"]
    context = client.app.state.app_context
    context.artifact_store.write_task_snapshot(context.store.get_task(task_id))

    blocked_task_json = client.get(
        f"/api/tasks/{task_id}/artifacts/task.json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert blocked_task_json.status_code == 404
    assert blocked_task_json.json()["detail"] == "resource_not_found"


def test_download_task_artifact_unknown_task_is_404(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    token = _login(client, "agent-a-secret")

    missing = client.get(
        "/api/tasks/missing-task/artifacts/final_video.mp4",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "task_not_found"



def test_result_only_emits_download_urls_for_existing_files(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {token}"},
    )
    task_id = created.json()["task_id"]

    context = client.app.state.app_context
    report_path = context.artifact_store.validation_report_path(task_id)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text('{"decision":"pass"}')

    result = client.get(f"/api/tasks/{task_id}/result", headers={"Authorization": f"Bearer {token}"})
    assert result.status_code == 200
    payload = result.json()
    assert "video_download_url" not in payload
    assert "script_download_url" not in payload
    assert "preview_download_urls" not in payload
    assert payload["validation_report_download_url"] == f"/api/tasks/{task_id}/artifacts/validations/{report_path.name}"
