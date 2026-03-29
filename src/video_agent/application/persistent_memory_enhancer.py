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


def normalize_retrieval_metadata(
    record: AgentMemoryRecord,
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = record.summary_text.strip()
    existing_retrieval = (existing or {}).get("retrieval", {})

    tokens = existing_retrieval.get("tokens")
    if not isinstance(tokens, list) or not all(isinstance(item, str) for item in tokens):
        tokens = _tokenize_text(text)

    keywords = existing_retrieval.get("keywords")
    if not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords):
        keywords = _default_keywords(tokens)

    return {
        "version": 1,
        "memory_id": record.memory_id,
        "text": text,
        "tokens": list(tokens),
        "keywords": list(keywords),
    }
