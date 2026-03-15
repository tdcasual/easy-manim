from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.models import VideoTask


def test_store_can_insert_and_fetch_task(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    task = VideoTask(prompt="draw a circle")
    store.create_task(task, idempotency_key="abc")

    loaded = store.get_task(task.task_id)
    assert loaded is not None
    assert loaded.prompt == "draw a circle"


def test_idempotency_key_returns_existing_task(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    first = VideoTask(prompt="draw a circle")
    second = VideoTask(prompt="draw another circle")

    created = store.create_task(first, idempotency_key="same")
    duplicate = store.create_task(second, idempotency_key="same")
    assert duplicate.task_id == created.task_id


def test_store_round_trips_agent_profile(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    profile = AgentProfile(
        agent_id="agent-a",
        name="Agent A",
        profile_json={"style_hints": {"tone": "teaching"}},
    )

    store.upsert_agent_profile(profile)

    loaded = store.get_agent_profile("agent-a")

    assert loaded is not None
    assert loaded.profile_json["style_hints"]["tone"] == "teaching"


def test_store_resolves_agent_token_by_hash(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()

    store.issue_agent_token(
        AgentToken(token_hash="hash-1", agent_id="agent-a", scopes_json={"mode": "default"})
    )

    loaded = store.get_agent_token("hash-1")

    assert loaded is not None
    assert loaded.agent_id == "agent-a"


def test_store_persists_task_agent_id(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    task = VideoTask(prompt="draw a circle", agent_id="agent-a")

    store.create_task(task, idempotency_key="k1")

    loaded = store.get_task(task.task_id)

    assert loaded is not None
    assert loaded.agent_id == "agent-a"
