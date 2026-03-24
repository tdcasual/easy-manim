from pathlib import Path

import pytest

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.config import Settings
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import (
    create_video_task_tool,
    disable_agent_memory_tool,
    get_agent_memory_tool,
    list_agent_memories_tool,
    promote_session_memory_tool,
)
from tests.support import bootstrapped_settings


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


def agent_principal(agent_id: str) -> AgentPrincipal:
    return AgentPrincipal(
        agent_id=agent_id,
        profile=AgentProfile(agent_id=agent_id, name=agent_id),
        token=AgentToken(token_hash=f"token-{agent_id}", agent_id=agent_id),
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
