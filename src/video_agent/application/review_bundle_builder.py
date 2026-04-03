from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.branch_arbitration import build_arbitration_summary, build_branch_scoreboard
from video_agent.application.case_memory_service import CaseMemoryService
from video_agent.application.session_memory_service import SessionMemoryService
from video_agent.application.task_service import TaskService
from video_agent.application.workflow_collaboration_service import WorkflowCollaborationService
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.review_workflow_models import (
    CollaborationSection,
    CollaborationSections,
    ReviewBundle,
    WorkflowAppliedActionFeedback,
    WorkflowAvailableActionCard,
    WorkflowAvailableActions,
    WorkflowAvailableActionSection,
    WorkflowAvailableActionSections,
    WorkflowAvailableActionIntent,
    WorkflowAvailableActionMemoryChange,
    WorkflowMemoryActionContract,
    WorkflowMemoryActionExample,
    WorkflowMemoryRecommendations,
    WorkflowMemoryState,
    WorkflowReviewPanelBadge,
    WorkflowReviewPanelEvent,
    WorkflowReviewPanelHeader,
    WorkflowReviewRenderContract,
    WorkflowReviewSectionPresentation,
    WorkflowReviewStatusSummary,
    WorkflowSuggestedAction,
    WorkflowSuggestedNextActions,
    WorkflowReviewControls,
)


