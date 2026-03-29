from video_agent.application.failure_contract import build_failure_contract


def test_preview_issue_codes_are_marked_retryable_when_enabled_in_retryable_list() -> None:
    contract = build_failure_contract(
        issue_code="near_blank_preview",
        summary="Preview quality failed",
        preview_issue_codes=["near_blank_preview"],
        retryable_issue_codes=["near_blank_preview", "static_previews"],
    )

    assert contract.blocking_layer == "preview"
    assert contract.retryable is True
    assert contract.recommended_action == "auto_repair"
    assert contract.repair_strategy == "preview_repair"
