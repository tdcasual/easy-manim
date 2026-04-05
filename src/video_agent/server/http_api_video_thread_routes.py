from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status

from video_agent.server.http_auth import current_internal_session_id
from video_agent.server.http_api_support import (
    AppendVideoTurnRequest,
    CreateVideoThreadRequest,
    RequestVideoExplanationRequest,
    RequestVideoThreadRevisionRequest,
    SelectVideoResultRequest,
    VideoThreadParticipantUpsertRequest,
    permission_http_error,
    tool_payload_or_http_error,
)
from video_agent.server.mcp_tools import (
    append_video_turn_tool,
    create_video_thread_tool,
    get_video_thread_surface_tool,
    list_video_thread_participants_tool,
    remove_video_thread_participant_tool,
    request_video_explanation_tool,
    request_video_revision_tool,
    select_video_result_tool,
    upsert_video_thread_participant_tool,
)


def register_video_thread_routes(
    *,
    app: FastAPI,
    context,
    resolve_optional_agent_session,
) -> None:
    @app.post("/api/video-threads")
    def create_video_thread(
        payload: CreateVideoThreadRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        principal = None if resolved is None else resolved.agent_principal
        owner_agent_id = (
            payload.owner_agent_id
            or (None if principal is None else principal.agent_id)
            or context.settings.anonymous_agent_id
        )
        return tool_payload_or_http_error(
            create_video_thread_tool(
                context,
                {
                    "owner_agent_id": owner_agent_id,
                    "title": payload.title,
                    "prompt": payload.prompt,
                    "memory_ids": payload.memory_ids,
                    "session_id": None if resolved is None else current_internal_session_id(resolved),
                },
                agent_principal=principal,
            )
        )

    @app.get("/api/video-threads/{thread_id}")
    def get_video_thread(
        thread_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        try:
            if resolved is not None and resolved.agent_principal is not None:
                context.agent_identity_service.require_action(resolved.agent_principal, "task:read")
            thread = context.video_thread_service.load_thread(thread_id)
        except PermissionError as exc:
            raise permission_http_error(exc) from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="thread_not_found") from exc
        return thread.model_dump(mode="json")

    @app.get("/api/video-threads/{thread_id}/surface")
    def get_video_thread_surface(
        thread_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        return tool_payload_or_http_error(
            get_video_thread_surface_tool(
                context,
                {"thread_id": thread_id},
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.get("/api/video-threads/{thread_id}/iterations/{iteration_id}")
    def get_video_thread_iteration(
        thread_id: str,
        iteration_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        try:
            if resolved is not None and resolved.agent_principal is not None:
                context.agent_identity_service.require_action(resolved.agent_principal, "task:read")
            return context.video_projection_service.build_iteration_payload(thread_id, iteration_id)
        except PermissionError as exc:
            raise permission_http_error(exc) from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="iteration_not_found") from exc

    @app.post("/api/video-threads/{thread_id}/turns")
    def append_video_thread_turn(
        thread_id: str,
        payload: AppendVideoTurnRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        return tool_payload_or_http_error(
            append_video_turn_tool(
                context,
                {
                    "thread_id": thread_id,
                    "iteration_id": payload.iteration_id,
                    "title": payload.title,
                    "summary": payload.summary,
                    "addressed_participant_id": payload.addressed_participant_id,
                    "reply_to_turn_id": payload.reply_to_turn_id,
                    "related_result_id": payload.related_result_id,
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.post("/api/video-threads/{thread_id}/iterations/{iteration_id}/request-revision")
    def request_video_thread_revision(
        thread_id: str,
        iteration_id: str,
        payload: RequestVideoThreadRevisionRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        return tool_payload_or_http_error(
            request_video_revision_tool(
                context,
                {
                    "thread_id": thread_id,
                    "iteration_id": iteration_id,
                    "summary": payload.summary,
                    "preserve_working_parts": payload.preserve_working_parts,
                    "memory_ids": payload.memory_ids,
                    "session_id": None if resolved is None else current_internal_session_id(resolved),
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.post("/api/video-threads/{thread_id}/iterations/{iteration_id}/request-explanation")
    def request_video_thread_explanation(
        thread_id: str,
        iteration_id: str,
        payload: RequestVideoExplanationRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        return tool_payload_or_http_error(
            request_video_explanation_tool(
                context,
                {
                    "thread_id": thread_id,
                    "iteration_id": iteration_id,
                    "summary": payload.summary,
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.post("/api/video-threads/{thread_id}/iterations/{iteration_id}/select-result")
    def select_video_thread_result(
        thread_id: str,
        iteration_id: str,
        payload: SelectVideoResultRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        return tool_payload_or_http_error(
            select_video_result_tool(
                context,
                {
                    "thread_id": thread_id,
                    "iteration_id": iteration_id,
                    "result_id": payload.result_id,
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.get("/api/video-threads/{thread_id}/participants")
    def list_video_thread_participants(
        thread_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        return tool_payload_or_http_error(
            list_video_thread_participants_tool(
                context,
                {"thread_id": thread_id},
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.post("/api/video-threads/{thread_id}/participants")
    def upsert_video_thread_participant(
        thread_id: str,
        payload: VideoThreadParticipantUpsertRequest,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        return tool_payload_or_http_error(
            upsert_video_thread_participant_tool(
                context,
                {
                    "thread_id": thread_id,
                    "participant_id": payload.participant_id,
                    "participant_type": payload.participant_type,
                    "agent_id": payload.agent_id,
                    "role": payload.role,
                    "display_name": payload.display_name,
                    "capabilities": payload.capabilities,
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )

    @app.delete("/api/video-threads/{thread_id}/participants/{participant_id}")
    def remove_video_thread_participant(
        thread_id: str,
        participant_id: str,
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        resolved = resolve_optional_agent_session(request, authorization)
        return tool_payload_or_http_error(
            remove_video_thread_participant_tool(
                context,
                {
                    "thread_id": thread_id,
                    "participant_id": participant_id,
                },
                agent_principal=None if resolved is None else resolved.agent_principal,
            )
        )
