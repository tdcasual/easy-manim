# Phase 6 Live Provider Stability and Quality Convergence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the current beta-ready, repair-capable pipeline into a repeatable live-provider promotion workflow with explicit live-case metadata, failure clustering, reviewer-ready digests, and a manual live gate that catches regressions before release decisions.

**Architecture:** Keep the current `eval -> summary.json/summary.md -> qa bundle -> release decision` flow. Extend the prompt-suite schema so curated live cases carry risk-domain and review metadata, propagate that metadata through `EvaluationService`, compute a dedicated `report.live` section plus reviewer-friendly digest artifacts, and add a separate manual live gate script that evaluates a real-provider run against thresholds and an optional prior baseline summary. Keep the deterministic `release_candidate_gate.py` unchanged except for documentation references; the new gate consumes already-produced live eval artifacts.

**Tech Stack:** Python 3.13, Pydantic, pytest, argparse, JSON, Markdown, existing evaluation / QA bundle services, and the current local filesystem artifact model.

---

**Execution notes**
- Follow `@superpowers:test-driven-development` on every task.
- Run `@superpowers:verification-before-completion` before claiming any task is done.
- Request `@superpowers:requesting-code-review` after the full phase is implemented.

### Task 1: Extend prompt-suite metadata for live-provider baselines

**Files:**
- Modify: `src/video_agent/evaluation/models.py`
- Modify: `src/video_agent/evaluation/corpus.py`
- Modify: `evals/beta_prompt_suite.json`
- Modify: `evals/beta_long_tail_regressions.json`
- Test: `tests/unit/evaluation/test_corpus.py`

**Step 1: Write the failing unit tests**

Add cases that prove the suite loader preserves live-review metadata:

```python
from pathlib import Path

from video_agent.evaluation.corpus import load_prompt_suite


def test_load_prompt_suite_preserves_live_case_metadata(tmp_path: Path) -> None:
    fixture = tmp_path / "suite.json"
    fixture.write_text(
        """
        {
          "suite_id": "live-demo",
          "cases": [
            {
              "case_id": "formula-live",
              "prompt": "show the quadratic formula",
              "tags": ["real-provider", "quality", "mathtex"],
              "risk_domains": ["formula", "layout"],
              "review_focus": ["formula legibility", "term emphasis"],
              "baseline_group": "live-rc-core",
              "manual_review_required": true
            }
          ]
        }
        """
    )

    suite = load_prompt_suite(fixture)

    case = suite.cases[0]
    assert case.risk_domains == ["formula", "layout"]
    assert case.review_focus == ["formula legibility", "term emphasis"]
    assert case.baseline_group == "live-rc-core"
    assert case.manual_review_required is True


def test_load_prompt_suite_rejects_unknown_risk_domains(tmp_path: Path) -> None:
    fixture = tmp_path / "suite.json"
    fixture.write_text(
        """
        {
          "suite_id": "live-demo",
          "cases": [
            {
              "case_id": "bad-risk",
              "prompt": "draw a circle",
              "tags": ["real-provider"],
              "risk_domains": ["made-up-domain"]
            }
          ]
        }
        """
    )

    with pytest.raises(ValueError, match="unknown risk_domains"):
        load_prompt_suite(fixture)
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/unit/evaluation/test_corpus.py -q`

Expected: FAIL because `PromptCase` does not yet expose or validate the new metadata fields.

**Step 3: Write minimal implementation**

In `src/video_agent/evaluation/models.py` extend `PromptCase`:

```python
LIVE_RISK_DOMAINS = {
    "formula",
    "layout",
    "camera",
    "motion",
    "labels",
    "annotation",
    "geometry",
    "graph",
    "provider",
}


class PromptCase(BaseModel):
    case_id: str
    prompt: str
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    risk_domains: list[str] = Field(default_factory=list)
    review_focus: list[str] = Field(default_factory=list)
    baseline_group: str | None = None
    manual_review_required: bool = False

    @field_validator("risk_domains")
    @classmethod
    def validate_risk_domains(cls, value: list[str]) -> list[str]:
        unknown = [item for item in value if item not in LIVE_RISK_DOMAINS]
        if unknown:
            raise ValueError(f"unknown risk_domains: {', '.join(sorted(unknown))}")
        return value
```

