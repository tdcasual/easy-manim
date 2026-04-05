from __future__ import annotations

from typing import Any, Callable

from video_agent.application.branch_arbitration import build_arbitration_summary, build_branch_scoreboard
from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask


def accept_task_as_best(
    accepted_task: VideoTask,
    *,
    store,
    artifact_store,
    get_quality_score: Callable[[str], dict[str, Any] | None],
    require_task: Callable[[str], VideoTask],
    build_snapshot: Callable[[str], Any],
    delivery_case_service=None,
    record_case_memory_branch_state: Callable[..., None] | None = None,
    record_case_memory_decision: Callable[..., None] | None = None,
):
    if accepted_task.status is not TaskStatus.COMPLETED:
        raise ValueError("accept_best_requires_completed_task")

    root_task_id = accepted_task.root_task_id or accepted_task.task_id
    lineage = store.list_lineage_tasks(root_task_id)
    root_task = require_task(root_task_id)
    delivery_case = store.get_delivery_case(root_task_id)
    previous_selected_task_id = root_task.resolved_task_id
    active_task_id = delivery_case.active_task_id if delivery_case is not None else accepted_task.task_id
    arbitration_summary = build_arbitration_summary(
        branch_scoreboard=build_branch_scoreboard(
            lineage_tasks=lineage,
            scorecards_by_task_id={candidate.task_id: get_quality_score(candidate.task_id) for candidate in lineage},
            selected_task_id=previous_selected_task_id,
            active_task_id=active_task_id,
        ),
        selected_task_id=previous_selected_task_id,
        active_task_id=active_task_id,
    )

    accepted_rank = 1
    for index, candidate in enumerate(lineage, start=1):
        is_selected = candidate.task_id == accepted_task.task_id
        candidate.accepted_as_best = is_selected
        candidate.accepted_version_rank = index if is_selected else None
        if is_selected:
            accepted_rank = index
        store.update_task(candidate)
        artifact_store.write_task_snapshot(candidate)

    root_task.status = TaskStatus.COMPLETED
    root_task.phase = TaskPhase.COMPLETED
    root_task.delivery_status = "delivered"
    root_task.resolved_task_id = accepted_task.task_id
    root_task.completion_mode = accepted_task.completion_mode
    root_task.delivery_tier = accepted_task.delivery_tier
    root_task.delivery_stop_reason = None
    root_task.accepted_as_best = accepted_task.task_id == root_task.task_id
    root_task.accepted_version_rank = accepted_rank if root_task.accepted_as_best else None
    store.update_task(root_task)
    artifact_store.write_task_snapshot(root_task)

    store.append_event(
        accepted_task.task_id,
        "task_accepted_as_best",
        {
            "root_task_id": root_task_id,
            "accepted_version_rank": accepted_rank,
            "previous_selected_task_id": previous_selected_task_id,
            "arbitration_summary": arbitration_summary,
        },
    )
    if delivery_case_service is not None:
        delivery_case_service.sync_case_for_root(root_task_id)
        delivery_case_service.record_winner_selected(
            selected_task=accepted_task,
            previous_selected_task_id=previous_selected_task_id,
            arbitration_summary=arbitration_summary,
        )

    if record_case_memory_branch_state is not None:
        fresh_lineage = store.list_lineage_tasks(root_task_id)
        record_case_memory_branch_state(
            root_task_id=root_task_id,
            branch_scoreboard=build_branch_scoreboard(
                lineage_tasks=fresh_lineage,
                scorecards_by_task_id={
                    candidate.task_id: get_quality_score(candidate.task_id)
                    for candidate in fresh_lineage
                },
                selected_task_id=accepted_task.task_id,
                active_task_id=accepted_task.task_id,
            ),
            arbitration_summary=arbitration_summary,
        )
    if record_case_memory_decision is not None:
        record_case_memory_decision(
            root_task_id=root_task_id,
            action="winner_selected",
            task_id=accepted_task.task_id,
            details={
                "previous_selected_task_id": previous_selected_task_id,
                "recommended_action": arbitration_summary.get("recommended_action"),
                "recommended_task_id": arbitration_summary.get("recommended_task_id"),
            },
        )
    return build_snapshot(accepted_task.task_id)
