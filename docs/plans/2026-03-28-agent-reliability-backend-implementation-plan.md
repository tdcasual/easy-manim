# Agent Reliability Backend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a supervised reliability layer to `easy-manim` that improves final task success rate through risk routing, preview gating, structured recovery plans, and quality scorecards, while laying the groundwork for strategy promotion.

**Architecture:** Build on the existing task lineage, workflow engine, auto-repair flow, review bundle flow, and eval reporting rather than replacing them. Keep task ownership unchanged, introduce JSON-first reliability artifacts and task metadata, then expose them through existing snapshot, MCP, and HTTP surfaces. Deliver the MVP first: risk classification, scene specs, preflight and preview gates, recovery plans, and quality scorecards. Add strategy promotion scaffolding only after the MVP path is testable.

**Tech Stack:** Python, Pydantic, FastAPI, FastMCP, SQLite, pytest, existing artifact-store-backed task pipeline

---

## Pre-flight

Read these files before implementation:

- `docs/plans/2026-03-28-agent-reliability-backend-design.md`
- `src/video_agent/domain/models.py`
- `src/video_agent/domain/enums.py`
- `src/video_agent/application/workflow_engine.py`
- `src/video_agent/application/task_service.py`
- `src/video_agent/application/auto_repair_service.py`
- `src/video_agent/application/failure_contract.py`
- `src/video_agent/application/eval_service.py`
- `src/video_agent/application/review_bundle_builder.py`
- `src/video_agent/application/multi_agent_workflow_service.py`
- `src/video_agent/adapters/storage/artifact_store.py`
- `src/video_agent/adapters/storage/sqlite_schema.py`
- `src/video_agent/adapters/storage/sqlite_store.py`
- `src/video_agent/server/http_api.py`
- `src/video_agent/server/mcp_tools.py`
- `tests/integration/test_workflow_completion.py`
- `tests/integration/test_auto_repair_loop.py`
- `tests/integration/test_http_task_api.py`
- `tests/integration/test_mcp_tools.py`

Implementation scope is phased:

1. Tasks 1-6 deliver the backend MVP.
2. Task 7 exposes the new data through APIs and review surfaces.
3. Task 8 adds strategy and promotion scaffolding.
4. Task 9 completes docs and regression verification.

### Task 1: Reliability Domain Models, Task Fields, and Settings

**Files:**
- Create: `src/video_agent/domain/scene_spec_models.py`
- Create: `src/video_agent/domain/recovery_models.py`
- Create: `src/video_agent/domain/quality_models.py`
- Create: `src/video_agent/domain/strategy_models.py`
- Modify: `src/video_agent/domain/models.py`
- Modify: `src/video_agent/domain/enums.py`
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Test: `tests/unit/domain/test_scene_spec_models.py`
- Test: `tests/unit/domain/test_recovery_models.py`
- Test: `tests/unit/domain/test_quality_models.py`
- Test: `tests/unit/domain/test_strategy_models.py`
- Test: `tests/unit/test_settings.py`

**Step 1: Write the failing tests**

```python
from video_agent.config import Settings
from video_agent.domain.enums import TaskPhase
from video_agent.domain.models import VideoTask
from video_agent.domain.quality_models import QualityScorecard
from video_agent.domain.recovery_models import RecoveryPlan
from video_agent.domain.scene_spec_models import SceneSpec


def test_settings_expose_reliability_defaults() -> None:
    settings = Settings()

    assert settings.preview_gate_enabled is True
    assert settings.quality_gate_min_score == 0.75
    assert settings.risk_routing_enabled is True
    assert settings.strategy_promotion_enabled is False


def test_task_phase_exposes_reliability_phases() -> None:
    assert TaskPhase.RISK_ROUTING == "risk_routing"
    assert TaskPhase.SCENE_PLANNING == "scene_planning"
    assert TaskPhase.PREVIEW_RENDER == "preview_render"
    assert TaskPhase.QUALITY_JUDGING == "quality_judging"


def test_video_task_tracks_reliability_metadata() -> None:
    task = VideoTask(prompt="draw a circle", risk_level="medium", generation_mode="guided_generate")

    assert task.risk_level == "medium"
    assert task.generation_mode == "guided_generate"
    assert task.accepted_as_best is False
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/unit/domain/test_scene_spec_models.py \
  tests/unit/domain/test_recovery_models.py \
  tests/unit/domain/test_quality_models.py \
  tests/unit/domain/test_strategy_models.py \
  tests/unit/test_settings.py -q
```

