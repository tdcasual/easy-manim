from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context
else:
    try:
        from mcp.server.fastmcp import Context
    except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional runtime dependency
        Context = Any

from video_agent.application.agent_identity_service import AgentPrincipal


class SessionAuthRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, AgentPrincipal] = {}

    def authenticate(self, session_key: str, principal: AgentPrincipal) -> AgentPrincipal:
        self._sessions[session_key] = principal
        return principal

    def get(self, session_key: str) -> AgentPrincipal | None:
        return self._sessions.get(session_key)

    def require(self, session_key: str) -> AgentPrincipal:
        principal = self.get(session_key)
        if principal is None:
            raise KeyError(f"Unknown session key: {session_key}")
        return principal


def session_key_for_context(ctx: Context) -> str:
    try:
        client_id = ctx.client_id
        if client_id:
            return client_id
        return f"session:{id(ctx.session)}"
    except ValueError:
        return "local-call"
