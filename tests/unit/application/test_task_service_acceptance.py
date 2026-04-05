import importlib
import importlib.util
from types import SimpleNamespace

import pytest

from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask


MODULE_NAME = "video_agent.application.task_service_acceptance"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


class _FakeStore:
    def __init__(self, tasks: list[VideoTask], delivery_case=None) -> None:
        self._tasks = {task.task_id: task for task in tasks}
        self._lineage = [task.task_id for task in tasks]
        self._delivery_case = delivery_case
        self.updated_tasks: list[VideoTask] = []
        self.events: list[tuple[str, str, dict[str, object]]] = []

    def list_lineage_tasks(self, root_task_id: str) -> list[VideoTask]:
        return [self._tasks[task_id] for task_id in self._lineage]

    def get_delivery_case(self, root_task_id: str):
        return self._delivery_case

    def update_task(self, task: VideoTask) -> None:
        self._tasks[task.task_id] = task
        self.updated_tasks.append(task.model_copy(deep=True))

    def append_event(self, task_id: str, event_type: str, payload: dict[str, object]) -> None:
        self.events.append((task_id, event_type, dict(payload)))


class _FakeArtifactStore:
    def __init__(self) -> None:
        self.snapshots: list[VideoTask] = []

    def write_task_snapshot(self, task: VideoTask) -> None:
        self.snapshots.append(task.model_copy(deep=True))


class _FakeDeliveryCaseService:
    def __init__(self) -> None:
        self.synced_roots: list[str] = []
        self.winner_records: list[dict[str, object]] = []

    def sync_case_for_root(self, root_task_id: str) -> None:
        self.synced_roots.append(root_task_id)

    def record_winner_selected(
        self,
        *,
        selected_task: VideoTask,
        previous_selected_task_id: str | None = None,
        arbitration_summary: dict[str, object] | None = None,
    ) -> None:
        self.winner_records.append(
            {
                "selected_task_id": selected_task.task_id,
                "previous_selected_task_id": previous_selected_task_id,
                "arbitration_summary": None if arbitration_summary is None else dict(arbitration_summary),
            }
        )


def _task(
    *,
    task_id: str,
    root_task_id: str,
    parent_task_id: str | None = None,
    branch_kind: str | None = None,
    total_score: float | None = None,
    quality_gate_status: str | None = "accepted",
    completion_mode: str | None = "repaired",
    delivery_tier: str | None = "guided_generate",
    accepted_as_best: bool = False,
    accepted_version_rank: int | None = None,
) -> VideoTask:
    task = VideoTask(
        task_id=task_id,
        root_task_id=root_task_id,
        parent_task_id=parent_task_id,
        branch_kind=branch_kind,
        status=TaskStatus.COMPLETED,
        phase=TaskPhase.COMPLETED,
        prompt="Draw a circle",
        delivery_status="delivered",
        quality_gate_status=quality_gate_status,
        completion_mode=completion_mode,
        delivery_tier=delivery_tier,
    )
    task.accepted_as_best = accepted_as_best
    task.accepted_version_rank = accepted_version_rank
    task.resolved_task_id = root_task_id if accepted_as_best else None
    task._score = total_score
    return task


def _quality_score_lookup(tasks: list[VideoTask]):
    return {
        task.task_id: {
            "task_id": task.task_id,
            "total_score": getattr(task, "_score", None),
            "accepted": task.quality_gate_status == "accepted",
        }
        for task in tasks
    }


def test_accept_task_as_best_rejects_non_completed_task() -> None:
    module = _load_module()
    task = VideoTask(
        task_id="task-1",
        root_task_id="task-1",
        status=TaskStatus.FAILED,
        phase=TaskPhase.FAILED,
        prompt="Draw a circle",
    )

    with pytest.raises(ValueError, match="accept_best_requires_completed_task"):
        module.accept_task_as_best(
            task,
            store=_FakeStore([task]),
            artifact_store=_FakeArtifactStore(),
            get_quality_score=lambda task_id: None,
            require_task=lambda task_id: task,
            build_snapshot=lambda task_id: {"task_id": task_id},
        )


