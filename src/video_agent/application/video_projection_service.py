from __future__ import annotations

from video_agent.application.video_projection_collaboration_runtime import (
    build_discussion_groups,
    build_discussion_runtime,
    build_participant_runtime,
)
from video_agent.application.video_projection_iteration_story import (
    build_iteration_compare,
    build_rationale_snapshots,
    current_result_author_display_name as resolve_current_result_author_display_name,
    current_result_author_role as resolve_current_result_author_role,
)
from video_agent.application.video_projection_iteration_detail import (
    build_iteration_detail,
    build_iteration_detail_summary,
)
from video_agent.application.video_projection_thread_context import (
    build_actions,
    build_composer,
    build_participant_management,
    build_responsibility,
    resolve_participants,
)
from video_agent.application.video_projection_history import (
    build_history,
    build_next_recommended_move,
    current_result_selection_reason,
)
from video_agent.application.video_projection_explainability import (
    build_artifact_lineage,
    build_authorship,
    build_decision_notes,
    build_latest_explanation,
)
from video_agent.application.video_projection_production_journal import build_production_journal
from video_agent.application.video_projection_render_contract import build_render_contract
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.video_thread_models import (
    VideoThreadConversation,
    VideoThreadConversationTurn,
    VideoThreadCurrentFocus,
    VideoThreadHeader,
    VideoThreadIterationCard,
    VideoThreadIterationWorkbench,
    VideoThreadParticipantsSection,
    VideoThreadProcess,
    VideoThreadProcessRun,
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
        participants = resolve_participants(
            store_participants=self.store.list_video_thread_participants(thread.thread_id),
            thread=thread,
        )

        current_iteration = next(
            (item for item in iterations if item.iteration_id == thread.current_iteration_id),
            iterations[-1] if iterations else None,
        )
        current_result = next(
            (item for item in results if item.result_id == thread.selected_result_id),
            results[-1] if results else None,
        )
        responsibility = build_responsibility(
            current_iteration=current_iteration,
            current_result=current_result,
            runs=runs,
        )
        actions = build_actions(
            current_iteration=current_iteration,
            current_result=current_result,
        )
        composer = build_composer(
            participants=participants,
            current_iteration=current_iteration,
            current_result=current_result,
            runs=runs,
            results=results,
            turns=turns,
        )
        current_result_author_display_name = resolve_current_result_author_display_name(
            participants=participants,
            current_iteration=current_iteration,
            runs=runs,
            turns=turns,
        )
        current_result_author_role = resolve_current_result_author_role(
            current_iteration=current_iteration,
            runs=runs,
            turns=turns,
        )
        current_result_selection_reason_value = current_result_selection_reason(
            current_iteration=current_iteration,
            current_result=current_result,
            runs=runs,
        )
        latest_explanation = build_latest_explanation(
            participants=participants,
            current_iteration=current_iteration,
            turns=turns,
            runs=runs,
        )
        decision_notes = build_decision_notes(
            current_iteration=current_iteration,
            current_result=current_result,
            current_result_selection_reason=current_result_selection_reason_value,
            latest_explanation=latest_explanation,
        )
        artifact_lineage = build_artifact_lineage(
            participants=participants,
            iterations=iterations,
            results=results,
            turns=turns,
            runs=runs,
            selected_result_id=thread.selected_result_id,
            current_iteration_id=None if current_iteration is None else current_iteration.iteration_id,
            current_result_selection_reason=current_result_selection_reason_value,
            latest_explanation=latest_explanation,
        )
        rationale_snapshots = build_rationale_snapshots(
            participants=participants,
            iterations=iterations,
            results=results,
            turns=turns,
            runs=runs,
            current_iteration_id=None if current_iteration is None else current_iteration.iteration_id,
            current_result_selection_reason=current_result_selection_reason_value,
        )
        iteration_compare = build_iteration_compare(
            participants=participants,
            iterations=iterations,
            results=results,
            turns=turns,
            runs=runs,
            current_iteration=current_iteration,
            current_result=current_result,
            current_result_selection_reason=current_result_selection_reason_value,
            latest_explanation=latest_explanation,
        )
        production_journal = build_production_journal(
            participants=participants,
            iterations=iterations,
            runs=runs,
            results=results,
            selected_result_id=thread.selected_result_id,
        )
        authorship = build_authorship(
            participants=participants,
            current_iteration=current_iteration,
            current_result=current_result,
            turns=turns,
            runs=runs,
        )
        history = build_history(
            participants=participants,
            turns=turns,
            runs=runs,
            latest_explanation=latest_explanation,
            current_iteration=current_iteration,
            current_result=current_result,
            current_result_selection_reason=current_result_selection_reason_value,
        )
        next_recommended_move = build_next_recommended_move(
            responsibility=responsibility,
            actions=actions,
            current_iteration=current_iteration,
            current_result=current_result,
        )
        discussion_groups = build_discussion_groups(
            participants=participants,
            turns=turns,
        )
        iteration_detail = build_iteration_detail_summary(
            thread_id=thread.thread_id,
            selected_iteration=current_iteration,
            participants=participants,
            turns=turns,
            runs=runs,
            results=results,
        )
        discussion_runtime = build_discussion_runtime(
            current_iteration=current_iteration,
            current_result=current_result,
            discussion_groups=discussion_groups,
            composer=composer,
            iteration_detail=iteration_detail,
            latest_explanation=latest_explanation,
        )
        participant_runtime = build_participant_runtime(
            current_iteration=current_iteration,
            participants=participants,
            turns=turns,
            runs=runs,
            composer=composer,
            responsibility=responsibility,
        )
        render_contract = build_render_contract(
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
                current_result_selection_reason=current_result_selection_reason_value,
            ),
            selection_summary=VideoThreadSelectionSummary(
                summary=current_result_selection_reason_value or "",
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
                management=build_participant_management(
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
        participants = resolve_participants(
            store_participants=self.store.list_video_thread_participants(thread.thread_id),
            thread=thread,
        )
        detail = build_iteration_detail(
            thread_id=thread_id,
            iteration=iteration,
            participants=participants,
            turns=self.store.list_video_turns(thread_id),
            runs=self.store.list_video_agent_runs(thread_id),
            results=self.store.list_video_results(thread_id),
        )
        return detail.model_dump(mode="json")
