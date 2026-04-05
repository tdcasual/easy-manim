from __future__ import annotations

from typing import Any

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.server.app import AppContext
from video_agent.server.mcp_tools_auth import (
    _authorize_agent_action,
    _error_payload,
    _permission_error_code,
)


def create_video_thread_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:create")
        result = context.video_thread_service.create_thread(
            owner_agent_id=payload["owner_agent_id"],
            title=payload["title"],
            prompt=payload["prompt"],
            session_id=payload.get("session_id"),
            memory_ids=payload.get("memory_ids"),
            agent_principal=principal,
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    return result.model_dump(mode="json")


def append_video_turn_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "task:mutate")
        result = context.video_thread_service.append_turn(
            thread_id=payload["thread_id"],
            iteration_id=payload["iteration_id"],
            title=payload["title"],
            summary=payload.get("summary", ""),
            addressed_participant_id=payload.get("addressed_participant_id"),
            reply_to_turn_id=payload.get("reply_to_turn_id"),
            related_result_id=payload.get("related_result_id"),
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    except KeyError as exc:
        code = str(exc.args[0]) if exc.args else "thread_not_found"
        return _error_payload(code, code)
    return result.model_dump(mode="json")


def request_video_explanation_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "task:mutate")
        result = context.video_thread_service.request_explanation(
            thread_id=payload["thread_id"],
            iteration_id=payload["iteration_id"],
            summary=payload["summary"],
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    except KeyError as exc:
        code = str(exc.args[0]) if exc.args else "thread_not_found"
        return _error_payload(code, code)
    return result.model_dump(mode="json")


def select_video_result_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "task:mutate")
        result = context.video_thread_service.select_result(
            payload["thread_id"],
            payload["result_id"],
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    except KeyError as exc:
        code = str(exc.args[0]) if exc.args else "thread_not_found"
        return _error_payload(code, code)
    return result.model_dump(mode="json")


def get_video_thread_surface_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:read")
        surface = context.video_projection_service.build_surface(
            payload["thread_id"],
            viewer_agent_id=None if principal is None else principal.agent_id,
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    except KeyError:
        return _error_payload("thread_not_found", "thread_not_found")
    return surface.model_dump(mode="json")


def list_video_thread_participants_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "task:read")
        items = context.video_thread_service.list_participants(payload["thread_id"])
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    except KeyError:
        return _error_payload("thread_not_found", "thread_not_found")
    return {
        "thread_id": payload["thread_id"],
        "items": [item.model_dump(mode="json") for item in items],
    }


def upsert_video_thread_participant_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:mutate")
        result = context.video_thread_service.upsert_participant(
            thread_id=payload["thread_id"],
            participant_id=payload["participant_id"],
            participant_type=payload["participant_type"],
            agent_id=payload.get("agent_id"),
            role=payload["role"],
            display_name=payload["display_name"],
            capabilities=payload.get("capabilities"),
            agent_principal=principal,
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    except KeyError:
        return _error_payload("thread_not_found", "thread_not_found")
    return result.model_dump(mode="json")


def remove_video_thread_participant_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:mutate")
        result = context.video_thread_service.remove_participant(
            thread_id=payload["thread_id"],
            participant_id=payload["participant_id"],
            agent_principal=principal,
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    except KeyError:
        return _error_payload("thread_not_found", "thread_not_found")
    return result.model_dump(mode="json")


def request_video_revision_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        principal = _authorize_agent_action(context, agent_principal, "task:mutate")
        result = context.video_thread_service.request_revision(
            thread_id=payload["thread_id"],
            base_task_id=payload.get("base_task_id"),
            base_iteration_id=payload.get("iteration_id"),
            summary=payload["summary"],
            preserve_working_parts=payload.get("preserve_working_parts", True),
            session_id=payload.get("session_id"),
            memory_ids=payload.get("memory_ids"),
            agent_principal=principal,
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))
    except KeyError as exc:
        code = str(exc.args[0]) if exc.args else "thread_not_found"
        return _error_payload(code, code)
    return result.model_dump(mode="json")
