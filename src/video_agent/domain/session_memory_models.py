from __future__ import annotations

from pydantic import BaseModel, Field


class SessionHandle(BaseModel):
    session_id: str
    agent_id: str | None = None


class SessionMemoryAttempt(BaseModel):
    task_id: str
    attempt_kind: str
    feedback_summary: str | None = None


class SessionMemoryEntry(BaseModel):
    root_task_id: str
    latest_task_id: str
    task_goal_summary: str
    attempts: list[SessionMemoryAttempt] = Field(default_factory=list)


class SessionMemorySnapshot(BaseModel):
    session_id: str
    agent_id: str | None = None
    entries: list[SessionMemoryEntry] = Field(default_factory=list)

    @property
    def entry_count(self) -> int:
        return len(self.entries)
