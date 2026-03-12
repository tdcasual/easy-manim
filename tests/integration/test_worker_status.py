from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_runtime_status_tool


def test_runtime_status_includes_recent_worker_heartbeat(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data", run_embedded_worker=False)
    context = create_app_context(settings)

    processed = context.worker.run_once()
    payload = get_runtime_status_tool(context, {})

    assert processed == 0
    assert payload["worker"]["workers"]
    assert payload["worker"]["workers"][0]["stale"] is False
