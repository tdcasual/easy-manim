from video_agent.agent_policy import (
    DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES,
    QUALITY_ISSUE_CODES,
)


def test_agent_policy_exposes_formula_repair_issue_codes() -> None:
    assert "unsafe_transformmatchingtex_slice" in DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES
    assert "unsafe_bare_tex_selection" in DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES
    assert "unsafe_bare_tex_highlight" in DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES


def test_agent_policy_exposes_preview_quality_issue_codes() -> None:
    assert "near_blank_preview" in QUALITY_ISSUE_CODES
    assert "static_previews" in QUALITY_ISSUE_CODES
