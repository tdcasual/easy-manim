from pathlib import Path

import pytest

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.persistent_memory_service import PersistentMemoryBackendHit
from video_agent.config import Settings
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
import video_agent.server.app as app_module
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import (
    create_video_task_tool,
    disable_agent_memory_tool,
    get_agent_memory_tool,
    list_agent_memories_tool,
    promote_session_memory_tool,
    query_agent_memories_tool,
)
from tests.support import bootstrapped_settings


class _FakeMemo0Backend:
    def __init__(self) -> None:
        self.deleted_memory_ids: list[str] = []
        self.search_hits: list[PersistentMemoryBackendHit] = []

    def __call__(self, record: AgentMemoryRecord) -> dict[str, object]:
        return {
            "status": "indexed",
            "backend": "memo0",
            "memory_ids": [f"remote-{record.memory_id}"],
        }

    def search(
        self,
        *,
        agent_id: str,
        query: str,
        limit: int,
    ) -> list[PersistentMemoryBackendHit]:
        return list(self.search_hits[:limit])

    def delete(self, record: AgentMemoryRecord) -> None:
        self.deleted_memory_ids.append(record.memory_id)


def _build_agent_memory_settings(tmp_path: Path, *, persistent_memory_backend: str = "local") -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
            auth_mode="required",
            persistent_memory_backend=persistent_memory_backend,
        )
    )


@pytest.fixture
def app_context(tmp_path: Path):
    return create_app_context(_build_agent_memory_settings(tmp_path))


def agent_principal(
    agent_id: str,
    *,
    scopes_json: dict | None = None,
    policy_json: dict | None = None,
) -> AgentPrincipal:
    return AgentPrincipal(
        agent_id=agent_id,
        profile=AgentProfile(agent_id=agent_id, name=agent_id, policy_json=policy_json or {}),
        token=AgentToken(token_hash=f"token-{agent_id}", agent_id=agent_id, scopes_json=scopes_json or {}),
    )


def seed_agent_memory(app_context, *, memory_id: str, agent_id: str, status: str = "active") -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id=memory_id,
            agent_id=agent_id,
            source_session_id=f"session-{agent_id}",
            status=status,
            summary_text=f"Remember {agent_id}",
            summary_digest=f"digest-{memory_id}",
        )
    )


def test_promote_session_memory_requires_non_empty_session(app_context) -> None:
    payload = promote_session_memory_tool(
        app_context,
        {},
        agent_principal=agent_principal("agent-a"),
        session_id="session-1",
    )

    assert payload["error"]["code"] == "agent_memory_empty_session"


def test_agent_can_only_list_own_memories(app_context) -> None:
    seed_agent_memory(app_context, memory_id="mem-a", agent_id="agent-a")
    seed_agent_memory(app_context, memory_id="mem-b", agent_id="agent-b")

    payload = list_agent_memories_tool(app_context, {}, agent_principal=agent_principal("agent-a"))

    assert [item["memory_id"] for item in payload["items"]] == ["mem-a"]


def test_get_agent_memory_rejects_cross_agent_access(app_context) -> None:
    seed_agent_memory(app_context, memory_id="mem-a", agent_id="agent-a")

    payload = get_agent_memory_tool(
        app_context,
        {"memory_id": "mem-a"},
        agent_principal=agent_principal("agent-b"),
    )

    assert payload["error"]["code"] == "agent_memory_forbidden"


def test_disabled_memory_cannot_be_used_after_disable(app_context) -> None:
    seed_agent_memory(app_context, memory_id="mem-a", agent_id="agent-a")

    payload = disable_agent_memory_tool(
        app_context,
        {"memory_id": "mem-a"},
        agent_principal=agent_principal("agent-a"),
    )

    assert payload["status"] == "disabled"


def test_create_rejects_disabled_memory_id(app_context) -> None:
    seed_agent_memory(app_context, memory_id="mem-a", agent_id="agent-a", status="disabled")

    payload = create_video_task_tool(
        app_context,
        {"prompt": "draw a circle", "session_id": "session-1", "memory_ids": ["mem-a"]},
        agent_principal=agent_principal("agent-a"),
    )

    assert payload["error"]["code"] == "agent_memory_disabled"


def test_promote_returns_enhancement_warning_without_failing(tmp_path: Path) -> None:
    app_context = create_app_context(_build_agent_memory_settings(tmp_path, persistent_memory_backend="memo0"))
    app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-a",
        agent_principal=agent_principal("agent-a"),
    )

    payload = promote_session_memory_tool(
        app_context,
        {},
        agent_principal=agent_principal("agent-a"),
        session_id="session-a",
    )

    assert payload["memory_id"]
    assert payload["enhancement"]["code"] == "agent_memory_enhancement_unavailable"
    assert payload["enhancement"]["backend"] == "memo0"


def test_promote_returns_memo0_index_metadata_when_backend_is_injected(tmp_path: Path, monkeypatch) -> None:
    backend = _FakeMemo0Backend()
    monkeypatch.setattr(app_module, "build_persistent_memory_backend", lambda **kwargs: backend, raising=False)

    app_context = create_app_context(_build_agent_memory_settings(tmp_path, persistent_memory_backend="memo0"))
    app_context.task_service.create_video_task(
        prompt="draw a circle",
        session_id="session-a",
        agent_principal=agent_principal("agent-a"),
    )

    payload = promote_session_memory_tool(
        app_context,
        {},
        agent_principal=agent_principal("agent-a"),
        session_id="session-a",
    )

    assert payload["enhancement"]["status"] == "indexed"
    assert payload["enhancement"]["backend"] == "memo0"
    assert payload["enhancement"]["memory_ids"] == [f"remote-{payload['memory_id']}"]


