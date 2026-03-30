from video_agent.evaluation.reporting import build_eval_report, render_eval_report_markdown



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


def test_build_eval_report_splits_delivery_rate_from_quality_success_rate() -> None:
    report = build_eval_report(
        [
            {
                "status": "completed",
                "delivery_passed": True,
                "quality_passed": False,
                "duration_seconds": 3.0,
                "issue_codes": [],
            },
            {
                "status": "completed",
                "delivery_passed": True,
                "quality_passed": True,
                "duration_seconds": 5.0,
                "issue_codes": [],
            },
        ]
    )

    assert report["completed_count"] == 1
    assert report["quality_pass_count"] == 1
    assert report["delivery_count"] == 2
    assert report["success_rate"] == 0.5
    assert report["delivery_rate"] == 1.0


def test_render_eval_report_markdown_separates_quality_pass_rate_from_delivery_rate() -> None:
    markdown = render_eval_report_markdown(
        {
            "suite_id": "suite-a",
            "run_id": "run-1",
            "provider": "mock",
            "total_cases": 2,
            "report": {
                "success_rate": 0.5,
                "delivery_rate": 1.0,
                "median_duration_seconds": 4.0,
                "failure_codes": {},
            },
        }
    )

    assert "- Quality Pass Rate: 50.00%" in markdown
    assert "- Delivery Rate: 100.00%" in markdown
    assert "- Success Rate:" not in markdown
