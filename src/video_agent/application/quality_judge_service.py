from __future__ import annotations

from video_agent.domain.quality_models import QualityScorecard


class QualityJudgeService:
    def __init__(self, min_score: float) -> None:
        self.min_score = min_score

    def score(
        self,
        *,
        status: str,
        issue_codes: list[str],
        preview_issue_codes: list[str],
        summary: str | None,
    ) -> QualityScorecard:
        motion = 0.4 if "static_previews" in preview_issue_codes else 0.9
        prompt_alignment = 0.7 if issue_codes else 0.9
        visual_clarity = 0.7 if preview_issue_codes else 0.9
        total = round(
            (
                (1.0 if status == "completed" else 0.5)
                + motion
                + prompt_alignment
                + visual_clarity
            )
            / 4,
            4,
        )
        must_fix = [code for code in issue_codes if code in {"static_previews", "near_blank_preview"}]
        return QualityScorecard(
            overall_score=total,
            dimensions={
                "motion_smoothness": motion,
                "prompt_alignment": prompt_alignment,
                "visual_clarity": visual_clarity,
            },
            total_score=total,
            dimension_scores={
                "motion_smoothness": motion,
                "prompt_alignment": prompt_alignment,
                "visual_clarity": visual_clarity,
            },
            must_fix_issues=must_fix,
            accepted=total >= self.min_score,
            summary=summary,
            decision="accept" if total >= self.min_score else "needs_revision",
            warning_codes=list(preview_issue_codes),
        )
