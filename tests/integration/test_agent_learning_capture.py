import json
from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_learning_service import AgentLearningService
from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_agent_learning_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-ql\" ]; then exit 11; fi\n"
        "if [ \"$4\" != \"--media_dir\" ]; then exit 12; fi\n"
        "if [ \"$6\" != \"-o\" ]; then exit 13; fi\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/480p15\"\n"
        "printf 'normal-video' > \"$5/videos/$script_name/480p15/$7\"\n"
        "printf 'render ok\\n'\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    probe_json = json.dumps(
        {
            "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
            "format": {"duration": "2.5"},
        }
    )
    _write_executable(
        fake_ffprobe,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-v\" ]; then exit 31; fi\n"
        f"printf '%s' '{probe_json}'\n",
    )

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "if [ \"$1\" != \"-y\" ]; then exit 20; fi\n"
        "if [ \"$2\" != \"-i\" ]; then exit 21; fi\n"
        "if [ \"$4\" != \"-vf\" ]; then exit 22; fi\n"
        "mkdir -p \"$(dirname \"$6\")\"\n"
        "printf 'frame1' > \"$(dirname \"$6\")/frame_001.png\"\n",
    )

    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
            run_embedded_worker=False,
            auth_mode="required",
        )
    )


def _build_auto_repair_learning_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim_fail.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "printf 'simulated render failure\\n' >&2\n"
        "exit 17\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    probe_json = json.dumps(
        {
            "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
            "format": {"duration": "2.5"},
        }
    )
    _write_executable(fake_ffprobe, f"#!/bin/sh\nprintf '%s' '{probe_json}'\n")

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "mkdir -p \"$2\"\n"
        "printf 'frame1' > \"$2/frame_001.png\"\n",
    )

    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
            run_embedded_worker=False,
            auto_repair_enabled=True,
            auto_repair_max_children_per_root=1,
            auto_repair_retryable_issue_codes=["render_failed"],
        )
    )


def _seed_agent(client: TestClient, agent_id: str, secret: str) -> None:
    context = client.app.state.app_context
    context.store.upsert_agent_profile(
        AgentProfile(
            agent_id=agent_id,
            name="Agent A",
            profile_json={"style_hints": {"tone": "teaching"}},
        )
    )
    context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token(secret),
            agent_id=agent_id,
        )
    )


def test_completed_task_writes_agent_learning_event(tmp_path: Path) -> None:
    client = TestClient(create_http_api(_build_agent_learning_settings(tmp_path)))
    _seed_agent(client, "agent-a", "agent-a-secret")

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    session_token = login.json()["session_token"]

    created = client.post(
        "/api/tasks",
        json={"prompt": "draw a circle"},
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    app_context = client.app.state.app_context
    processed = app_context.worker.run_once()
    assert processed == 1

    events = app_context.store.list_agent_learning_events("agent-a")
    assert len(events) == 1
    assert events[0].task_id == task_id
    assert events[0].agent_id == "agent-a"
    assert events[0].status == "completed"

    stored_task = app_context.store.get_task(task_id)
    assert stored_task is not None
    assert events[0].session_id == stored_task.session_id
    assert events[0].profile_digest == stored_task.effective_profile_digest

    scorecard = client.get("/api/profile/scorecard", headers={"Authorization": f"Bearer {session_token}"})
    assert scorecard.status_code == 200
    assert scorecard.json()["completed_count"] == 1
    assert scorecard.json()["failed_count"] == 0
    assert scorecard.json()["median_quality_score"] == 1.0
    assert scorecard.json()["top_issue_codes"] == []
    assert scorecard.json()["recent_profile_digests"] == [stored_task.effective_profile_digest]


def test_learning_telemetry_failure_does_not_change_completed_task_outcome(tmp_path: Path) -> None:
    app_context = create_app_context(_build_agent_learning_settings(tmp_path).model_copy(update={"auth_mode": "optional"}))

    def _raise_on_write(event):
        raise RuntimeError("telemetry unavailable")

    app_context.workflow_engine.agent_learning_service = AgentLearningService(write_event=_raise_on_write)
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="telemetry-non-fatal")

    processed = app_context.worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert processed == 1
    assert snapshot.status == "completed"
    assert app_context.store.list_agent_learning_events("local-anonymous") == []


def test_auto_repair_waits_for_final_outcome_before_counting_failure(tmp_path: Path) -> None:
    app_context = create_app_context(_build_auto_repair_learning_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle")

    app_context.worker.run_once()

    scorecard_during_repair = app_context.agent_learning_service.build_scorecard("local-anonymous")
    assert app_context.store.count_lineage_tasks(created.task_id) == 2
    assert scorecard_during_repair["failed_count"] == 0

    app_context.worker.run_once()

    final_scorecard = app_context.agent_learning_service.build_scorecard("local-anonymous")
    assert final_scorecard["failed_count"] == 1


def test_learning_events_are_idempotent_per_task(tmp_path: Path) -> None:
    app_context = create_app_context(_build_agent_learning_settings(tmp_path).model_copy(update={"auth_mode": "optional"}))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="dedupe-learning")

    app_context.worker.run_once()
    stored_task = app_context.store.get_task(created.task_id)
    assert stored_task is not None

    app_context.agent_learning_service.record_task_outcome(
        agent_id="local-anonymous",
        task_id=created.task_id,
        session_id=stored_task.session_id,
        status="completed",
        issue_codes=[],
        quality_score=0.5,
        profile_digest=stored_task.effective_profile_digest,
        memory_ids=[],
    )

    events = app_context.store.list_agent_learning_events("local-anonymous")
    scorecard = app_context.agent_learning_service.build_scorecard("local-anonymous")

    assert len(events) == 1
    assert events[0].quality_score == 0.5
    assert scorecard["completed_count"] == 1
