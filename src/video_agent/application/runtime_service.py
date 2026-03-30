from __future__ import annotations

from collections import Counter
import json
import shlex
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from video_agent.adapters.storage.sqlite_store import SQLiteTaskStore
from video_agent.config import DEFAULT_STUB_LLM_MODEL, Settings
from video_agent.domain.enums import TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.safety.runtime_policy import RuntimePolicy
from video_agent.validation.runtime_smoke import run_mathtex_smoke
from video_agent.version import get_release_metadata


class RuntimeCheckResult(BaseModel):
    command: str
    available: bool
    resolved_path: Optional[str] = None


class RuntimeFeatureStatus(BaseModel):
    checked: bool = False
    available: bool
    missing_checks: list[str] = Field(default_factory=list)
    smoke_error: Optional[str] = None


class RuntimeProviderStatus(BaseModel):
    mode: str
    configured: bool
    api_base_present: bool


class RuntimeWorkerHeartbeat(BaseModel):
    worker_id: str
    identity: str
    last_seen_at: str
    details: dict[str, object] = Field(default_factory=dict)
    stale: bool


class RuntimeWorkerStatus(BaseModel):
    embedded: bool
    workers: list[RuntimeWorkerHeartbeat] = Field(default_factory=list)


class RuntimeStorageStatus(BaseModel):
    data_dir: str
    database_path: str
    artifact_root: str


class RuntimeReleaseStatus(BaseModel):
    version: str
    channel: str


class RuntimeSandboxStatus(BaseModel):
    network_disabled: bool
    temp_root: str
    temp_root_allowed: bool
    process_limit: int | None = None
    memory_limit_mb: int | None = None
    resource_limits_supported: bool


class RuntimeCapabilityStatus(BaseModel):
    rollout_profile: str
    effective: dict[str, bool]


class RuntimeAutonomyGuardStatus(BaseModel):
    enabled: bool
    allowed: bool
    reasons: list[str] = Field(default_factory=list)
    canary_available: bool
    canary_delivered: bool | None = None
    delivery_rate: float
    min_delivery_rate: float
    emergency_fallback_rate: float
    max_emergency_fallback_rate: float
    branch_rejection_rate: float
    max_branch_rejection_rate: float


class RuntimeTaskProcessingStatus(BaseModel):
    ready: bool
    checked_at: str
    reasons: list[str] = Field(default_factory=list)
    artifact_root_writable: bool
    database_writable: bool
    core_binaries_available: bool


class RuntimeDeliveryStopReason(BaseModel):
    reason: str
    count: int


class RuntimeDeliverySummary(BaseModel):
    total_roots: int
    delivered_roots: int
    failed_roots: int
    pending_roots: int
    delivery_rate: float
    emergency_fallback_rate: float
    case_status_counts: dict[str, int] = Field(default_factory=dict)
    agent_run_status_counts: dict[str, int] = Field(default_factory=dict)
    agent_run_role_status_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    agent_run_stop_reason_counts: dict[str, int] = Field(default_factory=dict)
    completion_modes: dict[str, int] = Field(default_factory=dict)
    challenger_branches_completed: int
    challenger_branches_rejected: int
    branch_rejection_rate: float
    arbitration_attempts: int
    arbitration_successes: int
    arbitration_success_rate: float
    repair_loop_saturation_count: int
    repair_loop_saturation_rate: float
    top_stop_reasons: list[RuntimeDeliveryStopReason] = Field(default_factory=list)


class RuntimeDeliveryCanaryStatus(BaseModel):
    available: bool
    last_run: dict[str, object] | None = None


class RuntimeStatus(BaseModel):
    storage: RuntimeStorageStatus
    provider: RuntimeProviderStatus
    worker: RuntimeWorkerStatus
    release: RuntimeReleaseStatus
    sandbox: RuntimeSandboxStatus
    capabilities: RuntimeCapabilityStatus
    autonomy_guard: RuntimeAutonomyGuardStatus
    task_processing: RuntimeTaskProcessingStatus
    delivery_summary: RuntimeDeliverySummary
    delivery_canary: RuntimeDeliveryCanaryStatus
    checks: dict[str, RuntimeCheckResult]
    features: dict[str, RuntimeFeatureStatus]


