from video_agent.application.recovery_policy_service import RecoveryPolicyService


def test_recovery_policy_selects_preview_repair_for_near_blank_preview() -> None:
    service = RecoveryPolicyService()

    plan = service.build(issue_code="near_blank_preview", failure_contract={"blocking_layer": "preview"})

    assert plan.selected_action == "preview_repair"
    assert plan.repair_recipe == "preview_repair"


def test_recovery_policy_escalates_unknown_issue() -> None:
    service = RecoveryPolicyService()

    plan = service.build(issue_code="unknown_issue", failure_contract={"blocking_layer": "unknown"})

    assert plan.selected_action == "escalate_human"
    assert plan.human_gate_required is True
