from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_runtime_status_tool


def _write_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)


def test_runtime_status_tool_reports_binary_and_provider_state(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    fake_latex = tmp_path / "fake_latex.sh"
    fake_dvisvgm = tmp_path / "fake_dvisvgm.sh"
    _write_executable(fake_latex)
    _write_executable(fake_dvisvgm)
    settings = Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        manim_command="manim",
        ffmpeg_command="ffmpeg",
        ffprobe_command="ffprobe",
        latex_command=str(fake_latex),
        dvisvgm_command=str(fake_dvisvgm),
        llm_provider="stub",
        run_embedded_worker=False,
    )
    SQLiteBootstrapper(settings.database_path).bootstrap()
    context = create_app_context(settings)

    payload = get_runtime_status_tool(context, {})

    assert payload["provider"]["mode"] == "stub"
    assert payload["provider"]["api_base_present"] is False
    assert payload["storage"]["data_dir"].endswith("data")
    assert set(payload["checks"]).issuperset({"manim", "ffmpeg", "ffprobe", "latex", "dvisvgm"})
    assert payload["features"]["mathtex"]["available"] is True
    assert payload["features"]["mathtex"]["checked"] is False
    assert payload["features"]["mathtex"]["missing_checks"] == []
    assert payload["features"]["mathtex"]["smoke_error"] is None
    assert payload["worker"]["embedded"] is False
    assert payload["sandbox"]["network_disabled"] is False
    assert payload["sandbox"]["temp_root_allowed"] is True
    assert payload["sandbox"]["process_limit"] is None
    assert payload["sandbox"]["memory_limit_mb"] is None
    assert payload["release"]["version"]
    assert payload["release"]["channel"] == "beta"
