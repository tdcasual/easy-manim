# Agent Reliability Backend Design

## Goal

Evolve `easy-manim` from a single-pass generation pipeline into a supervised generation system that:

1. drives final success rate high through classification and recovery rather than blind retries,
2. improves output quality through structured review loops,
3. only learns from validated improvements instead of absorbing every run indiscriminately.

This design intentionally keeps the current single-owner task model. Reviewer and judge roles remain advisory. The orchestrator remains the only mutation authority.

## MVP Status

The backend MVP path is now implemented around JSON-first reliability artifacts and read APIs:

- tasks persist `risk_level`, `generation_mode`, `quality_gate_status`, `accepted_as_best`, and `accepted_version_rank`
- workflow execution writes `scene_spec.json`, `recovery_plan.json`, and `quality_score.json`
- review bundles include scene spec, recovery plan, quality scorecard, and quality gate status
- HTTP and MCP expose dedicated read surfaces for scene spec, recovery plan, and quality score
- strategy promotion remains eval-gated through stored strategy profiles and challenger runs

The remaining design ideas in this document still describe the intended direction, but the shipped MVP intentionally stops short of automatic policy promotion or a richer supervisor API.

## Design Principles

- Prefer supervised orchestration over free-form multi-agent mutation.
- Separate failure recovery from quality improvement.
- Treat `completed` as "render succeeded", not "ship quality approved".
- Introduce stable intermediate representations before code generation.
- Make every recovery path explicit and measurable.
- Promote strategies only after eval and preference evidence.

## Current Foundation

The current codebase already has several strong building blocks:

- task lineage and revision flow in `src/video_agent/domain/models.py` and `src/video_agent/application/task_service.py`
- generation and validation pipeline in `src/video_agent/application/workflow_engine.py`
- targeted repair entrypoint in `src/video_agent/application/auto_repair_service.py`
- failure contracts in `src/video_agent/application/failure_contract.py`
- review bundles and supervised review decisions in `src/video_agent/application/review_bundle_builder.py` and `src/video_agent/application/multi_agent_workflow_service.py`
- eval summaries and agent learning events in `src/video_agent/application/eval_service.py` and `src/video_agent/application/agent_learning_service.py`

The recommended direction is to wrap these capabilities in a stronger planning, judging, and promotion layer rather than replacing them.

## Reference Patterns

This design borrows the following ideas:

- TheoremExplainAgent: planning-first Manim generation
- SWE-agent: execution followed by verification and targeted repair
- Self-Refine / Reflexion: structured feedback loops
- VBench / VideoScore2: multi-dimensional video quality judgment

These references are used as pattern guides, not framework dependencies.

## Target Architecture

The target runtime keeps one owner task with bounded child attempts.

Flow:

1. `TaskRiskService` classifies request risk and selects a generation mode.
2. `SceneSpecService` converts prompt plus context into a stable scene plan.
3. `Generator` produces candidate Manim code from the scene plan.
4. `PreflightVerifier` validates syntax, capability requirements, and resource budgets.
5. `PreviewGate` performs a cheaper preview render and preview validation.
6. `RecoveryPolicyService` chooses a bounded recovery action when preview or render fails.
7. `QualityJudgeService` scores successful outputs across multiple dimensions.
8. `SupervisorWorkflowService` decides accept, revise, retry, downgrade, or escalate.
9. `PolicyPromotionService` uses eval evidence to decide whether a strategy becomes default.

## New Core Services

### `TaskRiskService`

Purpose:

- classify requests before generation,
- choose safer defaults for known high-risk prompts,
- avoid wasting attempts on obviously fragile open-ended generation.

Suggested output:

- `risk_level`: `low | medium | high | blocked`
- `generation_mode`: `template_first | guided_generate | open_generate`
- `blocked_capabilities`: list of missing requirements
- `expected_failure_modes`: list of likely issue codes
- `budget_class`: `tight | standard | exploratory`

### `SceneSpecService`

Purpose:

- translate prompt intent into a stable intermediate representation before code generation.

Suggested `SceneSpec` fields:

