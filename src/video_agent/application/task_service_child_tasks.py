from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable

from video_agent.application.persistent_memory_service import PersistentMemoryContext
from video_agent.application.task_memory_context import (
    apply_persistent_memory_context_to_task,
    persistent_memory_digest_from_task,
    persistent_memory_ids_from_task,
    persistent_memory_items_from_task,
    persistent_memory_summary_from_task,
)
from video_agent.domain.enums import TaskStatus
from video_agent.domain.models import VideoTask


def inherit_persistent_memory_context(base_task: VideoTask) -> PersistentMemoryContext | None:
    memory_ids = persistent_memory_ids_from_task(base_task)
    summary_text = persistent_memory_summary_from_task(base_task)
    summary_digest = persistent_memory_digest_from_task(base_task)
    items = persistent_memory_items_from_task(base_task)
    if not (memory_ids or summary_text or summary_digest or items):
        return None
    return PersistentMemoryContext(
        memory_ids=memory_ids,
        summary_text=summary_text,
        summary_digest=summary_digest,
        items=items,
    )


def create_challenger_child_task(
    *,
    base_task: VideoTask,
    feedback: str,
    session_id: str | None,
    persistent_memory: PersistentMemoryContext | None,
    is_completed_delivery_candidate: Callable[[VideoTask], bool],
    enforce_attempt_limit: Callable[[str], None],
    enforce_workflow_child_budget: Callable[[str], None],
    augment_feedback: Callable[[VideoTask, str], str],
    revision_service,
    persist_child_task: Callable[..., Any],
):
    if not is_completed_delivery_candidate(base_task):
        raise ValueError("create_challenger_task requires a completed delivered parent task")
    root_task_id = base_task.root_task_id or base_task.task_id
    enforce_attempt_limit(root_task_id)
    enforce_workflow_child_budget(root_task_id)
    effective_feedback = augment_feedback(base_task, feedback)
    metadata = revision_service.build_metadata(
        base_task,
        revision_mode="quality_challenger",
        preserve_working_parts=True,
    )
    child_task = revision_service.create_revision(
        base_task=base_task,
        feedback=effective_feedback,
        preserve_working_parts=True,
    )
    child_task.branch_kind = "challenger"
    child_task.delivery_status = "pending"
    child_task.resolved_task_id = None
    child_task.completion_mode = None
    child_task.delivery_tier = None
    child_task.delivery_stop_reason = None
    return persist_child_task(
        base_task=base_task,
        child_task=child_task,
        attempt_kind="challenger",
        session_id=session_id,
        event_type="challenger_created",
        event_payload={
            "parent_task_id": base_task.task_id,
            "feedback": feedback,
            "effective_feedback": effective_feedback,
            **metadata,
        },
        persistent_memory=persistent_memory,
    )


def persist_child_task(
    *,
    base_task: VideoTask,
    child_task: VideoTask,
    attempt_kind: str,
    session_id: str | None,
    event_type: str,
    event_payload: dict[str, Any],
    store,
    artifact_store,
    settings,
    task_resource_ref: Callable[[str], str],
    persistent_memory: PersistentMemoryContext | None = None,
    thread_id: str | None = None,
    iteration_id: str | None = None,
    execution_kind: str | None = None,
    target_participant_id: str | None = None,
    target_agent_id: str | None = None,
    target_agent_role: str | None = None,
    delivery_case_service=None,
    session_memory_service=None,
    result_factory: Callable[..., Any] | None = None,
):
    effective_session_id = child_task.session_id or base_task.session_id or session_id
    if effective_session_id is not None:
        child_task.session_id = effective_session_id
    child_task.thread_id = thread_id or child_task.thread_id or base_task.thread_id
    child_task.iteration_id = iteration_id or child_task.iteration_id
    child_task.execution_kind = execution_kind or child_task.execution_kind
    child_task.target_participant_id = target_participant_id or child_task.target_participant_id or base_task.target_participant_id
    child_task.target_agent_id = target_agent_id or child_task.target_agent_id or base_task.target_agent_id
    child_task.target_agent_role = target_agent_role or child_task.target_agent_role or base_task.target_agent_role
    child_task.result_id = None

    apply_memory_context(
        session_id=effective_session_id,
        child_task=child_task,
        session_memory_service=session_memory_service,
    )
    apply_persistent_memory_context(
        child_task=child_task,
        persistent_memory=persistent_memory,
    )
    persisted = store.create_task(child_task)
    artifact_store.ensure_task_dirs(persisted.task_id)
    artifact_store.write_task_snapshot(persisted)
    store.append_event(persisted.task_id, event_type, event_payload)
    if delivery_case_service is not None:
        delivery_case_service.ensure_case_for_task(persisted)
        delivery_case_service.queue_generator_run(task=persisted)
        delivery_case_service.sync_case_for_root(persisted.root_task_id or persisted.task_id)
        if base_task.status is TaskStatus.COMPLETED and base_task.delivery_status == "delivered":
            delivery_case_service.record_branch_spawned(
                incumbent_task=base_task,
                challenger_task=persisted,
            )
    if session_memory_service is not None:
        session_memory_service.record_task_created(persisted, attempt_kind=attempt_kind)
    payload = {
        "task_id": persisted.task_id,
        "status": persisted.status,
        "poll_after_ms": settings.default_poll_after_ms,
        "resource_refs": [task_resource_ref(persisted.task_id)],
        "display_title": persisted.display_title,
        "title_source": persisted.title_source,
    }
    if result_factory is not None:
        return result_factory(**payload)
    return SimpleNamespace(**payload)


def apply_memory_context(*, session_id: str | None, child_task: VideoTask, session_memory_service=None) -> None:
    if session_memory_service is None or session_id is None:
        return

    summary = session_memory_service.summarize_session_memory(session_id)
    if not summary.summary_text:
        return

    session_payload = _build_session_memory_payload(session_id=session_id, session_memory_service=session_memory_service, summary=summary)
    _apply_task_memory_section(child_task, "session", session_payload)
    child_task.memory_context_summary = summary.summary_text
    child_task.memory_context_digest = summary.summary_digest


def apply_persistent_memory_context(
    *,
    child_task: VideoTask,
    persistent_memory: PersistentMemoryContext | None,
) -> None:
    apply_persistent_memory_context_to_task(child_task, persistent_memory)


def _apply_task_memory_section(child_task: VideoTask, section: str, payload: dict[str, Any]) -> None:
    context = dict(child_task.task_memory_context or {})
    context[section] = payload
    child_task.task_memory_context = context


def _build_session_memory_payload(
    *,
    session_id: str,
    session_memory_service,
    summary,
) -> dict[str, Any]:
    if hasattr(session_memory_service, "build_continuity_context"):
        payload = session_memory_service.build_continuity_context(session_id)
        if isinstance(payload, dict):
            return dict(payload)
    return {
        "session_id": session_id,
        "summary_text": summary.summary_text,
        "summary_digest": summary.summary_digest,
        "entry_count": len(getattr(summary, "entries", []) or []),
        "lineage_refs": list(getattr(summary, "lineage_refs", []) or []),
        "entries": [entry.model_dump(mode="json") for entry in getattr(summary, "entries", []) or []],
    }
