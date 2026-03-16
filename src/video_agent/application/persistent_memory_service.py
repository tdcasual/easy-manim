from __future__ import annotations

import hashlib
from collections.abc import Callable
from uuid import uuid4

from pydantic import BaseModel, Field

from video_agent.application.persistent_memory_enhancer import PersistentMemoryEnhancer
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.session_memory_models import SessionMemorySummary


class PersistentMemoryError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


class PersistentMemoryContext(BaseModel):
    memory_ids: list[str] = Field(default_factory=list)
    summary_text: str | None = None
    summary_digest: str | None = None


class PersistentMemoryService:
    def __init__(
        self,
        *,
        create_record: Callable[[AgentMemoryRecord], AgentMemoryRecord],
        get_session_summary: Callable[[str], SessionMemorySummary],
        get_record: Callable[[str], AgentMemoryRecord | None] | None = None,
        list_records: Callable[[str, bool], list[AgentMemoryRecord]] | None = None,
        disable_record: Callable[[str], bool] | None = None,
        enhancer: PersistentMemoryEnhancer | None = None,
        memory_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.create_record = create_record
        self.get_session_summary = get_session_summary
        self.get_record = get_record or (lambda memory_id: None)
        self.list_records = list_records or (lambda agent_id, include_disabled=False: [])
        self.disable_record = disable_record or (lambda memory_id: False)
        self.enhancer = enhancer
        self.memory_id_factory = memory_id_factory or self._default_memory_id

    def promote_session_memory(self, session_id: str, *, agent_id: str) -> AgentMemoryRecord:
        summary = self.get_session_summary(session_id)
        if summary.agent_id is not None and summary.agent_id != agent_id:
            raise PersistentMemoryError("agent_memory_forbidden")
        if not summary.summary_text.strip():
            raise PersistentMemoryError("agent_memory_empty_session")

        record = AgentMemoryRecord(
            memory_id=self.memory_id_factory(),
            agent_id=agent_id,
            source_session_id=session_id,
            summary_text=summary.summary_text,
            summary_digest=summary.summary_digest or self._compute_summary_digest(summary.summary_text),
            lineage_refs=list(summary.lineage_refs),
            snapshot=summary.model_dump(mode="json"),
            enhancement={},
        )
        record = record.model_copy(update={"enhancement": self._build_enhancement(record)}, deep=True)
        return self.create_record(record)

    def get_agent_memory(self, memory_id: str, *, agent_id: str) -> AgentMemoryRecord:
        record = self.get_record(memory_id)
        if record is None:
            raise PersistentMemoryError("agent_memory_not_found")
        if record.agent_id != agent_id:
            raise PersistentMemoryError("agent_memory_forbidden")
        return record

    def list_agent_memories(self, agent_id: str, *, include_disabled: bool = False) -> list[AgentMemoryRecord]:
        return self.list_records(agent_id, include_disabled)

    def disable_agent_memory(self, memory_id: str, *, agent_id: str) -> AgentMemoryRecord:
        record = self.get_agent_memory(memory_id, agent_id=agent_id)
        if record.status == "disabled":
            return record
        if not self.disable_record(memory_id):
            raise PersistentMemoryError("agent_memory_not_found")
        return self.get_agent_memory(memory_id, agent_id=agent_id)

    def resolve_memory_context(self, agent_id: str, memory_ids: list[str] | None) -> PersistentMemoryContext:
        selected_ids = list(dict.fromkeys(memory_ids or []))
        if not selected_ids:
            return PersistentMemoryContext()

        records: list[AgentMemoryRecord] = []
        for memory_id in selected_ids:
            record = self.get_agent_memory(memory_id, agent_id=agent_id)
            if record.status != "active":
                raise PersistentMemoryError("agent_memory_disabled")
            records.append(record)

        summary_parts = [record.summary_text.strip() for record in records if record.summary_text.strip()]
        summary_text = "\n\n".join(summary_parts) or None
        return PersistentMemoryContext(
            memory_ids=selected_ids,
            summary_text=summary_text,
            summary_digest=None if summary_text is None else self._compute_summary_digest(summary_text),
        )

    def _build_enhancement(self, record: AgentMemoryRecord) -> dict[str, object]:
        if self.enhancer is None:
            return {}
        try:
            result = self.enhancer(record)
        except Exception as exc:
            return {
                "status": "unavailable",
                "code": "agent_memory_enhancement_unavailable",
                "message": str(exc),
            }
        return {} if result is None else dict(result)

    @staticmethod
    def _default_memory_id() -> str:
        return f"mem-{uuid4().hex}"

    @staticmethod
    def _compute_summary_digest(summary_text: str) -> str:
        return hashlib.sha256(summary_text.encode("utf-8")).hexdigest()
