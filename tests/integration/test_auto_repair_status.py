import json
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_auto_repair_settings(tmp_path: Path) -> Settings:
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

    return Settings(
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


def test_get_video_task_exposes_auto_repair_summary(tmp_path: Path) -> None:
    app = create_app_context(_build_auto_repair_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    app.worker.run_once()

    snapshot = app.task_service.get_video_task(created.task_id)

    assert snapshot.artifact_summary["repair_children"] == 1
    assert snapshot.latest_validation_summary
    assert snapshot.repair_state["attempted"] is True
    assert snapshot.repair_state["child_count"] == 1
    assert snapshot.repair_state["last_issue_code"] == "render_failed"
    assert snapshot.repair_state["stop_reason"] == "budget_exhausted"
    assert snapshot.auto_repair_summary["enabled"] is True
    assert snapshot.auto_repair_summary["remaining_budget"] == 0
    assert snapshot.auto_repair_summary["stopped_reason"] == "budget_exhausted"
