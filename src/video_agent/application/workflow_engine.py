from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from video_agent.adapters.llm.client import (
    LLMClient,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from video_agent.adapters.llm.script_sanitizer import sanitize_script_text
from video_agent.adapters.rendering.emergency_video_writer import EmergencyVideoWriter
from video_agent.adapters.rendering.frame_extractor import FrameExtractor
from video_agent.adapters.rendering.manim_runner import ManimRunner
from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.agent_learning_service import AgentLearningService, quality_score_for_task_outcome
from video_agent.application.auto_repair_service import AutoRepairService
from video_agent.application.branch_arbitration import build_arbitration_summary, build_branch_scoreboard
from video_agent.application.case_memory_service import CaseMemoryService
from video_agent.application.capability_gate_service import CapabilityGateService
from video_agent.application.delivery_case_service import DeliveryCaseService
from video_agent.application.delivery_guarantee_service import DeliveryGuaranteeDecision, DeliveryGuaranteeService
from video_agent.application.errors import AdmissionControlError
from video_agent.application.failure_context import build_failure_context
from video_agent.application.outcome_signals import is_quality_passed
from video_agent.application.quality_judge_service import QualityJudgeService
from video_agent.application.recovery_policy_service import RecoveryPolicyService
from video_agent.application.runtime_service import RuntimeService
from video_agent.application.scene_spec_service import SceneSpecService
from video_agent.application.scene_plan import build_scene_plan
from video_agent.application.session_memory_service import SessionMemoryService
from video_agent.application.task_risk_service import TaskRiskService
from video_agent.application.workflow_phases import (
    combined_validation_report,
    latex_dependency_report,
    provider_failure_report,
    render_failure_report,
    terminal_task_state,
)
from video_agent.domain.enums import TaskPhase, TaskStatus, ValidationDecision
from video_agent.domain.quality_models import QualityScorecard
from video_agent.domain.validation_models import ValidationIssue, ValidationReport
from video_agent.observability.logging import build_log_event
from video_agent.observability.metrics import MetricsCollector
from video_agent.safety.runtime_policy import RuntimePolicy, RuntimePolicyError
from video_agent.validation.hard_validation import HardValidator
from video_agent.validation.latex_support import script_uses_latex
from video_agent.validation.preview_quality import PreviewQualityValidator
from video_agent.validation.rule_validation import RuleValidator
from video_agent.validation.static_check import StaticCheckValidator


class WorkflowEngine:
    def __init__(
        self,
        store: SQLiteTaskStore,
        artifact_store: ArtifactStore,
        llm_client: LLMClient,
        prompt_builder: Callable[..., str],
        static_validator: StaticCheckValidator,
        manim_runner: ManimRunner,
        frame_extractor: FrameExtractor,
        hard_validator: HardValidator,
        rule_validator: RuleValidator,
        runtime_service: RuntimeService,
        agent_learning_service: AgentLearningService | None = None,
        session_memory_service: SessionMemoryService | None = None,
        runtime_policy: RuntimePolicy | None = None,
        metrics: MetricsCollector | None = None,
        task_risk_service: TaskRiskService | None = None,
        scene_spec_service: SceneSpecService | None = None,
        capability_gate_service: CapabilityGateService | None = None,
        recovery_policy_service: RecoveryPolicyService | None = None,
        quality_judge_service: QualityJudgeService | None = None,
        emergency_video_writer: EmergencyVideoWriter | None = None,
        delivery_guarantee_service: DeliveryGuaranteeService | None = None,
        delivery_case_service: DeliveryCaseService | None = None,
        case_memory_service: CaseMemoryService | None = None,
    ) -> None:
        self.store = store
        self.artifact_store = artifact_store
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.static_validator = static_validator
        self.manim_runner = manim_runner
        self.frame_extractor = frame_extractor
        self.hard_validator = hard_validator
        self.rule_validator = rule_validator
        self.preview_quality_validator = PreviewQualityValidator()
        self.runtime_service = runtime_service
        self.agent_learning_service = agent_learning_service
        self.session_memory_service = session_memory_service
        self.runtime_policy = runtime_policy or RuntimePolicy(work_root=artifact_store.root)
        self.metrics = metrics or MetricsCollector()
        self.task_risk_service = task_risk_service or TaskRiskService()
        self.scene_spec_service = scene_spec_service or SceneSpecService()
        self.capability_gate_service = capability_gate_service or CapabilityGateService()
        self.recovery_policy_service = recovery_policy_service or RecoveryPolicyService()
        self.quality_judge_service = quality_judge_service or QualityJudgeService(
            min_score=runtime_service.settings.quality_gate_min_score
        )
        self.emergency_video_writer = emergency_video_writer or EmergencyVideoWriter(
            command=runtime_service.settings.ffmpeg_command,
            validator=lambda path: self.hard_validator.validate(path).passed,
        )
        self.auto_repair_service = AutoRepairService(
            store=store,
            artifact_store=artifact_store,
            settings=runtime_service.settings,
            recovery_policy_service=self.recovery_policy_service,
        )
        self.delivery_guarantee_service = delivery_guarantee_service or DeliveryGuaranteeService(
            settings=runtime_service.settings,
            artifact_store=artifact_store,
            emergency_video_writer=self.emergency_video_writer,
        )
        self.delivery_case_service = delivery_case_service
        self.case_memory_service = case_memory_service

    def run_task(self, task_id: str) -> None:
        task = self.store.get_task(task_id)
        if task is None:
            raise KeyError(f"Unknown task_id: {task_id}")
        if task.status is TaskStatus.CANCELLED:
            self.metrics.increment("tasks_cancelled")
            self._log(task, TaskPhase.CANCELLED, "Task skipped because it was cancelled")
            return

        self.metrics.increment("task_runs")
        task.status = TaskStatus.RUNNING
        task.attempt_count += 1
        self._transition(task, TaskPhase.RISK_ROUTING)

        try:
            risk_profile = self.task_risk_service.classify(prompt=task.prompt, style_hints=task.style_hints)
            task.risk_level = risk_profile.risk_level
            task.generation_mode = risk_profile.generation_mode
            self.store.update_task(task)
            self.artifact_store.write_task_snapshot(task)
            self._log(
                task,
                TaskPhase.RISK_ROUTING,
                "Risk profile classified",
                risk_level=task.risk_level,
                generation_mode=task.generation_mode,
                risk_signals=risk_profile.triggered_signals,
            )

            self._transition(task, TaskPhase.SCENE_PLANNING)
            if self.delivery_case_service is not None:
                self.delivery_case_service.mark_planner_running(task=task)
            render_profile = self._resolve_render_profile(task)
            scene_spec = self.scene_spec_service.build(
                prompt=task.prompt,
                output_profile=render_profile,
                style_hints=task.style_hints,
                generation_mode=task.generation_mode or "guided_generate",
            ).model_copy(update={"task_id": task.task_id})
            risk_profile = self.task_risk_service.classify(
                prompt=task.prompt,
                style_hints=task.style_hints,
                scene_spec=scene_spec.model_dump(mode="json"),
            )
            # This is the authoritative structured classification and must be persisted
            # before downstream artifacts/events so task records stay aligned.
            task.risk_level = risk_profile.risk_level
            task.generation_mode = risk_profile.generation_mode
            self.store.update_task(task)
            self.artifact_store.write_task_snapshot(task)
            scene_spec = scene_spec.model_copy(
                update={
                    "generation_mode": risk_profile.generation_mode,
                    "risk_signals": risk_profile.triggered_signals,
                }
            )
            scene_spec_path = self.artifact_store.scene_spec_path(task.task_id)
            if not self._ensure_allowed_artifact_path(task, TaskPhase.SCENE_PLANNING, scene_spec_path, "scene spec artifact"):
                return
            written_scene_spec_path = self.artifact_store.write_scene_spec(task.task_id, scene_spec.model_dump(mode="json"))
            self.store.register_artifact(task.task_id, "scene_spec", written_scene_spec_path)
            task.scene_spec_id = scene_spec.scene_spec_id
            self.store.update_task(task)
            self.artifact_store.write_task_snapshot(task)
            scene_plan = build_scene_plan(
                prompt=task.prompt,
                output_profile=render_profile,
                style_hints=task.style_hints,
            )
            scene_plan_path = self.artifact_store.scene_plan_path(task.task_id)
            if not self._ensure_allowed_artifact_path(task, TaskPhase.PLANNING, scene_plan_path, "scene plan artifact"):
                return
            written_scene_plan_path = self.artifact_store.write_scene_plan(task.task_id, scene_plan.model_dump(mode="json"))
            self.store.register_artifact(task.task_id, "scene_plan", written_scene_plan_path)
            if self.delivery_case_service is not None:
                self.delivery_case_service.record_planner_run(
                    task=task,
                    scene_spec_path=written_scene_spec_path,
                    scene_plan_path=written_scene_plan_path,
                )
            if self.case_memory_service is not None:
                self.case_memory_service.record_planner_state(task)
            self._log(
                task,
                TaskPhase.SCENE_PLANNING,
                "Scene plan generated",
                scene_class=scene_plan.scene_class,
                camera_strategy=scene_plan.camera_strategy,
            )

            self._transition(task, TaskPhase.PREFLIGHT_CHECK)
            mathtex_status = self.runtime_service.inspect_mathtex_feature()
            gate = self.capability_gate_service.evaluate(
                prompt=task.prompt,
                scene_spec=scene_spec.model_dump(mode="json"),
                runtime_status={"mathtex": mathtex_status.model_dump(mode="json")},
            )
            capability_gate_payload: dict[str, Any] = {"allowed": gate.allowed}
            if gate.block_reason is not None:
                capability_gate_payload["block_reason"] = gate.block_reason
            if gate.suggested_mode is not None:
                capability_gate_payload["suggested_mode"] = gate.suggested_mode
            scene_spec = scene_spec.model_copy(
                update={
                    "capability_gate": capability_gate_payload,
                    "capability_gate_signals": gate.triggered_signals,
                }
            )
            self.artifact_store.write_scene_spec(task.task_id, scene_spec.model_dump(mode="json"))
            if not gate.allowed:
                if gate.block_reason == "latex_dependency_missing":
                    self._fail_task(
                        task,
                        latex_dependency_report(
                            "Script uses MathTex/Tex but required LaTeX commands are unavailable",
                            mathtex_status.missing_checks or ["latex", "dvisvgm"],
                        ),
                    )
                    return
            prompt_text = self.prompt_builder(
                prompt=task.prompt,
                output_profile=render_profile,
                feedback=task.feedback,
                style_hints=task.style_hints,
                memory_context_summary=task.memory_context_summary,
                persistent_memory_context=task.persistent_memory_context_summary,
                scene_plan=scene_plan,
            )

            self._transition(task, TaskPhase.GENERATING_CODE)
            if self.delivery_case_service is not None:
                self.delivery_case_service.mark_generator_running(task=task)
            generation_started = time.monotonic()
            try:
                script_text = sanitize_script_text(self.llm_client.generate_script(prompt_text))
            except ProviderAuthError as exc:
                self.metrics.increment("generation_failures")
                self.metrics.record_timing("generation_seconds", time.monotonic() - generation_started)
                self._log(task, TaskPhase.GENERATING_CODE, "LLM provider authentication failed", error=str(exc))
                self._fail_task(
                    task,
                    provider_failure_report("provider_auth_error", "Provider authentication failed", str(exc)),
                )
                return
            except ProviderRateLimitError as exc:
                self.metrics.increment("generation_failures")
                self.metrics.record_timing("generation_seconds", time.monotonic() - generation_started)
                self._log(task, TaskPhase.GENERATING_CODE, "LLM provider rate limited request", error=str(exc))
                self._fail_task(
                    task,
                    provider_failure_report("provider_rate_limited", "Provider rate limited request", str(exc)),
                )
                return
            except ProviderTimeoutError as exc:
                self.metrics.increment("generation_failures")
                self.metrics.record_timing("generation_seconds", time.monotonic() - generation_started)
                self._log(task, TaskPhase.GENERATING_CODE, "LLM provider timed out", error=str(exc))
                self._fail_task(
                    task,
                    provider_failure_report("provider_timeout", "Provider timed out", str(exc)),
                )
                return
            except ProviderResponseError as exc:
                self.metrics.increment("generation_failures")
                self.metrics.record_timing("generation_seconds", time.monotonic() - generation_started)
                self._log(task, TaskPhase.GENERATING_CODE, "LLM generation failed", error=str(exc))
                self._fail_task(
                    task,
                    provider_failure_report("generation_failed", "Generation failed", str(exc)),
                )
                return
            self.metrics.increment("generation_runs")
            self.metrics.record_timing("generation_seconds", time.monotonic() - generation_started)

            script_path = self.artifact_store.script_path(task.task_id)
            if not self._ensure_allowed_artifact_path(task, TaskPhase.GENERATING_CODE, script_path, "script artifact"):
                return
            script_path = self.artifact_store.write_script(task.task_id, script_text)
            task.current_script_artifact_id = self.store.register_artifact(
                task.task_id,
                "current_script",
                script_path,
            )
            self.store.update_task(task)
            self.artifact_store.write_task_snapshot(task)
            self._log(task, TaskPhase.GENERATING_CODE, "Script generated", script_path=str(script_path))

            self._transition(task, TaskPhase.STATIC_CHECK)
            static_report = self.static_validator.validate(script_text)
            if not static_report.passed:
                self._fail_task(task, static_report)
                return

            self._transition(task, TaskPhase.RENDERING)
            if script_uses_latex(script_text):
                mathtex_status = self.runtime_service.inspect_mathtex_feature()
                if not mathtex_status.available:
                    missing = mathtex_status.missing_checks
                    message = "Script uses MathTex/Tex but required LaTeX commands are unavailable"
                    self._log(
                        task,
                        TaskPhase.RENDERING,
                        "MathTex dependencies missing",
                        missing_checks=missing,
                    )
                    self._fail_task(
                        task,
                        latex_dependency_report(message, missing),
                    )
                    return
            render_output_dir = self.artifact_store.final_video_path(task.task_id).parent
            if not self._ensure_allowed_artifact_path(task, TaskPhase.RENDERING, render_output_dir, "render output directory"):
                return
            try:
                render_result = self.manim_runner.render(
                    script_path,
                    render_output_dir,
                    quality_preset=render_profile["quality_preset"],
                    frame_rate=render_profile["frame_rate"],
                    pixel_width=render_profile["pixel_width"],
                    pixel_height=render_profile["pixel_height"],
                    timeout_seconds=self.runtime_policy.render_timeout_seconds,
                    sandbox_policy=self.runtime_policy,
                )
            except RuntimePolicyError as exc:
                sandbox_policy = {"code": exc.code, "message": str(exc), **exc.details}
                self.metrics.increment("runtime_policy_violations")
                self._log(
                    task,
                    TaskPhase.RENDERING,
                    "Sandbox policy blocked render launch",
                    sandbox_policy=sandbox_policy,
                    sandbox_error=str(exc),
                )
                self._fail_task(
                    task,
                    ValidationReport(
                        decision=ValidationDecision.FAIL,
                        passed=False,
                        issues=[ValidationIssue(code="sandbox_policy_violation", message=str(exc))],
                        summary="Sandbox policy violation",
                        details={"sandbox_policy": sandbox_policy},
                    ),
                )
                return
            self.metrics.increment("render_runs")
            self.metrics.record_timing("render_seconds", render_result.duration_seconds)
            if render_result.exit_code != 0 or not render_result.video_path.exists():
                report = render_failure_report(render_result.stderr)
                self._log(
                    task,
                    TaskPhase.RENDERING,
                    "Render failed",
                    exit_code=render_result.exit_code,
                    stderr=render_result.stderr,
                )
                self._fail_task(task, report)
                return
            final_video_path = self.artifact_store.final_video_path(task.task_id)
            if not self._ensure_allowed_artifact_path(task, TaskPhase.RENDERING, final_video_path, "rendered video"):
                return
            final_video_path = self.artifact_store.promote_final_video(task.task_id, render_result.video_path)
            task.best_result_artifact_id = self.store.register_artifact(
                task.task_id,
                "final_video",
                final_video_path,
                metadata={"duration_seconds": render_result.duration_seconds},
            )
            self.store.update_task(task)
            self.artifact_store.write_task_snapshot(task)
            self._log(task, TaskPhase.RENDERING, "Render completed", video_path=str(final_video_path))
            if self.delivery_case_service is not None:
                self.delivery_case_service.record_generator_run(
                    task=task,
                    status="completed",
                    summary="Generation and render completed",
                    phase=TaskPhase.RENDERING.value,
                    script_path=script_path,
                    video_path=final_video_path,
                    decision={"attempt_count": task.attempt_count},
                )

            self._transition(task, TaskPhase.PREVIEW_RENDER)
            preview_dir = self.artifact_store.previews_dir(task.task_id)
            if not self._ensure_allowed_artifact_path(task, TaskPhase.PREVIEW_RENDER, preview_dir, "preview directory"):
                return
            preview_paths = self.frame_extractor.extract(final_video_path, preview_dir)
            for preview_path in preview_paths:
                self.store.register_artifact(task.task_id, "preview_frame", preview_path)
            self._log(task, TaskPhase.PREVIEW_RENDER, "Preview extraction completed", preview_count=len(preview_paths))

            self._transition(task, TaskPhase.PREVIEW_VALIDATION)
            if self.delivery_case_service is not None:
                self.delivery_case_service.mark_reviewer_running(task=task)
            preview_report = self.preview_quality_validator.validate(preview_paths, profile=task.validation_profile)
            self._transition(task, TaskPhase.VALIDATION)
            validation_started = time.monotonic()
            hard_report = self.hard_validator.validate(final_video_path, profile=task.validation_profile)
            rule_report = self.rule_validator.validate(final_video_path, profile=task.validation_profile)
            self.metrics.increment("validation_runs")
            self.metrics.record_timing("validation_seconds", time.monotonic() - validation_started)
            combined_report = combined_validation_report(hard_report, rule_report, preview_report)
            if not combined_report.passed:
                self._fail_task(task, combined_report)
                return

            validation_report_path = self.artifact_store.validation_report_path(task.task_id)
            if not self._ensure_allowed_artifact_path(task, TaskPhase.VALIDATION, validation_report_path, "validation report"):
                return
            report_path = self.artifact_store.write_validation_report(task.task_id, combined_report)
            self.store.record_validation(task.task_id, combined_report)
            self.store.register_artifact(task.task_id, "validation_report", report_path)

            self._transition(task, TaskPhase.QUALITY_JUDGING)
            preview_issue_codes = [issue.code for issue in preview_report.issues]
            scorecard = self.quality_judge_service.score(
                status="completed",
                issue_codes=[issue.code for issue in combined_report.issues],
                preview_issue_codes=preview_issue_codes,
                summary=combined_report.summary,
            ).model_copy(update={"task_id": task.task_id})
            quality_score_path = self.artifact_store.quality_score_path(task.task_id)
            if not self._ensure_allowed_artifact_path(task, TaskPhase.QUALITY_JUDGING, quality_score_path, "quality score artifact"):
                return
            written_quality_score_path = self.artifact_store.write_quality_score(task.task_id, scorecard.model_dump(mode="json"))
            self.store.register_artifact(task.task_id, "quality_score", written_quality_score_path)
            self.store.upsert_task_quality_score(task.task_id, scorecard)
            task.quality_gate_status = "accepted" if scorecard.accepted else "needs_revision"

            task.status, task.phase = terminal_task_state(combined_report)
            task.delivery_status = "delivered"
            task.resolved_task_id = task.task_id
            if task.completion_mode is None:
                task.completion_mode = "primary" if task.parent_task_id is None else "repaired"
            if task.delivery_tier is None:
                task.delivery_tier = "primary" if task.parent_task_id is None else (task.generation_mode or "guided_generate")
            task.delivery_stop_reason = None
            quality_passed = is_quality_passed(
                status=task.status.value,
                quality_gate_status=task.quality_gate_status,
                completion_mode=task.completion_mode,
            )
            self.metrics.increment("deliveries_completed")
            if quality_passed:
                self.metrics.increment("tasks_completed")
            self.store.update_task(task)
            self.artifact_store.write_task_snapshot(task)
            self._sync_root_delivery_resolution(task)
            if self.delivery_case_service is not None:
                self.delivery_case_service.record_reviewer_run(
                    task=task,
                    report=combined_report,
                    summary="Validation and quality review completed",
                    quality_gate_status=task.quality_gate_status,
                    validation_report_path=report_path,
                    quality_score_path=written_quality_score_path,
                )
                self.delivery_case_service.sync_case_for_root(task.root_task_id or task.task_id)
            if self.case_memory_service is not None:
                self.case_memory_service.record_review_outcome(
                    task,
                    summary=combined_report.summary,
                    quality_gate_status=task.quality_gate_status,
                    quality_scorecard=scorecard,
                    failure_contract=None,
                    recovery_plan=None,
                )
            self.store.append_event(task.task_id, "task_finished", {"status": task.status.value})
            auto_challenger_decision = self._maybe_schedule_quality_challenger(task, scorecard)
            self._record_auto_challenger_decision(task, auto_challenger_decision)
            auto_arbitration_decision = self._maybe_auto_promote_challenger(task)
            self._record_auto_arbitration_decision(task, auto_arbitration_decision)
            self._record_case_memory_branch_state(task)
            self._record_agent_learning_outcome(task, combined_report, task_quality_scorecard=scorecard)
            self._record_session_memory_outcome(
                task,
                result_summary=combined_report.summary,
                extra_artifact_refs=[
                    self.artifact_store.resource_uri(task.task_id, report_path),
                    self.artifact_store.resource_uri(task.task_id, written_quality_score_path),
                ],
            )
            self._log(task, task.phase, "Task finished", status=task.status.value, passed=combined_report.passed)
        except Exception as exc:
            self.metrics.increment("infra_failures")
            self._log(task, task.phase, "Infrastructure failure", error=str(exc))
            report = ValidationReport(
                decision=ValidationDecision.FAIL,
                passed=False,
                issues=[ValidationIssue(code="infra_error", message=str(exc))],
                summary="Infrastructure failure",
            )
            self._fail_task(task, report)

    def _ensure_allowed_artifact_path(self, task, phase: TaskPhase, path: Path, description: str) -> bool:
        candidate = Path(path)
        if self.runtime_policy.is_allowed_write(candidate):
            return True

        self.metrics.increment("runtime_policy_violations")
        self._log(
            task,
            phase,
            "Runtime policy blocked artifact write",
            blocked_path=str(candidate),
            description=description,
        )
        report = ValidationReport(
            decision=ValidationDecision.FAIL,
            passed=False,
            issues=[
                ValidationIssue(
                    code="runtime_policy_violation",
                    message=f"Runtime policy blocked {description}: {candidate}",
                )
            ],
            summary="Runtime policy violation",
            details={"blocked_path": str(candidate), "description": description},
        )
        self._fail_task(task, report, persist_report_artifact=False, persist_snapshot=False)
        return False

    def _fail_task(
        self,
        task,
        report: ValidationReport,
        persist_report_artifact: bool = True,
        persist_snapshot: bool = True,
    ) -> None:
        top_issue = report.issues[0] if report.issues else None
        if self.delivery_case_service is not None and task.phase in {
            TaskPhase.GENERATING_CODE,
            TaskPhase.STATIC_CHECK,
            TaskPhase.RENDERING,
        }:
            self.delivery_case_service.record_generator_run(
                task=task,
                status="failed",
                summary="Generation failed",
                phase=task.phase.value,
                stop_reason=None if top_issue is None else top_issue.code,
                decision={
                    "issue_codes": [issue.code for issue in report.issues],
                },
            )
        self.store.record_validation(task.task_id, report)
        if persist_report_artifact:
            report_path = self.artifact_store.validation_report_path(task.task_id)
            if self.runtime_policy.is_allowed_write(report_path):
                written_report_path = self.artifact_store.write_validation_report(task.task_id, report)
                self.store.register_artifact(task.task_id, "validation_report", written_report_path)
            else:
                self._log(
                    task,
                    TaskPhase.FAILED,
                    "Skipped validation report artifact due to runtime policy",
                    blocked_path=str(report_path),
                )
        task.status = TaskStatus.FAILED
        task.phase = TaskPhase.FAILED
        self.store.update_task(task)
        if persist_snapshot:
            self.artifact_store.write_task_snapshot(task)
        self.store.append_event(task.task_id, "task_failed", {"issues": [issue.code for issue in report.issues]})
        failure_context_path = self.artifact_store.failure_context_path(task.task_id)
        if self.runtime_policy.is_allowed_write(failure_context_path):
            failure_context = build_failure_context(
                task=task,
                report=report,
                artifact_store=self.artifact_store,
                events=self.store.list_events(task.task_id),
                retryable_issue_codes=self.runtime_service.settings.auto_repair_retryable_issue_codes,
            )
            semantic_diagnostics = failure_context.get("semantic_diagnostics") or []
            if semantic_diagnostics:
                self._log(
                    task,
                    TaskPhase.FAILED,
                    "Semantic diagnostics captured",
                    count=len(semantic_diagnostics),
                    codes=[item.get("code") for item in semantic_diagnostics],
                )
            failure_contract = failure_context.get("failure_contract")
            if isinstance(failure_contract, dict):
                failure_contract_path = self.artifact_store.failure_contract_path(task.task_id)
                if self.runtime_policy.is_allowed_write(failure_contract_path):
                    written_failure_contract_path = self.artifact_store.write_failure_contract(task.task_id, failure_contract)
                    self.store.register_artifact(task.task_id, "failure_contract", written_failure_contract_path)
                recovery_plan = self.recovery_policy_service.build(
                    issue_code=top_issue.code if top_issue else None,
                    failure_contract=failure_contract,
                ).model_copy(update={"task_id": task.task_id})
                recovery_plan_path = self.artifact_store.recovery_plan_path(task.task_id)
                if self.runtime_policy.is_allowed_write(recovery_plan_path):
                    written_recovery_plan_path = self.artifact_store.write_recovery_plan(
                        task.task_id,
                        recovery_plan.model_dump(mode="json"),
                    )
                    self.store.register_artifact(task.task_id, "recovery_plan", written_recovery_plan_path)
            written_failure_context_path = self.artifact_store.write_failure_context(task.task_id, failure_context)
            self.store.register_artifact(task.task_id, "failure_context", written_failure_context_path)
        else:
            self._log(
                task,
                TaskPhase.FAILED,
                "Skipped failure context artifact due to runtime policy",
                blocked_path=str(failure_context_path),
            )
        failure_artifact_refs: list[str] = []
        validation_report_path = self.artifact_store.validation_report_path(task.task_id)
        if persist_report_artifact and validation_report_path.exists():
            failure_artifact_refs.append(self.artifact_store.resource_uri(task.task_id, validation_report_path))
        if self.artifact_store.failure_contract_path(task.task_id).exists():
            failure_artifact_refs.append(
                self.artifact_store.resource_uri(task.task_id, self.artifact_store.failure_contract_path(task.task_id))
            )
        if self.artifact_store.failure_context_path(task.task_id).exists():
            failure_artifact_refs.append(
                self.artifact_store.resource_uri(task.task_id, self.artifact_store.failure_context_path(task.task_id))
            )
        self._record_session_memory_outcome(task, result_summary=report.summary, extra_artifact_refs=failure_artifact_refs)
        if self.delivery_case_service is not None:
            self.delivery_case_service.mark_repairer_running(task=task)
        auto_repair_decision = self.auto_repair_service.maybe_schedule_repair(task)
        self._record_repair_state(task, report, auto_repair_decision)
        if self.delivery_case_service is not None:
            self.delivery_case_service.record_reviewer_run(
                task=task,
                report=report,
                summary="Failure reviewed",
                quality_gate_status=task.quality_gate_status,
                failure_contract=self.artifact_store.read_failure_contract(task.task_id),
                recovery_plan=self.artifact_store.read_recovery_plan(task.task_id),
                validation_report_path=self.artifact_store.validation_report_path(task.task_id),
            )
            self.delivery_case_service.record_repairer_run(
                task=task,
                auto_repair_decision=auto_repair_decision,
                report=report,
            )
        if self.case_memory_service is not None:
            self.case_memory_service.record_review_outcome(
                task,
                summary=report.summary,
                quality_gate_status=task.quality_gate_status,
                quality_scorecard=self.store.get_task_quality_score(task.task_id),
                failure_contract=self.artifact_store.read_failure_contract(task.task_id),
                recovery_plan=self.artifact_store.read_recovery_plan(task.task_id),
            )
        delivery_decision = None
        if not auto_repair_decision.created:
            delivery_decision = self._maybe_schedule_degraded_delivery(task)
            if delivery_decision is None:
                if not self._allows_emergency_delivery(top_issue.code if top_issue is not None else None):
                    delivery_decision = DeliveryGuaranteeDecision(
                        delivered=False,
                        reason=top_issue.code if top_issue is not None else "delivery_blocked",
                    )
                else:
                    try:
                        delivery_decision = self.delivery_guarantee_service.maybe_deliver(task)
                    except Exception as exc:
                        delivery_decision = DeliveryGuaranteeDecision(delivered=False, reason="delivery_exception")
                        self._log(
                            task,
                            TaskPhase.FAILED,
                            "Delivery guarantee failed",
                            error=str(exc),
                        )
            if delivery_decision.delivered:
                self._finalize_guaranteed_delivery(task, delivery_decision)
            elif not delivery_decision.scheduled:
                self._mark_delivery_failed(task, stop_reason=delivery_decision.reason)
                self._record_agent_learning_outcome(task, report)
        self.store.append_event(
            task.task_id,
            "auto_repair_decision",
            {
                "created": auto_repair_decision.created,
                "reason": auto_repair_decision.reason,
                "issue_code": auto_repair_decision.issue_code,
                "child_task_id": auto_repair_decision.child_task_id,
            },
        )
        if task.root_task_id and task.root_task_id != task.task_id:
            self.store.append_event(
                task.root_task_id,
                "auto_repair_decision",
                {
                    "created": auto_repair_decision.created,
                    "reason": auto_repair_decision.reason,
                    "issue_code": auto_repair_decision.issue_code,
                    "child_task_id": auto_repair_decision.child_task_id,
                },
            )
        self._log(
            task,
            TaskPhase.FAILED,
            "Auto repair evaluated",
            created=auto_repair_decision.created,
            reason=auto_repair_decision.reason,
            issue_code=auto_repair_decision.issue_code,
            child_task_id=auto_repair_decision.child_task_id,
        )
        if delivery_decision is not None:
            self._log(
                task,
                TaskPhase.FAILED,
                "Delivery guarantee evaluated",
                delivered=delivery_decision.delivered,
                reason=delivery_decision.reason,
                scheduled=delivery_decision.scheduled,
                child_task_id=delivery_decision.child_task_id,
                completion_mode=delivery_decision.completion_mode,
                delivery_tier=delivery_decision.delivery_tier,
            )
        self._log(
            task,
            TaskPhase.FAILED,
            "Task failed",
            issues=[issue.code for issue in report.issues],
            summary=report.summary,
        )
        if delivery_decision is not None and delivery_decision.delivered:
            self.metrics.increment("deliveries_completed")
        else:
            self.metrics.increment("tasks_failed")
        if self.delivery_case_service is not None:
            self.delivery_case_service.sync_case_for_root(task.root_task_id or task.task_id)

    @staticmethod
    def _allows_emergency_delivery(issue_code: str | None) -> bool:
        return issue_code not in {
            "latex_dependency_missing",
            "sandbox_policy_violation",
            "runtime_policy_violation",
        }

    def _record_session_memory_outcome(
        self,
        task,
        *,
        result_summary: str | None,
        extra_artifact_refs: list[str] | None = None,
    ) -> None:
        if self.session_memory_service is None:
            return
        self.session_memory_service.record_task_outcome(
            task,
            result_summary=result_summary,
            extra_artifact_refs=extra_artifact_refs,
        )

    def _record_agent_learning_outcome(
        self,
        task,
        report: ValidationReport,
        task_quality_scorecard: QualityScorecard | None = None,
    ) -> None:
        if self.agent_learning_service is None or not task.agent_id:
            return
        issue_codes = [issue.code for issue in report.issues]
        quality_passed = is_quality_passed(
            status=task.status.value,
            quality_gate_status=task.quality_gate_status,
            completion_mode=task.completion_mode,
        )
        # Only load persisted scorecards for quality-passed outcomes to avoid
        # stale/mismatched scorecard reuse on failure or delivery-only telemetry.
        if task_quality_scorecard is None and quality_passed:
            task_quality_scorecard = self.store.get_task_quality_score(task.task_id)
        try:
            self.agent_learning_service.record_task_outcome(
                agent_id=task.agent_id,
                task_id=task.task_id,
                session_id=task.session_id,
                status=task.status.value,
                quality_passed=quality_passed,
                issue_codes=issue_codes,
                quality_score=quality_score_for_task_outcome(
                    status=task.status.value,
                    issue_codes=issue_codes,
                    scorecard=task_quality_scorecard,
                    quality_passed=quality_passed,
                ),
                profile_digest=task.effective_profile_digest,
                memory_ids=task.selected_memory_ids,
            )
        except Exception as exc:
            try:
                self._log(task, task.phase, "Agent learning telemetry skipped", error=str(exc))
            except Exception:
                return

    def _record_repair_state(self, task, report: ValidationReport, auto_repair_decision) -> None:
        root_task_id = task.root_task_id or task.task_id
        root_task = self.store.get_task(root_task_id)
        if root_task is None:
            return

        root_task.repair_attempted = root_task.repair_attempted or auto_repair_decision.created or (
            auto_repair_decision.reason not in {"disabled", "task_not_failed"}
        )
        root_task.repair_child_count = max(0, self.store.count_lineage_tasks(root_task_id) - 1)
        if report.issues:
            root_task.repair_last_issue_code = report.issues[0].code
        root_task.repair_stop_reason = None if auto_repair_decision.created else auto_repair_decision.reason
        self.store.update_task(root_task)
        self.artifact_store.write_task_snapshot(root_task)

    def _maybe_schedule_degraded_delivery(self, task) -> DeliveryGuaranteeDecision | None:
        if not self.runtime_service.settings.delivery_guarantee_enabled:
            return None
        if task.parent_task_id is None:
            return None
        if task.completion_mode == "degraded":
            return None
        if self._lineage_already_has_degraded_attempt(task.root_task_id or task.task_id):
            return None

        failure_contract = self.artifact_store.read_failure_contract(task.task_id) or {}
        if bool(failure_contract.get("human_review_required")):
            return None
        issue_code = str(failure_contract.get("issue_code") or "")
        if issue_code.startswith("provider_") or issue_code in {
            "latex_dependency_missing",
            "sandbox_policy_violation",
            "runtime_policy_violation",
        }:
            return None

        task_service = getattr(self.auto_repair_service, "task_service", None)
        if task_service is None:
            return None

        recovery_plan = self.artifact_store.read_recovery_plan(task.task_id) or {}
        generation_mode = str(
            recovery_plan.get("fallback_generation_mode")
            or failure_contract.get("fallback_generation_mode")
            or task.generation_mode
            or "guided_generate"
        )
        try:
            created = task_service.create_degraded_delivery_task(
                task.task_id,
                feedback=self._build_degraded_delivery_feedback(task, issue_code=issue_code, generation_mode=generation_mode),
                generation_mode=generation_mode,
                style_hints=self._build_degraded_style_hints(task.style_hints),
                output_profile=self._build_degraded_output_profile(task.output_profile),
            )
        except (AdmissionControlError, ValueError) as exc:
            self._log(
                task,
                TaskPhase.FAILED,
                "Skipped degraded delivery attempt",
                reason=str(exc),
            )
            return None

        return DeliveryGuaranteeDecision(
            delivered=False,
            reason="created_degraded_attempt",
            scheduled=True,
            child_task_id=created.task_id,
            completion_mode="degraded",
            delivery_tier=generation_mode,
        )

    def _maybe_schedule_quality_challenger(self, task, scorecard: QualityScorecard) -> dict[str, Any]:
        if not self.runtime_service.settings.multi_agent_workflow_enabled:
            return {
                "created": False,
                "reason": "multi_agent_workflow_disabled",
                "child_task_id": None,
                "quality_gate_status": task.quality_gate_status,
                "overall_score": scorecard.total_score,
            }
        if not self.runtime_service.settings.multi_agent_workflow_auto_challenger_enabled:
            return {
                "created": False,
                "reason": "auto_challenger_governance_disabled",
                "child_task_id": None,
                "quality_gate_status": task.quality_gate_status,
                "overall_score": scorecard.total_score,
            }
        if task.status is not TaskStatus.COMPLETED or task.delivery_status != "delivered":
            return {
                "created": False,
                "reason": "task_not_delivered",
                "child_task_id": None,
                "quality_gate_status": task.quality_gate_status,
                "overall_score": scorecard.total_score,
            }
        if task.quality_gate_status == "accepted":
            return {
                "created": False,
                "reason": "quality_accepted",
                "child_task_id": None,
                "quality_gate_status": task.quality_gate_status,
                "overall_score": scorecard.total_score,
            }
        if task.completion_mode in {"degraded", "emergency_fallback"}:
            return {
                "created": False,
                "reason": "completion_mode_ineligible",
                "child_task_id": None,
                "quality_gate_status": task.quality_gate_status,
                "overall_score": scorecard.total_score,
            }
        guard_blockers = self._guarded_rollout_blockers()
        if guard_blockers:
            return {
                "created": False,
                "reason": "guarded_rollout_blocked",
                "blocked_reasons": guard_blockers,
                "child_task_id": None,
                "quality_gate_status": task.quality_gate_status,
                "overall_score": scorecard.total_score,
            }

        task_service = getattr(self.auto_repair_service, "task_service", None)
        if task_service is None:
            return {
                "created": False,
                "reason": "task_service_unavailable",
                "child_task_id": None,
                "quality_gate_status": task.quality_gate_status,
                "overall_score": scorecard.total_score,
            }

        try:
            created = task_service.create_challenger_task(
                task.task_id,
                feedback=self._build_quality_challenger_feedback(task, scorecard),
                session_id=task.session_id,
            )
        except (AdmissionControlError, ValueError) as exc:
            return {
                "created": False,
                "reason": str(exc) if isinstance(exc, ValueError) else exc.code,
                "child_task_id": None,
                "quality_gate_status": task.quality_gate_status,
                "overall_score": scorecard.total_score,
            }

        return {
            "created": True,
            "reason": "created",
            "child_task_id": created.task_id,
            "quality_gate_status": task.quality_gate_status,
            "overall_score": scorecard.total_score,
        }

    def _record_auto_challenger_decision(self, task, decision: dict[str, Any]) -> None:
        self.store.append_event(task.task_id, "auto_challenger_decision", decision)
        if task.root_task_id and task.root_task_id != task.task_id:
            self.store.append_event(task.root_task_id, "auto_challenger_decision", decision)
        if self.case_memory_service is not None and task.root_task_id:
            self.case_memory_service.record_decision(
                task.root_task_id,
                action="auto_challenger_decision",
                task_id=task.task_id,
                details=decision,
            )
        self._log(
            task,
            TaskPhase.COMPLETED,
            "Auto challenger evaluated",
            created=bool(decision.get("created")),
            reason=decision.get("reason"),
            child_task_id=decision.get("child_task_id"),
            quality_gate_status=decision.get("quality_gate_status"),
            overall_score=decision.get("overall_score"),
        )

    def _maybe_auto_promote_challenger(self, task) -> dict[str, Any]:
        if not self.runtime_service.settings.multi_agent_workflow_enabled:
            return {
                "promoted": False,
                "reason": "multi_agent_workflow_disabled",
                "recommended_task_id": None,
                "recommended_action": None,
                "selected_task_id": None,
            }
        if not self.runtime_service.settings.multi_agent_workflow_auto_arbitration_enabled:
            return {
                "promoted": False,
                "reason": "auto_arbitration_governance_disabled",
                "recommended_task_id": None,
                "recommended_action": None,
                "selected_task_id": None,
            }
        if task.branch_kind != "challenger":
            return {
                "promoted": False,
                "reason": "not_challenger_branch",
                "recommended_task_id": None,
                "recommended_action": None,
                "selected_task_id": None,
            }
        if task.status is not TaskStatus.COMPLETED or task.delivery_status != "delivered":
            return {
                "promoted": False,
                "reason": "task_not_delivered",
                "recommended_task_id": None,
                "recommended_action": None,
                "selected_task_id": None,
            }
        if task.quality_gate_status != "accepted":
            return {
                "promoted": False,
                "reason": "quality_not_accepted",
                "recommended_task_id": task.task_id,
                "recommended_action": "wait_for_completion",
                "selected_task_id": None,
            }
        guard_blockers = self._guarded_rollout_blockers()
        if guard_blockers:
            return {
                "promoted": False,
                "reason": "guarded_rollout_blocked",
                "blocked_reasons": guard_blockers,
                "recommended_task_id": None,
                "recommended_action": None,
                "selected_task_id": None,
            }

        root_task_id = task.root_task_id or task.task_id
        delivery_case = self.store.get_delivery_case(root_task_id)
        selected_task_id = None if delivery_case is None else delivery_case.selected_task_id
        active_task_id = None if delivery_case is None else delivery_case.active_task_id
        lineage = self.store.list_lineage_tasks(root_task_id)
        arbitration_summary = build_arbitration_summary(
            branch_scoreboard=build_branch_scoreboard(
                lineage_tasks=lineage,
                scorecards_by_task_id={
                    lineage_task.task_id: self._load_quality_scorecard_json(lineage_task.task_id)
                    for lineage_task in lineage
                },
                selected_task_id=selected_task_id,
                active_task_id=active_task_id,
            ),
            selected_task_id=selected_task_id,
            active_task_id=active_task_id,
        )
        decision = {
            "promoted": False,
            "reason": str(arbitration_summary.get("reason") or "arbitration_completed"),
            "recommended_task_id": arbitration_summary.get("recommended_task_id"),
            "recommended_action": arbitration_summary.get("recommended_action"),
            "selected_task_id": arbitration_summary.get("selected_task_id"),
            "candidate_count": arbitration_summary.get("candidate_count"),
        }
        if (
            arbitration_summary.get("recommended_action") != "promote_challenger"
            or arbitration_summary.get("recommended_task_id") != task.task_id
        ):
            return decision

        task_service = getattr(self.auto_repair_service, "task_service", None)
        if task_service is None:
            decision["reason"] = "task_service_unavailable"
            return decision

        try:
            task_service.accept_best_version(task.task_id)
        except (AdmissionControlError, ValueError) as exc:
            decision["reason"] = str(exc) if isinstance(exc, ValueError) else exc.code
            return decision

        decision["promoted"] = True
        decision["selected_task_id"] = task.task_id
        return decision

    def _guarded_rollout_blockers(self) -> list[str]:
        guard = self.runtime_service.inspect_multi_agent_autonomy_guard()
        if not guard.enabled or guard.allowed:
            return []
        return list(guard.reasons)

    def _record_auto_arbitration_decision(self, task, decision: dict[str, Any]) -> None:
        self.store.append_event(task.task_id, "auto_arbitration_decision", decision)
        if task.root_task_id and task.root_task_id != task.task_id:
            self.store.append_event(task.root_task_id, "auto_arbitration_decision", decision)
        if self.delivery_case_service is not None and decision.get("recommended_action") is not None:
            self.delivery_case_service.record_auto_arbitration_evaluated(
                task=task,
                arbitration_summary=decision,
                promoted=bool(decision.get("promoted")),
            )
        if self.case_memory_service is not None and task.root_task_id:
            self.case_memory_service.record_decision(
                task.root_task_id,
                action="auto_arbitration_decision",
                task_id=task.task_id,
                details=decision,
            )
        self._log(
            task,
            TaskPhase.COMPLETED,
            "Auto arbitration evaluated",
            promoted=bool(decision.get("promoted")),
            reason=decision.get("reason"),
            recommended_task_id=decision.get("recommended_task_id"),
            recommended_action=decision.get("recommended_action"),
            selected_task_id=decision.get("selected_task_id"),
        )

    def _lineage_already_has_degraded_attempt(self, root_task_id: str) -> bool:
        for lineage_task in self.store.list_lineage_tasks(root_task_id):
            if lineage_task.parent_task_id is not None and lineage_task.completion_mode == "degraded":
                return True
        return False

    @staticmethod
    def _build_degraded_style_hints(style_hints: dict[str, Any] | None) -> dict[str, Any]:
        return {
            **(style_hints or {}),
            "scene_complexity": "low",
            "animation_density": "low",
            "camera": "static",
            "pace": "steady",
        }

    @staticmethod
    def _build_degraded_output_profile(output_profile: dict[str, Any] | None) -> dict[str, Any]:
        profile = dict(output_profile or {})
        profile["quality_preset"] = "development"
        return profile

    @staticmethod
    def _build_degraded_delivery_feedback(task, *, issue_code: str, generation_mode: str) -> str:
        issue_label = issue_code or "unknown_failure"
        return (
            "Guaranteed delivery degraded fallback. "
            f"Previous attempt failed with {issue_label}. "
            f"Prefer generation mode {generation_mode}. "
            "Produce the simplest playable video that still satisfies the core request. "
            "Use a static camera, low animation density, one focal idea, and simple shapes or text. "
            "Prioritize successful rendering over richness."
        )

    def _build_quality_challenger_feedback(self, task, scorecard: QualityScorecard) -> str:
        score_text = f"{float(scorecard.total_score or 0.0):.2f}"
        threshold_text = f"{float(self.runtime_service.settings.quality_gate_min_score):.2f}"
        issue_codes = list(scorecard.must_fix_issues or scorecard.warning_codes or [])
        issues = ", ".join(issue_codes[:3]) if issue_codes else "general quality improvements"
        return (
            "Auto challenger branch. "
            "The current version delivered successfully but did not pass the quality gate. "
            f"Current score {score_text} is below threshold {threshold_text}. "
            f"Focus on {issues}. "
            "Preserve the working render path, keep the core prompt intent, and produce a stronger alternative "
            "with better motion, clarity, or prompt alignment while staying render-safe."
        )

    def _load_quality_scorecard_json(self, task_id: str) -> dict[str, Any] | None:
        scorecard = self.store.get_task_quality_score(task_id)
        if scorecard is not None:
            return scorecard.model_dump(mode="json")
        return self.artifact_store.read_quality_score(task_id)

    def _record_case_memory_branch_state(self, task) -> None:
        if self.case_memory_service is None:
            return
        root_task_id = task.root_task_id or task.task_id
        delivery_case = self.store.get_delivery_case(root_task_id)
        selected_task_id = None if delivery_case is None else delivery_case.selected_task_id
        active_task_id = None if delivery_case is None else delivery_case.active_task_id
        lineage = self.store.list_lineage_tasks(root_task_id)
        branch_scoreboard = build_branch_scoreboard(
            lineage_tasks=lineage,
            scorecards_by_task_id={
                lineage_task.task_id: self._load_quality_scorecard_json(lineage_task.task_id)
                for lineage_task in lineage
            },
            selected_task_id=selected_task_id,
            active_task_id=active_task_id,
        )
        arbitration_summary = build_arbitration_summary(
            branch_scoreboard=branch_scoreboard,
            selected_task_id=selected_task_id,
            active_task_id=active_task_id,
        )
        self.case_memory_service.record_branch_state(
            root_task_id,
            branch_scoreboard=branch_scoreboard,
            arbitration_summary=arbitration_summary,
        )

    def _finalize_guaranteed_delivery(self, task, delivery_decision) -> None:
        artifact_path = Path(delivery_decision.video_path)
        task.best_result_artifact_id = self.store.register_artifact(
            task.task_id,
            "final_video",
            artifact_path,
            metadata={"completion_mode": delivery_decision.completion_mode, "delivery_tier": delivery_decision.delivery_tier},
        )
        task.status = TaskStatus.COMPLETED
        task.phase = TaskPhase.COMPLETED
        task.delivery_status = "delivered"
        task.resolved_task_id = task.task_id
        task.completion_mode = delivery_decision.completion_mode
        task.delivery_tier = delivery_decision.delivery_tier
        task.delivery_stop_reason = None
        self.store.update_task(task)
        self.artifact_store.write_task_snapshot(task)
        self._sync_root_delivery_resolution(task)
        self.store.append_event(
            task.task_id,
            "task_finished",
            {"status": task.status.value, "completion_mode": task.completion_mode},
        )

    def _mark_delivery_failed(self, task, *, stop_reason: str) -> None:
        task.delivery_status = "failed"
        task.delivery_stop_reason = stop_reason
        self.store.update_task(task)
        self.artifact_store.write_task_snapshot(task)

        root_task_id = task.root_task_id or task.task_id
        if root_task_id == task.task_id:
            return

        root_task = self.store.get_task(root_task_id)
        if root_task is None:
            return
        root_task.delivery_status = "failed"
        root_task.delivery_stop_reason = stop_reason
        self.store.update_task(root_task)
        self.artifact_store.write_task_snapshot(root_task)
        if self.delivery_case_service is not None:
            self.delivery_case_service.sync_case_for_root(root_task_id)

    def _sync_root_delivery_resolution(self, task) -> None:
        root_task_id = task.root_task_id or task.task_id
        root_task = self.store.get_task(root_task_id)
        if root_task is None:
            return
        if task.task_id != root_task_id and task.branch_kind == "challenger":
            if self.delivery_case_service is not None:
                self.delivery_case_service.sync_case_for_root(root_task_id)
            return
        root_task.delivery_status = "delivered"
        root_task.resolved_task_id = task.task_id
        root_task.completion_mode = task.completion_mode
        root_task.delivery_tier = task.delivery_tier
        root_task.delivery_stop_reason = None
        root_task.status = TaskStatus.COMPLETED
        root_task.phase = TaskPhase.COMPLETED
        self.store.update_task(root_task)
        self.artifact_store.write_task_snapshot(root_task)
        if self.delivery_case_service is not None:
            self.delivery_case_service.sync_case_for_root(root_task_id)

    def _resolve_render_profile(self, task) -> dict[str, Any]:
        settings = self.runtime_service.settings
        effective_profile = {}
        if getattr(task, "effective_request_profile", None):
            effective_profile = task.effective_request_profile.get("output_profile", {})
        profile = effective_profile or task.output_profile or {}
        return {
            "quality_preset": str(profile.get("quality_preset", settings.default_quality_preset)),
            "frame_rate": self._optional_positive_int(profile.get("frame_rate", settings.default_frame_rate)),
            "pixel_width": self._optional_positive_int(
                profile.get("pixel_width", profile.get("width", settings.default_pixel_width))
            ),
            "pixel_height": self._optional_positive_int(
                profile.get("pixel_height", profile.get("height", settings.default_pixel_height))
            ),
        }

    @staticmethod
    def _optional_positive_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _transition(self, task, phase: TaskPhase) -> None:
        task.phase = phase
        self.store.update_task(task)
        self.artifact_store.write_task_snapshot(task)
        self.store.append_event(task.task_id, "phase_changed", {"phase": task.phase.value})
        self._log(task, phase, "Phase changed")

    def _log(self, task, phase: TaskPhase, message: str, **extra: Any) -> None:
        event = build_log_event(
            task_id=task.task_id,
            phase=phase.value,
            message=message,
            attempt_count=task.attempt_count,
            **extra,
        )
        self.store.append_event(task.task_id, "task_log", event)
        log_path = self.artifact_store.task_log_path(task.task_id)
        if self.runtime_policy.is_allowed_write(log_path):
            self.artifact_store.append_task_log(task.task_id, event)