Update the curated JSON suites so every `real-provider` case has:
- at least one `risk_domains` entry
- at least one `review_focus` item
- a `baseline_group` such as `live-rc-core` or `live-long-tail`
- `manual_review_required: true`

Keep deterministic `smoke` and `repair` cases minimal; only add the new metadata where it adds value.

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/unit/evaluation/test_corpus.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/evaluation/models.py src/video_agent/evaluation/corpus.py evals/beta_prompt_suite.json evals/beta_long_tail_regressions.json tests/unit/evaluation/test_corpus.py
git commit -m "feat: add live-provider suite metadata"
```

### Task 2: Add live failure clustering and baseline metrics to eval summaries

**Files:**
- Create: `src/video_agent/evaluation/live_reporting.py`
- Modify: `src/video_agent/application/eval_service.py`
- Modify: `src/video_agent/evaluation/reporting.py`
- Test: `tests/unit/evaluation/test_live_reporting.py`
- Modify: `tests/integration/test_eval_run_cli.py`

**Step 1: Write the failing unit tests**

Add a report-level test:

```python
from video_agent.evaluation.live_reporting import build_live_report


def test_build_live_report_groups_failures_by_risk_domain() -> None:
    report = build_live_report(
        [
            {
                "case_id": "formula-case",
                "tags": ["real-provider", "quality"],
                "status": "failed",
                "risk_domains": ["formula", "layout"],
                "quality_issue_codes": ["static_previews"],
                "issue_codes": ["unsafe_transformmatchingtex_slice"],
            },
            {
                "case_id": "camera-case",
                "tags": ["real-provider", "quality"],
                "status": "completed",
                "risk_domains": ["camera"],
                "quality_issue_codes": [],
                "issue_codes": [],
            },
        ]
    )

    assert report["case_count"] == 2
    assert report["pass_rate"] == 0.5
    assert report["risk_domain_counts"]["formula"] == 1
    assert report["risk_domain_failure_counts"]["formula"] == 1
    assert report["formula_pass_rate"] == 0.0
    assert report["top_failing_cases"] == ["formula-case"]
```

Add an integration assertion in `tests/integration/test_eval_run_cli.py`:

```python
assert payload["report"]["live"]["case_count"] >= 1
assert "risk_domain_counts" in payload["report"]["live"]
assert "formula_pass_rate" in payload["report"]["live"]
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/unit/evaluation/test_live_reporting.py tests/integration/test_eval_run_cli.py -q`

Expected: FAIL because `report.live` does not exist.

**Step 3: Write minimal implementation**

Create `src/video_agent/evaluation/live_reporting.py`:

```python
from __future__ import annotations

from collections import Counter
from typing import Any


def build_live_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    live_items = [item for item in items if "real-provider" in (item.get("tags") or [])]
    domain_counts = Counter(domain for item in live_items for domain in item.get("risk_domains", []))
    domain_failures = Counter(
        domain
        for item in live_items
        if item.get("status") != "completed"
        for domain in item.get("risk_domains", [])
    )
    formula_items = [item for item in live_items if "formula" in (item.get("risk_domains") or [])]
    failed_cases = [item["case_id"] for item in live_items if item.get("status") != "completed"]
    total = len(live_items)
    completed = sum(1 for item in live_items if item.get("status") == "completed")
    formula_completed = sum(1 for item in formula_items if item.get("status") == "completed")
    return {
        "case_count": total,
        "pass_rate": (completed / total) if total else 0.0,
        "risk_domain_counts": dict(domain_counts),
        "risk_domain_failure_counts": dict(domain_failures),
        "formula_pass_rate": (formula_completed / len(formula_items)) if formula_items else 0.0,
        "top_failing_cases": failed_cases[:5],
    }
```

In `src/video_agent/application/eval_service.py` propagate new `PromptCase` metadata into each `EvaluationCaseResult`:

```python
class EvaluationCaseResult(BaseModel):
    ...
    risk_domains: list[str] = Field(default_factory=list)
    review_focus: list[str] = Field(default_factory=list)
    baseline_group: str | None = None
    manual_review_required: bool = False