- `scene_spec_id`
- `task_id`
- `summary`
- `scene_count`
- `scenes`
- `timing_budget_seconds`
- `camera_strategy`
- `visual_constraints`
- `text_constraints`
- `style_constraints`
- `forbidden_elements`
- `generation_mode`

### `CapabilityGateService`

Purpose:

- reject or downgrade requests when the runtime cannot satisfy them.

Checks should include:

- LaTeX availability,
- font and multilingual text support,
- render dimension and duration budget,
- complexity budget for objects and scene count,
- 3D feature risk,
- sandbox and runtime policy limits.

### `RecoveryPolicyService`

Purpose:

- convert a failure contract into an actual recovery plan instead of a passive hint.

Suggested output:

- `candidate_actions`
- `selected_action`
- `repair_recipe`
- `fallback_generation_mode`
- `cost_class`
- `human_gate_required`

### `QualityJudgeService`

Purpose:

- evaluate successful renders for quality rather than only binary completion.

Initial dimensions:

- `prompt_alignment`
- `visual_clarity`
- `text_readability`
- `motion_smoothness`
- `composition`
- `style_consistency`
- `educational_effectiveness`

### `PolicyPromotionService`

Purpose:

- compare active strategies against challengers,
- promote only after measurable improvement,
- prevent drift from noisy feedback.

## Data Model Changes

The recommended implementation is incremental. Use JSON-first persistence and artifacts before introducing many normalized tables.

### Extend `VideoTask`

Add fields to `src/video_agent/domain/models.py`:

- `risk_level: str | None = None`
- `generation_mode: str | None = None`
- `strategy_profile_id: str | None = None`
- `scene_spec_id: str | None = None`
- `quality_gate_status: str | None = None`
- `accepted_as_best: bool = False`
- `accepted_version_rank: int | None = None`

### New domain models

Create:

- `src/video_agent/domain/scene_spec_models.py`
- `src/video_agent/domain/recovery_models.py`
- `src/video_agent/domain/quality_models.py`
- `src/video_agent/domain/strategy_models.py`

Suggested models:

- `SceneSpec`
- `TaskRiskProfile`
- `RecoveryPlan`
- `QualityScorecard`
- `StrategyProfile`
- `PromptClusterStats`

### Persistence strategy

Phase 1 persistence:

- store canonical JSON blobs in task artifacts and optional JSON columns
- keep `task_json` authoritative
- use dedicated tables only for high-volume query paths

Suggested new SQLite tables once query pressure appears:

- `task_scene_specs`
- `task_quality_scores`
- `task_recovery_plans`
- `strategy_profiles`
- `strategy_eval_runs`
- `prompt_cluster_stats`

## SQLite Migration Plan

Add a new schema migration after `005_task_display_title_fields`.

Suggested migration sequence:

- `006_task_reliability_fields`
- `007_task_quality_scorecards`
- `008_strategy_profiles`

`006_task_reliability_fields` should add nullable columns to `video_tasks`:

- `risk_level`
- `generation_mode`
- `strategy_profile_id`
- `scene_spec_id`
- `quality_gate_status`
- `accepted_as_best`
- `accepted_version_rank`

`007_task_quality_scorecards` should create:

- `task_quality_scores(task_id TEXT PRIMARY KEY, scorecard_json TEXT NOT NULL, created_at TEXT NOT NULL)`

`008_strategy_profiles` should create:

- `strategy_profiles(strategy_id TEXT PRIMARY KEY, scope TEXT NOT NULL, prompt_cluster TEXT, status TEXT NOT NULL, params_json TEXT NOT NULL, metrics_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)`

## Execution State Machine

The existing `TaskPhase` enum should be expanded in `src/video_agent/domain/enums.py`.

Suggested new phases:

- `RISK_ROUTING`
- `SCENE_PLANNING`
- `PREFLIGHT_CHECK`
- `PREVIEW_RENDER`
- `PREVIEW_VALIDATION`
- `QUALITY_JUDGING`
- `ESCALATED`

Suggested run loop:

1. claim task
2. route risk
3. build scene spec
4. generate script
5. static check
6. preflight check
7. preview render
8. preview validation
9. full render
10. frame extract
11. validation
12. quality judge
13. complete, revise, retry, or escalate

## Recovery Policy Matrix

