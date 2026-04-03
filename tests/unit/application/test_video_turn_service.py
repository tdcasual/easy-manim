from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.video_iteration_service import VideoIterationService
from video_agent.application.video_turn_service import VideoTurnService


def _build_store(tmp_path: Path) -> SQLiteTaskStore:
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()
    return SQLiteTaskStore(database_path)


def test_video_turn_service_appends_owner_and_agent_turns(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    store.upsert_video_thread_json(
        thread_id="thread-1",
        owner_agent_id="owner",
        title="Circle explainer",
        origin_prompt="draw a circle",
    )
    iteration = VideoIterationService(store=store).create_iteration(
        thread_id="thread-1",
        goal="Initial generation",
    )
    service = VideoTurnService(store=store)

    owner_turn = service.append_owner_turn(
        thread_id="thread-1",
        iteration_id=iteration.iteration_id,
        title="Please slow down the opening",
        intent_type="request_revision",
        related_result_id="result-1",
        addressed_participant_id="repairer-1",
        addressed_agent_id="repairer-1",
    )
    agent_turn = service.append_agent_explanation_turn(
        thread_id="thread-1",
        iteration_id=iteration.iteration_id,
        title="Why the current opening is fast",
        summary="The pace keeps the geometry reveal compact.",
        speaker_agent_id="planner-1",
        speaker_role="planner",
        intent_type="request_explanation",
        reply_to_turn_id=owner_turn.turn_id,
    )

    assert owner_turn.turn_type == "owner_request"
    assert owner_turn.intent_type == "request_revision"
    assert owner_turn.related_result_id == "result-1"
    assert owner_turn.addressed_participant_id == "repairer-1"
    assert owner_turn.addressed_agent_id == "repairer-1"
    assert owner_turn.visibility == "product_safe"
    persisted_owner_turn = store.get_video_turn(owner_turn.turn_id)
    assert persisted_owner_turn is not None
    assert persisted_owner_turn.addressed_participant_id == "repairer-1"
    assert persisted_owner_turn.addressed_agent_id == "repairer-1"
    assert agent_turn.turn_type == "agent_explanation"
    assert agent_turn.intent_type == "request_explanation"
    assert agent_turn.reply_to_turn_id == owner_turn.turn_id
    assert agent_turn.speaker_type == "agent"
    assert agent_turn.visibility == "product_safe"
