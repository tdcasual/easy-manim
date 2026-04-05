from __future__ import annotations

from video_agent.application.video_projection_iteration_story import resolve_participant_display_name
from video_agent.domain.video_thread_models import (
    VideoThreadParticipant,
    VideoThreadProductionJournal,
    VideoThreadProductionJournalEntry,
)


def build_production_journal(
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
        stage = iteration_stage(iteration.requested_action)
        journal_entries.append(
            VideoThreadProductionJournalEntry(
                entry_id=f"journal-iteration-{iteration.iteration_id}",
                entry_kind="iteration",
                title=iteration_entry_title(iteration.requested_action),
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
        actor_display_name = resolve_participant_display_name(
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
        resource_refs = result_resource_refs(result)
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
            production_journal_kind_rank(item.entry_kind),
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


def iteration_stage(requested_action: str | None) -> str:
    if requested_action == "revise":
        return "revision"
    if requested_action == "generate":
        return "generation"
    return "discussion"


def iteration_entry_title(requested_action: str | None) -> str:
    stage = iteration_stage(requested_action)
    if stage == "revision":
        return "Revision iteration opened"
    if stage == "generation":
        return "Generation iteration opened"
    return "Discussion iteration opened"


def result_resource_refs(result) -> list[str]:
    refs: list[str] = []
    if result.video_resource:
        refs.append(result.video_resource)
    refs.extend(result.preview_resources)
    if result.script_resource:
        refs.append(result.script_resource)
    if result.validation_report_resource:
        refs.append(result.validation_report_resource)
    return refs


def production_journal_kind_rank(entry_kind: str) -> int:
    if entry_kind == "iteration":
        return 0
    if entry_kind == "run":
        return 1
    return 2
