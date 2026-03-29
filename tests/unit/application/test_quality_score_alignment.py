import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.application.agent_learning_service import quality_score_from_scorecard
from video_agent.application.eval_service import EvaluationService
from video_agent.config import Settings
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.evaluation.models import PromptCase
from video_agent.evaluation.quality_reporting import build_quality_report
from video_agent.server.app import create_app_context
from video_agent.server.http_api import create_http_api
from tests.support import bootstrapped_settings


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_quality_alignment_settings(
    tmp_path: Path,
    *,
    auth_mode: str = "optional",
    auto_apply_enabled: bool = False,
    auto_apply_min_completed_tasks: int = 1,
    auto_apply_min_quality_score: float = 0.0,
) -> Settings:
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
        "printf 'normal-video' > \"$5/videos/$script_name/480p15/$7\"\n",
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
            auth_mode=auth_mode,
            agent_learning_auto_apply_enabled=auto_apply_enabled,
            agent_learning_auto_apply_min_completed_tasks=auto_apply_min_completed_tasks,
            agent_learning_auto_apply_min_quality_score=auto_apply_min_quality_score,
            agent_learning_auto_apply_max_recent_failures=0,
        )
    )


def test_completed_task_quality_score_aligns_runtime_learning_profile_and_eval(tmp_path: Path) -> None:
    app_context = create_app_context(_build_quality_alignment_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle")

    processed = app_context.worker.run_once()
    assert processed == 1

    persisted_scorecard = app_context.store.get_task_quality_score(created.task_id)
    assert persisted_scorecard is not None
    expected_score = quality_score_from_scorecard(persisted_scorecard)

    persisted_artifact = app_context.artifact_store.read_quality_score(created.task_id)
    assert persisted_artifact is not None
    assert persisted_artifact["total_score"] == expected_score

    events = app_context.store.list_agent_learning_events("local-anonymous")
    assert len(events) == 1
    assert events[0].quality_score == expected_score

    profile_scorecard = app_context.agent_learning_service.build_scorecard("local-anonymous")
    assert profile_scorecard["completed_count"] == 1
    assert profile_scorecard["median_quality_score"] == expected_score

    snapshot = app_context.task_service.get_video_task(created.task_id)
    eval_result = EvaluationService(app_context)._build_case_result(
        case=PromptCase(case_id="alignment-case", prompt="draw a circle", tags=["quality"]),
        root_task_id=created.task_id,
        root_snapshot=snapshot,
        terminal_snapshot=snapshot,
        started=time.monotonic() - 0.5,
    )
    assert eval_result.quality_score == expected_score

    quality_report = build_quality_report([eval_result.model_dump(mode="json")])
    assert quality_report["median_quality_score"] == expected_score


def test_profile_auto_apply_threshold_uses_scorecard_derived_median(tmp_path: Path) -> None:
    app = create_http_api(
        _build_quality_alignment_settings(
            tmp_path,
            auth_mode="required",
            auto_apply_enabled=True,
            auto_apply_min_completed_tasks=1,
            auto_apply_min_quality_score=1.0,
        )
    )
    client = TestClient(app)
    context = app.state.app_context

    context.store.upsert_agent_profile(AgentProfile(agent_id="agent-a", name="Agent A"))
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

    login = client.post("/api/sessions", json={"agent_token": "agent-a-secret"})
    assert login.status_code == 200
    session_token = login.json()["session_token"]
    headers = {"Authorization": f"Bearer {session_token}"}

    created = client.post("/api/tasks", json={"prompt": "draw a circle"}, headers=headers)
    assert created.status_code == 200
    task_id = created.json()["task_id"]

    processed = context.worker.run_once()
    assert processed == 1

    persisted_scorecard = context.store.get_task_quality_score(task_id)
    assert persisted_scorecard is not None
    expected_score = quality_score_from_scorecard(persisted_scorecard)
    context.settings.agent_learning_auto_apply_min_quality_score = round(expected_score + 0.01, 4)

    first_generate = client.post("/api/profile/suggestions/generate", headers=headers)
    assert first_generate.status_code == 200
    assert first_generate.json()["items"]
    assert all(item["status"] == "pending" for item in first_generate.json()["items"])

    context.settings.agent_learning_auto_apply_min_quality_score = expected_score
    second_generate = client.post("/api/profile/suggestions/generate", headers=headers)
    assert second_generate.status_code == 200
    assert any(item["status"] == "applied" for item in second_generate.json()["items"])

    profile_scorecard = client.get("/api/profile/scorecard", headers=headers)
    assert profile_scorecard.status_code == 200
    assert profile_scorecard.json()["median_quality_score"] == expected_score
