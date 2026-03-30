from __future__ import annotations

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.errors import AdmissionControlError
from video_agent.application.review_bundle_builder import ReviewBundleBuilder
from video_agent.application.task_service import TaskService
from video_agent.application.workflow_loop_policy import WorkflowLoopPolicy
from video_agent.domain.review_workflow_models import ReviewBundle, ReviewDecision, ReviewDecisionOutcome


class MultiAgentWorkflowService:
    def __init__(
        self,
        *,
        enabled: bool,
        bundle_builder: ReviewBundleBuilder,
        task_service: TaskService,
        policy: WorkflowLoopPolicy,
    ) -> None:
        self.enabled = enabled
        self.bundle_builder = bundle_builder
        self.task_service = task_service
        self.policy = policy

    def get_review_bundle(
        self,
        task_id: str,
        agent_principal: AgentPrincipal | None = None,
    ) -> ReviewBundle:
        return self.bundle_builder.build(task_id=task_id, agent_principal=agent_principal)

    def apply_review_decision(
        self,
        task_id: str,
        review_decision: ReviewDecision,
        session_id: str | None = None,
        memory_ids: list[str] | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> ReviewDecisionOutcome:
        if not self.enabled:
            raise AdmissionControlError(
                code="multi_agent_workflow_disabled",
                message="Multi-agent workflow is disabled",
            )

        bundle = self.get_review_bundle(task_id=task_id, agent_principal=agent_principal)
        action = self.policy.choose_action(bundle, review_decision)

        if action == "accept":
            self.task_service.accept_best_version(task_id, agent_principal=agent_principal)
            return ReviewDecisionOutcome(
                task_id=task_id,
                root_task_id=bundle.root_task_id,
                action="accept",
                created_task_id=None,
                reason="winner_selected",
            )

        if action == "retry":
            created = self.task_service.retry_video_task(
                task_id,
                session_id=session_id,
                agent_principal=agent_principal,
            )
            return ReviewDecisionOutcome(
                task_id=task_id,
                root_task_id=bundle.root_task_id,
                action="retry",
                created_task_id=created.task_id,
                reason="retry_created",
            )

        if action == "revise":
            from_repair_hint = review_decision.resolved_decision() == "repair"
            feedback = (
                review_decision.feedback
                or (
                    None
                    if review_decision.collaboration is None
                    else review_decision.collaboration.repairer_execution_hint.execution_hint
                )
                or review_decision.summary
            )
            created = self.task_service.revise_video_task(
                task_id,
                feedback=feedback,
                preserve_working_parts=review_decision.preserve_working_parts,
                session_id=session_id,
                memory_ids=memory_ids,
                agent_principal=agent_principal,
            )
            return ReviewDecisionOutcome(
                task_id=task_id,
                root_task_id=bundle.root_task_id,
                action="revise",
                created_task_id=created.task_id,
                reason=(
                    "challenger_created"
                    if bundle.status == "completed" and bundle.selected_task_id == task_id
                    else "revision_created_from_repair_hint"
                    if from_repair_hint
                    else "revision_created"
                ),
            )

        return ReviewDecisionOutcome(
            task_id=task_id,
            root_task_id=bundle.root_task_id,
            action="escalate",
            created_task_id=None,
            reason=self._escalation_reason(bundle=bundle, review_decision=review_decision),
        )

    def _escalation_reason(self, *, bundle: ReviewBundle, review_decision: ReviewDecision) -> str:
        if bundle.child_attempt_count >= self.policy.settings.multi_agent_workflow_max_child_attempts:
            return "workflow_budget_exhausted"
        if review_decision.resolved_decision() == "accept":
            return "acceptance_blocked"
        if review_decision.resolved_decision() == "repair":
            return "repair_hint_missing"
        return "workflow_budget_exhausted"
