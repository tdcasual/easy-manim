from __future__ import annotations

from typing import Any

from video_agent.application.persistent_memory_service import PersistentMemoryBackendHit
from video_agent.domain.agent_memory_models import AgentMemoryRecord


class Memo0MemoryBackend:
    def __init__(
        self,
        *,
        api_key: str | None,
        org_id: str | None,
        project_id: str | None,
        enable_embeddings: bool,
        embedding_provider: str | None,
        embedding_model: str | None,
    ) -> None:
        self.api_key = api_key
        self.org_id = org_id
        self.project_id = project_id
        self.enable_embeddings = enable_embeddings
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self._client: Any | None = None
        self._client_initialized = False
        self._unavailable_message: str | None = None

    def __call__(self, record: AgentMemoryRecord) -> dict[str, object]:
        client = self._get_client()
        if client is None:
            return self._unavailable_payload()
        try:
            response = client.add(
                record.summary_text,
                user_id=record.agent_id,
                metadata=self._metadata(record),
            )
        except Exception as exc:
            return self._unavailable_payload(message=str(exc))

        return {
            "status": "indexed",
            "backend": "memo0",
            "memory_ids": self._extract_remote_ids(response),
        }

    def search(
        self,
        *,
        agent_id: str,
        query: str,
        limit: int,
    ) -> list[PersistentMemoryBackendHit]:
        client = self._get_client()
        if client is None:
            raise RuntimeError(self._unavailable_message or "memo0_unavailable")
        results = client.search(
            query=query,
            version="v2",
            filters={"user_id": agent_id},
            top_k=limit,
        )
        items = results if isinstance(results, list) else []

        hits: list[PersistentMemoryBackendHit] = []
        total = max(1, len(items))
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            memory_id = str(metadata.get("memory_id") or "").strip()
            if not memory_id:
                continue
            raw_score = item.get("score")
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                score = round((total - index) / total, 6)
            hits.append(
                PersistentMemoryBackendHit(
                    memory_id=memory_id,
                    score=score,
                    match_reasons=["memo0_semantic_search"],
                )
            )
        return hits

    def delete(self, record: AgentMemoryRecord) -> None:
        client = self._get_client()
        if client is None:
            return
        for remote_id in self._remote_ids_from_record(record):
            client.delete(memory_id=remote_id)

    def _get_client(self) -> Any | None:
        if self._client_initialized:
            return self._client

        self._client_initialized = True
        if not self.api_key:
            self._unavailable_message = "memo0_api_key_missing"
            return None
        try:
            from mem0 import MemoryClient
        except Exception as exc:
            self._unavailable_message = str(exc)
            return None

        kwargs: dict[str, object] = {"api_key": self.api_key}
        if self.org_id:
            kwargs["org_id"] = self.org_id
        if self.project_id:
            kwargs["project_id"] = self.project_id
        self._client = MemoryClient(**kwargs)
        return self._client

    def _metadata(self, record: AgentMemoryRecord) -> dict[str, object]:
        return {
            "memory_id": record.memory_id,
            "source_session_id": record.source_session_id,
            "summary_digest": record.summary_digest,
            "lineage_refs": list(record.lineage_refs),
        }

    def _unavailable_payload(self, *, message: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": "unavailable",
            "code": "agent_memory_enhancement_unavailable",
            "backend": "memo0",
        }
        if message or self._unavailable_message:
            payload["message"] = message or self._unavailable_message
        if self.enable_embeddings or self.embedding_provider or self.embedding_model:
            payload["embeddings"] = {
                "enabled": self.enable_embeddings,
                "provider": self.embedding_provider,
                "model": self.embedding_model,
            }
        return payload

    @staticmethod
    def _extract_remote_ids(response: object) -> list[str]:
        if isinstance(response, dict):
            candidates = response.get("results")
            if isinstance(candidates, list):
                return Memo0MemoryBackend._extract_remote_ids(candidates)
            value = str(response.get("id") or "").strip()
            return [value] if value else []
        if not isinstance(response, list):
            return []
        remote_ids: list[str] = []
        for item in response:
            if not isinstance(item, dict):
                continue
            value = str(item.get("id") or "").strip()
            if value:
                remote_ids.append(value)
        return remote_ids

    @staticmethod
    def _remote_ids_from_record(record: AgentMemoryRecord) -> list[str]:
        raw = record.enhancement.get("memory_ids")
        if not isinstance(raw, list):
            return []
        remote_ids: list[str] = []
        for item in raw:
            value = str(item).strip()
            if value:
                remote_ids.append(value)
        return remote_ids
