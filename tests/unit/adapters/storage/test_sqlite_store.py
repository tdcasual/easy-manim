import json
import sqlite3

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.agent_learning_models import AgentLearningEvent
from video_agent.domain.agent_memory_models import AgentMemoryRecord
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.domain.agent_profile_revision_models import AgentProfileRevision
from video_agent.domain.agent_profile_suggestion_models import AgentProfileSuggestion
from video_agent.domain.agent_session_models import AgentSession
from video_agent.domain.models import VideoTask
from video_agent.domain.quality_models import QualityScorecard
from video_agent.domain.review_workflow_models import WorkflowParticipant
from video_agent.domain.video_thread_models import (
    VideoAgentRun,
    VideoIteration,
    VideoResult,
    VideoThread,
    VideoThreadParticipant,
    VideoTurn,
)


def _build_store(tmp_path) -> SQLiteTaskStore:
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()
    return SQLiteTaskStore(database_path)


def test_store_can_insert_and_fetch_task(tmp_path) -> None:
    store = _build_store(tmp_path)
    task = VideoTask(prompt="draw a circle")
    store.create_task(task, idempotency_key="abc")

    loaded = store.get_task(task.task_id)
    assert loaded is not None
    assert loaded.prompt == "draw a circle"


def test_sqlite_bootstrapper_applies_migrations_and_prepares_store(tmp_path) -> None:
    database_path = tmp_path / "agent.db"
    report = SQLiteBootstrapper(database_path).bootstrap()

    assert report.database_path == database_path
    assert report.applied_migration_ids

    with sqlite3.connect(database_path) as connection:
        applied = connection.execute(
            "SELECT migration_id FROM schema_migrations ORDER BY migration_id"
        ).fetchall()
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert [row[0] for row in applied] == report.applied_migration_ids
    assert "video_tasks" in tables
    assert "agent_profiles" in tables

    store = SQLiteTaskStore(database_path)
    task = VideoTask(prompt="draw a circle")
    store.create_task(task, idempotency_key="bootstrapped")

    loaded = store.get_task(task.task_id)
    assert loaded is not None
    assert loaded.prompt == "draw a circle"


def test_sqlite_bootstrapper_adds_task_title_columns(tmp_path) -> None:
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(video_tasks)").fetchall()
        }

    assert "display_title" in columns
    assert "title_source" in columns


def test_sqlite_bootstrapper_adds_task_memory_projection_columns(tmp_path) -> None:
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(video_tasks)").fetchall()
        }

    assert "task_memory_context_json" in columns
    assert "selected_memory_ids_json" in columns
    assert "persistent_memory_context_summary" in columns
    assert "persistent_memory_context_digest" in columns


def test_sqlite_bootstrapper_adds_reliability_columns_and_tables(tmp_path) -> None:
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(video_tasks)").fetchall()
        }
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }

    assert "risk_level" in columns
    assert "generation_mode" in columns
    assert "strategy_profile_id" in columns
    assert "scene_spec_id" in columns
    assert "quality_gate_status" in columns
    assert "accepted_as_best" in columns
    assert "accepted_version_rank" in columns
    assert "task_quality_scores" in tables


def test_sqlite_bootstrapper_adds_video_thread_runtime_tables_and_columns(tmp_path) -> None:
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()

    with sqlite3.connect(database_path) as connection:
        task_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(video_tasks)").fetchall()
        }
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        indexes = {
            row[1]
            for row in connection.execute("PRAGMA index_list(video_iterations)").fetchall()
        }

    assert "thread_id" in task_columns
    assert "iteration_id" in task_columns
    assert "result_id" in task_columns
    assert "execution_kind" in task_columns
    assert "video_threads" in tables
    assert "video_iterations" in tables
    assert "video_turns" in tables
    assert "video_results" in tables
    assert "video_thread_participants" in tables
    assert "video_agent_runs" in tables
    assert "idx_video_iterations_thread_created_at" in indexes


