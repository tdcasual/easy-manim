from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from video_agent.application.repair_state import build_repair_state_snapshot
from video_agent.domain.enums import TaskStatus
from video_agent.domain.models import VideoTask


def build_video_task_snapshot(
    task: VideoTask,
    *,
    store,
    require_task: Callable[[str], VideoTask],
    get_failure_contract: Callable[[str], dict[str, Any] | None],
    build_auto_repair_summary: Callable[[str, int], dict[str, Any]],
    result_factory: Callable[..., Any],
):
    task_id = task.task_id
    latest_validation = store.get_latest_validation(task_id)
    root_task_id = task.root_task_id or task.task_id
    root_task = require_task(root_task_id)
    repair_children = max(0, store.count_lineage_tasks(root_task_id) - 1)
    failure_contract = get_failure_contract(task_id) if task.status is TaskStatus.FAILED else None
    artifact_summary = {
        "script_count": len(store.list_artifacts(task_id, "current_script")),
        "video_count": len(store.list_artifacts(task_id, "final_video")),
        "preview_count": len(store.list_artifacts(task_id, "preview_frame")),
        "repair_children": repair_children,
    }
    validation_summary = latest_validation.model_dump(mode="json") if latest_validation else {}
    repair_state = build_repair_state_snapshot(root_task, repair_children)
    return result_factory(
        task_id=task.task_id,
        task_memory_context=dict(task.task_memory_context),
        thread_id=task.thread_id,
        iteration_id=task.iteration_id,
        agent_id=task.agent_id,
        target_participant_id=task.target_participant_id,
        target_agent_id=task.target_agent_id,
        target_agent_role=task.target_agent_role,
        strategy_profile_id=task.strategy_profile_id,
        display_title=task.display_title,
        title_source=task.title_source,
        risk_level=task.risk_level,
        generation_mode=task.generation_mode,
        quality_gate_status=task.quality_gate_status,
        accepted_as_best=task.accepted_as_best,
        accepted_version_rank=task.accepted_version_rank,
        status=task.status,
        phase=task.phase,
        attempt_count=task.attempt_count,
        parent_task_id=task.parent_task_id,
        root_task_id=task.root_task_id,
        inherited_from_task_id=task.inherited_from_task_id,
        latest_validation_summary=validation_summary,
        artifact_summary=artifact_summary,
        repair_state=repair_state.model_dump(mode="json"),
        auto_repair_summary=build_auto_repair_summary(root_task_id, repair_children),
        failure_contract=failure_contract,
        delivery_status=task.delivery_status,
        resolved_task_id=task.resolved_task_id,
        completion_mode=task.completion_mode,
        delivery_tier=task.delivery_tier,
        delivery_stop_reason=task.delivery_stop_reason,
    )


def build_video_result(
    task: VideoTask,
    *,
    store,
    artifact_store,
    require_task: Callable[[str], VideoTask],
    latest_artifact_resource: Callable[..., str | None],
    artifact_resources: Callable[..., list[str]],
    task_has_valid_final_video: Callable[..., bool],
    result_factory: Callable[..., Any],
    resource_ref: Callable[[str, Path], str],
):
    latest_validation = store.get_latest_validation(task.task_id)
    resolved_task = resolved_result_task(
        task,
        require_task=require_task,
        task_has_valid_final_video=lambda task_id: task_has_valid_final_video(
            task_id,
            store=store,
            artifact_store=artifact_store,
        ),
    )
    result_task_id = task.task_id if resolved_task is None else resolved_task.task_id
    result_validation = latest_validation if result_task_id == task.task_id else store.get_latest_validation(result_task_id)

    video_resource = latest_artifact_resource(
        result_task_id,
        "final_video",
        list_artifacts=store.list_artifacts,
        resource_ref=resource_ref,
        fallback_paths=[artifact_store.final_video_path(result_task_id)],
    )
    preview_frame_resources = artifact_resources(
        result_task_id,
        "preview_frame",
        list_artifacts=store.list_artifacts,
        resource_ref=resource_ref,
        fallback_paths=sorted(
            path
            for path in artifact_store.previews_dir(result_task_id).glob("*.png")
            if path.is_file()
        ),
    )
    script_resource = latest_artifact_resource(
        result_task_id,
        "current_script",
        list_artifacts=store.list_artifacts,
        resource_ref=resource_ref,
        fallback_paths=[artifact_store.script_path(result_task_id)],
    )
    validation_report_resource = latest_artifact_resource(
        result_task_id,
        "validation_report",
        list_artifacts=store.list_artifacts,
        resource_ref=resource_ref,
        fallback_paths=sorted(
            path
            for path in artifact_store.task_dir(result_task_id).glob("validations/validation_report_v*.json")
            if path.is_file()
        ),
    )

    return result_factory(
        task_id=task.task_id,
        status=task.status if resolved_task is None else resolved_task.status,
        ready=resolved_task is not None,
        video_resource=video_resource,
        preview_frame_resources=preview_frame_resources,
        script_resource=script_resource,
        validation_report_resource=validation_report_resource,
        summary=(result_validation.summary if result_validation else latest_validation.summary if latest_validation else None),
        delivery_status=task.delivery_status,
        resolved_task_id=task.resolved_task_id,
        completion_mode=task.completion_mode,
        delivery_tier=task.delivery_tier,
        delivery_stop_reason=task.delivery_stop_reason,
    )


def resolved_result_task(
    task: VideoTask,
    *,
    require_task: Callable[[str], VideoTask],
    task_has_valid_final_video: Callable[[str], bool],
) -> VideoTask | None:
    if task.delivery_status == "delivered":
        resolved_task_id = task.resolved_task_id or task.task_id
        resolved_task = require_task(resolved_task_id)
        if task_has_valid_final_video(resolved_task_id):
            return resolved_task
        return None
    if task.status is TaskStatus.COMPLETED:
        if task_has_valid_final_video(task.task_id):
            return task
        return None
    return None


def task_has_valid_final_video(task_id: str, *, store, artifact_store) -> bool:
    artifacts = store.list_artifacts(task_id, "final_video")
    for artifact in reversed(artifacts):
        if Path(artifact["path"]).exists():
            return True
    return artifact_store.final_video_path(task_id).exists()


def latest_artifact_resource(
    task_id: str,
    artifact_kind: str,
    *,
    list_artifacts: Callable[[str, str], list[dict[str, Any]]],
    resource_ref: Callable[[str, Path], str],
    fallback_paths: list[Path] | None = None,
) -> str | None:
    resources = artifact_resources(
        task_id,
        artifact_kind,
        list_artifacts=list_artifacts,
        resource_ref=resource_ref,
        fallback_paths=fallback_paths,
    )
    if not resources:
        return None
    return resources[-1]


def artifact_resources(
    task_id: str,
    artifact_kind: str,
    *,
    list_artifacts: Callable[[str, str], list[dict[str, Any]]],
    resource_ref: Callable[[str, Path], str],
    fallback_paths: list[Path] | None = None,
) -> list[str]:
    resources: list[str] = []
    seen_paths: set[str] = set()

    for artifact in list_artifacts(task_id, artifact_kind):
        path = Path(artifact["path"])
        if not path.exists():
            continue
        path_key = str(path.resolve())
        if path_key in seen_paths:
            continue
        resources.append(resource_ref(task_id, path))
        seen_paths.add(path_key)

    for fallback_path in fallback_paths or []:
        path = Path(fallback_path)
        if not path.exists():
            continue
        path_key = str(path.resolve())
        if path_key in seen_paths:
            continue
        resources.append(resource_ref(task_id, path))
        seen_paths.add(path_key)

    return resources
