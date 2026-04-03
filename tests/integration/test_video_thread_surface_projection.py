from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from tests.support import bootstrapped_settings


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


def test_video_thread_surface_projection_tracks_focus_conversation_and_process(tmp_path: Path) -> None:
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
    app_context.video_thread_service.select_result(
        created.thread.thread_id,
        origin_result.result_id,
    )
    revised = app_context.video_thread_service.request_revision(
        thread_id=created.thread.thread_id,
        base_task_id=created.created_task.task_id if created.created_task is not None else "",
        summary="Slow the opener and make the title entrance more deliberate.",
        preserve_working_parts=True,
    )
    run = app_context.video_run_binding_service.attach_run(
        thread_id=created.thread.thread_id,
        iteration_id=revised.iteration.iteration_id,
        agent_id="repairer-1",
        role="repairer",
        task_id=revised.created_task.task_id if revised.created_task is not None else None,
    )
    app_context.video_run_binding_service.mark_run_status(
        run.run_id,
        status="running",
        phase="repairing",
        output_summary="Applying a more deliberate title motion.",
    )
    revised_result = app_context.video_iteration_service.register_result(
        thread_id=created.thread.thread_id,
        iteration_id=revised.iteration.iteration_id,
        source_task_id=revised.created_task.task_id if revised.created_task is not None else "task-revised",
        status="ready",
        result_summary="Selected cut with a slower title entrance.",
    )
    app_context.video_thread_service.select_result(
        created.thread.thread_id,
        revised_result.result_id,
    )

    surface = app_context.video_projection_service.build_surface(
        created.thread.thread_id,
        viewer_agent_id="owner",
    )
    intruder_surface = app_context.video_projection_service.build_surface(
        created.thread.thread_id,
        viewer_agent_id="reviewer-1",
    )

    assert surface.thread_header.thread_id == created.thread.thread_id
    assert surface.current_focus.current_iteration_id == revised.iteration.iteration_id
    assert surface.current_focus.current_result_author_role == "repairer"
    assert surface.current_focus.current_result_selection_reason
    assert surface.selection_summary.summary == surface.current_focus.current_result_selection_reason
    assert surface.latest_explanation.summary == "Applying a more deliberate title motion."
    assert surface.authorship.primary_agent_display_name == "Repairer"
    assert surface.authorship.primary_agent_role == "repairer"
    assert surface.authorship.source_run_id == run.run_id
    assert surface.decision_notes.title == "Decision Notes"
    assert [item.note_kind for item in surface.decision_notes.items] == [
        "selection_rationale",
        "agent_explanation",
        "iteration_goal",
    ]
    assert surface.artifact_lineage.title == "Artifact Lineage"
    assert surface.artifact_lineage.selected_result_id == revised_result.result_id
    assert [item.from_result_id for item in surface.artifact_lineage.items] == [
        None,
        origin_result.result_id,
    ]
    assert [item.to_result_id for item in surface.artifact_lineage.items] == [
        origin_result.result_id,
        revised_result.result_id,
    ]
    assert surface.artifact_lineage.items[1].status == "selected"
    assert surface.artifact_lineage.items[1].trigger_label == "Owner requested revision"
    assert surface.rationale_snapshots.title == "Rationale Snapshots"
    assert surface.rationale_snapshots.current_iteration_id == revised.iteration.iteration_id
    assert [item.snapshot_kind for item in surface.rationale_snapshots.items] == [
        "owner_goal",
        "selection_rationale",
    ]
    assert surface.rationale_snapshots.items[1].status == "current"
    assert surface.production_journal.title == "Production Journal"
    assert [item.entry_kind for item in surface.production_journal.entries] == [
        "iteration",
        "iteration",
        "run",
        "result",
        "result",
    ]
    assert any(
        item.entry_kind == "run" and item.actor_role == "repairer"
        for item in surface.production_journal.entries
    )
    assert surface.discussion_groups.groups[0].status == "open"
    assert surface.discussion_groups.groups[0].prompt_intent_type == "request_revision"
    assert [item.card_type for item in surface.history.cards] == [
        "process_update",
        "result_selection",
        "owner_request",
    ]
    assert surface.history.cards[0].summary == "Applying a more deliberate title motion."
    assert surface.history.cards[0].intent_type == "request_revision"
    assert surface.history.cards[2].actor_role == "owner"
    assert surface.history.cards[2].intent_type == "request_revision"
    assert surface.next_recommended_move.recommended_action_id == "request_revision"
    assert surface.next_recommended_move.owner_action_required == "review_latest_result"
    assert surface.iteration_workbench.latest_iteration_id == revised.iteration.iteration_id
    assert surface.conversation.turns[-1].title == "Slow the opener and make the title entrance more deliberate."
    assert surface.process.runs[-1].task_id == revised.created_task.task_id
    assert [item.role for item in surface.participants.items] == ["owner", "repairer"]
    assert surface.participants.management.can_manage is True
    assert surface.participants.management.can_invite is True
    assert surface.participants.management.can_remove is True
    assert surface.participants.management.removable_participant_ids == ["repairer-1"]
    assert intruder_surface.participants.management.can_manage is False
    assert intruder_surface.participants.management.removable_participant_ids == []
    assert intruder_surface.participants.management.disabled_reason == "Only the thread owner can manage participants."
    assert surface.actions.items[0].action_id == "request_revision"
    assert surface.actions.items[0].tone == "strong"
    assert surface.composer.placeholder
    assert surface.composer.context_hint
    assert surface.render_contract.default_focus_panel == "next_recommended_move"
    assert surface.render_contract.badge_order == [
        "owner_action_required",
        "selected_result",
        "expected_agent_role",
    ]
    assert "decision_notes" in surface.render_contract.panel_order
    assert "artifact_lineage" in surface.render_contract.panel_order
    assert "rationale_snapshots" in surface.render_contract.panel_order
    assert "production_journal" in surface.render_contract.panel_order
    assert surface.render_contract.sticky_primary_action_id == "request_revision"
    assert surface.render_contract.sticky_primary_action_emphasis == "strong"
    assert any(item.panel_id == "history" and item.default_open for item in surface.render_contract.panel_presentations)
