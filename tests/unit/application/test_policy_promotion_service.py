from video_agent.application.policy_promotion_service import PolicyPromotionService


def test_policy_promotion_requires_quality_gain_without_success_regression() -> None:
    service = PolicyPromotionService()

    approved = service.should_promote(
        baseline={"final_success_rate": 0.92, "accepted_quality_rate": 0.70},
        challenger={"final_success_rate": 0.92, "accepted_quality_rate": 0.76},
    )

    assert approved is True


def test_policy_promotion_rejects_success_regression() -> None:
    service = PolicyPromotionService()

    approved = service.should_promote(
        baseline={"final_success_rate": 0.92, "accepted_quality_rate": 0.70},
        challenger={"final_success_rate": 0.88, "accepted_quality_rate": 0.80},
    )

    assert approved is False
