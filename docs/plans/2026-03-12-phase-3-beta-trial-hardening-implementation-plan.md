# Phase 3 Beta Trial Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the current local-first beta operable by another engineer on a fresh machine with clear diagnostics, queue guardrails, cleanup tooling, and one-command beta acceptance verification.

**Architecture:** Keep the current SQLite + local-filesystem architecture intact and harden the operating surface around it. Add a reusable runtime diagnostics service, expose worker liveness and admission-control signals through MCP and CLIs, add safe task-retention utilities, and extract the existing end-to-end beta flow into a repeatable smoke harness used by humans and CI.

**Tech Stack:** Python 3.13, Pydantic, FastMCP, SQLite, pytest, httpx, Docker, standard-library `argparse`, `shutil`, `zipfile`, and `subprocess`.

---

## Assumptions and Non-Goals
- This phase optimizes for **real beta usage and operator confidence**, not for distributed scaling.
- Stay on SQLite + local artifact storage in this phase.
- Do **not** add multi-tenant auth, remote queues, object storage, or hosted deployment orchestration here.
- Reuse the current fake-binary E2E strategy so tests stay deterministic and cheap.

## Weekly Outcomes
- **Week 1:** An operator can run a doctor/status flow and immediately see whether binaries, provider config, storage paths, and server mode are healthy.
- **Week 2:** The system exposes worker heartbeats and rejects runaway queue growth before the beta stack becomes confusing to operate.
- **Week 3:** Operators can safely clean old tasks and export a single task bundle for debugging/support.
- **Week 4:** A single smoke command verifies the beta stack end-to-end locally and in CI, and the runbooks become release-grade.

---

## Week 1 - Runtime diagnostics and preflight

### Task 1: Add runtime diagnostics service and MCP status tool

**Files:**
- Create: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `src/video_agent/server/fastmcp_server.py`
- Test: `tests/integration/test_runtime_status_tool.py`

**Step 1: Write the failing integration test**

```python
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_runtime_status_tool


def test_runtime_status_tool_reports_binary_and_provider_state(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    settings = Settings(
        data_dir=data_dir,
        database_path=data_dir / "video_agent.db",
        artifact_root=data_dir / "tasks",
        manim_command="manim",
        ffmpeg_command="ffmpeg",
        ffprobe_command="ffprobe",
        llm_provider="stub",
        run_embedded_worker=False,
    )
    context = create_app_context(settings)

    payload = get_runtime_status_tool(context, {})

    assert payload["provider"]["mode"] == "stub"
    assert payload["storage"]["data_dir"].endswith("data")
    assert set(payload["checks"]).issuperset({"manim", "ffmpeg", "ffprobe"})
    assert payload["worker"]["embedded"] is False
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_runtime_status_tool.py -q`
Expected: FAIL because the runtime service and tool do not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/application/runtime_service.py` add:
- `RuntimeCheckResult`
- `RuntimeStatus`
- `RuntimeService.inspect()`

Implementation notes:
- Use `shutil.which()` for command discovery when the configured command is not an absolute path.
- Return explicit booleans instead of throwing for missing binaries.
- Include:
  - `storage`: `data_dir`, `database_path`, `artifact_root`
  - `provider`: `mode`, `configured`, `base_url_present`
  - `worker`: `embedded`
  - `checks`: binary availability + resolved path if found

In `src/video_agent/server/app.py`:
- Instantiate `RuntimeService(settings=settings)` and add it to `AppContext`.

In `src/video_agent/server/mcp_tools.py` add:
- `get_runtime_status_tool(context, payload)` returning `RuntimeStatus.model_dump(mode="json")`

In `src/video_agent/server/fastmcp_server.py` add:
- MCP tool `get_runtime_status`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_runtime_status_tool.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/runtime_service.py src/video_agent/server/app.py src/video_agent/server/mcp_tools.py src/video_agent/server/fastmcp_server.py tests/integration/test_runtime_status_tool.py
git commit -m "feat: add runtime diagnostics tool"
```

