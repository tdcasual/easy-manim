import importlib
import importlib.util
from types import SimpleNamespace

import pytest

from video_agent.application.task_service import CreateVideoTaskResult
from video_agent.application.persistent_memory_service import PersistentMemoryContext
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask


MODULE_NAME = "video_agent.application.task_service_child_tasks"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


class _FakeRevisionService:
    def __init__(self) -> None:
        self.metadata_calls: list[dict[str, object]] = []
        self.revision_calls: list[dict[str, object]] = []

    def build_metadata(self, base_task: VideoTask, *, revision_mode: str, preserve_working_parts: bool) -> dict[str, object]:
        self.metadata_calls.append(
            {
                "task_id": base_task.task_id,
                "revision_mode": revision_mode,
                "preserve_working_parts": preserve_working_parts,
            }
        )
        return {
            "revision_mode": revision_mode,
            "preserve_working_parts": preserve_working_parts,
            "source_task_id": base_task.task_id,
        }

    def create_revision(self, *, base_task: VideoTask, feedback: str, preserve_working_parts: bool) -> VideoTask:
        self.revision_calls.append(
            {
                "task_id": base_task.task_id,
                "feedback": feedback,
                "preserve_working_parts": preserve_working_parts,
            }
        )
        child = VideoTask.from_revision(
            base_task,
            feedback=feedback,
            preserve_working_parts=preserve_working_parts,
        )
        child.task_id = "child-generated"
        return child


class _FakeStore:
    def __init__(self) -> None:
        self.created_tasks: list[VideoTask] = []
        self.events: list[tuple[str, str, dict[str, object]]] = []

    def create_task(self, task: VideoTask) -> VideoTask:
        self.created_tasks.append(task.model_copy(deep=True))
        return task

    def append_event(self, task_id: str, event_type: str, payload: dict[str, object]) -> None:
        self.events.append((task_id, event_type, dict(payload)))


class _FakeArtifactStore:
    def __init__(self) -> None:
        self.ensured_task_ids: list[str] = []
        self.snapshots: list[VideoTask] = []

    def ensure_task_dirs(self, task_id: str) -> None:
        self.ensured_task_ids.append(task_id)

    def write_task_snapshot(self, task: VideoTask) -> None:
        self.snapshots.append(task.model_copy(deep=True))


class _FakeDeliveryCaseService:
    def __init__(self) -> None:
        self.ensured_task_ids: list[str] = []
        self.queued_task_ids: list[str] = []
        self.synced_root_ids: list[str] = []
        self.branch_spawns: list[tuple[str, str]] = []

    def ensure_case_for_task(self, task: VideoTask):
        self.ensured_task_ids.append(task.task_id)
        return None, False

    def queue_generator_run(self, *, task: VideoTask) -> None:
        self.queued_task_ids.append(task.task_id)

    def sync_case_for_root(self, root_task_id: str) -> None:
        self.synced_root_ids.append(root_task_id)

    def record_branch_spawned(self, *, incumbent_task: VideoTask, challenger_task: VideoTask) -> None:
        self.branch_spawns.append((incumbent_task.task_id, challenger_task.task_id))


class _FakeSessionMemoryService:
    def __init__(self) -> None:
        self.summaries: dict[str, object] = {}
        self.recorded: list[tuple[str, str]] = []

    def summarize_session_memory(self, session_id: str):
        return self.summaries.get(
            session_id,
            SimpleNamespace(summary_text=None, summary_digest=None),
        )

    def record_task_created(self, task: VideoTask, attempt_kind: str) -> None:
        self.recorded.append((task.task_id, attempt_kind))


def _task(
    *,
    task_id: str = "task-1",
    root_task_id: str = "task-1",
    parent_task_id: str | None = None,
    status: TaskStatus = TaskStatus.QUEUED,
    phase: TaskPhase = TaskPhase.QUEUED,
    delivery_status: str | None = "pending",
    session_id: str | None = "session-base",
    result_id: str | None = "result-1",
) -> VideoTask:
    return VideoTask(
        task_id=task_id,
        root_task_id=root_task_id,
        parent_task_id=parent_task_id,
        status=status,
        phase=phase,
        prompt="Draw a clear geometry explainer",
        delivery_status=delivery_status,
        session_id=session_id,
        result_id=result_id,
        thread_id="thread-1",
        iteration_id="iter-1",
        execution_kind="workflow",
        target_participant_id="participant-1",
        target_agent_id="agent-1",
        target_agent_role="planner",
        display_title="Geometry explainer",
        title_source="prompt",
    )


