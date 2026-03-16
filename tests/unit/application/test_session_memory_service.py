from video_agent.application.session_memory_service import SessionMemoryService
from video_agent.domain.models import VideoTask
from video_agent.server.session_memory import SessionMemoryRegistry


def test_create_task_is_recorded_but_not_injected_into_its_own_context() -> None:
    registry = SessionMemoryRegistry()
    session = registry.ensure_session("session-a", agent_id="agent-a")
    service = SessionMemoryService(registry=registry)
    task = VideoTask(prompt="draw a circle", session_id=session.session_id)

    service.record_task_created(task, attempt_kind="create")
    summary = service.summarize_session_memory(session.session_id)

    assert summary.entry_count == 1
    assert task.memory_context_summary is None


def test_summary_is_available_for_followup_attempts() -> None:
    registry = SessionMemoryRegistry()
    session = registry.ensure_session("session-a", agent_id="agent-a")
    service = SessionMemoryService(registry=registry)
    root = VideoTask(prompt="draw a circle", session_id=session.session_id)

    service.record_task_created(root, attempt_kind="create")
    summary = service.summarize_session_memory(session.session_id)

    assert "draw a circle" in summary.summary_text
    assert summary.summary_digest is not None
