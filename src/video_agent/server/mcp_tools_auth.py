from __future__ import annotations

from typing import Any

from video_agent.application.agent_identity_service import AgentPrincipal
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


def _permission_error_code(exc: PermissionError) -> str:
    code = str(exc)
    if code in {"agent_not_authenticated", "agent_access_denied", "agent_scope_denied"}:
        return code
    return "agent_access_denied"


def _require_agent_principal(
    context: AppContext,
    agent_principal: AgentPrincipal | None,
) -> AgentPrincipal | None:
    if context.settings.auth_mode != "required":
        return agent_principal
    if agent_principal is None:
        raise PermissionError("agent_not_authenticated")
    return agent_principal


def _resolve_memory_agent_id(
    context: AppContext,
    agent_principal: AgentPrincipal | None,
) -> str:
    principal = _require_agent_principal(context, agent_principal)
    if principal is None:
        return context.settings.anonymous_agent_id
    return principal.agent_id


def _authorize_agent_action(
    context: AppContext,
    agent_principal: AgentPrincipal | None,
    action: str,
) -> AgentPrincipal | None:
    principal = _require_agent_principal(context, agent_principal)
    if principal is not None:
        context.agent_identity_service.require_action(principal, action)
    return principal