Expected: FAIL with missing model imports, missing enum values, or missing settings fields such as `preview_gate_enabled`.

**Step 3: Write minimal implementation**

Add new settings in `src/video_agent/config.py`:

```python
preview_gate_enabled: bool = True
preview_gate_frame_limit: int = 12
quality_gate_min_score: float = 0.75
risk_routing_enabled: bool = True
strategy_promotion_enabled: bool = False
```

Add env wiring in `src/video_agent/server/main.py`:

```python
preview_gate_enabled=_env_bool("EASY_MANIM_PREVIEW_GATE_ENABLED", True),
preview_gate_frame_limit=_env_int("EASY_MANIM_PREVIEW_GATE_FRAME_LIMIT", 12),
quality_gate_min_score=_env_float("EASY_MANIM_QUALITY_GATE_MIN_SCORE", 0.75),
risk_routing_enabled=_env_bool("EASY_MANIM_RISK_ROUTING_ENABLED", True),
strategy_promotion_enabled=_env_bool("EASY_MANIM_STRATEGY_PROMOTION_ENABLED", False),
```

Add new `TaskPhase` values in `src/video_agent/domain/enums.py`:

```python
RISK_ROUTING = "risk_routing"
SCENE_PLANNING = "scene_planning"
PREFLIGHT_CHECK = "preflight_check"
PREVIEW_RENDER = "preview_render"
PREVIEW_VALIDATION = "preview_validation"
QUALITY_JUDGING = "quality_judging"
ESCALATED = "escalated"
```

Add fields to `VideoTask` in `src/video_agent/domain/models.py`:

```python
risk_level: Optional[str] = None
generation_mode: Optional[str] = None
strategy_profile_id: Optional[str] = None
scene_spec_id: Optional[str] = None
quality_gate_status: Optional[str] = None
accepted_as_best: bool = False
accepted_version_rank: Optional[int] = None
```

Create minimal Pydantic models:

- `SceneSpec`
- `TaskRiskProfile`
- `RecoveryPlan`
- `QualityScorecard`
- `StrategyProfile`
- `PromptClusterStats`

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/domain/scene_spec_models.py \
  src/video_agent/domain/recovery_models.py \
  src/video_agent/domain/quality_models.py \
  src/video_agent/domain/strategy_models.py \
  src/video_agent/domain/models.py \
  src/video_agent/domain/enums.py \
  src/video_agent/config.py \
  src/video_agent/server/main.py \
  tests/unit/domain/test_scene_spec_models.py \
  tests/unit/domain/test_recovery_models.py \
  tests/unit/domain/test_quality_models.py \
  tests/unit/domain/test_strategy_models.py \
  tests/unit/test_settings.py
git commit -m "feat: add reliability domain models and settings"
```

### Task 2: SQLite Schema, Artifact Helpers, and Task Persistence

**Files:**
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/domain/models.py`
- Test: `tests/unit/adapters/storage/test_sqlite_store.py`
- Create: `tests/unit/adapters/storage/test_artifact_store_reliability.py`

**Step 1: Write the failing tests**

```python
from video_agent.domain.models import VideoTask
from video_agent.domain.quality_models import QualityScorecard
from video_agent.domain.recovery_models import RecoveryPlan
from video_agent.domain.scene_spec_models import SceneSpec


def test_artifact_store_roundtrips_scene_spec(tmp_path) -> None:
    store = ArtifactStore(tmp_path / "tasks")
    spec = SceneSpec(task_id="task-1", summary="teach a blue circle", scene_count=1, scenes=[])

    store.write_scene_spec("task-1", spec.model_dump(mode="json"))

    assert store.read_scene_spec("task-1")["summary"] == "teach a blue circle"


def test_sqlite_store_persists_reliability_task_fields(tmp_path) -> None:
    task_store = SQLiteTaskStore(tmp_path / "video_agent.db")
    task = VideoTask(prompt="draw a circle", risk_level="high", generation_mode="template_first")
    task_store.create_task(task)

    persisted = task_store.get_task(task.task_id)

    assert persisted is not None
    assert persisted.risk_level == "high"
    assert persisted.generation_mode == "template_first"
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/unit/adapters/storage/test_artifact_store_reliability.py -q
```

