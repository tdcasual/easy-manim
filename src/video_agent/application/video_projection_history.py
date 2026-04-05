from __future__ import annotations

from video_agent.application.video_projection_iteration_story import (
    current_result_author_display_name,
    current_result_author_role,
    resolve_participant_display_name,
)
from video_agent.domain.video_thread_models import (
    VideoThreadActions,
    VideoThreadHistory,
    VideoThreadHistoryCard,
    VideoThreadLatestExplanation,
    VideoThreadNextRecommendedMove,
    VideoThreadParticipant,
    VideoThreadResponsibility,
)


def build_next_recommended_move(
    *,
    responsibility: VideoThreadResponsibility,
    actions: VideoThreadActions,
    current_iteration,
    current_result,
) -> VideoThreadNextRecommendedMove:
    action_map = {item.action_id: item for item in actions.items}
    action_id = None
    summary = "Keep the thread moving by choosing the next collaboration action."
    tone: str = "neutral"
    if responsibility.owner_action_required == "review_latest_result":
        action_id = "request_revision"
        summary = "Review the latest selected result, then request a focused revision or record a note."
        tone = "attention"
    elif responsibility.owner_action_required == "wait_for_agent":
        summary = "Wait for the active agent run to finish before steering the next iteration."
        tone = "active"
    elif responsibility.owner_action_required == "provide_follow_up":
        action_id = "discuss"
        summary = "Provide follow-up direction so the active revision can continue with sharper constraints."
        tone = "attention"
    elif current_result is not None:
        action_id = "request_explanation"
        summary = "You can request a product-safe explanation, ask for another revision, or add a note."
        tone = "active"
    elif current_iteration is not None:
        action_id = "discuss"
        summary = "Capture the next instruction or question to keep this iteration moving."
        tone = "active"
    action = None if action_id is None else action_map.get(action_id)
    return VideoThreadNextRecommendedMove(
        summary=summary,
        recommended_action_id=None if action is None else action.action_id,
        recommended_action_label=None if action is None else action.label,
        owner_action_required=responsibility.owner_action_required,
        tone=tone,  # type: ignore[arg-type]
    )


def build_history(
    *,
    participants: list[VideoThreadParticipant],
    turns,
    runs,
    latest_explanation: VideoThreadLatestExplanation,
    current_iteration,
    current_result,
    current_result_selection_reason: str | None,
) -> VideoThreadHistory:
    cards: list[VideoThreadHistoryCard] = []

    latest_run = runs[-1] if runs else None
    if latest_run is not None and latest_run.output_summary:
        cards.append(
            VideoThreadHistoryCard(
                card_id=f"run:{latest_run.run_id}",
                card_type="process_update",
                title=f"{resolve_participant_display_name(participants=participants, agent_id=latest_run.agent_id, role=latest_run.role) or 'Agent'} is working on this",
                summary=latest_run.output_summary,
                iteration_id=latest_run.iteration_id,
                intent_type=resolve_iteration_intent_type(
                    current_iteration=current_iteration,
                    turns=turns,
                    iteration_id=latest_run.iteration_id,
                ),
                actor_display_name=resolve_participant_display_name(
                    participants=participants,
                    agent_id=latest_run.agent_id,
                    role=latest_run.role,
                ),
                actor_role=latest_run.role,
                emphasis="supporting",
            )
        )

    if latest_explanation.turn_id and latest_explanation.summary:
        cards.append(
            VideoThreadHistoryCard(
                card_id=f"turn:{latest_explanation.turn_id}",
                card_type="agent_explanation",
                title=latest_explanation.title or "Latest visible explanation",
                summary=latest_explanation.summary,
                iteration_id=iteration_id_for_turn(turns, latest_explanation.turn_id),
                intent_type="request_explanation",
                reply_to_turn_id=reply_to_turn_id_for_turn(turns, latest_explanation.turn_id),
                related_result_id=related_result_id_for_turn(turns, latest_explanation.turn_id),
                actor_display_name=latest_explanation.speaker_display_name,
                actor_role=latest_explanation.speaker_role,
                emphasis="primary",
            )
        )

    if current_result_selection_reason and (current_result is not None or latest_run is not None):
        actor_role = current_result_author_role(
            current_iteration=current_iteration,
            runs=runs,
            turns=turns,
        )
        cards.append(
            VideoThreadHistoryCard(
                card_id=f"selection:{None if current_iteration is None else current_iteration.iteration_id}:{None if current_result is None else current_result.result_id}",
                card_type="result_selection",
                title="Selected result rationale",
                summary=current_result_selection_reason,
                iteration_id=None if current_iteration is None else current_iteration.iteration_id,
                intent_type=resolve_iteration_intent_type(
                    current_iteration=current_iteration,
                    turns=turns,
                    iteration_id=None if current_iteration is None else current_iteration.iteration_id,
                ),
                related_result_id=None if current_result is None else current_result.result_id,
                actor_display_name=current_result_author_display_name(
                    participants=participants,
                    current_iteration=current_iteration,
                    runs=runs,
                    turns=turns,
                ),
                actor_role=actor_role,
                emphasis="supporting",
            )
        )

    latest_owner_turn = next(
        (
            turn
            for turn in reversed(turns)
            if turn.visibility == "product_safe"
            and turn.speaker_type == "owner"
            and (turn.summary.strip() or turn.title.strip())
        ),
        None,
    )
    should_include_latest_owner_turn = not (
        latest_run is not None and latest_run.output_summary and latest_explanation.turn_id
    )
    if should_include_latest_owner_turn and latest_owner_turn is not None and (
        latest_owner_turn.summary.strip()
        or (
            current_iteration is not None
            and latest_owner_turn.iteration_id == current_iteration.iteration_id
        )
    ):
        cards.append(
            VideoThreadHistoryCard(
                card_id=f"turn:{latest_owner_turn.turn_id}",
                card_type="owner_request",
                title=latest_owner_turn.title,
                summary=latest_owner_turn.summary or latest_owner_turn.title,
                iteration_id=latest_owner_turn.iteration_id,
                intent_type=latest_owner_turn.intent_type,
                reply_to_turn_id=latest_owner_turn.reply_to_turn_id,
                related_result_id=latest_owner_turn.related_result_id,
                actor_display_name=resolve_participant_display_name(
                    participants=participants,
                    agent_id=latest_owner_turn.speaker_agent_id,
                    role=latest_owner_turn.speaker_role or "owner",
                )
                or "Owner",
                actor_role=latest_owner_turn.speaker_role or "owner",
                emphasis="context",
            )
        )

    return VideoThreadHistory(cards=dedupe_history_cards(cards))


