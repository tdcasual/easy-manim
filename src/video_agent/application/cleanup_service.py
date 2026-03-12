from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore


@dataclass
class CleanupCandidate:
    task_id: str
    status: str
    phase: str
    created_at: str
    updated_at: str


@dataclass
class CleanupSummary:
    candidates: list[CleanupCandidate]
    deleted_count: int = 0


class CleanupService:
    def __init__(self, store: SQLiteTaskStore, artifact_store: ArtifactStore) -> None:
        self.store = store
        self.artifact_store = artifact_store

    def find_candidates(self, statuses: list[str], older_than_iso: str, limit: int) -> list[CleanupCandidate]:
        return [
            CleanupCandidate(**item)
            for item in self.store.list_cleanup_candidates(statuses=statuses, older_than_iso=older_than_iso, limit=limit)
        ]

    def delete_candidates(self, candidates: Iterable[CleanupCandidate]) -> CleanupSummary:
        deleted_count = 0
        collected = list(candidates)
        for candidate in collected:
            self.store.delete_task(candidate.task_id)
            self.artifact_store.delete_task_dir(candidate.task_id)
            deleted_count += 1
        return CleanupSummary(candidates=collected, deleted_count=deleted_count)