Expected: FAIL because scene spec helpers and new schema columns do not exist yet.

**Step 3: Write minimal implementation**

In `src/video_agent/adapters/storage/sqlite_schema.py`, add migration `006_task_reliability_fields`:

```python
ensure_column(connection, "video_tasks", "risk_level", "TEXT")
ensure_column(connection, "video_tasks", "generation_mode", "TEXT")
ensure_column(connection, "video_tasks", "strategy_profile_id", "TEXT")
ensure_column(connection, "video_tasks", "scene_spec_id", "TEXT")
ensure_column(connection, "video_tasks", "quality_gate_status", "TEXT")
ensure_column(connection, "video_tasks", "accepted_as_best", "INTEGER NOT NULL DEFAULT 0")
ensure_column(connection, "video_tasks", "accepted_version_rank", "INTEGER")
```

Also create `007_task_quality_scorecards`:

```sql
CREATE TABLE IF NOT EXISTS task_quality_scores (
    task_id TEXT PRIMARY KEY,
    scorecard_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

In `src/video_agent/adapters/storage/artifact_store.py`, add:

```python
def scene_spec_path(self, task_id: str) -> Path: ...
def write_scene_spec(self, task_id: str, payload: dict[str, Any]) -> Path: ...
def read_scene_spec(self, task_id: str) -> dict[str, Any] | None: ...

def recovery_plan_path(self, task_id: str) -> Path: ...
def write_recovery_plan(self, task_id: str, payload: dict[str, Any]) -> Path: ...
def read_recovery_plan(self, task_id: str) -> dict[str, Any] | None: ...

def quality_score_path(self, task_id: str) -> Path: ...
def write_quality_score(self, task_id: str, payload: dict[str, Any]) -> Path: ...
def read_quality_score(self, task_id: str) -> dict[str, Any] | None: ...
```

Update `create_task(...)` and `update_task(...)` in `src/video_agent/adapters/storage/sqlite_store.py` to persist the new task columns alongside `task_json`.

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/adapters/storage/sqlite_schema.py \
  src/video_agent/adapters/storage/sqlite_store.py \
  src/video_agent/adapters/storage/artifact_store.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/unit/adapters/storage/test_artifact_store_reliability.py
git commit -m "feat: persist reliability artifacts and task metadata"
```

### Task 3: Risk Routing and Scene Spec Services

**Files:**
- Create: `src/video_agent/application/task_risk_service.py`
- Create: `src/video_agent/application/scene_spec_service.py`
- Modify: `src/video_agent/application/scene_plan.py`
- Modify: `src/video_agent/server/app.py`
- Test: `tests/unit/application/test_task_risk_service.py`
- Test: `tests/unit/application/test_scene_spec_service.py`

**Step 1: Write the failing tests**

```python
from video_agent.application.task_risk_service import TaskRiskService
from video_agent.application.scene_spec_service import SceneSpecService


def test_task_risk_service_routes_formula_prompt_to_high_risk() -> None:
    service = TaskRiskService()

    profile = service.classify(prompt="使用 MathTex 展示二次公式推导", style_hints={})

    assert profile.risk_level == "high"
    assert profile.generation_mode == "template_first"
    assert "latex_dependency_missing" in profile.expected_failure_modes


def test_scene_spec_service_builds_stable_scene_spec() -> None:
    service = SceneSpecService()

    spec = service.build(
        prompt="draw a blue circle and label the radius",
        output_profile={"quality_preset": "development"},
        style_hints={"tone": "teaching"},
    )

    assert spec.scene_count >= 1
    assert spec.summary
    assert spec.generation_mode in {"template_first", "guided_generate", "open_generate"}
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/unit/application/test_task_risk_service.py \
  tests/unit/application/test_scene_spec_service.py -q
```

Expected: FAIL because the services do not exist yet.

