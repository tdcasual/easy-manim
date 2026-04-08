from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from video_agent.application.persistent_memory_enhancer import (
    PersistentMemoryEnhancer,
    normalize_retrieval_metadata,
)
from video_agent.domain.agent_memory_models import AgentMemoryRecord, AgentMemoryRetrievalHit
from video_agent.domain.session_memory_models import SessionMemorySummary


class PersistentMemoryError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code


class PersistentMemoryContext(BaseModel):
    memory_ids: list[str] = Field(default_factory=list)
    summary_text: str | None = None
    summary_digest: str | None = None
    items: list[dict[str, object]] = Field(default_factory=list)


class PersistentMemoryBackendHit(BaseModel):
    memory_id: str
    score: float = 0.0
    matched_terms: list[str] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)


class PersistentMemoryBackend(PersistentMemoryEnhancer, Protocol):
    def search(
        self,
        *,
        agent_id: str,
        query: str,
        limit: int,
    ) -> list[PersistentMemoryBackendHit]: ...

    def delete(self, record: AgentMemoryRecord) -> None: ...


@dataclass(frozen=True)
class _RetrievalScore:
    score: float
    matched_terms: list[str]
    match_reasons: list[str]


def build_persistent_memory_enhancer(
    *,
    backend: str,
    enable_embeddings: bool,
    embedding_provider: str | None,
    embedding_model: str | None,
    memo0_api_key: str | None = None,
    memo0_org_id: str | None = None,
    memo0_project_id: str | None = None,
) -> PersistentMemoryEnhancer | None:
    return build_persistent_memory_backend(
        backend=backend,
        enable_embeddings=enable_embeddings,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        memo0_api_key=memo0_api_key,
        memo0_org_id=memo0_org_id,
        memo0_project_id=memo0_project_id,
    )