def test_store_persists_thread_binding_fields_on_tasks(tmp_path) -> None:
    store = _build_store(tmp_path)
    task = VideoTask(
        prompt="draw a circle",
        thread_id="thread-1",
        iteration_id="iter-1",
        result_id="result-1",
        execution_kind="initial_generation",
    )

    store.create_task(task, idempotency_key="thread-binding")
    loaded = store.get_task(task.task_id)

    assert loaded is not None
    assert loaded.thread_id == "thread-1"
    assert loaded.iteration_id == "iter-1"
    assert loaded.result_id == "result-1"
    assert loaded.execution_kind == "initial_generation"


def test_idempotency_key_returns_existing_task(tmp_path) -> None:
    store = _build_store(tmp_path)
    first = VideoTask(prompt="draw a circle")
    second = VideoTask(prompt="draw another circle")

    created = store.create_task(first, idempotency_key="same")
    duplicate = store.create_task(second, idempotency_key="same")
    assert duplicate.task_id == created.task_id


def test_store_lists_filtered_events_by_type_without_default_truncation(tmp_path) -> None:
    store = _build_store(tmp_path)
    task = VideoTask(prompt="draw a circle")
    store.create_task(task, idempotency_key="filtered-events")

    for index in range(205):
        store.append_event(
            task.task_id,
            "workflow_memory_pinned",
            {"memory_id": f"mem-{index}", "summary": f"pin memory {index}"},
        )
    store.append_event(task.task_id, "task_status_changed", {"status": "running"})

    filtered_events = store.list_events(
        task.task_id,
        limit=None,
        event_type="workflow_memory_pinned",
    )

    assert len(filtered_events) == 205
    assert filtered_events[0]["payload"]["memory_id"] == "mem-0"
    assert filtered_events[-1]["payload"]["memory_id"] == "mem-204"
    assert all(event["event_type"] == "workflow_memory_pinned" for event in filtered_events)


def test_store_round_trips_agent_profile(tmp_path) -> None:
    store = _build_store(tmp_path)
    profile = AgentProfile(
        agent_id="agent-a",
        name="Agent A",
        profile_json={"style_hints": {"tone": "teaching"}},
    )

    store.upsert_agent_profile(profile)

    loaded = store.get_agent_profile("agent-a")
    runtime_definition = store.get_agent_runtime_definition("agent-a")

    assert loaded is not None
    assert loaded.profile_json["style_hints"]["tone"] == "teaching"
    assert loaded.profile_version == 1
    assert runtime_definition is not None
    assert runtime_definition.definition_source == "materialized"
    assert runtime_definition.workspace.endswith("/agent-a/workspace")


def test_store_increments_profile_version_on_profile_update(tmp_path) -> None:
    store = _build_store(tmp_path)
    profile = AgentProfile(agent_id="agent-a", name="Agent A")
    store.upsert_agent_profile(profile)
    store.upsert_agent_profile(profile.model_copy(update={"profile_json": {"style_hints": {"tone": "teaching"}}}))

    loaded = store.get_agent_profile("agent-a")

    assert loaded is not None
    assert loaded.profile_version == 2


def test_store_resolves_agent_token_by_hash(tmp_path) -> None:
    store = _build_store(tmp_path)

    store.issue_agent_token(
        AgentToken(token_hash="hash-1", agent_id="agent-a", scopes_json={"mode": "default"})
    )

    loaded = store.get_agent_token("hash-1")

    assert loaded is not None
    assert loaded.agent_id == "agent-a"


def test_store_persists_task_agent_id(tmp_path) -> None:
    store = _build_store(tmp_path)
    task = VideoTask(prompt="draw a circle", agent_id="agent-a")

    store.create_task(task, idempotency_key="k1")

    loaded = store.get_task(task.task_id)

    assert loaded is not None
    assert loaded.agent_id == "agent-a"


