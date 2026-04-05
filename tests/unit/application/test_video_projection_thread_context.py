import importlib
import importlib.util

from video_agent.domain.video_thread_models import VideoIteration
from video_agent.domain.video_thread_models import VideoResult
from video_agent.domain.video_thread_models import VideoThread
from video_agent.domain.video_thread_models import VideoThreadParticipant


MODULE_NAME = "video_agent.application.video_projection_thread_context"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_thread_context_resolves_owner_fallback_and_management_permissions() -> None:
    module = _load_module()
    thread = VideoThread(
        thread_id="thread-1",
        owner_agent_id="owner-1",
        title="Circle explainer",
        origin_prompt="draw a circle",
    )
    fallback_participants = module.resolve_participants(
        store_participants=[],
        thread=thread,
    )
    management = module.build_participant_management(
        owner_agent_id="owner-1",
        participants=[
            fallback_participants[0],
            VideoThreadParticipant(
                thread_id="thread-1",
                participant_id="repairer-1",
                participant_type="agent",
                agent_id="repairer-1",
                role="repairer",
                display_name="Repairer",
            ),
        ],
        viewer_agent_id="viewer-2",
    )

    assert fallback_participants[0].participant_type == "owner"
    assert fallback_participants[0].display_name == "Owner"
    assert management.can_manage is False
    assert management.removable_participant_ids == []
    assert management.disabled_reason == "Only the thread owner can manage participants."


def test_thread_context_builds_responsibility_and_actions_from_iteration_and_result_state() -> None:
    module = _load_module()
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
        result_summary="Selected cut with a slower title entrance.",
    )
    responsibility = module.build_responsibility(
        current_iteration=current_iteration,
        current_result=current_result,
        runs=[],
    )
    actions = module.build_actions(
        current_iteration=current_iteration,
        current_result=current_result,
    )

    assert responsibility.owner_action_required == "review_latest_result"
    assert responsibility.expected_agent_role == "repairer"
    assert responsibility.expected_agent_id == "repairer-1"
    assert actions.items[0].action_id == "request_revision"
    assert actions.items[0].description == "Create the next revision from the selected result and current goal."
    assert actions.items[0].disabled is False


def test_thread_context_builds_composer_context_hint_and_disabled_state() -> None:
    module = _load_module()
    current_iteration = VideoIteration(
        iteration_id="iter-2",
        thread_id="thread-1",
        goal="Refine the opener pacing",
        requested_action="revise",
    )
    current_result = VideoResult(
        result_id="result-2",
        thread_id="thread-1",
        iteration_id="iter-2",
        result_summary="Selected cut with a slower title entrance.",
    )
    participants = [
        VideoThreadParticipant(
            thread_id="thread-1",
            participant_id="repairer-1",
            participant_type="agent",
            agent_id="repairer-1",
            role="repairer",
            display_name="Repairer",
        )
    ]
    composer = module.build_composer(
        participants=participants,
        current_iteration=current_iteration,
        current_result=current_result,
        runs=[],
        results=[current_result],
        turns=[],
    )
    disabled = module.build_composer(
        participants=participants,
        current_iteration=None,
        current_result=None,
        runs=[],
        results=[],
        turns=[],
    )

    assert composer.disabled is False
    assert composer.context_hint.startswith("The selected cut is ready for review")
    assert composer.target.iteration_id == "iter-2"
    assert disabled.disabled is True
    assert disabled.disabled_reason == "No active iteration is available yet."
