from __future__ import annotations

from typing import Any

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.persistent_memory_service import PersistentMemoryError
from video_agent.server.app import AppContext
from video_agent.server.mcp_tools_auth import (
    _authorize_agent_action,
    _error_payload,
    _permission_error_code,
    _resolve_memory_agent_id,
)


def get_session_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")
    try:
        _authorize_agent_action(context, agent_principal, "memory:read")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

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
    agent_principal: AgentPrincipal | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")
    try:
        _authorize_agent_action(context, agent_principal, "memory:read")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    summary = context.session_memory_service.summarize_session_memory(resolved_session_id)
    return {
        "session_id": summary.session_id,
        "agent_id": summary.agent_id,
        "entries": [entry.model_dump(mode="json") for entry in summary.entries],
        "entry_count": summary.entry_count,
        "lineage_refs": summary.lineage_refs,
        "summary_text": summary.summary_text,
        "summary_digest": summary.summary_digest,
    }


def clear_session_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")
    try:
        _authorize_agent_action(context, agent_principal, "memory:clear")
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    before = context.session_memory_service.get_session_memory(resolved_session_id)
    snapshot = context.session_memory_service.clear_session_memory(resolved_session_id)
    return {
        "session_id": snapshot.session_id,
        "agent_id": snapshot.agent_id,
        "entries": [entry.model_dump(mode="json") for entry in snapshot.entries],
        "entry_count": snapshot.entry_count,
        "cleared": True,
        "cleared_entry_count": before.entry_count,
        "cleared_attempt_count": sum(len(entry.attempts) for entry in before.entries),
    }


def promote_session_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    resolved_session_id = _resolve_session_id(payload, session_id)
    if resolved_session_id is None:
        return _error_payload("session_id_required", "session_id is required")

    try:
        _authorize_agent_action(context, agent_principal, "memory:promote")
        record = context.persistent_memory_service.promote_session_memory(
            resolved_session_id,
            agent_id=_resolve_memory_agent_id(context, agent_principal),
        )
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    return record.model_dump(mode="json")


def list_agent_memories_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "memory:read")
        records = context.persistent_memory_service.list_agent_memories(
            _resolve_memory_agent_id(context, agent_principal),
            include_disabled=payload.get("include_disabled", False),
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    return {"items": [record.model_dump(mode="json") for record in records]}


def get_agent_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "memory:read")
        record = context.persistent_memory_service.get_agent_memory(
            payload["memory_id"],
            agent_id=_resolve_memory_agent_id(context, agent_principal),
        )
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    return record.model_dump(mode="json")


def disable_agent_memory_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "memory:write")
        record = context.persistent_memory_service.disable_agent_memory(
            payload["memory_id"],
            agent_id=_resolve_memory_agent_id(context, agent_principal),
        )
    except PersistentMemoryError as exc:
        return _error_payload(exc.code, str(exc))
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    return record.model_dump(mode="json")


def query_agent_memories_tool(
    context: AppContext,
    payload: dict[str, Any],
    *,
    agent_principal: AgentPrincipal | None = None,
) -> dict[str, Any]:
    try:
        _authorize_agent_action(context, agent_principal, "memory:read")
        items = context.persistent_memory_service.query_agent_memories(
            _resolve_memory_agent_id(context, agent_principal),
            query=payload.get("query", ""),
            limit=payload.get("limit", 5),
        )
    except PermissionError as exc:
        return _error_payload(_permission_error_code(exc), str(exc))

    return {"items": [item.model_dump(mode="json") for item in items]}


def _resolve_session_id(payload: dict[str, Any], session_id: str | None) -> str | None:
    return session_id or payload.get("session_id")
