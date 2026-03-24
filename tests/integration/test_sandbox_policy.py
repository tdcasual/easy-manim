import json
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_runtime_status_tool
from tests.support import bootstrapped_settings


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _settings(tmp_path: Path, **overrides) -> Settings:
    data_dir = tmp_path / "data"

    fake_manim = tmp_path / "fake_manim.sh"
    _write_executable(
        fake_manim,
        "#!/bin/sh\n"
        "mkdir -p \"$5/videos/demo/480p15\"\n"
        "printf 'fake-video' > \"$5/videos/demo/480p15/$7\"\n",
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

    values = {
        "data_dir": data_dir,
        "database_path": data_dir / "video_agent.db",
        "artifact_root": data_dir / "tasks",
        "manim_command": str(fake_manim),
        "ffmpeg_command": str(fake_ffmpeg),
        "ffprobe_command": str(fake_ffprobe),
        "run_embedded_worker": False,
        "sandbox_network_disabled": True,
        "sandbox_process_limit": 1,
        "sandbox_memory_limit_mb": 256,
    }
    values.update(overrides)
    return bootstrapped_settings(Settings(**values))


def test_runtime_status_reports_sandbox_configuration(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    app = create_app_context(settings)

    payload = get_runtime_status_tool(app, {})

    assert payload["sandbox"]["network_disabled"] is True
    assert payload["sandbox"]["process_limit"] == 1
    assert payload["sandbox"]["memory_limit_mb"] == 256
    assert payload["sandbox"]["temp_root_allowed"] is True
    assert payload["sandbox"]["temp_root"].endswith(".sandbox/tmp")


def test_invalid_sandbox_temp_root_fails_task_and_writes_failure_context(tmp_path: Path) -> None:
    app = create_app_context(
        _settings(
            tmp_path,
            sandbox_temp_root=tmp_path.parent / "escape-tmp",
        )
    )
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()
    snapshot = app.task_service.get_video_task(created.task_id)
    failure_context_path = app.artifact_store.task_dir(created.task_id) / "artifacts" / "failure_context.json"
    payload = json.loads(failure_context_path.read_text())

    assert snapshot.status == "failed"
    assert snapshot.latest_validation_summary["issues"][0]["code"] == "sandbox_policy_violation"
    assert payload["failure_code"] == "sandbox_policy_violation"
    assert payload["sandbox_policy"]["code"] == "sandbox_temp_root_outside_work_root"
