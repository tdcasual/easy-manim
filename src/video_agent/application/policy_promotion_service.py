from __future__ import annotations

from video_agent.config import Settings
from video_agent.domain.strategy_models import StrategyPromotionDecision


class PolicyPromotionService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

    def evaluate_promotion(
        self,
        *,
        baseline: dict[str, float],
        challenger: dict[str, float],
    ) -> StrategyPromotionDecision:
        success_delta = float(challenger.get("final_success_rate", 0.0) or 0.0) - float(
            baseline.get("final_success_rate", 0.0) or 0.0
        )
        quality_delta = float(challenger.get("accepted_quality_rate", 0.0) or 0.0) - float(
            baseline.get("accepted_quality_rate", 0.0) or 0.0
        )
        must_fix_delta = float(challenger.get("must_fix_issue_rate", 0.0) or 0.0) - float(
            baseline.get("must_fix_issue_rate", 0.0) or 0.0
        )
        repair_delta = float(challenger.get("repair_rate", 0.0) or 0.0) - float(
            baseline.get("repair_rate", 0.0) or 0.0
        )

        reasons: list[str] = []
        if success_delta < -self.settings.strategy_promotion_max_success_regression:
            reasons.append("success_rate_regressed")
        if quality_delta < self.settings.strategy_promotion_min_quality_gain:
            reasons.append("quality_gain_too_small")
        if must_fix_delta > 0.0:
            reasons.append("must_fix_issue_rate_regressed")
        if float(challenger.get("must_fix_issue_rate", 0.0) or 0.0) > self.settings.strategy_promotion_max_must_fix_issue_rate:
            reasons.append("must_fix_issue_rate_too_high")
        if repair_delta > self.settings.strategy_promotion_max_repair_rate_regression:
            reasons.append("repair_rate_regressed")

        return StrategyPromotionDecision(
            approved=not reasons,
            reasons=reasons,
            deltas={
                "final_success_rate": round(success_delta, 6),
                "accepted_quality_rate": round(quality_delta, 6),
                "must_fix_issue_rate": round(must_fix_delta, 6),
                "repair_rate": round(repair_delta, 6),
            },
        )

    def should_promote(self, *, baseline: dict[str, float], challenger: dict[str, float]) -> bool:
        return self.evaluate_promotion(baseline=baseline, challenger=challenger).approved
