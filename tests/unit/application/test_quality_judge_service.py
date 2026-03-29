from video_agent.application.quality_judge_service import QualityJudgeService


def test_quality_judge_produces_dimension_scores() -> None:
    judge = QualityJudgeService(min_score=0.75)

    scorecard = judge.score(
        status="completed",
        issue_codes=["static_previews"],
        preview_issue_codes=["static_previews"],
        summary="Rendered but previews are static",
    )

    assert scorecard.total_score < 0.75
    assert scorecard.dimension_scores["motion_smoothness"] < 0.75
    assert "static_previews" in scorecard.must_fix_issues
    assert scorecard.accepted is False


def test_quality_judge_clean_completed_total_score_is_stable() -> None:
    judge = QualityJudgeService(min_score=0.75)

    scorecard = judge.score(
        status="completed",
        issue_codes=[],
        preview_issue_codes=[],
        summary="Clean render",
    )

    assert scorecard.total_score == 0.925
    assert scorecard.accepted is True
