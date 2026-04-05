import importlib
import importlib.util
from types import SimpleNamespace

from video_agent.domain.enums import TaskPhase, TaskStatus
from video_agent.domain.models import VideoTask
from video_agent.domain.quality_models import QualityScorecard


MODULE_NAME = "video_agent.application.workflow_quality_escalation"


def _load_module():
    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    return importlib.import_module(MODULE_NAME)


class _FakeTaskService:
    def __init__(self) -> None:
        self.challenger_calls: list[dict[str, object]] = []
        self.degraded_calls: list[dict[str, object]] = []
        self.accepted_task_ids: list[str] = []

    def create_challenger_task(self, parent_task_id: str, *, feedback: str, session_id: str | None):
        self.challenger_calls.append(
            {
                "parent_task_id": parent_task_id,
                "feedback": feedback,
                "session_id": session_id,
            }
        )
        return SimpleNamespace(task_id="challenger-child")

    def create_degraded_delivery_task(
        self,
        parent_task_id: str,
        *,
        feedback: str,
        generation_mode: str,
        style_hints: dict[str, object],
        output_profile: dict[str, object],
    ):
        self.degraded_calls.append(
            {
                "parent_task_id": parent_task_id,
                "feedback": feedback,
                "generation_mode": generation_mode,
                "style_hints": style_hints,
                "output_profile": output_profile,
            }
        )
        return SimpleNamespace(task_id="degraded-child")

    def accept_best_version(self, task_id: str) -> None:
        self.accepted_task_ids.append(task_id)


class _FakeStore:
    def __init__(
        self,
        *,
        lineage_tasks: list[VideoTask] | None = None,
        delivery_case=None,
        scorecards_by_task_id: dict[str, QualityScorecard | None] | None = None,
    ) -> None:
        self._lineage_tasks = lineage_tasks or []
        self._delivery_case = delivery_case
        self._scorecards_by_task_id = scorecards_by_task_id or {}

    def list_lineage_tasks(self, root_task_id: str) -> list[VideoTask]:
        return list(self._lineage_tasks)

    def get_delivery_case(self, root_task_id: str):
        return self._delivery_case

    def get_task_quality_score(self, task_id: str) -> QualityScorecard | None:
        return self._scorecards_by_task_id.get(task_id)


class _FakeArtifactStore:
    def __init__(
        self,
        *,
        failure_contract: dict[str, object] | None = None,
        recovery_plan: dict[str, object] | None = None,
        quality_scores: dict[str, dict[str, object] | None] | None = None,
    ) -> None:
        self.failure_contract = failure_contract or {}
        self.recovery_plan = recovery_plan or {}
        self.quality_scores = quality_scores or {}

    def read_failure_contract(self, task_id: str) -> dict[str, object]:
        return dict(self.failure_contract)

    def read_recovery_plan(self, task_id: str) -> dict[str, object]:
        return dict(self.recovery_plan)

    def read_quality_score(self, task_id: str) -> dict[str, object] | None:
        return self.quality_scores.get(task_id)


def _runtime_service(
    *,
    multi_agent_enabled: bool = True,
    auto_challenger_enabled: bool = True,
    auto_arbitration_enabled: bool = True,
    delivery_guarantee_enabled: bool = True,
    quality_gate_min_score: float = 0.75,
    guard_enabled: bool = False,
    guard_allowed: bool = True,
    guard_reasons: list[str] | None = None,
):
    settings = SimpleNamespace(
        multi_agent_workflow_enabled=multi_agent_enabled,
        multi_agent_workflow_auto_challenger_enabled=auto_challenger_enabled,
        multi_agent_workflow_auto_arbitration_enabled=auto_arbitration_enabled,
        delivery_guarantee_enabled=delivery_guarantee_enabled,
        quality_gate_min_score=quality_gate_min_score,
    )
    guard = SimpleNamespace(
        enabled=guard_enabled,
        allowed=guard_allowed,
        reasons=list(guard_reasons or []),
    )
    return SimpleNamespace(
        settings=settings,
        inspect_multi_agent_autonomy_guard=lambda: guard,
    )


def _task(
    *,
    task_id: str = "task-1",
    root_task_id: str = "task-1",
    parent_task_id: str | None = None,
    branch_kind: str | None = None,
    status: TaskStatus = TaskStatus.COMPLETED,
    phase: TaskPhase = TaskPhase.COMPLETED,
    delivery_status: str | None = "delivered",
    quality_gate_status: str | None = "needs_revision",
    completion_mode: str | None = "repaired",
    generation_mode: str | None = "guided_generate",
    session_id: str | None = "session-1",
) -> VideoTask:
    return VideoTask(
        task_id=task_id,
        root_task_id=root_task_id,
        parent_task_id=parent_task_id,
        branch_kind=branch_kind,
        status=status,
        phase=phase,
        prompt="Make a clean explainer animation",
        delivery_status=delivery_status,
        quality_gate_status=quality_gate_status,
        completion_mode=completion_mode,
        generation_mode=generation_mode,
        session_id=session_id,
        style_hints={"tone": "clean"},
        output_profile={"aspect_ratio": "16:9"},
    )


def test_maybe_schedule_quality_challenger_reports_governance_disabled_when_auto_flag_off() -> None:
    module = _load_module()
    decision = module.maybe_schedule_quality_challenger(
        _task(),
        QualityScorecard(total_score=0.55, warning_codes=["timing_overlap"]),
        runtime_service=_runtime_service(auto_challenger_enabled=False),
        auto_repair_service=SimpleNamespace(task_service=_FakeTaskService()),
    )

    assert decision == {
        "created": False,
        "reason": "auto_challenger_governance_disabled",
        "child_task_id": None,
        "quality_gate_status": "needs_revision",
        "overall_score": 0.55,
    }


