import json
import sqlite3
from pathlib import Path

from video_agent.adapters.llm.client import StubLLMClient
from video_agent.config import Settings
from video_agent.safety.runtime_policy import RuntimePolicy
from video_agent.server.app import create_app_context



def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)



def _build_fake_pipeline_settings(tmp_path: Path) -> Settings:
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

    return Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        manim_command=str(fake_manim),
        ffmpeg_command=str(fake_ffmpeg),
        ffprobe_command=str(fake_ffprobe),
    )



def _load_event_payloads(database_path: Path, task_id: str, event_type: str) -> list[dict[str, object]]:
    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute(
            "SELECT payload_json FROM task_events WHERE task_id = ? AND event_type = ? ORDER BY id ASC",
            (task_id, event_type),
        ).fetchall()
    finally:
        connection.close()
    return [json.loads(row[0]) for row in rows]



def test_task_becomes_completed_only_after_validation_passes(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="complete")

    processed = app_context.worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert processed == 1
    assert snapshot.status == "completed"
    assert snapshot.latest_validation_summary["passed"] is True



def test_get_video_result_returns_artifacts_for_completed_task(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="result")

    app_context.worker.run_once()
    result = app_context.task_service.get_video_result(created.task_id)

    assert result.video_resource == f"video-task://{created.task_id}/artifacts/final_video.mp4"
    assert app_context.artifact_store.final_video_path(created.task_id).exists()
    assert len(result.preview_frame_resources) >= 1



def test_successful_task_records_structured_logs_and_metrics(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="observability")

    app_context.worker.run_once()
    log_events = _load_event_payloads(app_context.settings.database_path, created.task_id, "task_log")

    assert any(event["phase"] == "rendering" and event["attempt_count"] == 1 for event in log_events)
    assert all(event["task_id"] == created.task_id for event in log_events)
    assert app_context.metrics.counters["generation_runs"] == 1
    assert app_context.metrics.counters["render_runs"] == 1
    assert app_context.metrics.counters["validation_runs"] == 1
    assert len(app_context.metrics.timings["generation_seconds"]) == 1
    assert len(app_context.metrics.timings["render_seconds"]) == 1
    assert len(app_context.metrics.timings["validation_seconds"]) == 1



def test_runtime_policy_blocks_artifacts_outside_allowed_root(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    app_context.workflow_engine.runtime_policy = RuntimePolicy(work_root=tmp_path / "sandbox")
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="policy")

    app_context.worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert snapshot.status == "failed"
    assert snapshot.latest_validation_summary["issues"][0]["code"] == "runtime_policy_violation"


def test_task_succeeds_when_provider_returns_markdown_fenced_code(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    app_context.workflow_engine.llm_client = StubLLMClient(
        script=(
            "```python\n"
            "from manim import Scene\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        pass\n"
            "```\n"
        )
    )
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="fenced")

    app_context.worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert snapshot.status == "completed"


def test_task_fails_before_render_when_mathtex_dependencies_are_missing(tmp_path: Path) -> None:
    settings = _build_fake_pipeline_settings(tmp_path)
    settings.latex_command = "missing-latex"
    settings.dvisvgm_command = "missing-dvisvgm"
    app_context = create_app_context(settings)
    app_context.workflow_engine.llm_client = StubLLMClient(
        script=(
            "from manim import MathTex, Scene\n\n"
            "class GeneratedScene(Scene):\n"
            "    def construct(self):\n"
            "        self.add(MathTex(r'x^2 + y^2 = z^2'))\n"
        )
    )
    created = app_context.task_service.create_video_task(prompt="show a formula", idempotency_key="mathtex-missing")

    app_context.worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert snapshot.status == "failed"
    assert snapshot.latest_validation_summary["issues"][0]["code"] == "latex_dependency_missing"
    assert snapshot.latest_validation_summary["details"]["missing_checks"] == ["latex", "dvisvgm"]
    assert app_context.metrics.counters.get("render_runs", 0) == 0
