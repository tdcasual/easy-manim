from __future__ import annotations

from video_agent.domain.video_thread_models import VideoThreadParticipant
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.video_thread_models import (
    VideoThreadAction,
    VideoThreadActions,
    VideoThreadArtifactLineage,
    VideoThreadArtifactLineageItem,
    VideoThreadAuthorship,
    VideoThreadComposer,
    VideoThreadComposerTarget,
    VideoThreadConversation,
    VideoThreadConversationTurn,
    VideoThreadCurrentFocus,
    VideoThreadDecisionNote,
    VideoThreadDecisionNotes,
    VideoThreadDiscussionGroup,
    VideoThreadDiscussionGroups,
    VideoThreadDiscussionRuntime,
    VideoThreadDiscussionReply,
    VideoThreadHeader,
    VideoThreadHistory,
    VideoThreadHistoryCard,
    VideoThreadIterationCard,
    VideoThreadIterationCompare,
    VideoThreadIterationDetail,
    VideoThreadIterationExecutionSummary,
    VideoThreadIterationDetailResult,
    VideoThreadIterationDetailRun,
    VideoThreadIterationDetailSummary,
    VideoThreadIterationDetailTurn,
    VideoThreadIterationWorkbench,
    VideoThreadLatestExplanation,
    VideoThreadNextRecommendedMove,
    VideoThreadPanelPresentation,
    VideoThreadParticipantManagement,
    VideoThreadParticipantRuntime,
    VideoThreadParticipantRuntimeContributor,
    VideoThreadParticipantsSection,
    VideoThreadProductionJournal,
    VideoThreadProductionJournalEntry,
    VideoThreadProcess,
    VideoThreadProcessRun,
    VideoThreadRationaleSnapshot,
    VideoThreadRationaleSnapshots,
    VideoThreadRenderContract,
    VideoThreadResponsibility,
    VideoThreadSelectionSummary,
    VideoThreadSurface,
)