class ReviewBundleBuilder:
    def __init__(
        self,
        *,
        task_service: TaskService,
        collaboration_service: WorkflowCollaborationService,
        store: SQLiteTaskStore,
        session_memory_service: SessionMemoryService | None,
        case_memory_service: CaseMemoryService | None = None,
    ) -> None:
        self.task_service = task_service
        self.collaboration_service = collaboration_service
        self.store = store
        self.session_memory_service = session_memory_service
        self.case_memory_service = case_memory_service or getattr(task_service, "case_memory_service", None)

    def build(self, task_id: str, agent_principal: AgentPrincipal | None = None) -> ReviewBundle:
        if agent_principal is None:
            snapshot = self.task_service.get_video_task(task_id)
            result = self.task_service.get_video_result(task_id)
            events = self.task_service.get_task_events(task_id)
            task = self.store.get_task(task_id)
        else:
            task = self.collaboration_service.require_workflow_access(
                task_id,
                agent_principal.agent_id,
                capability="review_bundle:read",
            )
            snapshot = self.task_service.get_video_task(task_id)
            result = self.task_service.get_video_result(task_id)
            events = self.task_service.get_task_events(task_id)
        owner_visible = agent_principal is None or (
            task is not None
            and agent_principal.agent_id == task.agent_id
        )
        session_memory_summary = ""
        if (
            task is not None
            and task.session_id is not None
            and self.session_memory_service is not None
        ):
            session_memory_summary = self.session_memory_service.summarize_session_memory(task.session_id).summary_text

        child_attempt_count = 0
        if snapshot.root_task_id is not None:
            child_attempt_count = max(0, self.store.count_lineage_tasks(snapshot.root_task_id) - 1)
        root_task_id = snapshot.root_task_id or snapshot.task_id
        root_task = self.store.get_task(root_task_id)
        delivery_case = self.store.get_delivery_case_by_root_task_id(root_task_id)
        lineage_tasks = self.store.list_lineage_tasks(root_task_id)
        branch_candidates = [
            {
                "task_id": lineage_task.task_id,
                "parent_task_id": lineage_task.parent_task_id,
                "branch_kind": lineage_task.branch_kind,
                "status": lineage_task.status.value,
                "phase": lineage_task.phase.value,
                "delivery_status": lineage_task.delivery_status,
                "quality_gate_status": lineage_task.quality_gate_status,
                "accepted_as_best": lineage_task.accepted_as_best,
                "accepted_version_rank": lineage_task.accepted_version_rank,
                "completion_mode": lineage_task.completion_mode,
            }
            for lineage_task in lineage_tasks
        ]
        selected_task_id = None if delivery_case is None else delivery_case.selected_task_id
        active_task_id = None if delivery_case is None else delivery_case.active_task_id
        scorecards_by_task_id = {
            lineage_task.task_id: self._get_quality_scorecard_json(lineage_task.task_id, agent_principal)
            for lineage_task in lineage_tasks
        }
        branch_scoreboard = build_branch_scoreboard(
            lineage_tasks=lineage_tasks,
            scorecards_by_task_id=scorecards_by_task_id,
            selected_task_id=selected_task_id,
            active_task_id=active_task_id,
        )
        arbitration_summary = build_arbitration_summary(
            branch_scoreboard=branch_scoreboard,
            selected_task_id=selected_task_id,
            active_task_id=active_task_id,
        )
        recent_agent_runs: list[dict[str, Any]] = []
        if delivery_case is not None:
            recent_agent_runs = [
                run.model_dump(mode="json")
                for run in self.store.list_agent_runs(delivery_case.case_id)[-10:]
            ]
        case_memory = {}
        if self.case_memory_service is not None:
            case_memory = self.case_memory_service.get_case_memory(root_task_id)

        recovery_plan = self.task_service.get_recovery_plan(snapshot.task_id)
        planner_summary = ""
        if recovery_plan:
            planner_summary = str(recovery_plan.get("selected_action") or "").strip()
        if not planner_summary and snapshot.failure_contract:
            planner_summary = str(snapshot.failure_contract.get("recommended_action") or "").strip()

        reviewer_summary = str(snapshot.latest_validation_summary.get("summary") or "").strip()
        repair_hint: str | None = None
        if recovery_plan:
            repair_hint = str(recovery_plan.get("repair_recipe") or "").strip() or None
        if not repair_hint and snapshot.failure_contract:
            repair_hint = str(snapshot.failure_contract.get("repair_strategy") or "").strip() or None
        quality_scorecard_json = self._get_quality_scorecard_json(snapshot.task_id, agent_principal)
        must_fix_issue_codes = self._must_fix_issue_codes(quality_scorecard_json)
        acceptance_blockers = self._acceptance_blockers(
            status=snapshot.status.value,
            quality_gate_status=snapshot.quality_gate_status,
            must_fix_issue_codes=must_fix_issue_codes,
            latest_validation_summary=snapshot.latest_validation_summary,
            failure_contract=snapshot.failure_contract,
        )
        decision_trace = self._decision_trace(
            status=snapshot.status.value,
            quality_gate_status=snapshot.quality_gate_status,
            must_fix_issue_codes=must_fix_issue_codes,
            latest_validation_summary=snapshot.latest_validation_summary,
            failure_contract=snapshot.failure_contract,
            recovery_plan=recovery_plan,
        )
        collaboration_summary = self.collaboration_service.build_workflow_summary(snapshot.task_id)
        collaboration_memory_context = self.collaboration_service.build_workflow_memory_context(snapshot.task_id)
        workflow_memory_recommendations = (
            self.collaboration_service.list_workflow_memory_recommendations(
                snapshot.task_id,
                agent_principal=agent_principal,
            )
            if owner_visible
            else None
        )
        workflow_memory_action_contract = self._build_workflow_memory_action_contract(
            workflow_memory_recommendations
        )
        workflow_review_controls = self._build_workflow_review_controls(
            root_task_id=root_task_id,
            owner_visible=owner_visible,
            status=snapshot.status.value,
            acceptance_blockers=acceptance_blockers,
            collaboration_summary=collaboration_summary,
            workflow_memory_recommendations=workflow_memory_recommendations,
            workflow_memory_action_contract=workflow_memory_action_contract,
        )

        return ReviewBundle(
            task_id=snapshot.task_id,
            root_task_id=snapshot.root_task_id,
            attempt_count=snapshot.attempt_count,
            child_attempt_count=child_attempt_count,
            prompt="" if task is None else task.prompt,
            feedback=None if task is None else task.feedback,
            display_title=snapshot.display_title,
            status=snapshot.status.value,
            phase=snapshot.phase.value,
            latest_validation_summary=snapshot.latest_validation_summary,
            failure_contract=snapshot.failure_contract,
            scene_spec=self.task_service.get_scene_spec(snapshot.task_id),
            recovery_plan=recovery_plan,
            quality_scorecard=quality_scorecard_json,
            quality_gate_status=snapshot.quality_gate_status,
            must_fix_issue_codes=must_fix_issue_codes,
            acceptance_blockers=acceptance_blockers,
            decision_trace=decision_trace,
            task_events=events,
            session_memory_summary=session_memory_summary or "",
            case_memory=case_memory,
            case_status=None if delivery_case is None else delivery_case.status,
            active_task_id=active_task_id,
            selected_task_id=selected_task_id,
            branch_candidates=branch_candidates,
            branch_scoreboard=branch_scoreboard,
            arbitration_summary=arbitration_summary,
            recent_agent_runs=recent_agent_runs,
            video_resource=result.video_resource,
            preview_frame_resources=result.preview_frame_resources,
            script_resource=result.script_resource,
            validation_report_resource=result.validation_report_resource,
            collaboration=CollaborationSections(
                planner_recommendation=CollaborationSection(
                    role="planner",
                    summary=planner_summary,
                ),
                reviewer_decision=CollaborationSection(
                    role="reviewer",
                    summary=reviewer_summary,
                ),
                repairer_execution_hint=CollaborationSection(
                    role="repairer",
                    execution_hint=repair_hint,
                ),
            ),
            collaboration_summary=collaboration_summary,
            collaboration_memory_context=collaboration_memory_context,
            workflow_memory_recommendations=workflow_memory_recommendations,
            workflow_memory_action_contract=workflow_memory_action_contract,
            workflow_review_controls=workflow_review_controls,
        )

    def _get_quality_scorecard_json(
        self,
        task_id: str,
        agent_principal: AgentPrincipal | None,
    ) -> dict[str, Any] | None:
        if agent_principal is not None:
            self.collaboration_service.require_workflow_access(
                task_id,
                agent_principal.agent_id,
                capability="review_bundle:read",
            )
        quality_scorecard = self.task_service.get_quality_score(task_id)
        if quality_scorecard is None:
            return None
        if isinstance(quality_scorecard, dict):
            return dict(quality_scorecard)
        return quality_scorecard.model_dump(mode="json")

    @staticmethod
    def _must_fix_issue_codes(quality_scorecard: dict[str, Any] | None) -> list[str]:
        if not isinstance(quality_scorecard, dict):
            return []
        return [
            str(item)
            for item in quality_scorecard.get("must_fix_issues", []) or []
            if str(item).strip()
        ]

    @classmethod
    def _acceptance_blockers(
        cls,
        *,
        status: str,
        quality_gate_status: str | None,
        must_fix_issue_codes: list[str],
        latest_validation_summary: dict[str, Any],
        failure_contract: dict[str, Any] | None,
    ) -> list[str]:
        blockers: list[str] = []
        if status != "completed":
            blockers.append("task_not_completed")
        if quality_gate_status and quality_gate_status != "accepted":
            blockers.append("quality_gate_not_accepted")
        if must_fix_issue_codes:
            blockers.append("must_fix_issue_codes")
        if cls._unresolved_validation_issue_codes(latest_validation_summary):
            blockers.append("unresolved_validation_issues")
        if isinstance(failure_contract, dict) and str(failure_contract.get("recommended_action") or "").strip():
            blockers.append("failure_contract_active")
        return blockers

    @classmethod
    def _decision_trace(
        cls,
        *,
        status: str,
        quality_gate_status: str | None,
        must_fix_issue_codes: list[str],
        latest_validation_summary: dict[str, Any],
        failure_contract: dict[str, Any] | None,
        recovery_plan: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "quality_gate_status": quality_gate_status,
            "must_fix_issue_codes": list(must_fix_issue_codes),
            "unresolved_validation_issue_codes": cls._unresolved_validation_issue_codes(latest_validation_summary),
            "failure_recommended_action": None
            if not isinstance(failure_contract, dict)
            else str(failure_contract.get("recommended_action") or "").strip() or None,
            "recovery_selected_action": None
            if not isinstance(recovery_plan, dict)
            else str(recovery_plan.get("selected_action") or "").strip() or None,
        }

    @classmethod
    def _build_workflow_memory_action_contract(
        cls,
        recommendations: WorkflowMemoryRecommendations | None,
    ) -> WorkflowMemoryActionContract | None:
        if recommendations is None:
            return None

        pinned_ids = list(recommendations.pinned_memory_ids)
        candidate_pin_ids: list[str] = []
        for item in recommendations.items:
            if item.pinned or not item.memory_id:
                continue
            if item.memory_id not in candidate_pin_ids:
                candidate_pin_ids.append(item.memory_id)

        examples: list[WorkflowMemoryActionExample] = []
        if candidate_pin_ids:
            examples.append(
                WorkflowMemoryActionExample(
                    name="pin",
                    summary="Pin one or more recommended workflow memories before the next revision.",
                    payload=cls._workflow_memory_action_payload(
                        summary="Pin recommended workflow memory before revising",
                        feedback="Use the refreshed workflow memory in the next revision.",
                        pin_ids=candidate_pin_ids[:2],
                    ),
                )
            )
        if pinned_ids:
            examples.append(
                WorkflowMemoryActionExample(
                    name="unpin",
                    summary="Remove outdated workflow memories while keeping the review decision flow unchanged.",
                    payload=cls._workflow_memory_action_payload(
                        summary="Remove outdated workflow memory before revising",
                        feedback="Continue with the current revision goals after dropping stale shared memory.",
                        unpin_ids=pinned_ids[:2],
                    ),
                )
            )
        if candidate_pin_ids and pinned_ids:
            examples.append(
                WorkflowMemoryActionExample(
                    name="replace",
                    summary="Swap pinned workflow memory in a single review-decision request.",
                    payload=cls._workflow_memory_action_payload(
                        summary="Replace workflow memory set before revising",
                        feedback="Use the refreshed shared memory set for the next revision.",
                        pin_ids=candidate_pin_ids[:2],
                        unpin_ids=pinned_ids[:2],
                    ),
                )
            )
        return WorkflowMemoryActionContract(examples=examples)

    @staticmethod
    def _parse_created_at(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    def _build_workflow_review_controls(
        self,
        *,
        root_task_id: str,
        owner_visible: bool,
        status: str,
        acceptance_blockers: list[str],
        collaboration_summary: Any,
        workflow_memory_recommendations: WorkflowMemoryRecommendations | None,
        workflow_memory_action_contract: WorkflowMemoryActionContract | None,
    ) -> WorkflowReviewControls | None:
        if not owner_visible:
            return None
        root_task = self.store.get_task(root_task_id)
        if root_task is None:
            return None
        recent_memory_events = [
            event
            for event in collaboration_summary.recent_events
            if event.event_type in {"workflow_memory_pinned", "workflow_memory_unpinned"}
        ]
        suggested_next_actions = self._build_suggested_next_actions(
            status=status,
            acceptance_blockers=acceptance_blockers,
            workflow_memory_recommendations=workflow_memory_recommendations,
            workflow_memory_action_contract=workflow_memory_action_contract,
        )
        available_actions = self._build_available_actions(suggested_next_actions)
        action_sections = self._build_action_sections(available_actions)
        status_summary = self._build_workflow_review_status_summary(
            acceptance_blockers=acceptance_blockers,
            pinned_memory_ids=list(root_task.selected_memory_ids),
            recent_memory_events=recent_memory_events,
            suggested_next_actions=suggested_next_actions,
            workflow_memory_recommendations=workflow_memory_recommendations,
        )
        panel_header = self._build_panel_header(
            recent_memory_events=recent_memory_events,
            status_summary=status_summary,
        )
        applied_action_feedback = self._build_applied_action_feedback(
            recent_memory_events=recent_memory_events,
            status_summary=status_summary,
        )
        render_contract = self._build_render_contract(
            panel_header=panel_header,
            action_sections=action_sections,
            status_summary=status_summary,
            applied_action_feedback=applied_action_feedback,
        )
        return WorkflowReviewControls(
            can_manage_workflow_memory=True,
            workflow_memory_state=WorkflowMemoryState(
                root_task_id=root_task.task_id,
                pinned_memory_ids=list(root_task.selected_memory_ids),
                persistent_memory_context_summary=root_task.persistent_memory_context_summary,
                persistent_memory_context_digest=root_task.persistent_memory_context_digest,
            ),
            recent_memory_events=recent_memory_events,
            workflow_memory_recommendations=workflow_memory_recommendations,
            workflow_memory_action_contract=workflow_memory_action_contract,
            suggested_next_actions=suggested_next_actions,
            available_actions=available_actions,
            action_sections=action_sections,
            panel_header=panel_header,
            applied_action_feedback=applied_action_feedback,
            status_summary=status_summary,
            render_contract=render_contract,
        )

    def _build_suggested_next_actions(
        self,
        *,
        status: str,
        acceptance_blockers: list[str],
        workflow_memory_recommendations: WorkflowMemoryRecommendations | None,
        workflow_memory_action_contract: WorkflowMemoryActionContract | None,
    ) -> WorkflowSuggestedNextActions:
        examples_by_name = {
            example.name: example
            for example in (workflow_memory_action_contract.examples if workflow_memory_action_contract else [])
        }
        unpinned_ids = []
        if workflow_memory_recommendations is not None:
            unpinned_ids = [
                item.memory_id
                for item in workflow_memory_recommendations.items
                if item.memory_id and not item.pinned
            ]

        blocked_accept_action = WorkflowSuggestedAction(
            action_id="accept",
            title="Accept current result",
            summary="Acceptance is currently blocked by the workflow state.",
            blocked=True,
            reasons=list(acceptance_blockers),
            payload={
                "review_decision": {
                    "decision": "accept",
                    "summary": "Accept current result",
                }
            },
        )

        if status == "completed" and not acceptance_blockers:
            return WorkflowSuggestedNextActions(
                primary=WorkflowSuggestedAction(
                    action_id="accept",
                    title="Accept current result",
                    summary="The current result is ready to be accepted as the best version.",
                    blocked=False,
                    reasons=[],
                    payload={
                        "review_decision": {
                            "decision": "accept",
                            "summary": "Accept current result",
                        }
                    },
                ),
                alternatives=[],
            )

        if unpinned_ids and "pin" in examples_by_name:
            alternatives: list[WorkflowSuggestedAction] = [
                WorkflowSuggestedAction(
                    action_id="revise",
                    title="Revise with current memory",
                    summary="Create another revision without changing the shared workflow memory set.",
                    payload=self._workflow_memory_action_payload(
                        summary="Revise with current workflow memory",
                        feedback="Continue iterating on the current task.",
                    ),
                )
            ]
            if acceptance_blockers:
                alternatives.append(blocked_accept_action)
            return WorkflowSuggestedNextActions(
                primary=WorkflowSuggestedAction(
                    action_id="pin_and_revise",
                    title="Pin suggested memory and revise",
                    summary="Attach the most relevant shared workflow memory before creating the next revision.",
                    reasons=["workflow_memory_recommendations_available"],
                    payload=dict(examples_by_name["pin"].payload),
                ),
                alternatives=alternatives,
            )

        if status == "failed":
            alternatives = [blocked_accept_action] if acceptance_blockers else []
            return WorkflowSuggestedNextActions(
                primary=WorkflowSuggestedAction(
                    action_id="retry",
                    title="Retry generation",
                    summary="The current task failed, so the safest next step is a retry.",
                    payload={
                        "review_decision": {
                            "decision": "retry",
                            "summary": "Retry failed task",
                        }
                    },
                ),
                alternatives=alternatives,
            )

        alternatives = [blocked_accept_action] if acceptance_blockers else []
        return WorkflowSuggestedNextActions(
            primary=WorkflowSuggestedAction(
                action_id="revise",
                title="Create another revision",
                summary="Keep iterating on the current task with the existing workflow memory set.",
                payload=self._workflow_memory_action_payload(
                    summary="Create another revision",
                    feedback="Continue iterating on the current task.",
                ),
            ),
            alternatives=alternatives,
        )

    @classmethod
    def _build_available_actions(
        cls,
        suggested_next_actions: WorkflowSuggestedNextActions | None,
    ) -> WorkflowAvailableActions | None:
        if suggested_next_actions is None:
            return None

        action_items: list[WorkflowAvailableActionCard] = []
        seen_action_ids: set[str] = set()
        ordered_actions: list[tuple[WorkflowSuggestedAction, bool]] = []
        if suggested_next_actions.primary is not None:
            ordered_actions.append((suggested_next_actions.primary, True))
        ordered_actions.extend((item, False) for item in suggested_next_actions.alternatives)

        for action, is_primary in ordered_actions:
            if action.action_id in seen_action_ids:
                continue
            seen_action_ids.add(action.action_id)
            intent = cls._build_action_intent(action.payload)
            action_items.append(
                WorkflowAvailableActionCard(
                    action_id=action.action_id,
                    title=action.title,
                    button_label=cls._button_label_for_action(action.action_id),
                    action_family=cls._resolve_action_family(intent),
                    summary=action.summary,
                    blocked=action.blocked,
                    reasons=list(action.reasons),
                    is_primary=is_primary,
                    intent=intent,
                    payload=dict(action.payload),
                )
            )

        return WorkflowAvailableActions(items=action_items)

    @staticmethod
    def _build_action_sections(
        available_actions: WorkflowAvailableActions | None,
    ) -> WorkflowAvailableActionSections | None:
        if available_actions is None:
            return None

        recommended_items = [item for item in available_actions.items if item.is_primary]
        available_items = [item for item in available_actions.items if not item.is_primary and not item.blocked]
        blocked_items = [item for item in available_actions.items if item.blocked]

        sections: list[WorkflowAvailableActionSection] = []
        if recommended_items:
            sections.append(
                WorkflowAvailableActionSection(
                    section_id="recommended",
                    title="Recommended next step",
                    summary="The strongest next action based on the current workflow state.",
                    items=recommended_items,
                )
            )
        if available_items:
            sections.append(
                WorkflowAvailableActionSection(
                    section_id="available",
                    title="Other available actions",
                    summary="Alternative actions that can be taken immediately.",
                    items=available_items,
                )
            )
        if blocked_items:
            sections.append(
                WorkflowAvailableActionSection(
                    section_id="blocked",
                    title="Blocked actions",
                    summary="Actions that are currently unavailable until blockers are resolved.",
                    items=blocked_items,
                )
            )
        return WorkflowAvailableActionSections(items=sections)

    @staticmethod
    def _build_workflow_review_status_summary(
        *,
        acceptance_blockers: list[str],
        pinned_memory_ids: list[str],
        recent_memory_events: list[Any],
        suggested_next_actions: WorkflowSuggestedNextActions | None,
        workflow_memory_recommendations: WorkflowMemoryRecommendations | None,
    ) -> WorkflowReviewStatusSummary:
        latest_memory_event = recent_memory_events[-1] if recent_memory_events else None
        pending_recommendation_ids: list[str] = []
        if workflow_memory_recommendations is not None:
            for item in workflow_memory_recommendations.items:
                if item.pinned or not item.memory_id:
                    continue
                if item.memory_id not in pending_recommendation_ids:
                    pending_recommendation_ids.append(item.memory_id)

        normalized_pinned_ids = [str(item) for item in pinned_memory_ids if str(item).strip()]
        primary_action_id = None
        if suggested_next_actions is not None and suggested_next_actions.primary is not None:
            primary_action_id = suggested_next_actions.primary.action_id

        return WorkflowReviewStatusSummary(
            recommended_action_id=primary_action_id,
            acceptance_ready=not acceptance_blockers,
            acceptance_blockers=list(acceptance_blockers),
            pinned_memory_count=len(normalized_pinned_ids),
            pending_memory_recommendation_count=len(pending_recommendation_ids),
            has_pending_memory_updates=bool(pending_recommendation_ids),
            latest_workflow_memory_event_type=None if latest_memory_event is None else latest_memory_event.event_type,
            latest_workflow_memory_event_at=None if latest_memory_event is None else latest_memory_event.created_at,
        )

    @classmethod
    def _build_panel_header(
        cls,
        *,
        recent_memory_events: list[Any],
        status_summary: WorkflowReviewStatusSummary | None,
    ) -> WorkflowReviewPanelHeader | None:
        if status_summary is None:
            return None

        badges: list[WorkflowReviewPanelBadge] = []
        if status_summary.recommended_action_id:
            badges.append(
                WorkflowReviewPanelBadge(
                    badge_id="recommended_action",
                    label="Recommended",
                    value=status_summary.recommended_action_id,
                    tone="ready" if status_summary.recommended_action_id == "accept" else "attention",
                )
            )
        if status_summary.pending_memory_recommendation_count > 0:
            badges.append(
                WorkflowReviewPanelBadge(
                    badge_id="pending_memory",
                    label="Pending memory",
                    value=str(status_summary.pending_memory_recommendation_count),
                    tone="attention",
                )
            )
        if status_summary.acceptance_blockers:
            badges.append(
                WorkflowReviewPanelBadge(
                    badge_id="acceptance_blockers",
                    label="Blockers",
                    value=str(len(status_summary.acceptance_blockers)),
                    tone="blocked",
                )
            )

        latest_event = recent_memory_events[-1] if recent_memory_events else None
        highlighted_event = None
        if latest_event is not None:
            highlighted_event = WorkflowReviewPanelEvent(
                event_type=latest_event.event_type,
                title=cls._panel_event_title(latest_event.event_type),
                summary="Most recent shared workflow memory change.",
                memory_id=latest_event.memory_id,
                created_at=latest_event.created_at,
            )

        return WorkflowReviewPanelHeader(
            tone=cls._panel_header_tone(status_summary),
            summary=cls._panel_header_summary(status_summary),
            badges=badges,
            highlighted_event=highlighted_event,
        )

    @staticmethod
    def _panel_header_tone(
        status_summary: WorkflowReviewStatusSummary,
    ) -> str:
        if status_summary.acceptance_ready and status_summary.recommended_action_id == "accept":
            return "ready"
        if status_summary.acceptance_blockers and status_summary.recommended_action_id is None:
            return "blocked"
        return "attention"

    @staticmethod
    def _panel_header_summary(
        status_summary: WorkflowReviewStatusSummary,
    ) -> str:
        action_id = status_summary.recommended_action_id
        if action_id == "accept":
            return "Current result is ready to accept as the best version."
        if action_id == "pin_and_revise":
            return "Pin suggested workflow memory before creating the next revision."
        if action_id == "retry":
            return "Retry the failed task to continue the workflow."
        if action_id == "revise":
            return "Create another revision with the current workflow memory set."
        return "Review the current workflow state and choose the next action."

    @staticmethod
    def _panel_event_title(event_type: str) -> str:
        return {
            "workflow_memory_pinned": "Workflow memory pinned",
            "workflow_memory_unpinned": "Workflow memory unpinned",
        }.get(event_type, "Workflow memory updated")

    @classmethod
    def _build_applied_action_feedback(
        cls,
        *,
        recent_memory_events: list[Any],
        status_summary: WorkflowReviewStatusSummary | None,
    ) -> WorkflowAppliedActionFeedback | None:
        latest_event = recent_memory_events[-1] if recent_memory_events else None
        if latest_event is None:
            return None

        return WorkflowAppliedActionFeedback(
            event_type=latest_event.event_type,
            tone="success" if latest_event.event_type == "workflow_memory_pinned" else "info",
            title=cls._applied_feedback_title(latest_event.event_type),
            summary=cls._applied_feedback_summary(
                event_type=latest_event.event_type,
                follow_up_action_id=None if status_summary is None else status_summary.recommended_action_id,
            ),
            memory_id=latest_event.memory_id,
            created_at=latest_event.created_at,
            follow_up_action_id=None if status_summary is None else status_summary.recommended_action_id,
        )

    @staticmethod
    def _applied_feedback_title(event_type: str) -> str:
        return {
            "workflow_memory_pinned": "Workflow memory update applied",
            "workflow_memory_unpinned": "Workflow memory removed",
        }.get(event_type, "Workflow memory updated")

    @staticmethod
    def _applied_feedback_summary(
        *,
        event_type: str,
        follow_up_action_id: str | None,
    ) -> str:
        if event_type == "workflow_memory_pinned":
            if follow_up_action_id:
                return f"Shared workflow memory was pinned. Continue with `{follow_up_action_id}` next."
            return "Shared workflow memory was pinned for upcoming revisions."
        if event_type == "workflow_memory_unpinned":
            if follow_up_action_id:
                return f"Shared workflow memory was removed. Continue with `{follow_up_action_id}` next."
            return "Shared workflow memory was removed from the workflow set."
        return "Workflow memory changed recently."

    @classmethod
    def _build_render_contract(
        cls,
        *,
        panel_header: WorkflowReviewPanelHeader | None,
        action_sections: WorkflowAvailableActionSections | None,
        status_summary: WorkflowReviewStatusSummary | None,
        applied_action_feedback: WorkflowAppliedActionFeedback | None,
    ) -> WorkflowReviewRenderContract | None:
        if panel_header is None and action_sections is None and status_summary is None:
            return None

        section_order = [
            section.section_id
            for section in (action_sections.items if action_sections is not None else [])
        ]
        default_focus_section_id = section_order[0] if section_order else None
        default_expanded_section_ids: list[str] = []
        if "recommended" in section_order:
            default_expanded_section_ids.append("recommended")
        if "blocked" in section_order:
            default_expanded_section_ids.append("blocked")
        if not default_expanded_section_ids and default_focus_section_id is not None:
            default_expanded_section_ids.append(default_focus_section_id)

        panel_tone = "attention" if panel_header is None else panel_header.tone
        return WorkflowReviewRenderContract(
            badge_order=[] if panel_header is None else [badge.badge_id for badge in panel_header.badges],
            panel_tone=panel_tone,
            display_priority=cls._render_display_priority(panel_tone),
            section_order=section_order,
            default_focus_section_id=default_focus_section_id,
            default_expanded_section_ids=default_expanded_section_ids,
            section_presentations=[
                WorkflowReviewSectionPresentation(
                    section_id=section_id,
                    tone=cls._section_tone(section_id),
                    collapsible=section_id != "recommended",
                )
                for section_id in section_order
            ],
            sticky_primary_action_id=None if status_summary is None else status_summary.recommended_action_id,
            sticky_primary_action_emphasis=cls._sticky_primary_action_emphasis(panel_tone),
            applied_feedback_dismissible=applied_action_feedback is not None,
        )

    @staticmethod
    def _render_display_priority(panel_tone: str) -> str:
        if panel_tone == "ready":
            return "normal"
        return "high"

    @staticmethod
    def _sticky_primary_action_emphasis(panel_tone: str) -> str:
        if panel_tone == "ready":
            return "normal"
        return "strong"

    @staticmethod
    def _section_tone(section_id: str) -> str:
        return {
            "recommended": "accent",
            "available": "neutral",
            "blocked": "muted",
        }.get(section_id, "neutral")

    @classmethod
    def _build_action_intent(cls, payload: dict[str, Any]) -> WorkflowAvailableActionIntent:
        review_decision = payload.get("review_decision") if isinstance(payload, dict) else None
        normalized_decision: str | None = None
        if isinstance(review_decision, dict):
            decision = str(review_decision.get("decision") or "").strip()
            if decision in {"accept", "revise", "retry", "repair", "escalate"}:
                normalized_decision = decision

        pin_memory_ids = cls._extract_action_memory_ids(payload.get("pin_workflow_memory_ids"))
        unpin_memory_ids = cls._extract_action_memory_ids(payload.get("unpin_workflow_memory_ids"))
        has_memory_change = bool(pin_memory_ids or unpin_memory_ids)

        memory_change = None
        if has_memory_change:
            memory_change = WorkflowAvailableActionMemoryChange(
                pin_memory_ids=pin_memory_ids,
                unpin_memory_ids=unpin_memory_ids,
                pin_count=len(pin_memory_ids),
                unpin_count=len(unpin_memory_ids),
            )

        return WorkflowAvailableActionIntent(
            review_decision=normalized_decision,
            mutates_workflow_memory=has_memory_change,
            workflow_memory_change=memory_change,
        )

    @staticmethod
    def _resolve_action_family(
        intent: WorkflowAvailableActionIntent,
    ) -> str:
        if intent.mutates_workflow_memory and intent.review_decision is not None:
            return "combined"
        if intent.mutates_workflow_memory:
            return "workflow_memory"
        return "review_decision"

    @staticmethod
    def _extract_action_memory_ids(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    @staticmethod
    def _button_label_for_action(action_id: str) -> str:
        return {
            "accept": "Accept result",
            "revise": "Create revision",
            "retry": "Retry task",
            "pin_and_revise": "Pin memory and revise",
        }.get(action_id, "Run action")

    @staticmethod
    def _workflow_memory_action_payload(
        *,
        summary: str,
        feedback: str,
        pin_ids: list[str] | None = None,
        unpin_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "review_decision": {
                "decision": "revise",
                "summary": summary,
                "feedback": feedback,
            }
        }
        if pin_ids:
            payload["pin_workflow_memory_ids"] = list(pin_ids)
        if unpin_ids:
            payload["unpin_workflow_memory_ids"] = list(unpin_ids)
        return payload

    @staticmethod
    def _unresolved_validation_issue_codes(latest_validation_summary: dict[str, Any]) -> list[str]:
        issues = latest_validation_summary.get("issues", []) if isinstance(latest_validation_summary, dict) else []
        codes: list[str] = []
        for item in issues or []:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or "").strip()
            if not code:
                continue
            if bool(item.get("resolved")):
                continue
            codes.append(code)
        return codes
