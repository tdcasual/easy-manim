from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_learning_models import AgentLearningEvent
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.enums import TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.server.http_api import create_http_api


def _build_http_profile_suggestion_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        run_embedded_worker=False,
        auth_mode="required",
    )


def _seed_agent_inputs(client: TestClient) -> str:
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
        )
    )
    context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-1",
            agent_id="agent-a",
            source_session_id="sess-1",
            summary_text="Use a steady teaching tone and 1280x720 output.",
            summary_digest="digest-1",
        )
    )
    context.store.create_agent_learning_event(
        AgentLearningEvent(
            event_id="evt-1",
            agent_id="agent-a",
            task_id="task-1",
            session_id="sess-1",
            status="completed",
            issue_codes=[],
            quality_score=0.95,
            profile_digest="digest-1",
            memory_ids=["mem-1"],
        )
    )
    return "mem-1"
def test_profile_suggestions_list_and_apply_flow(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_suggestion_settings(tmp_path)))
    memory_id = _seed_agent_inputs(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}
    session_id = client.app.state.app_context.agent_session_service.resolve_session(session_token).session_id

    proposed = client.post(
        "/api/profile/preferences/propose",
        json={"summary_text": "Prefer a teaching tone and steady pacing.", "session_id": session_id},
        headers=headers,
    )
    assert proposed.status_code == 200
    proposed_id = proposed.json()["suggestion"]["suggestion_id"]

    promoted = client.post(
        "/api/profile/preferences/promote",
        json={"memory_id": memory_id},
        headers=headers,
    )
    assert promoted.status_code == 200

    generated = client.post("/api/profile/suggestions/generate", headers=headers)
    assert generated.status_code == 200
    assert generated.json()["items"]

    listed = client.get("/api/profile/suggestions", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["items"]) >= 2

    generated_id = generated.json()["items"][0]["suggestion_id"]
    applied = client.post(f"/api/profile/suggestions/{generated_id}/apply", headers=headers)
    assert applied.status_code == 200
    assert applied.json()["applied"] is True
    assert applied.json()["profile"]["style_hints"]["tone"] == "teaching"
    assert applied.json()["profile"]["output_profile"]["pixel_width"] == 1280
    assert applied.json()["profile"]["output_profile"]["pixel_height"] == 720

    dismissed = client.post(f"/api/profile/suggestions/{proposed_id}/dismiss", headers=headers)
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "dismissed"


def test_generate_profile_suggestions_uses_recent_session_summaries(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_suggestion_settings(tmp_path)))
    _seed_agent_inputs(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}

    context = client.app.state.app_context
    session = context.agent_session_service.resolve_session(session_token)
    task = VideoTask(
        prompt="Prefer a teaching tone and steady pacing.",
        agent_id="agent-a",
        session_id=session.session_id,
        status=TaskStatus.COMPLETED,
    )
    context.session_memory_service.record_task_created(task, attempt_kind="create")
    context.session_memory_service.record_task_outcome(
        task,
        result_summary="Successful sessions preferred a teaching tone and steady pacing.",
    )
    context.store.disable_agent_memory("mem-1")

    generated = client.post("/api/profile/suggestions/generate", headers=headers)

    assert generated.status_code == 200
    assert generated.json()["items"]
    assert generated.json()["items"][0]["patch"]["style_hints"]["tone"] == "teaching"
    assert generated.json()["items"][0]["patch"]["style_hints"]["pace"] == "steady"