### Task 2: Add doctor CLI built on runtime diagnostics

**Files:**
- Create: `src/video_agent/doctor/main.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/runbooks/local-dev.md`
- Test: `tests/integration/test_doctor_cli.py`

**Step 1: Write the failing CLI tests**

```python
import json
import subprocess
import sys
from pathlib import Path


def test_doctor_cli_returns_json_summary(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    completed = subprocess.run(
        [sys.executable, "-m", "video_agent.doctor.main", "--data-dir", str(data_dir), "--json"],
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert "checks" in payload
    assert "storage" in payload
    assert completed.returncode in {0, 1}
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_doctor_cli.py -q`
Expected: FAIL because the module and console script do not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/doctor/main.py`:
- Parse `--data-dir`, `--json`, and optional `--strict-provider`
- Reuse `build_settings(...)` from `src/video_agent/server/main.py`
- Call `RuntimeService.inspect()`
- Exit `0` when required checks pass, else `1`
- Print either compact JSON or a readable text summary

In `pyproject.toml` add:
- `easy-manim-doctor = "video_agent.doctor.main:main"`

In `.env.example` and `docs/runbooks/local-dev.md` document:
- `easy-manim-doctor --json`
- how provider checks behave in `stub` vs `openai_compatible` mode

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_doctor_cli.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/doctor/main.py src/video_agent/server/main.py pyproject.toml README.md .env.example docs/runbooks/local-dev.md tests/integration/test_doctor_cli.py
git commit -m "feat: add operator doctor cli"
```

---

## Week 2 - Worker visibility and admission control

### Task 3: Persist worker heartbeats and expose worker status

**Files:**
- Modify: `src/video_agent/adapters/storage/schema.sql`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/worker/worker_loop.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `tests/unit/test_settings.py`
- Test: `tests/integration/test_worker_status.py`

**Step 1: Write the failing integration test**

```python
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context
from video_agent.server.mcp_tools import get_runtime_status_tool


def test_runtime_status_includes_recent_worker_heartbeat(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data", run_embedded_worker=False)
    context = create_app_context(settings)

    processed = context.worker.run_once()
    payload = get_runtime_status_tool(context, {})

    assert processed == 0
    assert payload["worker"]["workers"]
    assert payload["worker"]["workers"][0]["stale"] is False
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_worker_status.py -q`
Expected: FAIL because worker heartbeats are not persisted.

**Step 3: Write minimal implementation**

In `src/video_agent/adapters/storage/schema.sql` add:

```sql
CREATE TABLE IF NOT EXISTS worker_heartbeats (
    worker_id TEXT PRIMARY KEY,
    last_seen_at TEXT NOT NULL,
    details_json TEXT NOT NULL
);
```

In `src/video_agent/adapters/storage/sqlite_store.py` add:
- `record_worker_heartbeat(worker_id: str, details: dict[str, Any]) -> None`
- `list_worker_heartbeats() -> list[dict[str, Any]]`

In `src/video_agent/config.py` add:
- `worker_stale_after_seconds: int = 30`

In `src/video_agent/worker/worker_loop.py`:
- record a heartbeat before attempting work and after finishing work
- include `last_processed_task_id` and `processed_count` in `details`

In `src/video_agent/application/runtime_service.py`:
- include worker heartbeat rows
- compute `stale` by comparing `last_seen_at` to `worker_stale_after_seconds`

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_settings.py tests/integration/test_worker_status.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/adapters/storage/schema.sql src/video_agent/adapters/storage/sqlite_store.py src/video_agent/config.py src/video_agent/server/main.py src/video_agent/worker/worker_loop.py src/video_agent/application/runtime_service.py tests/unit/test_settings.py tests/integration/test_worker_status.py
git commit -m "feat: expose worker heartbeat status"
```

### Task 4: Add queue guardrails and normalized admission failures

**Files:**
- Create: `src/video_agent/application/errors.py`
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/application/task_service.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/server/mcp_tools.py`
- Modify: `.env.example`
- Modify: `docs/runbooks/beta-ops.md`
- Modify: `tests/unit/test_settings.py`
- Test: `tests/integration/test_queue_backpressure.py`

