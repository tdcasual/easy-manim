from pathlib import Path
from types import SimpleNamespace

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.application.auto_repair_service import AutoRepairService
from video_agent.config import Settings
from video_agent.domain.models import VideoTask


class _UnusedStore:
    pass


def test_auto_repair_feedback_uses_structured_task_session_memory_when_live_service_is_unavailable(tmp_path: Path) -> None:
    artifact_store = ArtifactStore(tmp_path / "tasks", eval_root=tmp_path / "evals")
    service = AutoRepairService(
        store=_UnusedStore(),
        artifact_store=artifact_store,
        settings=Settings(),
        task_service=SimpleNamespace(session_memory_service=None),
    )
    task = VideoTask(
        task_id="task-1",
        root_task_id="task-1",
        prompt="draw a circle",
        task_memory_context={
            "session": {
                "session_id": "session-1",
                "summary_text": "Earlier attempts already established a working light-background layout.",
                "summary_digest": "digest-session",
                "entry_count": 1,
                "entries": [],
            }
        },
    )

    feedback = service._build_feedback(task, "render_failed")

    assert "Session memory context:" in feedback
    assert "working light-background layout" in feedback