def test_promote_stores_retrieval_metadata_for_local_backend(app_context) -> None:
    app_context.task_service.create_video_task(
        prompt="Use a dark background with smooth transitions.",
        session_id="session-a",
        agent_principal=agent_principal("agent-a"),
    )

    payload = promote_session_memory_tool(
        app_context,
        {},
        agent_principal=agent_principal("agent-a"),
        session_id="session-a",
    )

    retrieval = payload["enhancement"]["retrieval"]
    assert retrieval["version"] == 1
    assert "dark" in retrieval["tokens"]
    assert retrieval["text"]


def test_query_agent_memories_returns_ranked_active_records(app_context) -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-a",
            agent_id="agent-a",
            source_session_id="session-agent-a",
            status="active",
            summary_text="Dark contrast style recommendations.",
            summary_digest="digest-mem-a",
        )
    )
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-b",
            agent_id="agent-a",
            source_session_id="session-agent-a",
            status="active",
            summary_text="Dark background with smooth transitions and easing.",
            summary_digest="digest-mem-b",
        )
    )
    seed_agent_memory(app_context, memory_id="mem-c", agent_id="agent-a", status="disabled")

    payload = query_agent_memories_tool(
        app_context,
        {"query": "dark transitions", "limit": 5},
        agent_principal=agent_principal("agent-a"),
    )

    assert [item["memory_id"] for item in payload["items"]] == ["mem-b", "mem-a"]
    assert payload["items"][0]["score"] > payload["items"][1]["score"]
    assert payload["items"][0]["matched_terms"] == ["dark", "transitions"]
    assert "keyword_overlap" in payload["items"][0]["match_reasons"]


def test_query_agent_memories_returns_empty_when_limit_is_zero(app_context) -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-a",
            agent_id="agent-a",
            source_session_id="session-agent-a",
            status="active",
            summary_text="Dark background with smooth transitions and easing.",
            summary_digest="digest-mem-a",
        )
    )

    payload = query_agent_memories_tool(
        app_context,
        {"query": "dark transitions", "limit": 0},
        agent_principal=agent_principal("agent-a"),
    )

    assert payload["items"] == []


def test_query_agent_memories_is_agent_scoped(app_context) -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-a",
            agent_id="agent-a",
            source_session_id="session-agent-a",
            status="active",
            summary_text="Dark background with smooth transitions.",
            summary_digest="digest-mem-a",
        )
    )
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-b",
            agent_id="agent-b",
            source_session_id="session-agent-b",
            status="active",
            summary_text="Dark background with contrast guidance.",
            summary_digest="digest-mem-b",
        )
    )

    payload = query_agent_memories_tool(
        app_context,
        {"query": "dark background", "limit": 5},
        agent_principal=agent_principal("agent-b"),
    )

    assert [item["memory_id"] for item in payload["items"]] == ["mem-b"]


def test_query_agent_memories_keeps_stable_order_for_equal_scores(app_context) -> None:
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-a",
            agent_id="agent-a",
            source_session_id="session-agent-a",
            status="active",
            summary_text="Dark background guidance.",
            summary_digest="digest-mem-a",
        )
    )
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-b",
            agent_id="agent-a",
            source_session_id="session-agent-a",
            status="active",
            summary_text="Dark background guidance.",
            summary_digest="digest-mem-b",
        )
    )

    payload = query_agent_memories_tool(
        app_context,
        {"query": "dark background", "limit": 5},
        agent_principal=agent_principal("agent-a"),
    )

    assert [item["memory_id"] for item in payload["items"]] == ["mem-a", "mem-b"]


def test_query_agent_memories_uses_memo0_backend_ordering(tmp_path: Path, monkeypatch) -> None:
    backend = _FakeMemo0Backend()
    backend.search_hits = [
        PersistentMemoryBackendHit(
            memory_id="mem-b",
            score=0.95,
            match_reasons=["memo0_semantic_search"],
        ),
        PersistentMemoryBackendHit(
            memory_id="mem-a",
            score=0.83,
            match_reasons=["memo0_semantic_search"],
        ),
    ]
    monkeypatch.setattr(app_module, "build_persistent_memory_backend", lambda **kwargs: backend, raising=False)

    app_context = create_app_context(_build_agent_memory_settings(tmp_path, persistent_memory_backend="memo0"))
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-a",
            agent_id="agent-a",
            source_session_id="session-agent-a",
            status="active",
            summary_text="Dark background with smooth transitions.",
            summary_digest="digest-mem-a",
        )
    )
    app_context.store.create_agent_memory(
        AgentMemoryRecord(
            memory_id="mem-b",
            agent_id="agent-a",
            source_session_id="session-agent-a",
            status="active",
            summary_text="High contrast title treatment.",
            summary_digest="digest-mem-b",
        )
    )

    payload = query_agent_memories_tool(
        app_context,
        {"query": "cinematic contrast", "limit": 5},
        agent_principal=agent_principal("agent-a"),
    )

    assert [item["memory_id"] for item in payload["items"]] == ["mem-b", "mem-a"]
    assert payload["items"][0]["match_reasons"] == ["memo0_semantic_search"]


def test_query_agent_memories_requires_memory_read_scope(app_context) -> None:
    payload = query_agent_memories_tool(
        app_context,
        {"query": "dark background", "limit": 5},
        agent_principal=agent_principal("agent-a", scopes_json={"allow": ["task:read"]}),
    )

    assert payload["error"]["code"] == "agent_scope_denied"