**Step 1: Write the failing integration tests**

```python
import pytest

from video_agent.application.errors import AdmissionControlError
from video_agent.config import Settings
from video_agent.server.app import create_app_context


def test_create_video_task_rejects_when_queue_limit_reached(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path / "data", max_queued_tasks=1)
    context = create_app_context(settings)
    context.task_service.create_video_task(prompt="first")

    with pytest.raises(AdmissionControlError) as exc:
        context.task_service.create_video_task(prompt="second")

    assert exc.value.code == "queue_full"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_queue_backpressure.py -q`
Expected: FAIL because no admission control exists.

**Step 3: Write minimal implementation**

In `src/video_agent/application/errors.py` add:
- `AdmissionControlError(code: str, message: str)`

In `src/video_agent/config.py` add:
- `max_queued_tasks: int = 20`
- `max_attempts_per_root_task: int = 5`

In `src/video_agent/adapters/storage/sqlite_store.py` add:
- `count_tasks(statuses: list[str]) -> int`
- `count_lineage_tasks(root_task_id: str) -> int`

In `src/video_agent/application/task_service.py`:
- reject `create_video_task()` when queued/running/revising count reaches `max_queued_tasks`
- reject `retry_video_task()` when lineage count reaches `max_attempts_per_root_task`
- raise `AdmissionControlError(code="queue_full", ...)` or `AdmissionControlError(code="attempt_limit_reached", ...)`

In `src/video_agent/server/mcp_tools.py`:
- catch `AdmissionControlError` in create/retry tools and return

```python
{"error": {"code": exc.code, "message": str(exc)}}
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_settings.py tests/integration/test_queue_backpressure.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/errors.py src/video_agent/config.py src/video_agent/server/main.py src/video_agent/application/task_service.py src/video_agent/adapters/storage/sqlite_store.py src/video_agent/server/mcp_tools.py .env.example docs/runbooks/beta-ops.md tests/unit/test_settings.py tests/integration/test_queue_backpressure.py
git commit -m "feat: add beta queue admission guardrails"
```

---

## Week 3 - Cleanup and supportability

### Task 5: Add retention-aware cleanup service and dry-run CLI

**Files:**
- Create: `src/video_agent/application/cleanup_service.py`
- Create: `src/video_agent/cleanup/main.py`
- Modify: `src/video_agent/adapters/storage/sqlite_store.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/server/app.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/runbooks/beta-ops.md`
- Test: `tests/integration/test_cleanup_cli.py`

**Step 1: Write the failing integration test**

```python
import subprocess
import sys
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context


def test_cleanup_cli_dry_run_reports_old_completed_tasks(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data")
    context = create_app_context(settings)
    task = context.task_service.create_video_task(prompt="draw a circle")
    context.worker.run_once()

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.cleanup.main",
            "--data-dir",
            str(settings.data_dir),
            "--older-than-hours",
            "0",
            "--status",
            "completed",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert task.task_id in completed.stdout
    assert completed.returncode == 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_cleanup_cli.py -q`
