from __future__ import annotations

import hashlib

from video_agent.domain.models import VideoTask
from video_agent.domain.session_memory_models import (
    SessionMemoryAttempt,
    SessionMemoryEntry,
    SessionMemorySnapshot,
    SessionMemorySummary,
)
from video_agent.server.session_memory import SessionMemoryRegistry


class SessionMemoryService:
    def __init__(
        self,
        registry: SessionMemoryRegistry,
        *,
        max_entries: int = 5,
        max_attempts_per_entry: int = 3,
        summary_char_limit: int = 2000,
    ) -> None:
        self.registry = registry
        self.max_entries = max_entries
        self.max_attempts_per_entry = max_attempts_per_entry
        self.summary_char_limit = summary_char_limit

    def record_task_created(self, task: VideoTask, attempt_kind: str) -> SessionMemorySnapshot | None:
        if task.session_id is None:
            return None

        snapshot = self.registry.get_snapshot(task.session_id)
        agent_id = task.agent_id or snapshot.agent_id
        root_task_id = task.root_task_id or task.task_id
        entries = [entry.model_copy(deep=True) for entry in snapshot.entries]

        existing_index = next((index for index, entry in enumerate(entries) if entry.root_task_id == root_task_id), None)
        if existing_index is not None:
            base_entry = entries.pop(existing_index)
        else:
            base_entry = SessionMemoryEntry(
                root_task_id=root_task_id,
                latest_task_id=task.task_id,
                task_goal_summary=self._compact_text(task.prompt),
            )

        attempts = [attempt.model_copy(deep=True) for attempt in base_entry.attempts]
        attempts.append(
            SessionMemoryAttempt(
                task_id=task.task_id,
                attempt_kind=attempt_kind,
                feedback_summary=self._compact_text(task.feedback),
            )
        )
        if len(attempts) > self.max_attempts_per_entry:
            attempts = attempts[-self.max_attempts_per_entry :]

        entries.append(
            base_entry.model_copy(
                update={
                    "latest_task_id": task.task_id,
                    "task_goal_summary": base_entry.task_goal_summary or self._compact_text(task.prompt),
                    "attempts": attempts,
                },
                deep=True,
            )
        )
        if len(entries) > self.max_entries:
            entries = entries[-self.max_entries :]

        updated = SessionMemorySnapshot(
            session_id=task.session_id,
            agent_id=agent_id,
            entries=entries,
        )
        return self.registry.store_snapshot(updated)

    def get_session_memory(self, session_id: str) -> SessionMemorySnapshot:
        return self.registry.get_snapshot(session_id)

    def summarize_session_memory(self, session_id: str) -> SessionMemorySummary:
        snapshot = self.get_session_memory(session_id)
        summary_text = self._build_summary_text(snapshot)
        return SessionMemorySummary(
            session_id=snapshot.session_id,
            agent_id=snapshot.agent_id,
            entries=snapshot.entries,
            summary_text=summary_text,
            summary_digest=self.compute_summary_digest(summary_text) if summary_text else None,
        )

    def clear_session_memory(self, session_id: str) -> SessionMemorySnapshot:
        return self.registry.clear_session(session_id)

    @staticmethod
    def compute_summary_digest(summary_text: str) -> str:
        return hashlib.sha256(summary_text.encode("utf-8")).hexdigest()

    def _build_summary_text(self, snapshot: SessionMemorySnapshot) -> str:
        if not snapshot.entries:
            return ""

        blocks: list[str] = []
        for index, entry in enumerate(snapshot.entries, start=1):
            attempt_parts = [self._format_attempt(attempt) for attempt in entry.attempts]
            block_lines = [f"{index}. Goal: {entry.task_goal_summary}"]
            if attempt_parts:
                block_lines.append(f"Attempts: {' | '.join(attempt_parts)}")
            blocks.append("\n".join(block_lines))

        return self._truncate_summary("\n\n".join(blocks))

    def _format_attempt(self, attempt: SessionMemoryAttempt) -> str:
        if attempt.feedback_summary:
            return f"{attempt.attempt_kind}: {attempt.feedback_summary}"
        return attempt.attempt_kind

    def _truncate_summary(self, text: str) -> str:
        if len(text) <= self.summary_char_limit:
            return text
        if self.summary_char_limit <= 3:
            return text[: self.summary_char_limit]
        return f"{text[: self.summary_char_limit - 3].rstrip()}..."

    @staticmethod
    def _compact_text(text: str | None) -> str | None:
        if text is None:
            return None
        compact = " ".join(text.split())
        return compact or None
