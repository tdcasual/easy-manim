# Phase 1 and Phase 2 Agent Hardening and Self-Repair Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the current workflow-style Manim agent into a more reliable and more autonomous system by first hardening runtime reliability and then adding an internal self-repair loop that can revise failed tasks automatically.

**Architecture:** Keep the current single-workflow execution model, SQLite storage, and MCP interface intact. In Phase 1, deepen runtime checks, subprocess environment control, validation policy support, and worker identity so failures are trustworthy. In Phase 2, add structured failure-context capture plus a bounded auto-revision loop that reuses the existing task lineage model instead of introducing multi-agent orchestration prematurely.

**Tech Stack:** Python 3.13, Pydantic, FastMCP, SQLite, pytest, standard-library `subprocess`/`json`/`pathlib`, local filesystem artifacts, and existing Manim / ffmpeg / ffprobe / LaTeX runtime dependencies.

---

## Assumptions and Non-Goals
- Stay on the current `FastMCP + SQLite + local filesystem` architecture.
- Do **not** introduce multi-agent role decomposition in this plan.
- Do **not** add hosted queues, external databases, or remote artifact stores.
- Keep every change backwards-compatible with existing MCP tool names and `video-task://...` resource references.
- Prefer reusing existing task lineage (`root_task_id`, `parent_task_id`, `inherited_from_task_id`) over inventing a second retry model.

## Recommended Approach
- **Recommended:** Phase 1 first, then Phase 2. Make failures reliable before adding auto-repair.
- **Alternative:** Add auto-repair first. This is faster to demo but risks creating loops around noisy runtime failures.
- **Not recommended now:** Split into planner / coder / reviewer agents before the underlying runtime and failure semantics are trustworthy.

## Weekly Outcomes
- **Week 1:** Runtime inspection can prove not only that commands exist, but that the critical render pipeline is actually runnable.
- **Week 2:** Render subprocesses receive an explicit execution environment, so real-provider runs behave the same way as shell repros.
- **Week 3:** `validation_profile` becomes meaningful, and task-specific validation thresholds are enforced by the workflow.
- **Week 4:** Every failed task writes a structured failure-context artifact that can be reused for manual diagnosis and automatic revision.
- **Week 5:** Failed tasks can auto-spawn bounded revision attempts with synthesized feedback and clear stop conditions.
- **Week 6:** MCP snapshots and operator docs clearly show lineage, repair outcomes, and when auto-repair stopped.

---

## Week 1 - Deep runtime smoke instead of shallow binary presence checks

### Task 1: Add runtime smoke checks for render prerequisites

**Files:**
- Create: `src/video_agent/validation/runtime_smoke.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/doctor/main.py`
- Test: `tests/unit/validation/test_runtime_smoke.py`
- Test: `tests/integration/test_runtime_status_tool.py`
- Test: `tests/integration/test_doctor_cli.py`
- Docs: `docs/runbooks/local-dev.md`

**Step 1: Write the failing tests**

In `tests/unit/validation/test_runtime_smoke.py` add tests like:

```python
from pathlib import Path

from video_agent.validation.runtime_smoke import run_mathtex_smoke


def test_mathtex_smoke_reports_success_when_tex_pipeline_writes_svg(tmp_path: Path) -> None:
    result = run_mathtex_smoke(
        work_dir=tmp_path,
        latex_command="fake-latex",
        dvisvgm_command="fake-dvisvgm",
    )

    assert result.available is True
    assert result.error is None


def test_mathtex_smoke_reports_failure_details_when_svg_conversion_fails(tmp_path: Path) -> None:
    result = run_mathtex_smoke(
        work_dir=tmp_path,
        latex_command="broken-latex",
        dvisvgm_command="broken-dvisvgm",
    )

    assert result.available is False
    assert "dvisvgm" in result.error.lower()
```

