import importlib
import importlib.util
import sqlite3
from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.domain.agent_learning_models import AgentLearningEvent
from video_agent.domain.agent_models import AgentProfile
from video_agent.domain.agent_profile_suggestion_models import AgentProfileSuggestion


MODULE_NAME = "video_agent.adapters.storage.sqlite_agent_profile_store"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def _build_store(tmp_path: Path):
    module = _load_module()
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()

    class TestStore(module.SQLiteAgentProfileStoreMixin):
        def __init__(self, database_path: Path) -> None:
            self.database_path = database_path

        def _connect(self) -> sqlite3.Connection:
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = sqlite3.Row
            return connection

    return TestStore(database_path)


def test_profile_store_mixin_applies_patch_and_records_revision(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient", "pace": "steady"}},
        )
    )

    updated_profile, revision = store.apply_agent_profile_patch(
        "agent-a",
        patch_json={"style_hints": {"tone": "teaching"}},
        source="http.profile.apply",
    )

    assert updated_profile.profile_version == 2
    assert updated_profile.profile_json == {"style_hints": {"tone": "teaching", "pace": "steady"}}
    assert revision.agent_id == "agent-a"
    assert store.list_agent_profile_revisions("agent-a")[0].revision_id == revision.revision_id


def test_profile_store_mixin_dedupes_pending_suggestions_and_updates_status(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    first = AgentProfileSuggestion(
        suggestion_id="sugg-1",
        agent_id="agent-a",
        patch_json={"style_hints": {"tone": "teaching"}},
        rationale_json={"profile_version": 3, "sources": [{"source": "memory", "memory_id": "mem-1"}]},
    )
    second = AgentProfileSuggestion(
        suggestion_id="sugg-2",
        agent_id="agent-a",
        patch_json={"style_hints": {"tone": "teaching"}},
        rationale_json={"profile_version": 3, "sources": [{"memory_id": "mem-1", "source": "memory"}]},
    )

    created = store.create_agent_profile_suggestion(first)
    duplicate = store.create_agent_profile_suggestion(second)
    applied = store.update_agent_profile_suggestion_status(
        created.suggestion_id,
        status="applied",
        applied_at=created.created_at,
        expected_status="pending",
    )

    assert duplicate.suggestion_id == created.suggestion_id
    assert len(store.list_agent_profile_suggestions("agent-a")) == 1
    assert applied is not None
    assert applied.status == "applied"


def test_profile_store_mixin_upserts_learning_events_by_task_id(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    first = AgentLearningEvent(
        event_id="evt-1",
        agent_id="agent-a",
        task_id="task-1",
        session_id="sess-1",
        status="completed",
        issue_codes=[],
        quality_score=1.0,
        profile_digest="digest-1",
        memory_ids=[],
    )
    second = AgentLearningEvent(
        event_id="evt-2",
        agent_id="agent-a",
        task_id="task-1",
        session_id="sess-1",
        status="completed",
        issue_codes=[],
        quality_score=0.5,
        profile_digest="digest-1",
        memory_ids=[],
    )

    store.create_agent_learning_event(first)
    persisted = store.create_agent_learning_event(second)

    assert persisted.event_id == "evt-1"
    assert persisted.quality_score == 0.5
    assert store.list_agent_learning_events("agent-a")[0].event_id == "evt-1"