Recovery should be issue-driven rather than generic.

- `provider_auth_error`
  action: `escalate_human`
- `provider_rate_limited`
  action: `retry_later` then `provider_fallback`
- `provider_timeout`
  action: `retry_same` then `guided_generate`
- `latex_dependency_missing`
  action: `downgrade_non_latex` or `escalate_human`
- `static_check_failed`
  action: `repair_static_only`
- `render_failed`
  action: `repair_render_path`
- `near_blank_preview`
  action: `preview_repair`
- `quality_below_threshold`
  action: `critic_revise_loop`

Each action should map to a named repair recipe instead of a single generic prompt.

## Strategy Profiles

Introduce explicit strategy families rather than one global policy.

Examples:

- `geometry_teaching_v1`
- `short_logo_intro_v1`
- `math_formula_safe_mode_v1`
- `subtitle_heavy_explainer_v1`

Each strategy profile should define:

- preferred prompt template,
- planner settings,
- generation mode,
- render defaults,
- quality thresholds,
- fallback chain,
- known safe constraints.

## Eval and Promotion

Extend `src/video_agent/application/eval_service.py` to support challenger evaluation.

Evaluation should have three layers:

- `rule_eval`
- `judge_eval`
- `preference_eval`

Promotion gates:

- challenger must not regress final success rate,
- challenger must improve accepted quality rate,
- challenger must not worsen top risk issue codes,
- challenger should win a minimum preference rate on sampled comparisons.

## API Additions

Add HTTP APIs for reliability and quality inspection.

Suggested new endpoints:

- `GET /api/tasks/{task_id}/scene-spec`
- `GET /api/tasks/{task_id}/quality-score`
- `GET /api/tasks/{task_id}/recovery-plan`
- `POST /api/tasks/{task_id}/accept-best`
- `POST /api/tasks/{task_id}/critic-review`
- `GET /api/strategies`
- `GET /api/strategies/{strategy_id}`
- `POST /api/evals/challenger-run`

The existing review workflow endpoints should remain the main orchestration boundary for external reviewer agents.

## Supervisor API Contract

The supervisor should return structured outcomes:

- `accept`
- `revise`
- `retry`
- `downgrade`
- `escalate`

Extend current review decision outcomes with:

- `selected_strategy_profile_id`
- `selected_recovery_action`
- `quality_gate_status`
- `accepted_as_best`

## UI and Product Implications

Backend-first, but the API should be designed for a future thread-based video review UI.

The UI should eventually be able to show:

- root task thread
- lineage tree
- current best version
- quality scorecard
- recovery rationale
- compare version metadata

This design supports that path without forcing frontend work first.

## Test Strategy

### Unit tests

Add unit tests for:

- risk classification
- capability gate decisions
- recovery policy selection
- quality threshold decisions
- promotion gate logic

### Integration tests

Add integration tests for:

- high-risk prompt routed to safer generation mode
- LaTeX risk downgraded before render
- preview failure leads to targeted repair
- quality-low successful render enters critic revise loop
- accepted best version updates lineage metadata
- challenger eval compares strategy A vs B

### Regression tests

Protect existing guarantees:

- task ownership remains enforced
- review agents remain read-only
- root lineage and child budgets remain bounded
- non-reliability task APIs behave as before

## Rollout Plan

### Phase 1

Ship:

- `TaskRiskService`
- `SceneSpecService`
- `CapabilityGateService`
- `RecoveryPolicyService`
- new task fields and migration

Goal:

- raise final success rate and reduce wasteful retries

### Phase 2

Ship:

- `QualityJudgeService`
- `QualityScorecard`
- quality-based revise loop
- best-version promotion

Goal:

- stop treating all successful renders as final

### Phase 3

Ship:

- `StrategyProfile`
- challenger evals
- policy promotion
- prompt-cluster reporting

Goal:

- steadily improve defaults using evidence

## Recommended MVP

If scope must stay tight, implement only:

1. `risk_level + generation_mode` on tasks
2. `SceneSpec` intermediate artifact
3. preview gate before full render
4. structured `RecoveryPlan`
5. `QualityScorecard` on successful tasks

This is the smallest meaningful slice that increases both reliability and future learning capacity.