class VideoProjectionService:
    def __init__(self, *, store: SQLiteTaskStore) -> None:
        self.store = store

    def build_surface(self, thread_id: str, viewer_agent_id: str | None = None) -> VideoThreadSurface:
        thread = self.store.get_video_thread(thread_id)
        if thread is None:
            raise KeyError(f"Unknown thread_id: {thread_id}")
        iterations = self.store.list_video_iterations(thread_id)
        results = self.store.list_video_results(thread_id)
        turns = self.store.list_video_turns(thread_id)
        runs = self.store.list_video_agent_runs(thread_id)
        participants = self._resolve_participants(thread)

        current_iteration = next(
            (item for item in iterations if item.iteration_id == thread.current_iteration_id),
            iterations[-1] if iterations else None,
        )
        current_result = next(
            (item for item in results if item.result_id == thread.selected_result_id),
            results[-1] if results else None,
        )
        responsibility = self._build_responsibility(
            current_iteration=current_iteration,
            current_result=current_result,
            runs=runs,
        )
        actions = self._build_actions(
            current_iteration=current_iteration,
            current_result=current_result,
        )
        composer = self._build_composer(
            participants=participants,
            current_iteration=current_iteration,
            current_result=current_result,
            runs=runs,
            results=results,
            turns=turns,
        )
        current_result_author_display_name = self._current_result_author_display_name(
            participants=participants,
            current_iteration=current_iteration,
            runs=runs,
            turns=turns,
        )
        current_result_author_role = self._current_result_author_role(
            current_iteration=current_iteration,
            runs=runs,
            turns=turns,
        )
        current_result_selection_reason = self._current_result_selection_reason(
            current_iteration=current_iteration,
            current_result=current_result,
            runs=runs,
        )
        latest_explanation = self._build_latest_explanation(
            participants=participants,
            current_iteration=current_iteration,
            turns=turns,
            runs=runs,
        )
        decision_notes = self._build_decision_notes(
            current_iteration=current_iteration,
            current_result=current_result,
            current_result_selection_reason=current_result_selection_reason,
            latest_explanation=latest_explanation,
        )
        artifact_lineage = self._build_artifact_lineage(
            participants=participants,
            iterations=iterations,
            results=results,
            turns=turns,
            runs=runs,
            selected_result_id=thread.selected_result_id,
            current_iteration_id=None if current_iteration is None else current_iteration.iteration_id,
            current_result_selection_reason=current_result_selection_reason,
            latest_explanation=latest_explanation,
        )
        rationale_snapshots = self._build_rationale_snapshots(
            participants=participants,
            iterations=iterations,
            results=results,
            turns=turns,
            runs=runs,
            current_iteration_id=None if current_iteration is None else current_iteration.iteration_id,
            current_result_selection_reason=current_result_selection_reason,
        )
        iteration_compare = self._build_iteration_compare(
            participants=participants,
            iterations=iterations,
            results=results,
            turns=turns,
            runs=runs,
            current_iteration=current_iteration,
            current_result=current_result,
            current_result_selection_reason=current_result_selection_reason,
            latest_explanation=latest_explanation,
        )
        production_journal = self._build_production_journal(
            participants=participants,
            iterations=iterations,
            runs=runs,
            results=results,
            selected_result_id=thread.selected_result_id,
        )
        authorship = self._build_authorship(
            participants=participants,
            current_iteration=current_iteration,
            current_result=current_result,
            turns=turns,
            runs=runs,
        )
        history = self._build_history(
            participants=participants,
            turns=turns,
            runs=runs,
            latest_explanation=latest_explanation,
            current_iteration=current_iteration,
            current_result=current_result,
            current_result_selection_reason=current_result_selection_reason,
        )
        next_recommended_move = self._build_next_recommended_move(
            responsibility=responsibility,
            actions=actions,
            current_iteration=current_iteration,
            current_result=current_result,
        )
        discussion_groups = self._build_discussion_groups(
            participants=participants,
            turns=turns,
        )
        iteration_detail = self._build_iteration_detail_summary(
            thread_id=thread.thread_id,
            selected_iteration=current_iteration,
            participants=participants,
            turns=turns,
            runs=runs,
            results=results,
        )
        discussion_runtime = self._build_discussion_runtime(
            current_iteration=current_iteration,
            current_result=current_result,
            discussion_groups=discussion_groups,
            composer=composer,
            iteration_detail=iteration_detail,
            latest_explanation=latest_explanation,
        )
        participant_runtime = self._build_participant_runtime(
            current_iteration=current_iteration,
            participants=participants,
            turns=turns,
            runs=runs,
            composer=composer,
            responsibility=responsibility,
        )
        render_contract = self._build_render_contract(
            responsibility=responsibility,
            participants=participants,
            current_result=current_result,
            current_iteration=current_iteration,
            actions=actions,
            latest_explanation=latest_explanation,
            decision_notes=decision_notes,
            artifact_lineage=artifact_lineage,
            rationale_snapshots=rationale_snapshots,
            iteration_compare=iteration_compare,
            authorship=authorship,
            production_journal=production_journal,
            discussion_runtime=discussion_runtime,
            participant_runtime=participant_runtime,
            history=history,
            discussion_groups=discussion_groups,
            has_iteration_detail=iteration_detail.selected_iteration_id is not None,
        )

        return VideoThreadSurface(
            thread_header=VideoThreadHeader(
                thread_id=thread.thread_id,
                title=thread.title,
                status=thread.status,
                current_iteration_id=thread.current_iteration_id,
                selected_result_id=thread.selected_result_id,
            ),
            thread_summary=f"{thread.title} is tracked as a durable video collaboration thread.",
            current_focus=VideoThreadCurrentFocus(
                current_iteration_id=None if current_iteration is None else current_iteration.iteration_id,
                current_iteration_goal=None if current_iteration is None else current_iteration.goal,
                current_result_id=None if current_result is None else current_result.result_id,
                current_result_summary=None if current_result is None else current_result.result_summary,
                current_result_author_display_name=current_result_author_display_name,
                current_result_author_role=current_result_author_role,
                current_result_selection_reason=current_result_selection_reason,
            ),
            selection_summary=VideoThreadSelectionSummary(
                summary=current_result_selection_reason or "",
                selected_result_id=None if current_result is None else current_result.result_id,
                author_display_name=current_result_author_display_name,
                author_role=current_result_author_role,
            ),
            latest_explanation=latest_explanation,
            decision_notes=decision_notes,
            artifact_lineage=artifact_lineage,
            rationale_snapshots=rationale_snapshots,
            iteration_compare=iteration_compare,
            authorship=authorship,
            next_recommended_move=next_recommended_move,
            responsibility=responsibility,
            iteration_workbench=VideoThreadIterationWorkbench(
                iterations=[
                    VideoThreadIterationCard(
                        iteration_id=item.iteration_id,
                        title=item.goal,
                        goal=item.goal,
                        status=item.status,
                        resolution_state=item.resolution_state,
                        requested_action=item.requested_action,
                        result_summary=next(
                            (
                                result.result_summary
                                for result in results
                                if result.iteration_id == item.iteration_id and result.selected
                            ),
                            None,
                        )
                        or next(
                            (
                                result.result_summary
                                for result in reversed(results)
                                if result.iteration_id == item.iteration_id
                            ),
                            None,
                        ),
                        responsible_role=item.responsible_role,
                        responsible_agent_id=item.responsible_agent_id,
                    )
                    for item in iterations
                ],
                selected_iteration_id=thread.current_iteration_id,
                latest_iteration_id=iterations[-1].iteration_id if iterations else None,
            ),
            iteration_detail=iteration_detail,
            conversation=VideoThreadConversation(
                turns=[
                    VideoThreadConversationTurn(
                        turn_id=turn.turn_id,
                        iteration_id=turn.iteration_id,
                        title=turn.title,
                        summary=turn.summary,
                        intent_type=turn.intent_type,
                        reply_to_turn_id=turn.reply_to_turn_id,
                        related_result_id=turn.related_result_id,
                        addressed_participant_id=turn.addressed_participant_id,
                        addressed_agent_id=turn.addressed_agent_id,
                        speaker_type=turn.speaker_type,
                        speaker_role=turn.speaker_role,
                    )
                    for turn in turns
                    if turn.visibility == "product_safe"
                ]
            ),
            history=history,
            production_journal=production_journal,
            discussion_groups=discussion_groups,
            discussion_runtime=discussion_runtime,
            participant_runtime=participant_runtime,
            process=VideoThreadProcess(
                runs=[
                    VideoThreadProcessRun(
                        run_id=run.run_id,
                        iteration_id=run.iteration_id,
                        task_id=run.task_id,
                        role=run.role,
                        status=run.status,
                        phase=run.phase,
                        output_summary=run.output_summary,
                    )
                    for run in runs
                ]
            ),
            participants=VideoThreadParticipantsSection(
                items=participants,
                management=self._build_participant_management(
                    owner_agent_id=thread.owner_agent_id,
                    participants=participants,
                    viewer_agent_id=viewer_agent_id,
                ),
            ),
            actions=actions,
            composer=composer,
            render_contract=render_contract,
        )

    def build_timeline_payload(self, thread_id: str) -> dict[str, object]:
        surface = self.build_surface(thread_id)
        return {
            "thread_id": thread_id,
            "conversation": surface.conversation.model_dump(mode="json"),
            "process": surface.process.model_dump(mode="json"),
        }

    def build_iteration_payload(self, thread_id: str, iteration_id: str) -> dict[str, object]:
        iteration = self.store.get_video_iteration(iteration_id)
        if iteration is None or iteration.thread_id != thread_id:
            raise KeyError(f"Unknown iteration_id: {iteration_id}")
        thread = self.store.get_video_thread(thread_id)
        if thread is None:
            raise KeyError(f"Unknown thread_id: {thread_id}")
        participants = self._resolve_participants(thread)
        detail = self._build_iteration_detail(
            thread_id=thread_id,
            iteration=iteration,
            participants=participants,
            turns=self.store.list_video_turns(thread_id),
            runs=self.store.list_video_agent_runs(thread_id),
            results=self.store.list_video_results(thread_id),
        )
        return detail.model_dump(mode="json")

    @classmethod
    def _build_iteration_detail_summary(
        cls,
        *,
        thread_id: str,
        selected_iteration,
        participants: list[VideoThreadParticipant],
        turns,
        runs,
        results,
    ) -> VideoThreadIterationDetailSummary:
        if selected_iteration is None:
            return VideoThreadIterationDetailSummary(
                summary="No iteration is selected yet.",
            )
        iteration_turns = [
            turn
            for turn in turns
            if turn.iteration_id == selected_iteration.iteration_id and turn.visibility == "product_safe"
        ]
        iteration_runs = [run for run in runs if run.iteration_id == selected_iteration.iteration_id]
        iteration_results = [result for result in results if result.iteration_id == selected_iteration.iteration_id]
        summary = (
            f"This iteration is focused on {selected_iteration.goal.strip()} "
            f"and currently tracks {len(iteration_turns)} visible turns, {len(iteration_runs)} runs, "
            f"and {len(iteration_results)} results."
            if selected_iteration.goal.strip()
            else f"This iteration currently tracks {len(iteration_turns)} visible turns, "
            f"{len(iteration_runs)} runs, and {len(iteration_results)} results."
        )
        return VideoThreadIterationDetailSummary(
            summary=summary,
            selected_iteration_id=selected_iteration.iteration_id,
            resource_uri=f"video-thread://{thread_id}/iterations/{selected_iteration.iteration_id}.json",
            turn_count=len(iteration_turns),
            run_count=len(iteration_runs),
            result_count=len(iteration_results),
            execution_summary=cls._build_iteration_execution_summary(
                iteration=selected_iteration,
                participants=participants,
                runs=iteration_runs,
                results=iteration_results,
                turns=iteration_turns,
            ),
        )

    @classmethod
    def _build_iteration_detail(
        cls,
        *,
        thread_id: str,
        iteration,
        participants: list[VideoThreadParticipant],
        turns,
        runs,
        results,
    ) -> VideoThreadIterationDetail:
        participant_by_agent_id = {
            participant.agent_id: participant
            for participant in participants
            if participant.agent_id
        }
        iteration_turns = [
            turn
            for turn in turns
            if turn.iteration_id == iteration.iteration_id and turn.visibility == "product_safe"
        ]
        iteration_runs = [run for run in runs if run.iteration_id == iteration.iteration_id]
        iteration_results = [result for result in results if result.iteration_id == iteration.iteration_id]
        summary = (
            f"This iteration is carrying the goal '{iteration.goal.strip()}' across visible discussion, "
            f"agent activity, and produced results."
            if iteration.goal.strip()
            else "This iteration captures the visible discussion, agent activity, and produced results."
        )
        composer_target = cls._build_composer_target(
            iteration=iteration,
            participants=participants,
            runs=iteration_runs,
            results=iteration_results,
            turns=iteration_turns,
        )
        return VideoThreadIterationDetail(
            thread_id=thread_id,
            iteration_id=iteration.iteration_id,
            summary=summary,
            execution_summary=cls._build_iteration_execution_summary(
                iteration=iteration,
                participants=participants,
                runs=iteration_runs,
                results=iteration_results,
                turns=iteration_turns,
            ),
            composer_target=composer_target,
            iteration=iteration,
            turns=[
                VideoThreadIterationDetailTurn(
                    turn_id=turn.turn_id,
                    turn_type=turn.turn_type,
                    title=turn.title,
                    summary=turn.summary,
                    intent_type=turn.intent_type,
                    reply_to_turn_id=turn.reply_to_turn_id,
                    related_result_id=turn.related_result_id,
                    addressed_participant_id=turn.addressed_participant_id,
                    addressed_agent_id=turn.addressed_agent_id,
                    addressed_display_name=cls._display_name_for_addressed_turn(
                        turn=turn,
                        participants=participants,
                    ),
                    speaker_display_name=cls._display_name_for_turn(
                        turn=turn,
                        participants=participants,
                    ),
                    speaker_role=turn.speaker_role,
                    created_at=turn.created_at,
                )
                for turn in iteration_turns
            ],
            runs=[
                VideoThreadIterationDetailRun(
                    run_id=run.run_id,
                    agent_id=run.agent_id,
                    agent_display_name=(
                        participant_by_agent_id.get(run.agent_id).display_name
                        if participant_by_agent_id.get(run.agent_id) is not None
                        else run.role.replace("_", " ").strip().title()
                    ),
                    role=run.role,
                    status=run.status,
                    phase=run.phase,
                    output_summary=run.output_summary,
                    task_id=run.task_id,
                    created_at=run.created_at,
                )
                for run in iteration_runs
            ],
            results=[
                VideoThreadIterationDetailResult(
                    result_id=result.result_id,
                    status=result.status,
                    result_summary=result.result_summary,
                    selected=result.selected,
                    video_resource=result.video_resource,
                    created_at=result.created_at,
                )
                for result in iteration_results
            ],
        )

    @classmethod
    def _build_iteration_execution_summary(
        cls,
        *,
        iteration,
        participants: list[VideoThreadParticipant],
        runs,
        results,
        turns,
    ) -> VideoThreadIterationExecutionSummary:
        target_result = cls._target_result_for_iteration(iteration=iteration, results=results)
        composer_target = cls._build_composer_target(
            iteration=iteration,
            participants=participants,
            runs=runs,
            results=results,
            turns=turns,
        )
        latest_owner_turn = next(
            (
                turn
                for turn in reversed(turns)
                if turn.iteration_id == iteration.iteration_id
                and turn.visibility == "product_safe"
                and turn.speaker_type == "owner"
                and turn.reply_to_turn_id is None
                and turn.intent_type != "generate"
            ),
            None,
        )
        latest_agent_turn = next(
            (
                turn
                for turn in reversed(turns)
                if turn.iteration_id == iteration.iteration_id
                and turn.visibility == "product_safe"
                and turn.speaker_type == "agent"
            ),
            None,
        )
        discussion_group_id = None if latest_owner_turn is None else f"group-{latest_owner_turn.turn_id}"
        participant_by_agent_id = {
            participant.agent_id: participant
            for participant in participants
            if participant.agent_id is not None
        }
        latest_run = next((run for run in reversed(runs) if run.iteration_id == iteration.iteration_id), None)
        if latest_run is not None:
            agent_display_name = (
                participant_by_agent_id.get(latest_run.agent_id).display_name
                if participant_by_agent_id.get(latest_run.agent_id) is not None
                else composer_target.agent_display_name
                or latest_run.role.replace("_", " ").strip().title()
            )
            phase_label = latest_run.phase or latest_run.status.replace("_", " ").strip()
            result_suffix = (
                f" while shaping result {target_result.result_id}"
                if target_result is not None
                else ""
            )
            if latest_run.status in {"running", "queued", "pending"}:
                summary = (
                    f"{agent_display_name} is currently {phase_label} for task {latest_run.task_id}{result_suffix}."
                    if latest_run.task_id
                    else f"{agent_display_name} is currently {phase_label}{result_suffix}."
                )
            elif latest_run.status == "completed":
                summary = (
                    f"{agent_display_name} completed {phase_label} for task {latest_run.task_id}"
                    f"{' and produced result ' + target_result.result_id if target_result is not None else ''}."
                    if latest_run.task_id
                    else f"{agent_display_name} completed {phase_label}"
                    f"{' and produced result ' + target_result.result_id if target_result is not None else ''}."
                )
            else:
                summary = (
                    f"{agent_display_name} ended {phase_label} for task {latest_run.task_id} with status {latest_run.status}."
                    if latest_run.task_id
                    else f"{agent_display_name} ended {phase_label} with status {latest_run.status}."
                )
            return VideoThreadIterationExecutionSummary(
                summary=summary,
                task_id=latest_run.task_id,
                run_id=latest_run.run_id,
                status=latest_run.status,
                phase=latest_run.phase,
                agent_id=latest_run.agent_id,
                agent_display_name=agent_display_name,
                agent_role=latest_run.role,
                result_id=None if target_result is None else target_result.result_id,
                discussion_group_id=discussion_group_id,
                reply_to_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
                latest_owner_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
                latest_agent_turn_id=None if latest_agent_turn is None else latest_agent_turn.turn_id,
                is_active=latest_run.status in {"running", "queued", "pending"},
            )

        agent_id = iteration.responsible_agent_id or composer_target.addressed_agent_id
        agent_role = iteration.responsible_role or composer_target.agent_role
        agent_display_name = composer_target.addressed_display_name or composer_target.agent_display_name
        if agent_display_name is None and agent_role is not None:
            agent_display_name = agent_role.replace("_", " ").strip().title()
        if agent_display_name is not None:
            return VideoThreadIterationExecutionSummary(
                summary=(
                    f"{agent_display_name} has not started a tracked task yet, but the iteration is anchored to this agent."
                ),
                agent_id=agent_id,
                agent_display_name=agent_display_name,
                agent_role=agent_role,
                result_id=None if target_result is None else target_result.result_id,
                discussion_group_id=discussion_group_id,
                reply_to_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
                latest_owner_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
                latest_agent_turn_id=None if latest_agent_turn is None else latest_agent_turn.turn_id,
            )
        if target_result is not None:
            return VideoThreadIterationExecutionSummary(
                summary=f"This iteration is currently anchored to result {target_result.result_id}.",
                result_id=target_result.result_id,
                discussion_group_id=discussion_group_id,
                reply_to_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
                latest_owner_turn_id=None if latest_owner_turn is None else latest_owner_turn.turn_id,
                latest_agent_turn_id=None if latest_agent_turn is None else latest_agent_turn.turn_id,
            )
        return VideoThreadIterationExecutionSummary()

    @staticmethod
    def _display_name_for_turn(*, turn, participants: list[VideoThreadParticipant]) -> str | None:
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

    @staticmethod
    def _display_name_for_addressed_turn(*, turn, participants: list[VideoThreadParticipant]) -> str | None:
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

    @classmethod
    def _build_composer_target(
        cls,
        *,
        iteration,
        participants: list[VideoThreadParticipant],
        runs,
        results,
        turns,
    ) -> VideoThreadComposerTarget:
        if iteration is None:
            return VideoThreadComposerTarget(summary="No iteration is available yet.")
        target_result = cls._target_result_for_iteration(iteration=iteration, results=results)
        addressed_participant = cls._resolve_composer_participant(
            iteration=iteration,
            participants=participants,
            runs=runs,
            turns=turns,
        )
        latest_run = next((run for run in reversed(runs) if run.iteration_id == iteration.iteration_id), None)
        latest_agent_turn = next(
            (
                turn
                for turn in reversed(turns)
                if turn.iteration_id == iteration.iteration_id
                and turn.visibility == "product_safe"
                and turn.speaker_type == "agent"
            ),
            None,
        )
        fallback_agent_turn = latest_agent_turn or next(
            (
                turn
                for turn in reversed(turns)
                if turn.visibility == "product_safe" and turn.speaker_type == "agent"
            ),
            None,
        )
        target_agent_role = (
            iteration.responsible_role
            or (None if latest_run is None else latest_run.role)
            or (None if fallback_agent_turn is None else fallback_agent_turn.speaker_role)
        )
        target_agent_display_name = None
        target_agent_id = (
            (None if addressed_participant is None else addressed_participant.agent_id)
            or iteration.responsible_agent_id
            or (None if latest_run is None else latest_run.agent_id)
            or (None if fallback_agent_turn is None else fallback_agent_turn.speaker_agent_id)
        )
        if target_agent_id is not None:
            participant = next((item for item in participants if item.agent_id == target_agent_id), None)
            if participant is not None:
                target_agent_display_name = participant.display_name
        if target_agent_display_name is None and target_agent_role is not None:
            target_agent_display_name = target_agent_role.replace("_", " ").strip().title()
        summary_parts = [f"New messages will attach to {iteration.iteration_id}"]
        if target_result is not None:
            summary_parts.append(f"stay anchored to {target_result.result_id}")
        if target_agent_display_name is not None:
            summary_parts.append(f"hand off to {target_agent_display_name}")
        summary = ", ".join(summary_parts[:-1])
        if len(summary_parts) > 1:
            summary = f"{', '.join(summary_parts[:-1])}, and {summary_parts[-1]}."
        else:
            summary = f"{summary_parts[0]}."
        return VideoThreadComposerTarget(
            iteration_id=iteration.iteration_id,
            result_id=None if target_result is None else target_result.result_id,
            addressed_participant_id=(
                None if addressed_participant is None else addressed_participant.participant_id
            ),
            addressed_agent_id=None if addressed_participant is None else addressed_participant.agent_id,
            addressed_display_name=(
                None if addressed_participant is None else addressed_participant.display_name
            ),
            agent_role=target_agent_role,
            agent_display_name=target_agent_display_name,
            summary=summary,
        )

    @classmethod
    def _resolve_composer_participant(
        cls,
        *,
        iteration,
        participants: list[VideoThreadParticipant],
        runs,
        turns,
    ) -> VideoThreadParticipant | None:
        participant_by_id = {participant.participant_id: participant for participant in participants}
        participant_by_agent_id = {
            participant.agent_id: participant
            for participant in participants
            if participant.agent_id is not None
        }
        if iteration.responsible_agent_id is not None:
            participant = participant_by_agent_id.get(iteration.responsible_agent_id)
            if participant is not None:
                return participant
        participant = cls._participant_from_addressed_turn(
            turns=turns,
            participant_by_id=participant_by_id,
            iteration_id=iteration.iteration_id,
        )
        if participant is not None:
            return participant
        participant = cls._participant_from_runs(
            runs=runs,
            participant_by_agent_id=participant_by_agent_id,
            iteration_id=iteration.iteration_id,
        )
        if participant is not None:
            return participant
        participant = cls._participant_from_agent_turns(
            turns=turns,
            participant_by_agent_id=participant_by_agent_id,
            iteration_id=iteration.iteration_id,
        )
        if participant is not None:
            return participant
        participant = cls._participant_from_addressed_turn(
            turns=turns,
            participant_by_id=participant_by_id,
            iteration_id=None,
        )
        if participant is not None:
            return participant
        return cls._participant_from_agent_turns(
            turns=turns,
            participant_by_agent_id=participant_by_agent_id,
            iteration_id=None,
        )

    @staticmethod
    def _participant_from_addressed_turn(
        *,
        turns,
        participant_by_id: dict[str, VideoThreadParticipant],
        iteration_id: str | None,
    ) -> VideoThreadParticipant | None:
        for turn in reversed(turns):
            if iteration_id is not None and turn.iteration_id != iteration_id:
                continue
            if turn.addressed_participant_id is None:
                continue
            participant = participant_by_id.get(turn.addressed_participant_id)
            if participant is not None:
                return participant
        return None

    @staticmethod
    def _participant_from_runs(
        *,
        runs,
        participant_by_agent_id: dict[str, VideoThreadParticipant],
        iteration_id: str | None,
    ) -> VideoThreadParticipant | None:
        for run in reversed(runs):
            if iteration_id is not None and run.iteration_id != iteration_id:
                continue
            participant = participant_by_agent_id.get(run.agent_id)
            if participant is not None:
                return participant
        return None

    @staticmethod
    def _participant_from_agent_turns(
        *,
        turns,
        participant_by_agent_id: dict[str, VideoThreadParticipant],
        iteration_id: str | None,
    ) -> VideoThreadParticipant | None:
        for turn in reversed(turns):
            if iteration_id is not None and turn.iteration_id != iteration_id:
                continue
            if turn.visibility != "product_safe" or turn.speaker_type != "agent" or turn.speaker_agent_id is None:
                continue
            participant = participant_by_agent_id.get(turn.speaker_agent_id)
            if participant is not None:
                return participant
        return None

    @staticmethod
    def _target_result_for_iteration(*, iteration, results):
        selected = next(
            (
                result
                for result in reversed(results)
                if result.iteration_id == iteration.iteration_id and result.selected
            ),
            None,
        )
        if selected is not None:
            return selected
        explicit = next(
            (
                result
                for result in reversed(results)
                if result.result_id == iteration.selected_result_id
            ),
            None,
        )
        if explicit is not None:
            return explicit
        return next(
            (
                result
                for result in reversed(results)
                if result.iteration_id == iteration.iteration_id
            ),
            None,
        )

    def _resolve_participants(self, thread) -> list[VideoThreadParticipant]:
        participants = self.store.list_video_thread_participants(thread.thread_id)
        if participants:
            return participants
        return [
            VideoThreadParticipant(
                thread_id=thread.thread_id,
                participant_id="owner",
                participant_type="owner",
                agent_id=thread.owner_agent_id,
                role="owner",
                display_name="Owner",
            )
        ]

    @staticmethod
    def _build_participant_management(
        *,
        owner_agent_id: str,
        participants: list[VideoThreadParticipant],
        viewer_agent_id: str | None,
    ) -> VideoThreadParticipantManagement:
        can_manage = viewer_agent_id is None or viewer_agent_id == owner_agent_id
        removable_participant_ids = [
            participant.participant_id
            for participant in participants
            if participant.participant_type != "owner"
        ]
        return VideoThreadParticipantManagement(
            can_manage=can_manage,
            can_invite=can_manage,
            can_remove=can_manage and bool(removable_participant_ids),
            removable_participant_ids=removable_participant_ids if can_manage else [],
            disabled_reason="" if can_manage else "Only the thread owner can manage participants.",
            context_hint=(
                "Invite reviewers or helper agents into this thread."
                if can_manage
                else "Only the thread owner can invite or remove participants."
            ),
        )

    @staticmethod
    def _build_responsibility(
        *,
        current_iteration,
        current_result,
        runs,
    ) -> VideoThreadResponsibility:
        latest_run = runs[-1] if runs else None
        owner_action_required = "none"
        if current_result is not None:
            owner_action_required = "review_latest_result"
        elif latest_run is not None and latest_run.status in {"pending", "running"}:
            owner_action_required = "wait_for_agent"
        elif current_iteration is not None and current_iteration.requested_action == "revise":
            owner_action_required = "provide_follow_up"

        expected_agent_role = None
        expected_agent_id = None
        if current_iteration is not None:
            expected_agent_role = current_iteration.responsible_role
            expected_agent_id = current_iteration.responsible_agent_id
        if latest_run is not None:
            expected_agent_role = expected_agent_role or latest_run.role
            expected_agent_id = expected_agent_id or latest_run.agent_id

        return VideoThreadResponsibility(
            owner_action_required=owner_action_required,
            expected_agent_role=expected_agent_role,
            expected_agent_id=expected_agent_id,
        )

    @staticmethod
    def _build_actions(
        *,
        current_iteration,
        current_result,
    ) -> VideoThreadActions:
        has_iteration = current_iteration is not None
        has_result = current_result is not None
        return VideoThreadActions(
            items=[
                VideoThreadAction(
                    action_id="request_revision",
                    label="Request revision",
                    description=(
                        "Create the next revision from the selected result and current goal."
                        if has_result
                        else "Create the next revision for the active iteration."
                    ),
                    tone="strong",
                    disabled=not has_iteration,
                    disabled_reason="" if has_iteration else "No active iteration is available yet.",
                ),
                VideoThreadAction(
                    action_id="request_explanation",
                    label="Ask why",
                    description="Request a product-safe explanation for the current direction.",
                    tone="neutral",
                    disabled=not has_iteration,
                    disabled_reason="" if has_iteration else "No active iteration is available yet.",
                ),
                VideoThreadAction(
                    action_id="discuss",
                    label="Add note",
                    description="Record context without creating a new revision immediately.",
                    tone="muted",
                    disabled=not has_iteration,
                    disabled_reason="" if has_iteration else "No active iteration is available yet.",
                ),
            ]
        )

    @staticmethod
    def _build_composer(
        *,
        participants: list[VideoThreadParticipant],
        current_iteration,
        current_result,
        runs,
        results,
        turns,
    ) -> VideoThreadComposer:
        disabled = current_iteration is None
        context_hint = ""
        if current_result is not None and current_result.result_summary.strip():
            context_hint = (
                "The selected cut is ready for review or a focused revision request: "
                f"{current_result.result_summary.strip()}"
            )
        elif current_iteration is not None and current_iteration.goal.strip():
            context_hint = f"The active iteration is focused on: {current_iteration.goal.strip()}"
        target = VideoThreadComposerTarget(summary="No iteration is available yet.")
        if current_iteration is not None:
            target = VideoProjectionService._build_composer_target(
                iteration=current_iteration,
                participants=participants,
                runs=runs,
                results=results,
                turns=turns,
            )
        return VideoThreadComposer(
            disabled=disabled,
            disabled_reason="" if not disabled else "No active iteration is available yet.",
            context_hint=context_hint,
            target=target,
        )

    @staticmethod
    def _build_render_contract(
        *,
        responsibility: VideoThreadResponsibility,
        participants: list[VideoThreadParticipant],
        current_result,
        current_iteration,
        actions: VideoThreadActions,
        latest_explanation: VideoThreadLatestExplanation,
        decision_notes: VideoThreadDecisionNotes,
        artifact_lineage: VideoThreadArtifactLineage,
        rationale_snapshots: VideoThreadRationaleSnapshots,
        iteration_compare: VideoThreadIterationCompare,
        authorship: VideoThreadAuthorship,
        production_journal: VideoThreadProductionJournal,
        discussion_runtime: VideoThreadDiscussionRuntime,
        participant_runtime: VideoThreadParticipantRuntime,
        history: VideoThreadHistory,
        discussion_groups: VideoThreadDiscussionGroups,
        has_iteration_detail: bool,
    ) -> VideoThreadRenderContract:
        default_focus_panel = "current_focus"
        panel_tone = "active"
        display_priority = "normal"
        if responsibility.owner_action_required == "review_latest_result":
            default_focus_panel = "next_recommended_move"
            panel_tone = "attention"
            display_priority = "high"
        elif responsibility.owner_action_required == "provide_follow_up":
            default_focus_panel = "next_recommended_move"
            panel_tone = "attention"
            display_priority = "high"
        elif current_result is not None:
            default_focus_panel = "selection_summary"
            panel_tone = "active"
        elif latest_explanation.summary:
            default_focus_panel = "latest_explanation"
        elif current_iteration is not None and current_iteration.requested_action == "revise":
            default_focus_panel = "next_recommended_move"
            panel_tone = "attention"
            display_priority = "high"
        elif history.cards:
            default_focus_panel = "history"
        sticky_primary_action_id = next(
            (item.action_id for item in actions.items if item.action_id == "request_revision" and not item.disabled),
            None,
        )
        badge_order = ["owner_action_required"]
        if current_result is not None:
            badge_order.extend(["selected_result", "expected_agent_role"])
        elif responsibility.expected_agent_role:
            badge_order.append("expected_agent_role")
        panel_order = [
            "thread_header",
            "current_focus",
            "selection_summary",
            "latest_explanation",
            "decision_notes",
            "artifact_lineage",
            "rationale_snapshots",
            "iteration_compare",
            "authorship",
            "next_recommended_move",
            "production_journal",
            "discussion_runtime",
            "participant_runtime",
            "discussion_groups",
            "history",
            "iteration_workbench",
            "iteration_detail",
            "conversation",
            "participants",
            "process",
            "actions",
            "composer",
        ]
        if not participants:
            panel_order = [panel for panel in panel_order if panel != "participants"]
        default_expanded_panels = ["current_focus", "history", "actions", "composer"]
        if decision_notes.items:
            default_expanded_panels.insert(1, "decision_notes")
        if artifact_lineage.items:
            default_expanded_panels.insert(2 if decision_notes.items else 1, "artifact_lineage")
        if rationale_snapshots.items:
            default_expanded_panels.insert(
                3 if decision_notes.items and artifact_lineage.items else 2 if decision_notes.items or artifact_lineage.items else 1,
                "rationale_snapshots",
            )
        if (
            iteration_compare.current_iteration_id is not None
            and (iteration_compare.change_summary or iteration_compare.rationale_shift_summary or iteration_compare.continuity_summary)
        ):
            default_expanded_panels.insert(
                4
                if decision_notes.items and artifact_lineage.items and rationale_snapshots.items
                else 3
                if sum(bool(item) for item in (decision_notes.items, artifact_lineage.items, rationale_snapshots.items)) >= 2
                else 2
                if decision_notes.items or artifact_lineage.items or rationale_snapshots.items
                else 1,
                "iteration_compare",
            )
        if authorship.primary_agent_role:
            default_expanded_panels.insert(1, "authorship")
        if default_focus_panel == "next_recommended_move":
            default_expanded_panels.insert(1, "next_recommended_move")
        if production_journal.entries:
            default_expanded_panels.append("production_journal")
        if discussion_runtime.active_iteration_id is not None or discussion_runtime.active_discussion_group_id is not None:
            default_expanded_panels.append("discussion_runtime")
        if participant_runtime.expected_display_name is not None or participant_runtime.recent_contributors:
            default_expanded_panels.append("participant_runtime")
        if discussion_groups.groups:
            default_expanded_panels.append("discussion_groups")
        if has_iteration_detail:
            default_expanded_panels.append("iteration_detail")
        return VideoThreadRenderContract(
            default_focus_panel=default_focus_panel,
            panel_tone=panel_tone,
            display_priority=display_priority,
            badge_order=badge_order,
            panel_order=panel_order,
            default_expanded_panels=default_expanded_panels,
            sticky_primary_action_id=sticky_primary_action_id,
            sticky_primary_action_emphasis=(
                "strong"
                if panel_tone == "attention" and sticky_primary_action_id is not None
                else "normal" if sticky_primary_action_id is not None else "subtle"
            ),
            panel_presentations=VideoProjectionService._build_panel_presentations(
                panel_tone=panel_tone,
                default_focus_panel=default_focus_panel,
                has_decision_notes=bool(decision_notes.items),
                has_artifact_lineage=bool(artifact_lineage.items),
                has_rationale_snapshots=bool(rationale_snapshots.items),
                has_iteration_compare=iteration_compare.current_iteration_id is not None,
                has_authorship=bool(authorship.primary_agent_role),
                has_production_journal=bool(production_journal.entries),
                has_discussion_runtime=(
                    discussion_runtime.active_iteration_id is not None
                    or discussion_runtime.active_discussion_group_id is not None
                ),
                has_participant_runtime=(
                    participant_runtime.expected_display_name is not None
                    or bool(participant_runtime.recent_contributors)
                ),
                has_discussion_groups=bool(discussion_groups.groups),
                has_iteration_detail=has_iteration_detail,
                history_has_cards=bool(history.cards),
            ),
        )

    @staticmethod
    def _build_panel_presentations(
        *,
        panel_tone: str,
        default_focus_panel: str,
        has_decision_notes: bool,
        has_artifact_lineage: bool,
        has_rationale_snapshots: bool,
        has_iteration_compare: bool,
        has_authorship: bool,
        has_production_journal: bool,
        has_discussion_runtime: bool,
        has_participant_runtime: bool,
        has_discussion_groups: bool,
        has_iteration_detail: bool,
        history_has_cards: bool,
    ) -> list[VideoThreadPanelPresentation]:
        presentations = [
            VideoThreadPanelPresentation(
                panel_id="current_focus",
                tone="neutral",
                emphasis="primary" if default_focus_panel == "current_focus" else "supporting",
                default_open=True,
                collapsible=False,
            ),
            VideoThreadPanelPresentation(
                panel_id="next_recommended_move",
                tone="attention" if panel_tone == "attention" else "neutral",
                emphasis="primary" if default_focus_panel == "next_recommended_move" else "supporting",
                default_open=panel_tone == "attention",
                collapsible=False,
            ),
            VideoThreadPanelPresentation(
                panel_id="composer",
                tone="accent",
                emphasis="primary",
                default_open=True,
                collapsible=False,
            ),
        ]
        if has_decision_notes:
            presentations.insert(
                2,
                VideoThreadPanelPresentation(
                    panel_id="decision_notes",
                    tone="neutral",
                    emphasis="supporting",
                    default_open=True,
                    collapsible=True,
                ),
            )
        if has_artifact_lineage:
            presentations.insert(
                3 if has_decision_notes else 2,
                VideoThreadPanelPresentation(
                    panel_id="artifact_lineage",
                    tone="neutral",
                    emphasis="primary" if default_focus_panel == "artifact_lineage" else "supporting",
                    default_open=True,
                    collapsible=True,
                ),
            )
        if has_rationale_snapshots:
            presentations.insert(
                4 if has_decision_notes and has_artifact_lineage else 3 if has_decision_notes or has_artifact_lineage else 2,
                VideoThreadPanelPresentation(
                    panel_id="rationale_snapshots",
                    tone="neutral",
                    emphasis="primary" if default_focus_panel == "rationale_snapshots" else "supporting",
                    default_open=True,
                    collapsible=True,
                ),
            )
        if has_iteration_compare:
            presentations.insert(
                (
                    5
                    if has_decision_notes and has_artifact_lineage and has_rationale_snapshots
                    else 4
                    if (has_decision_notes and has_artifact_lineage)
                    or (has_decision_notes and has_rationale_snapshots)
                    or (has_artifact_lineage and has_rationale_snapshots)
                    else 3
                    if has_decision_notes or has_artifact_lineage or has_rationale_snapshots
                    else 2
                ),
                VideoThreadPanelPresentation(
                    panel_id="iteration_compare",
                    tone="accent",
                    emphasis="primary" if default_focus_panel == "iteration_compare" else "supporting",
                    default_open=True,
                    collapsible=True,
                ),
            )
        if has_authorship:
            presentations.insert(
                (
                    6
                    if has_decision_notes and has_artifact_lineage and has_rationale_snapshots and has_iteration_compare
                    else 5
                    if (
                        (has_decision_notes and has_artifact_lineage and has_rationale_snapshots)
                        or (has_iteration_compare and has_decision_notes and has_artifact_lineage)
                        or (has_iteration_compare and has_decision_notes and has_rationale_snapshots)
                        or (has_iteration_compare and has_artifact_lineage and has_rationale_snapshots)
                    )
                    else 4
                    if sum(
                        1
                        for item in (
                            has_decision_notes,
                            has_artifact_lineage,
                            has_rationale_snapshots,
                            has_iteration_compare,
                        )
                        if item
                    ) >= 2
                    else 3
                    if has_decision_notes or has_artifact_lineage or has_rationale_snapshots or has_iteration_compare
                    else 2
                ),
                VideoThreadPanelPresentation(
                    panel_id="authorship",
                    tone="subtle",
                    emphasis="supporting",
                    default_open=True,
                    collapsible=True,
                ),
            )
        if has_production_journal:
            presentations.append(
                VideoThreadPanelPresentation(
                    panel_id="production_journal",
                    tone="neutral",
                    emphasis="supporting",
                    default_open=True,
                    collapsible=True,
                )
            )
        if has_discussion_runtime:
            presentations.append(
                VideoThreadPanelPresentation(
                    panel_id="discussion_runtime",
                    tone="accent",
                    emphasis="primary" if default_focus_panel == "discussion_runtime" else "supporting",
                    default_open=True,
                    collapsible=True,
                )
            )
        if has_participant_runtime:
            presentations.append(
                VideoThreadPanelPresentation(
                    panel_id="participant_runtime",
                    tone="subtle",
                    emphasis="primary" if default_focus_panel == "participant_runtime" else "supporting",
                    default_open=True,
                    collapsible=True,
                )
            )
        if has_discussion_groups:
            presentations.append(
                VideoThreadPanelPresentation(
                    panel_id="discussion_groups",
                    tone="neutral",
                    emphasis="primary" if default_focus_panel == "discussion_groups" else "supporting",
                    default_open=True,
                    collapsible=True,
                )
            )
        if has_iteration_detail:
            presentations.append(
                VideoThreadPanelPresentation(
                    panel_id="iteration_detail",
                    tone="neutral",
                    emphasis="primary" if default_focus_panel == "iteration_detail" else "supporting",
                    default_open=True,
                    collapsible=True,
                )
            )
        presentations.append(
            VideoThreadPanelPresentation(
                panel_id="history",
                tone="neutral",
                emphasis="primary" if default_focus_panel == "history" else "supporting",
                default_open=history_has_cards,
                collapsible=True,
            )
        )
        return presentations

    @staticmethod
    def _build_decision_notes(
        *,
        current_iteration,
        current_result,
        current_result_selection_reason: str | None,
        latest_explanation: VideoThreadLatestExplanation,
    ) -> VideoThreadDecisionNotes:
        items: list[VideoThreadDecisionNote] = []
        if current_result_selection_reason:
            items.append(
                VideoThreadDecisionNote(
                    note_id=f"decision-selection-{None if current_result is None else current_result.result_id or 'current'}",
                    note_kind="selection_rationale",
                    title="Why this version is selected",
                    summary=current_result_selection_reason,
                    emphasis="primary",
                    source_iteration_id=None if current_iteration is None else current_iteration.iteration_id,
                    source_result_id=None if current_result is None else current_result.result_id,
                )
            )
        if latest_explanation.summary:
            items.append(
                VideoThreadDecisionNote(
                    note_id=f"decision-explanation-{latest_explanation.turn_id or 'latest'}",
                    note_kind="agent_explanation",
                    title=latest_explanation.title or "Latest visible explanation",
                    summary=latest_explanation.summary,
                    emphasis="supporting",
                    source_iteration_id=None if current_iteration is None else current_iteration.iteration_id,
                    source_turn_id=latest_explanation.turn_id,
                    source_result_id=None if current_result is None else current_result.result_id,
                    actor_display_name=latest_explanation.speaker_display_name,
                    actor_role=latest_explanation.speaker_role,
                )
            )
        if current_iteration is not None and current_iteration.goal.strip():
            items.append(
                VideoThreadDecisionNote(
                    note_id=f"decision-goal-{current_iteration.iteration_id}",
                    note_kind="iteration_goal",
                    title="Current iteration goal",
                    summary=current_iteration.goal,
                    emphasis="supporting",
                    source_iteration_id=current_iteration.iteration_id,
                    actor_display_name="Owner",
                    actor_role="owner",
                )
            )
        return VideoThreadDecisionNotes(items=items)

    @classmethod
    def _build_artifact_lineage(
        cls,
        *,
        participants: list[VideoThreadParticipant],
        iterations,
        results,
        turns,
        runs,
        selected_result_id: str | None,
        current_iteration_id: str | None,
        current_result_selection_reason: str | None,
        latest_explanation: VideoThreadLatestExplanation,
    ) -> VideoThreadArtifactLineage:
        result_by_id = {result.result_id: result for result in results}
        items: list[VideoThreadArtifactLineageItem] = []
        ordered_iterations = sorted(iterations, key=lambda item: (item.created_at, item.iteration_id))

        for iteration in ordered_iterations:
            to_result = cls._lineage_target_result(
                iteration=iteration,
                results=results,
                result_by_id=result_by_id,
            )
            if to_result is None and iteration.source_result_id is None:
                continue

            trigger_turn = cls._lineage_trigger_turn(turns=turns, iteration=iteration)
            latest_run = cls._latest_relevant_run(runs=runs, iteration_id=iteration.iteration_id)
            latest_agent_turn = cls._latest_relevant_agent_turn(
                turns=turns,
                iteration_id=iteration.iteration_id,
            )
            is_selected = to_result is not None and to_result.result_id == selected_result_id
            is_active = current_iteration_id == iteration.iteration_id and not is_selected
            status = "selected" if is_selected else "active" if is_active else "origin" if iteration.source_result_id is None else "superseded"
            emphasis = "primary" if is_selected else "supporting" if is_active else "context" if iteration.source_result_id is None else "supporting"

            actor_role = None
            actor_display_name = None
            if latest_run is not None:
                actor_role = latest_run.role
                actor_display_name = cls._resolve_participant_display_name(
                    participants=participants,
                    agent_id=latest_run.agent_id,
                    role=latest_run.role,
                )
            elif latest_agent_turn is not None:
                actor_role = latest_agent_turn.speaker_role
                actor_display_name = cls._resolve_participant_display_name(
                    participants=participants,
                    agent_id=latest_agent_turn.speaker_agent_id,
                    role=latest_agent_turn.speaker_role,
                )
            elif iteration.responsible_role or iteration.responsible_agent_id:
                actor_role = iteration.responsible_role
                actor_display_name = cls._resolve_participant_display_name(
                    participants=participants,
                    agent_id=iteration.responsible_agent_id,
                    role=iteration.responsible_role,
                )

            change_summary = ""
            if to_result is not None and to_result.result_summary.strip():
                change_summary = to_result.result_summary.strip()
            elif iteration.focus_summary and iteration.focus_summary.strip():
                change_summary = iteration.focus_summary.strip()
            else:
                change_summary = iteration.goal.strip()

            change_reason = ""
            if trigger_turn is not None and trigger_turn.summary.strip():
                change_reason = trigger_turn.summary.strip()
            elif is_selected and current_result_selection_reason:
                change_reason = current_result_selection_reason
            elif latest_agent_turn is not None and latest_agent_turn.summary.strip():
                change_reason = latest_agent_turn.summary.strip()
            elif latest_explanation.summary and current_iteration_id == iteration.iteration_id:
                change_reason = latest_explanation.summary

            items.append(
                VideoThreadArtifactLineageItem(
                    lineage_id=f"lineage-{iteration.iteration_id}",
                    iteration_id=iteration.iteration_id,
                    from_result_id=iteration.source_result_id,
                    to_result_id=None if to_result is None else to_result.result_id,
                    change_summary=change_summary,
                    change_reason=change_reason,
                    trigger_turn_id=None if trigger_turn is None else trigger_turn.turn_id,
                    trigger_label=cls._lineage_trigger_label(trigger_turn),
                    actor_display_name=actor_display_name,
                    actor_role=actor_role,
                    emphasis=emphasis,
                    status=status,
                )
            )

        return VideoThreadArtifactLineage(
            summary="How the current video evolved across visible revisions.",
            selected_result_id=selected_result_id,
            items=items,
        )

    @staticmethod
    def _lineage_target_result(*, iteration, results, result_by_id):
        if iteration.selected_result_id and iteration.selected_result_id in result_by_id:
            return result_by_id[iteration.selected_result_id]
        for result in reversed(results):
            if result.iteration_id == iteration.iteration_id:
                return result
        return None

    @staticmethod
    def _lineage_trigger_turn(*, turns, iteration):
        if iteration.initiated_by_turn_id:
            for turn in turns:
                if turn.turn_id == iteration.initiated_by_turn_id and turn.visibility == "product_safe":
                    return turn
        for turn in reversed(turns):
            if turn.iteration_id != iteration.iteration_id or turn.visibility != "product_safe":
                continue
            if turn.turn_type == "owner_request":
                return turn
        return None

    @staticmethod
    def _lineage_trigger_label(trigger_turn) -> str | None:
        if trigger_turn is None:
            return None
        if trigger_turn.intent_type == "generate":
            return "Owner started the thread"
        if trigger_turn.intent_type == "request_revision":
            return "Owner requested revision"
        if trigger_turn.intent_type == "request_explanation":
            return "Owner asked for explanation"
        if trigger_turn.intent_type == "discuss":
            return "Owner added note"
        return trigger_turn.title or "Visible trigger"

    @classmethod
    def _build_rationale_snapshots(
        cls,
        *,
        participants: list[VideoThreadParticipant],
        iterations,
        results,
        turns,
        runs,
        current_iteration_id: str | None,
        current_result_selection_reason: str | None,
    ) -> VideoThreadRationaleSnapshots:
        items: list[VideoThreadRationaleSnapshot] = []
        result_by_id = {result.result_id: result for result in results}
        ordered_iterations = sorted(iterations, key=lambda item: (item.created_at, item.iteration_id))

        for iteration in ordered_iterations:
            latest_explanation_turn = cls._latest_iteration_explanation_turn(
                turns=turns,
                iteration_id=iteration.iteration_id,
            )
            latest_owner_turn = cls._latest_iteration_owner_turn(
                turns=turns,
                iteration_id=iteration.iteration_id,
            )
            target_result = cls._lineage_target_result(
                iteration=iteration,
                results=results,
                result_by_id=result_by_id,
            )
            is_current = iteration.iteration_id == current_iteration_id

            snapshot_kind = "owner_goal"
            title = "Original direction" if iteration.parent_iteration_id is None else "Revision goal"
            summary = (
                latest_owner_turn.summary.strip()
                if latest_owner_turn is not None and latest_owner_turn.summary.strip()
                else latest_owner_turn.title.strip()
                if latest_owner_turn is not None and latest_owner_turn.title.strip()
                else iteration.goal.strip()
            )
            source_turn_id = None if latest_owner_turn is None else latest_owner_turn.turn_id
            source_result_id = None if target_result is None else target_result.result_id
            actor_display_name = "Owner"
            actor_role = "owner"

            if is_current and current_result_selection_reason and target_result is not None:
                snapshot_kind = "selection_rationale"
                title = "Why the current revision is selected"
                summary = current_result_selection_reason
                source_turn_id = None
                source_result_id = None if target_result is None else target_result.result_id
                actor_role = cls._current_result_author_role(
                    current_iteration=iteration,
                    runs=runs,
                    turns=turns,
                )
                actor_display_name = cls._current_result_author_display_name(
                    participants=participants,
                    current_iteration=iteration,
                    runs=runs,
                    turns=turns,
                )
            elif latest_explanation_turn is not None and latest_explanation_turn.summary.strip():
                snapshot_kind = "agent_explanation"
                title = latest_explanation_turn.title or "Visible rationale"
                summary = latest_explanation_turn.summary.strip()
                source_turn_id = latest_explanation_turn.turn_id
                source_result_id = latest_explanation_turn.related_result_id or (
                    None if target_result is None else target_result.result_id
                )
                actor_display_name = cls._resolve_participant_display_name(
                    participants=participants,
                    agent_id=latest_explanation_turn.speaker_agent_id,
                    role=latest_explanation_turn.speaker_role,
                )
                actor_role = latest_explanation_turn.speaker_role

            items.append(
                VideoThreadRationaleSnapshot(
                    snapshot_id=f"snapshot-{iteration.iteration_id}",
                    iteration_id=iteration.iteration_id,
                    snapshot_kind=snapshot_kind,
                    title=title,
                    summary=summary,
                    source_turn_id=source_turn_id,
                    source_result_id=source_result_id,
                    actor_display_name=actor_display_name,
                    actor_role=actor_role,
                    emphasis="primary" if is_current else "context",
                    status="current" if is_current else "archived",
                )
            )

        return VideoThreadRationaleSnapshots(
            summary="Canonical product-safe why notes across iterations.",
            current_iteration_id=current_iteration_id,
            items=items,
        )

    @staticmethod
    def _latest_iteration_explanation_turn(*, turns, iteration_id: str):
        for turn in reversed(turns):
            if (
                turn.iteration_id == iteration_id
                and turn.visibility == "product_safe"
                and turn.turn_type == "agent_explanation"
            ):
                return turn
        return None

    @staticmethod
    def _latest_iteration_owner_turn(*, turns, iteration_id: str):
        for turn in reversed(turns):
            if (
                turn.iteration_id == iteration_id
                and turn.visibility == "product_safe"
                and turn.turn_type == "owner_request"
            ):
                return turn
        return None

    @classmethod
    def _build_iteration_compare(
        cls,
        *,
        participants: list[VideoThreadParticipant],
        iterations,
        results,
        turns,
        runs,
        current_iteration,
        current_result,
        current_result_selection_reason: str | None,
        latest_explanation: VideoThreadLatestExplanation,
    ) -> VideoThreadIterationCompare:
        if current_iteration is None:
            return VideoThreadIterationCompare(
                summary="No iteration is selected yet.",
            )

        ordered_iterations = sorted(iterations, key=lambda item: (item.created_at, item.iteration_id))
        current_index = next(
            (
                index
                for index, iteration in enumerate(ordered_iterations)
                if iteration.iteration_id == current_iteration.iteration_id
            ),
            None,
        )
        previous_iteration = (
            ordered_iterations[current_index - 1]
            if current_index is not None and current_index > 0
            else None
        )
        previous_result = (
            None if previous_iteration is None else cls._target_result_for_iteration(iteration=previous_iteration, results=results)
        )
        current_target_result = current_result or cls._target_result_for_iteration(iteration=current_iteration, results=results)

        continuity_status, continuity_summary = cls._build_iteration_continuity(
            participants=participants,
            previous_iteration=previous_iteration,
            current_iteration=current_iteration,
            turns=turns,
            runs=runs,
        )
        if previous_iteration is None:
            return VideoThreadIterationCompare(
                summary="Compare the current selected cut against the nearest earlier visible iteration.",
                previous_iteration_id=None,
                current_iteration_id=current_iteration.iteration_id,
                previous_result_id=None,
                current_result_id=None if current_target_result is None else current_target_result.result_id,
                change_summary="" if current_target_result is None else current_target_result.result_summary,
                rationale_shift_summary=(
                    current_iteration.goal
                    or current_result_selection_reason
                    or latest_explanation.summary
                ),
                continuity_status=continuity_status,
                continuity_summary=continuity_summary,
            )

        previous_rationale = cls._iteration_rationale_summary(
            iteration=previous_iteration,
            target_result=previous_result,
            turns=turns,
        )
        current_rationale = (
            current_iteration.goal
            or current_result_selection_reason
            or latest_explanation.summary
            or cls._iteration_rationale_summary(
                iteration=current_iteration,
                target_result=current_target_result,
                turns=turns,
            )
        )
        return VideoThreadIterationCompare(
            summary="Compare the current selected cut against the nearest earlier visible iteration.",
            previous_iteration_id=previous_iteration.iteration_id,
            current_iteration_id=current_iteration.iteration_id,
            previous_result_id=None if previous_result is None else previous_result.result_id,
            current_result_id=None if current_target_result is None else current_target_result.result_id,
            change_summary="" if current_target_result is None else current_target_result.result_summary,
            rationale_shift_summary=(
                f"The previous cut focused on {previous_rationale}. "
                f"The current revision shifts toward {current_rationale}."
            ),
            continuity_status=continuity_status,
            continuity_summary=continuity_summary,
        )

    @classmethod
    def _build_iteration_continuity(
        cls,
        *,
        participants: list[VideoThreadParticipant],
        previous_iteration,
        current_iteration,
        turns,
        runs,
    ) -> tuple[str, str]:
        if previous_iteration is None:
            return "new", "This is the first visible iteration in the thread, so there is no earlier participant continuity to preserve."
        previous_identity = cls._iteration_participant_identity(
            participants=participants,
            iteration=previous_iteration,
            turns=turns,
            runs=runs,
        )
        current_identity = cls._iteration_participant_identity(
            participants=participants,
            iteration=current_iteration,
            turns=turns,
            runs=runs,
        )
        previous_label = previous_identity["display_name"] or previous_identity["role"] or "the previous owner-safe context"
        current_label = current_identity["display_name"] or current_identity["role"] or "the current owner-safe context"
        if (
            previous_identity["agent_id"] is not None
            and current_identity["agent_id"] is not None
            and previous_identity["agent_id"] == current_identity["agent_id"]
        ):
            return "preserved", f"Participant continuity stays with {current_label} across the compared iterations."
        if (
            previous_identity["agent_id"] is None
            and current_identity["agent_id"] is None
            and previous_identity["role"] is not None
            and previous_identity["role"] == current_identity["role"]
        ):
            return "preserved", f"Role continuity stays with {current_label} across the compared iterations."
        if previous_label == current_label:
            return "preserved", f"Participant continuity stays with {current_label} across the compared iterations."
        if previous_identity["agent_id"] is None and current_identity["agent_id"] is None and previous_identity["role"] is None and current_identity["role"] is None:
            return "unknown", "The compared iterations do not expose enough participant continuity to make a stable comparison."
        return "changed", f"Participant continuity changed from {previous_label} to {current_label} between the compared iterations."

    @classmethod
    def _iteration_participant_identity(
        cls,
        *,
        participants: list[VideoThreadParticipant],
        iteration,
        turns,
        runs,
    ) -> dict[str, str | None]:
        latest_run = next((run for run in reversed(runs) if run.iteration_id == iteration.iteration_id), None)
        if latest_run is not None:
            return {
                "agent_id": latest_run.agent_id,
                "role": latest_run.role,
                "display_name": cls._resolve_participant_display_name(
                    participants=participants,
                    agent_id=latest_run.agent_id,
                    role=latest_run.role,
                ),
            }
        latest_agent_turn = cls._latest_relevant_agent_turn(turns=turns, iteration_id=iteration.iteration_id)
        if latest_agent_turn is not None:
            return {
                "agent_id": latest_agent_turn.speaker_agent_id,
                "role": latest_agent_turn.speaker_role,
                "display_name": cls._resolve_participant_display_name(
                    participants=participants,
                    agent_id=latest_agent_turn.speaker_agent_id,
                    role=latest_agent_turn.speaker_role,
                ),
            }
        latest_owner_turn = cls._latest_iteration_owner_turn(turns=turns, iteration_id=iteration.iteration_id)
        if latest_owner_turn is not None and (
            latest_owner_turn.addressed_agent_id is not None or latest_owner_turn.addressed_participant_id is not None
        ):
            participant = next(
                (
                    item
                    for item in participants
                    if item.participant_id == latest_owner_turn.addressed_participant_id
                    or item.agent_id == latest_owner_turn.addressed_agent_id
                ),
                None,
            )
            return {
                "agent_id": latest_owner_turn.addressed_agent_id or (None if participant is None else participant.agent_id),
                "role": None if participant is None else participant.role,
                "display_name": None if participant is None else participant.display_name,
            }
        return {
            "agent_id": iteration.responsible_agent_id,
            "role": iteration.responsible_role,
            "display_name": cls._resolve_participant_display_name(
                participants=participants,
                agent_id=iteration.responsible_agent_id,
                role=iteration.responsible_role,
            ),
        }

    @staticmethod
    def _iteration_rationale_summary(*, iteration, target_result, turns) -> str:
        latest_owner_turn = VideoProjectionService._latest_iteration_owner_turn(
            turns=turns,
            iteration_id=iteration.iteration_id,
        )
        if latest_owner_turn is not None and latest_owner_turn.summary.strip():
            return latest_owner_turn.summary.strip()
        if latest_owner_turn is not None and latest_owner_turn.title.strip():
            return latest_owner_turn.title.strip()
        if target_result is not None and target_result.result_summary.strip():
            return target_result.result_summary.strip()
        return iteration.goal.strip()

    @classmethod
    def _build_production_journal(
        cls,
        *,
        participants: list[VideoThreadParticipant],
        iterations,
        runs,
        results,
        selected_result_id: str | None,
    ) -> VideoThreadProductionJournal:
        journal_entries: list[VideoThreadProductionJournalEntry] = []
        ordered_iterations = sorted(iterations, key=lambda item: (item.created_at, item.iteration_id))
        ordered_runs = sorted(
            runs,
            key=lambda item: (
                item.started_at or item.created_at,
                item.created_at,
                item.run_id,
            ),
        )
        ordered_results = sorted(results, key=lambda item: (item.created_at, item.result_id))

        for iteration in ordered_iterations:
            stage = cls._iteration_stage(iteration.requested_action)
            journal_entries.append(
                VideoThreadProductionJournalEntry(
                    entry_id=f"journal-iteration-{iteration.iteration_id}",
                    entry_kind="iteration",
                    title=cls._iteration_entry_title(iteration.requested_action),
                    summary=iteration.goal,
                    stage=stage,
                    status=iteration.status,
                    iteration_id=iteration.iteration_id,
                    actor_display_name="Owner",
                    actor_role="owner",
                    created_at=iteration.created_at,
                )
            )

        for run in ordered_runs:
            actor_display_name = cls._resolve_participant_display_name(
                participants=participants,
                agent_id=run.agent_id,
                role=run.role,
            )
            journal_entries.append(
                VideoThreadProductionJournalEntry(
                    entry_id=f"journal-run-{run.run_id}",
                    entry_kind="run",
                    title=f"{actor_display_name or 'Agent'} is {run.phase or run.status}",
                    summary=run.output_summary or "A visible agent run is attached to this iteration.",
                    stage="execution",
                    status=run.status,
                    iteration_id=run.iteration_id,
                    task_id=run.task_id,
                    run_id=run.run_id,
                    actor_display_name=actor_display_name,
                    actor_role=run.role,
                    created_at=run.ended_at or run.started_at or run.created_at,
                )
            )

        for result in ordered_results:
            resource_refs = cls._result_resource_refs(result)
            is_selected = result.selected or result.result_id == selected_result_id
            journal_entries.append(
                VideoThreadProductionJournalEntry(
                    entry_id=f"journal-result-{result.result_id}",
                    entry_kind="result",
                    title="Selected result recorded" if is_selected else "Result candidate recorded",
                    summary=result.result_summary,
                    stage="result",
                    status=result.status,
                    iteration_id=result.iteration_id,
                    task_id=result.source_task_id,
                    result_id=result.result_id,
                    actor_display_name=None,
                    actor_role=None,
                    resource_refs=resource_refs,
                    created_at=result.created_at,
                )
            )

        ordered_entries = sorted(
            journal_entries,
            key=lambda item: (
                VideoProjectionService._production_journal_kind_rank(item.entry_kind),
                "" if item.created_at is None else item.created_at.isoformat(),
                item.entry_id,
            ),
        )
        summary = ""
        if ordered_entries:
            summary = (
                f"{len(ordered_entries)} visible production entries across "
                f"{len(ordered_iterations)} iteration(s), {len(ordered_runs)} run(s), and {len(ordered_results)} result(s)."
            )
        return VideoThreadProductionJournal(
            summary=summary,
            entries=ordered_entries,
        )

    @staticmethod
    def _iteration_stage(requested_action: str | None) -> str:
        if requested_action == "revise":
            return "revision"
        if requested_action == "generate":
            return "generation"
        return "discussion"

    @classmethod
    def _iteration_entry_title(cls, requested_action: str | None) -> str:
        stage = cls._iteration_stage(requested_action)
        if stage == "revision":
            return "Revision iteration opened"
        if stage == "generation":
            return "Generation iteration opened"
        return "Discussion iteration opened"

    @staticmethod
    def _result_resource_refs(result) -> list[str]:
        refs: list[str] = []
        if result.video_resource:
            refs.append(result.video_resource)
        refs.extend(result.preview_resources)
        if result.script_resource:
            refs.append(result.script_resource)
        if result.validation_report_resource:
            refs.append(result.validation_report_resource)
        return refs

    @staticmethod
    def _production_journal_kind_rank(entry_kind: str) -> int:
        if entry_kind == "iteration":
            return 0
        if entry_kind == "run":
            return 1
        return 2

    @classmethod
    def _build_authorship(
        cls,
        *,
        participants: list[VideoThreadParticipant],
        current_iteration,
        current_result,
        turns,
        runs,
    ) -> VideoThreadAuthorship:
        source_run = cls._latest_relevant_run(runs=runs, iteration_id=None if current_iteration is None else current_iteration.iteration_id)
        source_turn = cls._latest_relevant_agent_turn(
            turns=turns,
            iteration_id=None if current_iteration is None else current_iteration.iteration_id,
        )
        primary_agent_display_name = None
        primary_agent_role = None
        source_iteration_id = None
        source_run_id = None
        source_turn_id = None

        if source_run is not None:
            primary_agent_display_name = cls._resolve_participant_display_name(
                participants=participants,
                agent_id=source_run.agent_id,
                role=source_run.role,
            )
            primary_agent_role = source_run.role
            source_iteration_id = source_run.iteration_id
            source_run_id = source_run.run_id
        elif source_turn is not None:
            primary_agent_display_name = cls._resolve_participant_display_name(
                participants=participants,
                agent_id=source_turn.speaker_agent_id,
                role=source_turn.speaker_role,
            )
            primary_agent_role = source_turn.speaker_role
            source_iteration_id = source_turn.iteration_id
            source_turn_id = source_turn.turn_id
        elif current_iteration is not None:
            primary_agent_display_name = cls._resolve_participant_display_name(
                participants=participants,
                agent_id=current_iteration.responsible_agent_id,
                role=current_iteration.responsible_role,
            )
            primary_agent_role = current_iteration.responsible_role
            source_iteration_id = current_iteration.iteration_id

        summary = ""
        if primary_agent_display_name or primary_agent_role:
            actor_label = primary_agent_display_name or primary_agent_role or "The active agent"
            if current_result is not None:
                summary = (
                    f"{actor_label} is the latest visible agent shaping the selected cut for this iteration."
                )
            elif current_iteration is not None:
                summary = f"{actor_label} is the latest visible agent shaping the active iteration."
            else:
                summary = f"{actor_label} is the latest visible agent in this collaboration thread."

        return VideoThreadAuthorship(
            summary=summary,
            primary_agent_display_name=primary_agent_display_name,
            primary_agent_role=primary_agent_role,
            source_iteration_id=source_iteration_id,
            source_run_id=source_run_id,
            source_turn_id=source_turn_id,
        )

    @classmethod
    def _build_latest_explanation(
        cls,
        *,
        participants: list[VideoThreadParticipant],
        current_iteration,
        turns,
        runs,
    ) -> VideoThreadLatestExplanation:
        for turn in reversed(turns):
            if turn.visibility != "product_safe" or turn.turn_type != "agent_explanation":
                continue
            return VideoThreadLatestExplanation(
                title=turn.title or "Latest visible explanation",
                summary=turn.summary,
                turn_id=turn.turn_id,
                speaker_display_name=cls._resolve_participant_display_name(
                    participants=participants,
                    agent_id=turn.speaker_agent_id,
                    role=turn.speaker_role,
                ),
                speaker_role=turn.speaker_role,
            )
        latest_run = runs[-1] if runs else None
        if latest_run is not None and latest_run.output_summary:
            return VideoThreadLatestExplanation(
                title="Latest visible explanation",
                summary=latest_run.output_summary,
                speaker_display_name=cls._resolve_participant_display_name(
                    participants=participants,
                    agent_id=latest_run.agent_id,
                    role=latest_run.role,
                ),
                speaker_role=latest_run.role,
            )
        if current_iteration is not None and current_iteration.goal:
            return VideoThreadLatestExplanation(
                title="Latest visible explanation",
                summary=f"The active iteration is currently focused on '{current_iteration.goal}'.",
                speaker_display_name=cls._resolve_participant_display_name(
                    participants=participants,
                    agent_id=current_iteration.responsible_agent_id,
                    role=current_iteration.responsible_role,
                ),
                speaker_role=current_iteration.responsible_role,
            )
        return VideoThreadLatestExplanation()

    @classmethod
    def _build_discussion_groups(
        cls,
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
                    speaker_display_name=cls._resolve_participant_display_name(
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
                    prompt_actor_display_name=cls._resolve_participant_display_name(
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

    @classmethod
    def _build_discussion_runtime(
        cls,
        *,
        current_iteration,
        current_result,
        discussion_groups: VideoThreadDiscussionGroups,
        composer: VideoThreadComposer,
        iteration_detail: VideoThreadIterationDetailSummary,
        latest_explanation: VideoThreadLatestExplanation,
    ) -> VideoThreadDiscussionRuntime:
        active_group = cls._select_active_discussion_group(
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

    @staticmethod
    def _select_active_discussion_group(
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

    @classmethod
    def _build_participant_runtime(
        cls,
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
                display_name=cls._display_name_for_turn(turn=turn, participants=participants),
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

    @staticmethod
    def _build_next_recommended_move(
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

    @classmethod
    def _build_history(
        cls,
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
                    title=f"{cls._resolve_participant_display_name(participants=participants, agent_id=latest_run.agent_id, role=latest_run.role) or 'Agent'} is working on this",
                    summary=latest_run.output_summary,
                    iteration_id=latest_run.iteration_id,
                    intent_type=cls._resolve_iteration_intent_type(
                        current_iteration=current_iteration,
                        turns=turns,
                        iteration_id=latest_run.iteration_id,
                    ),
                    actor_display_name=cls._resolve_participant_display_name(
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
                    iteration_id=cls._iteration_id_for_turn(turns, latest_explanation.turn_id),
                    intent_type="request_explanation",
                    reply_to_turn_id=cls._reply_to_turn_id_for_turn(turns, latest_explanation.turn_id),
                    related_result_id=cls._related_result_id_for_turn(turns, latest_explanation.turn_id),
                    actor_display_name=latest_explanation.speaker_display_name,
                    actor_role=latest_explanation.speaker_role,
                    emphasis="primary",
                )
            )

        if current_result_selection_reason and (current_result is not None or latest_run is not None):
            actor_role = cls._current_result_author_role(
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
                    intent_type=cls._resolve_iteration_intent_type(
                        current_iteration=current_iteration,
                        turns=turns,
                        iteration_id=None if current_iteration is None else current_iteration.iteration_id,
                    ),
                    related_result_id=None if current_result is None else current_result.result_id,
                    actor_display_name=cls._current_result_author_display_name(
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
                    actor_display_name=cls._resolve_participant_display_name(
                        participants=participants,
                        agent_id=latest_owner_turn.speaker_agent_id,
                        role=latest_owner_turn.speaker_role or "owner",
                    )
                    or "Owner",
                    actor_role=latest_owner_turn.speaker_role or "owner",
                    emphasis="context",
                )
            )

        return VideoThreadHistory(cards=cls._dedupe_history_cards(cards))

    @staticmethod
    def _dedupe_history_cards(cards: list[VideoThreadHistoryCard]) -> list[VideoThreadHistoryCard]:
        deduped: list[VideoThreadHistoryCard] = []
        seen: set[tuple[str, str]] = set()
        for card in cards:
            key = (card.card_type, card.summary.strip())
            if not card.summary.strip() or key in seen:
                continue
            deduped.append(card)
            seen.add(key)
        return deduped

    @staticmethod
    def _iteration_id_for_turn(turns, turn_id: str) -> str | None:
        for turn in turns:
            if turn.turn_id == turn_id:
                return turn.iteration_id
        return None

    @staticmethod
    def _reply_to_turn_id_for_turn(turns, turn_id: str) -> str | None:
        for turn in turns:
            if turn.turn_id == turn_id:
                return turn.reply_to_turn_id
        return None

    @staticmethod
    def _related_result_id_for_turn(turns, turn_id: str) -> str | None:
        for turn in turns:
            if turn.turn_id == turn_id:
                return turn.related_result_id
        return None

    @staticmethod
    def _latest_relevant_run(*, runs, iteration_id: str | None):
        if iteration_id is not None:
            for run in reversed(runs):
                if run.iteration_id == iteration_id:
                    return run
        return runs[-1] if runs else None

    @staticmethod
    def _latest_relevant_agent_turn(*, turns, iteration_id: str | None):
        for turn in reversed(turns):
            if turn.visibility != "product_safe" or turn.speaker_type != "agent":
                continue
            if iteration_id is None or turn.iteration_id == iteration_id:
                return turn
        return None

    @staticmethod
    def _resolve_iteration_intent_type(*, current_iteration, turns, iteration_id: str | None) -> str | None:
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

    @staticmethod
    def _resolve_participant_display_name(
        *,
        participants: list[VideoThreadParticipant],
        agent_id: str | None,
        role: str | None,
    ) -> str | None:
        if agent_id:
            for participant in participants:
                if participant.agent_id == agent_id:
                    return participant.display_name
        if role:
            return role.replace("_", " ").strip().title() or "Agent"
        return None

    @staticmethod
    def _current_result_author_role(*, current_iteration, runs, turns) -> str | None:
        latest_run = runs[-1] if runs else None
        if latest_run is not None:
            return latest_run.role
        for turn in reversed(turns):
            if turn.speaker_type == "agent" and turn.speaker_role:
                return turn.speaker_role
        if current_iteration is not None:
            return current_iteration.responsible_role
        return None

    @classmethod
    def _current_result_author_display_name(
        cls,
        *,
        participants: list[VideoThreadParticipant],
        current_iteration,
        runs,
        turns,
    ) -> str | None:
        latest_run = runs[-1] if runs else None
        if latest_run is not None:
            for participant in participants:
                if participant.agent_id == latest_run.agent_id:
                    return participant.display_name
            return latest_run.role.replace("_", " ").strip().title() or "Agent"
        for turn in reversed(turns):
            if turn.speaker_type == "agent":
                if turn.speaker_agent_id:
                    for participant in participants:
                        if participant.agent_id == turn.speaker_agent_id:
                            return participant.display_name
                if turn.speaker_role:
                    return turn.speaker_role.replace("_", " ").strip().title() or "Agent"
        if current_iteration is not None and current_iteration.responsible_agent_id:
            for participant in participants:
                if participant.agent_id == current_iteration.responsible_agent_id:
                    return participant.display_name
        if current_iteration is not None and current_iteration.responsible_role:
            return current_iteration.responsible_role.replace("_", " ").strip().title() or "Agent"
        return None

    @staticmethod
    def _current_result_selection_reason(
        *,
        current_iteration,
        current_result,
        runs,
    ) -> str | None:
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
