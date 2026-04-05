from __future__ import annotations

from typing import Any, Callable

from video_agent.application.branch_arbitration import build_arbitration_summary, build_branch_scoreboard
from video_agent.application.delivery_guarantee_service import DeliveryGuaranteeDecision
from video_agent.application.errors import AdmissionControlError
from video_agent.application.workflow_render_profile import (
    build_degraded_delivery_feedback,
    build_degraded_output_profile,
    build_degraded_style_hints,
)
from video_agent.domain.enums import TaskStatus
from video_agent.domain.quality_models import QualityScorecard


def maybe_schedule_degraded_delivery(
    task,
    *,
    runtime_service,
    store,
    artifact_store,
    auto_repair_service,
    on_skip: Callable[[str], None] | None = None,
) -> DeliveryGuaranteeDecision | None:
    if not runtime_service.settings.delivery_guarantee_enabled:
        return None
    if task.parent_task_id is None:
        return None
    if task.completion_mode == "degraded":
        return None
    if lineage_already_has_degraded_attempt(store, task.root_task_id or task.task_id):
        return None

    failure_contract = artifact_store.read_failure_contract(task.task_id) or {}
    if bool(failure_contract.get("human_review_required")):
        return None
    issue_code = str(failure_contract.get("issue_code") or "")
    if issue_code.startswith("provider_") or issue_code in {
        "latex_dependency_missing",
        "sandbox_policy_violation",
        "runtime_policy_violation",
    }:
        return None

    task_service = getattr(auto_repair_service, "task_service", None)
    if task_service is None:
        return None

    recovery_plan = artifact_store.read_recovery_plan(task.task_id) or {}
    generation_mode = str(
        recovery_plan.get("fallback_generation_mode")
        or failure_contract.get("fallback_generation_mode")
        or task.generation_mode
        or "guided_generate"
    )
    try:
        created = task_service.create_degraded_delivery_task(
            task.task_id,
            feedback=build_degraded_delivery_feedback(issue_code=issue_code, generation_mode=generation_mode),
            generation_mode=generation_mode,
            style_hints=build_degraded_style_hints(task.style_hints),
            output_profile=build_degraded_output_profile(task.output_profile),
        )
    except (AdmissionControlError, ValueError) as exc:
        if on_skip is not None:
            on_skip(str(exc))
        return None

    return DeliveryGuaranteeDecision(
        delivered=False,
        reason="created_degraded_attempt",
        scheduled=True,
        child_task_id=created.task_id,
        completion_mode="degraded",
        delivery_tier=generation_mode,
    )


def maybe_schedule_quality_challenger(
    task,
    scorecard: QualityScorecard,
    *,
    runtime_service,
    auto_repair_service,
) -> dict[str, Any]:
    if not runtime_service.settings.multi_agent_workflow_enabled:
        return {
            "created": False,
            "reason": "multi_agent_workflow_disabled",
            "child_task_id": None,
            "quality_gate_status": task.quality_gate_status,
            "overall_score": scorecard.total_score,
        }
    if not runtime_service.settings.multi_agent_workflow_auto_challenger_enabled:
        return {
            "created": False,
            "reason": "auto_challenger_governance_disabled",
            "child_task_id": None,
            "quality_gate_status": task.quality_gate_status,
            "overall_score": scorecard.total_score,
        }
    if task.status is not TaskStatus.COMPLETED or task.delivery_status != "delivered":
        return {
            "created": False,
            "reason": "task_not_delivered",
            "child_task_id": None,
            "quality_gate_status": task.quality_gate_status,
            "overall_score": scorecard.total_score,
        }
    if task.quality_gate_status == "accepted":
        return {
            "created": False,
            "reason": "quality_accepted",
            "child_task_id": None,
            "quality_gate_status": task.quality_gate_status,
            "overall_score": scorecard.total_score,
        }
    if task.completion_mode in {"degraded", "emergency_fallback"}:
        return {
            "created": False,
            "reason": "completion_mode_ineligible",
            "child_task_id": None,
            "quality_gate_status": task.quality_gate_status,
            "overall_score": scorecard.total_score,
        }

    guard_blockers = guarded_rollout_blockers(runtime_service)
    if guard_blockers:
        return {
            "created": False,
            "reason": "guarded_rollout_blocked",
            "blocked_reasons": guard_blockers,
            "child_task_id": None,
            "quality_gate_status": task.quality_gate_status,
            "overall_score": scorecard.total_score,
        }

    task_service = getattr(auto_repair_service, "task_service", None)
    if task_service is None:
        return {
            "created": False,
            "reason": "task_service_unavailable",
            "child_task_id": None,
            "quality_gate_status": task.quality_gate_status,
            "overall_score": scorecard.total_score,
        }

    try:
        created = task_service.create_challenger_task(
            task.task_id,
            feedback=build_quality_challenger_feedback(
                task,
                scorecard,
                quality_gate_min_score=runtime_service.settings.quality_gate_min_score,
            ),
            session_id=task.session_id,
        )
    except (AdmissionControlError, ValueError) as exc:
        return {
            "created": False,
            "reason": str(exc) if isinstance(exc, ValueError) else exc.code,
            "child_task_id": None,
            "quality_gate_status": task.quality_gate_status,
            "overall_score": scorecard.total_score,
        }

    return {
        "created": True,
        "reason": "created",
        "child_task_id": created.task_id,
        "quality_gate_status": task.quality_gate_status,
        "overall_score": scorecard.total_score,
    }


