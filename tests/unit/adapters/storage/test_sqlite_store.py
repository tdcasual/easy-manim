from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.agent_profile_revision_models import AgentProfileRevision
from video_agent.domain.agent_session_models import AgentSession
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
    assert loaded.profile_version == 1


def test_store_increments_profile_version_on_profile_update(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    store.upsert_agent_profile(profile)
    store.upsert_agent_profile(profile.model_copy(update={"profile_json": {"style_hints": {"tone": "teaching"}}}))

    loaded = store.get_agent_profile("agent-a")

    assert loaded is not None
    assert loaded.profile_version == 2


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


def test_store_persists_task_profile_version_and_policy_flags(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    task = VideoTask(
        prompt="draw a circle",
        agent_id="agent-a",
        profile_version=3,
        effective_policy_flags={"deny_actions": ["task:mutate"]},
    )

    store.create_task(task, idempotency_key="profile-version-1")
    loaded = store.get_task(task.task_id)

    assert loaded is not None
    assert loaded.profile_version == 3
    assert loaded.effective_policy_flags == {"deny_actions": ["task:mutate"]}


def test_store_persists_task_session_id_and_memory_context(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    task = VideoTask(
        prompt="draw a circle",
        session_id="session-1",
        memory_context_summary="Recent attempts already established a light background.",
        memory_context_digest="digest-1",
    )

    store.create_task(task, idempotency_key="mem-1")
    loaded = store.get_task(task.task_id)

    assert loaded is not None
    assert loaded.session_id == "session-1"
    assert loaded.memory_context_summary == "Recent attempts already established a light background."
    assert loaded.memory_context_digest == "digest-1"


def test_store_round_trips_agent_memory_record(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    record = AgentMemoryRecord(
        memory_id="mem-1",
        agent_id="agent-a",
        source_session_id="session-1",
        summary_text="Use a light background and clear labels.",
        summary_digest="digest-1",
        lineage_refs=["video-task://task-1/task.json"],
        snapshot={"entry_count": 1},
    )

    store.create_agent_memory(record)
    loaded = store.get_agent_memory("mem-1")

    assert loaded is not None
    assert loaded.agent_id == "agent-a"
    assert loaded.summary_text == "Use a light background and clear labels."
    assert loaded.lineage_refs == ["video-task://task-1/task.json"]


def test_store_disables_agent_memory_without_deleting_it(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    record = AgentMemoryRecord(
        memory_id="mem-1",
        agent_id="agent-a",
        source_session_id="session-1",
        summary_text="Use a light background.",
        summary_digest="digest-1",
        lineage_refs=["video-task://task-1/task.json"],
        snapshot={"entry_count": 1},
    )

    store.create_agent_memory(record)
    assert store.disable_agent_memory("mem-1") is True

    loaded = store.get_agent_memory("mem-1")
    assert loaded is not None
    assert loaded.status == "disabled"
    assert loaded.disabled_at is not None


def test_store_round_trips_agent_session(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    session = AgentSession(
        session_id="sess-1",
        session_hash="hash-1",
        agent_id="agent-a",
    )

    store.create_agent_session(session)
    loaded = store.get_agent_session("hash-1")

    assert loaded is not None
    assert loaded.agent_id == "agent-a"
    assert loaded.status == "active"


def test_store_touches_and_revokes_agent_session(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    session = AgentSession(
        session_id="sess-1",
        session_hash="hash-1",
        agent_id="agent-a",
    )
    store.create_agent_session(session)

    touched = store.touch_agent_session("hash-1")
    assert touched is not None
    assert touched.last_seen_at >= session.last_seen_at

    assert store.revoke_agent_session("hash-1") is True

    revoked = store.get_agent_session("hash-1")
    assert revoked is not None
    assert revoked.status == "revoked"
    assert revoked.revoked_at is not None


def test_store_round_trips_agent_profile_revision(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    revision = AgentProfileRevision(
        revision_id="rev-1",
        agent_id="agent-a",
        patch_json={"style_hints": {"tone": "teaching"}},
        source="http.profile.apply",
    )

    store.create_agent_profile_revision(revision)

    loaded = store.list_agent_profile_revisions("agent-a")

    assert len(loaded) == 1
    assert loaded[0].revision_id == "rev-1"
    assert loaded[0].patch_json == {"style_hints": {"tone": "teaching"}}
    assert loaded[0].source == "http.profile.apply"


def test_store_applies_agent_profile_patch_and_records_revision(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
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
    assert revision.patch_json == {"style_hints": {"tone": "teaching"}}

    loaded_revisions = store.list_agent_profile_revisions("agent-a")
    assert len(loaded_revisions) == 1
    assert loaded_revisions[0].revision_id == revision.revision_id


def test_store_rejects_profile_patch_for_inactive_profile(tmp_path) -> None:
    store = SQLiteTaskStore(tmp_path / "agent.db")
    store.initialize()
    store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            status="disabled",
        )
    )

    try:
        store.apply_agent_profile_patch(
            "agent-a",
            patch_json={"style_hints": {"tone": "teaching"}},
            source="http.profile.apply",
        )
    except ValueError as exc:
        assert str(exc) == "inactive agent profile"
    else:
        raise AssertionError("Expected apply_agent_profile_patch() to reject inactive profiles")
