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


def test_build_eval_report_includes_agent_breakdown() -> None:
    report = build_eval_report(
        [
            {
                "status": "completed",
                "duration_seconds": 3.0,
                "issue_codes": [],
                "quality_score": 0.95,
                "agent_id": "agent-a",
                "profile_digest": "digest-2",
            },
            {
                "status": "failed",
                "duration_seconds": 5.0,
                "issue_codes": ["generation_failed"],
                "quality_score": 0.4,
                "agent_id": "agent-a",
                "profile_digest": "digest-1",
            },
        ]
    )

    assert report["agent"]["agent_id"] == "agent-a"
    assert report["agent"]["pass_rate"] == 0.5
    assert report["agent"]["median_quality_score"] == 0.675
    assert report["agent"]["top_issue_codes"] == ["generation_failed"]
    assert report["agent"]["active_profile_digest"] == "digest-2"
