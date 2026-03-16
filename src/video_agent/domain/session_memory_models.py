from __future__ import annotations

from pydantic import BaseModel, Field


class SessionHandle(BaseModel):
    session_id: str
    agent_id: str | None = None


class SessionMemoryAttempt(BaseModel):
    task_id: str
    attempt_kind: str
    feedback_summary: str | None = None
    status: str | None = None
    result_summary: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)


class SessionMemoryEntry(BaseModel):
    root_task_id: str
    latest_task_id: str
    task_goal_summary: str
    latest_status: str | None = None
    latest_result_summary: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    attempts: list[SessionMemoryAttempt] = Field(default_factory=list)


class SessionMemorySnapshot(BaseModel):
    session_id: str
    agent_id: str | None = None
    entries: list[SessionMemoryEntry] = Field(default_factory=list)

    @property
    def entry_count(self) -> int:
        return len(self.entries)


class SessionMemorySummary(BaseModel):
    session_id: str
    agent_id: str | None = None
    entries: list[SessionMemoryEntry] = Field(default_factory=list)
    lineage_refs: list[str] = Field(default_factory=list)
    summary_text: str = ""
    summary_digest: str | None = None

    @property
    def entry_count(self) -> int:
        return len(self.entries)
