from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse

from video_agent.server.http_auth import ResolvedAgentSession, current_internal_session_id, resolve_agent_session
from video_agent.server.http_api_support import (
    LEGACY_DISCUSSION_TRANSPORT_REMOVED,
    ApplyReviewDecisionRequest,
    CreateTaskRequest,
    ReviseTaskRequest,
    WorkflowMemoryPinRequest,
    WorkflowParticipantUpsertRequest,
    allowed_task_artifact_resource_uri,
    download_url_from_resource_uri,
    permission_http_error,
    strip_internal_session_fields,
    tool_payload_or_http_error,
)
from video_agent.server.mcp_resources import guess_mime_type, resolve_resource_path
from video_agent.server.mcp_tools import (
    accept_best_version_tool,
    apply_review_decision_tool,
    cancel_video_task_tool,
    create_video_task_tool,
    get_quality_score_tool,
    get_recovery_plan_tool,
    get_review_bundle_tool,
    get_scene_spec_tool,
    get_video_result_tool,
    get_video_task_tool,
    list_video_tasks_tool,
    list_workflow_memory_recommendations_tool,
    list_workflow_participants_tool,
    pin_workflow_memory_tool,
    remove_workflow_participant_tool,
    retry_video_task_tool,
    revise_video_task_tool,
    unpin_workflow_memory_tool,
    upsert_workflow_participant_tool,
)


