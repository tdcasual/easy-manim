from __future__ import annotations

from video_agent.config import Settings
from video_agent.domain.review_workflow_models import ReviewBundle, ReviewDecision


class WorkflowLoopPolicy:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def choose_action(self, bundle: ReviewBundle, review_decision: ReviewDecision) -> str:
        if review_decision.decision == "accept":
            if self.settings.multi_agent_workflow_require_completed_for_accept and bundle.status != "completed":
                return "escalate"
            return "accept"

        if bundle.child_attempt_count >= self.settings.multi_agent_workflow_max_child_attempts:
            return "escalate"

        if review_decision.decision == "repair":
            return "revise"

        return review_decision.decision