def build_persistent_memory_backend(
    *,
    backend: str,
    enable_embeddings: bool,
    embedding_provider: str | None,
    embedding_model: str | None,
    memo0_api_key: str | None = None,
    memo0_org_id: str | None = None,
    memo0_project_id: str | None = None,
) -> PersistentMemoryBackend | None:
    if backend == "local":
        return None
    if backend == "memo0":
        from video_agent.application.memo0_memory_backend import Memo0MemoryBackend

        return Memo0MemoryBackend(
            api_key=memo0_api_key,
            org_id=memo0_org_id,
            project_id=memo0_project_id,
            enable_embeddings=enable_embeddings,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
        )
    raise ValueError(f"Unsupported persistent_memory_backend: {backend}")


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
        memory_backend: PersistentMemoryBackend | None = None,
        memory_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.create_record = create_record
        self.get_session_summary = get_session_summary
        self.get_record = get_record or (lambda memory_id: None)
        self.list_records = list_records or (lambda agent_id, include_disabled=False: [])
        self.disable_record = disable_record or (lambda memory_id: False)
        self.enhancer = enhancer
        self.memory_backend = memory_backend or self._coerce_memory_backend(enhancer)
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
        self._disable_memory_backend(record)
        if not self.disable_record(memory_id):
            raise PersistentMemoryError("agent_memory_not_found")
        return self.get_agent_memory(memory_id, agent_id=agent_id)

    def query_agent_memories(
        self,
        agent_id: str,
        *,
        query: str,
        limit: int = 5,
    ) -> list[AgentMemoryRetrievalHit]:
        if limit <= 0:
            return []
        normalized_query = query.strip()
        if not normalized_query:
            return []

        backend_hits = self._query_memory_backend(
            agent_id,
            query=normalized_query,
            limit=limit,
        )
        if backend_hits:
            return backend_hits

        query_tokens = self._tokenize_for_retrieval(normalized_query)
        if not query_tokens:
            return []

        scored: list[tuple[_RetrievalScore, AgentMemoryRecord]] = []
        for record in self.list_records(agent_id, False):
            retrieval_score = self._score_record(record, query=normalized_query, query_tokens=query_tokens)
            if retrieval_score.score <= 0:
                continue
            scored.append((retrieval_score, record))

        scored.sort(key=lambda item: (-item[0].score, item[1].created_at), reverse=False)
        return [
            AgentMemoryRetrievalHit(
                memory_id=record.memory_id,
                score=round(retrieval_score.score, 6),
                summary_text=record.summary_text,
                summary_digest=record.summary_digest,
                matched_terms=list(retrieval_score.matched_terms),
                match_reasons=list(retrieval_score.match_reasons),
                lineage_refs=list(record.lineage_refs),
                enhancement=dict(record.enhancement),
            )
            for retrieval_score, record in scored[:limit]
        ]

    def _query_memory_backend(
        self,
        agent_id: str,
        *,
        query: str,
        limit: int,
    ) -> list[AgentMemoryRetrievalHit]:
        if self.memory_backend is None:
            return []
        try:
            backend_hits = self.memory_backend.search(
                agent_id=agent_id,
                query=query,
                limit=limit,
            )
        except Exception:
            return []

        resolved: list[AgentMemoryRetrievalHit] = []
        for backend_hit in backend_hits:
            record = self.get_record(backend_hit.memory_id)
            if record is None or record.agent_id != agent_id or record.status != "active":
                continue
            resolved.append(
                AgentMemoryRetrievalHit(
                    memory_id=record.memory_id,
                    score=round(backend_hit.score, 6),
                    summary_text=record.summary_text,
                    summary_digest=record.summary_digest,
                    matched_terms=list(backend_hit.matched_terms),
                    match_reasons=list(backend_hit.match_reasons),
                    lineage_refs=list(record.lineage_refs),
                    enhancement=dict(record.enhancement),
                )
            )
        return resolved

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
            items=[
                {
                    "memory_id": record.memory_id,
                    "summary_text": record.summary_text,
                    "summary_digest": record.summary_digest,
                    "lineage_refs": list(record.lineage_refs),
                    "enhancement": dict(record.enhancement),
                }
                for record in records
            ],
        )

    def _build_enhancement(self, record: AgentMemoryRecord) -> dict[str, object]:
        if self.enhancer is None:
            result: dict[str, object] = {}
        else:
            try:
                result_payload = self.enhancer(record)
            except Exception as exc:
                result = {
                    "status": "unavailable",
                    "code": "agent_memory_enhancement_unavailable",
                    "message": str(exc),
                }
            else:
                result = {} if result_payload is None else dict(result_payload)
        result["retrieval"] = normalize_retrieval_metadata(record, existing=result)
        return result

    def _disable_memory_backend(self, record: AgentMemoryRecord) -> None:
        if self.memory_backend is None:
            return
        try:
            self.memory_backend.delete(record)
        except Exception:
            return

    @staticmethod
    def _coerce_memory_backend(
        enhancer: PersistentMemoryEnhancer | None,
    ) -> PersistentMemoryBackend | None:
        if enhancer is None:
            return None
        if hasattr(enhancer, "search") and hasattr(enhancer, "delete"):
            return enhancer  # type: ignore[return-value]
        return None

    @staticmethod
    def _tokenize_for_retrieval(text: str) -> list[str]:
        retrieval = normalize_retrieval_metadata(
            AgentMemoryRecord(
                memory_id="query",
                agent_id="query",
                source_session_id="query",
                summary_text=text,
                summary_digest="query",
            )
        )
        return [token for token in retrieval["tokens"] if isinstance(token, str)]

    @classmethod
    def _score_record(cls, record: AgentMemoryRecord, *, query: str, query_tokens: list[str]) -> _RetrievalScore:
        retrieval = normalize_retrieval_metadata(record, existing=record.enhancement)
        tokens = [token for token in retrieval["tokens"] if isinstance(token, str)]
        keywords = [token for token in retrieval["keywords"] if isinstance(token, str)]
        if not tokens:
            return _RetrievalScore(score=0.0, matched_terms=[], match_reasons=[])

        token_set = set(tokens)
        keyword_set = set(keywords)
        matched_terms = sorted({token for token in query_tokens if token in token_set})
        matched_keyword_terms = sorted({token for token in query_tokens if token in keyword_set})
        denominator = max(1, len(set(query_tokens)))
        token_overlap = len(matched_terms) / denominator
        keyword_overlap = len(matched_keyword_terms) / denominator
        phrase_match = query.lower() in str(retrieval.get("text", "")).lower()
        phrase_score = 1.0 if phrase_match else 0.0

        score = (
            (token_overlap * 0.45)
            + (keyword_overlap * 0.35)
            + (phrase_score * 0.20)
        )

        match_reasons: list[str] = []
        if matched_terms:
            match_reasons.append("token_overlap")
        if matched_keyword_terms:
            match_reasons.append("keyword_overlap")
        if phrase_match:
            match_reasons.append("phrase_match")

        return _RetrievalScore(
            score=score,
            matched_terms=matched_terms,
            match_reasons=match_reasons,
        )

    @staticmethod
    def _default_memory_id() -> str:
        return f"mem-{uuid4().hex}"

    @staticmethod
    def _compute_summary_digest(summary_text: str) -> str:
        return hashlib.sha256(summary_text.encode("utf-8")).hexdigest()
