from video_agent.evaluation.reviewer_digest import render_reviewer_digest


def test_render_reviewer_digest_prioritizes_manual_review_failures() -> None:
    content = render_reviewer_digest(
        {
            "run_id": "run-123",
            "items": [
                {
                    "case_id": "formula-case",
                    "task_id": "task-1",
                    "status": "failed",
                    "manual_review_required": True,
                    "risk_domains": ["formula"],
                    "review_focus": ["formula legibility"],
                    "issue_codes": ["unsafe_transformmatchingtex_slice"],
                    "quality_issue_codes": ["static_previews"],
                },
                {
                    "case_id": "circle-case",
                    "task_id": "task-2",
                    "status": "completed",
                    "manual_review_required": False,
                    "risk_domains": ["geometry"],
                    "review_focus": [],
                    "issue_codes": [],
                    "quality_issue_codes": [],
                },
            ],
            "report": {"live": {"top_failing_cases": ["formula-case"]}},
        }
    )

    assert "formula-case" in content
    assert "Review First" in content
    assert "unsafe_transformmatchingtex_slice" in content
    assert "formula legibility" in content