def dedupe_history_cards(cards: list[VideoThreadHistoryCard]) -> list[VideoThreadHistoryCard]:
    deduped: list[VideoThreadHistoryCard] = []
    seen: set[tuple[str, str]] = set()
    for card in cards:
        key = (card.card_type, card.summary.strip())
        if not card.summary.strip() or key in seen:
            continue
        deduped.append(card)
        seen.add(key)
    return deduped


def iteration_id_for_turn(turns, turn_id: str) -> str | None:
    for turn in turns:
        if turn.turn_id == turn_id:
            return turn.iteration_id
    return None


def reply_to_turn_id_for_turn(turns, turn_id: str) -> str | None:
    for turn in turns:
        if turn.turn_id == turn_id:
            return turn.reply_to_turn_id
    return None


def related_result_id_for_turn(turns, turn_id: str) -> str | None:
    for turn in turns:
        if turn.turn_id == turn_id:
            return turn.related_result_id
    return None


def latest_relevant_run(*, runs, iteration_id: str | None):
    if iteration_id is not None:
        for run in reversed(runs):
            if run.iteration_id == iteration_id:
                return run
    return runs[-1] if runs else None


def resolve_iteration_intent_type(*, current_iteration, turns, iteration_id: str | None) -> str | None:
    if iteration_id is None:
        return None
    if current_iteration is not None and current_iteration.iteration_id == iteration_id:
        if current_iteration.requested_action == "revise":
            return "request_revision"
        if current_iteration.requested_action == "generate":
            return "generate"
    for turn in reversed(turns):
        if turn.iteration_id == iteration_id and turn.intent_type:
            return turn.intent_type
    return None


def current_result_selection_reason(*, current_iteration, current_result, runs) -> str | None:
    if current_result is not None and current_iteration is not None:
        return (
            "This is the latest selected revision for the active iteration and remains aligned with "
            f"'{current_iteration.goal}'."
        )
    latest_run = runs[-1] if runs else None
    if latest_run is not None and current_iteration is not None:
        return (
            f"The active iteration is currently being shaped by the {latest_run.role} role "
            f"for '{current_iteration.goal}'."
        )
    if current_iteration is not None:
        return f"The active focus is still centered on '{current_iteration.goal}'."
    return None
