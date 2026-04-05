from __future__ import annotations

from typing import Any, Literal, cast

from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.models import VideoTask
from video_agent.domain.review_workflow_models import (
    CollaborationMemoryItem,
    RoleCollaborationMemoryContext,
    WorkflowCollaborationMemoryContext,
)


def build_workflow_memory_context(
    *,
    task: VideoTask,
    root_task: VideoTask,
    shared_records: list[AgentMemoryRecord],
    case_memory: dict[str, Any],
) -> WorkflowCollaborationMemoryContext:
    root_task_id = root_task.task_id
    shared_memory_ids = list(
        dict.fromkeys(
            list(task.selected_memory_ids)
            + list(root_task.selected_memory_ids)
        )
    )
    task_context_summary = resolve_task_memory_context_summary(task=task, root_task=root_task)
    return WorkflowCollaborationMemoryContext(
        root_task_id=root_task_id,
        agent_id=root_task.agent_id,
        shared_memory_ids=shared_memory_ids,
        planner=build_role_memory_context(
            role="planner",
            shared_records=shared_records,
            task_context_summary=task_context_summary,
            case_memory=case_memory,
        ),
        reviewer=build_role_memory_context(
            role="reviewer",
            shared_records=shared_records,
            task_context_summary=task_context_summary,
            case_memory=case_memory,
        ),
        repairer=build_role_memory_context(
            role="repairer",
            shared_records=shared_records,
            task_context_summary=task_context_summary,
            case_memory=case_memory,
        ),
    )


def build_role_memory_context(
    *,
    role: Literal["planner", "reviewer", "repairer"],
    shared_records: list[AgentMemoryRecord],
    task_context_summary: str | None,
    case_memory: dict[str, Any],
) -> RoleCollaborationMemoryContext:
    items: list[CollaborationMemoryItem] = []
    for record in shared_records:
        items.append(
            CollaborationMemoryItem(
                source="persistent_memory",
                title=_persistent_memory_title(role),
                summary=record.summary_text.strip(),
                memory_id=record.memory_id,
            )
        )
    if task_context_summary and not shared_records:
        items.append(
            CollaborationMemoryItem(
                source="task_context",
                title="Attached workflow memory",
                summary=task_context_summary,
            )
        )
    items.extend(_build_case_memory_items(role=role, case_memory=case_memory))
    summary = "\n".join(
        f"{item.title}: {item.summary}".strip()
        for item in items
        if item.summary.strip()
    ).strip()
    return RoleCollaborationMemoryContext(
        role=cast(Literal["planner", "reviewer", "repairer"], role),
        summary=summary,
        item_count=len(items),
        items=items,
    )


def resolve_task_memory_context_summary(*, task: VideoTask, root_task: VideoTask) -> str | None:
    for candidate in (
        task.persistent_memory_context_summary,
        root_task.persistent_memory_context_summary,
    ):
        text = str(candidate or "").strip()
        if text:
            return text
    return None


def build_workflow_memory_query(
    *,
    root_task: VideoTask,
    case_memory: dict[str, Any],
) -> str:
    parts = [str(root_task.prompt or "").strip()]
    review_findings = case_memory.get("review_findings") or []
    if isinstance(review_findings, list) and review_findings:
        latest_finding = review_findings[-1] if isinstance(review_findings[-1], dict) else {}
        summary = str(latest_finding.get("summary") or "").strip()
        if summary:
            parts.append(summary)
    repair_constraints = case_memory.get("repair_constraints") or []
    if isinstance(repair_constraints, list) and repair_constraints:
        latest_constraint = repair_constraints[-1] if isinstance(repair_constraints[-1], dict) else {}
        repair_strategy = str(latest_constraint.get("repair_strategy") or "").strip()
        if repair_strategy:
            parts.append(repair_strategy)
    return " ".join(part for part in parts if part).strip()


