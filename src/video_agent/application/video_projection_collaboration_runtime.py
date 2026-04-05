from __future__ import annotations

from video_agent.application.video_projection_iteration_story import resolve_participant_display_name
from video_agent.domain.video_thread_models import (
    VideoThreadComposer,
    VideoThreadDiscussionGroup,
    VideoThreadDiscussionGroups,
    VideoThreadDiscussionReply,
    VideoThreadDiscussionRuntime,
    VideoThreadIterationDetailSummary,
    VideoThreadLatestExplanation,
    VideoThreadParticipant,
    VideoThreadParticipantRuntime,
    VideoThreadParticipantRuntimeContributor,
    VideoThreadResponsibility,
)


def display_name_for_turn(*, turn, participants: list[VideoThreadParticipant]) -> str | None:
    if turn.speaker_type == "owner":
        owner = next((participant for participant in participants if participant.participant_type == "owner"), None)
        return None if owner is None else owner.display_name
    if turn.speaker_agent_id is not None:
        participant = next(
            (item for item in participants if item.agent_id == turn.speaker_agent_id),
            None,
        )
        if participant is not None:
            return participant.display_name
    if turn.speaker_role:
        return turn.speaker_role.replace("_", " ").strip().title()
    return None


def display_name_for_addressed_turn(*, turn, participants: list[VideoThreadParticipant]) -> str | None:
    if turn.addressed_participant_id is not None:
        participant = next(
            (item for item in participants if item.participant_id == turn.addressed_participant_id),
            None,
        )
        if participant is not None:
            return participant.display_name
    if turn.addressed_agent_id is not None:
        participant = next(
            (item for item in participants if item.agent_id == turn.addressed_agent_id),
            None,
        )
        if participant is not None:
            return participant.display_name
    return None


def build_discussion_groups(
    *,
    participants: list[VideoThreadParticipant],
    turns,
) -> VideoThreadDiscussionGroups:
    visible_turns = [turn for turn in turns if turn.visibility == "product_safe"]
    groups: list[VideoThreadDiscussionGroup] = []

    for turn in reversed(visible_turns):
        if turn.speaker_type != "owner":
            continue
        if turn.reply_to_turn_id is not None:
            continue
        if turn.intent_type == "generate":
            continue

        replies = [
            VideoThreadDiscussionReply(
                turn_id=reply.turn_id,
                title=reply.title,
                summary=reply.summary,
                speaker_display_name=resolve_participant_display_name(
                    participants=participants,
                    agent_id=reply.speaker_agent_id,
                    role=reply.speaker_role or reply.speaker_type,
                ),
                speaker_role=reply.speaker_role,
                intent_type=reply.intent_type,
                related_result_id=reply.related_result_id,
            )
            for reply in visible_turns
            if reply.reply_to_turn_id == turn.turn_id
        ]
        groups.append(
            VideoThreadDiscussionGroup(
                group_id=f"group-{turn.turn_id}",
                iteration_id=turn.iteration_id,
                prompt_turn_id=turn.turn_id,
                prompt_title=turn.title,
                prompt_summary=turn.summary or turn.title,
                prompt_intent_type=turn.intent_type,
                prompt_actor_display_name=resolve_participant_display_name(
                    participants=participants,
                    agent_id=turn.speaker_agent_id,
                    role=turn.speaker_role or "owner",
                )
                or "Owner",
                prompt_actor_role=turn.speaker_role or "owner",
                related_result_id=turn.related_result_id,
                status="answered" if replies else "open",
                replies=replies,
            )
        )
    return VideoThreadDiscussionGroups(groups=groups)


