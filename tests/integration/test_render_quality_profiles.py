from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_settings(tmp_path: Path) -> tuple[Settings, Path]:
    data_dir = tmp_path / "data"
    invocation_log = tmp_path / "manim_invocation.log"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$@\" > \"{invocation_log}\"\n"
        "if [ \"$1\" != \"-qh\" ]; then exit 11; fi\n"
        "if [ \"$4\" != \"--media_dir\" ]; then exit 12; fi\n"
        "if [ \"$6\" != \"-o\" ]; then exit 13; fi\n"
        "script_name=$(basename \"$2\" .py)\n"
        "mkdir -p \"$5/videos/$script_name/1080p60\"\n"
        "printf 'normal-video' > \"$5/videos/$script_name/1080p60/$7\"\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    _write_executable(
        fake_ffprobe,
        "#!/bin/sh\n"
        "printf '%s' '{\"streams\": [{\"codec_type\": \"video\", \"width\": 1920, \"height\": 1080}], \"format\": {\"duration\": \"6.0\"}}'\n",
    )

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "mkdir -p \"$(dirname \"$6\")\"\n"
        "printf 'frame1' > \"$(dirname \"$6\")/frame_001.png\"\n",
    )

    settings = bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
        )
    )
    return settings, invocation_log


def test_output_profile_can_request_production_quality_render(tmp_path: Path) -> None:
    settings, invocation_log = _build_settings(tmp_path)
    app = create_app_context(settings)
    created = app.task_service.create_video_task(
        prompt="draw a blue circle",
        output_profile={"quality_preset": "production"},
    )

    app.worker.run_once()

    snapshot = app.task_service.get_video_task(created.task_id)
    assert snapshot.status == "completed"
    assert "-qh" in invocation_log.read_text()
