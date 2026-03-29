import json
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _build_fake_pipeline_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
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
    _write_executable(fake_ffprobe, f"#!/bin/sh\nprintf '%s' '{probe_json}'\n")

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
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
        )
    )


def _build_preview_failure_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
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
    _write_executable(fake_ffprobe, f"#!/bin/sh\nprintf '%s' '{probe_json}'\n")

    fake_ffmpeg = tmp_path / "fake_ffmpeg_blank.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "python - \"$6\" <<'PY'\n"
        "from pathlib import Path\n"
        "from PIL import Image\n"
        "import sys\n"
        "pattern = Path(sys.argv[1])\n"
        "pattern.parent.mkdir(parents=True, exist_ok=True)\n"
        "for index in (1, 2):\n"
        "    Image.new('RGB', (320, 180), (0, 0, 0)).save(pattern.parent / f'frame_{index:03d}.png')\n"
        "PY\n",
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
        )
    )


def test_workflow_persists_scene_spec_and_quality_score(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a blue circle", session_id="session-1")

    app.worker.run_once()

    assert app.artifact_store.read_scene_spec(created.task_id) is not None
    assert app.artifact_store.read_quality_score(created.task_id) is not None


def test_workflow_writes_recovery_plan_when_preview_validation_fails(tmp_path: Path) -> None:
    app = create_app_context(_build_preview_failure_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    recovery_plan = app.artifact_store.read_recovery_plan(created.task_id)
    assert recovery_plan is not None
    assert recovery_plan["selected_action"] == "preview_repair"


def test_workflow_persists_structured_risk_and_gate_signals(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(
        prompt="draw a blue circle",
        style_hints={"scene_complexity": "high", "animation_density": "high"},
    )

    app.worker.run_once()

    snapshot = app.task_service.get_video_task(created.task_id)
    scene_spec = app.artifact_store.read_scene_spec(created.task_id)
    assert snapshot.risk_level == "high"
    assert scene_spec is not None
    assert scene_spec["requested_scene_complexity"] == "high"
    assert "requested_scene_complexity:high" in scene_spec["risk_signals"]
    assert scene_spec["capability_gate"] == {"allowed": True}


def test_workflow_persists_second_stage_structured_risk_classification(tmp_path: Path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(
        prompt="show a sine wave and clearly label its amplitude",
        style_hints={},
    )

    app.worker.run_once()

    snapshot = app.task_service.get_video_task(created.task_id)
    scene_spec = app.artifact_store.read_scene_spec(created.task_id)
    assert scene_spec is not None
    assert scene_spec["animation_density"] == "high"
    assert scene_spec["generation_mode"] == "template_first"
    assert "animation_density:high" in scene_spec["risk_signals"]
    assert snapshot.risk_level == "high"
    assert snapshot.generation_mode == "template_first"
