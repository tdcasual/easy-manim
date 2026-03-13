# Phase 5 Agent System Semantic Repair and Sandbox Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evolve the current beta-ready single-agent pipeline into a semantically-aware, safer, and more measurable repair-capable system that can recover from common Manim-generation failures with higher precision.

**Architecture:** Keep the current `FastMCP + SQLite + local filesystem` operating model. Add one explicit semantic-repair layer between `failure_context` and `auto_repair`, decompose the workflow engine into smaller phase-oriented handlers, and harden execution with a stricter sandbox profile rather than jumping prematurely to multi-agent orchestration.

**Tech Stack:** Python 3.13, `pydantic`, `FastMCP`, SQLite, `pytest`, standard-library `ast`/`subprocess`/`resource`/`signal`/`pathlib`, existing Manim/ffmpeg toolchain, local eval suites.

---

## Why this phase exists

The current system is already strong on:
- task lifecycle control
- artifact persistence
- runtime diagnostics
- bounded auto-repair
- operator visibility

The next limiting factor is **semantic correctness**, not infrastructure. The main observed failure mode is now model-generated invalid or brittle Manim code, which the current prompt-based repair loop can describe but cannot yet fix with enough precision.

## Recommended direction

### Recommended: semantic-repair-first
- Add structured code diagnostics for common Manim/API misuse
- Feed those diagnostics into bounded repair
- Harden execution isolation in parallel

**Why:** This directly attacks the current top failure class while preserving the system’s simple local-first shape.

### Alternative A: prompt-tuning-only
- Keep the architecture as-is
- Improve generation and repair prompts only

**Tradeoff:** Lowest implementation cost, but repair quality will plateau quickly.

### Alternative B: multi-agent orchestrator
- Add planner / coder / reviewer agents

**Tradeoff:** Potentially powerful, but much higher coordination cost and observability complexity. Not justified before single-agent semantic repair is mature.

---

## Phase 5 scope

### In scope
- Semantic diagnosis for generated scripts
- Structured repair hints and patch-oriented revision flow
- Workflow-engine decomposition for maintainability
- Stronger local execution sandboxing
- Repair-quality evaluation and release gating

### Out of scope
- Hosted multi-tenant architecture
- Distributed queues or object storage
- Web dashboards
- General-purpose autonomous coding agent behavior beyond the Manim generation domain

---

## Weekly outcomes

- **Week 1:** Workflow state is easier to reason about because repair state and phase handling are explicit rather than buried in one large engine method.
- **Week 2:** Failure context contains semantic diagnosis for common Manim mistakes, not just stderr and generic validation issues.
- **Week 3:** Auto-repair uses structured hints and patch-oriented preservation rules, improving repair precision while staying bounded.
- **Week 4:** Render execution is materially safer, with stricter isolation and clearer operator-visible sandbox failures.
- **Week 5:** The team can measure semantic repair success rate with a dedicated eval slice and use it as a go / no-go gate.

---

## Week 1 - Decompose workflow control and expose explicit repair state

### Task 1: Split the workflow engine into phase handlers and add repair-state snapshots

**Files:**
- Create: `src/video_agent/application/workflow_phases.py`
- Create: `src/video_agent/application/repair_state.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/domain/models.py`
- Test: `tests/integration/test_auto_repair_status.py`
- Test: `tests/integration/test_workflow_completion.py`
- Docs: `docs/runbooks/incident-response.md`

**Implementation outline:**
- Extract generation/static/render/validation failure branches into focused phase functions
- Introduce a lightweight repair-state payload on the task snapshot, including:
  - `repair_attempted`
  - `repair_child_count`
  - `repair_last_issue_code`
  - `repair_stop_reason`
- Keep the public MCP tool names unchanged

**Verification:**
- `python -m pytest tests/integration/test_auto_repair_status.py tests/integration/test_workflow_completion.py -q`

