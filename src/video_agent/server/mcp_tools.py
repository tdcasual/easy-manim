from __future__ import annotations

from typing import Any

from video_agent.application.errors import AdmissionControlError
from video_agent.server.app import AppContext



def create_video_task_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = context.task_service.create_video_task(
            prompt=payload["prompt"],
            idempotency_key=payload.get("idempotency_key"),
            output_profile=payload.get("output_profile"),
            validation_profile=payload.get("validation_profile"),
            feedback=payload.get("feedback"),
        )
    except AdmissionControlError as exc:
        return {"error": {"code": exc.code, "message": str(exc)}}
    return result.model_dump(mode="json")



def get_video_task_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    result = context.task_service.get_video_task(payload["task_id"])
    return result.model_dump(mode="json")



def list_video_tasks_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    items = context.task_service.list_video_tasks(
        limit=payload.get("limit", 50),
        status=payload.get("status"),
    )
    return {"items": items, "next_cursor": None}



def get_task_events_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    items = context.task_service.get_task_events(
        payload["task_id"],
        limit=payload.get("limit", 200),
    )
    return {"items": items, "next_cursor": None}



def get_metrics_snapshot_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "counters": dict(context.metrics.counters),
        "timings": {name: list(values) for name, values in context.metrics.timings.items()},
    }



def get_runtime_status_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    return context.runtime_service.inspect().model_dump(mode="json")



def retry_video_task_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = context.task_service.retry_video_task(payload["task_id"])
    except AdmissionControlError as exc:
        return {"error": {"code": exc.code, "message": str(exc)}}
    return result.model_dump(mode="json")



def revise_video_task_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    result = context.task_service.revise_video_task(
        base_task_id=payload["base_task_id"],
        feedback=payload["feedback"],
        preserve_working_parts=payload.get("preserve_working_parts", True),
    )
    return result.model_dump(mode="json")



def cancel_video_task_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    context.task_service.cancel_video_task(payload["task_id"])
    return {"task_id": payload["task_id"], "status": "cancelled"}



def get_video_result_tool(context: AppContext, payload: dict[str, Any]) -> dict[str, Any]:
    result = context.task_service.get_video_result(payload["task_id"])
    return result.model_dump(mode="json")
