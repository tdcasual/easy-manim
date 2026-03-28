from video_agent.application.failure_contract import build_failure_contract


def test_failure_contract_marks_render_failed_as_retryable() -> None:
    contract = build_failure_contract(
        issue_code="render_failed",
        summary="Render failed",
        preview_issue_codes=[],
        retryable_issue_codes=["render_failed"],
    )

    assert contract.retryable is True
    assert contract.blocking_layer == "render"
    assert contract.recommended_action == "auto_repair"
    assert "repair_render_path" in contract.candidate_actions


def test_failure_contract_marks_provider_auth_error_as_fix_credentials() -> None:
    contract = build_failure_contract(
        issue_code="provider_auth_error",
        summary="Provider authentication failed",
        preview_issue_codes=[],
        retryable_issue_codes=["render_failed"],
    )

    assert contract.retryable is False
    assert contract.blocking_layer == "provider"
    assert contract.recommended_action == "fix_credentials"


def test_failure_contract_adds_preview_repair_actions_for_preview_failures() -> None:
    contract = build_failure_contract(
        issue_code="near_blank_preview",
        summary="Preview quality failed",
        preview_issue_codes=["near_blank_preview"],
        retryable_issue_codes=["near_blank_preview"],
    )

    assert contract.blocking_layer == "preview"
    assert contract.repair_strategy == "preview_repair"
    assert contract.candidate_actions == ["preview_repair"]
    assert contract.cost_class == "low"
    assert contract.fallback_generation_mode == "guided_generate"
