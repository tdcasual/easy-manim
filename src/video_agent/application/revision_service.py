from __future__ import annotations

from video_agent.domain.models import VideoTask


class RevisionService:
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
