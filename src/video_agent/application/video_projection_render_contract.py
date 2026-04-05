from __future__ import annotations

from video_agent.domain.video_thread_models import (
    VideoThreadActions,
    VideoThreadArtifactLineage,
    VideoThreadAuthorship,
    VideoThreadDecisionNotes,
    VideoThreadDiscussionGroups,
    VideoThreadDiscussionRuntime,
    VideoThreadHistory,
    VideoThreadIterationCompare,
    VideoThreadLatestExplanation,
    VideoThreadPanelPresentation,
    VideoThreadParticipantRuntime,
    VideoThreadProductionJournal,
    VideoThreadRenderContract,
    VideoThreadResponsibility,
)


def build_render_contract(
    *,
    responsibility: VideoThreadResponsibility,
    participants,
    current_result,
    current_iteration,
    actions: VideoThreadActions,
    latest_explanation: VideoThreadLatestExplanation,
    decision_notes: VideoThreadDecisionNotes,
    artifact_lineage: VideoThreadArtifactLineage,
    rationale_snapshots,
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
        and (
            iteration_compare.change_summary
            or iteration_compare.rationale_shift_summary
            or iteration_compare.continuity_summary
        )
    ):
        default_expanded_panels.insert(
            4
            if decision_notes.items and artifact_lineage.items and rationale_snapshots.items
            else 3
            if sum(
                bool(item)
                for item in (
                    decision_notes.items,
                    artifact_lineage.items,
                    rationale_snapshots.items,
                )
            )
            >= 2
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
        panel_presentations=build_panel_presentations(
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


def build_panel_presentations(
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
                )
                >= 2
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
