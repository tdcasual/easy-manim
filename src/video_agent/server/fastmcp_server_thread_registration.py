from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.server.app import AppContext
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


def register_thread_tools(
    *,
    mcp: FastMCP,
    context: AppContext,
    current_principal: Callable[[Context | None], AgentPrincipal | None],
    current_session_id: Callable[[Context | None], str | None],
) -> None:
    @mcp.tool(name="create_video_thread")
    def create_video_thread(
        owner_agent_id: str,
        title: str,
        prompt: str,
        memory_ids: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return create_video_thread_tool(
            context,
            {
                "owner_agent_id": owner_agent_id,
                "title": title,
                "prompt": prompt,
                "memory_ids": memory_ids,
                "session_id": current_session_id(ctx),
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_video_thread_surface")
    def get_video_thread_surface(thread_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return get_video_thread_surface_tool(
            context,
            {"thread_id": thread_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="append_video_turn")
    def append_video_turn(
        thread_id: str,
        iteration_id: str,
        title: str,
        summary: str = "",
        addressed_participant_id: str | None = None,
        reply_to_turn_id: str | None = None,
        related_result_id: str | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return append_video_turn_tool(
            context,
            {
                "thread_id": thread_id,
                "iteration_id": iteration_id,
                "title": title,
                "summary": summary,
                "addressed_participant_id": addressed_participant_id,
                "reply_to_turn_id": reply_to_turn_id,
                "related_result_id": related_result_id,
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="list_video_thread_participants")
    def list_video_thread_participants(thread_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return list_video_thread_participants_tool(
            context,
            {"thread_id": thread_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="upsert_video_thread_participant")
    def upsert_video_thread_participant(
        thread_id: str,
        participant_id: str,
        participant_type: str,
        role: str,
        display_name: str,
        agent_id: str | None = None,
        capabilities: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return upsert_video_thread_participant_tool(
            context,
            {
                "thread_id": thread_id,
                "participant_id": participant_id,
                "participant_type": participant_type,
                "agent_id": agent_id,
                "role": role,
                "display_name": display_name,
                "capabilities": capabilities,
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="remove_video_thread_participant")
    def remove_video_thread_participant(
        thread_id: str,
        participant_id: str,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return remove_video_thread_participant_tool(
            context,
            {
                "thread_id": thread_id,
                "participant_id": participant_id,
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="request_video_revision")
    def request_video_revision(
        thread_id: str,
        iteration_id: str,
        summary: str,
        preserve_working_parts: bool = True,
        memory_ids: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return request_video_revision_tool(
            context,
            {
                "thread_id": thread_id,
                "iteration_id": iteration_id,
                "summary": summary,
                "preserve_working_parts": preserve_working_parts,
                "memory_ids": memory_ids,
                "session_id": current_session_id(ctx),
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="request_video_explanation")
    def request_video_explanation(
        thread_id: str,
        iteration_id: str,
        summary: str,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return request_video_explanation_tool(
            context,
            {
                "thread_id": thread_id,
                "iteration_id": iteration_id,
                "summary": summary,
            },
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="select_video_result")
    def select_video_result(
        thread_id: str,
        iteration_id: str,
        result_id: str,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        return select_video_result_tool(
            context,
            {
                "thread_id": thread_id,
                "iteration_id": iteration_id,
                "result_id": result_id,
            },
            agent_principal=current_principal(ctx),
        )
