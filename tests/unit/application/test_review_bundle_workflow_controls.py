import importlib
import importlib.util
from datetime import datetime, timezone

from video_agent.domain.review_workflow_models import (
    WorkflowMemoryRecommendation,
    WorkflowMemoryRecommendations,
)


MODULE_NAME = "video_agent.application.review_bundle_workflow_controls"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


def _recommendations() -> WorkflowMemoryRecommendations:
    return WorkflowMemoryRecommendations(
        root_task_id="root-1",
        pinned_memory_ids=["mem-old"],
        items=[
            WorkflowMemoryRecommendation(
                memory_id="mem-new",
                summary_text="Use higher contrast labels",
                summary_digest="digest-new",
                score=0.91,
                pinned=False,
            ),
            WorkflowMemoryRecommendation(
                memory_id="mem-old",
                summary_text="Old preference",
                summary_digest="digest-old",
                score=0.77,
                pinned=True,
            ),
        ],
    )


def test_build_workflow_memory_action_contract_includes_pin_unpin_and_replace_examples() -> None:
    module = _load_module()

    contract = module.build_workflow_memory_action_contract(_recommendations())

    assert contract is not None
    assert [example.name for example in contract.examples] == ["pin", "unpin", "replace"]
    assert contract.examples[0].payload["pin_workflow_memory_ids"] == ["mem-new"]
    assert contract.examples[1].payload["unpin_workflow_memory_ids"] == ["mem-old"]


def test_build_suggested_next_actions_prefers_pin_and_revise_when_recommendations_exist() -> None:
    module = _load_module()
    contract = module.build_workflow_memory_action_contract(_recommendations())

    actions = module.build_suggested_next_actions(
        status="running",
        acceptance_blockers=["quality_gate_not_accepted"],
        workflow_memory_recommendations=_recommendations(),
        workflow_memory_action_contract=contract,
    )

    assert actions.primary is not None
    assert actions.primary.action_id == "pin_and_revise"
    assert actions.primary.payload["pin_workflow_memory_ids"] == ["mem-new"]
    assert [item.action_id for item in actions.alternatives] == ["revise", "accept"]
    assert actions.alternatives[-1].blocked is True
    assert actions.alternatives[-1].reasons == ["quality_gate_not_accepted"]


def test_build_suggested_next_actions_returns_accept_when_completed_without_blockers() -> None:
    module = _load_module()

    actions = module.build_suggested_next_actions(
        status="completed",
        acceptance_blockers=[],
        workflow_memory_recommendations=None,
        workflow_memory_action_contract=None,
    )

    assert actions.primary is not None
    assert actions.primary.action_id == "accept"
    assert actions.primary.blocked is False
    assert actions.alternatives == []


def test_build_panel_header_marks_accept_ready_and_surfaces_badges() -> None:
    module = _load_module()
    status_summary = module.build_workflow_review_status_summary(
        acceptance_blockers=[],
        pinned_memory_ids=["mem-a"],
        recent_memory_events=[],
        suggested_next_actions=module.build_suggested_next_actions(
            status="completed",
            acceptance_blockers=[],
            workflow_memory_recommendations=None,
            workflow_memory_action_contract=None,
        ),
        workflow_memory_recommendations=None,
    )

    header = module.build_panel_header(
        recent_memory_events=[],
        status_summary=status_summary,
    )

    assert header is not None
    assert header.tone == "ready"
    assert "ready to accept" in header.summary
    assert {badge.badge_id: badge.value for badge in header.badges} == {
        "recommended_action": "accept",
    }


def test_build_panel_header_highlights_latest_memory_event_and_blockers() -> None:
    module = _load_module()
    status_summary = module.build_workflow_review_status_summary(
        acceptance_blockers=["quality_gate_not_accepted"],
        pinned_memory_ids=["mem-old"],
        recent_memory_events=[
            type(
                "Event",
                (),
                {
                    "event_type": "workflow_memory_pinned",
                    "memory_id": "mem-new",
                    "created_at": datetime(2026, 4, 5, tzinfo=timezone.utc),
                },
            )()
        ],
        suggested_next_actions=module.build_suggested_next_actions(
            status="running",
            acceptance_blockers=["quality_gate_not_accepted"],
            workflow_memory_recommendations=_recommendations(),
            workflow_memory_action_contract=module.build_workflow_memory_action_contract(_recommendations()),
        ),
        workflow_memory_recommendations=_recommendations(),
    )

    header = module.build_panel_header(
        recent_memory_events=[
            type(
                "Event",
                (),
                {
                    "event_type": "workflow_memory_pinned",
                    "memory_id": "mem-new",
                    "created_at": datetime(2026, 4, 5, tzinfo=timezone.utc),
                },
            )()
        ],
        status_summary=status_summary,
    )

    assert header is not None
    assert header.tone == "attention"
    badge_values = {badge.badge_id: badge.value for badge in header.badges}
    assert badge_values["recommended_action"] == "pin_and_revise"
    assert badge_values["pending_memory"] == "1"
    assert badge_values["acceptance_blockers"] == "1"
    assert header.highlighted_event is not None
    assert header.highlighted_event.event_type == "workflow_memory_pinned"
