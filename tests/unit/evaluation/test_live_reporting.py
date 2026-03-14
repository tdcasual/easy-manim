from video_agent.evaluation.live_reporting import build_live_report


def test_build_live_report_groups_failures_by_risk_domain() -> None:
    report = build_live_report(
        [
            {
                "case_id": "formula-case",
                "tags": ["real-provider", "quality"],
                "status": "failed",
                "risk_domains": ["formula", "layout"],
                "quality_issue_codes": ["static_previews"],
                "issue_codes": ["unsafe_transformmatchingtex_slice"],
            },
            {
                "case_id": "camera-case",
                "tags": ["real-provider", "quality"],
                "status": "completed",
                "risk_domains": ["camera"],
                "quality_issue_codes": [],
                "issue_codes": [],
            },
        ]
    )

    assert report["case_count"] == 2
    assert report["pass_rate"] == 0.5
    assert report["risk_domain_counts"]["formula"] == 1
    assert report["risk_domain_failure_counts"]["formula"] == 1
    assert report["formula_pass_rate"] == 0.0
    assert report["top_failing_cases"] == ["formula-case"]