def test_store_persists_task_profile_version_and_policy_flags(tmp_path) -> None:
    store = _build_store(tmp_path)
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
    store = _build_store(tmp_path)
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


def test_store_projects_structured_task_memory_context_into_dedicated_columns(tmp_path) -> None:
    store = _build_store(tmp_path)
    task = VideoTask(
        prompt="draw a circle",
        task_memory_context={
            "session": {
                "session_id": "session-1",
                "summary_text": "Recent attempts already established a light background.",
            },
            "persistent": {
                "memory_ids": ["mem-a"],
                "summary_text": "Prefer high-contrast diagrams and concise labels.",
                "summary_digest": "digest-mem-a",
                "items": [
                    {
                        "memory_id": "mem-a",
                        "summary_text": "Prefer high-contrast diagrams and concise labels.",
                        "summary_digest": "digest-mem-a",
                        "lineage_refs": ["video-task://task-1/task.json"],
                        "enhancement": {},
                    }
                ],
            },
        },
        selected_memory_ids=["mem-a"],
        persistent_memory_context_summary="Prefer high-contrast diagrams and concise labels.",
        persistent_memory_context_digest="digest-mem-a",
    )

    store.create_task(task, idempotency_key="task-memory-projection")
    task.feedback = "add labels"
    task.selected_memory_ids = ["mem-a", "mem-b"]
    task.task_memory_context["persistent"]["memory_ids"] = ["mem-a", "mem-b"]
    task.task_memory_context["persistent"]["items"].append(
        {
            "memory_id": "mem-b",
            "summary_text": "Add concise labels to every key step.",
            "summary_digest": "digest-mem-b",
            "lineage_refs": ["video-task://task-1/task.json"],
            "enhancement": {},
        }
    )
    task.persistent_memory_context_summary = "Prefer high-contrast diagrams and concise labels.\nAdd concise labels."
    task.persistent_memory_context_digest = "digest-mem-ab"
    store.update_task(task)

    with sqlite3.connect(store.database_path) as connection:
        row = connection.execute(
            """
            SELECT
                task_memory_context_json,
                selected_memory_ids_json,
                persistent_memory_context_summary,
                persistent_memory_context_digest
            FROM video_tasks
            WHERE task_id = ?
            """,
            (task.task_id,),
        ).fetchone()

    assert row is not None
    assert json.loads(row[0])["persistent"]["memory_ids"] == ["mem-a", "mem-b"]
    assert json.loads(row[1]) == ["mem-a", "mem-b"]
    assert row[2] == "Prefer high-contrast diagrams and concise labels.\nAdd concise labels."
    assert row[3] == "digest-mem-ab"