Expected: FAIL because cleanup tooling does not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/application/cleanup_service.py` add:
- `CleanupCandidate`
- `CleanupSummary`
- `CleanupService.find_candidates(...)`
- `CleanupService.delete_candidates(...)`

In `src/video_agent/adapters/storage/sqlite_store.py` add:
- `list_cleanup_candidates(statuses: list[str], older_than_iso: str, limit: int) -> list[dict[str, Any]]`
- `delete_task(task_id: str) -> None` that deletes from `task_events`, `task_artifacts`, `task_validations`, `task_leases`, and `video_tasks`

In `src/video_agent/adapters/storage/artifact_store.py` add:
- `delete_task_dir(task_id: str) -> None`

In `src/video_agent/cleanup/main.py` add:
- flags: `--data-dir`, `--older-than-hours`, `--status`, `--limit`, `--dry-run`, `--json`
- dry-run default should print candidates only; destructive mode should require `--confirm`

In `pyproject.toml` add:
- `easy-manim-cleanup = "video_agent.cleanup.main:main"`

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_cleanup_cli.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/cleanup_service.py src/video_agent/cleanup/main.py src/video_agent/adapters/storage/sqlite_store.py src/video_agent/adapters/storage/artifact_store.py src/video_agent/server/app.py pyproject.toml README.md docs/runbooks/beta-ops.md tests/integration/test_cleanup_cli.py
git commit -m "feat: add cleanup cli for retained tasks"
```

### Task 6: Add task export bundle CLI for support handoff

**Files:**
- Create: `src/video_agent/application/export_service.py`
- Create: `src/video_agent/export/main.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `pyproject.toml`
- Modify: `docs/runbooks/beta-ops.md`
- Test: `tests/integration/test_export_cli.py`

**Step 1: Write the failing integration test**

```python
import subprocess
import sys
import zipfile
from pathlib import Path

from video_agent.config import Settings
from video_agent.server.app import create_app_context


