from pathlib import Path

import pytest

from video_agent.application.agent_identity_service import hash_agent_token
from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.video_iteration_service import VideoIterationService
from video_agent.application.video_thread_service import VideoThreadService
from video_agent.application.video_turn_service import VideoTurnService
from video_agent.config import Settings
from video_agent.domain.agent_models import AgentProfile, AgentToken
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


def _build_store(tmp_path: Path) -> SQLiteTaskStore:
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()
    return SQLiteTaskStore(database_path)


def _build_settings(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    return bootstrapped_settings(
        Settings(
            data_dir=data_dir,
            database_path=data_dir / "video_agent.db",
            artifact_root=data_dir / "tasks",
            run_embedded_worker=False,
        )
    )


def test_video_thread_service_creates_root_iteration_and_owner_turn(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    iteration_service = VideoIterationService(store=store)
    turn_service = VideoTurnService(store=store)
    service = VideoThreadService(
        store=store,
        iteration_service=iteration_service,
        turn_service=turn_service,
    )

    outcome = service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle with a bold title card",
    )

    assert outcome.thread.thread_id.startswith("thread-")
    assert outcome.thread.origin_prompt == "draw a circle with a bold title card"
    assert outcome.iteration.parent_iteration_id is None
    assert outcome.iteration.requested_action == "generate"
    assert outcome.turn.turn_type == "owner_request"
    assert outcome.turn.speaker_type == "owner"
    assert service.load_thread(outcome.thread.thread_id).thread_id == outcome.thread.thread_id


def test_video_thread_service_selects_result_for_thread(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    iteration_service = VideoIterationService(store=store)
    turn_service = VideoTurnService(store=store)
    service = VideoThreadService(
        store=store,
        iteration_service=iteration_service,
        turn_service=turn_service,
    )
    outcome = service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle",
    )
    result = iteration_service.register_result(
        thread_id=outcome.thread.thread_id,
        iteration_id=outcome.iteration.iteration_id,
        source_task_id="task-1",
        status="ready",
        result_summary="First cut",
    )

    updated = service.select_result(outcome.thread.thread_id, result.result_id)

    assert updated.thread.selected_result_id == result.result_id
    assert updated.thread.current_iteration_id == outcome.iteration.iteration_id


def test_video_thread_service_carries_selected_result_into_revision_source(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))

    created = app_context.video_thread_service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle",
    )
    origin_result = app_context.video_iteration_service.register_result(
        thread_id=created.thread.thread_id,
        iteration_id=created.iteration.iteration_id,
        source_task_id=created.created_task.task_id if created.created_task is not None else "task-origin",
        status="ready",
        result_summary="Initial cut with a brisk opener.",
    )
    app_context.video_thread_service.select_result(created.thread.thread_id, origin_result.result_id)

    revised = app_context.video_thread_service.request_revision(
        thread_id=created.thread.thread_id,
        base_task_id=created.created_task.task_id if created.created_task is not None else "",
        summary="Slow the opener and make the title entrance more deliberate.",
        preserve_working_parts=True,
    )

    assert revised.iteration.source_result_id == origin_result.result_id


def test_video_thread_service_uses_base_iteration_result_for_targeted_revision(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))

    created = app_context.video_thread_service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle",
    )
    origin_result = app_context.video_iteration_service.register_result(
        thread_id=created.thread.thread_id,
        iteration_id=created.iteration.iteration_id,
        source_task_id=created.created_task.task_id if created.created_task is not None else "task-origin",
        status="ready",
        result_summary="Initial cut with a brisk opener.",
    )
    app_context.video_thread_service.select_result(created.thread.thread_id, origin_result.result_id)

    revised = app_context.video_thread_service.request_revision(
        thread_id=created.thread.thread_id,
        base_task_id=created.created_task.task_id if created.created_task is not None else "",
        base_iteration_id=created.iteration.iteration_id,
        summary="Slow the opener and make the title entrance more deliberate.",
        preserve_working_parts=True,
    )
    revised_result = app_context.video_iteration_service.register_result(
        thread_id=created.thread.thread_id,
        iteration_id=revised.iteration.iteration_id,
        source_task_id=revised.created_task.task_id if revised.created_task is not None else "task-revised",
        status="ready",
        result_summary="Selected cut with a slower title entrance.",
    )
    app_context.video_thread_service.select_result(created.thread.thread_id, revised_result.result_id)

    targeted = app_context.video_thread_service.request_revision(
        thread_id=created.thread.thread_id,
        base_iteration_id=created.iteration.iteration_id,
        summary="Create an alternate opener branch from the first cut.",
        preserve_working_parts=True,
    )

    assert targeted.iteration.parent_iteration_id == created.iteration.iteration_id
    assert targeted.iteration.source_result_id == origin_result.result_id
    assert targeted.turn.related_result_id == origin_result.result_id