**Step 3: Write minimal implementation**

Create `TaskRiskService`:

```python
class TaskRiskService:
    def classify(self, *, prompt: str, style_hints: dict[str, Any]) -> TaskRiskProfile:
        text = prompt.lower()
        if "mathtex" in text or "tex" in text:
            return TaskRiskProfile(
                risk_level="high",
                generation_mode="template_first",
                expected_failure_modes=["latex_dependency_missing", "render_failed"],
                budget_class="tight",
            )
        if "logo" in text or "开场" in prompt:
            return TaskRiskProfile(risk_level="low", generation_mode="guided_generate", budget_class="standard")
        return TaskRiskProfile(risk_level="medium", generation_mode="guided_generate", budget_class="standard")
```

Create `SceneSpecService` that wraps current planning logic instead of replacing it:

```python
class SceneSpecService:
    def build(self, *, prompt: str, output_profile: dict[str, Any], style_hints: dict[str, Any], generation_mode: str = "guided_generate") -> SceneSpec:
        scene_plan = build_scene_plan(prompt=prompt, output_profile=output_profile, style_hints=style_hints)
        return SceneSpec(
            task_id="",
            summary=scene_plan.scene_goal,
            scene_count=1,
            scenes=[scene_plan.model_dump(mode="json")],
            camera_strategy=scene_plan.camera_strategy,
            generation_mode=generation_mode,
        )
```

Wire both services into `AppContext` in `src/video_agent/server/app.py`.

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/task_risk_service.py \
  src/video_agent/application/scene_spec_service.py \
  src/video_agent/application/scene_plan.py \
  src/video_agent/server/app.py \
  tests/unit/application/test_task_risk_service.py \
  tests/unit/application/test_scene_spec_service.py
git commit -m "feat: add risk routing and scene spec services"
```

### Task 4: Capability Gate and Recovery Policy

**Files:**
- Create: `src/video_agent/application/capability_gate_service.py`
- Create: `src/video_agent/application/recovery_policy_service.py`
- Modify: `src/video_agent/application/failure_contract.py`
- Modify: `src/video_agent/server/app.py`
- Test: `tests/unit/application/test_capability_gate_service.py`
- Test: `tests/unit/application/test_recovery_policy_service.py`
- Test: `tests/unit/application/test_failure_contract.py`

**Step 1: Write the failing tests**

```python
from video_agent.application.capability_gate_service import CapabilityGateService
from video_agent.application.recovery_policy_service import RecoveryPolicyService


def test_capability_gate_blocks_formula_scene_when_latex_missing() -> None:
    gate = CapabilityGateService()

    decision = gate.evaluate(
        prompt="使用 MathTex 展示公式",
        scene_spec={"generation_mode": "template_first"},
        runtime_status={"mathtex": {"available": False}},
    )

    assert decision.allowed is False
    assert decision.block_reason == "latex_dependency_missing"
    assert decision.suggested_mode == "guided_generate"


def test_recovery_policy_selects_preview_repair_for_near_blank_preview() -> None:
    service = RecoveryPolicyService()

    plan = service.build(issue_code="near_blank_preview", failure_contract={"blocking_layer": "preview"})

    assert plan.selected_action == "preview_repair"
    assert plan.repair_recipe == "preview_repair"
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/unit/application/test_capability_gate_service.py \
  tests/unit/application/test_recovery_policy_service.py \
  tests/unit/application/test_failure_contract.py -q
```

Expected: FAIL because services and richer failure contract fields are missing.

**Step 3: Write minimal implementation**

Create `CapabilityGateService`:

```python
class CapabilityGateDecision(BaseModel):
    allowed: bool
    block_reason: str | None = None
    suggested_mode: str | None = None


class CapabilityGateService:
    def evaluate(self, *, prompt: str, scene_spec: dict[str, Any], runtime_status: dict[str, Any]) -> CapabilityGateDecision:
        if ("MathTex" in prompt or "Tex" in prompt) and not runtime_status.get("mathtex", {}).get("available", False):
            return CapabilityGateDecision(allowed=False, block_reason="latex_dependency_missing", suggested_mode="guided_generate")
        return CapabilityGateDecision(allowed=True)