```

Populate those fields from `case`.

Then append:

```python
from video_agent.evaluation.live_reporting import build_live_report
...
report["live"] = build_live_report(item_payloads)
```

In `src/video_agent/evaluation/reporting.py`, add a `## Live Slice` section to `render_eval_report_markdown` that prints:
- case count
- pass rate
- formula pass rate
- risk-domain failure counts

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/unit/evaluation/test_live_reporting.py tests/integration/test_eval_run_cli.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/evaluation/live_reporting.py src/video_agent/application/eval_service.py src/video_agent/evaluation/reporting.py tests/unit/evaluation/test_live_reporting.py tests/integration/test_eval_run_cli.py
git commit -m "feat: add live-provider eval reporting"
```

### Task 3: Generate a reviewer digest and include it in QA bundles

**Files:**
- Create: `src/video_agent/evaluation/reviewer_digest.py`
- Modify: `src/video_agent/adapters/storage/artifact_store.py`
- Modify: `src/video_agent/application/eval_service.py`
- Modify: `src/video_agent/application/qa_bundle_service.py`
- Create: `tests/unit/evaluation/test_reviewer_digest.py`
- Modify: `tests/integration/test_qa_bundle_cli.py`

**Step 1: Write the failing unit and integration tests**

Unit test:

```python
from video_agent.evaluation.reviewer_digest import render_reviewer_digest


def test_render_reviewer_digest_prioritizes_manual_review_failures() -> None:
    content = render_reviewer_digest(
        {
            "run_id": "run-123",
            "items": [
                {
                    "case_id": "formula-case",
                    "task_id": "task-1",
                    "status": "failed",
                    "manual_review_required": True,
                    "risk_domains": ["formula"],
                    "review_focus": ["formula legibility"],
                    "issue_codes": ["unsafe_transformmatchingtex_slice"],
                    "quality_issue_codes": ["static_previews"],
                },
                {
                    "case_id": "circle-case",
                    "task_id": "task-2",
                    "status": "completed",
                    "manual_review_required": False,
                    "risk_domains": ["geometry"],
                    "review_focus": [],
                    "issue_codes": [],
                    "quality_issue_codes": [],
                },
            ],
            "report": {"live": {"top_failing_cases": ["formula-case"]}},
        }
    )

    assert "formula-case" in content
    assert "Review First" in content
    assert "unsafe_transformmatchingtex_slice" in content
    assert "formula legibility" in content
```

Integration test in `tests/integration/test_qa_bundle_cli.py` should assert:

```python
assert "review_digest.md" in zip_names
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/unit/evaluation/test_reviewer_digest.py tests/integration/test_qa_bundle_cli.py -q`

Expected: FAIL because there is no reviewer digest artifact yet.

**Step 3: Write minimal implementation**

Create `src/video_agent/evaluation/reviewer_digest.py`:

```python
from __future__ import annotations

from typing import Any


def render_reviewer_digest(summary: dict[str, Any]) -> str:
    lines = [
        "# Reviewer Digest",
        "",
        f"- Run ID: `{summary['run_id']}`",
        "",
        "## Review First",
    ]
    items = sorted(
        summary.get("items", []),
        key=lambda item: (
            not item.get("manual_review_required", False),
            item.get("status") == "completed",
            item.get("case_id", ""),
        ),
    )
    review_first = False
    for item in items:
        if not item.get("manual_review_required") and item.get("status") == "completed":
            continue
        review_first = True
        lines.append(
            "- `{case_id}` (`{task_id}`): status={status}, risk_domains={risk_domains}, "
            "review_focus={review_focus}, issue_codes={issue_codes}, quality_issue_codes={quality_issue_codes}".format(
                case_id=item["case_id"],
                task_id=item["task_id"],
                status=item["status"],
                risk_domains=",".join(item.get("risk_domains", [])) or "none",
                review_focus=",".join(item.get("review_focus", [])) or "none",
                issue_codes=",".join(item.get("issue_codes", [])) or "none",
                quality_issue_codes=",".join(item.get("quality_issue_codes", [])) or "none",
            )
        )
    if not review_first:
        lines.append("- No priority review items")
    return "\n".join(lines) + "\n"
```

In `src/video_agent/adapters/storage/artifact_store.py` add:

```python
def write_eval_reviewer_digest(self, run_id: str, content: str) -> Path:
    target = self.eval_run_dir(run_id) / "review_digest.md"
    target.write_text(content)
    return target
