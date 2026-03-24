import json
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_fake_pipeline_settings(
    tmp_path: Path,
    *,
    video_bytes: bytes = b"normal-video",
    width: int = 1280,
    height: int = 720,
    duration_seconds: float = 2.5,
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
        f"printf '%s' '{video_bytes.decode('utf-8')}' > \"$5/videos/$script_name/480p15/$7\"\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    probe_json = json.dumps(
        {
            "streams": [{"codec_type": "video", "width": width, "height": height}],
            "format": {"duration": str(duration_seconds)},
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
        )
    )


def test_validation_profile_can_raise_minimum_duration_threshold(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path, duration_seconds=2.5))
    created = app.task_service.create_video_task(
        prompt="draw a circle",
        validation_profile={"min_duration_seconds": 5.0},
    )

    app.worker.run_once()
    snapshot = app.task_service.get_video_task(created.task_id)

    assert snapshot.status == "failed"
    assert snapshot.latest_validation_summary["issues"][0]["code"] == "min_duration_not_met"


def test_validation_profile_can_disable_black_frame_rule(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path, video_bytes=b"black-video"))
    created = app.task_service.create_video_task(
        prompt="draw a circle",
        validation_profile={"check_black_frames": False},
    )

    app.worker.run_once()
    snapshot = app.task_service.get_video_task(created.task_id)

    assert snapshot.status == "completed"