**Commit:**
```bash
git add src/video_agent/application/workflow_phases.py src/video_agent/application/repair_state.py src/video_agent/application/workflow_engine.py src/video_agent/application/task_service.py src/video_agent/domain/models.py tests/integration/test_auto_repair_status.py tests/integration/test_workflow_completion.py docs/runbooks/incident-response.md
git commit -m "refactor: extract workflow phases and explicit repair state"
```

---

## Week 2 - Add semantic script diagnostics for Manim-specific failures

### Task 2: Diagnose generated scripts before and after failed renders

**Files:**
- Create: `src/video_agent/validation/script_diagnostics.py`
- Modify: `src/video_agent/application/failure_context.py`
- Modify: `src/video_agent/application/auto_repair_service.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Test: `tests/unit/validation/test_script_diagnostics.py`
- Test: `tests/integration/test_failure_context_artifact.py`
- Test: `tests/integration/test_auto_repair_loop.py`
- Docs: `docs/runbooks/beta-ops.md`

**Implementation outline:**
- Add AST-based diagnostics that flag common repairable patterns such as:
  - unsupported keyword arguments on likely Manim helpers
  - missing scene construction shape
  - suspicious chained helper calls on likely coordinate objects
  - likely “wrong object / wrong method” API usage
- Persist these diagnostics into `failure_context.json`
- Feed structured hints, not just raw stderr, into the auto-repair feedback builder

**Verification:**
- `python -m pytest tests/unit/validation/test_script_diagnostics.py tests/integration/test_failure_context_artifact.py tests/integration/test_auto_repair_loop.py -q`

**Commit:**
```bash
git add src/video_agent/validation/script_diagnostics.py src/video_agent/application/failure_context.py src/video_agent/application/auto_repair_service.py src/video_agent/application/workflow_engine.py tests/unit/validation/test_script_diagnostics.py tests/integration/test_failure_context_artifact.py tests/integration/test_auto_repair_loop.py docs/runbooks/beta-ops.md
git commit -m "feat: add semantic script diagnostics for repairable failures"
```

---

## Week 3 - Move from generic retries to patch-oriented repair

### Task 3: Add repair prompts that preserve known-good script sections and request targeted patches

**Files:**
- Create: `src/video_agent/application/repair_prompt_builder.py`
- Modify: `src/video_agent/application/auto_repair_service.py`
- Modify: `src/video_agent/application/revision_service.py`
- Modify: `src/video_agent/application/task_service.py`
- Test: `tests/integration/test_auto_repair_loop.py`
- Test: `tests/integration/test_revision_and_cancel.py`
- Test: `tests/integration/test_generation_provider_failures.py`
- Docs: `docs/runbooks/beta-ops.md`

**Implementation outline:**
- Add a dedicated repair prompt builder that includes:
  - the previous script resource
  - semantic diagnosis
  - bounded instructions to preserve working sections
  - the minimal region or behavior to revise
- Differentiate “full regeneration” from “targeted repair” in revision metadata
- Keep bounded-child semantics and issue-code allowlist

**Verification:**
- `python -m pytest tests/integration/test_auto_repair_loop.py tests/integration/test_revision_and_cancel.py tests/integration/test_generation_provider_failures.py -q`

**Commit:**
```bash
git add src/video_agent/application/repair_prompt_builder.py src/video_agent/application/auto_repair_service.py src/video_agent/application/revision_service.py src/video_agent/application/task_service.py tests/integration/test_auto_repair_loop.py tests/integration/test_revision_and_cancel.py tests/integration/test_generation_provider_failures.py docs/runbooks/beta-ops.md
git commit -m "feat: add patch-oriented repair prompts"
```

---

## Week 4 - Harden execution sandbox and failure surfacing

### Task 4: Enforce stricter local isolation and explicit sandbox failure signals

**Files:**
- Modify: `src/video_agent/safety/runtime_policy.py`
- Modify: `src/video_agent/adapters/rendering/manim_runner.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Test: `tests/integration/test_render_and_hard_validation.py`
- Test: `tests/integration/test_runtime_status_tool.py`
- Create: `tests/integration/test_sandbox_policy.py`
- Docs: `docs/runbooks/local-dev.md`
- Docs: `docs/runbooks/incident-response.md`