def test_maybe_schedule_quality_challenger_reports_guarded_rollout_blockers() -> None:
    module = _load_module()
    decision = module.maybe_schedule_quality_challenger(
        _task(),
        QualityScorecard(total_score=0.6, must_fix_issues=["static_previews"]),
        runtime_service=_runtime_service(
            guard_enabled=True,
            guard_allowed=False,
            guard_reasons=["delivery_canary_unhealthy"],
        ),
        auto_repair_service=SimpleNamespace(task_service=_FakeTaskService()),
    )

    assert decision["created"] is False
    assert decision["reason"] == "guarded_rollout_blocked"
    assert decision["blocked_reasons"] == ["delivery_canary_unhealthy"]
    assert decision["child_task_id"] is None


def test_maybe_schedule_quality_challenger_creates_child_task_with_feedback() -> None:
    module = _load_module()
    task_service = _FakeTaskService()
    decision = module.maybe_schedule_quality_challenger(
        _task(),
        QualityScorecard(total_score=0.61, must_fix_issues=["timing_overlap"]),
        runtime_service=_runtime_service(quality_gate_min_score=0.8),
        auto_repair_service=SimpleNamespace(task_service=task_service),
    )

    assert decision["created"] is True
    assert decision["reason"] == "created"
    assert decision["child_task_id"] == "challenger-child"
    assert task_service.challenger_calls[0]["parent_task_id"] == "task-1"
    assert task_service.challenger_calls[0]["session_id"] == "session-1"
    assert "timing_overlap" in str(task_service.challenger_calls[0]["feedback"])
    assert "below threshold 0.80" in str(task_service.challenger_calls[0]["feedback"])


def test_maybe_auto_promote_challenger_returns_quality_not_accepted_for_unaccepted_branch() -> None:
    module = _load_module()
    task = _task(task_id="challenger-1", root_task_id="root-1", parent_task_id="root-1", branch_kind="challenger")
    task.quality_gate_status = "needs_revision"

    decision = module.maybe_auto_promote_challenger(
        task,
        runtime_service=_runtime_service(),
        store=_FakeStore(),
        artifact_store=_FakeArtifactStore(),
        auto_repair_service=SimpleNamespace(task_service=_FakeTaskService()),
    )

    assert decision == {
        "promoted": False,
        "reason": "quality_not_accepted",
        "recommended_task_id": "challenger-1",
        "recommended_action": "wait_for_completion",
        "selected_task_id": None,
    }


def test_maybe_auto_promote_challenger_promotes_selected_accepted_branch() -> None:
    module = _load_module()
    task_service = _FakeTaskService()
    root = _task(task_id="root-1", root_task_id="root-1", quality_gate_status="accepted")
    challenger = _task(
        task_id="challenger-1",
        root_task_id="root-1",
        parent_task_id="root-1",
        branch_kind="challenger",
        quality_gate_status="accepted",
    )
    decision = module.maybe_auto_promote_challenger(
        challenger,
        runtime_service=_runtime_service(),
        store=_FakeStore(
            lineage_tasks=[root, challenger],
            delivery_case=SimpleNamespace(selected_task_id="root-1", active_task_id="challenger-1"),
            scorecards_by_task_id={
                "root-1": QualityScorecard(total_score=0.72, accepted=True),
                "challenger-1": QualityScorecard(total_score=0.91, accepted=True),
            },
        ),
        artifact_store=_FakeArtifactStore(),
        auto_repair_service=SimpleNamespace(task_service=task_service),
    )

    assert decision["promoted"] is True
    assert decision["reason"] == "challenger_has_best_accepted_score"
    assert decision["recommended_task_id"] == "challenger-1"
    assert decision["recommended_action"] == "promote_challenger"
    assert decision["selected_task_id"] == "challenger-1"
    assert task_service.accepted_task_ids == ["challenger-1"]


def test_maybe_schedule_degraded_delivery_returns_none_when_human_review_required() -> None:
    module = _load_module()
    decision = module.maybe_schedule_degraded_delivery(
        _task(task_id="child-1", root_task_id="root-1", parent_task_id="root-1", delivery_status="failed"),
        runtime_service=_runtime_service(),
        store=_FakeStore(lineage_tasks=[]),
        artifact_store=_FakeArtifactStore(failure_contract={"human_review_required": True}),
        auto_repair_service=SimpleNamespace(task_service=_FakeTaskService()),
    )

    assert decision is None


def test_maybe_schedule_degraded_delivery_creates_child_task_when_eligible() -> None:
    module = _load_module()
    task_service = _FakeTaskService()
    task = _task(
        task_id="child-1",
        root_task_id="root-1",
        parent_task_id="root-1",
        status=TaskStatus.FAILED,
        phase=TaskPhase.FAILED,
        delivery_status="failed",
        quality_gate_status=None,
    )
    decision = module.maybe_schedule_degraded_delivery(
        task,
        runtime_service=_runtime_service(),
        store=_FakeStore(lineage_tasks=[_task(task_id="root-1"), task]),
        artifact_store=_FakeArtifactStore(failure_contract={"issue_code": "static_previews"}),
        auto_repair_service=SimpleNamespace(task_service=task_service),
    )

    assert decision is not None
    assert decision.reason == "created_degraded_attempt"
    assert decision.child_task_id == "degraded-child"
    assert decision.completion_mode == "degraded"
    assert decision.delivery_tier == "guided_generate"
    assert task_service.degraded_calls[0]["parent_task_id"] == "child-1"
    assert task_service.degraded_calls[0]["generation_mode"] == "guided_generate"