def register_task_routes(*, app: FastAPI, context) -> None:
    @app.post("/api/tasks")
    def create_task(
        payload: CreateTaskRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return tool_payload_or_http_error(
            create_video_task_tool(
                context,
                {
                    "prompt": payload.prompt,
                    "idempotency_key": payload.idempotency_key,
                    "output_profile": payload.output_profile,
                    "style_hints": payload.style_hints,
                    "validation_profile": payload.validation_profile,
                    "strategy_prompt_cluster": payload.strategy_prompt_cluster,
                    "memory_ids": payload.memory_ids,
                    "session_id": current_internal_session_id(resolved),
                    "source_kind": "http_control",
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/tasks")
    def list_tasks(resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return tool_payload_or_http_error(
            list_video_tasks_tool(
                context,
                {},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return tool_payload_or_http_error(
            get_video_task_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/tasks/{task_id}/scene-spec")
    def get_task_scene_spec(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        payload = tool_payload_or_http_error(
            get_scene_spec_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )
        return payload["scene_spec"]

    @app.get("/api/tasks/{task_id}/recovery-plan")
    def get_task_recovery_plan(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        payload = tool_payload_or_http_error(
            get_recovery_plan_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )
        return payload["recovery_plan"]

    @app.get("/api/tasks/{task_id}/quality-score")
    def get_task_quality_score(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        payload = tool_payload_or_http_error(
            get_quality_score_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )
        return payload["quality_score"]

    @app.get("/api/tasks/{task_id}/result")
    def get_task_result(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        try:
            payload = tool_payload_or_http_error(
                get_video_result_tool(
                    context,
                    {"task_id": task_id},
                    agent_principal=resolved.agent_principal,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task_not_found") from exc

        video_download_url = download_url_from_resource_uri(payload.get("video_resource"))
        if video_download_url is not None:
            payload["video_download_url"] = video_download_url

        preview_resources = payload.get("preview_frame_resources") or []
        preview_urls: list[str] = []
        if preview_resources:
            for uri in preview_resources:
                download_url = download_url_from_resource_uri(str(uri))
                if download_url is not None:
                    preview_urls.append(download_url)
        if preview_urls:
            payload["preview_download_urls"] = preview_urls

        script_download_url = download_url_from_resource_uri(payload.get("script_resource"))
        if script_download_url is not None:
            payload["script_download_url"] = script_download_url

        if payload.get("validation_report_resource"):
            validation_report_download_url = download_url_from_resource_uri(payload["validation_report_resource"])
            if validation_report_download_url is not None:
                payload["validation_report_download_url"] = validation_report_download_url
        return payload

    @app.get("/api/tasks/{task_id}/review-bundle")
    def get_task_review_bundle(
        task_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return strip_internal_session_fields(
            tool_payload_or_http_error(
                get_review_bundle_tool(
                    context,
                    {"task_id": task_id},
                    agent_principal=resolved.agent_principal,
                )
            )
        )

    @app.get("/api/tasks/{task_id}/discussion-thread")
    def get_task_discussion_thread(
        task_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        _ = (task_id, resolved)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=LEGACY_DISCUSSION_TRANSPORT_REMOVED,
        )

    @app.post("/api/tasks/{task_id}/review-decision")
    def apply_task_review_decision(
        task_id: str,
        payload: ApplyReviewDecisionRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return strip_internal_session_fields(
            tool_payload_or_http_error(
                apply_review_decision_tool(
                    context,
                    {
                        "task_id": task_id,
                        "review_decision": payload.review_decision.model_dump(mode="json"),
                        "memory_ids": payload.memory_ids,
                        "pin_workflow_memory_ids": payload.pin_workflow_memory_ids,
                        "unpin_workflow_memory_ids": payload.unpin_workflow_memory_ids,
                        "session_id": current_internal_session_id(resolved),
                        "source_kind": "http_control",
                    },
                    agent_principal=resolved.agent_principal,
                )
            )
        )

    @app.post("/api/tasks/{task_id}/discussion-messages")
    def create_task_discussion_message(
        task_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        _ = (task_id, resolved)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=LEGACY_DISCUSSION_TRANSPORT_REMOVED,
        )

    @app.get("/api/tasks/{task_id}/workflow-participants")
    def list_task_workflow_participants(
        task_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return tool_payload_or_http_error(
            list_workflow_participants_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/workflow-participants")
    def upsert_task_workflow_participant(
        task_id: str,
        payload: WorkflowParticipantUpsertRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return tool_payload_or_http_error(
            upsert_workflow_participant_tool(
                context,
                {
                    "task_id": task_id,
                    "agent_id": payload.agent_id,
                    "role": payload.role,
                    "capabilities": payload.capabilities,
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.delete("/api/tasks/{task_id}/workflow-participants/{agent_id}")
    def remove_task_workflow_participant(
        task_id: str,
        agent_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return tool_payload_or_http_error(
            remove_workflow_participant_tool(
                context,
                {
                    "task_id": task_id,
                    "agent_id": agent_id,
                },
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/tasks/{task_id}/workflow-memory/recommendations")
    def list_task_workflow_memory_recommendations(
        task_id: str,
        limit: int = 5,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return tool_payload_or_http_error(
            list_workflow_memory_recommendations_tool(
                context,
                {"task_id": task_id, "limit": limit},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/workflow-memory/pins")
    def pin_task_workflow_memory(
        task_id: str,
        payload: WorkflowMemoryPinRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return tool_payload_or_http_error(
            pin_workflow_memory_tool(
                context,
                {"task_id": task_id, "memory_id": payload.memory_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.delete("/api/tasks/{task_id}/workflow-memory/pins/{memory_id}")
    def unpin_task_workflow_memory(
        task_id: str,
        memory_id: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return tool_payload_or_http_error(
            unpin_workflow_memory_tool(
                context,
                {"task_id": task_id, "memory_id": memory_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.get("/api/videos/recent")
    def list_recent_videos(
        limit: int = 12,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        principal = resolved.agent_principal
        try:
            if context.settings.auth_mode == "required" and principal is None:
                raise PermissionError("agent_not_authenticated")
            if principal is not None:
                context.agent_identity_service.require_action(principal, "task:read")
        except PermissionError as exc:
            raise permission_http_error(exc) from exc

        agent_id = principal.agent_id if principal is not None else context.settings.anonymous_agent_id
        safe_limit = max(1, min(limit, 50))
        recent = context.task_service.list_recent_videos_for_agent(agent_id, limit=safe_limit)

        items: list[dict[str, Any]] = []
        for entry in recent:
            preview_path = entry.get("preview_path")
            preview_url = (
                f"/api/tasks/{entry['task_id']}/artifacts/previews/{preview_path.name}"
                if preview_path is not None
                else None
            )
            items.append(
                {
                    "task_id": entry["task_id"],
                    "thread_id": entry.get("thread_id"),
                    "display_title": entry["display_title"],
                    "title_source": entry["title_source"],
                    "status": entry["status"],
                    "updated_at": entry["updated_at"],
                    "latest_summary": entry["latest_summary"],
                    "latest_video_url": f"/api/tasks/{entry['task_id']}/artifacts/final_video.mp4",
                    "latest_preview_url": preview_url,
                }
            )
        return {"items": items, "next_cursor": None}

    @app.get("/api/tasks/{task_id}/artifacts/{artifact_path:path}")
    def download_task_artifact(
        task_id: str,
        artifact_path: str,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> FileResponse:
        try:
            context.agent_identity_service.require_action(resolved.agent_principal, "task:read")
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="agent_scope_denied") from exc

        try:
            resource_uri = allowed_task_artifact_resource_uri(task_id, artifact_path)
            resolved_task_id, target = resolve_resource_path(
                context,
                resource_uri,
                agent_id=resolved.agent_principal.agent_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="agent_access_denied") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task_not_found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found") from exc
        if resolved_task_id != task_id or not target.exists() or not target.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource_not_found")
        return FileResponse(target, media_type=guess_mime_type(target), filename=target.name)

    @app.post("/api/tasks/{task_id}/revise")
    def revise_task(
        task_id: str,
        payload: ReviseTaskRequest,
        resolved: ResolvedAgentSession = Depends(resolve_agent_session),
    ) -> dict[str, Any]:
        return tool_payload_or_http_error(
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
        return tool_payload_or_http_error(
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
        return tool_payload_or_http_error(
            cancel_video_task_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )

    @app.post("/api/tasks/{task_id}/accept-best")
    def accept_task_as_best(task_id: str, resolved: ResolvedAgentSession = Depends(resolve_agent_session)) -> dict[str, Any]:
        return tool_payload_or_http_error(
            accept_best_version_tool(
                context,
                {"task_id": task_id},
                agent_principal=resolved.agent_principal,
            )
        )
