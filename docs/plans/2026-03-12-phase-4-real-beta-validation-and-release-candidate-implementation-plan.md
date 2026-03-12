# Phase 4 Real Beta Validation and Release Candidate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the hardened local beta into an evidence-backed release candidate with curated prompt evaluation, reviewer-ready QA bundles, release metadata, and a repeatable promotion gate for real-provider trials.

**Architecture:** Reuse the existing task, worker, artifact, and beta smoke pipeline as the execution substrate. Add a thin evaluation layer that runs curated prompt suites through the existing app context, writes structured run summaries and QA bundles under dedicated evaluation directories, and promotes builds only when deterministic local gates pass and a documented real-provider trial has been completed.

**Tech Stack:** Python 3.13, Pydantic, FastMCP, SQLite, pytest, Docker, standard-library `statistics`, `zipfile`, `subprocess`, `argparse`, and JSON/Markdown artifacts.

---

## Assumptions and Non-Goals
- This phase is about **evidence, repeatability, and release confidence**, not about adding end-user product features.
- Stay on the current SQLite + local-filesystem architecture.
- Keep real-provider execution **out of CI**; automated checks must remain deterministic.
- Do **not** introduce a web dashboard, distributed workers, or hosted storage in this phase.

## Weekly Outcomes
- **Week 1:** A curated prompt suite can be loaded, filtered, and executed as a deterministic evaluation run.
- **Week 2:** Each evaluation run produces machine-readable summaries, Markdown reviewer reports, and a QA bundle for human inspection.
- **Week 3:** The runtime surfaces release metadata clearly, and beta operators have an RC-specific configuration and runbook.
- **Week 4:** A single release-candidate gate script combines tests, smoke, eval thresholds, and documented real-provider signoff.

---

## Week 1 - Curated prompt evaluation foundation

### Task 1: Add prompt suite schema and loader

**Files:**
- Create: `src/video_agent/evaluation/__init__.py`
- Create: `src/video_agent/evaluation/models.py`
- Create: `src/video_agent/evaluation/corpus.py`
- Create: `evals/beta_prompt_suite.json`
- Test: `tests/unit/evaluation/test_corpus.py`

**Step 1: Write the failing unit tests**

```python
from pathlib import Path

from video_agent.evaluation.corpus import load_prompt_suite


def test_load_prompt_suite_returns_cases() -> None:
    suite = load_prompt_suite(Path("evals/beta_prompt_suite.json"))

    assert suite.suite_id == "beta-prompt-suite"
    assert len(suite.cases) >= 3
    assert {case.case_id for case in suite.cases}


def test_load_prompt_suite_can_filter_by_tag(tmp_path: Path) -> None:
    fixture = tmp_path / "suite.json"
    fixture.write_text(
        '{"suite_id":"demo","cases":['
        '{"case_id":"a","prompt":"draw a circle","tags":["smoke"]},'
        '{"case_id":"b","prompt":"draw a square","tags":["real-provider"]}'
        ']}'
    )

    suite = load_prompt_suite(fixture, include_tags={"smoke"})

    assert [case.case_id for case in suite.cases] == ["a"]
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/evaluation/test_corpus.py -q`
Expected: FAIL because the evaluation module and prompt suite do not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/evaluation/models.py` add:
- `PromptCase`
- `PromptSuite`

Minimal schema:

```python
class PromptCase(BaseModel):
    case_id: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
```

In `src/video_agent/evaluation/corpus.py` add:
- `load_prompt_suite(path: Path, include_tags: set[str] | None = None) -> PromptSuite`
- validate unique `case_id` values
- filter cases when `include_tags` is provided

In `evals/beta_prompt_suite.json` add a small initial suite with tagged cases such as:
- `smoke`
- `core-shapes`
- `real-provider`

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/evaluation/test_corpus.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/evaluation/__init__.py src/video_agent/evaluation/models.py src/video_agent/evaluation/corpus.py evals/beta_prompt_suite.json tests/unit/evaluation/test_corpus.py
git commit -m "feat: add curated beta prompt suite loader"
```

### Task 2: Add deterministic evaluation runner service and CLI

**Files:**
- Create: `src/video_agent/application/eval_service.py`
- Create: `src/video_agent/eval/__init__.py`
- Create: `src/video_agent/eval/main.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/config.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `pyproject.toml`
- Test: `tests/integration/test_eval_run_cli.py`

**Step 1: Write the failing integration test**

```python
import json
import subprocess
import sys
from pathlib import Path


