from __future__ import annotations

from typing import Any

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.errors import AdmissionControlError
from video_agent.server.app import AppContext



def authenticate_agent_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    session_key: str | None = None,
) -> dict[str, Any]:
    principal = context.agent_identity_service.authenticate(payload["agent_token"])
    if session_key is not None:
        context.session_auth.authenticate(session_key, principal)
        context.session_memory_registry.ensure_session(session_key, agent_id=principal.agent_id)
    return {
        "authenticated": True,
        "agent_id": principal.agent_id,
        "name": principal.profile.name,
        "profile": principal.profile.profile_json,
    }


def _error_payload(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


def _require_agent_principal(
    context: AppContext,
    agent_principal: AgentPrincipal | None,
) -> AgentPrincipal | None:
    if context.settings.auth_mode != "required":
        return agent_principal
    if agent_principal is None:
        raise PermissionError("agent_not_authenticated")
    return agent_principal


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
            feedback=payload.get("feedback"),
            session_id=payload.get("session_id"),
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        code = "agent_not_authenticated" if str(exc) == "agent_not_authenticated" else "agent_access_denied"
        return _error_payload(code, str(exc))
    return result.model_dump(mode="json")


def get_video_task_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _require_agent_principal(context, agent_principal)
        if principal is None:
            result = context.task_service.get_video_task(payload["task_id"])
        else:
            result = context.task_service.get_video_task_for_agent(payload["task_id"], principal.agent_id)
    except PermissionError as exc:
        code = "agent_not_authenticated" if str(exc) == "agent_not_authenticated" else "agent_access_denied"
        return _error_payload(code, str(exc))
    return result.model_dump(mode="json")


def get_failure_contract_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _require_agent_principal(context, agent_principal)
        failure_contract = (
            context.task_service.get_failure_contract(payload["task_id"])
            if principal is None
            else context.task_service.get_failure_contract_for_agent(payload["task_id"], principal.agent_id)
        )
    except PermissionError as exc:
        code = "agent_not_authenticated" if str(exc) == "agent_not_authenticated" else "agent_access_denied"
        return _error_payload(code, str(exc))
    return {"task_id": payload["task_id"], "failure_contract": failure_contract}


def list_video_tasks_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _require_agent_principal(context, agent_principal)
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
        code = "agent_not_authenticated" if str(exc) == "agent_not_authenticated" else "agent_access_denied"
        return _error_payload(code, str(exc))
    return {"items": items, "next_cursor": None}


def get_task_events_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _require_agent_principal(context, agent_principal)
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
        code = "agent_not_authenticated" if str(exc) == "agent_not_authenticated" else "agent_access_denied"
        return _error_payload(code, str(exc))
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
        code = "agent_not_authenticated" if str(exc) == "agent_not_authenticated" else "agent_access_denied"
        return _error_payload(code, str(exc))
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
            agent_principal=agent_principal,
        )
    except AdmissionControlError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        code = "agent_not_authenticated" if str(exc) == "agent_not_authenticated" else "agent_access_denied"
        return _error_payload(code, str(exc))
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
        code = "agent_not_authenticated" if str(exc) == "agent_not_authenticated" else "agent_access_denied"
        return _error_payload(code, str(exc))
    return {"task_id": payload["task_id"], "status": "cancelled"}


def get_video_result_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _require_agent_principal(context, agent_principal)
        result = (
            context.task_service.get_video_result(payload["task_id"])
            if principal is None
            else context.task_service.get_video_result_for_agent(payload["task_id"], principal.agent_id)
        )
    except PermissionError as exc:
        code = "agent_not_authenticated" if str(exc) == "agent_not_authenticated" else "agent_access_denied"
        return _error_payload(code, str(exc))
    return result.model_dump(mode="json")


def get_session_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")

    snapshot = context.session_memory_service.get_session_memory(resolved_session_id)
    return {
        "session_id": snapshot.session_id,
        "agent_id": snapshot.agent_id,
        "entries": [entry.model_dump(mode="json") for entry in snapshot.entries],
        "entry_count": snapshot.entry_count,
    }


def summarize_session_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")

    summary = context.session_memory_service.summarize_session_memory(resolved_session_id)
    return {
        "session_id": summary.session_id,
        "agent_id": summary.agent_id,
        "entries": [entry.model_dump(mode="json") for entry in summary.entries],
        "entry_count": summary.entry_count,
        "summary_text": summary.summary_text,
        "summary_digest": summary.summary_digest,
    }


def clear_session_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")

    before = context.session_memory_service.get_session_memory(resolved_session_id)
    snapshot = context.session_memory_service.clear_session_memory(resolved_session_id)
    return {
        "session_id": snapshot.session_id,
        "agent_id": snapshot.agent_id,
        "entries": [entry.model_dump(mode="json") for entry in snapshot.entries],
        "entry_count": snapshot.entry_count,
        "cleared": True,
        "cleared_entry_count": before.entry_count,
    }


def _resolve_session_id(payload: dict[str, Any], session_id: str | None) -> str | None:
    return session_id or payload.get("session_id")
