import importlib
import importlib.util

from video_agent.domain.video_thread_models import (
    VideoAgentRun,
    VideoIteration,
    VideoResult,
    VideoThreadAction,
    VideoThreadActions,
    VideoThreadLatestExplanation,
    VideoThreadParticipant,
    VideoTurn,
)


MODULE_NAME = "video_agent.application.video_projection_history"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_build_history_prefers_run_explanation_and_selection_cards_without_duplicate_owner_request() -> None:
    module = _load_module()
    participants = [
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="repairer-1",
            participant_type="agent",
            agent_id="repairer-1",
            role="repairer",
            display_name="Repairer",
        ),
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="planner-1",
            participant_type="agent",
            agent_id="planner-1",
            role="planner",
            display_name="Planner",
        ),
    ]
    current_iteration = VideoIteration(
        iteration_id="iter-2",
        thread_id="thread-1",
        goal="Refine the opener pacing",
        requested_action="revise",
        responsible_role="repairer",
        responsible_agent_id="repairer-1",
    )
    current_result = VideoResult(
        result_id="result-2",
        thread_id="thread-1",
        iteration_id="iter-2",
        result_summary="Slower opener with more deliberate title motion.",
    )
    turns = [
        VideoTurn(
            turn_id="turn-owner",
            thread_id="thread-1",
            iteration_id="iter-2",
            turn_type="owner_request",
            intent_type="request_explanation",
            speaker_type="owner",
            title="Why this pacing?",
            summary="Explain the slower opener.",
            related_result_id=current_result.result_id,
        ),
        VideoTurn(
            turn_id="turn-agent",
            thread_id="thread-1",
            iteration_id="iter-2",
            turn_type="agent_reply",
            intent_type="request_explanation",
            speaker_type="agent",
            speaker_agent_id="planner-1",
            speaker_role="planner",
            title="Why the opener changed",
            summary="The slower opening gives the title card room to land.",
            reply_to_turn_id="turn-owner",
            related_result_id=current_result.result_id,
        ),
    ]
    runs = [
        VideoAgentRun(
            run_id="run-1",
            thread_id="thread-1",
            iteration_id="iter-2",
            task_id="task-1",
            agent_id="repairer-1",
            role="repairer",
            status="running",
            output_summary="Refining the title motion timing.",
        )
    ]
    latest_explanation = VideoThreadLatestExplanation(
        turn_id="turn-agent",
        summary="The slower opening gives the title card room to land.",
        speaker_display_name="Planner",
        speaker_role="planner",
    )

    history = module.build_history(
        participants=participants,
        turns=turns,
        runs=runs,
        latest_explanation=latest_explanation,
        current_iteration=current_iteration,
        current_result=current_result,
        current_result_selection_reason="This is the latest selected revision for the active iteration.",
    )

    assert [card.card_type for card in history.cards] == [
        "process_update",
        "agent_explanation",
        "result_selection",
    ]
    assert history.cards[0].actor_display_name == "Repairer"
    assert history.cards[0].intent_type == "request_revision"
    assert history.cards[1].reply_to_turn_id == "turn-owner"
    assert history.cards[2].actor_display_name == "Repairer"


def test_build_history_falls_back_to_latest_owner_request_when_no_run_or_explanation_exists() -> None:
    module = _load_module()
    current_iteration = VideoIteration(
        iteration_id="iter-1",
        thread_id="thread-1",
        goal="Clarify the ask",
        requested_action="generate",
    )
    turns = [
        VideoTurn(
            turn_id="turn-owner-1",
            thread_id="thread-1",
            iteration_id="iter-1",
            turn_type="owner_request",
            intent_type="generate",
            speaker_type="owner",
            title="Make it bolder",
            summary="Make it bolder",
        )
    ]

    history = module.build_history(
        participants=[],
        turns=turns,
        runs=[],
        latest_explanation=VideoThreadLatestExplanation(),
        current_iteration=current_iteration,
        current_result=None,
        current_result_selection_reason=None,
    )

    assert [card.card_type for card in history.cards] == ["owner_request"]
    assert history.cards[0].summary == "Make it bolder"
    assert history.cards[0].actor_role == "owner"


def test_dedupe_history_cards_keeps_first_non_empty_summary_per_card_type() -> None:
    module = _load_module()
    deduped = module.dedupe_history_cards(
        [
            module.VideoThreadHistoryCard(
                card_id="a",
                card_type="process_update",
                title="A",
                summary="Same summary",
            ),
            module.VideoThreadHistoryCard(
                card_id="b",
                card_type="process_update",
                title="B",
                summary="Same summary",
            ),
            module.VideoThreadHistoryCard(
                card_id="c",
                card_type="owner_request",
                title="C",
                summary="",
            ),
        ]
    )

    assert [card.card_id for card in deduped] == ["a"]


def test_build_next_recommended_move_matches_owner_action_required() -> None:
    module = _load_module()
    actions = VideoThreadActions(
        items=[
            VideoThreadAction(action_id="discuss", label="Discuss"),
            VideoThreadAction(action_id="request_revision", label="Request revision"),
            VideoThreadAction(action_id="request_explanation", label="Request explanation"),
        ]
    )

    attention = module.build_next_recommended_move(
        responsibility=type("R", (), {"owner_action_required": "review_latest_result"})(),
        actions=actions,
        current_iteration=None,
        current_result=None,
    )
    active = module.build_next_recommended_move(
        responsibility=type("R", (), {"owner_action_required": "provide_follow_up"})(),
        actions=actions,
        current_iteration=object(),
        current_result=None,
    )

    assert attention.recommended_action_id == "request_revision"
    assert attention.tone == "attention"
    assert active.recommended_action_id == "discuss"
    assert active.tone == "attention"
