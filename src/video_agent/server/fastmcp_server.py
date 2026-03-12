from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from mcp.server.fastmcp import FastMCP

from video_agent.config import Settings
from video_agent.server.app import AppContext, create_app_context
from video_agent.server.mcp_resources import read_resource
from video_agent.server.mcp_tools import (
    cancel_video_task_tool,
    create_video_task_tool,
    get_metrics_snapshot_tool,
    get_runtime_status_tool,
    get_task_events_tool,
    get_video_result_tool,
    get_video_task_tool,
    list_video_tasks_tool,
    retry_video_task_tool,
    revise_video_task_tool,
)



def create_mcp_server(
    settings: Settings,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    debug: bool = False,
) -> FastMCP:
    context = create_app_context(settings)
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

    @mcp.tool(name="create_video_task")
    def create_video_task(
        prompt: str,
        idempotency_key: str | None = None,
        output_profile: dict[str, Any] | None = None,
        validation_profile: dict[str, Any] | None = None,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        return create_video_task_tool(
            context,
            {
                "prompt": prompt,
                "idempotency_key": idempotency_key,
                "output_profile": output_profile,
                "validation_profile": validation_profile,
                "feedback": feedback,
            },
        )

    @mcp.tool(name="get_video_task")
    def get_video_task(task_id: str) -> dict[str, Any]:
        return get_video_task_tool(context, {"task_id": task_id})

    @mcp.tool(name="list_video_tasks")
    def list_video_tasks(limit: int = 50, status: str | None = None) -> dict[str, Any]:
        return list_video_tasks_tool(context, {"limit": limit, "status": status})

    @mcp.tool(name="get_task_events")
    def get_task_events(task_id: str, limit: int = 200) -> dict[str, Any]:
        return get_task_events_tool(context, {"task_id": task_id, "limit": limit})

    @mcp.tool(name="get_metrics_snapshot")
    def get_metrics_snapshot() -> dict[str, Any]:
        return get_metrics_snapshot_tool(context, {})

    @mcp.tool(name="get_runtime_status")
    def get_runtime_status() -> dict[str, Any]:
        return get_runtime_status_tool(context, {})

    @mcp.tool(name="revise_video_task")
    def revise_video_task(
        base_task_id: str,
        feedback: str,
        preserve_working_parts: bool = True,
    ) -> dict[str, Any]:
        return revise_video_task_tool(
            context,
            {
                "base_task_id": base_task_id,
                "feedback": feedback,
                "preserve_working_parts": preserve_working_parts,
            },
        )

    @mcp.tool(name="retry_video_task")
    def retry_video_task(task_id: str) -> dict[str, Any]:
        return retry_video_task_tool(context, {"task_id": task_id})

    @mcp.tool(name="get_video_result")
    def get_video_result(task_id: str) -> dict[str, Any]:
        return get_video_result_tool(context, {"task_id": task_id})

    @mcp.tool(name="cancel_video_task")
    def cancel_video_task(task_id: str) -> dict[str, Any]:
        return cancel_video_task_tool(context, {"task_id": task_id})

    @mcp.resource("video-task://{task_id}/task.json", mime_type="application/json")
    def task_resource(task_id: str) -> str:
        return _read_text_resource(context, f"video-task://{task_id}/task.json")

    @mcp.resource("video-task://{task_id}/artifacts/current_script.py", mime_type="text/x-python")
    def script_resource(task_id: str) -> str:
        return _read_text_resource(context, f"video-task://{task_id}/artifacts/current_script.py")

    @mcp.resource("video-task://{task_id}/artifacts/final_video.mp4", mime_type="video/mp4")
    def video_resource(task_id: str) -> bytes:
        return _read_binary_resource(context, task_id, Path("artifacts/final_video.mp4"))

    @mcp.resource("video-task://{task_id}/artifacts/previews/{frame_name}", mime_type="image/png")
    def preview_resource(task_id: str, frame_name: str) -> bytes:
        return _read_binary_resource(context, task_id, Path("artifacts/previews") / frame_name)

    @mcp.resource("video-task://{task_id}/validations/{report_name}", mime_type="application/json")
    def validation_resource(task_id: str, report_name: str) -> str:
        return _read_text_resource(context, f"video-task://{task_id}/validations/{report_name}")

    @mcp.resource("video-task://{task_id}/logs/events.jsonl", mime_type="application/jsonl")
    def log_resource(task_id: str) -> str:
        return _read_text_resource(context, f"video-task://{task_id}/logs/events.jsonl")

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



def _read_text_resource(context: AppContext, uri: str) -> str:
    return read_resource(context, uri)



def _read_binary_resource(context: AppContext, task_id: str, relative_path: Path) -> bytes:
    target = context.artifact_store.task_dir(task_id) / relative_path
    return target.read_bytes()
