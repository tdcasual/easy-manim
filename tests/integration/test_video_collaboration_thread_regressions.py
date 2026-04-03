from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


def _build_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
            multi_agent_workflow_enabled=True,
        )
    )


def test_video_collaboration_regression_removes_internal_discussion_service_methods(
    tmp_path: Path,
) -> None:
    app_context = create_app_context(_build_settings(tmp_path))

    assert not hasattr(app_context.multi_agent_workflow_service, "create_discussion_message")
    assert not hasattr(app_context.multi_agent_workflow_service, "get_video_discussion_surface")
    assert not hasattr(app_context.workflow_collaboration_service, "add_discussion_message")
    assert not hasattr(app_context.workflow_collaboration_service, "add_agent_discussion_reply")
    assert not hasattr(app_context.workflow_collaboration_service, "list_discussion_events")
