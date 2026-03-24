from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.agent_profile_revision_models import AgentProfileRevision


def test_store_round_trips_agent_profile_revision(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    SQLiteBootstrapper(tmp_path / "agent.db").bootstrap()

    revision = AgentProfileRevision(
        revision_id="rev-1",
        agent_id="agent-a",
        patch={"style_hints": {"tone": "teaching"}},
        source="http_apply",
    )
    store.create_agent_profile_revision(revision)

    revisions = store.list_agent_profile_revisions("agent-a")

    assert len(revisions) == 1
    assert revisions[0].patch["style_hints"]["tone"] == "teaching"