def test_eval_run_cli_writes_summary_json(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            "evals/beta_prompt_suite.json",
            "--include-tag",
            "smoke",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(completed.stdout)
    assert payload["suite_id"] == "beta-prompt-suite"
    assert payload["total_cases"] >= 1
    assert completed.returncode == 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_eval_run_cli.py -q`
Expected: FAIL because the runner CLI does not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/config.py` add:
- `eval_root: Path | None = None`
- derive default `data/evals`

In `src/video_agent/adapters/storage/artifact_store.py` add:
- `eval_run_dir(run_id: str) -> Path`
- `write_eval_summary(run_id: str, payload: dict[str, Any]) -> Path`

In `src/video_agent/application/eval_service.py` add:
- `EvaluationCaseResult`
- `EvaluationRunSummary`
- `EvaluationService.run_suite(...)`

Implementation notes:
- reuse existing `create_app_context(settings)` and `worker.run_once()` loop
- for each case: create a task, wait until terminal status, snapshot the result
- emit `summary.json` under `data/evals/<run_id>/summary.json`
- include `suite_id`, `run_id`, `provider`, `total_cases`, and `items`

In `src/video_agent/eval/main.py` add:
- flags: `--data-dir`, `--suite`, `--include-tag`, `--limit`, `--json`
- console script: `easy-manim-eval-run = "video_agent.eval.main:main"`

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_eval_run_cli.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/eval_service.py src/video_agent/eval/__init__.py src/video_agent/eval/main.py src/video_agent/adapters/storage/artifact_store.py src/video_agent/config.py src/video_agent/server/main.py pyproject.toml tests/integration/test_eval_run_cli.py
git commit -m "feat: add deterministic evaluation runner cli"
```

---

## Week 2 - Reports and reviewer handoff

### Task 3: Add aggregate eval reporting and thresholds

**Files:**
- Create: `src/video_agent/evaluation/reporting.py`
- Modify: `src/video_agent/application/eval_service.py`
- Test: `tests/unit/evaluation/test_reporting.py`

**Step 1: Write the failing unit tests**

```python
from video_agent.evaluation.reporting import build_eval_report


def test_build_eval_report_computes_success_rate_and_failures() -> None:
    report = build_eval_report(
        [
            {"status": "completed", "duration_seconds": 3.0, "issues": []},
            {"status": "failed", "duration_seconds": 5.0, "issues": ["generation_failed"]},
        ]
    )

    assert report["success_rate"] == 0.5
    assert report["failure_codes"]["generation_failed"] == 1
    assert report["median_duration_seconds"] == 4.0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/evaluation/test_reporting.py -q`
Expected: FAIL because reporting helpers do not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/evaluation/reporting.py` add:
- `build_eval_report(items: list[dict[str, Any]]) -> dict[str, Any]`
- `render_eval_report_markdown(summary: dict[str, Any]) -> str`

Implementation details:
- compute:
  - `completed_count`
  - `failed_count`
  - `success_rate`
  - `failure_codes`
  - `median_duration_seconds`
- keep percentile math simple; only add `p95` if at least 20 items exist

In `src/video_agent/application/eval_service.py`:
- call the reporting helpers
- write `summary.md` next to `summary.json`

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/evaluation/test_reporting.py tests/integration/test_eval_run_cli.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/evaluation/reporting.py src/video_agent/application/eval_service.py tests/unit/evaluation/test_reporting.py
git commit -m "feat: add aggregate evaluation reporting"
```

### Task 4: Add QA bundle export for evaluation runs

**Files:**
- Create: `src/video_agent/application/qa_bundle_service.py`
- Create: `src/video_agent/qa_bundle/__init__.py`
- Create: `src/video_agent/qa_bundle/main.py`
- Modify: `pyproject.toml`
- Test: `tests/integration/test_qa_bundle_cli.py`

**Step 1: Write the failing integration test**

```python
import json
import subprocess
import sys
import zipfile
from pathlib import Path


def test_qa_bundle_cli_exports_eval_bundle(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    eval_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.eval.main",
            "--data-dir",
            str(data_dir),
            "--suite",
            "evals/beta_prompt_suite.json",
            "--include-tag",
            "smoke",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    run_id = json.loads(eval_run.stdout)["run_id"]
    bundle_path = tmp_path / "qa-bundle.zip"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "video_agent.qa_bundle.main",
            "--data-dir",
            str(data_dir),
            "--run-id",
            run_id,
            "--output",
            str(bundle_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    with zipfile.ZipFile(bundle_path) as bundle:
        assert "summary.json" in bundle.namelist()
        assert "summary.md" in bundle.namelist()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_qa_bundle_cli.py -q`
Expected: FAIL because QA bundle tooling does not exist.

**Step 3: Write minimal implementation**

In `src/video_agent/application/qa_bundle_service.py` add:
- `QABundleService.export_run_bundle(run_id: str, output_path: Path) -> Path`

Bundle contents:
- `summary.json`
- `summary.md`
- `tasks/<task_id>/task.json`
- `tasks/<task_id>/logs/events.jsonl`
- `tasks/<task_id>/validations/validation_report_v1.json`
- selected artifacts when present

In `src/video_agent/qa_bundle/main.py` add:
- flags: `--data-dir`, `--run-id`, `--output`
- console script: `easy-manim-qa-bundle = "video_agent.qa_bundle.main:main"`

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/integration/test_eval_run_cli.py tests/integration/test_qa_bundle_cli.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/application/qa_bundle_service.py src/video_agent/qa_bundle/__init__.py src/video_agent/qa_bundle/main.py pyproject.toml tests/integration/test_qa_bundle_cli.py
git commit -m "feat: add qa bundle export for evaluation runs"
```

---

## Week 3 - Release metadata and operator surface

### Task 5: Add release metadata to runtime status and CLI entrypoints

**Files:**
- Create: `src/video_agent/version.py`
- Modify: `src/video_agent/application/runtime_service.py`
- Modify: `src/video_agent/doctor/main.py`
- Modify: `src/video_agent/server/main.py`
- Modify: `src/video_agent/config.py`
- Modify: `tests/integration/test_runtime_status_tool.py`
- Modify: `tests/integration/test_cli_entrypoints.py`
- Test: `tests/unit/test_version.py`

**Step 1: Write the failing tests**

```python
from video_agent.version import get_release_metadata


def test_get_release_metadata_exposes_version_and_channel() -> None:
    metadata = get_release_metadata()

    assert metadata["version"]
    assert metadata["channel"] in {"beta", "rc", "stable"}
```

Add one integration assertion that `get_runtime_status` now returns a `release` section.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_version.py tests/integration/test_runtime_status_tool.py tests/integration/test_cli_entrypoints.py -q`
Expected: FAIL because release metadata is not surfaced.

**Step 3: Write minimal implementation**

In `src/video_agent/version.py` add:
- `get_release_metadata() -> dict[str, str]`
- derive package version via `importlib.metadata.version("easy-manim")`
- read `EASY_MANIM_RELEASE_CHANNEL`, default `beta`

In `src/video_agent/application/runtime_service.py`:
- add `release` payload with `version` and `channel`

In `src/video_agent/server/main.py` and `src/video_agent/doctor/main.py`:
- add `--version` handling via `argparse` `action="version"`

In `src/video_agent/config.py` add:
- `release_channel: str = "beta"`

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_version.py tests/integration/test_runtime_status_tool.py tests/integration/test_cli_entrypoints.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/version.py src/video_agent/application/runtime_service.py src/video_agent/doctor/main.py src/video_agent/server/main.py src/video_agent/config.py tests/unit/test_version.py tests/integration/test_runtime_status_tool.py tests/integration/test_cli_entrypoints.py
git commit -m "feat: surface release metadata in runtime diagnostics"
```

### Task 6: Add RC environment template and release candidate gate script

**Files:**
- Create: `.env.beta.example`
- Create: `scripts/release_candidate_gate.py`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/e2e/test_release_candidate_gate.py`

**Step 1: Write the failing e2e-style test**

```python
from scripts.release_candidate_gate import evaluate_gate_result


def test_evaluate_gate_result_fails_when_pass_rate_is_too_low() -> None:
    result = evaluate_gate_result(
        {
            "eval": {"success_rate": 0.4},
            "smoke": {"status": "passed"},
            "tests": {"status": "passed"},
        },
        min_pass_rate=0.8,
    )

    assert result["ok"] is False
    assert "success_rate" in result["reasons"][0]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/e2e/test_release_candidate_gate.py -q`
Expected: FAIL because the gate script does not exist.

**Step 3: Write minimal implementation**

In `.env.beta.example` add:
- provider placeholders
- release channel example
- queue/worker defaults for beta trial hosts

In `scripts/release_candidate_gate.py` add:
- `evaluate_gate_result(payload: dict[str, Any], min_pass_rate: float) -> dict[str, Any]`
- `main()` that runs:
  - `easy-manim-doctor --json`
  - `python -m pytest -q`
  - `python scripts/beta_smoke.py --mode ci`
  - `easy-manim-eval-run --suite evals/beta_prompt_suite.json --include-tag smoke --json`
- fail when tests or smoke fail, or when eval pass rate is below threshold
- emit a single JSON summary to stdout

In `.github/workflows/ci.yml` add a release-gate step after the regular test step.

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/e2e/test_release_candidate_gate.py -q`
Expected: PASS

Then run:

Run: `source .venv/bin/activate && python scripts/release_candidate_gate.py --mode ci`
Expected: PASS with a JSON summary and `ok: true`

**Step 5: Commit**

```bash
git add .env.beta.example scripts/release_candidate_gate.py .github/workflows/ci.yml tests/e2e/test_release_candidate_gate.py
git commit -m "test: add release candidate gate"
```

---

## Week 4 - Real-provider trial and promotion package

### Task 7: Finalize real-provider trial runbook and RC decision template

**Files:**
- Create: `docs/runbooks/real-provider-trial.md`
- Create: `docs/templates/release-candidate-decision.md`
- Modify: `README.md`
- Modify: `docs/runbooks/beta-ops.md`
- Modify: `docs/runbooks/release-checklist.md`
- Test: `tests/e2e/test_release_candidate_gate.py`

**Step 1: Write the documentation checklist before editing**

Create a checklist covering:
- how to choose the real-provider subset from `evals/beta_prompt_suite.json`
- which env file to copy for RC trials
- how to run `easy-manim-eval-run` with `real-provider` tags
- where to find `summary.json`, `summary.md`, and the QA bundle
- how to record a go/no-go decision
- what evidence is required to promote from beta to RC

**Step 2: Verify the docs are incomplete today**

Run: `rg -n "real-provider|release candidate|qa bundle|easy-manim-eval-run|release-candidate-gate" README.md docs/runbooks docs/templates`
Expected: Missing or incomplete references before this task is implemented.

**Step 3: Write the minimal docs**

In `docs/runbooks/real-provider-trial.md` document:
- exact setup commands
- exact `easy-manim-eval-run` command for `real-provider` tagged prompts
- required artifacts to collect
- operator notes to record during review

In `docs/templates/release-candidate-decision.md` include:
- build identifier
- suite used
- pass rate
- top failure codes
- reviewer names
- release decision

Update `README.md`, `docs/runbooks/beta-ops.md`, and `docs/runbooks/release-checklist.md` so the RC path is discoverable without reading source code.

**Step 4: Run final verification**

Run: `source .venv/bin/activate && python -m pytest -q`
Expected: PASS

Run: `source .venv/bin/activate && python scripts/release_candidate_gate.py --mode ci`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md docs/runbooks/beta-ops.md docs/runbooks/release-checklist.md docs/runbooks/real-provider-trial.md docs/templates/release-candidate-decision.md
git commit -m "docs: finalize real-provider trial and rc decision package"
```

---

## Final Verification Gate

Before calling Phase 4 complete, run all of the following fresh in the worktree:

```bash
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/beta_smoke.py --mode ci
python scripts/release_candidate_gate.py --mode ci
docker build -t easy-manim-phase4 .
docker run --rm easy-manim-phase4 easy-manim-doctor --json
docker run --rm easy-manim-phase4 easy-manim-eval-run --help
docker run --rm easy-manim-phase4 easy-manim-qa-bundle --help
```

Manual release-candidate evidence, outside CI:

```bash
source .venv/bin/activate
cp .env.beta.example .env.beta
EASY_MANIM_LLM_PROVIDER=openai_compatible easy-manim-eval-run --suite evals/beta_prompt_suite.json --include-tag real-provider --json
```

Expected outcome:
- deterministic test, smoke, and RC gate checks are green
- evaluation summary and Markdown report exist under `data/evals/<run_id>/`
- QA bundle exports successfully for at least one run
- manual real-provider trial results are captured in the RC decision template

## Suggested Commit Cadence
- 2 commits in Week 1
- 2 commits in Week 2
- 2 commits in Week 3
- 1 commit in Week 4
- optional final `chore: run phase 4 release candidate gate` commit only if verification artifacts or docs changed during signoff
