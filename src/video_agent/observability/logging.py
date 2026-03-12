from __future__ import annotations

import json
from typing import Any



def build_log_event(
    task_id: str,
    phase: str,
    message: str,
    attempt_count: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    event = {"task_id": task_id, "phase": phase, "message": message}
    if attempt_count is not None:
        event["attempt_count"] = attempt_count
    event.update(extra)
    return event



def serialize_log_event(event: dict[str, Any]) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"
