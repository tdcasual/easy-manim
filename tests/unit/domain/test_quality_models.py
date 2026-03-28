from video_agent.domain.quality_models import QualityScorecard


def test_quality_scorecard_tracks_overall_score_and_dimensions() -> None:
    scorecard = QualityScorecard(
        task_id="task-1",
        overall_score=0.85,
        dimensions={"prompt_alignment": 0.9, "visual_clarity": 0.8},
    )

    assert scorecard.overall_score == 0.85
    assert scorecard.dimensions["prompt_alignment"] == 0.9