```

Create `RecoveryPolicyService`:

```python
class RecoveryPolicyService:
    def build(self, *, issue_code: str | None, failure_contract: dict[str, Any] | None) -> RecoveryPlan:
        if issue_code == "near_blank_preview":
            return RecoveryPlan(issue_code=issue_code, candidate_actions=["preview_repair"], selected_action="preview_repair", repair_recipe="preview_repair")
        if issue_code == "render_failed":
            return RecoveryPlan(issue_code=issue_code, candidate_actions=["repair_render_path"], selected_action="repair_render_path", repair_recipe="targeted_render_repair")
        return RecoveryPlan(issue_code=issue_code, candidate_actions=["escalate_human"], selected_action="escalate_human", human_gate_required=True)
```

Extend `FailureContract` to include:

- `candidate_actions`
- `cost_class`
- `fallback_generation_mode`

Wire the new services into `AppContext`.

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/capability_gate_service.py \
  src/video_agent/application/recovery_policy_service.py \
  src/video_agent/application/failure_contract.py \
  src/video_agent/server/app.py \
  tests/unit/application/test_capability_gate_service.py \
  tests/unit/application/test_recovery_policy_service.py \
  tests/unit/application/test_failure_contract.py
git commit -m "feat: add capability gate and recovery policy services"
```

### Task 5: Quality Judge Service and Scorecards

**Files:**
- Create: `src/video_agent/application/quality_judge_service.py`
- Modify: `src/video_agent/application/agent_learning_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Test: `tests/unit/application/test_quality_judge_service.py`
- Modify: `tests/unit/application/test_agent_learning_service.py`
- Modify: `tests/unit/adapters/storage/test_sqlite_store.py`

**Step 1: Write the failing tests**

```python
from video_agent.application.quality_judge_service import QualityJudgeService


def test_quality_judge_produces_dimension_scores() -> None:
    judge = QualityJudgeService(min_score=0.75)

    scorecard = judge.score(
        status="completed",
        issue_codes=["static_previews"],
        preview_issue_codes=["static_previews"],
        summary="Rendered but previews are static",
    )

    assert scorecard.total_score < 0.75
    assert scorecard.dimension_scores["motion_smoothness"] < 0.75
    assert "static_previews" in scorecard.must_fix_issues
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/unit/application/test_quality_judge_service.py \
  tests/unit/application/test_agent_learning_service.py \
  tests/unit/adapters/storage/test_sqlite_store.py -q
```

Expected: FAIL because quality scorecards do not exist yet.

**Step 3: Write minimal implementation**

Create `QualityJudgeService`:

```python
class QualityJudgeService:
    def __init__(self, min_score: float) -> None:
        self.min_score = min_score

    def score(self, *, status: str, issue_codes: list[str], preview_issue_codes: list[str], summary: str | None) -> QualityScorecard:
        motion = 0.4 if "static_previews" in preview_issue_codes else 0.9
        total = round((1.0 if status == "completed" else 0.5 + motion) / 2, 4)
        return QualityScorecard(
            total_score=total,
            dimension_scores={"motion_smoothness": motion, "prompt_alignment": 0.9, "visual_clarity": 0.9},
            must_fix_issues=[code for code in issue_codes if code in {"static_previews", "near_blank_preview"}],
            accepted=total >= self.min_score,
        )
```

Extend `AgentLearningEvent` recording to include scorecard-derived values through `quality_score`.

Add `upsert_task_quality_score(...)` and `get_task_quality_score(...)` to `SQLiteTaskStore`.

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/quality_judge_service.py \
  src/video_agent/application/agent_learning_service.py \
  src/video_agent/adapters/storage/sqlite_store.py \
  tests/unit/application/test_quality_judge_service.py \
  tests/unit/application/test_agent_learning_service.py \
  tests/unit/adapters/storage/test_sqlite_store.py
git commit -m "feat: add quality judge service and scorecards"
```

### Task 6: Workflow Engine Integration for Risk, Preview, Recovery, and Quality

