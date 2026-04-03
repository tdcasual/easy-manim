from __future__ import annotations

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.errors import AdmissionControlError
from video_agent.application.review_bundle_builder import ReviewBundleBuilder
from video_agent.application.task_service import TaskService
from video_agent.application.workflow_collaboration_service import WorkflowCollaborationService
from video_agent.application.workflow_loop_policy import WorkflowLoopPolicy
from video_agent.domain.review_workflow_models import (
    ReviewBundle,
    ReviewDecision,
    ReviewDecisionOutcome,
    WorkflowMemoryState,
)


class MultiAgentWorkflowService:
    def __init__(
        self,
        *,
        enabled: bool,
        bundle_builder: ReviewBundleBuilder,
        collaboration_service: WorkflowCollaborationService,
        task_service: TaskService,
        policy: WorkflowLoopPolicy,
    ) -> None:
        self.enabled = enabled
        self.bundle_builder = bundle_builder
        self.collaboration_service = collaboration_service
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
        pin_workflow_memory_ids: list[str] | None = None,
        unpin_workflow_memory_ids: list[str] | None = None,
        agent_principal: AgentPrincipal | None = None,
    ) -> ReviewDecisionOutcome:
        if not self.enabled:
            raise AdmissionControlError(
                code="multi_agent_workflow_disabled",
                message="Multi-agent workflow is disabled",
            )

        bundle = self.get_review_bundle(task_id=task_id, agent_principal=agent_principal)
        action = self.policy.choose_action(bundle, review_decision)
        authorization = self.collaboration_service.authorize_review_decision(task_id, agent_principal)
        actor_agent_id = authorization.actor_agent_id
        owner_submission = authorization.owner_submission
        workflow_memory_state = self._apply_workflow_memory_updates(
            task_id=task_id,
            owner_submission=owner_submission,
            pin_workflow_memory_ids=pin_workflow_memory_ids,
            unpin_workflow_memory_ids=unpin_workflow_memory_ids,
            agent_principal=agent_principal,
        )

        if action == "accept":
            if owner_submission:
                self.task_service.accept_best_version(task_id, agent_principal=agent_principal)
            else:
                self.collaboration_service.accept_best_version(
                    task_id,
                    actor_agent_id=actor_agent_id,
                )
            return ReviewDecisionOutcome(
                task_id=task_id,
                root_task_id=bundle.root_task_id,
                action="accept",
                created_task_id=None,
                reason="winner_selected",
                workflow_memory_state=workflow_memory_state,
                refresh_scope="task_and_panel",
                refresh_task_id=task_id,
            )

        if action == "retry":
            if owner_submission:
                created = self.task_service.retry_video_task(
                    task_id,
                    session_id=session_id,
                    agent_principal=agent_principal,
                )
            else:
                created = self.collaboration_service.retry_video_task(
                    task_id,
                    actor_agent_id=actor_agent_id,
                    session_id=session_id,
                )
            return ReviewDecisionOutcome(
                task_id=task_id,
                root_task_id=bundle.root_task_id,
                action="retry",
                created_task_id=created.task_id,
                reason="retry_created",
                workflow_memory_state=workflow_memory_state,
                refresh_scope="navigate",
                refresh_task_id=created.task_id,
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
            if owner_submission:
                created = self.task_service.revise_video_task(
                    task_id,
                    feedback=feedback,
                    preserve_working_parts=review_decision.preserve_working_parts,
                    session_id=session_id,
                    memory_ids=memory_ids,
                    agent_principal=agent_principal,
                )
            else:
                created = self.collaboration_service.revise_video_task(
                    task_id,
                    feedback=feedback,
                    actor_agent_id=actor_agent_id,
                    preserve_working_parts=review_decision.preserve_working_parts,
                    session_id=session_id,
                    memory_ids=memory_ids,
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
                workflow_memory_state=workflow_memory_state,
                refresh_scope="navigate",
                refresh_task_id=created.task_id,
            )

        return ReviewDecisionOutcome(
            task_id=task_id,
            root_task_id=bundle.root_task_id,
            action="escalate",
            created_task_id=None,
            reason=self._escalation_reason(bundle=bundle, review_decision=review_decision),
            workflow_memory_state=workflow_memory_state,
            refresh_scope="panel_only",
            refresh_task_id=task_id,
        )

    def _apply_workflow_memory_updates(
        self,
        *,
        task_id: str,
        owner_submission: bool,
        pin_workflow_memory_ids: list[str] | None,
        unpin_workflow_memory_ids: list[str] | None,
        agent_principal: AgentPrincipal | None,
    ) -> WorkflowMemoryState | None:
        if not (pin_workflow_memory_ids or unpin_workflow_memory_ids):
            return None
        if not owner_submission:
            raise PermissionError("agent_access_denied")
        return self.collaboration_service.apply_workflow_memory_updates(
            task_id,
            pin_memory_ids=pin_workflow_memory_ids,
            unpin_memory_ids=unpin_workflow_memory_ids,
            agent_principal=agent_principal,
        )

    def _escalation_reason(self, *, bundle: ReviewBundle, review_decision: ReviewDecision) -> str:
        if bundle.child_attempt_count >= self.policy.settings.multi_agent_workflow_max_child_attempts:
            return "workflow_budget_exhausted"
        if review_decision.resolved_decision() == "accept":
            return "acceptance_blocked"
        if review_decision.resolved_decision() == "repair":
            return "repair_hint_missing"
        return "workflow_budget_exhausted"
