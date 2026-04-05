import importlib
import importlib.util
from datetime import datetime, timezone

from video_agent.domain.review_workflow_models import (
    WorkflowAvailableActionCard,
    WorkflowAvailableActionIntent,
    WorkflowAvailableActionSection,
    WorkflowAvailableActionSections,
    WorkflowReviewPanelBadge,
    WorkflowReviewPanelHeader,
    WorkflowReviewStatusSummary,
)


MODULE_NAME = "video_agent.application.review_bundle_render_contract"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def test_build_applied_action_feedback_for_pinned_memory_uses_success_tone_and_follow_up() -> None:
    module = _load_module()
    feedback = module.build_applied_action_feedback(
        recent_memory_events=[
            type(
                "Event",
                (),
                {
                    "event_type": "workflow_memory_pinned",
                    "memory_id": "mem-1",
                    "created_at": datetime(2026, 4, 5, tzinfo=timezone.utc),
                },
            )()
        ],
        status_summary=WorkflowReviewStatusSummary(recommended_action_id="pin_and_revise"),
    )

    assert feedback is not None
    assert feedback.tone == "success"
    assert feedback.title == "Workflow memory update applied"
    assert "pin_and_revise" in feedback.summary
    assert feedback.follow_up_action_id == "pin_and_revise"


def test_build_render_contract_prefers_high_priority_for_attention_panels() -> None:
    module = _load_module()
    render_contract = module.build_render_contract(
        panel_header=WorkflowReviewPanelHeader(
            tone="attention",
            badges=[WorkflowReviewPanelBadge(badge_id="recommended_action", label="Recommended", value="pin_and_revise")],
        ),
        action_sections=WorkflowAvailableActionSections(
            items=[
                WorkflowAvailableActionSection(
                    section_id="recommended",
                    title="Recommended next step",
                    items=[
                        WorkflowAvailableActionCard(
                            action_id="pin_and_revise",
                            title="Pin and revise",
                            button_label="Pin memory and revise",
                            action_family="combined",
                            is_primary=True,
                            intent=WorkflowAvailableActionIntent(review_decision="revise", mutates_workflow_memory=True),
                        )
                    ],
                ),
                WorkflowAvailableActionSection(section_id="blocked", title="Blocked actions"),
            ]
        ),
        status_summary=WorkflowReviewStatusSummary(recommended_action_id="pin_and_revise"),
        applied_action_feedback=None,
    )

    assert render_contract is not None
    assert render_contract.panel_tone == "attention"
    assert render_contract.display_priority == "high"
    assert render_contract.default_focus_section_id == "recommended"
    assert render_contract.default_expanded_section_ids == ["recommended", "blocked"]
    assert render_contract.sticky_primary_action_id == "pin_and_revise"
    assert render_contract.sticky_primary_action_emphasis == "strong"
    tones = {item.section_id: item.tone for item in render_contract.section_presentations}
    assert tones == {"recommended": "accent", "blocked": "muted"}


def test_build_render_contract_relaxes_priority_for_ready_accept_panel() -> None:
    module = _load_module()
    render_contract = module.build_render_contract(
        panel_header=WorkflowReviewPanelHeader(
            tone="ready",
            badges=[WorkflowReviewPanelBadge(badge_id="recommended_action", label="Recommended", value="accept")],
        ),
        action_sections=WorkflowAvailableActionSections(
            items=[
                WorkflowAvailableActionSection(
                    section_id="recommended",
                    title="Recommended next step",
                    items=[
                        WorkflowAvailableActionCard(
                            action_id="accept",
                            title="Accept",
                            button_label="Accept result",
                            action_family="review_decision",
                            is_primary=True,
                            intent=WorkflowAvailableActionIntent(review_decision="accept"),
                        )
                    ],
                )
            ]
        ),
        status_summary=WorkflowReviewStatusSummary(recommended_action_id="accept"),
        applied_action_feedback=None,
    )

    assert render_contract is not None
    assert render_contract.display_priority == "normal"
    assert render_contract.sticky_primary_action_emphasis == "normal"
    assert render_contract.section_presentations[0].section_id == "recommended"
    assert render_contract.section_presentations[0].collapsible is False
