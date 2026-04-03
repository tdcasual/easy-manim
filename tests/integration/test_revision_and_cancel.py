import json
from pathlib import Path

import pytest

from video_agent.adapters.llm.client import StubLLMClient
from video_agent.config import Settings
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.server.app import create_app_context
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
        "mkdir -p \"$2\"\n"
        "printf 'normal-video' > \"$2/final_video.mp4\"\n",
    )

    fake_ffprobe = tmp_path / "fake_ffprobe.sh"
    probe_json = json.dumps(
        {
            "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
            "format": {"duration": "2.5"},
        }
    )
    _write_executable(fake_ffprobe, f"#!/bin/sh\nprintf '%s' '{probe_json}'\n")

    fake_ffmpeg = tmp_path / "fake_ffmpeg.sh"
    _write_executable(
        fake_ffmpeg,
        "#!/bin/sh\n"
        "mkdir -p \"$2\"\n"
        "printf 'frame1' > \"$2/frame_001.png\"\n",
    )

    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            manim_command=str(fake_manim),
            ffmpeg_command=str(fake_ffmpeg),
            ffprobe_command=str(fake_ffprobe),
        )
    )


def _seed_agent_memory(
    app_context,
    *,
    memory_id: str,
    agent_id: str,
    status: str = "active",
    summary_text: str | None = None,
) -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id=memory_id,
            agent_id=agent_id,
            source_session_id=f"session-{agent_id}",
            status=status,
            summary_text=summary_text or f"Remember {agent_id}",
            summary_digest=f"digest-{memory_id}",
        )
    )


class CapturingLLMClient(StubLLMClient):
    def __init__(self) -> None:
        super().__init__()
        self.last_prompt: str | None = None

    def generate_script(self, prompt_text: str) -> str:
        self.last_prompt = prompt_text
        return super().generate_script(prompt_text)



def test_revise_task_creates_child_task(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    parent = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="parent")
    child = app_context.task_service.revise_video_task(parent.task_id, feedback="make it blue")
    snapshot = app_context.task_service.get_video_task(child.task_id)

    assert snapshot.parent_task_id == parent.task_id
    assert snapshot.root_task_id == parent.task_id
    assert snapshot.status == "queued"



def test_revision_inherits_parent_context(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    completed = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="complete-parent")
    app_context.worker.run_once()

    child = app_context.task_service.revise_video_task(completed.task_id, feedback="add title")
    snapshot = app_context.task_service.get_video_task(child.task_id)
    assert snapshot.inherited_from_task_id == completed.task_id


def test_revision_inherits_parent_session_id(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )

    child = app_context.task_service.revise_video_task(created.task_id, feedback="add labels")
    task = app_context.store.get_task(child.task_id)

    assert task is not None
    assert task.session_id == "session-1"


def test_revision_can_attach_persistent_memory_ids(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", session_id="session-1")
    _seed_agent_memory(app_context, memory_id="mem-a", agent_id="local-anonymous")

    child = app_context.task_service.revise_video_task(
        created.task_id,
        feedback="add labels",
        session_id="session-1",
        memory_ids=["mem-a"],
    )
    task = app_context.store.get_task(child.task_id)

    assert task is not None
    assert task.selected_memory_ids == ["mem-a"]


def test_revision_child_receives_memory_context_summary(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )

    child = app_context.task_service.revise_video_task(created.task_id, feedback="add title")
    stored = app_context.store.get_task(child.task_id)

    assert stored is not None
    assert stored.memory_context_summary is not None
    assert stored.memory_context_digest is not None


def test_revision_reuses_session_memory_after_app_restart(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )

    restarted = create_app_context(_build_fake_pipeline_settings(tmp_path))

    child = restarted.task_service.revise_video_task(created.task_id, feedback="add title")
    stored = restarted.store.get_task(child.task_id)

    assert stored is not None
    assert stored.memory_context_summary is not None
    assert "draw a circle" in stored.memory_context_summary


def test_revision_prompt_separates_session_and_persistent_memory_contexts(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    app_context.workflow_engine.llm_client = CapturingLLMClient()
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )
    _seed_agent_memory(app_context, memory_id="mem-a", agent_id="local-anonymous")

    child = app_context.task_service.revise_video_task(
        created.task_id,
        feedback="add title",
        session_id="session-1",
        memory_ids=["mem-a"],
    )
    app_context.worker.run_once()
    app_context.worker.run_once()

    prompt = app_context.workflow_engine.llm_client.last_prompt

    assert child.task_id
    assert prompt is not None
    assert "Session memory context:" in prompt
    assert "Persistent memory context:" in prompt


def test_owner_revision_inherits_root_workflow_pinned_memory_when_memory_ids_omitted(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )
    _seed_agent_memory(
        app_context,
        memory_id="mem-a",
        agent_id="local-anonymous",
        summary_text="Prefer high-contrast diagrams and concise labels.",
    )
    app_context.workflow_collaboration_service.pin_workflow_memory(
        created.task_id,
        memory_id="mem-a",
    )

    child = app_context.task_service.revise_video_task(
        created.task_id,
        feedback="add labels",
        session_id="session-1",
    )
    task = app_context.store.get_task(child.task_id)

    assert task is not None
    assert task.selected_memory_ids == ["mem-a"]
    assert "high-contrast diagrams" in (task.persistent_memory_context_summary or "")


def test_owner_revision_can_explicitly_clear_root_workflow_pinned_memory(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-1",
    )
    _seed_agent_memory(
        app_context,
        memory_id="mem-a",
        agent_id="local-anonymous",
        summary_text="Prefer high-contrast diagrams and concise labels.",
    )
    app_context.workflow_collaboration_service.pin_workflow_memory(
        created.task_id,
        memory_id="mem-a",
    )

    child = app_context.task_service.revise_video_task(
        created.task_id,
        feedback="add labels",
        session_id="session-1",
        memory_ids=[],
    )
    task = app_context.store.get_task(child.task_id)

    assert task is not None
    assert task.selected_memory_ids == []
    assert task.persistent_memory_context_summary is None



def test_cancel_task_marks_queued_task_as_cancelled(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="cancel-q")
    app_context.task_service.cancel_video_task(created.task_id)
    snapshot = app_context.task_service.get_video_task(created.task_id)
    assert snapshot.status == "cancelled"



def test_worker_stops_processing_cancelled_task(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="cancel-r")
    app_context.task_service.cancel_video_task(created.task_id)
    processed = app_context.worker.run_once()
    assert processed == 0


def test_auto_repair_task_requires_failed_parent(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="auto-repair-parent")

    with pytest.raises(ValueError, match="failed parent"):
        app_context.task_service.create_auto_repair_task(created.task_id, feedback="fix render failure")


def test_auto_repair_task_records_targeted_repair_metadata(tmp_path: Path) -> None:
    app_context = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="auto-repair-meta")
    parent_task = app_context.store.get_task(created.task_id)
    assert parent_task is not None
    parent_task.status = TaskStatus.FAILED
    parent_task.phase = TaskPhase.FAILED
    app_context.store.update_task(parent_task)

    child = app_context.task_service.create_auto_repair_task(created.task_id, feedback="fix render failure")
    events = app_context.task_service.get_task_events(child.task_id)
    creation_events = [item for item in events if item["event_type"] == "auto_repair_created"]

    assert len(creation_events) == 1
    assert creation_events[0]["payload"]["revision_mode"] == "targeted_repair"
    assert creation_events[0]["payload"]["preserve_working_parts"] is True
    assert creation_events[0]["payload"]["source_task_id"] == created.task_id
