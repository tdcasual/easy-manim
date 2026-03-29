from video_agent.agent_policy import DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES
from video_agent.config import Settings


def test_preview_quality_failures_are_retryable_by_default() -> None:
    settings = Settings()

    assert "near_blank_preview" in DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES
    assert "static_previews" in DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES
    assert "near_blank_preview" in settings.auto_repair_retryable_issue_codes
    assert "static_previews" in settings.auto_repair_retryable_issue_codes
