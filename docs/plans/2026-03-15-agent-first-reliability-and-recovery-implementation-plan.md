# Agent-First Reliability and Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `easy-manim` more reliable as an agent-called subsystem by centralizing runtime policy defaults, making evaluation runs resumable, and exposing a machine-decidable failure contract.

**Architecture:** Keep the current local-first `FastMCP + SQLite + filesystem artifacts` shape, but remove policy drift and manual recovery from the hot path. Introduce one shared agent-policy module, persist eval-run case state under the eval artifact root so interrupted runs can be resumed deterministically, and add a small failure-contract layer that turns validation and runtime failures into machine-actionable decisions for upstream agents.

**Tech Stack:** Python 3.14, Pydantic, FastMCP, SQLite, pytest, JSON artifact manifests, existing eval/reporting services, and the current local filesystem artifact model.

---

## Recommended Approach

**Recommended: unified agent reliability substrate**
- Put all agent-facing defaults behind one importable policy module.
- Persist eval progress per case so runs can be resumed or selectively replayed.
- Expose a structured failure contract to MCP tools and failure artifacts.

**Why this is the right next move**
- removes the configuration drift we already observed between `Settings` and `build_settings(...)`
- makes long-running live-provider evals recoverable without manual artifact merging
- gives higher-level agents deterministic signals for “retry / repair / stop / escalate”

**Alternative A: only add resumable eval runs**
- fastest operational win
- still leaves policy drift and weak machine-decision semantics in place

**Alternative B: only harden auto-repair prompts**
- improves some live failures
- does not address interrupted runs or agent orchestration reliability

---

### Task 1: Extract shared agent policy defaults into a single source of truth

**Files:**
- Create: `src/video_agent/agent_policy.py`
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/application/eval_service.py`
- Test: `tests/unit/test_settings.py`
- Test: `tests/integration/test_eval_run_cli.py`
- Test: `tests/unit/test_agent_policy.py`

**Step 1: Write the failing tests**

Create `tests/unit/test_agent_policy.py` with focused assertions like:

```python
from video_agent.agent_policy import (
    DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES,
    QUALITY_ISSUE_CODES,
)


def test_agent_policy_exposes_formula_repair_issue_codes() -> None:
    assert "unsafe_transformmatchingtex_slice" in DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES
    assert "unsafe_bare_tex_selection" in DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES
    assert "unsafe_bare_tex_highlight" in DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES


def test_agent_policy_exposes_preview_quality_issue_codes() -> None:
    assert "near_blank_preview" in QUALITY_ISSUE_CODES
    assert "static_previews" in QUALITY_ISSUE_CODES
```

Extend `tests/unit/test_settings.py` so it verifies both:
- `Settings()` uses the shared retryable-issue defaults
- `build_settings(Path("data"))` also uses the same defaults when the env var is unset

Extend `tests/integration/test_eval_run_cli.py` with a small assertion that the eval path still recognizes the quality issue-code set from one shared location rather than a duplicated local constant.

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/test_agent_policy.py \
  tests/unit/test_settings.py \
  tests/integration/test_eval_run_cli.py \
  -q
```

Expected:
- FAIL because `src/video_agent/agent_policy.py` does not exist yet
- or FAIL because some call sites still keep duplicated literal lists

**Step 3: Write minimal implementation**

Create `src/video_agent/agent_policy.py` with shared constants such as:

```python
DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES = [
    "render_failed",
    "generation_failed",
    "syntax_error",
    "missing_scene",
    "unsafe_transformmatchingtex_slice",
    "unsafe_bare_tex_selection",
    "unsafe_bare_tex_highlight",
    "black_frames",
    "frozen_tail",
    "encoding_error",
    "min_width_not_met",
    "min_height_not_met",
    "min_duration_not_met",
]

QUALITY_ISSUE_CODES = {
    "near_blank_preview",
    "static_previews",
    "black_frames",
    "frozen_tail",
    "encoding_error",
    "min_width_not_met",
    "min_height_not_met",
    "min_duration_not_met",
}
```

