from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_task_events_tool, list_video_tasks_tool



def test_list_video_tasks_tool_returns_created_tasks(temp_settings) -> None:
    app = create_app_context(temp_settings)
    app.task_service.create_video_task(prompt="one", idempotency_key="one")

    payload = list_video_tasks_tool(app, {"limit": 10})

    assert payload["items"]
    assert payload["next_cursor"] is None



def test_get_task_events_tool_returns_event_items(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="one", idempotency_key="events")

    payload = get_task_events_tool(app, {"task_id": created.task_id})

    assert payload["items"][0]["event_type"] == "task_created"
