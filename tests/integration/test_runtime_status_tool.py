from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_runtime_status_tool


def test_runtime_status_tool_reports_binary_and_provider_state(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    settings = Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        manim_command="manim",
        ffmpeg_command="ffmpeg",
        ffprobe_command="ffprobe",
        llm_provider="stub",
        run_embedded_worker=False,
    )
    context = create_app_context(settings)

    payload = get_runtime_status_tool(context, {})

    assert payload["provider"]["mode"] == "stub"
    assert payload["storage"]["data_dir"].endswith("data")
    assert set(payload["checks"]).issuperset({"manim", "ffmpeg", "ffprobe"})
    assert payload["worker"]["embedded"] is False
    assert payload["release"]["version"]
    assert payload["release"]["channel"] == "beta"
