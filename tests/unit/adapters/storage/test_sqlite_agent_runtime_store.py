import sqlite3
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.domain.agent_models import AgentProfile
from video_agent.domain.agent_runtime_models import AgentRuntimeDefinition


def _build_store(tmp_path: Path):
    from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore

    database_path = tmp_path / "runtime.db"
    SQLiteBootstrapper(database_path).bootstrap()

    class TestStore(SQLiteTaskStore):
        def _connect(self) -> sqlite3.Connection:
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = sqlite3.Row
            return connection

    return TestStore(database_path)


def test_runtime_definition_round_trip(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    definition = AgentRuntimeDefinition(
        agent_id="agent-a",
        name="Agent A Runtime",
        workspace="/tmp/agent-a/workspace",
        agent_dir="/tmp/agent-a/agent",
        tools_allow=["read", "exec", "message"],
        channels=[{"channel": "discord", "account_id": "main"}],
    )

    persisted = store.upsert_agent_runtime_definition(definition)
    loaded = store.get_agent_runtime_definition("agent-a")

    assert persisted.agent_id == "agent-a"
    assert loaded is not None
    assert loaded.workspace == "/tmp/agent-a/workspace"
    assert loaded.tools_allow == ["read", "exec", "message"]
    assert loaded.definition_source == "explicit"


def test_materialized_runtime_definition_syncs_when_profile_updates(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )

    store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A Prime",
            profile_json={"style_hints": {"tone": "teaching"}},
        )
    )

    runtime_definition = store.get_agent_runtime_definition("agent-a")

    assert runtime_definition is not None
    assert runtime_definition.definition_source == "materialized"
    assert runtime_definition.name == "Agent A Prime"
    assert runtime_definition.workspace.endswith("/agent-a/workspace")
    assert runtime_definition.agent_dir.endswith("/agent-a/agent")


def test_explicit_runtime_definition_is_not_overwritten_by_profile_update(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    store.upsert_agent_profile(AgentProfile(agent_id="agent-a", name="Agent A"))
    store.upsert_agent_runtime_definition(
        AgentRuntimeDefinition(
            agent_id="agent-a",
            name="Custom Runtime",
            workspace="/custom/workspace",
            agent_dir="/custom/agent",
            tools_allow=["read", "exec"],
            definition_source="explicit",
        )
    )

    store.upsert_agent_profile(AgentProfile(agent_id="agent-a", name="Agent A Updated"))

    runtime_definition = store.get_agent_runtime_definition("agent-a")

    assert runtime_definition is not None
    assert runtime_definition.definition_source == "explicit"
    assert runtime_definition.name == "Custom Runtime"
    assert runtime_definition.workspace == "/custom/workspace"
    assert runtime_definition.agent_dir == "/custom/agent"