```

In `src/video_agent/application/eval_service.py` render and write the digest after `summary.md`.

In `src/video_agent/application/qa_bundle_service.py` include `review_digest.md` when present; do not fail older runs that only have `summary.json` and `summary.md`.

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/unit/evaluation/test_reviewer_digest.py tests/integration/test_qa_bundle_cli.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add src/video_agent/evaluation/reviewer_digest.py src/video_agent/adapters/storage/artifact_store.py src/video_agent/application/eval_service.py src/video_agent/application/qa_bundle_service.py tests/unit/evaluation/test_reviewer_digest.py tests/integration/test_qa_bundle_cli.py
git commit -m "feat: add reviewer digest for live evals"
```

### Task 4: Add a manual live-provider promotion gate with optional baseline comparison

**Files:**
- Create: `scripts/live_provider_gate.py`
- Create: `tests/e2e/test_live_provider_gate.py`
- Modify: `docs/runbooks/real-provider-trial.md`
- Modify: `docs/runbooks/release-checklist.md`
- Modify: `README.md`

**Step 1: Write the failing e2e tests**

Create `tests/e2e/test_live_provider_gate.py`:

```python
import json
import subprocess
import sys
from pathlib import Path


def test_live_provider_gate_fails_on_formula_regression(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "report": {
                    "live": {
                        "case_count": 4,
                        "pass_rate": 0.75,
                        "formula_pass_rate": 0.0,
                        "risk_domain_failure_counts": {"formula": 2, "camera": 0},
                    }
                }
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/live_provider_gate.py",
            "--summary",
            str(summary),
            "--min-live-pass-rate",
            "0.75",
            "--min-formula-pass-rate",
            "0.5",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["ok"] is False
    assert any("formula_pass_rate" in reason for reason in payload["reasons"])


def test_live_provider_gate_detects_baseline_regression(tmp_path: Path) -> None:
    current = tmp_path / "current.json"
    baseline = tmp_path / "baseline.json"
    current.write_text(
        json.dumps(
            {
                "report": {
                    "live": {
                        "case_count": 4,
                        "pass_rate": 1.0,
                        "formula_pass_rate": 1.0,
                        "risk_domain_failure_counts": {"formula": 1, "camera": 1},
                    }
                }
            }
        )
    )
    baseline.write_text(
        json.dumps(
            {
                "report": {
                    "live": {
                        "risk_domain_failure_counts": {"formula": 0, "camera": 1}
                    }
                }
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/live_provider_gate.py",
            "--summary",
            str(current),
            "--baseline-summary",
            str(baseline),
            "--max-risk-regression",
            "0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert any("risk_domain formula regressed" in reason for reason in payload["reasons"])
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && python -m pytest tests/e2e/test_live_provider_gate.py -q`

Expected: FAIL because the script does not exist.

**Step 3: Write minimal implementation**

Create `scripts/live_provider_gate.py`:

```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def evaluate_live_gate(
    summary: dict,
    *,
    min_live_pass_rate: float,
    min_formula_pass_rate: float,
    max_risk_regression: int,
    baseline: dict | None = None,
) -> dict[str, object]:
    reasons: list[str] = []
    live = summary.get("report", {}).get("live", {})
    pass_rate = float(live.get("pass_rate", 0.0))
    formula_pass_rate = float(live.get("formula_pass_rate", 0.0))
    if pass_rate < min_live_pass_rate:
        reasons.append(f"live_pass_rate {pass_rate:.2f} below threshold {min_live_pass_rate:.2f}")
    if formula_pass_rate < min_formula_pass_rate:
        reasons.append(
            f"formula_pass_rate {formula_pass_rate:.2f} below threshold {min_formula_pass_rate:.2f}"
        )

    if baseline is not None:
        current_counts = live.get("risk_domain_failure_counts", {})
        baseline_counts = baseline.get("report", {}).get("live", {}).get("risk_domain_failure_counts", {})
        for domain, current_value in current_counts.items():
            previous_value = int(baseline_counts.get(domain, 0))
            if int(current_value) - previous_value > max_risk_regression:
                reasons.append(
                    f"risk_domain {domain} regressed from {previous_value} to {current_value}"
                )

    return {"ok": not reasons, "reasons": reasons}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a manual live-provider run")
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--baseline-summary", type=Path)
    parser.add_argument("--min-live-pass-rate", type=float, default=0.8)
    parser.add_argument("--min-formula-pass-rate", type=float, default=0.8)
    parser.add_argument("--max-risk-regression", type=int, default=0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = json.loads(args.summary.read_text())
    baseline = json.loads(args.baseline_summary.read_text()) if args.baseline_summary else None
    payload = evaluate_live_gate(
        summary,
        min_live_pass_rate=args.min_live_pass_rate,
        min_formula_pass_rate=args.min_formula_pass_rate,
        max_risk_regression=args.max_risk_regression,
        baseline=baseline,
    )
    print(json.dumps(payload))
    raise SystemExit(0 if payload["ok"] else 1)


if __name__ == "__main__":
    main()
```

