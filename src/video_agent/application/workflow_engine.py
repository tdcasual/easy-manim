from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from video_agent.adapters.llm.client import LLMClient
from video_agent.adapters.llm.script_sanitizer import sanitize_script_text
from video_agent.adapters.llm.openai_compatible_client import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from video_agent.adapters.rendering.frame_extractor import FrameExtractor
from video_agent.adapters.rendering.manim_runner import ManimRunner
from video_agent.adapters.storage.artifact_store import ArtifactStore
from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.application.auto_repair_service import AutoRepairService
from video_agent.application.failure_context import build_failure_context
from video_agent.application.runtime_service import RuntimeService
from video_agent.application.scene_plan import build_scene_plan
from video_agent.application.session_memory_service import SessionMemoryService
from video_agent.application.workflow_phases import (
    combined_validation_report,
    latex_dependency_report,
    provider_failure_report,
    render_failure_report,
    terminal_task_state,
)
from video_agent.domain.enums import TaskPhase, TaskStatus, ValidationDecision
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
        session_memory_service: SessionMemoryService | None = None,
        runtime_policy: RuntimePolicy | None = None,
        metrics: MetricsCollector | None = None,
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
        self.session_memory_service = session_memory_service
        self.runtime_policy = runtime_policy or RuntimePolicy(work_root=artifact_store.root)
        self.metrics = metrics or MetricsCollector()
        self.auto_repair_service = AutoRepairService(
            store=store,
            artifact_store=artifact_store,
            settings=runtime_service.settings,
        )

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
        self._transition(task, TaskPhase.PLANNING)

        try:
            render_profile = self._resolve_render_profile(task)
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
            self._log(
                task,
                TaskPhase.PLANNING,
                "Scene plan generated",
                scene_class=scene_plan.scene_class,
                camera_strategy=scene_plan.camera_strategy,
            )
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

            self._transition(task, TaskPhase.FRAME_EXTRACT)
            preview_dir = self.artifact_store.previews_dir(task.task_id)
            if not self._ensure_allowed_artifact_path(task, TaskPhase.FRAME_EXTRACT, preview_dir, "preview directory"):
                return
            preview_paths = self.frame_extractor.extract(final_video_path, preview_dir)
            for preview_path in preview_paths:
                self.store.register_artifact(task.task_id, "preview_frame", preview_path)
            self._log(task, TaskPhase.FRAME_EXTRACT, "Preview extraction completed", preview_count=len(preview_paths))

            self._transition(task, TaskPhase.VALIDATION)
            validation_started = time.monotonic()
            hard_report = self.hard_validator.validate(final_video_path, profile=task.validation_profile)
            rule_report = self.rule_validator.validate(final_video_path, profile=task.validation_profile)
            preview_report = self.preview_quality_validator.validate(preview_paths, profile=task.validation_profile)
            self.metrics.increment("validation_runs")
            self.metrics.record_timing("validation_seconds", time.monotonic() - validation_started)
            combined_report = combined_validation_report(hard_report, rule_report, preview_report)
            validation_report_path = self.artifact_store.validation_report_path(task.task_id)
            if not self._ensure_allowed_artifact_path(task, TaskPhase.VALIDATION, validation_report_path, "validation report"):
                return
            report_path = self.artifact_store.write_validation_report(task.task_id, combined_report)
            self.store.record_validation(task.task_id, combined_report)
            self.store.register_artifact(task.task_id, "validation_report", report_path)

            task.status, task.phase = terminal_task_state(combined_report)
            if combined_report.passed:
                self.metrics.increment("tasks_completed")
            else:
                self.metrics.increment("tasks_failed")
            self.store.update_task(task)
            self.artifact_store.write_task_snapshot(task)
            self.store.append_event(task.task_id, "task_finished", {"status": task.status.value})
            self._record_session_memory_outcome(
                task,
                result_summary=combined_report.summary,
                extra_artifact_refs=[self.artifact_store.resource_uri(task.task_id, report_path)],
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
        auto_repair_decision = self.auto_repair_service.maybe_schedule_repair(task)
        self._record_repair_state(task, report, auto_repair_decision)
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
        self._log(
            task,
            TaskPhase.FAILED,
            "Task failed",
            issues=[issue.code for issue in report.issues],
            summary=report.summary,
        )
        self.metrics.increment("tasks_failed")

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

    def _resolve_render_profile(self, task) -> dict[str, Any]:
        settings = self.runtime_service.settings
        profile = task.output_profile or {}
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
