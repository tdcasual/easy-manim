import json
import os
import subprocess
import sys
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_runtime_status_tool
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
            eval_root=data_dir / "evals",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
            run_embedded_worker=False,
        )
    )


def _build_fake_pipeline_env(tmp_path: Path, data_dir: Path) -> dict[str, str]:
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

    SQLiteBootstrapper(data_dir / "video_agent.db").bootstrap()
    env = dict(os.environ)
    pythonpath = str(Path.cwd() / "src")
    if env.get("PYTHONPATH"):
        pythonpath = f"{pythonpath}:{env['PYTHONPATH']}"
    env.update(
        {
            "PYTHONPATH": pythonpath,
            "EASY_MANIM_MANIM_COMMAND": str(fake_manim),
            "EASY_MANIM_FFMPEG_COMMAND": str(fake_ffmpeg),
            "EASY_MANIM_FFPROBE_COMMAND": str(fake_ffprobe),
            "EASY_MANIM_LLM_PROVIDER": "stub",
            "EASY_MANIM_CAPABILITY_ROLLOUT_PROFILE": "supervised",
        }
    )
    return env


def test_delivery_canary_runs_minimal_task_and_updates_runtime_visibility(tmp_path: Path) -> None:
    from video_agent.application.delivery_canary_service import DeliveryCanaryService

    context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    service = DeliveryCanaryService(
        settings=context.settings,
        store=context.store,
        artifact_store=context.artifact_store,
        task_service=context.task_service,
        worker=context.worker,
    )

    payload = service.run()
    runtime_status = get_runtime_status_tool(context, {})

    assert payload["mode"] == "single-branch"
    assert payload["delivered"] is True
    assert payload["completion_mode"] == "primary"
    assert payload["processed_iterations"] >= 1
    assert payload["run_duration_seconds"] >= 0.0
    assert payload["video_metadata"]["duration_seconds"] == 2.5
    assert payload["artifact_size_bytes"] > 0
    assert runtime_status["delivery_canary"]["available"] is True
    assert runtime_status["delivery_canary"]["last_run"]["task_id"] == payload["task_id"]
    assert runtime_status["delivery_canary"]["last_run"]["mode"] == "single-branch"
    assert runtime_status["delivery_canary"]["last_run"]["delivered"] is True


def test_delivery_canary_runs_native_multi_agent_mode_and_records_arbitration(tmp_path: Path) -> None:
    from video_agent.application.delivery_canary_service import DeliveryCanaryService

    context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    service = DeliveryCanaryService(
        settings=context.settings,
        store=context.store,
        artifact_store=context.artifact_store,
        task_service=context.task_service,
        worker=context.worker,
    )

    payload = service.run(mode="native-multi-agent")
    runtime_status = get_runtime_status_tool(context, {})

    assert payload["mode"] == "native-multi-agent"
    assert payload["delivered"] is True
    assert payload["challenger_created"] is True
    assert payload["arbitration_evaluated"] is True
    assert payload["arbitration_promoted"] is True
    assert payload["lineage_count"] == 2
    assert payload["challenger_task_id"] is not None
    assert payload["resolved_task_id"] == payload["challenger_task_id"]
    assert payload["case_status"] == "completed"
    assert payload["branch_scoreboard"] is not None
    assert runtime_status["delivery_canary"]["last_run"]["mode"] == "native-multi-agent"
    assert runtime_status["delivery_canary"]["last_run"]["challenger_created"] is True


def test_native_multi_agent_delivery_canary_reports_blocked_when_workflow_disabled(tmp_path: Path) -> None:
    from video_agent.application.delivery_canary_service import DeliveryCanaryService

    settings = _build_fake_pipeline_settings(tmp_path)
    settings.multi_agent_workflow_enabled = False
    context = create_app_context(settings)
    service = DeliveryCanaryService(
        settings=context.settings,
        store=context.store,
        artifact_store=context.artifact_store,
        task_service=context.task_service,
        worker=context.worker,
    )

    payload = service.run(mode="native-multi-agent")

    assert payload["mode"] == "native-multi-agent"
    assert payload["delivered"] is False
    assert payload["status"] == "blocked"
    assert payload["stop_reason"] == "multi_agent_workflow_disabled"
    assert payload["challenger_created"] is False
    assert payload["arbitration_evaluated"] is False


def test_delivery_canary_cli_outputs_json(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    env = _build_fake_pipeline_env(tmp_path, data_dir)

    completed = subprocess.run(
        [sys.executable, "-m", "video_agent.eval.canary", "--data-dir", str(data_dir), "--json"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["mode"] == "single-branch"
    assert payload["delivered"] is True
    assert payload["completion_mode"] == "primary"
    assert payload["run_duration_seconds"] >= 0.0
    assert payload["video_metadata"]["duration_seconds"] == 2.5


def test_delivery_canary_cli_supports_native_multi_agent_mode(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    env = _build_fake_pipeline_env(tmp_path, data_dir)

    completed = subprocess.run(
        [sys.executable, "-m", "video_agent.eval.canary", "--data-dir", str(data_dir), "--mode", "native-multi-agent", "--json"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["mode"] == "native-multi-agent"
    assert payload["delivered"] is True
    assert payload["challenger_created"] is True
    assert payload["arbitration_promoted"] is True
