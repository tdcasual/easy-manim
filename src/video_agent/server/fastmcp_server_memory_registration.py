from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.server.app import AppContext
from video_agent.server.mcp_tools import (
    authenticate_agent_tool,
    clear_session_memory_tool,
    disable_agent_memory_tool,
    get_agent_memory_tool,
    get_session_memory_tool,
    list_agent_memories_tool,
    promote_session_memory_tool,
    query_agent_memories_tool,
    summarize_session_memory_tool,
)


def register_memory_tools(
    *,
    mcp: FastMCP,
    context: AppContext,
    current_principal: Callable[[Context | None], AgentPrincipal | None],
    current_session_id: Callable[[Context | None], str | None],
    session_key_for_ctx: Callable[[Context], str],
) -> None:
    @mcp.tool(name="authenticate_agent")
    def authenticate_agent(agent_token: str, ctx: Context) -> dict[str, Any]:
        return authenticate_agent_tool(
            context,
            {"agent_token": agent_token},
            session_key=session_key_for_ctx(ctx),
        )

    @mcp.tool(name="get_session_memory")
    def get_session_memory(ctx: Context | None = None) -> dict[str, Any]:
        return get_session_memory_tool(
            context,
            {},
            agent_principal=current_principal(ctx),
            session_id=current_session_id(ctx),
        )

    @mcp.tool(name="summarize_session_memory")
    def summarize_session_memory(ctx: Context | None = None) -> dict[str, Any]:
        return summarize_session_memory_tool(
            context,
            {},
            agent_principal=current_principal(ctx),
            session_id=current_session_id(ctx),
        )

    @mcp.tool(name="clear_session_memory")
    def clear_session_memory(ctx: Context | None = None) -> dict[str, Any]:
        return clear_session_memory_tool(
            context,
            {},
            agent_principal=current_principal(ctx),
            session_id=current_session_id(ctx),
        )

    @mcp.tool(name="promote_session_memory")
    def promote_session_memory(ctx: Context | None = None) -> dict[str, Any]:
        return promote_session_memory_tool(
            context,
            {},
            agent_principal=current_principal(ctx),
            session_id=current_session_id(ctx),
        )

    @mcp.tool(name="list_agent_memories")
    def list_agent_memories(include_disabled: bool = False, ctx: Context | None = None) -> dict[str, Any]:
        return list_agent_memories_tool(
            context,
            {"include_disabled": include_disabled},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="get_agent_memory")
    def get_agent_memory(memory_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return get_agent_memory_tool(
            context,
            {"memory_id": memory_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="disable_agent_memory")
    def disable_agent_memory(memory_id: str, ctx: Context | None = None) -> dict[str, Any]:
        return disable_agent_memory_tool(
            context,
            {"memory_id": memory_id},
            agent_principal=current_principal(ctx),
        )

    @mcp.tool(name="query_agent_memories")
    def query_agent_memories(query: str, limit: int = 5, ctx: Context | None = None) -> dict[str, Any]:
        return query_agent_memories_tool(
            context,
            {"query": query, "limit": limit},
            agent_principal=current_principal(ctx),
        )
