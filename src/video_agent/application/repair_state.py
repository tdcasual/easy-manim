from __future__ import annotations

from pydantic import BaseModel

from video_agent.domain.models import VideoTask


class RepairStateSnapshot(BaseModel):
    attempted: bool = False
    child_count: int = 0
    last_issue_code: str | None = None
    stop_reason: str | None = None


def build_repair_state_snapshot(root_task: VideoTask, child_count: int) -> RepairStateSnapshot:
    return RepairStateSnapshot(
        attempted=root_task.repair_attempted,
        child_count=child_count,
        last_issue_code=root_task.repair_last_issue_code,
        stop_reason=root_task.repair_stop_reason,
    )
