import json
import subprocess

from fastapi.testclient import TestClient

from video_agent.config import Settings
from video_agent.domain.agent_learning_models import AgentLearningEvent
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def test_auto_apply_mode_only_applies_safe_supported_patch(tmp_path) -> None:
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
            agent_learning_auto_apply_enabled=True,
            agent_learning_auto_apply_min_completed_tasks=2,
            agent_learning_auto_apply_min_quality_score=0.9,
            agent_learning_auto_apply_max_recent_failures=0,
        )
    )
    app = create_http_api(settings)
    ctx = app.state.app_context
    ctx.store.upsert_agent_profile(AgentProfile(agent_id="agent-a", name="Agent A"))
    ctx.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-1",
            agent_id="agent-a",
            source_session_id="sess-1",
            summary_text="Use a steady teaching tone and 1280x720 output.",
            summary_digest="digest-1",
        )
    )
    ctx.store.create_agent_learning_event(
        AgentLearningEvent(
            event_id="learn-1",
            agent_id="agent-a",
            task_id="task-1",
            session_id="sess-1",
            status="completed",
            quality_score=0.95,
            profile_digest="digest-1",
        )
    )
    ctx.store.create_agent_learning_event(
        AgentLearningEvent(
            event_id="learn-2",
            agent_id="agent-a",
            task_id="task-2",
            session_id="sess-2",
            status="completed",
            quality_score=0.96,
            profile_digest="digest-1",
        )
    )

    token_payload = json.loads(
        subprocess.check_output(
            [
                ".venv/bin/easy-manim-agent-admin",
                "--data-dir",
                str(tmp_path / "data"),
                "issue-token",
                "--agent-id",
                "agent-a",
            ],
            text=True,
        )
    )
    client = TestClient(app)
    login = client.post("/api/sessions", json={"agent_token": token_payload["agent_token"]})
    login_token = login.json()["session_token"]

    generated = client.post("/api/profile/suggestions/generate", headers={"Authorization": f"Bearer {login_token}"})
    assert generated.status_code == 200
    assert any(item["status"] == "applied" for item in generated.json()["items"])

    profile = client.get("/api/profile", headers={"Authorization": f"Bearer {login_token}"})
    assert profile.status_code == 200
    assert profile.json()["profile_json"]["style_hints"]["tone"] == "teaching"
