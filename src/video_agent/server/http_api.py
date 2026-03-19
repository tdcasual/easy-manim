from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.http_auth import ResolvedAgentSession, resolve_agent_session


class SessionLoginRequest(BaseModel):
    agent_token: str


def create_http_api(settings: Settings) -> FastAPI:
    context = create_app_context(settings)
    app = FastAPI(title="easy-manim API", version="0.1.0")
    app.state.app_context = context

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ready"}

    @app.post("/api/sessions")
    def create_session(payload: SessionLoginRequest) -> dict[str, object]:
        try:
            created = context.agent_session_service.create_session(payload.agent_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_agent_token") from exc

        context.session_memory_registry.ensure_session(
            created.session.session_id,
            agent_id=created.profile.agent_id,
        )
        return {
            "session_token": created.session_token,
            "session_id": created.session.session_id,
            "agent_id": created.profile.agent_id,
            "name": created.profile.name,
            "expires_at": created.session.expires_at.isoformat(),
        }

    @app.get("/api/whoami")
    def whoami(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
        return {
            "agent_id": resolved.agent_principal.agent_id,
            "name": resolved.agent_principal.profile.name,
            "profile": resolved.agent_principal.profile.profile_json,
            "session_id": resolved.session_id,
        }

    @app.delete("/api/sessions/current")
    def delete_session(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, bool]:
        context.agent_session_service.revoke_session(resolved.session_token)
        return {"revoked": True}

    return app
