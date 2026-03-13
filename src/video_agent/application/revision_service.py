from __future__ import annotations

from typing import Any

from video_agent.domain.models import VideoTask


class RevisionService:
    def build_metadata(
        self,
        base_task: VideoTask,
        *,
        revision_mode: str,
        preserve_working_parts: bool,
    ) -> dict[str, Any]:
        return {
            "revision_mode": revision_mode,
            "preserve_working_parts": preserve_working_parts,
            "source_task_id": base_task.task_id,
        }

    def create_revision(
        self,
        base_task: VideoTask,
        feedback: str,
        preserve_working_parts: bool = True,
    ) -> VideoTask:
        return VideoTask.from_revision(
            parent=base_task,
            feedback=feedback,
            preserve_working_parts=preserve_working_parts,
        )

    def create_retry(self, base_task: VideoTask, feedback: str = "retry failed task") -> VideoTask:
        return VideoTask.from_revision(
            parent=base_task,
            feedback=feedback,
            preserve_working_parts=True,
        )

    def create_auto_repair(self, base_task: VideoTask, feedback: str) -> VideoTask:
        return VideoTask.from_revision(
            parent=base_task,
            feedback=feedback,
            preserve_working_parts=True,
        )
