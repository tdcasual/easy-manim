from pathlib import Path

from video_agent.adapters.storage.sqlite_bootstrap import SQLiteBootstrapper
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.video_iteration_service import VideoIterationService
from video_agent.application.video_projection_service import VideoProjectionService
from video_agent.application.video_run_binding_service import VideoRunBindingService
from video_agent.application.video_thread_service import VideoThreadService
from video_agent.application.video_turn_service import VideoTurnService
from video_agent.domain.video_thread_models import VideoThread


def _build_store(tmp_path: Path) -> SQLiteTaskStore:
    database_path = tmp_path / "agent.db"
    SQLiteBootstrapper(database_path).bootstrap()
    return SQLiteTaskStore(database_path)


def test_video_projection_service_builds_zero_inference_owner_surface(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    iteration_service = VideoIterationService(store=store)
    turn_service = VideoTurnService(store=store)
    run_binding_service = VideoRunBindingService(store=store)
    thread_service = VideoThreadService(
        store=store,
        iteration_service=iteration_service,
        turn_service=turn_service,
    )
    projection_service = VideoProjectionService(store=store)

    created = thread_service.create_thread(
        owner_agent_id="owner",
        title="Circle explainer",
        prompt="draw a circle",
    )
    initial_result = iteration_service.register_result(
        thread_id=created.thread.thread_id,
        iteration_id=created.iteration.iteration_id,
        source_task_id="task-0",
        status="ready",
        result_summary="Initial cut with a brisk opener.",
    )
    follow_up = iteration_service.create_iteration(
        thread_id=created.thread.thread_id,
        goal="Refine the opener pacing",
        parent_iteration_id=created.iteration.iteration_id,
        requested_action="revise",
        source_result_id=initial_result.result_id,
    )
    thread_service.upsert_participant(
        thread_id=created.thread.thread_id,
        participant_id="repairer-1",
        participant_type="agent",
        agent_id="repairer-1",
        role="repairer",
        display_name="Repairer",
    )
    iteration_service.assign_responsibility(
        follow_up.iteration_id,
        responsible_role="repairer",
        responsible_agent_id="repairer-1",
    )
    result = iteration_service.register_result(
        thread_id=created.thread.thread_id,
        iteration_id=follow_up.iteration_id,
        source_task_id="task-1",
        status="ready",
        result_summary="A slower opener with a more deliberate title entrance.",
    )
    result.video_resource = "video-task://task-1/artifacts/final.mp4"
    result.preview_resources = ["video-task://task-1/artifacts/previews/frame-001.png"]
    result.script_resource = "video-task://task-1/artifacts/script.py"
    store.upsert_video_result(result)
    store.upsert_video_thread(
        VideoThread(
            thread_id=created.thread.thread_id,
            owner_agent_id=created.thread.owner_agent_id,
            title=created.thread.title,
            status=created.thread.status,
            current_iteration_id=follow_up.iteration_id,
            selected_result_id=result.result_id,
            origin_prompt=created.thread.origin_prompt,
            origin_context_summary=created.thread.origin_context_summary,
            created_at=created.thread.created_at,
        )
    )
    turn_service.append_agent_explanation_turn(
        thread_id=created.thread.thread_id,
        iteration_id=follow_up.iteration_id,
        title="Why the opener changed",
        summary="The slower opening gives the title card room to land before the geometry animation begins.",
        speaker_agent_id="planner-1",
        speaker_role="planner",
        intent_type="request_explanation",
        reply_to_turn_id=turn_service.append_owner_turn(
            thread_id=created.thread.thread_id,
            iteration_id=follow_up.iteration_id,
            title="Why this pacing?",
            summary="Explain the slower opener.",
            intent_type="request_explanation",
            related_result_id=result.result_id,
        ).turn_id,
        related_result_id=result.result_id,
    )
    run = run_binding_service.attach_run(
        thread_id=created.thread.thread_id,
        iteration_id=follow_up.iteration_id,
        agent_id="repairer-1",
        role="repairer",
        task_id="task-1",
    )
    run_binding_service.mark_run_status(
        run.run_id,
        status="running",
        phase="repairing",
        output_summary="Refining the title motion timing.",
    )

    surface = projection_service.build_surface(created.thread.thread_id)

    assert surface.thread_header.title == "Circle explainer"
    assert surface.current_focus.current_iteration_id == follow_up.iteration_id
    assert surface.current_focus.current_result_id == result.result_id
    assert surface.current_focus.current_result_author_display_name == "Repairer"
    assert surface.current_focus.current_result_author_role == "repairer"
    assert surface.current_focus.current_result_selection_reason
    assert surface.selection_summary.summary == surface.current_focus.current_result_selection_reason
    assert surface.selection_summary.selected_result_id == result.result_id
    assert surface.latest_explanation.summary == (
        "The slower opening gives the title card room to land before the geometry animation begins."
    )
    assert surface.latest_explanation.speaker_display_name == "Planner"
    assert surface.authorship.primary_agent_display_name == "Repairer"
    assert surface.authorship.primary_agent_role == "repairer"
    assert surface.authorship.source_run_id == run.run_id
    assert surface.decision_notes.title == "Decision Notes"
    assert [item.note_kind for item in surface.decision_notes.items] == [
        "selection_rationale",
        "agent_explanation",
        "iteration_goal",
    ]
    assert surface.decision_notes.items[0].source_result_id == result.result_id
    assert surface.decision_notes.items[1].source_turn_id == surface.latest_explanation.turn_id
    assert surface.artifact_lineage.title == "Artifact Lineage"
    assert surface.artifact_lineage.selected_result_id == result.result_id
    assert [item.from_result_id for item in surface.artifact_lineage.items] == [
        None,
        initial_result.result_id,
    ]
    assert [item.to_result_id for item in surface.artifact_lineage.items] == [
        initial_result.result_id,
        result.result_id,
    ]
    assert surface.artifact_lineage.items[0].status == "origin"
    assert surface.artifact_lineage.items[1].status == "selected"
    assert surface.artifact_lineage.items[1].trigger_label == "Owner asked for explanation"
    assert surface.artifact_lineage.items[1].actor_role == "repairer"
    assert surface.rationale_snapshots.title == "Rationale Snapshots"
    assert surface.rationale_snapshots.current_iteration_id == follow_up.iteration_id
    assert [item.snapshot_kind for item in surface.rationale_snapshots.items] == [
        "owner_goal",
        "selection_rationale",
    ]
    assert surface.rationale_snapshots.items[0].status == "archived"
    assert surface.rationale_snapshots.items[1].status == "current"
    assert surface.rationale_snapshots.items[1].source_result_id == result.result_id
    assert surface.iteration_compare.title == "Iteration Compare"
    assert surface.iteration_compare.previous_iteration_id == created.iteration.iteration_id
    assert surface.iteration_compare.current_iteration_id == follow_up.iteration_id
    assert surface.iteration_compare.previous_result_id == initial_result.result_id
    assert surface.iteration_compare.current_result_id == result.result_id
    assert surface.iteration_compare.change_summary == (
        "A slower opener with a more deliberate title entrance."
    )
    assert "Refine the opener pacing" in (
        surface.iteration_compare.rationale_shift_summary
    )
    assert surface.iteration_compare.continuity_status == "changed"
    assert surface.production_journal.title == "Production Journal"
    assert [item.entry_kind for item in surface.production_journal.entries] == [
        "iteration",
        "iteration",
        "run",
        "result",
        "result",
    ]
    assert surface.production_journal.entries[-1].resource_refs == [
        "video-task://task-1/artifacts/final.mp4",
        "video-task://task-1/artifacts/previews/frame-001.png",
        "video-task://task-1/artifacts/script.py",
    ]
    assert surface.discussion_groups.groups[0].status == "answered"
    assert surface.discussion_groups.groups[0].prompt_intent_type == "request_explanation"
    assert surface.discussion_groups.groups[0].replies[0].turn_id == surface.latest_explanation.turn_id
    assert surface.discussion_runtime.title == "Discussion Runtime"
    assert surface.discussion_runtime.active_iteration_id == follow_up.iteration_id
    assert surface.discussion_runtime.active_discussion_group_id == (
        f"group-{surface.discussion_groups.groups[0].prompt_turn_id}"
    )
    assert surface.discussion_runtime.continuity_scope == "iteration"
    assert surface.discussion_runtime.reply_policy == "continue_thread"
    assert surface.discussion_runtime.default_intent_type == "discuss"
    assert surface.discussion_runtime.default_reply_to_turn_id == (
        surface.discussion_groups.groups[0].prompt_turn_id
    )
    assert surface.discussion_runtime.default_related_result_id == result.result_id
    assert surface.discussion_runtime.addressed_participant_id == "repairer-1"
    assert surface.discussion_runtime.addressed_agent_id == "repairer-1"
    assert surface.discussion_runtime.addressed_display_name == "Repairer"
    assert surface.discussion_runtime.suggested_follow_up_modes == [
        "ask_why",
        "request_change",
        "preserve_direction",
        "branch_revision",
    ]
    assert surface.discussion_runtime.active_thread_title == "Why this pacing?"
    assert surface.discussion_runtime.active_thread_summary == "Explain the slower opener."
    assert surface.discussion_runtime.latest_owner_turn_id == surface.discussion_groups.groups[0].prompt_turn_id
    assert surface.discussion_runtime.latest_agent_turn_id == surface.latest_explanation.turn_id
    assert surface.discussion_runtime.latest_agent_summary == surface.latest_explanation.summary
    assert surface.participant_runtime.title == "Participant Runtime"
    assert surface.participant_runtime.active_iteration_id == follow_up.iteration_id
    assert surface.participant_runtime.expected_participant_id == "repairer-1"
    assert surface.participant_runtime.expected_agent_id == "repairer-1"
    assert surface.participant_runtime.expected_display_name == "Repairer"
    assert surface.participant_runtime.expected_role == "repairer"
    assert surface.participant_runtime.continuity_mode == "keep_current_participant"
    assert surface.participant_runtime.follow_up_target_locked is True
    assert [item.display_name for item in surface.participant_runtime.recent_contributors] == [
        "Repairer",
        "Planner",
    ]
    assert [card.card_type for card in surface.history.cards] == [
        "process_update",
        "agent_explanation",
        "result_selection",
    ]
    assert surface.history.cards[0].summary == "Refining the title motion timing."
    assert surface.history.cards[0].actor_display_name == "Repairer"
    assert surface.history.cards[0].intent_type == "request_revision"
    assert surface.history.cards[1].emphasis == "primary"
    assert surface.history.cards[1].intent_type == "request_explanation"
    assert surface.history.cards[2].iteration_id == follow_up.iteration_id
    assert surface.next_recommended_move.recommended_action_id == "request_revision"
    assert surface.next_recommended_move.owner_action_required == "review_latest_result"
    assert surface.responsibility.owner_action_required == "review_latest_result"
    assert surface.responsibility.expected_agent_role == "repairer"
    assert surface.responsibility.expected_agent_id == "repairer-1"
    assert surface.iteration_detail.title == "Iteration Detail"
    assert surface.iteration_detail.selected_iteration_id == follow_up.iteration_id
    assert surface.iteration_detail.resource_uri == (
        f"video-thread://{created.thread.thread_id}/iterations/{follow_up.iteration_id}.json"
    )
    assert surface.iteration_detail.turn_count == 2
    assert surface.iteration_detail.run_count == 1
    assert surface.iteration_detail.result_count == 1
    assert surface.iteration_detail.execution_summary.title == "Execution Summary"
    assert surface.iteration_detail.execution_summary.summary == (
        f"Repairer is currently repairing for task task-1 while shaping result {result.result_id}."
    )
    assert surface.iteration_detail.execution_summary.task_id == "task-1"
    assert surface.iteration_detail.execution_summary.run_id == run.run_id
    assert surface.iteration_detail.execution_summary.status == "running"
    assert surface.iteration_detail.execution_summary.phase == "repairing"
    assert surface.iteration_detail.execution_summary.agent_id == "repairer-1"
    assert surface.iteration_detail.execution_summary.agent_display_name == "Repairer"
    assert surface.iteration_detail.execution_summary.agent_role == "repairer"
    assert surface.iteration_detail.execution_summary.result_id == result.result_id
    assert surface.iteration_detail.execution_summary.discussion_group_id == (
        f"group-{surface.discussion_groups.groups[0].prompt_turn_id}"
    )
    assert surface.iteration_detail.execution_summary.reply_to_turn_id == (
        surface.discussion_groups.groups[0].prompt_turn_id
    )
    assert surface.iteration_detail.execution_summary.latest_owner_turn_id == (
        surface.discussion_groups.groups[0].prompt_turn_id
    )
    assert surface.iteration_detail.execution_summary.latest_agent_turn_id == surface.latest_explanation.turn_id
    assert surface.iteration_detail.execution_summary.is_active is True
    assert surface.iteration_workbench.selected_iteration_id == follow_up.iteration_id
    assert surface.conversation.turns[-1].title == "Why the opener changed"
    assert surface.process.runs[-1].phase == "repairing"
    assert [item.role for item in surface.participants.items] == ["owner", "repairer"]
    assert surface.actions.items[0].action_id == "request_revision"
    assert surface.actions.items[0].tone == "strong"
    assert surface.actions.items[0].description
    assert surface.actions.items[1].action_id == "request_explanation"
    assert surface.actions.items[1].disabled is False
    assert surface.composer.disabled is False
    assert surface.composer.target.iteration_id == follow_up.iteration_id
    assert surface.composer.target.result_id == result.result_id
    assert surface.composer.target.addressed_participant_id == "repairer-1"
    assert surface.composer.target.addressed_agent_id == "repairer-1"
    assert surface.composer.target.addressed_display_name == "Repairer"
    assert surface.composer.target.agent_role == "repairer"
    assert surface.composer.target.summary
    assert "A slower opener with a more deliberate title entrance." in surface.composer.context_hint
    assert surface.render_contract.default_focus_panel == "next_recommended_move"
    assert surface.render_contract.panel_tone == "attention"
    assert surface.render_contract.display_priority == "high"
    assert surface.render_contract.badge_order == [
        "owner_action_required",
        "selected_result",
        "expected_agent_role",
    ]
    assert surface.render_contract.sticky_primary_action_id == "request_revision"
    assert surface.render_contract.sticky_primary_action_emphasis == "strong"
    history_panel = next(
        item for item in surface.render_contract.panel_presentations if item.panel_id == "history"
    )
    assert history_panel.default_open is True
    assert history_panel.emphasis == "supporting"
    next_move_panel = next(
        item for item in surface.render_contract.panel_presentations if item.panel_id == "next_recommended_move"
    )
    assert next_move_panel.tone == "attention"
    assert next_move_panel.emphasis == "primary"
    discussion_runtime_panel = next(
        item for item in surface.render_contract.panel_presentations if item.panel_id == "discussion_runtime"
    )
    assert discussion_runtime_panel.default_open is True
    participant_runtime_panel = next(
        item for item in surface.render_contract.panel_presentations if item.panel_id == "participant_runtime"
    )
    assert participant_runtime_panel.default_open is True
    assert "selection_summary" in surface.render_contract.panel_order
    assert "latest_explanation" in surface.render_contract.panel_order
    assert "decision_notes" in surface.render_contract.panel_order
    assert "artifact_lineage" in surface.render_contract.panel_order
    assert "rationale_snapshots" in surface.render_contract.panel_order
    assert "discussion_runtime" in surface.render_contract.panel_order
    assert "participant_runtime" in surface.render_contract.panel_order
    assert "next_recommended_move" in surface.render_contract.panel_order
    assert "iteration_detail" in surface.render_contract.panel_order
    assert "production_journal" in surface.render_contract.panel_order
    assert "history" in surface.render_contract.panel_order
    assert "participants" in surface.render_contract.panel_order

    iteration_payload = projection_service.build_iteration_payload(
        created.thread.thread_id,
        follow_up.iteration_id,
    )
    assert iteration_payload["summary"]
    assert iteration_payload["composer_target"]["iteration_id"] == follow_up.iteration_id
    assert iteration_payload["composer_target"]["result_id"] == result.result_id
    assert iteration_payload["composer_target"]["addressed_participant_id"] == "repairer-1"
    assert iteration_payload["composer_target"]["addressed_agent_id"] == "repairer-1"
    assert iteration_payload["composer_target"]["addressed_display_name"] == "Repairer"
    assert iteration_payload["composer_target"]["agent_role"] == "repairer"
    assert iteration_payload["execution_summary"]["title"] == "Execution Summary"
    assert iteration_payload["execution_summary"]["summary"] == (
        f"Repairer is currently repairing for task task-1 while shaping result {result.result_id}."
    )
    assert iteration_payload["execution_summary"]["task_id"] == "task-1"
    assert iteration_payload["execution_summary"]["run_id"] == run.run_id
    assert iteration_payload["execution_summary"]["status"] == "running"
    assert iteration_payload["execution_summary"]["phase"] == "repairing"
    assert iteration_payload["execution_summary"]["agent_id"] == "repairer-1"
    assert iteration_payload["execution_summary"]["agent_display_name"] == "Repairer"
    assert iteration_payload["execution_summary"]["agent_role"] == "repairer"
    assert iteration_payload["execution_summary"]["result_id"] == result.result_id
    assert iteration_payload["execution_summary"]["discussion_group_id"] == (
        f"group-{surface.discussion_groups.groups[0].prompt_turn_id}"
    )
    assert iteration_payload["execution_summary"]["reply_to_turn_id"] == (
        surface.discussion_groups.groups[0].prompt_turn_id
    )
    assert iteration_payload["execution_summary"]["latest_owner_turn_id"] == (
        surface.discussion_groups.groups[0].prompt_turn_id
    )
    assert iteration_payload["execution_summary"]["latest_agent_turn_id"] == surface.latest_explanation.turn_id
    assert iteration_payload["execution_summary"]["is_active"] is True
    assert iteration_payload["runs"][0]["role"] == "repairer"
    assert iteration_payload["runs"][0]["agent_display_name"] == "Repairer"
    assert iteration_payload["turns"][1]["reply_to_turn_id"] is not None
    assert iteration_payload["results"][0]["video_resource"] == "video-task://task-1/artifacts/final.mp4"
