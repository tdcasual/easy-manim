import importlib
import importlib.util
import sqlite3
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentToken
from video_agent.domain.agent_session_models import AgentSession
from video_agent.domain.session_memory_models import SessionMemoryEntry
from video_agent.domain.session_memory_models import SessionMemorySnapshot


MODULE_NAME = "video_agent.adapters.storage.sqlite_agent_runtime_store"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def _build_store(tmp_path: Path):
    module = _load_module()
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()

    class TestStore(module.SQLiteAgentRuntimeStoreMixin):
        def __init__(self, database_path: Path) -> None:
            self.database_path = database_path

        def _connect(self) -> sqlite3.Connection:
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = sqlite3.Row
            return connection

    return TestStore(database_path)


def test_runtime_store_mixin_round_trips_and_disables_tokens(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    first = AgentToken(token_hash="hash-1", agent_id="agent-a", scopes_json={"allow": ["task:read"]})
    second = AgentToken(token_hash="hash-2", agent_id="agent-a", scopes_json={"allow": ["task:write"]})

    store.issue_agent_token(first)
    store.issue_agent_token(second)
    assert store.disable_agent_token("hash-2") is True

    loaded = store.get_agent_token("hash-1")
    tokens = store.list_agent_tokens("agent-a")

    assert loaded is not None
    assert loaded.allowed_actions == {"task:read"}
    assert [token.token_hash for token in tokens] == ["hash-1", "hash-2"]
    assert tokens[-1].status == "disabled"


def test_runtime_store_mixin_round_trips_and_revokes_sessions(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    session = AgentSession(
        session_id="sess-1",
        session_hash="hash-1",
        agent_id="agent-a",
        token_hash="token-hash-1",
    )

    created = store.create_agent_session(session)
    touched = store.touch_agent_session("hash-1")
    revoked = store.revoke_agent_session("hash-1")
    loaded_by_hash = store.get_agent_session("hash-1")
    loaded_by_id = store.get_agent_session_by_id("sess-1")

    assert created.session_id == "sess-1"
    assert touched is not None
    assert touched.last_seen_at >= session.last_seen_at
    assert revoked is True
    assert loaded_by_hash is not None
    assert loaded_by_hash.status == "revoked"
    assert loaded_by_hash.revoked_at is not None
    assert loaded_by_id is not None
    assert loaded_by_id.session_hash == "hash-1"


def test_runtime_store_mixin_round_trips_and_disables_memories(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    first = AgentMemoryRecord(
        memory_id="mem-1",
        agent_id="agent-a",
        source_session_id="session-1",
        summary_text="Use a light background.",
        summary_digest="digest-1",
        lineage_refs=["video-task://task-1/task.json"],
        snapshot={"entry_count": 1},
    )
    second = AgentMemoryRecord(
        memory_id="mem-2",
        agent_id="agent-a",
        source_session_id="session-2",
        summary_text="Keep labels concise.",
        summary_digest="digest-2",
        lineage_refs=["video-task://task-2/task.json"],
        snapshot={"entry_count": 2},
    )

    store.create_agent_memory(first)
    store.create_agent_memory(second)
    assert store.disable_agent_memory("mem-2") is True

    loaded = store.get_agent_memory("mem-1")
    active = store.list_agent_memories("agent-a")
    all_memories = store.list_agent_memories("agent-a", include_disabled=True)

    assert loaded is not None
    assert loaded.summary_digest == "digest-1"
    assert [record.memory_id for record in active] == ["mem-1"]
    assert [record.memory_id for record in all_memories] == ["mem-1", "mem-2"]
    assert all_memories[-1].status == "disabled"


def test_runtime_store_mixin_upserts_session_snapshots_without_resetting_creation_time(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    first = SessionMemorySnapshot(
        session_id="sess-1",
        agent_id="agent-a",
        entries=[
            SessionMemoryEntry(
                root_task_id="root-1",
                latest_task_id="task-1",
                task_goal_summary="Create intro animation",
            )
        ],
    )
    second = SessionMemorySnapshot(
        session_id="sess-1",
        agent_id="agent-a",
        entries=[
            SessionMemoryEntry(
                root_task_id="root-1",
                latest_task_id="task-2",
                task_goal_summary="Create intro animation",
                latest_result_summary="Updated cut with tighter pacing",
            )
        ],
    )

    store.upsert_session_memory_snapshot(first)
    with store._connect() as connection:
        original = connection.execute(
            "SELECT created_at, updated_at FROM session_memory_snapshots WHERE session_id = ?",
            ("sess-1",),
        ).fetchone()
    assert original is not None

    store.upsert_session_memory_snapshot(second)
    loaded = store.get_session_memory_snapshot("sess-1")
    filtered = store.list_session_memory_snapshots("agent-a")
    with store._connect() as connection:
        updated = connection.execute(
            "SELECT created_at, updated_at FROM session_memory_snapshots WHERE session_id = ?",
            ("sess-1",),
        ).fetchone()

    assert loaded is not None
    assert loaded.entries[0].latest_task_id == "task-2"
    assert [snapshot.session_id for snapshot in filtered] == ["sess-1"]
    assert updated is not None
    assert updated["created_at"] == original["created_at"]
    assert updated["updated_at"] >= original["updated_at"]