In `tests/integration/test_runtime_status_tool.py` add an assertion that runtime status can expose a deeper feature payload, not only `available=True/False`.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/validation/test_runtime_smoke.py tests/integration/test_runtime_status_tool.py tests/integration/test_doctor_cli.py -q`

Expected: FAIL because the smoke checker and richer runtime payload do not exist yet.

**Step 3: Write minimal implementation**

- In `src/video_agent/validation/runtime_smoke.py`, add small smoke helpers that:
  - create a temp work directory
  - invoke the configured commands in the smallest possible way
  - return structured success/failure info rather than throwing raw exceptions
- In `src/video_agent/application/runtime_service.py`:
  - add richer feature status fields such as `checked`, `available`, `missing_checks`, and `smoke_error`
  - keep the existing binary presence checks for speed
  - add an opt-in deeper smoke path for doctor/runtime inspection
- In `src/video_agent/doctor/main.py`:
  - surface the deeper failure message in JSON and text mode
  - keep `--require-latex` semantics, but now fail when the smoke check fails even if binaries are present
- Update `docs/runbooks/local-dev.md` to explain the difference between binary detection and smoke validation.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/validation/test_runtime_smoke.py tests/integration/test_runtime_status_tool.py tests/integration/test_doctor_cli.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/validation/runtime_smoke.py src/video_agent/application/runtime_service.py src/video_agent/doctor/main.py tests/unit/validation/test_runtime_smoke.py tests/integration/test_runtime_status_tool.py tests/integration/test_doctor_cli.py docs/runbooks/local-dev.md
git commit -m "feat: add runtime smoke checks for render prerequisites"
```

---

## Week 2 - Explicit subprocess environment for reproducible rendering

### Task 2: Pass a controlled render environment into Manim and related subprocesses

**Files:**
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/adapters/rendering/manim_runner.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Test: `tests/integration/test_render_and_hard_validation.py`
- Test: `tests/integration/test_workflow_completion.py`
- Docs: `docs/runbooks/local-dev.md`
- Docs: `docs/runbooks/real-provider-trial.md`

**Step 1: Write the failing tests**

In `tests/integration/test_render_and_hard_validation.py` add a test like:

```python
def test_manim_runner_passes_explicit_environment_to_subprocess(tmp_path: Path) -> None:
    runner = ManimRunner(command=str(fake_manim))
    result = runner.render(
        script_path=script_path,
        output_dir=tmp_path / "out",
        timeout_seconds=30,
        env={"TEXMFCNF": "/expected/path"},
    )

    assert result.exit_code == 0
    assert (tmp_path / "out" / "env-captured.txt").read_text() == "/expected/path"
```

In `tests/integration/test_workflow_completion.py` add a workflow-level test proving a task can succeed only when the configured render environment is forwarded.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_render_and_hard_validation.py tests/integration/test_workflow_completion.py -q`

Expected: FAIL because `ManimRunner.render()` does not accept or pass an explicit environment.

**Step 3: Write minimal implementation**

- In `src/video_agent/config.py`, add explicit optional render environment fields for critical runtime variables needed by external tools.
- In `src/video_agent/server/main.py`, derive those fields from environment variables so shell configuration can be frozen into app settings.
- In `src/video_agent/server/app.py`, wire the settings into `ManimRunner`.
- In `src/video_agent/adapters/rendering/manim_runner.py`:
  - add an `env` parameter to `render()`
  - pass it through `subprocess.run(..., env=...)`
- In `src/video_agent/application/workflow_engine.py`, build the exact render environment once and pass it to the runner.
- Update the runbooks so operators know these values must be present in the service process, not only in an interactive shell.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_render_and_hard_validation.py tests/integration/test_workflow_completion.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/config.py src/video_agent/server/main.py src/video_agent/server/app.py src/video_agent/adapters/rendering/manim_runner.py src/video_agent/application/workflow_engine.py tests/integration/test_render_and_hard_validation.py tests/integration/test_workflow_completion.py docs/runbooks/local-dev.md docs/runbooks/real-provider-trial.md
git commit -m "fix: pass explicit render environment to manim subprocesses"
```

---

## Week 3 - Make validation profiles actually control validation behavior