**Implementation outline:**
- Add sandbox-oriented settings such as:
  - optional network-disabled mode
  - CPU / memory / process limits where supported
  - stricter temporary-work-root rules
- Surface explicit sandbox policy failures in runtime status and failure context
- Keep deterministic tests with fake binaries

**Verification:**
- `python -m pytest tests/integration/test_render_and_hard_validation.py tests/integration/test_runtime_status_tool.py tests/integration/test_sandbox_policy.py -q`

**Commit:**
```bash
git add src/video_agent/safety/runtime_policy.py src/video_agent/adapters/rendering/manim_runner.py src/video_agent/server/main.py src/video_agent/config.py src/video_agent/application/runtime_service.py tests/integration/test_render_and_hard_validation.py tests/integration/test_runtime_status_tool.py tests/integration/test_sandbox_policy.py docs/runbooks/local-dev.md docs/runbooks/incident-response.md
git commit -m "feat: harden local render sandbox policy"
```

---

## Week 5 - Measure semantic repair quality and gate on evidence

### Task 5: Add a repair-focused evaluation slice and promotion thresholds

**Files:**
- Modify: `evals/beta_prompt_suite.json`
- Create: `src/video_agent/evaluation/repair_reporting.py`
- Modify: `src/video_agent/application/eval_service.py`
- Modify: `src/video_agent/eval/main.py`
- Modify: `scripts/release_candidate_gate.py`
- Test: `tests/integration/test_eval_run_cli.py`
- Create: `tests/unit/evaluation/test_repair_reporting.py`
- Docs: `docs/runbooks/release-checklist.md`
- Docs: `docs/runbooks/real-provider-trial.md`

**Implementation outline:**
- Add a tagged eval subset for semantically repairable failures
- Report:
  - repair attempt rate
  - repair success rate
  - average children per repaired root
  - top failure codes after repair
- Extend RC gate to require a minimum repair success rate for the repair-tagged slice

**Verification:**
- `python -m pytest tests/integration/test_eval_run_cli.py tests/unit/evaluation/test_repair_reporting.py -q`
- `python scripts/release_candidate_gate.py --mode ci`

**Commit:**
```bash
git add evals/beta_prompt_suite.json src/video_agent/evaluation/repair_reporting.py src/video_agent/application/eval_service.py src/video_agent/eval/main.py scripts/release_candidate_gate.py tests/integration/test_eval_run_cli.py tests/unit/evaluation/test_repair_reporting.py docs/runbooks/release-checklist.md docs/runbooks/real-provider-trial.md
git commit -m "feat: add semantic repair evaluation gate"
```

---

## Exit criteria

- Task snapshots surface repair state directly, not only through inferred event history
- Failure context includes semantic diagnosis for common Manim/API misuse
- Auto-repair feedback is structured and patch-oriented instead of purely generic retry text
- Sandbox policy failures are explicit, testable, and operator-visible
- The project tracks repair success as a first-class release signal

## Final verification sequence

```bash
source .venv/bin/activate
python -m pytest tests/unit/validation/test_script_diagnostics.py -q
python -m pytest tests/integration/test_failure_context_artifact.py tests/integration/test_auto_repair_loop.py tests/integration/test_auto_repair_status.py -q
python -m pytest tests/integration/test_render_and_hard_validation.py tests/integration/test_runtime_status_tool.py tests/integration/test_sandbox_policy.py -q
python -m pytest tests/integration/test_eval_run_cli.py tests/unit/evaluation/test_repair_reporting.py -q
python -m pytest -q
python scripts/release_candidate_gate.py --mode ci
```

## Recommended execution order

1. Complete **Week 1** first so later work does not deepen `WorkflowEngine` complexity
2. Complete **Week 2** before trying to tune repair prompts further
3. Complete **Week 3** only after semantic hints exist
4. Complete **Week 4** before broadening real-provider trials
5. Complete **Week 5** last so the gate measures the final repaired system rather than an intermediate shape
