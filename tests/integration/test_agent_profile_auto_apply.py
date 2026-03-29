import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_learning_service import quality_score_from_scorecard
from video_agent.config import Settings
from video_agent.domain.agent_learning_models import AgentLearningEvent
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile
from video_agent.domain.quality_models import QualityScorecard
from video_agent.domain.enums import TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def _load_cli_runner():
    module_path = Path(__file__).resolve().parents[1] / "support" / "cli_runner.py"
    spec = importlib.util.spec_from_file_location("tests_support_cli_runner", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Failed to load cli runner module at {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_repo_module_json = _load_cli_runner().run_repo_module_json


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
    ctx.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-2",
            agent_id="agent-a",
            source_session_id="sess-2",
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

    token_payload = run_repo_module_json(
        "video_agent.agent_admin.main",
        "--data-dir",
        str(tmp_path / "data"),
        "issue-token",
        "--agent-id",
        "agent-a",
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


def test_auto_apply_refuses_low_confidence_patch_even_when_global_thresholds_pass(tmp_path) -> None:
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
            agent_learning_auto_apply_min_quality_score=0.90,
            agent_learning_auto_apply_max_recent_failures=0,
        )
    )
    app = create_http_api(settings)
    ctx = app.state.app_context
    ctx.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    ctx.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-1",
            agent_id="agent-a",
            source_session_id="sess-1",
            summary_text="Use a teaching tone.",
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
            issue_codes=["static_previews"],
            quality_score=high_quality,
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
            issue_codes=["static_previews"],
            quality_score=high_quality,
            profile_digest="digest-2",
        )
    )

    token_payload = run_repo_module_json(
        "video_agent.agent_admin.main",
        "--data-dir",
        str(tmp_path / "data"),
        "issue-token",
        "--agent-id",
        "agent-a",
    )
    client = TestClient(app)
    login = client.post("/api/sessions", json={"agent_token": token_payload["agent_token"]})
    login_token = login.json()["session_token"]

    generated = client.post("/api/profile/suggestions/generate", headers={"Authorization": f"Bearer {login_token}"})

    assert generated.status_code == 200
    assert generated.json()["items"]
    assert all(item["status"] == "pending" for item in generated.json()["items"])
    assert generated.json()["items"][0]["rationale"]["confidence"] < 0.8

    profile = client.get("/api/profile", headers={"Authorization": f"Bearer {login_token}"})
    assert profile.status_code == 200
    assert profile.json()["profile_json"]["style_hints"]["tone"] == "patient"


def test_auto_apply_treats_single_observation_suggestion_as_low_confidence(tmp_path) -> None:
    high_quality = quality_score_from_scorecard(QualityScorecard(total_score=0.98, accepted=True))
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
            agent_learning_auto_apply_enabled=True,
            agent_learning_auto_apply_min_completed_tasks=2,
            agent_learning_auto_apply_min_quality_score=0.90,
            agent_learning_auto_apply_max_recent_failures=0,
        )
    )
    app = create_http_api(settings)
    ctx = app.state.app_context
    ctx.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    ctx.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-1",
            agent_id="agent-a",
            source_session_id="sess-1",
            summary_text="Use a teaching tone.",
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
            quality_score=high_quality,
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

    token_payload = run_repo_module_json(
        "video_agent.agent_admin.main",
        "--data-dir",
        str(tmp_path / "data"),
        "issue-token",
        "--agent-id",
        "agent-a",
    )
    client = TestClient(app)
    login = client.post("/api/sessions", json={"agent_token": token_payload["agent_token"]})
    login_token = login.json()["session_token"]

    generated = client.post("/api/profile/suggestions/generate", headers={"Authorization": f"Bearer {login_token}"})

    assert generated.status_code == 200
    assert generated.json()["items"]
    assert all(item["status"] == "pending" for item in generated.json()["items"])
    assert generated.json()["items"][0]["rationale"]["confidence"] < 0.8
    assert generated.json()["items"][0]["rationale"]["supporting_evidence_counts"]["style_hints.tone"] == 1

    profile = client.get("/api/profile", headers={"Authorization": f"Bearer {login_token}"})
    assert profile.status_code == 200
    assert profile.json()["profile_json"]["style_hints"]["tone"] == "patient"


def test_auto_apply_treats_split_single_field_evidence_as_low_confidence(tmp_path) -> None:
    high_quality = quality_score_from_scorecard(QualityScorecard(total_score=0.98, accepted=True))
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
            agent_learning_auto_apply_enabled=True,
            agent_learning_auto_apply_min_completed_tasks=2,
            agent_learning_auto_apply_min_quality_score=0.90,
            agent_learning_auto_apply_max_recent_failures=0,
        )
    )
    app = create_http_api(settings)
    ctx = app.state.app_context
    ctx.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    ctx.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-1",
            agent_id="agent-a",
            source_session_id="sess-1",
            summary_text="Use a teaching tone.",
            summary_digest="digest-1",
        )
    )
    ctx.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-2",
            agent_id="agent-a",
            source_session_id="sess-2",
            summary_text="Use 1280x720 output.",
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
            quality_score=high_quality,
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

    token_payload = run_repo_module_json(
        "video_agent.agent_admin.main",
        "--data-dir",
        str(tmp_path / "data"),
        "issue-token",
        "--agent-id",
        "agent-a",
    )
    client = TestClient(app)
    login = client.post("/api/sessions", json={"agent_token": token_payload["agent_token"]})
    login_token = login.json()["session_token"]

    generated = client.post("/api/profile/suggestions/generate", headers={"Authorization": f"Bearer {login_token}"})

    assert generated.status_code == 200
    assert generated.json()["items"]
    assert all(item["status"] == "pending" for item in generated.json()["items"])
    assert generated.json()["items"][0]["rationale"]["confidence"] < 0.8
    assert generated.json()["items"][0]["rationale"]["supporting_evidence_counts"]["style_hints.tone"] == 1
    assert generated.json()["items"][0]["rationale"]["supporting_evidence_counts"]["output_profile.pixel_width"] == 1

    profile = client.get("/api/profile", headers={"Authorization": f"Bearer {login_token}"})
    assert profile.status_code == 200
    assert profile.json()["profile_json"]["style_hints"]["tone"] == "patient"