Then update:
- `src/video_agent/config.py` to use `DEFAULT_AUTO_REPAIR_RETRYABLE_ISSUE_CODES`
- `src/video_agent/server/main.py` to use the same constant in `build_settings(...)`
- `src/video_agent/application/eval_service.py` to import `QUALITY_ISSUE_CODES` instead of maintaining a second copy

Keep this task intentionally narrow: no new behavior, only shared defaults and deduplication.

**Step 4: Run the tests to verify they pass**

Run the same command again:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/test_agent_policy.py \
  tests/unit/test_settings.py \
  tests/integration/test_eval_run_cli.py \
  -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add \
  src/video_agent/agent_policy.py \
  src/video_agent/config.py \
  src/video_agent/server/main.py \
  src/video_agent/application/eval_service.py \
  tests/unit/test_agent_policy.py \
  tests/unit/test_settings.py \
  tests/integration/test_eval_run_cli.py
git commit -m "refactor: centralize agent policy defaults"
```

---

### Task 2: Persist eval-run state so interrupted live runs can be resumed or selectively replayed

**Files:**
- Create: `src/video_agent/evaluation/run_manifest.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/application/eval_service.py`
- Modify: `src/video_agent/eval/main.py`
- Test: `tests/unit/evaluation/test_run_manifest.py`
- Test: `tests/integration/test_eval_run_cli.py`
- Docs: `docs/runbooks/real-provider-trial.md`
- Docs: `docs/runbooks/release-checklist.md`

**Step 1: Write the failing tests**

Create `tests/unit/evaluation/test_run_manifest.py` with cases like:

```python
from pathlib import Path

from video_agent.evaluation.run_manifest import EvalRunManifest, EvalCaseState


def test_run_manifest_round_trips_case_state(tmp_path: Path) -> None:
    manifest = EvalRunManifest(
        run_id="run-123",
        suite_id="demo",
        provider="stub",
        include_tags=["quality"],
        match_all_tags=True,
        cases={
            "case-a": EvalCaseState(status="completed", root_task_id="task-1", terminal_task_id="task-1"),
        },
    )

    path = tmp_path / "run.json"
    path.write_text(manifest.model_dump_json(indent=2))
    restored = EvalRunManifest.model_validate_json(path.read_text())

    assert restored.cases["case-a"].status == "completed"
```

Extend `tests/integration/test_eval_run_cli.py` with a failing CLI test like:

```python
def test_eval_run_cli_can_resume_existing_run(tmp_path: Path) -> None:
    ...
    first = subprocess.run([... "--suite", str(suite_path), "--json"], ...)
    first_payload = json.loads(first.stdout)

    resumed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            str(suite_path),
            "--resume-run-id",
            first_payload["run_id"],
            "--json",
        ],
        ...
    )

    resumed_payload = json.loads(resumed.stdout)
    assert resumed_payload["run_id"] == first_payload["run_id"]
```

Use a fake suite and fake commands so the test stays deterministic.

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/evaluation/test_run_manifest.py \
  tests/integration/test_eval_run_cli.py \
  -q
```

Expected:
- FAIL because the manifest model does not exist
- FAIL because the CLI has no `--resume-run-id` path

**Step 3: Write minimal implementation**

Create `src/video_agent/evaluation/run_manifest.py` with compact persisted models:

```python
class EvalCaseState(BaseModel):
    status: str = "pending"
    root_task_id: str | None = None
    terminal_task_id: str | None = None
    issue_codes: list[str] = Field(default_factory=list)


class EvalRunManifest(BaseModel):
    run_id: str
    suite_id: str
    provider: str
    include_tags: list[str] = Field(default_factory=list)
    match_all_tags: bool = False
    cases: dict[str, EvalCaseState] = Field(default_factory=dict)
```

In `src/video_agent/adapters/storage/artifact_store.py` add helpers:
- `eval_run_manifest_path(run_id)`
- `write_eval_run_manifest(run_id, payload)`
- `read_eval_run_manifest(run_id)`

In `src/video_agent/application/eval_service.py`:
- initialize a manifest at the start of `run_suite(...)`
- mark each case as `pending`, `running`, then `completed` / `failed`
- when resuming, skip cases already marked `completed`
- allow rerunning a case explicitly if requested