def test_video_thread_service_revision_inherits_continuity_target_into_iteration_and_task(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))

    created = app_context.video_thread_service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle",
    )
    app_context.video_thread_service.upsert_participant(
        thread_id=created.thread.thread_id,
        participant_id="repairer-1",
        participant_type="agent",
        agent_id="repairer-1",
        role="repairer",
        display_name="Repairer",
    )
    app_context.video_iteration_service.assign_responsibility(
        created.iteration.iteration_id,
        responsible_role="repairer",
        responsible_agent_id="repairer-1",
    )
    origin_result = app_context.video_iteration_service.register_result(
        thread_id=created.thread.thread_id,
        iteration_id=created.iteration.iteration_id,
        source_task_id=created.created_task.task_id if created.created_task is not None else "task-origin",
        status="ready",
        result_summary="Initial cut with a brisk opener.",
    )
    app_context.video_thread_service.select_result(created.thread.thread_id, origin_result.result_id)

    revised = app_context.video_thread_service.request_revision(
        thread_id=created.thread.thread_id,
        base_iteration_id=created.iteration.iteration_id,
        summary="Keep the geometry but let Repairer soften the title entrance.",
        preserve_working_parts=True,
    )

    assert revised.iteration.responsible_role == "repairer"
    assert revised.iteration.responsible_agent_id == "repairer-1"
    stored_task = app_context.store.get_task(revised.created_task.task_id if revised.created_task is not None else "")
    assert stored_task is not None
    assert stored_task.target_participant_id == "repairer-1"
    assert stored_task.target_agent_id == "repairer-1"
    assert stored_task.target_agent_role == "repairer"


def test_video_thread_service_defaults_discussion_target_to_responsible_participant(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    iteration_service = VideoIterationService(store=store)
    turn_service = VideoTurnService(store=store)
    service = VideoThreadService(
        store=store,
        iteration_service=iteration_service,
        turn_service=turn_service,
    )
    created = service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle",
    )
    iteration_service.assign_responsibility(
        created.iteration.iteration_id,
        responsible_role="repairer",
        responsible_agent_id="repairer-1",
    )
    service.upsert_participant(
        thread_id=created.thread.thread_id,
        participant_id="repairer-1",
        participant_type="agent",
        agent_id="repairer-1",
        role="repairer",
        display_name="Repairer",
    )

    outcome = service.append_turn(
        thread_id=created.thread.thread_id,
        iteration_id=created.iteration.iteration_id,
        title="Please keep the title but slow the opener",
        summary="I want to discuss the pacing tradeoff.",
        reply_to_turn_id="turn-root",
        related_result_id="result-1",
    )

    assert outcome.turn.intent_type == "discuss"
    assert outcome.turn.addressed_participant_id == "repairer-1"
    assert outcome.turn.addressed_agent_id == "repairer-1"
    assert outcome.turn.reply_to_turn_id == "turn-root"
    assert outcome.turn.related_result_id == "result-1"


def test_create_app_context_wires_video_thread_services(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))

    assert app_context.video_thread_service is not None
    assert app_context.video_iteration_service is not None
    assert app_context.video_turn_service is not None
    assert app_context.video_run_binding_service is not None
    assert app_context.video_policy_service is not None


def test_video_thread_service_denies_non_owner_participant_mutation(tmp_path: Path) -> None:
    app_context = create_app_context(_build_settings(tmp_path))
    app_context.store.upsert_agent_profile(AgentProfile(agent_id="agent-a", name="agent-a"))
    app_context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-a-secret"),
            agent_id="agent-a",
        )
    )
    app_context.store.upsert_agent_profile(AgentProfile(agent_id="agent-b", name="agent-b"))
    app_context.store.issue_agent_token(
        AgentToken(
            token_hash=hash_agent_token("agent-b-secret"),
            agent_id="agent-b",
            scopes_json={"allow": ["task:read", "task:mutate"]},
        )
    )
    owner = app_context.agent_identity_service.authenticate("agent-a-secret")
    intruder = app_context.agent_identity_service.authenticate("agent-b-secret")
    outcome = app_context.video_thread_service.create_thread(
        owner_agent_id="agent-a",
        title="Circle explainer",
        prompt="draw a circle",
        agent_principal=owner,
    )

    with pytest.raises(PermissionError):
        app_context.video_thread_service.upsert_participant(
            thread_id=outcome.thread.thread_id,
            participant_id="reviewer-1",
            participant_type="agent",
            agent_id="agent-b",
            role="reviewer",
            display_name="Reviewer",
            capabilities=["review_bundle:read"],
            agent_principal=intruder,
        )

    with pytest.raises(PermissionError):
        app_context.video_thread_service.remove_participant(
            thread_id=outcome.thread.thread_id,
            participant_id="owner",
            agent_principal=intruder,
        )