def test_inherit_persistent_memory_context_returns_none_when_task_has_no_persistent_memory() -> None:
    module = _load_module()

    assert module.inherit_persistent_memory_context(_task()) is None


def test_inherit_persistent_memory_context_clones_memory_fields() -> None:
    module = _load_module()
    base_task = _task(session_id=None)
    base_task.selected_memory_ids = ["mem-a"]
    base_task.persistent_memory_context_summary = "Keep labels concise."
    base_task.persistent_memory_context_digest = "digest-a"

    inherited = module.inherit_persistent_memory_context(base_task)

    assert inherited == PersistentMemoryContext(
        memory_ids=["mem-a"],
        summary_text="Keep labels concise.",
        summary_digest="digest-a",
        items=[
            {
                "memory_id": "mem-a",
                "summary_text": "Keep labels concise.",
                "summary_digest": "digest-a",
                "lineage_refs": [],
                "enhancement": {},
            }
        ],
    )
    assert inherited is not None
    assert inherited.memory_ids is not base_task.selected_memory_ids


def test_inherit_persistent_memory_context_prefers_structured_task_memory_context_when_legacy_fields_are_empty() -> None:
    module = _load_module()
    base_task = _task(session_id=None)
    base_task.task_memory_context = {
        "persistent": {
            "memory_ids": ["mem-a"],
            "summary_text": "Keep labels concise.",
            "summary_digest": "digest-a",
            "items": [
                {
                    "memory_id": "mem-a",
                    "summary_text": "Keep labels concise.",
                    "summary_digest": "digest-a",
                    "lineage_refs": ["video-task://task-root/task.json"],
                    "enhancement": {},
                }
            ],
        }
    }

    inherited = module.inherit_persistent_memory_context(base_task)

    assert inherited == PersistentMemoryContext(
        memory_ids=["mem-a"],
        summary_text="Keep labels concise.",
        summary_digest="digest-a",
        items=[
            {
                "memory_id": "mem-a",
                "summary_text": "Keep labels concise.",
                "summary_digest": "digest-a",
                "lineage_refs": ["video-task://task-root/task.json"],
                "enhancement": {},
            }
        ],
    )


def test_create_challenger_child_task_rejects_non_delivered_parent() -> None:
    module = _load_module()
    with pytest.raises(ValueError, match="completed delivered parent"):
        module.create_challenger_child_task(
            base_task=_task(status=TaskStatus.FAILED, phase=TaskPhase.FAILED, delivery_status="failed"),
            feedback="Push quality further",
            session_id=None,
            persistent_memory=None,
            is_completed_delivery_candidate=lambda task: False,
            enforce_attempt_limit=lambda root_task_id: None,
            enforce_workflow_child_budget=lambda root_task_id: None,
            augment_feedback=lambda base_task, feedback: feedback,
            revision_service=_FakeRevisionService(),
            persist_child_task=lambda **kwargs: None,
        )


def test_create_challenger_child_task_marks_child_as_pending_branch_and_forwards_effective_feedback() -> None:
    module = _load_module()
    revision_service = _FakeRevisionService()
    persisted_calls: list[dict[str, object]] = []

    def _persist_child_task(**kwargs):
        persisted_calls.append(kwargs)
        return CreateVideoTaskResult(task_id="child-generated", status=TaskStatus.QUEUED, poll_after_ms=2000)

    result = module.create_challenger_child_task(
        base_task=_task(
            status=TaskStatus.COMPLETED,
            phase=TaskPhase.COMPLETED,
            delivery_status="delivered",
        ),
        feedback="Push quality further",
        session_id="session-override",
        persistent_memory=PersistentMemoryContext(memory_ids=["mem-a"], summary_text="summary", summary_digest="digest"),
        is_completed_delivery_candidate=lambda task: True,
        enforce_attempt_limit=lambda root_task_id: None,
        enforce_workflow_child_budget=lambda root_task_id: None,
        augment_feedback=lambda base_task, feedback: f"{feedback}\n\nShared case constraints:\nStay on brand.",
        revision_service=revision_service,
        persist_child_task=_persist_child_task,
    )

    persisted_child = persisted_calls[0]["child_task"]
    assert result.task_id == "child-generated"
    assert revision_service.metadata_calls[0]["revision_mode"] == "quality_challenger"
    assert "Shared case constraints" in str(revision_service.revision_calls[0]["feedback"])
    assert persisted_child.branch_kind == "challenger"
    assert persisted_child.delivery_status == "pending"
    assert persisted_child.resolved_task_id is None
    assert persisted_child.completion_mode is None
    assert persisted_child.delivery_tier is None
    assert persisted_child.delivery_stop_reason is None
    assert persisted_calls[0]["attempt_kind"] == "challenger"
    assert persisted_calls[0]["event_type"] == "challenger_created"


