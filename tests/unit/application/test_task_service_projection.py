import importlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.domain.validation_models import ValidationReport


MODULE_NAME = "video_agent.application.task_service_projection"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


class _FakeStore:
    def __init__(self, tasks: list[VideoTask], latest_validations: dict[str, ValidationReport | None] | None = None) -> None:
        self._tasks = {task.task_id: task for task in tasks}
        self._artifacts: dict[tuple[str, str], list[dict[str, str]]] = {}
        self._latest_validations = latest_validations or {}
        self.lineage_count = len(tasks)

    def get_task(self, task_id: str) -> VideoTask | None:
        return self._tasks.get(task_id)

    def count_lineage_tasks(self, root_task_id: str) -> int:
        return self.lineage_count

    def get_latest_validation(self, task_id: str) -> ValidationReport | None:
        return self._latest_validations.get(task_id)

    def list_artifacts(self, task_id: str, artifact_kind: str) -> list[dict[str, str]]:
        return list(self._artifacts.get((task_id, artifact_kind), []))


def _task(
    *,
    task_id: str = "task-1",
    root_task_id: str = "task-1",
    parent_task_id: str | None = None,
    status: TaskStatus = TaskStatus.COMPLETED,
    phase: TaskPhase = TaskPhase.COMPLETED,
    delivery_status: str | None = "delivered",
    resolved_task_id: str | None = None,
    completion_mode: str | None = "repaired",
    delivery_tier: str | None = "guided_generate",
    delivery_stop_reason: str | None = None,
) -> VideoTask:
    return VideoTask(
        task_id=task_id,
        root_task_id=root_task_id,
        parent_task_id=parent_task_id,
        status=status,
        phase=phase,
        prompt="Draw a circle",
        delivery_status=delivery_status,
        resolved_task_id=resolved_task_id,
        completion_mode=completion_mode,
        delivery_tier=delivery_tier,
        delivery_stop_reason=delivery_stop_reason,
    )


def test_artifact_resources_include_existing_fallbacks_without_duplicates(tmp_path: Path) -> None:
    module = _load_module()
    persisted = tmp_path / "persisted.mp4"
    fallback = tmp_path / "fallback.mp4"
    duplicate = tmp_path / "duplicate.mp4"
    persisted.write_text("persisted")
    fallback.write_text("fallback")
    duplicate.write_text("duplicate")

    resources = module.artifact_resources(
        "task-1",
        "final_video",
        list_artifacts=lambda task_id, artifact_kind: [
            {"path": str(persisted)},
            {"path": str(duplicate)},
            {"path": str(duplicate)},
            {"path": str(tmp_path / "missing.mp4")},
        ],
        resource_ref=lambda task_id, path: f"video-task://{task_id}/{Path(path).name}",
        fallback_paths=[duplicate, fallback],
    )

    assert resources == [
        "video-task://task-1/persisted.mp4",
        "video-task://task-1/duplicate.mp4",
        "video-task://task-1/fallback.mp4",
    ]
    assert module.latest_artifact_resource(
        "task-1",
        "final_video",
        list_artifacts=lambda task_id, artifact_kind: [{"path": str(persisted)}],
        resource_ref=lambda task_id, path: f"video-task://{task_id}/{Path(path).name}",
        fallback_paths=[fallback],
    ) == "video-task://task-1/fallback.mp4"