**Files:**
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/auto_repair_service.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/domain/enums.py`
- Modify: `src/video_agent/application/task_service.py`
- Test: `tests/integration/test_workflow_completion.py`
- Create: `tests/integration/test_reliability_workflow_engine.py`

**Step 1: Write the failing tests**

```python
def test_workflow_persists_scene_spec_and_quality_score(tmp_path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a blue circle", session_id="session-1")

    app.worker.run_once()

    assert app.artifact_store.read_scene_spec(created.task_id) is not None
    assert app.artifact_store.read_quality_score(created.task_id) is not None


def test_workflow_writes_recovery_plan_when_preview_validation_fails(tmp_path) -> None:
    app = create_app_context(_build_preview_failure_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    recovery_plan = app.artifact_store.read_recovery_plan(created.task_id)
    assert recovery_plan is not None
    assert recovery_plan["selected_action"] == "preview_repair"
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/integration/test_reliability_workflow_engine.py \
  tests/integration/test_workflow_completion.py -q
```

Expected: FAIL because the workflow does not yet emit scene spec, recovery plan, or quality score artifacts.

**Step 3: Write minimal implementation**

In `src/video_agent/application/workflow_engine.py`:

- inject `TaskRiskService`, `SceneSpecService`, `CapabilityGateService`, `RecoveryPolicyService`, and `QualityJudgeService`
- add transitions:
  - `RISK_ROUTING`
  - `SCENE_PLANNING`
  - `PREFLIGHT_CHECK`
  - `PREVIEW_RENDER`
  - `PREVIEW_VALIDATION`
  - `QUALITY_JUDGING`

Implementation outline:

```python
risk_profile = self.task_risk_service.classify(prompt=task.prompt, style_hints=task.style_hints)
task.risk_level = risk_profile.risk_level
task.generation_mode = risk_profile.generation_mode

scene_spec = self.scene_spec_service.build(...)
self.artifact_store.write_scene_spec(task.task_id, scene_spec.model_dump(mode="json"))

gate = self.capability_gate_service.evaluate(...)
if not gate.allowed:
    recovery_plan = self.recovery_policy_service.build(issue_code=gate.block_reason, failure_contract={...})
    self.artifact_store.write_recovery_plan(task.task_id, recovery_plan.model_dump(mode="json"))
    self._fail_task(...)
    return

# after preview/static/render validation
scorecard = self.quality_judge_service.score(...)
self.artifact_store.write_quality_score(task.task_id, scorecard.model_dump(mode="json"))
task.quality_gate_status = "accepted" if scorecard.accepted else "needs_revision"
```

In `src/video_agent/application/auto_repair_service.py`, use `RecoveryPolicyService` output instead of only `issue_code -> feedback`.

In `src/video_agent/application/task_service.py`, include `risk_level`, `generation_mode`, and `quality_gate_status` in snapshots.

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/workflow_engine.py \
  src/video_agent/application/auto_repair_service.py \
  src/video_agent/application/task_service.py \
  src/video_agent/server/app.py \
  tests/integration/test_reliability_workflow_engine.py \
  tests/integration/test_workflow_completion.py
git commit -m "feat: integrate reliability services into workflow engine"
```

### Task 7: Snapshot, Review Bundle, MCP, and HTTP API Exposure

**Files:**
- Modify: `src/video_agent/application/review_bundle_builder.py`
- Modify: `src/video_agent/domain/review_workflow_models.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/http_api.py`
- Modify: `src/video_agent/application/task_service.py`
- Create: `tests/integration/test_http_task_reliability_api.py`
- Create: `tests/integration/test_mcp_task_reliability_tools.py`
- Modify: `tests/integration/test_http_task_api.py`
- Modify: `tests/integration/test_mcp_tools.py`

**Step 1: Write the failing tests**

```python
def test_http_task_reliability_endpoints_expose_scene_spec_and_quality_score(tmp_path) -> None:
    client = TestClient(create_http_api(_build_http_task_settings(tmp_path)))
    token = _login_seeded_agent(client)
    task_id = _create_completed_task_with_quality(client, token)

    scene_spec = client.get(f"/api/tasks/{task_id}/scene-spec", headers={"Authorization": f"Bearer {token}"})
    quality = client.get(f"/api/tasks/{task_id}/quality-score", headers={"Authorization": f"Bearer {token}"})

    assert scene_spec.status_code == 200
    assert quality.status_code == 200
    assert "total_score" in quality.json()


def test_review_bundle_includes_quality_gate_and_recovery_plan(tmp_path) -> None:
    app = create_app_context(_build_fake_pipeline_settings(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a blue circle")
    app.worker.run_once()

    bundle = app.multi_agent_workflow_service.get_review_bundle(created.task_id)

    assert bundle.quality_scorecard is not None
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/integration/test_http_task_reliability_api.py \
  tests/integration/test_mcp_task_reliability_tools.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_mcp_tools.py -q
```

Expected: FAIL because the new reliability APIs and bundle fields do not exist yet.

**Step 3: Write minimal implementation**

Extend `ReviewBundle` in `src/video_agent/domain/review_workflow_models.py`:

```python
quality_scorecard: dict[str, Any] | None = None
recovery_plan: dict[str, Any] | None = None
scene_spec: dict[str, Any] | None = None
quality_gate_status: str | None = None
```

In `src/video_agent/application/review_bundle_builder.py`, load and attach:

- `artifact_store.read_scene_spec(task_id)`
- `artifact_store.read_recovery_plan(task_id)`
- `artifact_store.read_quality_score(task_id)`

Add MCP tools:

- `get_scene_spec`
- `get_recovery_plan`
- `get_quality_score`

Add HTTP endpoints:

- `GET /api/tasks/{task_id}/scene-spec`
- `GET /api/tasks/{task_id}/recovery-plan`
- `GET /api/tasks/{task_id}/quality-score`
- `POST /api/tasks/{task_id}/accept-best`

Keep all reads behind `task:read` scope.

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/review_bundle_builder.py \
  src/video_agent/domain/review_workflow_models.py \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/server/fastmcp_server.py \
  src/video_agent/server/http_api.py \
  src/video_agent/application/task_service.py \
  tests/integration/test_http_task_reliability_api.py \
  tests/integration/test_mcp_task_reliability_tools.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_mcp_tools.py
git commit -m "feat: expose reliability metadata over review, mcp, and http"
```

### Task 8: Strategy Profiles and Promotion Scaffolding

**Files:**
- Create: `src/video_agent/application/policy_promotion_service.py`
- Modify: `src/video_agent/application/eval_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_schema.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/domain/strategy_models.py`
- Create: `tests/unit/application/test_policy_promotion_service.py`
- Create: `tests/integration/test_eval_strategy_promotion.py`

**Step 1: Write the failing tests**

```python
from video_agent.application.policy_promotion_service import PolicyPromotionService


def test_policy_promotion_requires_quality_gain_without_success_regression() -> None:
    service = PolicyPromotionService()

    approved = service.should_promote(
        baseline={"final_success_rate": 0.92, "accepted_quality_rate": 0.70},
        challenger={"final_success_rate": 0.92, "accepted_quality_rate": 0.76},
    )

    assert approved is True


def test_policy_promotion_rejects_success_regression() -> None:
    service = PolicyPromotionService()

    approved = service.should_promote(
        baseline={"final_success_rate": 0.92, "accepted_quality_rate": 0.70},
        challenger={"final_success_rate": 0.88, "accepted_quality_rate": 0.80},
    )

    assert approved is False
```

**Step 2: Run test to verify it fails**

Run:

```bash
pytest \
  tests/unit/application/test_policy_promotion_service.py \
  tests/integration/test_eval_strategy_promotion.py -q
```

Expected: FAIL because promotion scaffolding does not exist yet.

**Step 3: Write minimal implementation**

Create `PolicyPromotionService`:

```python
class PolicyPromotionService:
    def should_promote(self, *, baseline: dict[str, float], challenger: dict[str, float]) -> bool:
        return (
            challenger["final_success_rate"] >= baseline["final_success_rate"]
            and challenger["accepted_quality_rate"] > baseline["accepted_quality_rate"]
        )
```

Add migration `008_strategy_profiles` to `src/video_agent/adapters/storage/sqlite_schema.py`.

Add `create_strategy_profile(...)`, `list_strategy_profiles(...)`, and `record_strategy_eval_run(...)` to `SQLiteTaskStore`.

Extend `src/video_agent/application/eval_service.py` with a challenger-run entrypoint:

```python
def run_strategy_challenger(...):
    baseline_summary = self.run_suite(...)
    challenger_summary = self.run_suite(...)
    return {"baseline": baseline_summary.model_dump(mode="json"), "challenger": challenger_summary.model_dump(mode="json")}
```

**Step 4: Run test to verify it passes**

Run the same `pytest` command.

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/application/policy_promotion_service.py \
  src/video_agent/application/eval_service.py \
  src/video_agent/adapters/storage/sqlite_schema.py \
  src/video_agent/adapters/storage/sqlite_store.py \
  src/video_agent/domain/strategy_models.py \
  tests/unit/application/test_policy_promotion_service.py \
  tests/integration/test_eval_strategy_promotion.py
git commit -m "feat: add strategy promotion scaffolding"
```

### Task 9: Documentation, Runbooks, and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/runbooks/agent-self-serve.md`
- Modify: `docs/plans/2026-03-28-agent-reliability-backend-design.md`
- Modify: `tests/integration/test_http_task_api.py`
- Modify: `tests/integration/test_mcp_tools.py`

**Step 1: Write the failing regression checks**

Add regression assertions that legacy task create/list/get/result flows still work after reliability metadata is added, and that the new reliability endpoints do not leak cross-agent data.

```python
def test_reliability_metadata_does_not_break_task_roundtrip(tmp_path) -> None:
    ...
```

**Step 2: Run targeted regression tests**

Run:

```bash
pytest tests/integration/test_http_task_api.py tests/integration/test_mcp_tools.py -q
```

Expected: PASS, or targeted FAILs that indicate old snapshots need updates.

**Step 3: Update docs**

Document:

1. risk routing and generation modes
2. scene spec, recovery plan, and quality score artifacts
3. new HTTP and MCP read APIs
4. strategy promotion as an internal eval mechanism

Suggested README snippet:

```markdown
### Reliability Metadata

Each task now records a risk profile, scene spec, recovery plan, and quality scorecard.
Use the task APIs to inspect why a video succeeded, failed, or was revised before accepting it as the best version.
```

**Step 4: Run the final verification set**

Run:

```bash
pytest \
  tests/unit/domain/test_scene_spec_models.py \
  tests/unit/domain/test_recovery_models.py \
  tests/unit/domain/test_quality_models.py \
  tests/unit/domain/test_strategy_models.py \
  tests/unit/application/test_task_risk_service.py \
  tests/unit/application/test_scene_spec_service.py \
  tests/unit/application/test_capability_gate_service.py \
  tests/unit/application/test_recovery_policy_service.py \
  tests/unit/application/test_quality_judge_service.py \
  tests/unit/application/test_policy_promotion_service.py \
  tests/unit/test_settings.py \
  tests/unit/adapters/storage/test_sqlite_store.py \
  tests/unit/adapters/storage/test_artifact_store_reliability.py \
  tests/integration/test_reliability_workflow_engine.py \
  tests/integration/test_workflow_completion.py \
  tests/integration/test_auto_repair_loop.py \
  tests/integration/test_http_task_reliability_api.py \
  tests/integration/test_mcp_task_reliability_tools.py \
  tests/integration/test_eval_strategy_promotion.py \
  tests/integration/test_http_task_api.py \
  tests/integration/test_mcp_tools.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add \
  README.md \
  docs/runbooks/agent-self-serve.md \
  docs/plans/2026-03-28-agent-reliability-backend-design.md \
  tests/integration/test_http_task_api.py \
  tests/integration/test_mcp_tools.py
git commit -m "docs: document reliability backend and verify regressions"
```

## Notes for the Implementer

1. Do not change task ownership semantics. Reviewer and judge paths must remain read-only.
2. Keep `completed` as render success for backward compatibility in phase 1. Use `quality_gate_status` instead of redefining `TaskStatus`.
3. Prefer JSON-first artifact persistence for scene specs, recovery plans, and scorecards.
4. Keep repair budgets bounded by existing lineage and retry rules.
5. Make all new APIs read-only except `accept-best`; quality improvement loops should still flow through controlled revise/retry actions.
6. Only promote strategies after eval evidence. Do not let casual production traffic auto-promote defaults.