def test_accept_task_as_best_updates_lineage_ranking_and_root_resolution() -> None:
    module = _load_module()
    root = _task(task_id="root-1", root_task_id="root-1", completion_mode="primary", delivery_tier="guided_generate")
    challenger = _task(
        task_id="challenger-1",
        root_task_id="root-1",
        parent_task_id="root-1",
        branch_kind="challenger",
        total_score=0.93,
        completion_mode="repaired",
        delivery_tier="quality_challenger",
    )
    root._score = 0.71
    store = _FakeStore([root, challenger], delivery_case=SimpleNamespace(active_task_id="challenger-1"))
    artifact_store = _FakeArtifactStore()
    scores = _quality_score_lookup([root, challenger])

    snapshot = module.accept_task_as_best(
        challenger,
        store=store,
        artifact_store=artifact_store,
        get_quality_score=lambda task_id: scores[task_id],
        require_task=lambda task_id: root,
        build_snapshot=lambda task_id: {"task_id": task_id, "kind": "snapshot"},
    )

    persisted_root = store._tasks["root-1"]
    persisted_challenger = store._tasks["challenger-1"]

    assert snapshot == {"task_id": "challenger-1", "kind": "snapshot"}
    assert persisted_challenger.accepted_as_best is True
    assert persisted_challenger.accepted_version_rank == 2
    assert persisted_root.status is TaskStatus.COMPLETED
    assert persisted_root.phase is TaskPhase.COMPLETED
    assert persisted_root.delivery_status == "delivered"
    assert persisted_root.resolved_task_id == "challenger-1"
    assert persisted_root.completion_mode == "repaired"
    assert persisted_root.delivery_tier == "quality_challenger"
    assert persisted_root.accepted_as_best is False
    assert persisted_root.accepted_version_rank is None
    assert len(artifact_store.snapshots) == 3


def test_accept_task_as_best_records_event_and_delivery_case_callback_with_same_arbitration_summary() -> None:
    module = _load_module()
    root = _task(task_id="root-1", root_task_id="root-1", total_score=0.71)
    challenger = _task(
        task_id="challenger-1",
        root_task_id="root-1",
        parent_task_id="root-1",
        branch_kind="challenger",
        total_score=0.93,
    )
    store = _FakeStore(
        [root, challenger],
        delivery_case=SimpleNamespace(active_task_id="challenger-1"),
    )
    artifact_store = _FakeArtifactStore()
    delivery_case_service = _FakeDeliveryCaseService()
    scores = _quality_score_lookup([root, challenger])

    module.accept_task_as_best(
        challenger,
        store=store,
        artifact_store=artifact_store,
        get_quality_score=lambda task_id: scores[task_id],
        require_task=lambda task_id: root,
        build_snapshot=lambda task_id: {"task_id": task_id},
        delivery_case_service=delivery_case_service,
    )

    assert store.events[0][0] == "challenger-1"
    assert store.events[0][1] == "task_accepted_as_best"
    event_summary = store.events[0][2]["arbitration_summary"]
    callback_summary = delivery_case_service.winner_records[0]["arbitration_summary"]

    assert delivery_case_service.synced_roots == ["root-1"]
    assert delivery_case_service.winner_records[0]["selected_task_id"] == "challenger-1"
    assert event_summary == callback_summary
    assert event_summary["recommended_action"] == "promote_challenger"
    assert event_summary["recommended_task_id"] == "challenger-1"


def test_accept_task_as_best_records_case_memory_branch_state_and_decision() -> None:
    module = _load_module()
    root = _task(task_id="root-1", root_task_id="root-1", total_score=0.71)
    challenger = _task(
        task_id="challenger-1",
        root_task_id="root-1",
        parent_task_id="root-1",
        branch_kind="challenger",
        total_score=0.93,
    )
    store = _FakeStore(
        [root, challenger],
        delivery_case=SimpleNamespace(active_task_id="challenger-1"),
    )
    scores = _quality_score_lookup([root, challenger])
    branch_state_records: list[dict[str, object]] = []
    decision_records: list[dict[str, object]] = []

    module.accept_task_as_best(
        challenger,
        store=store,
        artifact_store=_FakeArtifactStore(),
        get_quality_score=lambda task_id: scores[task_id],
        require_task=lambda task_id: root,
        build_snapshot=lambda task_id: {"task_id": task_id},
        record_case_memory_branch_state=lambda **kwargs: branch_state_records.append(kwargs),
        record_case_memory_decision=lambda **kwargs: decision_records.append(kwargs),
    )

    assert branch_state_records[0]["root_task_id"] == "root-1"
    assert branch_state_records[0]["arbitration_summary"]["recommended_task_id"] == "challenger-1"
    scoreboard = branch_state_records[0]["branch_scoreboard"]
    selected_entry = next(item for item in scoreboard if item["task_id"] == "challenger-1")
    assert selected_entry["is_selected"] is True
    assert selected_entry["accepted_as_best"] is True
    assert decision_records == [
        {
            "root_task_id": "root-1",
            "action": "winner_selected",
            "task_id": "challenger-1",
            "details": {
                "previous_selected_task_id": None,
                "recommended_action": "promote_challenger",
                "recommended_task_id": "challenger-1",
            },
        }
    ]
