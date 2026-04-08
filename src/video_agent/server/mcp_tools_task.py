from __future__ import annotations

from typing import Any

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.errors import AdmissionControlError
from video_agent.application.persistent_memory_service import PersistentMemoryError
from video_agent.server.app import AppContext
from video_agent.server.mcp_tools_auth import (
    _authorize_agent_action,
    _error_payload,
    _permission_error_code,
)


def create_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        result = context.task_service.create_video_task(
            prompt=payload["prompt"],
            idempotency_key=payload.get("idempotency_key"),
            output_profile=payload.get("output_profile"),
            style_hints=payload.get("style_hints"),
            validation_profile=payload.get("validation_profile"),
            strategy_prompt_cluster=payload.get("strategy_prompt_cluster"),
            feedback=payload.get("feedback"),
            session_id=payload.get("session_id"),
            memory_ids=payload.get("memory_ids"),
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    if agent_principal is not None and payload.get("session_id"):
        task = context.store.get_task(result.task_id)
        context.agent_runtime_run_service.record_task_invocation(
            session_id=str(payload["session_id"]),
            principal=agent_principal,
            source_kind=str(payload.get("source_kind", "task_api")),
            trigger_kind="create_video_task",
            task_id=result.task_id,
            thread_id=None if task is None else task.thread_id,
            iteration_id=None if task is None else task.iteration_id,
            summary=f"Created video task for prompt: {payload['prompt']}",
        )
    return result.model_dump(mode="json")


def get_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        if principal is None:
            result = context.task_service.get_video_task(payload["task_id"])
        else:
            result = context.task_service.get_video_task_for_agent(payload["task_id"], principal.agent_id)
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")


def get_failure_contract_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        failure_contract = (
            context.task_service.get_failure_contract(payload["task_id"])
            if principal is None
            else context.task_service.get_failure_contract_for_agent(payload["task_id"], principal.agent_id)
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {"task_id": payload["task_id"], "failure_contract": failure_contract}


def get_scene_spec_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        scene_spec = (
            context.task_service.get_scene_spec(payload["task_id"])
            if principal is None
            else context.task_service.get_scene_spec_for_agent(payload["task_id"], principal.agent_id)
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    if scene_spec is None:
        return _error_payload("scene_spec_not_found", "scene_spec_not_found")
    return {"task_id": payload["task_id"], "scene_spec": scene_spec}


def get_recovery_plan_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        recovery_plan = (
            context.task_service.get_recovery_plan(payload["task_id"])
            if principal is None
            else context.task_service.get_recovery_plan_for_agent(payload["task_id"], principal.agent_id)
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    if recovery_plan is None:
        return _error_payload("recovery_plan_not_found", "recovery_plan_not_found")
    return {"task_id": payload["task_id"], "recovery_plan": recovery_plan}


def get_quality_score_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        quality_score = (
            context.task_service.get_quality_score(payload["task_id"])
            if principal is None
            else context.task_service.get_quality_score_for_agent(payload["task_id"], principal.agent_id)
        )
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    if quality_score is None:
        return _error_payload("quality_score_not_found", "quality_score_not_found")
    return {"task_id": payload["task_id"], "quality_score": quality_score}


def list_video_tasks_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        items = (
            context.task_service.list_video_tasks(
                limit=payload.get("limit", 50),
                status=payload.get("status"),
            )
            if principal is None
            else context.task_service.list_video_tasks_for_agent(
                principal.agent_id,
                limit=payload.get("limit", 50),
                status=payload.get("status"),
            )
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {"items": items, "next_cursor": None}


def get_task_events_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        items = (
            context.task_service.get_task_events(
                payload["task_id"],
                limit=payload.get("limit", 200),
            )
            if principal is None
            else context.task_service.get_task_events_for_agent(
                payload["task_id"],
                principal.agent_id,
                limit=payload.get("limit", 200),
            )
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {"items": items, "next_cursor": None}


def get_metrics_snapshot_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "counters": dict(context.metrics.counters),
        "timings": {name: list(values) for name, values in context.metrics.timings.items()},
    }


def get_runtime_status_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    return context.runtime_service.inspect().model_dump(mode="json")


def retry_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        result = context.task_service.retry_video_task(
            payload["task_id"],
            session_id=payload.get("session_id"),
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    if agent_principal is not None and payload.get("session_id"):
        task = context.store.get_task(result.task_id)
        context.agent_runtime_run_service.record_task_invocation(
            session_id=str(payload["session_id"]),
            principal=agent_principal,
            source_kind=str(payload.get("source_kind", "task_api")),
            trigger_kind="retry_video_task",
            task_id=result.task_id,
            thread_id=None if task is None else task.thread_id,
            iteration_id=None if task is None else task.iteration_id,
            summary=f"Retried task {payload['task_id']}",
        )
    return result.model_dump(mode="json")


def revise_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        result = context.task_service.revise_video_task(
            base_task_id=payload["base_task_id"],
            feedback=payload["feedback"],
            preserve_working_parts=payload.get("preserve_working_parts", True),
            session_id=payload.get("session_id"),
            memory_ids=payload.get("memory_ids"),
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    if agent_principal is not None and payload.get("session_id"):
        task = context.store.get_task(result.task_id)
        context.agent_runtime_run_service.record_task_invocation(
            session_id=str(payload["session_id"]),
            principal=agent_principal,
            source_kind=str(payload.get("source_kind", "task_api")),
            trigger_kind="revise_video_task",
            task_id=result.task_id,
            thread_id=None if task is None else task.thread_id,
            iteration_id=None if task is None else task.iteration_id,
            summary=f"Created revision from {payload['base_task_id']}",
        )
    return result.model_dump(mode="json")


def cancel_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        context.task_service.cancel_video_task(payload["task_id"], agent_principal=agent_principal)
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return {"task_id": payload["task_id"], "status": "cancelled"}


def accept_best_version_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        snapshot = context.task_service.accept_best_version(
            payload["task_id"],
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except KeyError:
        return _error_payload("task_not_found", "task_not_found")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    except ValueError as exc:
        return _error_payload("invalid_task_state", str(exc))
    return {
        "task_id": snapshot.task_id,
        "accepted_as_best": snapshot.accepted_as_best,
        "accepted_version_rank": snapshot.accepted_version_rank,
    }


def get_video_result_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        result = (
            context.task_service.get_video_result(payload["task_id"])
            if principal is None
            else context.task_service.get_video_result_for_agent(payload["task_id"], principal.agent_id)
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")
