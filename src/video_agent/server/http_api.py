from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.http_auth import (
    ResolvedAgentSession,
    current_internal_session_id,
    resolve_agent_session,
)
from video_agent.server.mcp_tools import (
    cancel_video_task_tool,
    create_video_task_tool,
    get_video_result_tool,
    get_video_task_tool,
    list_video_tasks_tool,
    retry_video_task_tool,
    revise_video_task_tool,
)


class SessionLoginRequest(BaseModel):
    agent_token: str


class CreateTaskRequest(BaseModel):
    prompt: str
    idempotency_key: str | None = None
    output_profile: dict[str, Any] | None = None
    style_hints: dict[str, Any] | None = None
    validation_profile: dict[str, Any] | None = None
    memory_ids: list[str] | None = None


class ReviseTaskRequest(BaseModel):
    feedback: str
    preserve_working_parts: bool = True
    memory_ids: list[str] | None = None


def _tool_payload_or_http_error(payload: dict[str, Any]) -> dict[str, Any]:
    error = payload.get("error")
    if error is None:
        return payload

    code = error.get("code", "bad_request")
    if code == "agent_not_authenticated":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=code)
    if code == "agent_access_denied":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=code)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)


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
        return {
            "agent_id": resolved.agent_principal.agent_id,
            "name": resolved.agent_principal.profile.name,
            "profile": resolved.agent_principal.profile.profile_json,
        }

    @app.delete("/api/sessions/current")
    def delete_session(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, bool]:
        context.agent_session_service.revoke_session(resolved.session_token)
        return {"revoked": True}

    @app.get("/api/memory/session")
    def get_session_memory(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, object]:
        snapshot = context.session_memory_service.get_session_memory(current_internal_session_id(resolved))
        payload = snapshot.model_dump(mode="json")
        payload.pop("session_id", None)
        payload["entry_count"] = snapshot.entry_count
        return payload

    @app.post("/api/tasks")
    def create_task(
        payload: CreateTaskRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            create_video_task_tool(
                context,
                {
                    "prompt": payload.prompt,
                    "idempotency_key": payload.idempotency_key,
                    "output_profile": payload.output_profile,
                    "style_hints": payload.style_hints,
                    "validation_profile": payload.validation_profile,
                    "memory_ids": payload.memory_ids,
                    "session_id": current_internal_session_id(resolved),
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/tasks")
    def list_tasks(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            list_video_tasks_tool(
                context,
                {},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            get_video_task_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/tasks/{task_id}/result")
    def get_task_result(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            get_video_result_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/revise")
    def revise_task(
        task_id: str,
        payload: ReviseTaskRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            revise_video_task_tool(
                context,
                {
                    "base_task_id": task_id,
                    "feedback": payload.feedback,
                    "preserve_working_parts": payload.preserve_working_parts,
                    "memory_ids": payload.memory_ids,
                    "session_id": current_internal_session_id(resolved),
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/retry")
    def retry_task(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            retry_video_task_tool(
                context,
                {
                    "task_id": task_id,
                    "session_id": current_internal_session_id(resolved),
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/cancel")
    def cancel_task(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return _tool_payload_or_http_error(
            cancel_video_task_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )

    return app