### Task 3: Turn `validation_profile` into executable validation policy

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/validation/hard_validation.py`
- Modify: `src/video_agent/validation/rule_validation.py`
- Modify: `src/video_agent/domain/validation_models.py`
- Test: `tests/integration/test_frame_and_rule_validation.py`
- Test: `tests/integration/test_mcp_tools.py`
- Create: `tests/integration/test_validation_profiles.py`
- Docs: `docs/runbooks/beta-ops.md`

**Step 1: Write the failing tests**

In `tests/integration/test_validation_profiles.py` add tests like:

```python
def test_validation_profile_can_raise_minimum_duration_threshold(tmp_path: Path) -> None:
    app = create_app_context(settings_with_short_video(tmp_path))
    created = app.task_service.create_video_task(
        prompt="draw a circle",
        validation_profile={"min_duration_seconds": 5.0},
    )

    app.worker.run_once()
    snapshot = app.task_service.get_video_task(created.task_id)

    assert snapshot.status == "failed"
    assert snapshot.latest_validation_summary["issues"][0]["code"] == "min_duration_not_met"


def test_validation_profile_can_disable_preview_related_rule(tmp_path: Path) -> None:
    ...
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_frame_and_rule_validation.py tests/integration/test_validation_profiles.py tests/integration/test_mcp_tools.py -q`

Expected: FAIL because validators ignore `validation_profile`.

**Step 3: Write minimal implementation**

- In `src/video_agent/domain/validation_models.py`, add optional profile-aware detail fields only if needed to keep the API explicit.
- In `src/video_agent/application/workflow_engine.py`, pass `task.validation_profile` into both validators.
- In `src/video_agent/validation/hard_validation.py`, support thresholds such as:
  - `min_width`
  - `min_height`
  - `min_duration_seconds`
- In `src/video_agent/validation/rule_validation.py`, support toggles and thresholds such as:
  - enable/disable heuristic checks
  - stricter empty/corrupt file checks
- In `src/video_agent/application/task_service.py`, preserve the existing API shape; only normalize user-supplied profile values if needed.
- Update `docs/runbooks/beta-ops.md` with examples of stricter validation profiles for beta trials.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_frame_and_rule_validation.py tests/integration/test_validation_profiles.py tests/integration/test_mcp_tools.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/task_service.py src/video_agent/application/workflow_engine.py src/video_agent/validation/hard_validation.py src/video_agent/validation/rule_validation.py src/video_agent/domain/validation_models.py tests/integration/test_frame_and_rule_validation.py tests/integration/test_validation_profiles.py tests/integration/test_mcp_tools.py docs/runbooks/beta-ops.md
git commit -m "feat: apply validation profiles during workflow validation"
```

---

## Week 4 - Capture structured failure context instead of only raw logs

### Task 4: Write a failure-context artifact for every failed task

**Files:**
- Create: `src/video_agent/application/failure_context.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/server/mcp_resources.py`
- Test: `tests/integration/test_generation_provider_failures.py`
- Create: `tests/integration/test_failure_context_artifact.py`
- Docs: `docs/runbooks/incident-response.md`

**Step 1: Write the failing tests**

In `tests/integration/test_failure_context_artifact.py` add tests like:

```python
def test_failed_task_writes_failure_context_artifact(tmp_path: Path) -> None:
    app = create_app_context(settings_with_failing_render(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    failure_context = app.artifact_store.task_dir(created.task_id) / "artifacts" / "failure_context.json"
    payload = json.loads(failure_context.read_text())

    assert payload["task_id"] == created.task_id
    assert payload["failure_code"]
    assert payload["phase"] == "failed"
    assert "summary" in payload
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_generation_provider_failures.py tests/integration/test_failure_context_artifact.py -q`

Expected: FAIL because no failure-context artifact is written or exposed.

**Step 3: Write minimal implementation**

- In `src/video_agent/application/failure_context.py`, add a small builder that collects:
  - task identifiers and lineage
  - terminal phase
  - top validation issue code
  - summary
  - latest stderr / provider error / missing runtime checks if present
  - current script resource or path
