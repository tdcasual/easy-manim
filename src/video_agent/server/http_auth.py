from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, Request, status

from video_agent.application.agent_identity_service import AgentPrincipal


@dataclass
class ResolvedAgentSession:
    session_token: str
    session_id: str
    agent_principal: AgentPrincipal


def _extract_bearer(authorization: str | None) -> str:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_session_token")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_session_token")
    return token


def resolve_agent_session(
    request: Request,
    authorization: str | None = Header(default=None),
) -> ResolvedAgentSession:
    context = request.app.state.app_context
    plain_session_token = _extract_bearer(authorization)
    try:
        session = context.agent_session_service.resolve_session(plain_session_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token") from exc

    profile = context.store.get_agent_profile(session.agent_id)
    active_tokens = [token for token in context.store.list_agent_tokens(session.agent_id) if token.status == "active"]
    if profile is None or profile.status != "active" or not active_tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token")

    context.session_memory_registry.ensure_session(session.session_id, agent_id=session.agent_id)
    return ResolvedAgentSession(
        session_token=plain_session_token,
        session_id=session.session_id,
        agent_principal=AgentPrincipal(
            agent_id=session.agent_id,
            profile=profile,
            token=active_tokens[-1],
        ),
    )
