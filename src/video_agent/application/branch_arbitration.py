from __future__ import annotations

from typing import Any, Mapping, Sequence

from video_agent.domain.models import VideoTask


def build_branch_scoreboard(
    *,
    lineage_tasks: Sequence[VideoTask],
    scorecards_by_task_id: Mapping[str, Mapping[str, Any] | None],
    selected_task_id: str | None,
    active_task_id: str | None,
) -> list[dict[str, Any]]:
    if not lineage_tasks:
        return []

    root_task_id = lineage_tasks[0].root_task_id or lineage_tasks[0].task_id
    incumbent_task_id = selected_task_id or root_task_id
    scoreboard: list[dict[str, Any]] = []

    for index, task in enumerate(lineage_tasks):
        scorecard = _normalize_scorecard(scorecards_by_task_id.get(task.task_id))
        comparison_label = "incumbent" if task.task_id == incumbent_task_id else "challenger"
        scoreboard.append(
            {
                "task_id": task.task_id,
                "parent_task_id": task.parent_task_id,
                "branch_kind": _normalized_branch_kind(task, root_task_id=root_task_id),
                "comparison_label": comparison_label,
                "lineage_index": index,
                "is_selected": task.task_id == selected_task_id,
                "is_active": task.task_id == active_task_id,
                "status": task.status.value,
                "phase": task.phase.value,
                "delivery_status": task.delivery_status,
                "quality_gate_status": task.quality_gate_status,
                "overall_score": _score_value(scorecard),
                "accepted": bool(scorecard.get("accepted")),
                "accepted_as_best": task.accepted_as_best,
                "accepted_version_rank": task.accepted_version_rank,
                "completion_mode": task.completion_mode,
            }
        )
    return scoreboard


def build_arbitration_summary(
    *,
    branch_scoreboard: Sequence[Mapping[str, Any]],
    selected_task_id: str | None,
    active_task_id: str | None,
) -> dict[str, Any]:
    incumbent_task_id = selected_task_id
    if incumbent_task_id is None and branch_scoreboard:
        incumbent_task_id = str(branch_scoreboard[0]["task_id"])

    scoreboard = [dict(entry) for entry in branch_scoreboard]
    eligible = [entry for entry in scoreboard if _is_delivered_candidate(entry)]
    accepted = [entry for entry in eligible if entry.get("quality_gate_status") == "accepted"]
    active_entry = _find_entry(scoreboard, active_task_id)
    incumbent_entry = _find_entry(scoreboard, incumbent_task_id)

    recommended_task_id = incumbent_task_id
    recommended_action = "wait_for_completion"
    reason = "no_delivered_candidate_available"

    if accepted:
        best = _select_best_candidate(accepted, incumbent_task_id=incumbent_task_id)
        recommended_task_id = str(best["task_id"])
        if recommended_task_id == incumbent_task_id:
            recommended_action = "keep_incumbent"
            reason = "incumbent_has_best_accepted_score"
        else:
            recommended_action = "promote_challenger"
            reason = "challenger_has_best_accepted_score"
    elif _is_active_incomplete(active_entry):
        recommended_action = "wait_for_completion"
        reason = "active_branch_still_running"
    elif incumbent_entry is not None and _is_delivered_candidate(incumbent_entry):
        recommended_task_id = str(incumbent_entry["task_id"])
        recommended_action = "keep_incumbent"
        reason = "incumbent_is_only_delivered_candidate"
    elif eligible:
        best = _select_best_candidate(eligible, incumbent_task_id=incumbent_task_id)
        recommended_task_id = str(best["task_id"])
        recommended_action = "wait_for_completion"
        reason = "delivered_candidates_pending_quality_acceptance"

    return {
        "recommended_task_id": recommended_task_id,
        "recommended_action": recommended_action,
        "reason": reason,
        "candidate_count": len(scoreboard),
        "eligible_task_ids": [str(entry["task_id"]) for entry in eligible],
        "selected_task_id": selected_task_id,
        "active_task_id": active_task_id,
        "incumbent_task_id": incumbent_task_id,
    }


def _normalized_branch_kind(task: VideoTask, *, root_task_id: str) -> str:
    if task.branch_kind:
        return str(task.branch_kind)
    if task.task_id == root_task_id:
        return "primary"
    return "revision"


def _normalize_scorecard(scorecard: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(scorecard, Mapping):
        return {}
    return dict(scorecard)


def _score_value(scorecard: Mapping[str, Any]) -> float | None:
    if not scorecard:
        return None
    total_score = scorecard.get("total_score", scorecard.get("overall_score"))
    if total_score is None:
        return None
    return float(total_score)


def _is_delivered_candidate(entry: Mapping[str, Any]) -> bool:
    return entry.get("status") == "completed" and entry.get("delivery_status") == "delivered"


def _is_active_incomplete(entry: Mapping[str, Any] | None) -> bool:
    if entry is None:
        return False
    return str(entry.get("status") or "") in {"queued", "revising", "running"}


def _find_entry(items: Sequence[Mapping[str, Any]], task_id: str | None) -> dict[str, Any] | None:
    if task_id is None:
        return None
    for item in items:
        if item.get("task_id") == task_id:
            return dict(item)
    return None


def _select_best_candidate(
    items: Sequence[Mapping[str, Any]],
    *,
    incumbent_task_id: str | None,
) -> dict[str, Any]:
    return min(
        (dict(item) for item in items),
        key=lambda item: (
            -(_score_value(item) or 0.0),
            0 if item.get("task_id") == incumbent_task_id else 1,
            int(item.get("lineage_index") or 0),
        ),
    )