In `src/video_agent/eval/main.py` add CLI flags:
- `--resume-run-id`
- `--rerun-case` (repeatable)

Keep the first implementation deliberately simple:
- same suite / tag filter required when resuming
- only skip already completed cases
- still write the final `summary.json`, `summary.md`, and `review_digest.md`

**Step 4: Run the tests to verify they pass**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/evaluation/test_run_manifest.py \
  tests/integration/test_eval_run_cli.py \
  -q
```

Expected: PASS

**Step 5: Update docs**

Update:
- `docs/runbooks/real-provider-trial.md` to show a resume flow such as `--resume-run-id <run_id>`
- `docs/runbooks/release-checklist.md` to mention resumed live runs are valid only when the persisted manifest and final summary agree on case count

**Step 6: Commit**

```bash
git add \
  src/video_agent/evaluation/run_manifest.py \
  src/video_agent/adapters/storage/artifact_store.py \
  src/video_agent/application/eval_service.py \
  src/video_agent/eval/main.py \
  tests/unit/evaluation/test_run_manifest.py \
  tests/integration/test_eval_run_cli.py \
  docs/runbooks/real-provider-trial.md \
  docs/runbooks/release-checklist.md
git commit -m "feat: add resumable evaluation run manifests"
```

---

### Task 3: Add a machine-decidable failure contract for agent orchestration

**Files:**
- Create: `src/video_agent/application/failure_contract.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/application/failure_context.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Test: `tests/unit/application/test_failure_contract.py`
- Test: `tests/integration/test_failure_context_artifact.py`
- Test: `tests/integration/test_mcp_tools.py`
- Docs: `docs/runbooks/beta-ops.md`

**Step 1: Write the failing tests**

Create `tests/unit/application/test_failure_contract.py` with a focused behavior like:

```python
from video_agent.application.failure_contract import build_failure_contract


def test_failure_contract_marks_render_failed_as_retryable() -> None:
    contract = build_failure_contract(
        issue_code="render_failed",
        summary="Render failed",
        preview_issue_codes=[],
        retryable_issue_codes=["render_failed"],
    )

    assert contract.retryable is True
    assert contract.blocking_layer == "render"
    assert contract.recommended_action == "auto_repair"
```

Add another case for:

```python
contract = build_failure_contract(
    issue_code="provider_auth_error",
    ...
)

assert contract.retryable is False
assert contract.recommended_action == "fix_credentials"
```

Extend `tests/integration/test_failure_context_artifact.py` so it asserts:
- `failure_context.json` now contains a `failure_contract` object
- the object includes fields like `retryable`, `blocking_layer`, and `recommended_action`

Extend `tests/integration/test_mcp_tools.py` so `get_video_task_tool(...)` exposes a top-level `failure_contract` when the task failed.

**Step 2: Run the tests to verify they fail**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/application/test_failure_contract.py \
  tests/integration/test_failure_context_artifact.py \
  tests/integration/test_mcp_tools.py \
  -q
```

Expected:
- FAIL because the failure-contract builder does not exist
- FAIL because snapshots and artifacts do not expose the new contract

**Step 3: Write minimal implementation**

Create `src/video_agent/application/failure_contract.py` with:

```python
class FailureContract(BaseModel):
    issue_code: str | None = None
    retryable: bool = False
    blocking_layer: str = "unknown"
    recommended_action: str = "inspect_failure_context"
    repair_strategy: str | None = None
    suggested_tool: str | None = None
    human_review_required: bool = False
```

Add a `build_failure_contract(...)` helper that maps common issue-code families:
- `provider_*` -> provider / credentials / wait / inspect upstream
- `render_failed` -> render / auto_repair
- `unsafe_*` -> validation / auto_repair
- `near_blank_preview`, `static_previews` -> preview / auto_repair
- `latex_dependency_missing` -> runtime / install_dependencies

Then wire it through:
- `src/video_agent/application/failure_context.py` so the contract is persisted into `failure_context.json`
- `src/video_agent/application/task_service.py` so failed task snapshots expose the contract
- `src/video_agent/adapters/storage/artifact_store.py` to optionally write `artifacts/failure_contract.json`
- `src/video_agent/server/mcp_tools.py` and `src/video_agent/server/fastmcp_server.py` to expose either:
  - a new `get_failure_contract` tool, or
  - an explicit `failure_contract` block on `get_video_task`

Prefer doing both: snapshot exposure plus a dedicated tool for agent convenience.

**Step 4: Run the tests to verify they pass**

Run:

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/application/test_failure_contract.py \
  tests/integration/test_failure_context_artifact.py \
  tests/integration/test_mcp_tools.py \
  -q
```

