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
    bound_token = context.store.get_agent_token(session.token_hash)
    if (
        profile is None
        or profile.status != "active"
        or bound_token is None
        or bound_token.status != "active"
        or bound_token.agent_id != session.agent_id
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token")

    principal = AgentPrincipal(
        agent_id=session.agent_id,
        profile=profile,
        token=bound_token,
    )
    context.session_auth.authenticate(session.session_id, principal)

    context.session_memory_registry.ensure_session(session.session_id, agent_id=session.agent_id)
    return ResolvedAgentSession(
        session_token=plain_session_token,
        session_id=session.session_id,
        agent_principal=principal,
    )


def current_internal_session_id(resolved: ResolvedAgentSession) -> str:
    return resolved.session_id
