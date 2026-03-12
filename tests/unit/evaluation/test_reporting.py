from video_agent.evaluation.reporting import build_eval_report



def test_build_eval_report_computes_success_rate_and_failures() -> None:
    report = build_eval_report(
        [
            {"status": "completed", "duration_seconds": 3.0, "issue_codes": []},
            {"status": "failed", "duration_seconds": 5.0, "issue_codes": ["generation_failed"]},
        ]
    )

    assert report["success_rate"] == 0.5
    assert report["failure_codes"]["generation_failed"] == 1
    assert report["median_duration_seconds"] == 4.0
