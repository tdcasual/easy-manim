from video_agent.evaluation.repair_reporting import build_repair_report


def test_build_repair_report_computes_attempt_rate_and_post_repair_failures() -> None:
    report = build_repair_report(
        [
            {
                "tags": ["repair"],
                "repair_attempted": True,
                "repair_success": True,
                "repair_children": 1,
                "issue_codes": [],
            },
            {
                "tags": ["repair"],
                "repair_attempted": True,
                "repair_success": False,
                "repair_children": 2,
                "issue_codes": ["render_failed"],
            },
            {
                "tags": ["repair"],
                "repair_attempted": False,
                "repair_success": False,
                "repair_children": 0,
                "issue_codes": ["missing_scene"],
            },
            {
                "tags": ["smoke"],
                "repair_attempted": False,
                "repair_success": False,
                "repair_children": 0,
                "issue_codes": [],
            },
        ]
    )

    assert report["case_count"] == 3
    assert report["attempted_count"] == 2
    assert report["repair_attempt_rate"] == 2 / 3
    assert report["success_count"] == 1
    assert report["repair_success_rate"] == 1 / 3
    assert report["average_children_per_repaired_root"] == 1.5
    assert report["failure_codes_after_repair"]["render_failed"] == 1
    assert report["failure_codes_after_repair"]["missing_scene"] == 1