Document the intended workflow:
- deterministic local gate stays `python scripts/release_candidate_gate.py --mode ci`
- real-provider gate becomes:
  - run `easy-manim-eval-run --include-tag real-provider --include-tag quality --match-all-tags --json`
  - feed `data/evals/<run_id>/summary.json` into `python scripts/live_provider_gate.py`
  - optionally compare against the previous approved live summary with `--baseline-summary`

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m pytest tests/e2e/test_live_provider_gate.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/live_provider_gate.py tests/e2e/test_live_provider_gate.py docs/runbooks/real-provider-trial.md docs/runbooks/release-checklist.md README.md
git commit -m "feat: add manual live-provider promotion gate"
```

### Task 5: Verify the full Phase 6 flow end-to-end

**Files:**
- Test: `tests/unit/evaluation/test_corpus.py`
- Test: `tests/unit/evaluation/test_live_reporting.py`
- Test: `tests/unit/evaluation/test_reviewer_digest.py`
- Test: `tests/integration/test_eval_run_cli.py`
- Test: `tests/integration/test_qa_bundle_cli.py`
- Test: `tests/e2e/test_live_provider_gate.py`

**Step 1: Run focused unit tests**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/unit/evaluation/test_corpus.py tests/unit/evaluation/test_live_reporting.py tests/unit/evaluation/test_reviewer_digest.py -q
```

Expected: PASS

**Step 2: Run focused integration tests**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/integration/test_eval_run_cli.py tests/integration/test_qa_bundle_cli.py -q
```

Expected: PASS

**Step 3: Run live-gate e2e tests**

Run:

```bash
source .venv/bin/activate
python -m pytest tests/e2e/test_live_provider_gate.py -q
```

Expected: PASS

**Step 4: Run the deterministic release gate to ensure no regression**

Run:

```bash
source .venv/bin/activate
python scripts/release_candidate_gate.py --mode ci
```

Expected: PASS; the Phase 6 additions should not break the deterministic RC flow.

**Step 5: Commit**

```bash
git add tests/unit/evaluation/test_corpus.py tests/unit/evaluation/test_live_reporting.py tests/unit/evaluation/test_reviewer_digest.py tests/integration/test_eval_run_cli.py tests/integration/test_qa_bundle_cli.py tests/e2e/test_live_provider_gate.py
git commit -m "test: verify phase 6 live-provider stability flow"
```

## Exit criteria

- `real-provider` cases carry explicit risk-domain and review metadata in the prompt suite
- `summary.json` includes `report.live` with pass-rate and risk-domain failure counts
- `summary.md` includes a readable `Live Slice` section
- each eval run writes `review_digest.md` for reviewer triage
- QA bundles include the reviewer digest when present
- a manual live-provider gate can validate a run against thresholds and optionally compare against the previous approved baseline

## Final verification sequence

```bash
source .venv/bin/activate
python -m pytest tests/unit/evaluation/test_corpus.py tests/unit/evaluation/test_live_reporting.py tests/unit/evaluation/test_reviewer_digest.py -q
python -m pytest tests/integration/test_eval_run_cli.py tests/integration/test_qa_bundle_cli.py -q
python -m pytest tests/e2e/test_live_provider_gate.py -q
python scripts/release_candidate_gate.py --mode ci
```

