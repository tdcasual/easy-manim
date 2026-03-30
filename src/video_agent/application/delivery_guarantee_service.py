from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from video_agent.adapters.rendering.emergency_video_writer import (
    EmergencyVideoWriteError,
    EmergencyVideoWriter,
)
from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.config import Settings
from video_agent.domain.models import VideoTask


class DeliveryGuaranteeDecision(BaseModel):
    delivered: bool
    reason: str
    scheduled: bool = False
    child_task_id: str | None = None
    completion_mode: str | None = None
    delivery_tier: str | None = None
    video_path: Path | None = None


class DeliveryGuaranteeService:
    def __init__(
        self,
        *,
        settings: Settings,
        artifact_store: ArtifactStore,
        emergency_video_writer: EmergencyVideoWriter,
    ) -> None:
        self.settings = settings
        self.artifact_store = artifact_store
        self.emergency_video_writer = emergency_video_writer

    def maybe_deliver(self, task: VideoTask) -> DeliveryGuaranteeDecision:
        if not self.settings.delivery_guarantee_enabled:
            return DeliveryGuaranteeDecision(delivered=False, reason="disabled")
        if not self.settings.delivery_guarantee_allow_emergency_video:
            return DeliveryGuaranteeDecision(delivered=False, reason="emergency_video_disabled")

        try:
            output_path = self.emergency_video_writer.write(self.artifact_store.final_video_path(task.task_id))
        except EmergencyVideoWriteError as exc:
            return DeliveryGuaranteeDecision(delivered=False, reason=exc.reason)
        if task.parent_task_id is None:
            return DeliveryGuaranteeDecision(
                delivered=True,
                reason="emergency_fallback",
                completion_mode="emergency_fallback",
                delivery_tier="emergency",
                video_path=output_path,
            )
        return DeliveryGuaranteeDecision(
            delivered=True,
            reason="degraded_delivery",
            completion_mode="degraded",
            delivery_tier=task.generation_mode or "guided_generate",
            video_path=output_path,
        )