def test_build_video_result_prefers_resolved_descendant_and_uses_fallback_resources(tmp_path: Path) -> None:
    module = _load_module()
    root = _task(task_id="root-1", root_task_id="root-1", resolved_task_id="child-1", completion_mode="degraded")
    child = _task(
        task_id="child-1",
        root_task_id="root-1",
        parent_task_id="root-1",
        resolved_task_id="child-1",
        completion_mode="degraded",
    )
    child_video = tmp_path / "final_video.mp4"
    child_script = tmp_path / "current_script.py"
    validations_dir = tmp_path / "validations"
    validations_dir.mkdir()
    validation_path = validations_dir / "validation_report_v1.json"
    child_video.write_text("video")
    child_script.write_text("script")
    validation_path.write_text("{}")

    store = _FakeStore(
        [root, child],
        latest_validations={
            "root-1": ValidationReport(passed=False, summary="Root failed first"),
            "child-1": ValidationReport(passed=True, summary="Child delivered"),
        },
    )

    result = module.build_video_result(
        root,
        store=store,
        artifact_store=SimpleNamespace(
            final_video_path=lambda task_id: child_video if task_id == "child-1" else tmp_path / "missing.mp4",
            previews_dir=lambda task_id: tmp_path / "previews",
            script_path=lambda task_id: child_script,
            task_dir=lambda task_id: tmp_path,
        ),
        require_task=lambda task_id: child if task_id == "child-1" else root,
        latest_artifact_resource=module.latest_artifact_resource,
        artifact_resources=module.artifact_resources,
        task_has_valid_final_video=module.task_has_valid_final_video,
        result_factory=lambda **kwargs: kwargs,
        resource_ref=lambda task_id, path: f"video-task://{task_id}/{Path(path).name}",
    )

    assert result["ready"] is True
    assert result["status"] is TaskStatus.COMPLETED
    assert result["resolved_task_id"] == "child-1"
    assert result["completion_mode"] == "degraded"
    assert result["video_resource"] == "video-task://child-1/final_video.mp4"
    assert result["script_resource"] == "video-task://child-1/current_script.py"
    assert result["validation_report_resource"] == "video-task://child-1/validation_report_v1.json"
    assert result["summary"] == "Child delivered"


def test_build_video_task_snapshot_includes_repair_state_artifact_counts_and_failed_contract_only_when_failed() -> None:
    module = _load_module()
    root = _task(task_id="root-1", root_task_id="root-1", status=TaskStatus.FAILED, phase=TaskPhase.FAILED, delivery_status="failed")
    root.repair_attempted = True
    root.repair_last_issue_code = "render_failed"
    root.repair_stop_reason = "budget_exhausted"
    child = _task(task_id="child-1", root_task_id="root-1", parent_task_id="root-1", status=TaskStatus.FAILED, phase=TaskPhase.FAILED, delivery_status="failed")
    child.task_memory_context = {
        "persistent": {
            "memory_ids": ["mem-a"],
            "summary_text": "Prefer high-contrast diagrams with concise labels.",
            "summary_digest": "digest-mem-a",
            "items": [
                {
                    "memory_id": "mem-a",
                    "summary_text": "Prefer high-contrast diagrams with concise labels.",
                    "summary_digest": "digest-mem-a",
                    "lineage_refs": ["video-task://root-1/task.json"],
                    "enhancement": {},
                }
            ],
        }
    }
    store = _FakeStore(
        [root, child],
        latest_validations={"child-1": ValidationReport(passed=False, summary="Validation failed")},
    )
    store._artifacts[("child-1", "current_script")] = [{"path": "/tmp/script.py"}]
    store._artifacts[("child-1", "final_video")] = [{"path": "/tmp/final_video.mp4"}]
    store._artifacts[("child-1", "preview_frame")] = [{"path": "/tmp/frame_001.png"}]

    snapshot = module.build_video_task_snapshot(
        child,
        store=store,
        require_task=lambda task_id: root,
        get_failure_contract=lambda task_id: {"issue_code": "render_failed"},
        build_auto_repair_summary=lambda root_task_id, repair_children: {"remaining_budget": 0},
        result_factory=lambda **kwargs: kwargs,
    )

    assert snapshot["task_id"] == "child-1"
    assert snapshot["latest_validation_summary"]["summary"] == "Validation failed"
    assert snapshot["artifact_summary"] == {
        "script_count": 1,
        "video_count": 1,
        "preview_count": 1,
        "repair_children": 1,
    }
    assert snapshot["repair_state"] == {
        "attempted": True,
        "child_count": 1,
        "last_issue_code": "render_failed",
        "stop_reason": "budget_exhausted",
    }
    assert snapshot["auto_repair_summary"] == {"remaining_budget": 0}
    assert snapshot["failure_contract"] == {"issue_code": "render_failed"}
    assert snapshot["task_memory_context"]["persistent"]["memory_ids"] == ["mem-a"]
    assert snapshot["task_memory_context"]["persistent"]["items"][0]["memory_id"] == "mem-a"
