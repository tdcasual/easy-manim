from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.enums import TaskPhase, TaskStatus, ValidationDecision
from video_agent.domain.validation_models import ValidationReport
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def _build_http_task_settings(tmp_path: Path) -> Settings:
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


def test_recent_videos_endpoint_returns_playable_tasks(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    session_token = _login(client, "agent-a-secret")

    created = client.post(
        "/api/tasks",
        json={"prompt": "做一个蓝色圆形开场动画，画面干净简洁"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    task_id = created.json()["task_id"]

    context = client.app.state.app_context
    task = context.store.get_task(task_id)
    assert task is not None
    task.status = TaskStatus.COMPLETED
    task.phase = TaskPhase.COMPLETED
    task.updated_at = datetime.now(timezone.utc)
    context.store.update_task(task)

    final_video = context.artifact_store.task_dir(task_id) / "artifacts" / "final_video.mp4"
    final_video.parent.mkdir(parents=True, exist_ok=True)
    final_video.write_bytes(b"video-bytes")
    preview_dir = final_video.parent / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview = preview_dir / "frame.png"
    preview.write_bytes(b"png")

    context.store.record_validation(
        task_id,
        ValidationReport(
            decision=ValidationDecision.PASS,
            passed=True,
            summary="最新摘要",
        ),
    )

    created_missing = client.post(
        "/api/tasks",
        json={"prompt": "生成一个简洁的贺卡动画"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    missing_task_id = created_missing.json()["task_id"]
    missing_task = context.store.get_task(missing_task_id)
    assert missing_task is not None
    missing_task.status = TaskStatus.COMPLETED
    missing_task.phase = TaskPhase.COMPLETED
    context.store.update_task(missing_task)

    response = client.get("/api/videos/recent", headers={"Authorization": f"Bearer {session_token}"})
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    items = payload["items"]
    assert len(items) == 1
    entry = items[0]
    assert entry["task_id"] == task_id
    assert entry["display_title"] == "蓝色圆形开场动画"
    assert entry["title_source"] == "prompt"
    assert entry["status"] == TaskStatus.COMPLETED.value
    assert isinstance(entry["updated_at"], str)
    assert datetime.fromisoformat(entry["updated_at"])
    assert entry["latest_summary"] == "最新摘要"
    assert entry["latest_video_url"] == f"/api/tasks/{task_id}/artifacts/final_video.mp4"
    assert entry["latest_preview_url"] == f"/api/tasks/{task_id}/artifacts/previews/{preview.name}"


def test_recent_videos_endpoint_prefers_most_recent_updated_playable_tasks(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_task_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")
    session_token = _login(client, "agent-a-secret")
    context = client.app.state.app_context

    first = client.post(
        "/api/tasks",
        json={"prompt": "做一个蓝色圆形开场动画"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    first_id = first.json()["task_id"]
    first_task = context.store.get_task(first_id)
    assert first_task is not None
    first_task.status = TaskStatus.COMPLETED
    first_task.phase = TaskPhase.COMPLETED
    context.store.update_task(first_task)
    context.artifact_store.task_dir(first_id).mkdir(parents=True, exist_ok=True)
    context.artifact_store.final_video_path(first_id).write_bytes(b"a")
    context.artifact_store.previews_dir(first_id).mkdir(parents=True, exist_ok=True)
    frame1 = context.artifact_store.previews_dir(first_id) / "frame1.png"
    frame1.write_bytes(b"a")
    context.store.record_validation(
        first_id,
        ValidationReport(decision=ValidationDecision.PASS, passed=True, summary="first summary"),
    )

    second = client.post(
        "/api/tasks",
        json={"prompt": "做一个绿叶动画"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    second_id = second.json()["task_id"]
    second_task = context.store.get_task(second_id)
    assert second_task is not None
    second_task.status = TaskStatus.COMPLETED
    second_task.phase = TaskPhase.COMPLETED
    context.store.update_task(second_task)
    context.artifact_store.final_video_path(second_id).write_bytes(b"b")
    context.artifact_store.previews_dir(second_id).mkdir(parents=True, exist_ok=True)
    frame2 = context.artifact_store.previews_dir(second_id) / "frame2.png"
    frame2.write_bytes(b"b")
    context.store.record_validation(
        second_id,
        ValidationReport(decision=ValidationDecision.PASS, passed=True, summary="second summary"),
    )

    third = client.post(
        "/api/tasks",
        json={"prompt": "做一个临时占位任务"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    third_id = third.json()["task_id"]
    third_task = context.store.get_task(third_id)
    assert third_task is not None
    third_task.status = TaskStatus.COMPLETED
    third_task.phase = TaskPhase.COMPLETED
    context.store.update_task(third_task)

    first_task = context.store.get_task(first_id)
    assert first_task is not None
    first_task.status = TaskStatus.COMPLETED
    first_task.phase = TaskPhase.COMPLETED
    context.store.update_task(first_task)

    response = client.get("/api/videos/recent?limit=1", headers={"Authorization": f"Bearer {session_token}"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["task_id"] == first_id
