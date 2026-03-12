from video_agent.server.mcp_tools import create_video_task_tool, get_video_task_tool
from video_agent.server.app import create_app_context



def test_create_video_task_tool_returns_task_id(temp_settings) -> None:
    app_context = create_app_context(temp_settings)
    payload = create_video_task_tool(app_context, {"prompt": "draw a circle"})
    assert payload["task_id"]
    assert payload["status"] == "queued"



def test_get_video_task_tool_returns_snapshot(temp_settings) -> None:
    app_context = create_app_context(temp_settings)
    created = create_video_task_tool(app_context, {"prompt": "draw a circle"})
    snapshot = get_video_task_tool(app_context, {"task_id": created["task_id"]})
    assert snapshot["task_id"] == created["task_id"]