class RuntimeService:
    CORE_CHECK_NAMES = ("manim", "ffprobe")
    MATHTEX_CHECK_NAMES = ("latex", "dvisvgm")

    def __init__(
        self,
        settings: Settings,
        store: SQLiteTaskStore | None = None,
        runtime_policy: RuntimePolicy | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.runtime_policy = runtime_policy

    def inspect(self, run_feature_smoke: bool = False) -> RuntimeStatus:
        checks = self.inspect_checks()
        task_processing = self.inspect_task_processing(checks)
        delivery_summary = self.inspect_delivery_summary()
        delivery_canary = self.inspect_delivery_canary()
        return RuntimeStatus(
            storage=RuntimeStorageStatus(
                data_dir=str(self.settings.data_dir),
                database_path=str(self.settings.database_path),
                artifact_root=str(self.settings.artifact_root),
            ),
            provider=RuntimeProviderStatus(
                mode=self.settings.llm_provider,
                configured=self._provider_configured(),
                api_base_present=bool(self.settings.llm_api_base),
            ),
            worker=RuntimeWorkerStatus(
                embedded=self.settings.run_embedded_worker,
                workers=self._load_workers(),
            ),
            release=RuntimeReleaseStatus(
                version=get_release_metadata()["version"],
                channel=self.settings.release_channel,
            ),
            sandbox=RuntimeSandboxStatus.model_validate(self._sandbox_status()),
            capabilities=RuntimeCapabilityStatus(
                rollout_profile=self.settings.capability_rollout_profile,
                effective={
                    "agent_learning_auto_apply_enabled": self.settings.agent_learning_auto_apply_enabled,
                    "auto_repair_enabled": self.settings.auto_repair_enabled,
                    "delivery_guarantee_enabled": self.settings.delivery_guarantee_enabled,
                    "multi_agent_workflow_enabled": self.settings.multi_agent_workflow_enabled,
                    "multi_agent_workflow_auto_challenger_enabled": self.settings.multi_agent_workflow_auto_challenger_enabled,
                    "multi_agent_workflow_auto_arbitration_enabled": self.settings.multi_agent_workflow_auto_arbitration_enabled,
                    "multi_agent_workflow_guarded_rollout_enabled": self.settings.multi_agent_workflow_guarded_rollout_enabled,
                    "strategy_promotion_enabled": self.settings.strategy_promotion_enabled,
                    "strategy_promotion_guarded_auto_apply_enabled": self.settings.strategy_promotion_guarded_auto_apply_enabled,
                },
            ),
            autonomy_guard=self.inspect_multi_agent_autonomy_guard(
                delivery_summary=delivery_summary,
                delivery_canary=delivery_canary,
            ),
            task_processing=task_processing,
            delivery_summary=delivery_summary,
            delivery_canary=delivery_canary,
            checks=checks,
            features={
                "mathtex": self.inspect_mathtex_feature(checks, run_smoke=run_feature_smoke),
            },
        )

    def inspect_checks(self) -> dict[str, RuntimeCheckResult]:
        return {
            "manim": self._check_command(self.settings.manim_command),
            "ffmpeg": self._check_command(self.settings.ffmpeg_command),
            "ffprobe": self._check_command(self.settings.ffprobe_command),
            "latex": self._check_command(self.settings.latex_command),
            "dvisvgm": self._check_command(self.settings.dvisvgm_command),
        }

    def inspect_mathtex_feature(
        self,
        checks: dict[str, RuntimeCheckResult] | None = None,
        *,
        run_smoke: bool = False,
    ) -> RuntimeFeatureStatus:
        effective_checks = checks or self.inspect_checks()
        missing = [name for name in self.MATHTEX_CHECK_NAMES if not effective_checks[name].available]
        if missing:
            return RuntimeFeatureStatus(
                checked=False,
                available=False,
                missing_checks=missing,
                smoke_error=None,
            )
        if not run_smoke:
            return RuntimeFeatureStatus(
                checked=False,
                available=True,
                missing_checks=[],
                smoke_error=None,
            )

        smoke_result = run_mathtex_smoke(
            work_dir=self.settings.data_dir / ".runtime-smoke" / "mathtex",
            latex_command=self.settings.latex_command,
            dvisvgm_command=self.settings.dvisvgm_command,
        )
        return RuntimeFeatureStatus(
            checked=smoke_result.checked,
            available=smoke_result.available,
            missing_checks=[],
            smoke_error=smoke_result.error,
        )

    def inspect_task_processing(
        self,
        checks: dict[str, RuntimeCheckResult] | None = None,
    ) -> RuntimeTaskProcessingStatus:
        effective_checks = checks or self.inspect_checks()
        reasons: list[str] = []
        artifact_root_writable = self._directory_writable(self.settings.artifact_root)
        if not artifact_root_writable:
            reasons.append("artifact_root_not_writable")
        database_writable = self._directory_writable(self.settings.database_path.parent)
        if not database_writable:
            reasons.append("database_not_writable")
        missing_core = [
            name for name in self.CORE_CHECK_NAMES if not effective_checks.get(name, RuntimeCheckResult(command=name, available=False)).available
        ]
        for name in missing_core:
            reasons.append(f"missing_core_binary:{name}")
        return RuntimeTaskProcessingStatus(
            ready=not reasons,
            checked_at=datetime.now(timezone.utc).isoformat(),
            reasons=reasons,
            artifact_root_writable=artifact_root_writable,
            database_writable=database_writable,
            core_binaries_available=not missing_core,
        )

    def inspect_delivery_summary(self) -> RuntimeDeliverySummary:
        roots = self._load_root_tasks()
        total_roots = len(roots)
        if total_roots == 0:
            return RuntimeDeliverySummary(
                total_roots=0,
                delivered_roots=0,
                failed_roots=0,
                pending_roots=0,
                delivery_rate=0.0,
                emergency_fallback_rate=0.0,
                case_status_counts={},
                agent_run_status_counts={},
                agent_run_role_status_counts={},
                agent_run_stop_reason_counts={},
                completion_modes={},
                challenger_branches_completed=0,
                challenger_branches_rejected=0,
                branch_rejection_rate=0.0,
                arbitration_attempts=0,
                arbitration_successes=0,
                arbitration_success_rate=0.0,
                repair_loop_saturation_count=0,
                repair_loop_saturation_rate=0.0,
                top_stop_reasons=[],
            )

        delivered_roots = 0
        failed_roots = 0
        emergency_fallback_roots = 0
        case_status_counts: Counter[str] = Counter()
        agent_run_status_counts: Counter[str] = Counter()
        agent_run_role_status_counts: dict[str, Counter[str]] = {}
        agent_run_stop_reason_counts: Counter[str] = Counter()
        completion_modes: Counter[str] = Counter()
        stop_reasons: Counter[str] = Counter()
        completed_challenger_count = 0
        rejected_challenger_count = 0
        arbitration_attempt_count = 0
        arbitration_success_count = 0
        repair_loop_saturation_count = 0

        for task in roots:
            if task.delivery_status == "delivered":
                delivered_roots += 1
                if task.completion_mode:
                    completion_modes[str(task.completion_mode)] += 1
                if task.completion_mode == "emergency_fallback":
                    emergency_fallback_roots += 1
            elif task.delivery_status == "failed":
                failed_roots += 1
                if task.delivery_stop_reason:
                    stop_reasons[task.delivery_stop_reason] += 1
            if task.repair_stop_reason == "budget_exhausted":
                repair_loop_saturation_count += 1

            delivery_case = self.store.get_delivery_case(task.task_id)
            if delivery_case is not None and delivery_case.status:
                case_status_counts[str(delivery_case.status)] += 1

            lifecycle_runs = [
                run
                for run in self.store.list_agent_runs(task.task_id)
                if bool(run.metadata.get("lifecycle"))
            ]
            for run in lifecycle_runs:
                if run.status:
                    agent_run_status_counts[str(run.status)] += 1
                    role_counts = agent_run_role_status_counts.setdefault(str(run.role), Counter())
                    role_counts[str(run.status)] += 1
                if run.stop_reason:
                    agent_run_stop_reason_counts[str(run.stop_reason)] += 1

            orchestrator_runs = self.store.list_agent_runs(task.task_id, role="orchestrator")
            arbitration_runs = [
                run
                for run in orchestrator_runs
                if run.decision.get("action") == "auto_arbitration_evaluated"
            ]
            has_resolved_branch_outcome = bool(arbitration_runs) or any(
                run.decision.get("action") == "winner_selected" for run in orchestrator_runs
            )
            if has_resolved_branch_outcome:
                for lineage_task in self.store.list_lineage_tasks(task.task_id):
                    if lineage_task.task_id == task.task_id or lineage_task.branch_kind != "challenger":
                        continue
                    if lineage_task.status is TaskStatus.COMPLETED and lineage_task.delivery_status == "delivered":
                        completed_challenger_count += 1
                        if not lineage_task.accepted_as_best:
                            rejected_challenger_count += 1
            if arbitration_runs:
                arbitration_attempt_count += 1
                if any(bool(run.decision.get("promoted")) for run in arbitration_runs):
                    arbitration_success_count += 1

        pending_roots = total_roots - delivered_roots - failed_roots
        top_stop_reasons = [
            RuntimeDeliveryStopReason(reason=reason, count=count)
            for reason, count in sorted(stop_reasons.items(), key=lambda item: (-item[1], item[0]))
        ]
        return RuntimeDeliverySummary(
            total_roots=total_roots,
            delivered_roots=delivered_roots,
            failed_roots=failed_roots,
            pending_roots=pending_roots,
            delivery_rate=delivered_roots / total_roots,
            emergency_fallback_rate=emergency_fallback_roots / total_roots,
            case_status_counts=dict(sorted(case_status_counts.items())),
            agent_run_status_counts=dict(sorted(agent_run_status_counts.items())),
            agent_run_role_status_counts={
                role: dict(sorted(counts.items()))
                for role, counts in sorted(agent_run_role_status_counts.items())
            },
            agent_run_stop_reason_counts=dict(sorted(agent_run_stop_reason_counts.items())),
            completion_modes=dict(sorted(completion_modes.items())),
            challenger_branches_completed=completed_challenger_count,
            challenger_branches_rejected=rejected_challenger_count,
            branch_rejection_rate=0.0
            if completed_challenger_count == 0
            else rejected_challenger_count / completed_challenger_count,
            arbitration_attempts=arbitration_attempt_count,
            arbitration_successes=arbitration_success_count,
            arbitration_success_rate=0.0
            if arbitration_attempt_count == 0
            else arbitration_success_count / arbitration_attempt_count,
            repair_loop_saturation_count=repair_loop_saturation_count,
            repair_loop_saturation_rate=repair_loop_saturation_count / total_roots,
            top_stop_reasons=top_stop_reasons,
        )

    def inspect_delivery_canary(self) -> RuntimeDeliveryCanaryStatus:
        target = self.settings.eval_root / "delivery-canary" / "latest.json"
        if not target.exists():
            return RuntimeDeliveryCanaryStatus(available=False, last_run=None)
        try:
            payload = json.loads(target.read_text())
        except (OSError, json.JSONDecodeError):
            return RuntimeDeliveryCanaryStatus(available=False, last_run=None)
        return RuntimeDeliveryCanaryStatus(available=True, last_run=payload)

    def inspect_multi_agent_autonomy_guard(
        self,
        *,
        delivery_summary: RuntimeDeliverySummary | None = None,
        delivery_canary: RuntimeDeliveryCanaryStatus | None = None,
    ) -> RuntimeAutonomyGuardStatus:
        summary = delivery_summary or self.inspect_delivery_summary()
        canary = delivery_canary or self.inspect_delivery_canary()
        canary_delivered = None
        if isinstance(canary.last_run, dict):
            canary_delivered = bool(canary.last_run.get("delivered"))

        if not self.settings.multi_agent_workflow_guarded_rollout_enabled:
            return RuntimeAutonomyGuardStatus(
                enabled=False,
                allowed=True,
                reasons=[],
                canary_available=canary.available,
                canary_delivered=canary_delivered,
                delivery_rate=summary.delivery_rate,
                min_delivery_rate=self.settings.multi_agent_workflow_guarded_min_delivery_rate,
                emergency_fallback_rate=summary.emergency_fallback_rate,
                max_emergency_fallback_rate=self.settings.multi_agent_workflow_guarded_max_emergency_fallback_rate,
                branch_rejection_rate=summary.branch_rejection_rate,
                max_branch_rejection_rate=self.settings.multi_agent_workflow_guarded_max_branch_rejection_rate,
            )

        reasons: list[str] = []
        if not canary.available:
            reasons.append("delivery_canary_unavailable")
        elif not canary_delivered:
            reasons.append("delivery_canary_unhealthy")
        if summary.total_roots > 0 and summary.delivery_rate < self.settings.multi_agent_workflow_guarded_min_delivery_rate:
            reasons.append("delivery_rate_below_threshold")
        if (
            summary.total_roots > 0
            and summary.emergency_fallback_rate > self.settings.multi_agent_workflow_guarded_max_emergency_fallback_rate
        ):
            reasons.append("emergency_fallback_rate_above_threshold")
        if (
            summary.challenger_branches_completed > 0
            and summary.branch_rejection_rate > self.settings.multi_agent_workflow_guarded_max_branch_rejection_rate
        ):
            reasons.append("branch_rejection_rate_above_threshold")
        return RuntimeAutonomyGuardStatus(
            enabled=True,
            allowed=not reasons,
            reasons=reasons,
            canary_available=canary.available,
            canary_delivered=canary_delivered,
            delivery_rate=summary.delivery_rate,
            min_delivery_rate=self.settings.multi_agent_workflow_guarded_min_delivery_rate,
            emergency_fallback_rate=summary.emergency_fallback_rate,
            max_emergency_fallback_rate=self.settings.multi_agent_workflow_guarded_max_emergency_fallback_rate,
            branch_rejection_rate=summary.branch_rejection_rate,
            max_branch_rejection_rate=self.settings.multi_agent_workflow_guarded_max_branch_rejection_rate,
        )

    def _load_workers(self) -> list[RuntimeWorkerHeartbeat]:
        if self.store is None:
            return []

        now = datetime.now(timezone.utc)
        workers: list[RuntimeWorkerHeartbeat] = []
        for item in self.store.list_worker_heartbeats():
            last_seen = datetime.fromisoformat(item["last_seen_at"])
            stale = (now - last_seen).total_seconds() > self.settings.worker_stale_after_seconds
            workers.append(
                RuntimeWorkerHeartbeat(
                    worker_id=item["worker_id"],
                    identity=str(item["details"].get("worker_identity", item["worker_id"])),
                    last_seen_at=item["last_seen_at"],
                    details=item["details"],
                    stale=stale,
                )
            )
        return workers

    def _load_root_tasks(self) -> list[VideoTask]:
        if self.store is None:
            return []

        roots: list[VideoTask] = []
        seen: set[str] = set()
        for row in self.store.list_tasks(limit=None, order_by="updated_at"):
            task = self.store.get_task(row["task_id"])
            if task is None or task.task_id in seen:
                continue
            if (task.root_task_id or task.task_id) != task.task_id:
                continue
            seen.add(task.task_id)
            roots.append(task)
        return roots

    def _provider_configured(self) -> bool:
        if self.settings.llm_provider == "stub":
            return True
        if self.settings.llm_provider == "litellm":
            return bool(self.settings.llm_model and self.settings.llm_model != DEFAULT_STUB_LLM_MODEL)
        return False

    def _directory_writable(self, directory: Path) -> bool:
        target = Path(directory)
        probe = target / ".runtime-write-check"
        try:
            target.mkdir(parents=True, exist_ok=True)
            probe.write_text("ok")
            probe.unlink()
            return True
        except OSError:
            return False

    def _sandbox_status(self) -> dict[str, object]:
        policy = self.runtime_policy or RuntimePolicy(
            work_root=self.settings.artifact_root,
            render_timeout_seconds=self.settings.render_timeout_seconds,
            network_disabled=self.settings.sandbox_network_disabled,
            process_limit=self.settings.sandbox_process_limit,
            memory_limit_mb=self.settings.sandbox_memory_limit_mb,
            temp_root=self.settings.sandbox_temp_root,
        )
        return policy.describe()

    def _check_command(self, command: str) -> RuntimeCheckResult:
        executable = self._extract_executable(command)
        resolved_path = None
        if executable is not None:
            path = Path(executable)
            if path.is_absolute():
                if path.exists():
                    resolved_path = str(path)
            else:
                resolved_path = shutil.which(executable)
        return RuntimeCheckResult(
            command=command,
            available=resolved_path is not None,
            resolved_path=resolved_path,
        )

    @staticmethod
    def _extract_executable(command: str) -> Optional[str]:
        parts = shlex.split(command)
        if not parts:
            return None
        return parts[0]
