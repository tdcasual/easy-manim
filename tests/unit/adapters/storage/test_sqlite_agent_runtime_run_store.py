import sqlite3
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.domain.agent_runtime_run_models import AgentRuntimeRun


def _build_store(tmp_path: Path):
    from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore

    database_path = tmp_path / "runtime-runs.db"
    SQLiteBootstrapper(database_path).bootstrap()

    class TestStore(SQLiteTaskStore):
        def _connect(self) -> sqlite3.Connection:
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = sqlite3.Row
            return connection

    return TestStore(database_path)


def test_runtime_run_round_trip(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    run = AgentRuntimeRun(
        session_id="gw-sess-1",
        agent_id="agent-a",
        source_kind="http_control",
        trigger_kind="authenticate",
        summary="Authenticated runtime",
    )

    persisted = store.create_agent_runtime_run(run)
    loaded = store.list_agent_runtime_runs(session_id="gw-sess-1")

    assert persisted.run_id.startswith("agent-run-")
    assert len(loaded) == 1
    assert loaded[0].trigger_kind == "authenticate"
    assert loaded[0].agent_id == "agent-a"
