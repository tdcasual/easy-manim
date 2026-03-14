from video_agent.evaluation.quality_reporting import build_quality_report


def test_build_quality_report_summarizes_quality_slice() -> None:
    report = build_quality_report(
        [
            {"tags": ["quality"], "status": "completed", "quality_score": 0.9, "quality_issue_codes": []},
            {"tags": ["quality"], "status": "failed", "quality_score": 0.2, "quality_issue_codes": ["static_previews"]},
        ]
    )

    assert report["case_count"] == 2
    assert report["pass_rate"] == 0.5
    assert report["median_quality_score"] == 0.55
    assert report["quality_issue_codes"]["static_previews"] == 1
