from __future__ import annotations

from video_agent.config import Settings
from video_agent.domain.review_workflow_models import ReviewBundle, ReviewDecision


class WorkflowLoopPolicy:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def choose_action(self, bundle: ReviewBundle, review_decision: ReviewDecision) -> str:
        normalized_decision = review_decision.resolved_decision()

        if normalized_decision == "accept":
            if self._accept_is_blocked(bundle):
                return "escalate"
            return "accept"

        if bundle.child_attempt_count >= self.settings.multi_agent_workflow_max_child_attempts:
            return "escalate"

        if normalized_decision == "repair":
            if self._has_repair_execution_hint(review_decision):
                return "revise"
            return "escalate"

        return normalized_decision

    def _accept_is_blocked(self, bundle: ReviewBundle) -> bool:
        if self.settings.multi_agent_workflow_require_completed_for_accept and bundle.status != "completed":
            return True
        if bundle.quality_gate_status is not None and bundle.quality_gate_status != "accepted":
            return True
        if bundle.acceptance_blockers:
            return True
        return False

    @staticmethod
    def _has_repair_execution_hint(review_decision: ReviewDecision) -> bool:
        collaboration = review_decision.collaboration
        if collaboration is None:
            return False
        return bool((collaboration.repairer_execution_hint.execution_hint or "").strip())