def test_generate_profile_suggestions_skips_empty_recent_sessions(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_suggestion_settings(tmp_path)))
    _seed_agent_inputs(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}

    context = client.app.state.app_context
    session = context.agent_session_service.resolve_session(session_token)
    task = VideoTask(
        prompt="Prefer a teaching tone and steady pacing.",
        agent_id="agent-a",
        session_id=session.session_id,
        status=TaskStatus.COMPLETED,
    )
    context.session_memory_service.record_task_created(task, attempt_kind="create")
    context.session_memory_service.record_task_outcome(
        task,
        result_summary="Successful sessions preferred a teaching tone and steady pacing.",
    )
    context.store.disable_agent_memory("mem-1")

    for _ in range(6):
        client.post("/api/sessions", json={"agent_token": "agent-a-secret"})

    generated = client.post("/api/profile/suggestions/generate", headers=headers)

    assert generated.status_code == 200
    assert generated.json()["items"]
    assert generated.json()["items"][0]["patch"]["style_hints"]["tone"] == "teaching"
    assert generated.json()["items"][0]["patch"]["style_hints"]["pace"] == "steady"


def test_generate_profile_suggestions_uses_recent_memories_only(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_suggestion_settings(tmp_path)))
    _seed_agent_inputs(client)

    context = client.app.state.app_context
    context.store.disable_agent_memory("mem-1")
    context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-old",
            agent_id="agent-a",
            source_session_id="sess-old",
            summary_text="Use 640x360 output.",
            summary_digest="digest-old",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    for index in range(2, 7):
        context.store.create_agent_memory(
            AgentMemoryRecord(
                memory_id=f"mem-{index}",
                agent_id="agent-a",
                source_session_id=f"sess-{index}",
                summary_text="Use a teaching tone.",
                summary_digest=f"digest-{index}",
            )
        )

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}

    generated = client.post("/api/profile/suggestions/generate", headers=headers)

    assert generated.status_code == 200
    assert generated.json()["items"]
    assert generated.json()["items"][0]["patch"]["style_hints"]["tone"] == "teaching"
    assert "output_profile" not in generated.json()["items"][0]["patch"]


def test_profile_suggestion_lifecycle_is_pending_only(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_suggestion_settings(tmp_path)))
    _seed_agent_inputs(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}

    generated = client.post("/api/profile/suggestions/generate", headers=headers)
    suggestion_id = generated.json()["items"][0]["suggestion_id"]

    applied = client.post(f"/api/profile/suggestions/{suggestion_id}/apply", headers=headers)
    assert applied.status_code == 200
    assert applied.json()["suggestion"]["status"] == "applied"
    assert applied.json()["suggestion"]["applied_at"] is not None

    dismissed = client.post(f"/api/profile/suggestions/{suggestion_id}/dismiss", headers=headers)
    assert dismissed.status_code == 409
    assert dismissed.json()["detail"] == "profile_suggestion_state_conflict"

    reapplied = client.post(f"/api/profile/suggestions/{suggestion_id}/apply", headers=headers)
    assert reapplied.status_code == 409
    assert reapplied.json()["detail"] == "profile_suggestion_state_conflict"


def test_profile_suggestion_generate_dedupes_pending_rows(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_suggestion_settings(tmp_path)))
    _seed_agent_inputs(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}

    first = client.post("/api/profile/suggestions/generate", headers=headers)
    second = client.post("/api/profile/suggestions/generate", headers=headers)
    listed = client.get("/api/profile/suggestions", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["items"][0]["suggestion_id"] == second.json()["items"][0]["suggestion_id"]
    assert len(listed.json()["items"]) == 1


def test_profile_preference_endpoints_validate_source_ownership(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_http_profile_suggestion_settings(tmp_path)))
    _seed_agent_inputs(client)

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}

    missing_memory = client.post(
        "/api/profile/preferences/promote",
        json={"memory_id": "missing-memory"},
        headers=headers,
    )
    assert missing_memory.status_code == 404
    assert missing_memory.json()["detail"] == "agent_memory_not_found"

    forged_session = client.post(
        "/api/profile/preferences/propose",
        json={"summary_text": "Prefer teaching tone.", "session_id": "someone-elses-session"},
        headers=headers,
    )
    assert forged_session.status_code == 404
    assert forged_session.json()["detail"] == "session_memory_not_found"
