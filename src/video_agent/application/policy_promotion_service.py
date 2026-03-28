from __future__ import annotations


class PolicyPromotionService:
    def should_promote(self, *, baseline: dict[str, float], challenger: dict[str, float]) -> bool:
        return (
            challenger.get("final_success_rate", 0.0) >= baseline.get("final_success_rate", 0.0)
            and challenger.get("accepted_quality_rate", 0.0) > baseline.get("accepted_quality_rate", 0.0)
        )
