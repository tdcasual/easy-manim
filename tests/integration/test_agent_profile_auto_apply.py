import json
import subprocess

from fastapi.testclient import TestClient

from video_agent.application.agent_learning_service import quality_score_from_scorecard
from video_agent.config import Settings
from video_agent.domain.agent_learning_models import AgentLearningEvent
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile
from video_agent.domain.quality_models import QualityScorecard
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def test_auto_apply_mode_only_applies_safe_supported_patch(tmp_path) -> None:
    low_quality = quality_score_from_scorecard(QualityScorecard(total_score=0.91, accepted=True))
    high_quality = quality_score_from_scorecard(QualityScorecard(total_score=0.97, accepted=True))
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
            agent_learning_auto_apply_enabled=True,
            agent_learning_auto_apply_min_completed_tasks=2,
            agent_learning_auto_apply_min_quality_score=0.94,
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
            quality_score=low_quality,
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
            quality_score=high_quality,
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
    scorecard = client.get("/api/profile/scorecard", headers={"Authorization": f"Bearer {login_token}"})
    assert scorecard.status_code == 200
    assert scorecard.json()["median_quality_score"] == 0.94

    profile = client.get("/api/profile", headers={"Authorization": f"Bearer {login_token}"})
    assert profile.status_code == 200
    assert profile.json()["profile_json"]["style_hints"]["tone"] == "teaching"
