import importlib
import importlib.util
from types import SimpleNamespace

from video_agent.domain.video_thread_models import (
    VideoThreadAction,
    VideoThreadActions,
    VideoThreadArtifactLineage,
    VideoThreadArtifactLineageItem,
    VideoThreadAuthorship,
    VideoThreadDecisionNote,
    VideoThreadDecisionNotes,
    VideoThreadDiscussionGroup,
    VideoThreadDiscussionGroups,
    VideoThreadDiscussionRuntime,
    VideoThreadHistory,
    VideoThreadHistoryCard,
    VideoThreadIterationCompare,
    VideoThreadLatestExplanation,
    VideoThreadParticipantRuntime,
    VideoThreadParticipantRuntimeContributor,
    VideoThreadProductionJournal,
    VideoThreadProductionJournalEntry,
    VideoThreadRationaleSnapshot,
    VideoThreadRationaleSnapshots,
    VideoThreadResponsibility,
)


MODULE_NAME = "video_agent.application.video_projection_render_contract"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_build_render_contract_highlights_next_move_when_review_is_required() -> None:
    module = _load_module()

    contract = module.build_render_contract(
        responsibility=VideoThreadResponsibility(
            owner_action_required="review_latest_result",
            expected_agent_role="repairer",
        ),
        participants=[SimpleNamespace(participant_id="owner")],
        current_result=object(),
        current_iteration=None,
        actions=VideoThreadActions(
            items=[
                VideoThreadAction(
                    action_id="request_revision",
                    label="Request revision",
                    tone="strong",
                )
            ]
        ),
        latest_explanation=VideoThreadLatestExplanation(),
        decision_notes=VideoThreadDecisionNotes(),
        artifact_lineage=VideoThreadArtifactLineage(),
        rationale_snapshots=VideoThreadRationaleSnapshots(),
        iteration_compare=VideoThreadIterationCompare(),
        authorship=VideoThreadAuthorship(),
        production_journal=VideoThreadProductionJournal(),
        discussion_runtime=VideoThreadDiscussionRuntime(),
        participant_runtime=VideoThreadParticipantRuntime(),
        history=VideoThreadHistory(),
        discussion_groups=VideoThreadDiscussionGroups(),
        has_iteration_detail=False,
    )

    next_move_panel = next(
        item for item in contract.panel_presentations if item.panel_id == "next_recommended_move"
    )

    assert contract.default_focus_panel == "next_recommended_move"
    assert contract.panel_tone == "attention"
    assert contract.display_priority == "high"
    assert contract.badge_order == [
        "owner_action_required",
        "selected_result",
        "expected_agent_role",
    ]
    assert contract.sticky_primary_action_id == "request_revision"
    assert contract.sticky_primary_action_emphasis == "strong"
    assert next_move_panel.tone == "attention"
    assert next_move_panel.default_open is True
    assert "participants" in contract.panel_order


def test_build_render_contract_drops_participants_and_opens_optional_panels_when_data_exists() -> None:
    module = _load_module()

    contract = module.build_render_contract(
        responsibility=VideoThreadResponsibility(expected_agent_role="repairer"),
        participants=[],
        current_result=None,
        current_iteration=SimpleNamespace(requested_action=None),
        actions=VideoThreadActions(),
        latest_explanation=VideoThreadLatestExplanation(summary="Why this cut is working."),
        decision_notes=VideoThreadDecisionNotes(
            items=[
                VideoThreadDecisionNote(
                    note_id="note-1",
                    note_kind="selection_rationale",
                    title="Why this version is selected",
                    summary="It lands more clearly.",
                )
            ]
        ),
        artifact_lineage=VideoThreadArtifactLineage(
            items=[
                VideoThreadArtifactLineageItem(
                    lineage_id="lineage-1",
                    status="selected",
                )
            ]
        ),
        rationale_snapshots=VideoThreadRationaleSnapshots(
            items=[
                VideoThreadRationaleSnapshot(
                    snapshot_id="snapshot-1",
                    snapshot_kind="selection_rationale",
                    title="Current rationale",
                    status="current",
                )
            ]
        ),
        iteration_compare=VideoThreadIterationCompare(
            current_iteration_id="iter-2",
            change_summary="Slower opener.",
        ),
        authorship=VideoThreadAuthorship(primary_agent_role="repairer"),
        production_journal=VideoThreadProductionJournal(
            entries=[
                VideoThreadProductionJournalEntry(
                    entry_id="journal-1",
                    entry_kind="run",
                    title="Run started",
                )
            ]
        ),
        discussion_runtime=VideoThreadDiscussionRuntime(active_iteration_id="iter-2"),
        participant_runtime=VideoThreadParticipantRuntime(
            expected_display_name="Repairer",
            recent_contributors=[
                VideoThreadParticipantRuntimeContributor(display_name="Repairer")
            ],
        ),
        history=VideoThreadHistory(
            cards=[
                VideoThreadHistoryCard(
                    card_id="history-1",
                    card_type="owner_request",
                    title="Slow the opener",
                )
            ]
        ),
        discussion_groups=VideoThreadDiscussionGroups(
            groups=[
                VideoThreadDiscussionGroup(
                    group_id="group-1",
                    prompt_turn_id="turn-1",
                    prompt_title="Slow the opener",
                )
            ]
        ),
        has_iteration_detail=True,
    )

    history_panel = next(item for item in contract.panel_presentations if item.panel_id == "history")
    discussion_runtime_panel = next(
        item for item in contract.panel_presentations if item.panel_id == "discussion_runtime"
    )
    participant_runtime_panel = next(
        item for item in contract.panel_presentations if item.panel_id == "participant_runtime"
    )

    assert contract.default_focus_panel == "latest_explanation"
    assert "participants" not in contract.panel_order
    assert "decision_notes" in contract.default_expanded_panels
    assert "artifact_lineage" in contract.default_expanded_panels
    assert "rationale_snapshots" in contract.default_expanded_panels
    assert "iteration_compare" in contract.default_expanded_panels
    assert "authorship" in contract.default_expanded_panels
    assert "production_journal" in contract.default_expanded_panels
    assert "discussion_runtime" in contract.default_expanded_panels
    assert "participant_runtime" in contract.default_expanded_panels
    assert "discussion_groups" in contract.default_expanded_panels
    assert "iteration_detail" in contract.default_expanded_panels
    assert discussion_runtime_panel.default_open is True
    assert participant_runtime_panel.default_open is True
    assert history_panel.default_open is True
