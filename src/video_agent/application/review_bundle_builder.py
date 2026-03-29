from __future__ import annotations

from typing import Any

from video_agent.application.agent_identity_service import AgentPrincipal
from video_agent.application.session_memory_service import SessionMemoryService
from video_agent.application.task_service import TaskService
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.domain.review_workflow_models import CollaborationSection, CollaborationSections, ReviewBundle


class ReviewBundleBuilder:
    def __init__(
        self,
        *,
        task_service: TaskService,
        store: SQLiteTaskStore,
        session_memory_service: SessionMemoryService | None,
    ) -> None:
        self.task_service = task_service
        self.store = store
        self.session_memory_service = session_memory_service

    def build(self, task_id: str, agent_principal: AgentPrincipal | None = None) -> ReviewBundle:
        if agent_principal is None:
            snapshot = self.task_service.get_video_task(task_id)
            result = self.task_service.get_video_result(task_id)
            events = self.task_service.get_task_events(task_id)
            task = self.store.get_task(task_id)
        else:
            snapshot = self.task_service.get_video_task_for_agent(task_id, agent_principal.agent_id)
            result = self.task_service.get_video_result_for_agent(task_id, agent_principal.agent_id)
            events = self.task_service.get_task_events_for_agent(task_id, agent_principal.agent_id)
            task = self.task_service.require_task_access(task_id, agent_principal.agent_id)
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
        quality_scorecard = self.task_service.get_quality_score(snapshot.task_id)
        if quality_scorecard is None:
            quality_scorecard_json = None
        elif isinstance(quality_scorecard, dict):
            quality_scorecard_json = dict(quality_scorecard)
        else:
            quality_scorecard_json = quality_scorecard.model_dump(mode="json")
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
        )

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
