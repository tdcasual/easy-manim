import json
from pathlib import Path

import pytest

from video_agent.config import Settings
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
        "mkdir -p \"$2\"\n"
        "printf 'normal-video' > \"$2/final_video.mp4\"\n",
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
    )



def test_revise_task_creates_child_task(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    parent = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="parent")
    child = app_context.task_service.revise_video_task(parent.task_id, feedback="make it blue")
    snapshot = app_context.task_service.get_video_task(child.task_id)

    assert snapshot.parent_task_id == parent.task_id
    assert snapshot.root_task_id == parent.task_id
    assert snapshot.status == "queued"



def test_revision_inherits_parent_context(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    completed = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="complete-parent")
    app_context.worker.run_once()

    child = app_context.task_service.revise_video_task(completed.task_id, feedback="add title")
    snapshot = app_context.task_service.get_video_task(child.task_id)
    assert snapshot.inherited_from_task_id == completed.task_id



def test_cancel_task_marks_queued_task_as_cancelled(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="cancel-q")
    app_context.task_service.cancel_video_task(created.task_id)
    snapshot = app_context.task_service.get_video_task(created.task_id)
    assert snapshot.status == "cancelled"



def test_worker_stops_processing_cancelled_task(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="cancel-r")
    app_context.task_service.cancel_video_task(created.task_id)
    processed = app_context.worker.run_once()
    assert processed == 0


def test_auto_repair_task_requires_failed_parent(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="auto-repair-parent")

    with pytest.raises(ValueError, match="failed parent"):
        app_context.task_service.create_auto_repair_task(created.task_id, feedback="fix render failure")