def test_sqlite_store_persists_reliability_task_fields(tmp_path) -> None:
    store = _build_store(tmp_path)
    task = VideoTask(
        prompt="draw a circle",
        risk_level="high",
        generation_mode="template_first",
    )

    store.create_task(task)
    loaded = store.get_task(task.task_id)

    assert loaded is not None
    assert loaded.risk_level == "high"
    assert loaded.generation_mode == "template_first"

    with sqlite3.connect(store.database_path) as connection:
        row = connection.execute(
            "SELECT risk_level, generation_mode FROM video_tasks WHERE task_id = ?",
            (task.task_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == "high"
    assert row[1] == "template_first"


def test_store_round_trips_agent_memory_record(tmp_path) -> None:
    store = _build_store(tmp_path)
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
    store = _build_store(tmp_path)
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
    store = _build_store(tmp_path)
    session = AgentSession(
        session_id="sess-1",
        session_hash="hash-1",
        agent_id="agent-a",
        token_hash="token-hash-1",
    )

    store.create_agent_session(session)
    loaded = store.get_agent_session("hash-1")

    assert loaded is not None
    assert loaded.agent_id == "agent-a"
    assert loaded.status == "active"


def test_store_touches_and_revokes_agent_session(tmp_path) -> None:
    store = _build_store(tmp_path)
    session = AgentSession(
        session_id="sess-1",
        session_hash="hash-1",
        agent_id="agent-a",
        token_hash="token-hash-1",
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


def test_store_round_trips_task_quality_score(tmp_path) -> None:
    store = _build_store(tmp_path)
    scorecard = QualityScorecard(
        task_id="task-1",
        total_score=0.72,
        dimension_scores={"motion_smoothness": 0.4, "prompt_alignment": 0.8},
        must_fix_issues=["static_previews"],
        accepted=False,
    )

    store.upsert_task_quality_score("task-1", scorecard)
    loaded = store.get_task_quality_score("task-1")

    assert loaded is not None
    assert loaded.total_score == 0.72
    assert loaded.dimension_scores["motion_smoothness"] == 0.4


def test_store_round_trips_workflow_participants(tmp_path) -> None:
    store = _build_store(tmp_path)
    reviewer = store.upsert_workflow_participant(
        WorkflowParticipant(
            root_task_id="root-1",
            agent_id="agent-b",
            role="reviewer",
        )
    )
    repairer = store.upsert_workflow_participant(
        WorkflowParticipant(
            root_task_id="root-1",
            agent_id="agent-c",
            role="repairer",
        )
    )

    loaded = store.get_workflow_participant("root-1", "agent-b")
    participants = store.list_workflow_participants("root-1")

    assert loaded is not None
    assert loaded.role == "reviewer"
    assert loaded.capabilities == ["review_bundle:read", "review_decision:write"]
    assert [participant.agent_id for participant in participants] == ["agent-b", "agent-c"]
    assert participants[0].created_at == reviewer.created_at
    assert participants[1].created_at == repairer.created_at


def test_store_round_trips_video_thread_runtime_entities(tmp_path) -> None:
    store = _build_store(tmp_path)
    thread = store.upsert_video_thread(
        VideoThread(
            thread_id="thread-1",
            owner_agent_id="agent-a",
            title="Circle lesson",
            origin_prompt="draw a circle",
        )
    )
    iteration = store.upsert_video_iteration(
        VideoIteration(
            iteration_id="iter-1",
            thread_id=thread.thread_id,
            goal="Draft the first version",
        )
    )
    turn = store.upsert_video_turn(
        VideoTurn(
            turn_id="turn-1",
            thread_id=thread.thread_id,
            iteration_id=iteration.iteration_id,
            turn_type="owner_request",
            speaker_type="owner",
            title="Initial request",
            summary="Please draw a circle",
        )
    )
    result = store.upsert_video_result(
        VideoResult(
            result_id="result-1",
            thread_id=thread.thread_id,
            iteration_id=iteration.iteration_id,
            source_task_id="task-1",
            status="completed",
            result_summary="Produced a blue circle",
        )
    )
    participant = store.upsert_video_thread_participant(
        VideoThreadParticipant(
            thread_id=thread.thread_id,
            participant_id="participant-1",
            participant_type="agent",
            agent_id="agent-b",
            role="reviewer",
            display_name="Reviewer",
        )
    )
    run = store.upsert_video_agent_run(
        VideoAgentRun(
            run_id="run-1",
            thread_id=thread.thread_id,
            iteration_id=iteration.iteration_id,
            agent_id="agent-b",
            role="reviewer",
            status="completed",
        )
    )

    loaded_thread = store.get_video_thread(thread.thread_id)
    loaded_iteration = store.get_video_iteration(iteration.iteration_id)
    loaded_turn = store.get_video_turn(turn.turn_id)
    loaded_result = store.get_video_result(result.result_id)
    loaded_participant = store.get_video_thread_participant(thread.thread_id, participant.participant_id)
    loaded_run = store.get_video_agent_run(run.run_id)

    assert loaded_thread is not None
    assert loaded_thread.title == "Circle lesson"
    assert loaded_iteration is not None
    assert loaded_iteration.goal == "Draft the first version"
    assert loaded_turn is not None
    assert loaded_turn.summary == "Please draw a circle"
    assert loaded_result is not None
    assert loaded_result.result_summary == "Produced a blue circle"
    assert loaded_participant is not None
    assert loaded_participant.display_name == "Reviewer"
    assert loaded_run is not None
    assert loaded_run.role == "reviewer"

    assert [item.iteration_id for item in store.list_video_iterations(thread.thread_id)] == ["iter-1"]
    assert [item.turn_id for item in store.list_video_turns(thread.thread_id)] == ["turn-1"]
    assert [item.result_id for item in store.list_video_results(thread.thread_id)] == ["result-1"]
    assert [item.participant_id for item in store.list_video_thread_participants(thread.thread_id)] == ["participant-1"]
    assert [item.run_id for item in store.list_video_agent_runs(thread.thread_id)] == ["run-1"]


def test_store_video_thread_runtime_upserts_preserve_created_at(tmp_path) -> None:
    store = _build_store(tmp_path)
    thread = store.upsert_video_thread(
        VideoThread(
            thread_id="thread-1",
            owner_agent_id="agent-a",
            title="Circle lesson",
            origin_prompt="draw a circle",
        )
    )
    iteration = store.upsert_video_iteration(
        VideoIteration(
            iteration_id="iter-1",
            thread_id=thread.thread_id,
            goal="Draft the first version",
        )
    )
    result = store.upsert_video_result(
        VideoResult(
            result_id="result-1",
            thread_id=thread.thread_id,
            iteration_id=iteration.iteration_id,
            result_summary="First result",
        )
    )
    run = store.upsert_video_agent_run(
        VideoAgentRun(
            run_id="run-1",
            thread_id=thread.thread_id,
            iteration_id=iteration.iteration_id,
            agent_id="agent-b",
            role="reviewer",
        )
    )

    updated_thread = store.upsert_video_thread(thread.model_copy(update={"title": "Updated title"}))
    updated_iteration = store.upsert_video_iteration(iteration.model_copy(update={"goal": "Refine the version"}))
    updated_result = store.upsert_video_result(result.model_copy(update={"result_summary": "Updated result"}))
    updated_run = store.upsert_video_agent_run(run.model_copy(update={"status": "completed"}))

    assert updated_thread.created_at == thread.created_at
    assert updated_iteration.created_at == iteration.created_at
    assert updated_result.created_at == result.created_at
    assert updated_run.created_at == run.created_at


def test_store_round_trips_agent_profile_revision(tmp_path) -> None:
    store = _build_store(tmp_path)
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
    assert revision.patch_json == {"style_hints": {"tone": "teaching"}}

    loaded_revisions = store.list_agent_profile_revisions("agent-a")
    assert len(loaded_revisions) == 1
    assert loaded_revisions[0].revision_id == revision.revision_id


def test_store_rejects_profile_patch_for_inactive_profile(tmp_path) -> None:
    store = _build_store(tmp_path)
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


def test_store_dedupes_pending_profile_suggestions(tmp_path) -> None:
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

    assert duplicate.suggestion_id == created.suggestion_id
    assert len(store.list_agent_profile_suggestions("agent-a")) == 1


def test_store_requires_expected_status_for_profile_suggestion_transition(tmp_path) -> None:
    store = _build_store(tmp_path)
    suggestion = store.create_agent_profile_suggestion(
        AgentProfileSuggestion(
            suggestion_id="sugg-1",
            agent_id="agent-a",
            patch_json={"style_hints": {"tone": "teaching"}},
            rationale_json={"profile_version": 3},
        )
    )

    applied = store.update_agent_profile_suggestion_status(
        suggestion.suggestion_id,
        status="applied",
        applied_at=suggestion.created_at,
        expected_status="pending",
    )
    rejected = store.update_agent_profile_suggestion_status(
        suggestion.suggestion_id,
        status="dismissed",
        expected_status="pending",
    )

    assert applied is not None
    assert applied.status == "applied"
    assert applied.applied_at == suggestion.created_at
    assert rejected is None
    persisted = store.get_agent_profile_suggestion(suggestion.suggestion_id)
    assert persisted is not None
    assert persisted.status == "applied"
    assert persisted.applied_at == suggestion.created_at


def test_store_apply_agent_profile_suggestion_updates_profile_revision_and_status(tmp_path) -> None:
    store = _build_store(tmp_path)
    store.upsert_agent_profile(
        AgentProfile(
            agent_id="agent-a",
            name="Agent A",
            profile_json={"style_hints": {"tone": "patient"}},
        )
    )
    suggestion = store.create_agent_profile_suggestion(
        AgentProfileSuggestion(
            suggestion_id="sugg-1",
            agent_id="agent-a",
            patch_json={"style_hints": {"tone": "teaching"}},
            rationale_json={"profile_version": 1},
        )
    )

    updated_profile, revision, updated_suggestion = store.apply_agent_profile_suggestion(
        "agent-a",
        suggestion_id=suggestion.suggestion_id,
        source="profile_suggestion:sugg-1",
    )

    assert updated_profile.profile_json["style_hints"]["tone"] == "teaching"
    assert revision.source == "profile_suggestion:sugg-1"
    assert updated_suggestion.status == "applied"
    assert updated_suggestion.applied_at is not None


def test_store_apply_agent_profile_suggestion_rejects_non_pending_status(tmp_path) -> None:
    store = _build_store(tmp_path)
    store.upsert_agent_profile(AgentProfile(agent_id="agent-a", name="Agent A"))
    suggestion = store.create_agent_profile_suggestion(
        AgentProfileSuggestion(
            suggestion_id="sugg-1",
            agent_id="agent-a",
            patch_json={"style_hints": {"tone": "teaching"}},
            rationale_json={"profile_version": 1},
            status="dismissed",
        )
    )

    try:
        store.apply_agent_profile_suggestion(
            "agent-a",
            suggestion_id=suggestion.suggestion_id,
            source="profile_suggestion:sugg-1",
        )
    except RuntimeError as exc:
        assert str(exc) == "profile_suggestion_state_conflict"
    else:
        raise AssertionError("Expected apply_agent_profile_suggestion() to reject non-pending status")


def test_store_learning_event_upsert_returns_persisted_row(tmp_path) -> None:
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


def test_initialize_deduplicates_legacy_learning_events_before_adding_unique_index(tmp_path) -> None:
    database_path = tmp_path / "agent.db"
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            CREATE TABLE agent_learning_events (
                event_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                session_id TEXT,
                status TEXT NOT NULL,
                issue_codes_json TEXT NOT NULL,
                quality_score REAL NOT NULL,
                profile_digest TEXT,
                memory_ids_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO agent_learning_events (
                event_id, agent_id, task_id, session_id, status, issue_codes_json,
                quality_score, profile_digest, memory_ids_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evt-1",
                "agent-a",
                "task-1",
                "sess-1",
                "failed",
                "[]",
                0.2,
                "digest-1",
                "[]",
                "2026-03-20T00:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO agent_learning_events (
                event_id, agent_id, task_id, session_id, status, issue_codes_json,
                quality_score, profile_digest, memory_ids_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "evt-2",
                "agent-a",
                "task-1",
                "sess-1",
                "completed",
                "[]",
                0.9,
                "digest-1",
                "[]",
                "2026-03-20T00:01:00+00:00",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    SQLiteBootstrapper(database_path).bootstrap()
    store = SQLiteTaskStore(database_path)

    events = store.list_agent_learning_events("agent-a")

    assert len(events) == 1
    assert events[0].event_id == "evt-2"
    assert events[0].quality_score == 0.9
