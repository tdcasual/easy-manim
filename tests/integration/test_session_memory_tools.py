from pathlib import Path

import pytest

from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import clear_session_memory_tool, get_session_memory_tool, summarize_session_memory_tool


@pytest.fixture
def app_context(temp_settings):
    return create_app_context(temp_settings)


def test_get_session_memory_returns_stable_empty_payload(app_context) -> None:
    payload = get_session_memory_tool(app_context, {}, session_id="session-1")

    assert payload["session_id"] == "session-1"
    assert payload["entries"] == []
    assert payload["entry_count"] == 0


def test_clear_session_memory_only_clears_target_session(app_context) -> None:
    app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-a")
    app_context.task_service.create_video_task(prompt="draw a square", session_id="session-b")

    cleared = clear_session_memory_tool(app_context, {}, session_id="session-a")
    memory_a = get_session_memory_tool(app_context, {}, session_id="session-a")
    memory_b = get_session_memory_tool(app_context, {}, session_id="session-b")

    assert cleared["cleared"] is True
    assert cleared["cleared_attempt_count"] == 1
    assert memory_a["entry_count"] == 0
    assert memory_b["entry_count"] == 1


def test_summarize_session_memory_returns_lineage_refs(app_context) -> None:
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-a")

    payload = summarize_session_memory_tool(app_context, {}, session_id="session-a")

    assert payload["lineage_refs"] == [f"video-task://{created.task_id}/task.json"]