- In `src/video_agent/adapters/storage/artifact_store.py`, add a canonical path helper and write method for `artifacts/failure_context.json`.
- In `src/video_agent/application/workflow_engine.py`, write the artifact inside `_fail_task()`.
- In `src/video_agent/server/fastmcp_server.py` and `src/video_agent/server/mcp_resources.py`, expose it as another readable `video-task://...` resource.
- Update `docs/runbooks/incident-response.md` to make this the first inspection target after a failed run.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_generation_provider_failures.py tests/integration/test_failure_context_artifact.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/failure_context.py src/video_agent/adapters/storage/artifact_store.py src/video_agent/application/workflow_engine.py src/video_agent/server/fastmcp_server.py src/video_agent/server/mcp_resources.py tests/integration/test_generation_provider_failures.py tests/integration/test_failure_context_artifact.py docs/runbooks/incident-response.md
git commit -m "feat: persist structured failure context artifacts"
```

---

## Week 5 - Add bounded auto-repair on top of existing task lineage

### Task 5: Create automatic revision attempts for repairable failures

**Files:**
- Create: `src/video_agent/application/auto_repair_service.py`
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/application/revision_service.py`
- Modify: `src/video_agent/application/workflow_engine.py`
- Test: `tests/integration/test_retry_video_task.py`
- Test: `tests/integration/test_revision_and_cancel.py`
- Create: `tests/integration/test_auto_repair_loop.py`
- Docs: `docs/runbooks/beta-ops.md`

**Step 1: Write the failing tests**

In `tests/integration/test_auto_repair_loop.py` add tests like:

```python
def test_failed_task_can_spawn_auto_revision_within_budget(tmp_path: Path) -> None:
    app = create_app_context(settings_with_auto_repair(tmp_path))
    created = app.task_service.create_video_task(prompt="draw a circle")

    app.worker.run_once()

    children = app.store.list_tasks(limit=10)
    assert len([item for item in children if item["task_id"] != created.task_id]) == 1


def test_auto_repair_does_not_retry_non_repairable_failure(tmp_path: Path) -> None:
    ...
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_retry_video_task.py tests/integration/test_revision_and_cancel.py tests/integration/test_auto_repair_loop.py -q`

Expected: FAIL because the system never auto-creates revision children.

**Step 3: Write minimal implementation**

- In `src/video_agent/config.py`, add small bounded settings such as:
  - `auto_repair_enabled`
  - `auto_repair_max_children_per_root`
  - `auto_repair_retryable_issue_codes`
- In `src/video_agent/application/auto_repair_service.py`, add logic that:
  - inspects the latest validation report
  - decides whether the failure is retryable
  - synthesizes revision feedback from the failure context artifact
  - creates a revision child using existing lineage semantics
- In `src/video_agent/application/workflow_engine.py`, call the new service only after a task is marked failed.
- In `src/video_agent/application/task_service.py` and `src/video_agent/application/revision_service.py`, keep the child-task API explicit and reuse the current lineage fields.
- Update `docs/runbooks/beta-ops.md` with a note that auto-repair is bounded and not a replacement for operator review.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_retry_video_task.py tests/integration/test_revision_and_cancel.py tests/integration/test_auto_repair_loop.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/auto_repair_service.py src/video_agent/config.py src/video_agent/server/main.py src/video_agent/application/task_service.py src/video_agent/application/revision_service.py src/video_agent/application/workflow_engine.py tests/integration/test_retry_video_task.py tests/integration/test_revision_and_cancel.py tests/integration/test_auto_repair_loop.py docs/runbooks/beta-ops.md
git commit -m "feat: add bounded automatic repair revisions"
```

---

## Week 6 - Surface repair lineage and stop reasons to clients and operators

### Task 6: Expose repair summary in task snapshots and MCP tools

**Files:**
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/worker/worker_loop.py`
- Test: `tests/integration/test_mcp_tools.py`
- Test: `tests/integration/test_worker_status.py`
- Create: `tests/integration/test_auto_repair_status.py`
- Docs: `docs/runbooks/incident-response.md`
- Docs: `docs/runbooks/release-checklist.md`

