from __future__ import annotations

import re
from typing import Any, Protocol

from video_agent.domain.agent_memory_models import AgentMemoryRecord


class PersistentMemoryEnhancer(Protocol):
    def __call__(self, record: AgentMemoryRecord) -> dict[str, Any]: ...


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset({"a", "an", "and", "the", "to", "for", "or", "of", "in", "on", "with", "use"})


def _tokenize_text(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


def _default_keywords(tokens: list[str]) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if len(token) < 4 or token in _STOPWORDS or token in seen:
            continue
        keywords.append(token)
        seen.add(token)
    return keywords


def _normalize_preserved_terms(raw_terms: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw in raw_terms:
        normalized.extend(_tokenize_text(raw))
    return normalized


def _normalize_preserved_keywords(raw_keywords: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for token in _normalize_preserved_terms(raw_keywords):
        if len(token) < 4 or token in _STOPWORDS or token in seen:
            continue
        normalized.append(token)
        seen.add(token)
    return normalized


def normalize_retrieval_metadata(
    record: AgentMemoryRecord,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = record.summary_text.strip()
    existing_retrieval = (existing or {}).get("retrieval", {})

    tokens = existing_retrieval.get("tokens")
    if isinstance(tokens, list) and all(isinstance(item, str) for item in tokens):
        tokens = _normalize_preserved_terms(tokens)
    else:
        tokens = _tokenize_text(text)

    keywords = existing_retrieval.get("keywords")
    if isinstance(keywords, list) and all(isinstance(item, str) for item in keywords):
        keywords = _normalize_preserved_keywords(keywords)
    else:
        keywords = _default_keywords(tokens)

    return {
        "version": 1,
        "memory_id": record.memory_id,
        "text": text,
        "tokens": list(tokens),
        "keywords": list(keywords),
    }