def test_export_cli_writes_bundle_zip(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path / "data")
    context = create_app_context(settings)
    created = context.task_service.create_video_task(prompt="draw a square")
    context.worker.run_once()
    bundle_path = tmp_path / "bundle.zip"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.export.main",
            "--data-dir",
            str(settings.data_dir),
            "--task-id",
            created.task_id,
            "--output",
            str(bundle_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    with zipfile.ZipFile(bundle_path) as bundle:
        assert "task.json" in bundle.namelist()
        assert "logs/events.jsonl" in bundle.namelist()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_export_cli.py -q`
Expected: FAIL because no export tooling exists.

**Step 3: Write minimal implementation**

In `src/video_agent/application/export_service.py` add:
- `TaskExportService.export_bundle(task_id: str, output_path: Path) -> Path`

Behavior:
- copy task-local files under a stable ZIP layout:
  - `task.json`
  - `logs/events.jsonl`
  - `validations/...`
  - `artifacts/current_script.py`
  - `artifacts/previews/...`
  - `artifacts/final_video.mp4` when present
- fail with a clear message when the task directory does not exist

In `src/video_agent/export/main.py` add:
- flags: `--data-dir`, `--task-id`, `--output`

In `pyproject.toml` add:
- `easy-manim-export-task = "video_agent.export.main:main"`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_export_cli.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/export_service.py src/video_agent/export/main.py src/video_agent/adapters/storage/artifact_store.py pyproject.toml docs/runbooks/beta-ops.md tests/integration/test_export_cli.py
git commit -m "feat: add task export bundle cli"
```

---

## Week 4 - Beta acceptance automation and release gate

### Task 7: Extract the HTTP beta smoke flow into a reusable script and CI step

**Files:**
- Create: `scripts/beta_smoke.py`
- Modify: `tests/e2e/test_streamable_http_single_task_flow.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `docker-compose.yml`
- Test: `tests/e2e/test_streamable_http_single_task_flow.py`

**Step 1: Write the failing smoke-oriented test**

Refactor the existing HTTP E2E test so the process-launch and client-flow logic live in `scripts/beta_smoke.py`, then add a focused test that imports and calls the shared helper.

```python
from pathlib import Path

from scripts.beta_smoke import run_beta_smoke


def test_streamable_http_single_task_flow(tmp_path: Path) -> None:
    summary = run_beta_smoke(tmp_path)
    assert summary["snapshot"]["status"] == "completed"
    assert summary["result"]["ready"] is True
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/e2e/test_streamable_http_single_task_flow.py -q`
Expected: FAIL because the helper module does not exist yet.

**Step 3: Write minimal implementation**

In `scripts/beta_smoke.py`:
- move the following helpers out of the test file:
  - free-port selection
  - fake binary generation
  - subprocess server/worker lifecycle
  - async MCP client flow
- expose:

```python
def run_beta_smoke(tmp_path: Path) -> dict[str, object]:
    ...
```

In `.github/workflows/ci.yml` add a second verification line after pytest:
- `python scripts/beta_smoke.py --mode ci`

In `docker-compose.yml` add optional comments or profiles only if needed to document the smoke topology; avoid changing the default behavior.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/e2e/test_streamable_http_single_task_flow.py -q`
Expected: PASS

Then run:

Run: `python scripts/beta_smoke.py --mode ci`
Expected: PASS with a summary showing one completed task.

**Step 5: Commit**

```bash
git add scripts/beta_smoke.py tests/e2e/test_streamable_http_single_task_flow.py .github/workflows/ci.yml docker-compose.yml
git commit -m "test: add reusable beta smoke harness"
```

### Task 8: Finalize release runbooks and capture the Phase 3 release gate

**Files:**
- Modify: `README.md`
- Modify: `docs/runbooks/local-dev.md`
- Modify: `docs/runbooks/beta-ops.md`
- Modify: `docs/runbooks/release-checklist.md`
- Create: `docs/runbooks/incident-response.md`
- Test: `tests/e2e/test_streamable_http_single_task_flow.py`

**Step 1: Write the documentation checklist before editing**

Create a checklist in the PR or task description that explicitly covers:
- doctor flow
- runtime status MCP tool
- worker heartbeat interpretation
- queue-full / attempt-limit failures
- cleanup CLI dry-run and destructive modes
- export bundle CLI
- beta smoke command
- rollback / incident triage steps

**Step 2: Verify the checklist is not fully covered yet**

Run: `rg -n "doctor|runtime status|cleanup|export-task|incident" README.md docs/runbooks`
Expected: Missing or incomplete references for the new Phase 3 surfaces.

**Step 3: Write the minimal docs**

Update the docs so a beta operator can do the following without reading source code:
- confirm environment readiness
- inspect runtime status from MCP
- identify stale/missing workers
- recover from queue pressure or retry limits
- clean old data safely
- export a failed task bundle for support
- run the full beta smoke path before release
- follow first-response incident steps

In `docs/runbooks/incident-response.md` include:
- symptom
- likely cause
- first checks
- exact commands
- escalation boundary

**Step 4: Run final verification**

Run: `source .venv/bin/activate && python -m pytest -q`
Expected: PASS

Run: `python scripts/beta_smoke.py --mode ci`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md docs/runbooks/local-dev.md docs/runbooks/beta-ops.md docs/runbooks/release-checklist.md docs/runbooks/incident-response.md
git commit -m "docs: finalize beta release gate runbooks"
```

---

## Final Verification Gate

Before calling Phase 3 complete, run all of the following fresh in the worktree:

```bash
source .venv/bin/activate
python -m pytest -q
python scripts/beta_smoke.py --mode ci
docker build -t easy-manim-phase3 .
docker run --rm easy-manim-phase3 easy-manim-doctor --json
docker run --rm easy-manim-phase3 easy-manim-mcp --help
docker run --rm easy-manim-phase3 easy-manim-worker --help
docker run --rm easy-manim-phase3 easy-manim-cleanup --help
docker run --rm easy-manim-phase3 easy-manim-export-task --help
```

Expected outcome:
- pytest is green
- smoke script completes one happy-path task
- doctor exits `0` in stub mode
- all CLI entrypoints resolve in the container

## Suggested Commit Cadence
- 2 commits in Week 1
- 2 commits in Week 2
- 2 commits in Week 3
- 2 commits in Week 4
- optional final `chore: run phase 3 release gate` commit only if documentation or scripts changed during final verification
