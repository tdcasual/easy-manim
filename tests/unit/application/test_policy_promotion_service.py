from video_agent.application.policy_promotion_service import PolicyPromotionService


def test_policy_promotion_requires_quality_gain_without_success_regression() -> None:
    service = PolicyPromotionService()

    decision = service.evaluate_promotion(
        baseline={"final_success_rate": 0.92, "accepted_quality_rate": 0.70},
        challenger={"final_success_rate": 0.92, "accepted_quality_rate": 0.76},
    )

    assert decision.approved is True
    assert decision.reasons == []
    assert decision.deltas["accepted_quality_rate"] > 0.0


def test_policy_promotion_rejects_success_regression() -> None:
    service = PolicyPromotionService()

    decision = service.evaluate_promotion(
        baseline={"final_success_rate": 0.92, "accepted_quality_rate": 0.70},
        challenger={"final_success_rate": 0.88, "accepted_quality_rate": 0.80},
    )

    assert decision.approved is False
    assert "success_rate_regressed" in decision.reasons


def test_policy_promotion_rejects_must_fix_regression_even_when_quality_improves() -> None:
    service = PolicyPromotionService()

    decision = service.evaluate_promotion(
        baseline={
            "final_success_rate": 0.93,
            "accepted_quality_rate": 0.72,
            "must_fix_issue_rate": 0.05,
            "repair_rate": 0.20,
        },
        challenger={
            "final_success_rate": 0.93,
            "accepted_quality_rate": 0.78,
            "must_fix_issue_rate": 0.20,
            "repair_rate": 0.20,
        },
    )

    assert decision.approved is False
    assert "must_fix_issue_rate_regressed" in decision.reasons