**Step 1: Write the failing tests**

In `tests/integration/test_auto_repair_status.py` add tests like:

```python
def test_get_video_task_exposes_auto_repair_summary(tmp_path: Path) -> None:
    app = create_app_context(settings_with_auto_repair(tmp_path))
    created = seed_failed_task_with_child_revision(app)

    snapshot = app.task_service.get_video_task(created.task_id)

    assert snapshot.artifact_summary["repair_children"] >= 1
    assert snapshot.latest_validation_summary
    assert snapshot.auto_repair_summary["stopped_reason"]
```

In `tests/integration/test_worker_status.py`, add an assertion that worker heartbeat details include a stable worker identity rather than assuming a hard-coded singleton.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/integration/test_mcp_tools.py tests/integration/test_worker_status.py tests/integration/test_auto_repair_status.py -q`

Expected: FAIL because task snapshots and worker status do not expose repair lifecycle details yet.

**Step 3: Write minimal implementation**

- In `src/video_agent/application/task_service.py`, extend `VideoTaskSnapshot` with an `auto_repair_summary` field that reports:
  - child count in lineage
  - whether auto-repair is enabled
  - remaining budget
  - stop reason, if any
- In `src/video_agent/worker/worker_loop.py`, allow configurable worker IDs so multi-process use is observable.
- In `src/video_agent/application/runtime_service.py`, surface those worker IDs through runtime status.
- In `src/video_agent/server/mcp_tools.py` and `src/video_agent/server/fastmcp_server.py`, keep the public API shape stable while returning the richer payload.
- Update `docs/runbooks/incident-response.md` and `docs/runbooks/release-checklist.md` so operators know how to tell whether a failure exhausted repair budget or still has repair capacity.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_mcp_tools.py tests/integration/test_worker_status.py tests/integration/test_auto_repair_status.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/task_service.py src/video_agent/server/mcp_tools.py src/video_agent/server/fastmcp_server.py src/video_agent/application/runtime_service.py src/video_agent/worker/worker_loop.py tests/integration/test_mcp_tools.py tests/integration/test_worker_status.py tests/integration/test_auto_repair_status.py docs/runbooks/incident-response.md docs/runbooks/release-checklist.md
git commit -m "feat: expose auto-repair lineage and worker identity"
```

---

## Final Verification Sequence

Run these commands after Week 6 implementation is complete:

```bash
python -m pytest tests/unit/validation/test_runtime_smoke.py -q
python -m pytest tests/integration/test_runtime_status_tool.py tests/integration/test_doctor_cli.py -q
python -m pytest tests/integration/test_render_and_hard_validation.py tests/integration/test_workflow_completion.py -q
python -m pytest tests/integration/test_validation_profiles.py tests/integration/test_frame_and_rule_validation.py -q
python -m pytest tests/integration/test_failure_context_artifact.py tests/integration/test_generation_provider_failures.py -q
python -m pytest tests/integration/test_auto_repair_loop.py tests/integration/test_auto_repair_status.py tests/integration/test_retry_video_task.py tests/integration/test_revision_and_cancel.py -q
python -m pytest -q
```

Expected:
- all focused suites pass before moving to the next week
- full suite passes after the final week

## Exit Criteria
- Runtime inspection can catch “binary exists but feature still broken” cases.
- Real-provider MathTex runs succeed without relying on an interactive shell session.
- `validation_profile` changes behavior in a testable way.
- Failed tasks produce a structured failure-context artifact.
- Auto-repair can create bounded revision children for retryable failures only.
- MCP snapshots and runtime status explain repair lineage and stop reasons clearly.

## Recommended Execution Order
- Execute **Weeks 1-3** first in one branch as “Phase 1 reliability hardening”.
- Execute **Weeks 4-6** only after Phase 1 is verified against a real-provider smoke.
- Keep each weekly milestone mergeable on its own.