def test_persist_child_task_applies_memory_context_and_records_side_effects() -> None:
    module = _load_module()
    store = _FakeStore()
    artifact_store = _FakeArtifactStore()
    delivery_case_service = _FakeDeliveryCaseService()
    session_memory_service = _FakeSessionMemoryService()
    session_memory_service.summaries["session-child"] = SimpleNamespace(
        summary_text="Session memory context.",
        summary_digest="session-digest",
    )
    base_task = _task(session_id=None)
    child_task = VideoTask.from_revision(base_task, feedback="Add labels", preserve_working_parts=True)
    child_task.task_id = "child-1"
    child_task.session_id = None
    child_task.thread_id = None
    child_task.iteration_id = None
    child_task.execution_kind = None
    child_task.target_participant_id = None
    child_task.target_agent_id = None
    child_task.target_agent_role = None

    result = module.persist_child_task(
        base_task=base_task,
        child_task=child_task,
        attempt_kind="revise",
        session_id="session-child",
        event_type="revision_created",
        event_payload={"parent_task_id": base_task.task_id},
        persistent_memory=PersistentMemoryContext(
            memory_ids=["mem-a"],
            summary_text="Persistent memory context.",
            summary_digest="persistent-digest",
        ),
        thread_id="thread-override",
        iteration_id="iter-override",
        execution_kind="direct",
        target_participant_id="participant-override",
        target_agent_id="agent-override",
        target_agent_role="reviewer",
        store=store,
        artifact_store=artifact_store,
        settings=SimpleNamespace(default_poll_after_ms=1500),
        delivery_case_service=delivery_case_service,
        session_memory_service=session_memory_service,
        task_resource_ref=lambda task_id: f"video-task://{task_id}",
    )

    persisted = store.created_tasks[0]
    assert result.task_id == "child-1"
    assert result.poll_after_ms == 1500
    assert result.resource_refs == ["video-task://child-1"]
    assert persisted.session_id == "session-child"
    assert persisted.thread_id == "thread-override"
    assert persisted.iteration_id == "iter-override"
    assert persisted.execution_kind == "direct"
    assert persisted.target_participant_id == "participant-override"
    assert persisted.target_agent_id == "agent-override"
    assert persisted.target_agent_role == "reviewer"
    assert persisted.result_id is None
    assert persisted.memory_context_summary == "Session memory context."
    assert persisted.memory_context_digest == "session-digest"
    assert persisted.task_memory_context["session"]["summary_text"] == "Session memory context."
    assert persisted.task_memory_context["session"]["entry_count"] == 0
    assert persisted.selected_memory_ids == ["mem-a"]
    assert persisted.persistent_memory_context_summary == "Persistent memory context."
    assert persisted.persistent_memory_context_digest == "persistent-digest"
    assert persisted.task_memory_context["persistent"]["memory_ids"] == ["mem-a"]
    assert persisted.task_memory_context["persistent"]["items"][0]["memory_id"] == "mem-a"
    assert artifact_store.ensured_task_ids == ["child-1"]
    assert store.events == [("child-1", "revision_created", {"parent_task_id": "task-1"})]
    assert delivery_case_service.ensured_task_ids == ["child-1"]
    assert delivery_case_service.queued_task_ids == ["child-1"]
    assert delivery_case_service.synced_root_ids == ["task-1"]
    assert session_memory_service.recorded == [("child-1", "revise")]


def test_persist_child_task_records_branch_spawn_for_delivered_completed_parent() -> None:
    module = _load_module()
    store = _FakeStore()
    artifact_store = _FakeArtifactStore()
    delivery_case_service = _FakeDeliveryCaseService()
    base_task = _task(
        status=TaskStatus.COMPLETED,
        phase=TaskPhase.COMPLETED,
        delivery_status="delivered",
    )
    child_task = VideoTask.from_revision(base_task, feedback="Push quality", preserve_working_parts=True)
    child_task.task_id = "challenger-1"

    module.persist_child_task(
        base_task=base_task,
        child_task=child_task,
        attempt_kind="challenger",
        session_id=None,
        event_type="challenger_created",
        event_payload={"parent_task_id": base_task.task_id},
        store=store,
        artifact_store=artifact_store,
        settings=SimpleNamespace(default_poll_after_ms=1500),
        delivery_case_service=delivery_case_service,
        session_memory_service=None,
        task_resource_ref=lambda task_id: f"video-task://{task_id}",
    )

    assert delivery_case_service.branch_spawns == [("task-1", "challenger-1")]