def build_discussion_runtime(
    *,
    current_iteration,
    current_result,
    discussion_groups: VideoThreadDiscussionGroups,
    composer: VideoThreadComposer,
    iteration_detail: VideoThreadIterationDetailSummary,
    latest_explanation: VideoThreadLatestExplanation,
) -> VideoThreadDiscussionRuntime:
    active_group = select_active_discussion_group(
        discussion_groups=discussion_groups,
        current_iteration_id=None if current_iteration is None else current_iteration.iteration_id,
        execution_discussion_group_id=iteration_detail.execution_summary.discussion_group_id,
    )
    latest_reply = active_group.replies[-1] if active_group is not None and active_group.replies else None
    active_iteration_id = (
        None if current_iteration is None else current_iteration.iteration_id
    ) or iteration_detail.selected_iteration_id
    default_related_result_id = (
        composer.target.result_id
        or (None if active_group is None else active_group.related_result_id)
        or (None if current_result is None else current_result.result_id)
    )
    addressed_display_name = composer.target.addressed_display_name or composer.target.agent_display_name
    continuity_scope: str = "thread"
    if active_iteration_id is not None:
        continuity_scope = "iteration"
    elif default_related_result_id is not None:
        continuity_scope = "result"

    summary = "Continue the active collaboration thread for this video."
    if active_group is not None and addressed_display_name is not None:
        summary = (
            f"Continue '{active_group.prompt_title}' with {addressed_display_name} while staying on the active iteration."
        )
    elif active_group is not None:
        summary = f"Continue '{active_group.prompt_title}' while staying on the active iteration."
    elif addressed_display_name is not None and active_iteration_id is not None:
        summary = (
            f"New follow-ups will stay on iteration {active_iteration_id} and route to {addressed_display_name}."
        )

    return VideoThreadDiscussionRuntime(
        summary=summary,
        active_iteration_id=active_iteration_id,
        active_discussion_group_id=(
            None if active_group is None else active_group.group_id
        )
        or iteration_detail.execution_summary.discussion_group_id,
        continuity_scope=continuity_scope,  # type: ignore[arg-type]
        reply_policy="continue_thread",
        default_intent_type="discuss",
        default_reply_to_turn_id=(
            None if active_group is None else active_group.prompt_turn_id
        )
        or iteration_detail.execution_summary.reply_to_turn_id,
        default_related_result_id=default_related_result_id,
        addressed_participant_id=composer.target.addressed_participant_id,
        addressed_agent_id=composer.target.addressed_agent_id,
        addressed_display_name=addressed_display_name,
        suggested_follow_up_modes=[
            "ask_why",
            "request_change",
            "preserve_direction",
            "branch_revision",
        ],
        active_thread_title=None if active_group is None else active_group.prompt_title,
        active_thread_summary="" if active_group is None else active_group.prompt_summary,
        latest_owner_turn_id=(
            None if active_group is None else active_group.prompt_turn_id
        )
        or iteration_detail.execution_summary.latest_owner_turn_id,
        latest_agent_turn_id=(
            None if latest_reply is None else latest_reply.turn_id
        )
        or iteration_detail.execution_summary.latest_agent_turn_id
        or latest_explanation.turn_id,
        latest_agent_summary=(
            "" if latest_reply is None else latest_reply.summary
        )
        or latest_explanation.summary
        or iteration_detail.execution_summary.summary,
    )


def select_active_discussion_group(
    *,
    discussion_groups: VideoThreadDiscussionGroups,
    current_iteration_id: str | None,
    execution_discussion_group_id: str | None,
) -> VideoThreadDiscussionGroup | None:
    if current_iteration_id is not None:
        iteration_groups = [
            group
            for group in discussion_groups.groups
            if group.iteration_id == current_iteration_id
        ]
        if iteration_groups:
            return next(
                (group for group in iteration_groups if group.status == "answered"),
                iteration_groups[0],
            )
    if execution_discussion_group_id is not None:
        return next(
            (
                group
                for group in discussion_groups.groups
                if group.group_id == execution_discussion_group_id
            ),
            None,
        )
    return discussion_groups.groups[0] if discussion_groups.groups else None


