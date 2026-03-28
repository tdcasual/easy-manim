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
            return ReviewDecisionOutcome(
                task_id=task_id,
                root_task_id=bundle.root_task_id,
                action="accept",
                created_task_id=None,
                reason="accepted",
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
            created = self.task_service.revise_video_task(
                task_id,
                feedback=review_decision.feedback or review_decision.summary,
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
                reason="revision_created",
            )

        return ReviewDecisionOutcome(
            task_id=task_id,
            root_task_id=bundle.root_task_id,
            action="escalate",
            created_task_id=None,
            reason="workflow_budget_exhausted",
        )