def _persistent_memory_title(role: Literal["planner", "reviewer", "repairer"]) -> str:
    titles = {
        "planner": "Shared planning memory",
        "reviewer": "Shared review memory",
        "repairer": "Shared repair memory",
    }
    return titles[role]


def _build_case_memory_items(
    *,
    role: Literal["planner", "reviewer", "repairer"],
    case_memory: dict[str, Any],
) -> list[CollaborationMemoryItem]:
    if role == "planner":
        return _planner_case_memory_items(case_memory)
    if role == "reviewer":
        return _reviewer_case_memory_items(case_memory)
    return _repairer_case_memory_items(case_memory)


def _planner_case_memory_items(case_memory: dict[str, Any]) -> list[CollaborationMemoryItem]:
    items: list[CollaborationMemoryItem] = []
    for invariant in (case_memory.get("delivery_invariants") or [])[:2]:
        text = str(invariant).strip()
        if text:
            items.append(
                CollaborationMemoryItem(
                    source="case_memory",
                    title="Delivery invariant",
                    summary=text,
                )
            )
    notes = case_memory.get("planner_notes") or []
    if isinstance(notes, list) and notes:
        latest = notes[-1] if isinstance(notes[-1], dict) else {}
        generation_mode = str(latest.get("generation_mode") or "").strip()
        risk_level = str(latest.get("risk_level") or "").strip()
        parts = [
            f"generation_mode={generation_mode}" if generation_mode else "",
            f"risk_level={risk_level}" if risk_level else "",
        ]
        summary = ", ".join(part for part in parts if part)
        if summary:
            items.append(
                CollaborationMemoryItem(
                    source="case_memory",
                    title="Latest planner state",
                    summary=summary,
                )
            )
    return items


def _reviewer_case_memory_items(case_memory: dict[str, Any]) -> list[CollaborationMemoryItem]:
    items: list[CollaborationMemoryItem] = []
    findings = case_memory.get("review_findings") or []
    if not isinstance(findings, list):
        return items
    for finding in findings[-2:]:
        if not isinstance(finding, dict):
            continue
        quality_gate_status = str(finding.get("quality_gate_status") or "").strip()
        summary = str(finding.get("summary") or "").strip()
        must_fix = list(finding.get("must_fix_issue_codes", []) or [])
        parts = []
        if quality_gate_status:
            parts.append(f"quality_gate_status={quality_gate_status}")
        if summary:
            parts.append(summary)
        if must_fix:
            parts.append("must_fix=" + ", ".join(str(item) for item in must_fix[:3]))
        text = "; ".join(parts).strip()
        if text:
            items.append(
                CollaborationMemoryItem(
                    source="case_memory",
                    title="Latest review finding",
                    summary=text,
                )
            )
    return items


def _repairer_case_memory_items(case_memory: dict[str, Any]) -> list[CollaborationMemoryItem]:
    items: list[CollaborationMemoryItem] = []
    constraints = case_memory.get("repair_constraints") or []
    if not isinstance(constraints, list):
        return items
    for constraint in constraints[-2:]:
        if not isinstance(constraint, dict):
            continue
        parts = []
        quality_gate_status = str(constraint.get("quality_gate_status") or "").strip()
        if quality_gate_status:
            parts.append(f"quality_gate_status={quality_gate_status}")
        summary = str(constraint.get("summary") or "").strip()
        if summary:
            parts.append(summary)
        repair_strategy = str(constraint.get("repair_strategy") or "").strip()
        if repair_strategy:
            parts.append(repair_strategy)
        recovery_action = str(constraint.get("recovery_selected_action") or "").strip()
        if recovery_action:
            parts.append(f"recovery_selected_action={recovery_action}")
        must_fix = list(constraint.get("must_fix_issue_codes", []) or [])
        if must_fix:
            parts.append("must_fix=" + ", ".join(str(item) for item in must_fix[:3]))
        text = "; ".join(parts).strip()
        if text:
            items.append(
                CollaborationMemoryItem(
                    source="case_memory",
                    title="Latest repair constraint",
                    summary=text,
                )
            )
    return items