def build_participant_runtime(
    *,
    current_iteration,
    participants: list[VideoThreadParticipant],
    turns,
    runs,
    composer: VideoThreadComposer,
    responsibility: VideoThreadResponsibility,
) -> VideoThreadParticipantRuntime:
    participant_by_agent_id = {
        participant.agent_id: participant
        for participant in participants
        if participant.agent_id is not None
    }
    active_iteration_id = (
        None if current_iteration is None else current_iteration.iteration_id
    ) or composer.target.iteration_id
    expected_agent_id = composer.target.addressed_agent_id or responsibility.expected_agent_id
    expected_display_name = (
        composer.target.addressed_display_name or composer.target.agent_display_name
    )
    expected_role = composer.target.agent_role or responsibility.expected_agent_role
    continuity_mode = (
        "keep_current_participant"
        if composer.target.addressed_participant_id is not None or expected_agent_id is not None
        else "agent_choice"
    )

    contributors: list[VideoThreadParticipantRuntimeContributor] = []
    seen_contributors: set[tuple[str | None, str | None, str]] = set()

    def add_contributor(
        *,
        participant_id: str | None,
        agent_id: str | None,
        display_name: str | None,
        role: str | None,
        contribution_kind: str,
        summary: str,
    ) -> None:
        label = display_name or (role.replace("_", " ").strip().title() if role else None)
        if label is None:
            return
        contributor_key = (participant_id, agent_id, label)
        if contributor_key in seen_contributors:
            return
        seen_contributors.add(contributor_key)
        contributors.append(
            VideoThreadParticipantRuntimeContributor(
                participant_id=participant_id,
                agent_id=agent_id,
                display_name=label,
                role=role,
                contribution_kind=contribution_kind,  # type: ignore[arg-type]
                summary=summary,
            )
        )

    add_contributor(
        participant_id=composer.target.addressed_participant_id,
        agent_id=expected_agent_id,
        display_name=expected_display_name,
        role=expected_role,
        contribution_kind="expected_responder",
        summary="Currently targeted for the next owner follow-up.",
    )
    for run in reversed(runs):
        if active_iteration_id is not None and run.iteration_id != active_iteration_id:
            continue
        participant = participant_by_agent_id.get(run.agent_id)
        add_contributor(
            participant_id=None if participant is None else participant.participant_id,
            agent_id=run.agent_id,
            display_name=(
                None if participant is None else participant.display_name
            )
            or run.role.replace("_", " ").strip().title(),
            role=run.role,
            contribution_kind="recent_run",
            summary=run.output_summary or f"Latest run is {run.status}.",
        )
    for turn in reversed(turns):
        if active_iteration_id is not None and turn.iteration_id != active_iteration_id:
            continue
        if turn.visibility != "product_safe" or turn.speaker_type != "agent":
            continue
        participant = participant_by_agent_id.get(turn.speaker_agent_id)
        add_contributor(
            participant_id=None if participant is None else participant.participant_id,
            agent_id=turn.speaker_agent_id,
            display_name=display_name_for_turn(turn=turn, participants=participants),
            role=turn.speaker_role,
            contribution_kind="recent_reply",
            summary=turn.summary or turn.title,
        )

    summary = "No participant continuity has been projected yet."
    if expected_display_name is not None:
        other_contributor = next(
            (
                contributor
                for contributor in contributors
                if contributor.display_name != expected_display_name
            ),
            None,
        )
        if other_contributor is not None and active_iteration_id is not None:
            summary = (
                f"{expected_display_name} is currently expected to respond, while "
                f"{other_contributor.display_name} also shaped the active iteration."
            )
        elif active_iteration_id is not None:
            summary = f"{expected_display_name} is currently expected to respond for the active iteration."
        else:
            summary = f"{expected_display_name} is currently expected to respond."

    return VideoThreadParticipantRuntime(
        summary=summary,
        active_iteration_id=active_iteration_id,
        expected_participant_id=composer.target.addressed_participant_id,
        expected_agent_id=expected_agent_id,
        expected_display_name=expected_display_name,
        expected_role=expected_role,
        continuity_mode=continuity_mode,  # type: ignore[arg-type]
        follow_up_target_locked=continuity_mode == "keep_current_participant",
        recent_contributors=contributors,
    )
