from __future__ import annotations

from typing import Any, Protocol

from video_agent.domain.agent_memory_models import AgentMemoryRecord


class PersistentMemoryEnhancer(Protocol):
    def __call__(self, record: AgentMemoryRecord) -> dict[str, Any]: ...