def test_auto_apply_allows_memory_plus_summary_corroboration(tmp_path) -> None:
    high_quality = quality_score_from_scorecard(QualityScorecard(total_score=0.98, accepted=True))
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
            agent_learning_auto_apply_enabled=True,
            agent_learning_auto_apply_min_completed_tasks=2,
            agent_learning_auto_apply_min_quality_score=0.90,
            agent_learning_auto_apply_max_recent_failures=0,
        )
    )
    app = create_http_api(settings)
    ctx = app.state.app_context
    ctx.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    ctx.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-1",
            agent_id="agent-a",
            source_session_id="sess-1",
            summary_text="Use a teaching tone.",
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
            quality_score=high_quality,
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

    token_payload = run_repo_module_json(
        "video_agent.agent_admin.main",
        "--data-dir",
        str(tmp_path / "data"),
        "issue-token",
        "--agent-id",
        "agent-a",
    )
    client = TestClient(app)
    login = client.post("/api/sessions", json={"agent_token": token_payload["agent_token"]})
    login_token = login.json()["session_token"]

    session = ctx.agent_session_service.resolve_session(login_token)
    task = VideoTask(
        prompt="Prefer a teaching tone.",
        agent_id="agent-a",
        session_id=session.session_id,
        status=TaskStatus.COMPLETED,
    )
    ctx.session_memory_service.record_task_created(task, attempt_kind="create")
    ctx.session_memory_service.record_task_outcome(
        task,
        result_summary="Successful sessions preferred a teaching tone.",
    )

    generated = client.post("/api/profile/suggestions/generate", headers={"Authorization": f"Bearer {login_token}"})

    assert generated.status_code == 200
    assert generated.json()["items"]
    assert generated.json()["items"][0]["status"] == "applied"
    assert generated.json()["items"][0]["rationale"]["supporting_evidence_counts"]["style_hints.tone"] >= 2
    assert generated.json()["items"][0]["rationale"]["field_support"]["style_hints.tone"]["source_type_counts"]["memory"] >= 1
    assert generated.json()["items"][0]["rationale"]["field_support"]["style_hints.tone"]["source_type_counts"]["session_summary"] >= 1


def test_auto_apply_keeps_conflicting_evidence_pending(tmp_path) -> None:
    high_quality = quality_score_from_scorecard(QualityScorecard(total_score=0.98, accepted=True))
    settings = bootstrapped_settings(
        Settings(
            data_dir=tmp_path / "data",
            database_path=tmp_path / "data" / "video_agent.db",
            artifact_root=tmp_path / "data" / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
            agent_learning_auto_apply_enabled=True,
            agent_learning_auto_apply_min_completed_tasks=2,
            agent_learning_auto_apply_min_quality_score=0.90,
            agent_learning_auto_apply_max_recent_failures=0,
        )
    )
    app = create_http_api(settings)
    ctx = app.state.app_context
    ctx.store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    ctx.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-1",
            agent_id="agent-a",
            source_session_id="sess-1",
            summary_text="Use a teaching tone and steady pacing.",
            summary_digest="digest-1",
        )
    )
    ctx.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-2",
            agent_id="agent-a",
            source_session_id="sess-2",
            summary_text="Use a direct tone and steady pacing.",
            summary_digest="digest-2",
        )
    )
    ctx.store.create_agent_learning_event(
        AgentLearningEvent(
            event_id="learn-1",
            agent_id="agent-a",
            task_id="task-1",
            session_id="sess-1",
            status="completed",
            quality_score=high_quality,
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

    token_payload = run_repo_module_json(
        "video_agent.agent_admin.main",
        "--data-dir",
        str(tmp_path / "data"),
        "issue-token",
        "--agent-id",
        "agent-a",
    )
    client = TestClient(app)
    login = client.post("/api/sessions", json={"agent_token": token_payload["agent_token"]})
    login_token = login.json()["session_token"]

    generated = client.post("/api/profile/suggestions/generate", headers={"Authorization": f"Bearer {login_token}"})

    assert generated.status_code == 200
    assert generated.json()["items"]
    assert generated.json()["items"][0]["status"] == "pending"
    assert generated.json()["items"][0]["rationale"]["conflicts"]
    assert generated.json()["items"][0]["rationale"]["supporting_evidence_counts"]["style_hints.pace"] >= 2
