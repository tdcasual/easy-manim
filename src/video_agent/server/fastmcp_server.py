from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import Context, FastMCP

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.config import Settings
from video_agent.server.app import AppContext, create_app_context
from video_agent.server.fastmcp_server_memory_registration import register_memory_tools
from video_agent.server.fastmcp_server_resource_registration import register_resources
from video_agent.server.fastmcp_server_task_registration import register_task_tools
from video_agent.server.fastmcp_server_thread_registration import register_thread_tools
from video_agent.server.session_auth import session_key_for_context


def create_mcp_server(
    settings: Settings,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    debug: bool = False,
) -> FastMCP:
    context = create_app_context(settings)

    def current_principal(ctx: Context | None) -> AgentPrincipal | None:
        if ctx is None:
            return None
        return context.session_auth.get(session_key_for_context(ctx))

    def current_session_id(ctx: Context | None) -> str | None:
        if ctx is None:
            return None
        principal = current_principal(ctx)
        handle = context.session_memory_registry.ensure_session(
            session_key_for_context(ctx),
            agent_id=None if principal is None else principal.agent_id,
        )
        return handle.session_id

    mcp = FastMCP(
        name="easy-manim",
        instructions=(
            "Create and manage validated Manim video generation tasks. "
            "Use tools for task lifecycle actions and resources for structured artifacts."
        ),
        host=host,
        port=port,
        debug=debug,
        lifespan=_build_lifespan(context),
    )

    register_memory_tools(
        mcp=mcp,
        context=context,
        current_principal=current_principal,
        current_session_id=current_session_id,
        session_key_for_ctx=session_key_for_context,
    )
    register_task_tools(
        mcp=mcp,
        context=context,
        current_principal=current_principal,
        current_session_id=current_session_id,
    )
    register_thread_tools(
        mcp=mcp,
        context=context,
        current_principal=current_principal,
        current_session_id=current_session_id,
    )
    register_resources(
        mcp=mcp,
        context=context,
        current_principal=current_principal,
    )
    return mcp


def _build_lifespan(context: AppContext):
    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[dict[str, AppContext]]:
        if not context.settings.run_embedded_worker:
            yield {"app_context": context}
            return

        stop_event = asyncio.Event()
        worker_task = asyncio.create_task(_run_background_worker(context, stop_event))
        try:
            yield {"app_context": context}
        finally:
            stop_event.set()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

    return lifespan


async def _run_background_worker(context: AppContext, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        processed = await asyncio.to_thread(context.worker.run_once)
        if processed == 0:
            await asyncio.sleep(context.settings.worker_poll_interval_seconds)
        else:
            await asyncio.sleep(0)