Expected: PASS

**Step 5: Update docs**

Update `docs/runbooks/beta-ops.md` to explain:
- how operators and upstream agents should interpret `retryable`
- when to trust `recommended_action=auto_repair`
- when `human_review_required=true` should stop autonomous retries

**Step 6: Commit**

```bash
git add \
  src/video_agent/application/failure_contract.py \
  src/video_agent/adapters/storage/artifact_store.py \
  src/video_agent/application/failure_context.py \
  src/video_agent/application/task_service.py \
  src/video_agent/application/workflow_engine.py \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/server/fastmcp_server.py \
  tests/unit/application/test_failure_contract.py \
  tests/integration/test_failure_context_artifact.py \
  tests/integration/test_mcp_tools.py \
  docs/runbooks/beta-ops.md
git commit -m "feat: expose machine-decidable failure contracts"
```

---

### Task 4: Final verification for the agent-first reliability slice

**Files:**
- Verify: `src/video_agent/agent_policy.py`
- Verify: `src/video_agent/evaluation/run_manifest.py`
- Verify: `src/video_agent/application/failure_contract.py`
- Verify: `src/video_agent/eval/main.py`
- Verify: `src/video_agent/server/fastmcp_server.py`
- Verify: `tests/integration/test_eval_run_cli.py`
- Verify: `tests/integration/test_failure_context_artifact.py`
- Verify: `tests/integration/test_mcp_tools.py`

**Step 1: Run focused verification**

```bash
source .venv/bin/activate && \
python -m pytest \
  tests/unit/test_agent_policy.py \
  tests/unit/test_settings.py \
  tests/unit/evaluation/test_run_manifest.py \
  tests/unit/application/test_failure_contract.py \
  tests/integration/test_eval_run_cli.py \
  tests/integration/test_failure_context_artifact.py \
  tests/integration/test_mcp_tools.py \
  tests/e2e/test_live_provider_gate.py \
  -q
```

Expected: PASS

**Step 2: Run full verification**

```bash
source .venv/bin/activate && python -m pytest -q
```

Expected: PASS

**Step 3: Run deterministic release verification**

```bash
source .venv/bin/activate && python scripts/release_candidate_gate.py --mode ci
```

Expected:
- `ok: true`
- deterministic repair eval still passes

**Step 4: Run a narrow resume-path smoke**

Use fake commands and a tiny suite to prove:
- first eval run creates a manifest
- resumed eval run reuses the same `run_id`
- already completed cases are skipped

Run the narrowest adjacent CLI test if one was added for this path.

**Step 5: Review changed files**

```bash
git status -sb
git diff -- \
  src/video_agent/agent_policy.py \
  src/video_agent/config.py \
  src/video_agent/server/main.py \
  src/video_agent/adapters/storage/artifact_store.py \
  src/video_agent/application/eval_service.py \
  src/video_agent/eval/main.py \
  src/video_agent/application/failure_contract.py \
  src/video_agent/application/failure_context.py \
  src/video_agent/application/task_service.py \
  src/video_agent/application/workflow_engine.py \
  src/video_agent/server/mcp_tools.py \
  src/video_agent/server/fastmcp_server.py \
  tests/unit/test_agent_policy.py \
  tests/unit/test_settings.py \
  tests/unit/evaluation/test_run_manifest.py \
  tests/unit/application/test_failure_contract.py \
  tests/integration/test_eval_run_cli.py \
  tests/integration/test_failure_context_artifact.py \
  tests/integration/test_mcp_tools.py \
  docs/runbooks/real-provider-trial.md \
  docs/runbooks/release-checklist.md \
  docs/runbooks/beta-ops.md
```

**Step 6: Commit**

```bash
git add .
git commit -m "feat: harden agent-first reliability and recovery"
```
