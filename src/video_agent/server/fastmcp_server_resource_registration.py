from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.server.app import AppContext
from video_agent.server.mcp_resources import authorize_resource_access, read_resource, read_resource_for_agent
from video_agent.server.mcp_tools import get_video_thread_surface_tool


def register_resources(
    *,
    mcp: FastMCP,
    context: AppContext,
    current_principal: Callable[[Context | None], AgentPrincipal | None],
) -> None:
    @mcp.resource("video-task://{task_id}/task.json", mime_type="application/json")
    def task_resource(task_id: str, ctx: Context | None = None) -> str:
        return _read_text_resource(context, f"video-task://{task_id}/task.json", agent_principal=current_principal(ctx))

    @mcp.resource("video-task://{task_id}/artifacts/current_script.py", mime_type="text/x-python")
    def script_resource(task_id: str, ctx: Context | None = None) -> str:
        return _read_text_resource(
            context,
            f"video-task://{task_id}/artifacts/current_script.py",
            agent_principal=current_principal(ctx),
        )

    @mcp.resource("video-task://{task_id}/artifacts/failure_context.json", mime_type="application/json")
    def failure_context_resource(task_id: str, ctx: Context | None = None) -> str:
        return _read_text_resource(
            context,
            f"video-task://{task_id}/artifacts/failure_context.json",
            agent_principal=current_principal(ctx),
        )

    @mcp.resource("video-task://{task_id}/artifacts/failure_contract.json", mime_type="application/json")
    def failure_contract_resource(task_id: str, ctx: Context | None = None) -> str:
        return _read_text_resource(
            context,
            f"video-task://{task_id}/artifacts/failure_contract.json",
            agent_principal=current_principal(ctx),
        )

    @mcp.resource("video-task://{task_id}/artifacts/final_video.mp4", mime_type="video/mp4")
    def video_resource(task_id: str, ctx: Context | None = None) -> bytes:
        return _read_binary_resource(
            context,
            task_id,
            Path("artifacts/final_video.mp4"),
            agent_principal=current_principal(ctx),
        )

    @mcp.resource("video-task://{task_id}/artifacts/previews/{frame_name}", mime_type="image/png")
    def preview_resource(task_id: str, frame_name: str, ctx: Context | None = None) -> bytes:
        return _read_binary_resource(
            context,
            task_id,
            Path("artifacts/previews") / frame_name,
            agent_principal=current_principal(ctx),
        )

    @mcp.resource("video-task://{task_id}/validations/{report_name}", mime_type="application/json")
    def validation_resource(task_id: str, report_name: str, ctx: Context | None = None) -> str:
        return _read_text_resource(
            context,
            f"video-task://{task_id}/validations/{report_name}",
            agent_principal=current_principal(ctx),
        )

    @mcp.resource("video-task://{task_id}/logs/events.jsonl", mime_type="application/jsonl")
    def log_resource(task_id: str, ctx: Context | None = None) -> str:
        return _read_text_resource(
            context,
            f"video-task://{task_id}/logs/events.jsonl",
            agent_principal=current_principal(ctx),
        )

    @mcp.resource("video-thread://{thread_id}/surface.json", mime_type="application/json")
    def video_thread_surface_resource(thread_id: str, ctx: Context | None = None) -> str:
        return _read_video_thread_surface_resource(
            context,
            thread_id,
            agent_principal=current_principal(ctx),
        )

    @mcp.resource("video-thread://{thread_id}/timeline.json", mime_type="application/json")
    def video_thread_timeline_resource(thread_id: str, ctx: Context | None = None) -> str:
        return _read_video_thread_timeline_resource(
            context,
            thread_id,
            agent_principal=current_principal(ctx),
        )

    @mcp.resource("video-thread://{thread_id}/iterations/{iteration_id}.json", mime_type="application/json")
    def video_thread_iteration_resource(
        thread_id: str,
        iteration_id: str,
        ctx: Context | None = None,
    ) -> str:
        return _read_video_thread_iteration_resource(
            context,
            thread_id,
            iteration_id,
            agent_principal=current_principal(ctx),
        )


def _read_text_resource(
    context: AppContext,
    uri: str,
    *,
    agent_principal: AgentPrincipal | None = None,
) -> str:
    if context.settings.auth_mode != "required":
        return read_resource(context, uri)
    if agent_principal is None:
        raise PermissionError("agent_not_authenticated")
    return read_resource_for_agent(context, uri, agent_principal.agent_id)


def _read_binary_resource(
    context: AppContext,
    task_id: str,
    relative_path: Path,
    *,
    agent_principal: AgentPrincipal | None = None,
) -> bytes:
    authorize_resource_access(context, task_id, agent_principal=agent_principal)
    target = context.artifact_store.task_dir(task_id) / relative_path
    return target.read_bytes()


def _read_video_thread_surface_resource(
    context: AppContext,
    thread_id: str,
    *,
    agent_principal: AgentPrincipal | None = None,
) -> str:
    surface = get_video_thread_surface_tool(
        context,
        {"thread_id": thread_id},
        agent_principal=agent_principal,
    )
    return json.dumps(surface, indent=2)


def _read_video_thread_timeline_resource(
    context: AppContext,
    thread_id: str,
    *,
    agent_principal: AgentPrincipal | None = None,
) -> str:
    if agent_principal is not None:
        context.agent_identity_service.require_action(agent_principal, "task:read")
    payload = context.video_projection_service.build_timeline_payload(thread_id)
    return json.dumps(payload, indent=2)


def _read_video_thread_iteration_resource(
    context: AppContext,
    thread_id: str,
    iteration_id: str,
    *,
    agent_principal: AgentPrincipal | None = None,
) -> str:
    if agent_principal is not None:
        context.agent_identity_service.require_action(agent_principal, "task:read")
    payload = context.video_projection_service.build_iteration_payload(thread_id, iteration_id)
    return json.dumps(payload, indent=2)
