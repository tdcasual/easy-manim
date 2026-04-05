from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.server.http_auth import ResolvedAgentSession, resolve_agent_session
from video_agent.server.http_api_support import SessionLoginRequest, permission_http_error


def register_identity_routes(*, app: FastAPI, context) -> None:
    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/api/runtime/status")
    def runtime_status(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if context.settings.auth_mode == "required":
            resolved = resolve_agent_session(request, authorization=authorization)
            try:
                context.agent_identity_service.require_action(resolved.agent_principal, "task:read")
            except PermissionError as exc:
                raise permission_http_error(exc) from exc
        return context.runtime_service.inspect().model_dump(mode="json")

    @app.post("/api/sessions")
    def create_session(payload: SessionLoginRequest) -> dict[str, object]:
        try:
            created = context.agent_session_service.create_session(payload.agent_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_agent_token") from exc

        context.session_auth.authenticate(
            created.session.session_id,
            AgentPrincipal(
                agent_id=created.profile.agent_id,
                profile=created.profile,
                token=created.token,
            ),
        )
        context.session_memory_registry.ensure_session(
            created.session.session_id,
            agent_id=created.profile.agent_id,
        )
        return {
            "session_token": created.session_token,
            "agent_id": created.profile.agent_id,
            "name": created.profile.name,
            "expires_at": created.session.expires_at.isoformat(),
        }

    @app.get("/api/whoami")
    def whoami(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return {
            "agent_id": resolved.agent_principal.agent_id,
            "name": resolved.agent_principal.profile.name,
            "profile": resolved.agent_principal.profile.profile_json,
        }

    @app.delete("/api/sessions/current")
    def delete_session(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, bool]:
        context.agent_session_service.revoke_session(resolved.session_token)
        return {"revoked": True}

    @app.get("/api/profile")
    def get_profile(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        profile = context.store.get_agent_profile(resolved.agent_principal.agent_id)
        if profile is None or profile.status != "active":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session_token")

        return {
            "agent_id": profile.agent_id,
            "name": profile.name,
            "status": profile.status,
            "profile_version": profile.profile_version,
            "profile_json": profile.profile_json,
            "policy_json": profile.policy_json,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
            "profile": profile.profile_json,
            "policy": profile.policy_json,
        }

    @app.get("/api/profile/scorecard")
    def profile_scorecard(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "profile:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return context.agent_learning_service.build_scorecard(resolved.agent_principal.agent_id)
