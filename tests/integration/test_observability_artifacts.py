import json
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_metrics_snapshot_tool



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



def test_task_log_events_are_written_to_jsonl(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    log_path = app.artifact_store.task_dir(created.task_id) / "logs" / "events.jsonl"
    assert log_path.exists()
    assert '"phase": "rendering"' in log_path.read_text()



def test_metrics_snapshot_tool_returns_current_counters(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    payload = get_metrics_snapshot_tool(app, {})

    assert payload["counters"]["render_runs"] == 1
    assert len(payload["timings"]["render_seconds"]) == 1
    assert created.task_id