def maybe_auto_promote_challenger(
    task,
    *,
    runtime_service,
    store,
    artifact_store,
    auto_repair_service,
) -> dict[str, Any]:
    if not runtime_service.settings.multi_agent_workflow_enabled:
        return {
            "promoted": False,
            "reason": "multi_agent_workflow_disabled",
            "recommended_task_id": None,
            "recommended_action": None,
            "selected_task_id": None,
        }
    if not runtime_service.settings.multi_agent_workflow_auto_arbitration_enabled:
        return {
            "promoted": False,
            "reason": "auto_arbitration_governance_disabled",
            "recommended_task_id": None,
            "recommended_action": None,
            "selected_task_id": None,
        }
    if task.branch_kind != "challenger":
        return {
            "promoted": False,
            "reason": "not_challenger_branch",
            "recommended_task_id": None,
            "recommended_action": None,
            "selected_task_id": None,
        }
    if task.status is not TaskStatus.COMPLETED or task.delivery_status != "delivered":
        return {
            "promoted": False,
            "reason": "task_not_delivered",
            "recommended_task_id": None,
            "recommended_action": None,
            "selected_task_id": None,
        }
    if task.quality_gate_status != "accepted":
        return {
            "promoted": False,
            "reason": "quality_not_accepted",
            "recommended_task_id": task.task_id,
            "recommended_action": "wait_for_completion",
            "selected_task_id": None,
        }

    guard_blockers = guarded_rollout_blockers(runtime_service)
    if guard_blockers:
        return {
            "promoted": False,
            "reason": "guarded_rollout_blocked",
            "blocked_reasons": guard_blockers,
            "recommended_task_id": None,
            "recommended_action": None,
            "selected_task_id": None,
        }

    root_task_id = task.root_task_id or task.task_id
    delivery_case = store.get_delivery_case(root_task_id)
    selected_task_id = None if delivery_case is None else delivery_case.selected_task_id
    active_task_id = None if delivery_case is None else delivery_case.active_task_id
    lineage = store.list_lineage_tasks(root_task_id)
    arbitration_summary = build_arbitration_summary(
        branch_scoreboard=build_branch_scoreboard(
            lineage_tasks=lineage,
            scorecards_by_task_id={
                lineage_task.task_id: load_quality_scorecard_json(
                    store=store,
                    artifact_store=artifact_store,
                    task_id=lineage_task.task_id,
                )
                for lineage_task in lineage
            },
            selected_task_id=selected_task_id,
            active_task_id=active_task_id,
        ),
        selected_task_id=selected_task_id,
        active_task_id=active_task_id,
    )
    decision = {
        "promoted": False,
        "reason": str(arbitration_summary.get("reason") or "arbitration_completed"),
        "recommended_task_id": arbitration_summary.get("recommended_task_id"),
        "recommended_action": arbitration_summary.get("recommended_action"),
        "selected_task_id": arbitration_summary.get("selected_task_id"),
        "candidate_count": arbitration_summary.get("candidate_count"),
    }
    if (
        arbitration_summary.get("recommended_action") != "promote_challenger"
        or arbitration_summary.get("recommended_task_id") != task.task_id
    ):
        return decision

    task_service = getattr(auto_repair_service, "task_service", None)
    if task_service is None:
        decision["reason"] = "task_service_unavailable"
        return decision

    try:
        task_service.accept_best_version(task.task_id)
    except (AdmissionControlError, ValueError) as exc:
        decision["reason"] = str(exc) if isinstance(exc, ValueError) else exc.code
        return decision

    decision["promoted"] = True
    decision["selected_task_id"] = task.task_id
    return decision


def guarded_rollout_blockers(runtime_service) -> list[str]:
    guard = runtime_service.inspect_multi_agent_autonomy_guard()
    if not guard.enabled or guard.allowed:
        return []
    return list(guard.reasons)


def lineage_already_has_degraded_attempt(store, root_task_id: str) -> bool:
    for lineage_task in store.list_lineage_tasks(root_task_id):
        if lineage_task.parent_task_id is not None and lineage_task.completion_mode == "degraded":
            return True
    return False


def build_quality_challenger_feedback(
    task,
    scorecard: QualityScorecard,
    *,
    quality_gate_min_score: float,
) -> str:
    score_text = f"{float(scorecard.total_score or 0.0):.2f}"
    threshold_text = f"{float(quality_gate_min_score):.2f}"
    issue_codes = list(scorecard.must_fix_issues or scorecard.warning_codes or [])
    issues = ", ".join(issue_codes[:3]) if issue_codes else "general quality improvements"
    return (
        "Auto challenger branch. "
        "The current version delivered successfully but did not pass the quality gate. "
        f"Current score {score_text} is below threshold {threshold_text}. "
        f"Focus on {issues}. "
        "Preserve the working render path, keep the core prompt intent, and produce a stronger alternative "
        "with better motion, clarity, or prompt alignment while staying render-safe."
    )


def load_quality_scorecard_json(*, store, artifact_store, task_id: str) -> dict[str, Any] | None:
    scorecard = store.get_task_quality_score(task_id)
    if scorecard is not None:
        return scorecard.model_dump(mode="json")
    return artifact_store.read_quality_score(task_id)
